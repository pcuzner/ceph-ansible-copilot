
import os
import json
import socket
from collections import OrderedDict

from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import (AuthenticationException,
                                    NoValidConnectionsError, SSHException)

from ceph_ansible_copilot.utils import (merge_dicts, netmask_to_cidr,
                                        bytes2human)
from ceph_ansible_copilot.rules import HostState


# Requires
# 'install' command on the target ceph nodes


class Host(object):

    # supported_platforms = ['RedHat']
    connection_timeout = 2
    supported_roles = OrderedDict([
        ("mon", "M"),
        ("osd", "O"),
        ("rgw", "R"),
        ("mds", "F"),
    ])

    ssh_status = {
        0: "ok",
        4: "connection attempt timed out",
        8: "authentication exception",
        12: "host unresponsive/uncontactable",
        16: "copy of public key failed",
        20: "unable to copy key without a password"
    }

    # nic_prefix = ('en', 'eth')          # tuple

    def __init__(self, hostname=None, roles=None):
        self.hostname = hostname
        self.username = 'root'
        self.ssh_ready = False
        self.password = None
        self.roles = roles if roles else []
        self._facts = {}                # populated by ansible setup module
        self.state = 'Unknown'          # Unknown, OK, NOTOK
        self.state_msg = ''
        self.selected = True

        self.available_cores = 0
        self.available_mb = 0

        self.core_count = 0
        self.ram = 0
        self.hdd_list = list()
        self.hdd_count = 0
        self.ssd_list = list()
        self.ssd_count = 0
        self.nic_count = 0
        self.disk_capacity = 0
        self.subnets = []              # ipv4 network list
        self.nics = {}                  # NIC details

    @property
    def role_types(self):
        """
        Provide an abbreviated version of the roles required
        :return: (str) string of chars corresponding to the roles required
        """

        role_str = ''
        for role in Host.supported_roles:
            if role in self.roles:
                role_str += Host.supported_roles[role]
            else:
                role_str += '.'
        return role_str

    def seed(self, ansible_facts):
        nic_drivers = {
            "ixgbe": 10,
            "i40e": 40,
            "cxgb": 10
        }

        self._facts = ansible_facts['ansible_facts']

        self.available_cores = self._facts.get('ansible_processor_count') * \
            self._facts.get('ansible_processor_threads_per_core')
        self.available_mb = self._facts['ansible_memory_mb']['real']['total']

        # extract the stats that the UI will show
        self.core_count = self.available_cores
        self.ram = self.available_mb

        hdd = self._free_disks(rotational=1)
        ssd = self._free_disks(rotational=0)
        self.hdd_list = hdd.keys()
        self.ssd_list = ssd.keys()
        self.hdd_count = len(hdd.keys())
        self.ssd_count = len(ssd.keys())
        all_disks = merge_dicts(hdd, ssd)
        total = 0
        for disk_id in all_disks:
            sectors = int(all_disks[disk_id]['sectors'])
            sectorsz = int(all_disks[disk_id]['sectorsize'])
            total += sectors * sectorsz
        self.disk_capacity = total

        subnets = set()
        nic_blacklist = ('lo')
        interfaces = [nic for nic in self._facts['ansible_interfaces']
                      if not nic.startswith(nic_blacklist)]
        self.nic_count = len(interfaces)

        for nic_id in interfaces:
            key = 'ansible_{}'.format(nic_id)
            nic_config = self._facts[key].get('ipv4')
            if nic_config:
                network = nic_config['network']
                cidr = netmask_to_cidr(nic_config['netmask'])
                net_str = '{}/{}'.format(network, cidr)
                subnets.add(net_str)

                nic_type = nic_drivers.get(self._facts[key].get('module'), 1)
                self.nics[nic_id] = {
                                     "network": net_str,
                                     "driver": self._facts[key].get("module"),
                                     "state": self._facts[key].get("active"),
                                     "nic_gb": nic_type
                                    }

        self.subnets = list(subnets)

    def check(self):

        host_state = HostState(self)
        host_state.check()
        self.state = host_state.state
        self.state_msg = host_state.state_long

    @property
    def ssh_state(self):

        client = SSHClient()
        rc = self._ssh_connect(client)
        if rc == 0:
            client.close()

        return rc

    def _ssh_connect(self, client, use_password=False):

        client.set_missing_host_key_policy(AutoAddPolicy())
        client.load_host_keys(
            os.path.expanduser('~root/.ssh/known_hosts'))

        conn_args = {
            "hostname": self.hostname,
            "username": self.username,
            "timeout": Host.connection_timeout
        }

        if use_password:
            conn_args['password'] = self.password

        try:
            client.connect(**conn_args)

        except socket.timeout:
            # connection taking too long
            return 4

        except (AuthenticationException, SSHException):
            # Auth issue
            return 8

        except NoValidConnectionsError:
            # ssh uncontactable e.g. host is offline, port 22 inaccessible
            return 12

        return 0

    def copy_key(self):

        if not self.password:
            return 20

        copy_state = 0

        auth_key_file = "~/.ssh/authorized_keys"
        check_cmd = "cat {}".format(auth_key_file)
        client = SSHClient()

        rc = self._ssh_connect(client, use_password=True)

        if rc == 0:
            # connection successful
            # read our public key
            with open(os.path.expanduser("~/.ssh/id_rsa.pub"), "r") as pub:
                local_key = pub.readlines()

            stdin, stdout, stderr = client.exec_command(check_cmd)

            output = stdout.readlines()
            if output:
                # assumption is the format of the auth file is OK to use
                if local_key not in output:
                    # local key needs adding
                    cmd = "echo -e {} >> {}".format(local_key,
                                                    auth_key_file)
                    stdin, stdout, stderr = client.exec_command(cmd)
                else:
                    # key already there - noop
                    pass
            else:
                # auth file not there
                client.exec_command("install -DTm600 {}".format(auth_key_file))
                client.exec_command("echo -e {} > {}".format(local_key,
                                                             auth_key_file))

            self.ssh_ready = True
            client.close()
        else:
            # connection failure, unable to populate public key
            copy_state = 16
            self.ssh_ready = False

        return copy_state

    def _free_disks(self, rotational=1):
        free = {}
        for disk_id in self._facts['ansible_devices']:
            disk = self._facts['ansible_devices'][disk_id]
            if int(disk['rotational']) == rotational:
                if not disk['partitions']:
                    free[disk_id] = disk
        return free

    # def validate(self):
    #
    #     # Basic Checks
    #     if not self._facts:
    #         self.state = "Failed"
    #         self.state_msg = "Probe failure"
    #         return
    #
    #     if self._facts.get('ansible_os_family') not in Host.supported_platforms:
    #         self.state = "Failed"
    #         self.state_msg = "Unsupported OS"
    #         return

        # # Process the roles
        # for role in self.roles:
        #     if role == 'mon':
        #         self._valid_mon()
        #     if role == 'osd':
        #         self._valid_osd()
        #     if role == 'rgw':
        #         self._valid_rgw()

        # return True

    def info(self):
        """ function used by the table shown in the Hosts Validation page"""

        if self.selected:
            sel = ' X ' if self.state.lower() == 'ok' else ' '*3
        else:
            sel = ' '*3

        ram_bytes = self.ram * 1024**2

        # use a _ char in the string to help visual formatting
        s = ("{}_{}_{:<12s}__{:>2d}_{:>4s}__{:>2d}_{:>3d}_"
             "{:>3d}_{:>4s}_{:<11s}".format(sel,
                                            self.role_types,
                                            self.hostname[:12],
                                            self.core_count,
                                            bytes2human(ram_bytes),
                                            self.nic_count,
                                            self.hdd_count,
                                            self.ssd_count,
                                            bytes2human(self.disk_capacity),
                                            self.state[:11]))
        s = s.replace('_', ' ')

        return s

    # def _valid_mon(self):
    #     return True
    #
    # def _valid_osd(self):
    #     return True
    #
    # def _valid_rgw(self):
    #     return True

    def __repr__(self):
        return json.dumps({attr: getattr(self, attr) for attr in self.__dict__
                           if not attr.startswith('_')}, indent=4)

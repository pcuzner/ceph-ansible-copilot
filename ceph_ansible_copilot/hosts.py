
import json
from collections import OrderedDict

from ceph_ansible_copilot.utils import (merge_dicts, netmask_to_cidr,
                                        bytes2human, SSHsession)
from ceph_ansible_copilot.rules import HostState


class Host(object):

    supported_roles = OrderedDict([
        ("mon", "M"),
        ("osd", "O"),
        ("rgw", "R"),
        ("mds", "F"),
    ])

    def __init__(self, hostname=None, roles=None):

        self.hostname = hostname
        self.ssh = SSHsession(self.hostname)

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
        self.probed = False

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
            "cxgb": 10,
            "mlx4_core": 10
        }

        self._facts = ansible_facts['ansible_facts']

        # FIXME: Should this use ansible_processort_vcpus?
        self.available_cores = self._facts.get('ansible_processor_count') * \
            self._facts.get('ansible_processor_threads_per_core') * \
            self._facts.get('ansible_processor_cores')

        self.available_mb = self._facts['ansible_memory_mb']['real']['total']

        # extract the stats that the UI will show
        self.core_count = self.available_cores
        self.ram = self.available_mb

        hdd = self._free_disks(rotational=1)
        ssd = self._free_disks(rotational=0)
        self.hdd_list = sorted(hdd.keys())
        self.ssd_list = sorted(ssd.keys())
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

    def _free_disks(self, rotational=1):
        free = {}
        for disk_id in self._facts['ansible_devices']:
            disk = self._facts['ansible_devices'][disk_id]

            # skip device-mapper devices
            if disk_id.startswith('dm-'):
                continue
            # skip disks that have partitions already
            if disk['partitions']:
                continue
            # skip lvm owned devices
            if disk['holders']:
                continue
            # skip child devices of software RAID
            if disk['links']['masters']:
                continue

            if int(disk['rotational']) == rotational:
                if not disk['partitions']:
                    free[disk_id] = disk
        return free

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

    def __repr__(self):

        dumper = dict()
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (str, int, list, dict)):
                dumper[k] = v
            else:
                dumper[k] = json.loads(repr(v))

        return json.dumps(dumper, indent=4)

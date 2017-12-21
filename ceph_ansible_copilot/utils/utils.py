
import shutil
import ConfigParser
import os
import pwd
import socket
import threading
import Queue
import getpass
import yaml
from yaml.scanner import ScannerError

from paramiko.rsakey import RSAKey
from paramiko.ssh_exception import SSHException

from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import (AuthenticationException,
                                    NoValidConnectionsError)

TCP_TIMEOUT = 2


def bytes2human(in_bytes, target_unit=None):
    """
    Convert a given number of bytes into a more consumable form
    :param in_bytes: bytes to convert (int)
    :param target_unit: target representation MB, GB, TB etc
    :return: string of the converted value with a suffix e.g. 5G
    """

    suffixes = ['K', 'M', 'G', 'T', 'P']

    rounding = {'K': 0, 'M': 0, 'G': 0, 'T': 0, 'P': 1}

    size = float(in_bytes)

    if size < 0:
        raise ValueError('number must be non-negative')

    divisor = 1024

    for suffix in suffixes:
        size /= divisor
        if size < divisor or suffix == target_unit:
            char1 = suffix[0]
            precision = rounding[char1]
            size = round(size, precision)
            fmt_string = '{0:.%df}{1}' % rounding[char1]

            return fmt_string.format(size, suffix)

    raise ValueError('number too large')


def user_exists(username):
    try:
        pwd.getpwnam(username)
    except KeyError:
        # user does not exist
        return False
    else:
        return True


def merge_dicts(*dict_args):
    result = {}

    for dictionary in dict_args:
        result.update(dictionary)
    return result


def netmask_to_cidr(netmask):
    """ convert dotted quad netmask to CIDR (int) notation """
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])


def dns_ok(host_name, timeout=None):

    def check_host_in_dns():
        try:
            socket.gethostbyname(host_name)
        except socket.gaierror:
            q.put(False)
        else:
            q.put(True)

    if not timeout:
        try:
            timeout = TCP_TIMEOUT
        except NameError:
            timeout = 2

    q = Queue.Queue()
    t = threading.Thread(target=check_host_in_dns)
    t.daemon = True
    t.start()
    try:
        return q.get(True, timeout)
    except Queue.Empty:
        return False


def expand_hosts(host_text):
    hosts = []
    for hostname in host_text.split('\n'):
        if '[' in hostname:
            brkt_pos = hostname.index('[')
            prefix = hostname[:brkt_pos]
            sfx_range = hostname[brkt_pos + 1:-1].split('-')
            for n in range(int(sfx_range[0]), int(sfx_range[1]) + 1, 1):
                hosts.append(prefix + str(n))

        else:
            if hostname:
                hosts.append(hostname)
    return hosts


def check_dns(host_list):
    return sorted([host for host in host_list if not dns_ok(host)])


def get_selected_button(button_group):
    return [btn.get_label() for btn in button_group
            if btn.state is True][0]


def check_ssh_access(local_user=None, ssh_user='root', hosts=None):

    ssh_errors = []
    for hostname in hosts:
        host = hosts[hostname]
        if host.ssh_state == 0:
            host.ssh_ready = True
        else:
            ssh_errors.append(hostname)

    return sorted(ssh_errors)


def valid_yaml(yml_data):
    """
    Validate a data stream(list) as acceptable yml
    :param yml_data: (list) of lines that would represent a yml file
    :return: (bool) to confirm whether the yaml is ok or not
    """

    yml_stream = '\n'.join(yml_data)
    try:
        _yml_ok = yaml.safe_load(yml_stream)
    except ScannerError:
        return False
    else:
        return True


def setup_ansible_cfg(ceph_ansible_dir='/usr/share/ceph-ansible'):
    """
    update the ansible.cfg file in the ceph-ansible directory to turn off
    deprecation warnings. The original file is saved, for restoration after
    copilot completes
    :param ceph_ansible_dir : (str) path to the ceph-ansible root directory
    :return: None
    """

    ansible_cfg = os.path.join(ceph_ansible_dir, 'ansible.cfg')
    ansible_cfg_bkup = '{}_bak'.format(ansible_cfg)

    cfg_changes = [
        ('defaults', 'deprecation_warnings', 'False')
    ]

    if not os.path.exists(ansible_cfg):
        raise EnvironmentError("ansible.cfg is not in the ceph-ansible"
                               "directory - unable to continue")

    cfg_file = ConfigParser.SafeConfigParser()
    cfg_file.readfp(open(ansible_cfg, 'r'))
    changes_made = False
    for setting in cfg_changes:
        section, variable, required_value = setting
        try:
            current_value = cfg_file.get(section, variable)
            if current_value != required_value:
                cfg_file.set(section, variable, required_value)
                changes_made = True
        except ConfigParser.NoOptionError:
            cfg_file.set(section, variable, required_value)
            changes_made = True

    if changes_made:
        shutil.copy2(ansible_cfg,
                     ansible_cfg_bkup)

    # use unbuffered I/O to commit the change
    with open(ansible_cfg, 'w', 0) as c:
        cfg_file.write(c)


def restore_ansible_cfg(ceph_ansible_dir='/usr/share/ceph-ansible'):
    """
    if a backup copy exists, restore the ansible.cfg file in the ceph-ansible
    directory and then remove our backup copy
    :param ceph_ansible_dir: (str) installation directory of ceph-ansible
    :return: None
    """

    ansible_cfg = os.path.join(ceph_ansible_dir, 'ansible.cfg')
    ansible_cfg_bkup = '{}_bak'.format(ansible_cfg)

    if os.path.exists(ansible_cfg_bkup):
        shutil.copy2(ansible_cfg_bkup,
                     ansible_cfg)

        # delete the _bak file
        os.remove(ansible_cfg_bkup)


def get_used_roles(config):
    """
    Process the config object's hosts to provide a consolidated list of
    roles that the hosts are defined to use
    :param config: (object) config object containing host objects
    :return: (list) consolidated list of roles from hosts selected for
    installation
    """

    used_roles = set([])

    for host_name in config.hosts.keys():
        host_obj = config.hosts[host_name]
        if not host_obj.selected:
            continue

        host_roles = set(host_obj.roles)
        used_roles |= host_roles

    # mgr roles are aligned to the mon role, so if there is a mon defined we
    # automatically enable it to be a mgr too
    if 'mon' in used_roles:
        used_roles.add('mgr')

    return list(used_roles)


def get_pgnum(config):
    """
    simplistic pgnum calculation based on
    http://docs.ceph.com/docs/master/rados/operations/placement-groups/
    :param config: (config object) contains a hosts dict, with all gathered
                   specs
    :return: (int) pg number to use for a pool
    """

    hdd_total = 0
    ssd_total = 0
    for host_name in config.hosts:
        host = config.hosts[host_name]
        if host.selected:
            hdd_total += host.hdd_count
            ssd_total += host.ssd_count

    total_drives = max(hdd_total, ssd_total)
    if total_drives < 5:
        return 64
    elif total_drives < 10:
        return 128
    elif total_drives < 50:
        return 512
    else:
        return 1024


class SSHConfig(object):

    def __init__(self, user=None, autoadd=True):

        self.configured = False

        if not user:
            self.user = getpass.getuser()
        else:
            self.user = user

        if self.key_exists:
            self.configured = True
        else:
            if autoadd:
                self.add_key()
            else:
                self.configured = False

    @property
    def key_exists(self):
        return os.path.exists(os.path.expanduser('~/.ssh/id_rsa'))

    def add_key(self):
        ssh_dir = os.path.expanduser('~/.ssh')
        if not os.path.exists(ssh_dir):
            # create the dir
            os.mkdir(ssh_dir, 0700)

        # key is needed
        key = RSAKey.generate(4096)
        pub_file = os.path.join(ssh_dir, 'id_rsa.pub')
        prv_file = os.path.join(ssh_dir, 'id_rsa')
        comment_str = '{}@{}'.format(self.user,
                                     socket.gethostname())

        # Setup the public key file
        try:
            with open(pub_file, "w", 0) as pub:
                pub.write("ssh-rsa {} {}\n".format(key.get_base64(),
                                                   comment_str))
        except IOError:
            print("Unable to write to {}".format(pub_file))
            return
        except SSHException:
            print("generated key is invalid")
            return
        else:
            os.chmod(pub_file, 0600)

        # setup the private key file
        try:
            with open(prv_file, "w", 0) as prv:
                key.write_private_key(prv)
        except IOError:
            print("Unable to write to {}".format(prv_file))
            return
        except SSHException:
            print("generated key is invalid")
            return
        else:
            os.chmod(prv_file, 0600)

        self.configured = True

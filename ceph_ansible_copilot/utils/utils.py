
import os
import pwd
import socket
import threading
import Queue
import getpass

from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import (AuthenticationException, SSHException,
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


def check_ssh_access(local_user=None, ssh_user='root', host_list=None):

    if not host_list:
        host_list = []

    if not local_user:
        local_user = getpass.getuser()

    ssh_errors = []
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.load_host_keys(
        os.path.expanduser('~{}/.ssh/known_hosts'.format(local_user)))

    for hostname in host_list:
        try:
            client.connect(hostname=hostname, username=ssh_user,
                           timeout=TCP_TIMEOUT)
        except socket.timeout:
            # connection taking too long
            ssh_errors.append(hostname)
            continue
        except (AuthenticationException, SSHException) as err:
            # TODO : log this error to a copilot log file
            ssh_errors.append(hostname)
            continue
        except NoValidConnectionsError:
            # ssh uncontactable e.g. host is offline, port 22 inaccessible
            ssh_errors.append(hostname)
            continue
        else:
            client.close()

    return sorted(ssh_errors)

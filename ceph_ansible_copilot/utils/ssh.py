import os
import socket
import getpass
import json

from paramiko.rsakey import RSAKey
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import (AuthenticationException,
                                    NoValidConnectionsError, SSHException)

# Requires
# 'install' command on the target ceph nodes


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


class SSHsession(object):

    connection_timeout = 2

    ssh_status_codes = {
        0: ("OK", "ok"),
        4: ("TIMEOUT", "connection attempt timed out"),
        8: ("AUTHFAIL", "authentication exception"),
        12: ("NOCONN", "host unresponsive/uncontactable"),
        16: ("COPYFAIL", "copy of public key failed"),
        20: ("NOPASSWD", "unable to copy key without a password"),
        24: ("UNKNOWN", "Unknown or unprobed state"),
        28: ("NOTFOUND", "Unable to resolve hostname - missing DNS?"),
        32: ("CHECKING", "checking access"),
        36: ("KEY-COPY", "copying ssh public key"),
    }

    def __init__(self, hostname, username='root', password=''):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.status_code = 24

    @property
    def ok(self):
        return self.status_code == 0

    def _check(self):

        client = SSHClient()
        self.status_code = self._ssh_connect(client)
        if self.status_code == 0:
            client.close()

    def setup(self, callback=None):

        self.status_code = 32                   # checking state
        if callback:
            callback()

        self._check()
        if callback:
            callback()

        if self.status_code in [0, 4, 12, 28]:
            # nothing more to do for this host
            return
        elif self.status_code == 8:
            # attempt to use the configured password
            self.status_code = 36
            if callback:
                callback()
            self._copy_key()

        if callback:
            callback()

    @property
    def shortmsg(self):
        return SSHsession.ssh_status_codes[self.status_code][0]

    @property
    def longmsg(self):
        return SSHsession.ssh_status_codes[self.status_code][1]

    def _ssh_connect(self, client, use_password=False):

        client.set_missing_host_key_policy(AutoAddPolicy())

        known_hosts_file = os.path.expanduser('~/.ssh/known_hosts')
        if not os.path.exists(known_hosts_file):
            open(known_hosts_file, "a")
            os.chmod(known_hosts_file, mode=0644)

        client.load_host_keys(known_hosts_file)

        conn_args = {
            "hostname": self.hostname,
            "username": self.username,
            "timeout": SSHsession.connection_timeout
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

        except socket.gaierror:
            # hostname not found - not in DNS or /etc/hosts?
            return 28

        return 0

    def _copy_key(self):

        if not self.password:
            self.status_code = 20
            return

        auth_key_file = "~/.ssh/authorized_keys"
        check_cmd = "cat {}".format(auth_key_file)
        client = SSHClient()

        self.status_code = self._ssh_connect(client, use_password=True)

        if self.status_code == 0:
            # connection successful
            # read our public key
            with open(os.path.expanduser("~/.ssh/id_rsa.pub"), "r") as pub:
                local_key = pub.read().rstrip()

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

            client.close()
        else:
            # connection with password failed
            pass

    def __repr__(self):
        return json.dumps({attr: getattr(self, attr) for attr in self.__dict__
                           if not attr.startswith('_')}, indent=4)

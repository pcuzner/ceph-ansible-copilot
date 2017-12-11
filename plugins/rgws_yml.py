#!/usr/bin/env python2

import os
import shutil
from ceph_ansible_copilot.utils import get_used_roles

description = "use the existing rgws.yml, or create one from the sample"
yml_file = '/usr/share/ceph-ansible/group_vars/rgws.yml'


def plugin_main(config=None):

    if not config:
        raise ValueError("Config object not received from caller")

    used_roles = get_used_roles(config)
    if "rgw" not in used_roles:
        return None

    if not os.path.exists(yml_file):
        # create a copy from the sample file
        sample = '{}.sample'.format(yml_file)
        if os.path.exists(sample):
            shutil.copy2(sample, yml_file)
        else:
            raise EnvironmentError("sample file for rgws.yml not found")

    return None


if __name__ == '__main__':
    pass

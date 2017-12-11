#!/usr/bin/env python2

import os
import shutil

from ceph_ansible_copilot.utils import get_used_roles, valid_yaml, get_pgnum

description = "use the existing mons.yml, or create one from the sample"
yml_file = '/usr/share/ceph-ansible/group_vars/mons.yml'


def plugin_main(config=None):

    if not config:
        raise ValueError("Config object not received from caller")

    if not os.path.exists(yml_file):

        used_roles = get_used_roles(config)
        if 'mds' in used_roles:
            pgcount = get_pgnum(config)
            yaml_data = create_yaml(pgcount)

            if valid_yaml(yaml_data):
                return ('yml', yaml_data)
        else:
            # create a copy from the sample file
            sample = '{}.sample'.format(yml_file)
            if os.path.exists(sample):
                shutil.copy2(sample, yml_file)
            else:
                raise EnvironmentError("sample file for mons.yml not found")

    return None


def create_yaml(pgcount):

    num_cephfs_pools = 2

    out = list()
    out.append("mon_group_name: mons")
    out.append("cephfs: cephfs")
    out.append("cephfs_data: cephfs_data")
    out.append("cephfs_metadata: cephfs_metadata")
    out.append("cephfs_pools:")
    out.append('  - {{ name: "{{{{ cephfs_data }}}}", '
               'pgs: {} }}'.format(int(pgcount/num_cephfs_pools)))
    out.append('  - {{ name: "{{{{ cephfs_metadata }}}}", '
               'pgs: {} }}'.format(int(pgcount/num_cephfs_pools)))
    out.append(' ')


    return out


if __name__ == '__main__':
    pass

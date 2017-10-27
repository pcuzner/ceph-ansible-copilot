#!/usr/bin/env python2

import os
import shutil


description = "use the existing mons.yml, or create one from the sample"
yml_file = '/usr/share/ceph-ansible/group_vars/mons.yml'


def plugin_main(config=None):

    if not os.path.exists(yml_file):
        # create a copy from the sample file
        sample = '{}.sample'.format(yml_file)
        if os.path.exists(sample):
            shutil.copy2(sample, yml_file)
        else:
            raise EnvironmentError("sample file for mons.yml not found")

    return None


if __name__ == '__main__':
    pass

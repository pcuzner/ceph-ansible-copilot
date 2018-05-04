#!/usr/bin/python

from setuptools import setup
import distutils.command.install_scripts
import shutil
import os

import ceph_ansible_copilot


if os.path.exists('README'):
    with open('README') as readme_file:
        long_description = readme_file.read().strip()
else:
    long_description = ''


# idea from http://stackoverflow.com/a/11400431/2139420
class StripExtension(distutils.command.install_scripts.install_scripts):
    """
    Class to handle the stripping of .py extensions in for executable file names
    making them more user friendly
    """
    def run(self):
        distutils.command.install_scripts.install_scripts.run(self)
        for script in self.get_outputs():
            if script.endswith(".py"):
                shutil.move(script, script[:-3])


setup(
    name="copilot",
    version=ceph_ansible_copilot.__version__,
    description="Text based UI to simplify Ceph installation for new users",
    long_description=long_description,
    author="Paul Cuzner",
    author_email="pcuzner@redhat.com",
    url="http://github.com/pcuzner/ceph-ansible-copilot",
    license="LGPLv2",
    packages=[
        "ceph_ansible_copilot",
        "ceph_ansible_copilot/ansible",
        "ceph_ansible_copilot/rules",
        "ceph_ansible_copilot/ui",
        "ceph_ansible_copilot/utils",
        ],
    scripts=[
        'copilot.py'
    ],
    data_files=[('/usr/share/ceph-ansible-copilot/plugins',
                 ['plugins/all_yml.py', 'plugins/ansible_hosts.py',
                  'plugins/mdss_yml.py', 'plugins/mgrs_yml.py',
                  'plugins/mons_yml.py', 'plugins/osds_yml.py',
                  'plugins/rgws_yml.py', 'plugins/site_yml.py'])],
    cmdclass={
        "install_scripts": StripExtension
    }
)

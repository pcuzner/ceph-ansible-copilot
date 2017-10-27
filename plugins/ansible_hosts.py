#!/usr/bin/env python2

from collections import OrderedDict
import json

# Requires ansible 2.0->2.3

from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory


description = 'Create /etc/ansible/hosts'
yml_file = '/etc/ansible/hosts'


def plugin_main(config=None):

    if not config:
        return []
    role_to_group = {
        "mon": "mons",
        "osd": "osds",
        "rgw": "rgws",
        "mds": "mdss"
    }

    groups = OrderedDict([
        ("mons", []),
        ("osds", []),
        ("rgws", []),
        ("mdss", [])
    ])

    # groups = {
    #     "mons": [],
    #     "osds": [],
    #     "rgws": [],
    #     "mdss": []
    # }

    # for host_name in sorted(config['hosts'].keys()):
    #     host_obj = config['hosts'][host_name]
    for host_name in sorted(config.hosts.keys()):
        host_obj = config.hosts[host_name]
        if host_obj.selected:
            for role in host_obj.roles:
                groups[role_to_group.get(role)].append(host_name)

    return ('ini', format_groups(groups))


def format_groups(groups):

    def write_group(group_name, group_hosts):
        grp = []
        grp.append("[{}]".format(group_name))
        for _h in group_hosts:
            grp.append(_h)
        grp.append(" ")
        return grp

    contents = []
    for group in groups:
        hosts = groups[group]
        if hosts:
            contents.extend(write_group(group, hosts))
            if group == 'mons':
                contents.extend(write_group('mgrs', hosts))

    return contents


def dump_hosts():

    variable_manager = VariableManager()
    loader = DataLoader()
    inventory = Inventory(
        loader=loader,
        variable_manager=variable_manager,
        host_list=yml_file
    )

    hosts = {}
    for group in inventory.get_groups():
        host_list = inventory.get_group(group).hosts
        hosts[group] = [host.name for host in host_list]

    return json.dumps(hosts, indent=4)

if __name__ == "__main__":
    print dump_hosts()

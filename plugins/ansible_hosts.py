#!/usr/bin/env python2

from collections import OrderedDict
import json

from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager


description = 'Create /etc/ansible/hosts'
yml_file = '/etc/ansible/hosts'


def plugin_main(config=None):

    if not config:
        raise ValueError("Config object not received from caller")

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

    loader = DataLoader()
    inventory = InventoryManager(
        loader=loader,
        sources=yml_file)

    hosts = {}
    groups = inventory.groups
    for group in groups.keys():
        host_list = inventory.get_hosts(group)
        hosts[group] = [host.name for host in host_list]

    return json.dumps(hosts, indent=4)

if __name__ == "__main__":
    print dump_hosts()

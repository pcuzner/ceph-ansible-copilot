#!/usr/bin/env python2

import os
import yaml
import collections

description = "use the existing site.yml, or create one from the sample"
yml_file = '/usr/share/ceph-ansible/site.yml'

# The sample file includes a host entry for each role, but if the role isn't
# supported by copilot, the playbook generates warning messages that disrupt
# the UI. To address this, roles that are NOT supported by copilot, are
# deleted from the generated site.yml file.


# Setup Ordered dicts for the internal representation of the yaml. Without this
# the yaml created for site.yml doesn't look like the original sample
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())


def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)


def plugin_main(config=None):

    if not config:
        raise ValueError("Config object not received from caller")

    if not os.path.exists(yml_file):
        # create a copy from the sample file
        sample = '{}.sample'.format(yml_file)
        if os.path.exists(sample):
            # shutil.copy2(sample, yml_file)
            used_roles = get_used_roles(config)
            updated_yaml = process_yaml(sample, used_roles)
            write_yaml(yml_file, updated_yaml)
        else:
            raise EnvironmentError("sample file for site.yml not found")

    return None


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


def process_yaml(sample_file, used_roles):
    """
    Update the site.yml file, deleting any role that is not used
    by copilot (i.e. doesn't match an item in the used_roles parameter)
    :param sample_file: (str) filename of the source yml file
    :param used_roles: (list) list of role names (mon, rgw, osd)
    :return: yaml data to write to the site.yml file
    """

    with open(sample_file, "r") as stream:
        yaml_data = yaml.load(stream)

    roles = ["{}s".format(role) for role in used_roles]

    for item in yaml_data:
        if 'hosts' not in item:
            # only interested yaml tasks that defined the hosts, skip the rest
            continue

        # yaml section has a hosts definition, so check it
        hosts = item['hosts']
        if isinstance(hosts, str):
            # single role
            if hosts in roles:
                continue
            # this role is not defined by copilot, so drop the entry
            item = 'DELETED'

        else:
            # multiple roles
            item['hosts'] = [role for role in hosts if role in roles]

    return [item for item in yaml_data if item != "DELETED"]


def write_yaml(yaml_file, yaml_data):

    with open(yaml_file, "w") as out:
        yaml.dump(yaml_data,
                  stream=out,
                  default_flow_style=False,
                  explicit_start=True)


if __name__ == '__main__':
    pass

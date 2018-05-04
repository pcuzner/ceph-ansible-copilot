#!/usr/bin/env python2

import os
import yaml
import logging

from collections import OrderedDict

from ceph_ansible_copilot.utils import get_used_roles


description = ("use the existing site.yml or site-docker.yml, or create one "
               "from the sample")
yml_file = '/usr/share/ceph-ansible/site.yml'

logger = logging.getLogger('copilot')

# The sample file includes a host entry for each role, but if the role isn't
# supported by copilot, the playbook generates warning messages that disrupt
# the UI. To address this, roles that are NOT supported by copilot, are
# deleted from the generated site.yml file. Also, the all.yml vars file is
# not found by default in Ansible 2.4 (2.3 is fine), so this plugin also
# adds a task to use include_vars to ensure all.yml is included in the play.


def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):

    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):

    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def plugin_main(config=None, mode='add'):


    if not config:
        raise ValueError("Config object not received from caller")

    # pick yml file based on the deployment type, bare-metal or container
    yml_file = config.defaults.playbook[config.deployment_type]
    logger.debug("will use site file: {}".format(yml_file))
    logger.debug("update mode is {}".format(mode))

    if not os.path.exists(yml_file):
        # create a copy from the sample file
        sample = '{}.sample'.format(yml_file)
        if os.path.exists(sample):

            if isinstance(config, list):
                used_roles = config
            else:
                used_roles = get_used_roles(config)

            yml_data = load_yaml(sample)
            logger.debug("Cluster is using the following roles - "
                         "{}".format(','.join(used_roles)))
            # updated_yaml = process_yaml(yml_data, used_roles)
            updated_yaml = manage_all_yml(yml_data, mode=mode)

            write_yaml(yml_file, updated_yaml)
        else:
            raise EnvironmentError("sample 'site' file not found")
    else:
        # site.yml already exists, so we just make sure the include for
        # all.yml is not there
        yaml_data = load_yaml(yml_file)
        updated_yaml_data = manage_all_yml(yaml_data, mode=mode)
        if updated_yaml_data:
            write_yaml(yml_file, updated_yaml_data)

    return None


def manage_all_yml(yaml_data, mode):

    all_vars_file = '/usr/share/ceph-ansible/group_vars/all.yml'
    pre_req_tasks = yaml_data[0].get('tasks', yaml_data[0].get('pre_tasks'))

    if mode == 'add':
        all_vars = OrderedDict([('name', 'Add all.yml'),
                               ('include_vars',
                                OrderedDict([('file',
                                              all_vars_file)]))])
        pre_req_tasks.append(all_vars)
        return yaml_data
    elif mode == 'delete':
        p = [item for item in pre_req_tasks if item['name'] != 'Add all.yml']
        yaml_data[0]['tasks'] = p
        if len(yaml_data[0]['tasks']) == len(pre_req_tasks):
            return None
        else:
            return yaml_data
    else:
        raise ValueError("manage_all_yml passed invalid mode")


def load_yaml(yml_filename):
    logger.debug("Loading yaml from {}".format(yml_filename))
    with open(yml_filename, "r") as stream:
        yaml_data = ordered_load(stream, yaml.SafeLoader)

    return yaml_data


def process_yaml(yaml_data, used_roles):
    """
    Read the site.yml.sample deleting any role that is not used by copilot
    (i.e. doesn't match an item in the used_roles parameter)
    :param yaml_data: (list) load yamldata
    :param used_roles: (list) list of role names (mon, rgw, osd)
    :return: edited yaml data to write to the site.yml file
    """

    supported_roles = ["{}s".format(role) for role in used_roles]
    if 'mons' in supported_roles:
        supported_roles.append('mgrs')

    for item in yaml_data:
        if 'hosts' not in item:
            # only interested yaml tasks that defined the hosts, skip the rest
            continue

        # yaml section has a hosts definition, so check it
        hosts = item['hosts']
        if isinstance(hosts, str):
            # single role
            if hosts in supported_roles:
                continue
            # this role is not defined by copilot, so drop the entry
            item['deleteme'] = True

        else:
            # multiple roles
            item['hosts'] = [role for role in hosts if role in supported_roles]

    return [item for item in yaml_data if not item.get('deleteme')]


def write_yaml(yaml_file, yaml_data):
    logger.debug("Writing out playbook to {}".format(yaml_file))
    with open(yaml_file, "w", 0) as out:
        ordered_dump(yaml_data,
                     Dumper=yaml.SafeDumper,
                     stream=out,
                     default_flow_style=False,
                     explicit_start=True)


if __name__ == '__main__':
    plugin_main(config=['mon', 'osd', 'rgw', 'mds'])

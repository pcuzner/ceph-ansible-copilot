#!/usr/bin/env python2

from ceph_ansible_copilot.utils import valid_yaml

description = "Create a osds.yml file to control osd creation"
yml_file = '/usr/share/ceph-ansible/group_vars/osds.yml'


def plugin_main(config=None):

    yml_data = create_yml(config)

    if valid_yaml(yml_data):
        return ('yml', yml_data)
    else:
        raise SyntaxError("Invalid yml created in osds_yml.py plugin")


def yml_ok(yml_list):
    yml = list(yml_list)
    yml.insert(0, '---')

    return True


def create_yml(config):

    out = []

    keys = ['osd_objectstore', 'osd_scenario', 'dmcrypt']
    for config_key in keys:
        out.append('{}: {}'.format(config_key,
                                   getattr(config, config_key)))
    out.append('')

    devices = get_devs(config.hosts)

    if devices:
        out.append('# devices common to all osd hosts')
        out.append("devices:")
        for dev in sorted(devices):
            out.append("  - /dev/{}".format(dev))

        if config.osd_scenario == 'non-collocated':
            journals = get_devs(config.hosts, dev_type='journal')

            # Assumption is the main app validates the ssd count is correct
            if journals:
                out.append('dedicated_devices:')
                tgt = len(devices)
                done = False
                for jrnl in sorted(list(journals)):
                    if jrnl.startswith('nvme'):
                        max_journals = 10
                    else:
                        max_journals = 5
                    for _n in range(0, max_journals, 1):
                        out.append("  - /dev/{}".format(jrnl))
                        tgt -= 1
                        if tgt == 0:
                            done = True
                            break
                    if done:
                        break

    out.append(' ')

    return out


def get_devs(host_data, dev_type='hdd'):
    dev_lists = []
    for h in host_data:
        if dev_type == 'hdd':
            dev_lists.append(set(host_data[h].hdd_list))
        else:
            dev_lists.append(set(host_data[h].ssd_list))

    return set.intersection(*dev_lists)


def test():
    hosts = {}
    class Host(object):
        pass
    hosts['a'] = Host
    hosts['b'] = Host
    hosts['c'] = Host

    hosts['a'].hdd_list = set(['a', 'b', 'c'])
    hosts['b'].hdd_list = set(['a', 'b', 'c'])
    hosts['c'].hdd_list = set(['a', 'b', 'c'])

    print get_devs(hosts)


if __name__ == '__main__':
    test()

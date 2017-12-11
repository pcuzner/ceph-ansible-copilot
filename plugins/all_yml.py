#!/usr/bin/env python2

import os
import platform

from ceph_ansible_copilot.utils import valid_yaml

description = "define the base variables"
yml_file = '/usr/share/ceph-ansible/group_vars/all.yml'


def plugin_main(config=None):

    if not config:
        raise ValueError("Config object not received from caller")

    yml = create_yml(config)

    if valid_yaml(yml):
        return ('yml', yml)
    else:
        raise SyntaxError("Invalid yml generated for {}".format(yml_file))


def create_yml(config):
    ceph_to_rhcs = {
        10: 2,
        12: 3
    }
    ceph_name = {
        10: 'jewel',
        11: 'kraken',
        12: 'luminous',
        13: 'mimic'
    }
    repo = {
        "RH CDN": {
            "type": "repository",
            "repo": "rhcs"
        },
        "Community": {
            "type": "repository",
            "repo": "community"
        },
        "Distro": {
            "type": "distro",
            "repo": None
        }
    }

    out = list()
    out.append('fetch_directory: ~/ceph-ansible-keys')
    out.append('cluster: {}'.format(config.cluster_name))
    # out.append('ceph_release_num: {}'.format(config['ceph_version']))
    out.append(' ')

    sw_src = config.sw_source
    ceph_repo = repo[sw_src]['repo']
    out.append('ceph_origin: {}'.format(repo[sw_src]['type']))
    if ceph_repo:
        out.append('ceph_repository: {}'.format(ceph_repo))
        if ceph_repo == 'rhcs':
            out.append('ceph_rhcs_version: '
                       '{}'.format(ceph_to_rhcs[config.ceph_version]))
            out.append('ceph_repository_type: cdn')
        else:
            # community deployment
            if platform.dist()[0] in ['redhat']:
                out.append('ceph_stable_redhat_distro: el7')
                out.append('ceph_stable_release: '
                           '{}'.format(ceph_name[config.ceph_version]))
            else:
                out.append('ceph_stable_release: '
                           '{}'.format(ceph_name[config.ceph_version]))

    out.append(' ')
    out.append('osd_objectstore: {}'.format(config.osd_objectstore))
    out.append(' ')

    mon_nic = get_common_nic('mon',
                             config.hosts,
                             config.public_network)

    out.append('monitor_interface: {}'.format(mon_nic))
    out.append('public_network: {}'.format(config.public_network))
    out.append('cluster_network: {}'.format(config.cluster_network))
    out.append(' ')
    out.append('# General ceph options')
    out.append("generate_fsid: true")
    out.append("cephx: true")
    out.append(' ')

    rgws = get_hosts(config.hosts, 'rgw')
    if rgws:
        dns_tld = '.'.join(os.environ['HOSTNAME'].split('.')[1:])
        out.append('# radosgw options')
        out.append('radosgw_dns_name: {}'.format(dns_tld))

        # default to use the public network as the i/f for radosgw instance
        rgw_nic = get_common_nic('rgw',
                                 config.hosts,
                                 config.public_network)
        out.append('radosgw_interface: {}'.format(rgw_nic))
        out.append(' ')

    return out


def get_hosts(host_data, host_type):
    return [h for h in host_data
            if host_data[h].selected and host_type in host_data[h].roles
            and host_data[h].state.lower() == 'ready']


def get_common_nic(role, host_data, public_network):

    role_txt = '{}s'.format(role.upper())
    nics_on_public = set()
    host_group = get_hosts(host_data, role)
    on_public = []

    for h in host_group:
        host = host_data[h]
        for nic in host.nics.keys():
            if host.nics[nic]['network'] == public_network:
                nics_on_public.add(nic)
                on_public.append(h)

    if len(on_public) != len(host_group):
        raise EnvironmentError("{} must connect to the public "
                               "subnet ({})".format(role_txt,
                                                    public_network))

    if len(nics_on_public) != 1:
        raise EnvironmentError("You have {} on a common subnet, but access it "
                               "using different NIC's - copilot uses a common "
                               "NIC name when defining the "
                               "{}".format(role_txt, role_txt))

    return list(nics_on_public)[0]


if __name__ == '__main__':
    pass

#!/usr/bin/env python2

from .base import BaseCheck


class ClusterState(BaseCheck):

    def __init__(self, hosts, mode='dev', install_source='community'):
        """
        Check the host membership within a cluster do not violate best
        practice rules. The checks are all _check prefixed and invoked by the
        parent classes 'run' method
        :param host_list: (dict) dict of Host objects, indexed by hostname
        :param mode: (str) either dev or prod
        """

        self.hosts = hosts
        self.mode = mode
        self.installation_source = install_source
        self.hosts_by_role = dict()
        self.selected_hosts = set()

        self._analyse_roles()

        assert isinstance(hosts, dict), \
            "ClusterCheck requires a dict of hosts, indexed by hostname"
        assert mode in ClusterState.valid_run_modes, \
            "Mode invalid, must be {}".format(ClusterState.valid_run_modes)

        BaseCheck.__init__(self)

    def _analyse_roles(self):

        for hostname in self.hosts:
            host = self.hosts[hostname]
            if not host.selected:
                continue

            self.selected_hosts.add(hostname)

            for role in host.roles:
                if role in self.hosts_by_role:
                    self.hosts_by_role[role].append(host.hostname)
                else:
                    self.hosts_by_role[role] = list([host.hostname])

    @property
    def mons(self):
        return len(self.hosts_by_role.get('mon', list()))

    @property
    def mdss(self):
        return len(self.hosts_by_role.get('mds', list()))

    def mgrs(self):
        return len(self.hosts_by_role.get('mgr', list()))

    @property
    def osds(self):
        return len(self.hosts_by_role.get('osd', list()))

    def _check_mons(self):
        mon_count = self.mons
        if self.mode == 'prod':
            if mon_count not in [3, 5]:
                self._add_problem('error',
                                  '{} mon(s) is invalid for production'.format(mon_count))

        else:
            if mon_count == 0:
                self._add_problem('error',
                                  "No mons selected")
                return
            if mon_count % 2 == 0:
                self._add_problem('error',
                                  '#MONs must be odd ({})'.format(mon_count))

    def _check_mds(self):
        if self.mode == 'prod':
            pass
        else:
            pass

    def _check_osds(self):
        osd_host_count = self.osds
        if self.mode == 'prod':
            if osd_host_count < 3:
                self._add_problem('error', 'too few OSD hosts'
                                           '({})'.format(osd_host_count))

    def _check_collocation(self):
        if self.mode == 'prod':

            for hostname in self.hosts:
                host = self.hosts[hostname]
                if len(host.roles) > 1:
                    if set(host.roles) == {'mon', 'mgr'}:
                        continue
                    else:
                        if self.installation_source == 'RH CDN':
                            self._add_problem('error',
                                              'collocation unsupported')
                            break
        else:
            pass

    def _check_host_states(self):

        for hostname in self.selected_hosts:
            host = self.hosts[hostname]
            if host.state_msg.lower().startswith('error'):
                self._add_problem('error',
                                  "Selected hosts have errors. Resolve, "
                                  "then click 'Next'")
                break


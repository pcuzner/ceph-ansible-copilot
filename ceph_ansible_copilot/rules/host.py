#!/usr/bin/env python2

import math
from .base import BaseCheck


class HostState(BaseCheck):

    disks_per_10g = 12

    reqs = {
        "os": {"cpu": 2,
               "ram": 4096},
        "osd": {"cpu": .5,
                "ram": 2048}
    }

    def __init__(self, host_object, mode='dev'):
        self.host = host_object
        self.mode = mode
        self.disk_count = max(self.host.ssd_count, self.host.hdd_count)

        BaseCheck.__init__(self)

    def _check_cpu_ram(self):
        available_cpu = self.host.core_count
        available_ram = self.host.ram

        for role in self.host.roles:
            if role == 'osd':
                available_cpu -= (self.disk_count * HostState.reqs[role]['cpu'])
                available_ram -= (self.disk_count * HostState.reqs[role]['ram'])

        if available_cpu < HostState.reqs['os']['cpu']:
            self._add_problem('warning', "#CPU's low")
        if available_ram < HostState.reqs['os']['ram']:
            self._add_problem('warning', 'RAM low')

    def _check_network(self):
        if 'osd' in self.host.roles:
            bandwidth = sum([self.host.nics[nic]['nic_gb']
                             for nic in self.host.nics])

            # 12 disks per 10g link - throughput optimised check
            multiplier = int(math.ceil(self.disk_count /
                                       float(self.disks_per_10g)))
            if bandwidth < (multiplier * 10):
                self._add_problem('warning', 'Network bandwidth low')

    def _check_role_prereq(self):

        if 'osd' in self.host.roles:

            if self.disk_count == 0:
                self._add_problem('error', 'no disks')

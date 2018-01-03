import unittest
import sys

sys.path.insert(0, '../')

from ceph_ansible_copilot import Host
from ceph_ansible_copilot.rules import ClusterState, HostState


class ClusterChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("ClusterChecks")
        cls.hosts = list([
            Host('mon_mgr', ['mon', 'mgr']),
            Host('mon', ['mon']),
            Host('osd', ['osd']),
            Host('mon_osd', ['mon', 'osd']),
            Host('osd_rgw', ['osd', 'rgw']),
            Host('rgw', ['rgw']),
            Host('mds', ['mds']),
            Host('mgr', ['mgr'])]
        )

    def _check_cluster(self, host_id_list, mode='dev', install_source='Community'):

        sfx = 1
        cluster_members = dict()
        for id in host_id_list:
            host_object = self.hosts[id]
            hostname = host_object.hostname
            if hostname in cluster_members:

                hostname = "{}{}".format(hostname,
                                         sfx)
                sfx += 1
                roles = host_object.roles
                host_object = Host(hostname, roles)

            cluster_members[hostname] = host_object

        c = ClusterState(cluster_members,
                         mode=mode,
                         install_source=install_source)
        c.check()
        return c

    def test_prod_1mons_3osds_FAIL(self):
        """ Prod - 1 mon with 3 osds should fail """
        c = self._check_cluster([0, 2, 2, 2], mode='prod')
        self.assertNotEqual(c.state, 'OK', msg=c.state_long)
        # print(c.state_long)

    def test_prod_3mons_3osds_OK(self):
        """ Prod - happy state test, separate mons and osds"""
        c = self._check_cluster([0, 0, 0, 2, 2, 2], mode='prod')
        # self.assertEqual(c.state, 'OK', msg=c.state_long)

    def test_prod_low_osd_hosts_FAIL(self):
        """ Prod - not enough hosts as OSDs, so should fail"""
        c = self._check_cluster([0, 0, 0, 2, 2], mode='prod')
        self.assertNotEqual(c.state, 'OK', msg=c.state_long)
        # print(c.state_long)

    def test_prod_4mons_3osds_FAIL(self):
        """ Prod - Even number of mons, should fail"""
        c = self._check_cluster([0, 0, 0, 0, 2, 2, 2], mode='prod')
        self.assertNotEqual(c.state, 'OK', msg=c.state_long)
        # print(c.state_long)

    def test_prod_collocation_OK(self):
        """ Prod - collocation of services, should work"""
        c = self._check_cluster([3, 3, 3], mode='prod')
        self.assertEqual(c.state, 'OK', msg=c.state_long)

    def test_prod_collocation_RH_FAIL(self):
        """ Prod - collocation of services, unsupported on RHT"""
        c = self._check_cluster([3, 3, 3], mode='prod', install_source='RH CDN')
        self.assertNotEqual(c.state, 'OK', msg=c.state_long)

    def shortDescription(self):
        return None

    def __str__(self):
        return "(%s) : %s" % (self._testMethodName,
                              self._testMethodDoc)


class HostChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("HostChecks")
        cls.specs = [
            # core_count, ram, hdd_count, ssd_count, nics
            (8, 36864, 10, 2, {"eth0": {"nic_gb": 10}}),
            (4, 2048, 10, 2, {"eth0": {"nic_gb": 10}}),
            (8, 36864, 16, 4, {"eth0": {"nic_gb": 10}}),
            (8, 4096, 0, 0, {"eth0": {"nic_gb": 10}})
        ]

    def _apply_spec(self, host_object, case_num, mode='dev'):
        specs = self.specs[case_num]
        host_object.core_count = specs[0]
        host_object.ram = specs[1]
        host_object.hdd_count = specs[2]
        host_object.ssd_count = specs[3]
        host_object.nics = specs[4]

        host_health = HostState(host_object, mode=mode)
        host_health.check()
        return host_health
        
    def test_prod_osd_resources_OK(self):
        """Prod - osd resources are OK for this configuration"""
        h = Host(hostname='svr1', roles='osd')
        host_health = self._apply_spec(h, 0, 'prod')

        self.assertEqual(host_health.state, 'OK',
                         msg="cpu/ram resources should be ok for this testcase")

    def test_prod_osd_resources_FAIL(self):
        """Prod - check osd cpu and ram low fails"""
        h = Host(hostname='svr1', roles='osd')
        host_health = self._apply_spec(h, 1, 'prod')

        self.assertNotEqual(host_health.state, 'OK')

    def test_prod_osd_network_FAIL(self):
        """Prod - Network bandwidth low for HDDs fails"""
        h = Host(hostname='svr1', roles='osd')
        host_health = self._apply_spec(h, 2, 'prod')
        self.assertNotEqual(host_health.state, 'OK')

    def test_prod_no_osd_disks_FAIL(self):
        """Prod - No free disks will fail"""
        h = Host(hostname='svr1', roles='osd')
        host_health = self._apply_spec(h, 3, 'prod')
        self.assertNotEqual(host_health.state, 'OK')

    def shortDescription(self):
        return None

    def __str__(self):
        return "(%s) : %s" % (self._testMethodName,
                              self._testMethodDoc)


if __name__ == '__main__':
    
    cluster_suite = unittest.TestLoader().loadTestsFromTestCase(ClusterChecks)
    host_suite = unittest.TestLoader().loadTestsFromTestCase(HostChecks)

    unittest.TextTestRunner(verbosity=2).run(cluster_suite)

    unittest.TextTestRunner(verbosity=2).run(host_suite)

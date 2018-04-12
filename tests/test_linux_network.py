#!/usr/bin/env python
#
# unit tests for igcollect/linux_network
#
# Copyright (c) 2018, InnoGames GmbH
#

from inspect import currentframe, getfile
from os.path import dirname, join
from src.linux_network import InterfaceStatistics
from tarfile import open as taropen
import unittest


_stat = {
    'bond0': {
        'bytesIn': 45172046900537, 'bytesOut': 54060616468741,
        'pktsIn': 49024433682, 'pktsOut': 52659406145
    },
    'bond0.10': {
        'bytesIn': 42846041034881, 'bytesOut': 49593465689742,
        'pktsIn': 26513809452, 'pktsOut': 49323945815
    },
    'br0': {
        'bytesIn': 915875620045, 'bytesOut': 190757907787,
        'pktsIn': 724040019, 'pktsOut': 69837376
    },
    'docker_gwbridge': {
        'bytesIn': 31203724271, 'bytesOut': 81264919337,
        'pktsIn': 251251406, 'pktsOut': 263269215
    },
    'eno1': {
        'bytesIn': 45168704612628, 'bytesOut': 54060616468219,
        'carrierOut': 0, 'collsOut': 0, 'dropIn': 5, 'dropOut': 0,
        'errsIn': 0, 'errsOut': 0, 'fifoIn': 0, 'fifoOut': 0, 'frameIn': 0,
        'pktsIn': 48976191639, 'pktsOut': 52659406140
    },
    'enp4s0f0': {
        'bytesIn': 3342287909, 'bytesOut': 522,
        'carrierOut': 0, 'collsOut': 0, 'dropIn': 1, 'dropOut': 0,
        'errsIn': 0, 'errsOut': 0, 'fifoIn': 0, 'fifoOut': 0, 'frameIn': 0,
        'pktsIn': 48242043, 'pktsOut': 5
    },
    'eth0': {
        'bytesIn': 174948514739, 'bytesOut': 80511808678,
        'carrierOut': 0, 'collsOut': 0, 'dropIn': 13, 'dropOut': 0,
        'errsIn': 0, 'errsOut': 0, 'fifoIn': 0, 'fifoOut': 0, 'frameIn': 0,
        'pktsIn': 386886632, 'pktsOut': 357720371
    },
    'ifb0': {
        'bytesIn': 0, 'bytesOut': 0,
        'pktsIn': 0, 'pktsOut': 0
    },
    'lo': {
        'bytesIn': 4050049925, 'bytesOut': 4050049925,
        'pktsIn': 9328608, 'pktsOut': 9328608
    },
    'ovs-system': {
        'bytesIn': 0, 'bytesOut': 0,
        'pktsIn': 0, 'pktsOut': 0
    },
    'tun_h1_d1_ds2': {
        'bytesIn': 6428, 'bytesOut': 282966348,
        'pktsIn': 72, 'pktsOut': 4421321
    },
    'tun_h1_d1_ds2_6': {
        'bytesIn': 4560, 'bytesOut': 336212180,
        'pktsIn': 57, 'pktsOut': 4423836
    },
    'veth0a16a40': {
        'bytesIn': 108707320, 'bytesOut': 5317234031,
        'pktsIn': 1037360, 'pktsOut': 2397970
    },
}
_devs_by_type = {
    'bond': ['bond0'],
    'bond_slave': ['eno1', 'enp4s0f0'],
    'bridge': ['docker_gwbridge'],
    'bridge_slave': ['veth0a16a40'],
    'general_slave': ['eno1', 'enp4s0f0', 'veth0a16a40'],
    'lo': ['lo'],
    'ovs-br0': ['br0'],
    'ovs-system': ['ovs-system'],
    'phys': ['eno1', 'enp4s0f0', 'eth0'],
    'tunnel': ['tun_h1_d1_ds2', 'tun_h1_d1_ds2_6'],
    'vlan': ['bond0.10'],
}


class TestInterfaceStatistics(unittest.TestCase):
    _tests_dir = dirname(getfile(currentframe()))
    _scn_mock = join(_tests_dir, 'linux_network', 'sys', 'class', 'net')
    _temp_dir = join(_tests_dir, 'linux_network')

    @classmethod
    def setUpClass(self):
        tf = taropen(join(self._tests_dir, 'linux_network.tgz'))
        tf.extractall(path=self._temp_dir)
        InterfaceStatistics._scn = self._scn_mock

    @classmethod
    def tearDownClass(self):
        from shutil import rmtree
        rmtree(self._temp_dir, ignore_errors=True)

    def test_check_dir(self):
        ns = InterfaceStatistics()
        self.assertTrue(ns._check_dir('lo', 'statistics'))

    def test_check_name(self):
        ns = InterfaceStatistics()
        self.assertTrue(ns._check_name('lo', 'lo'))

    def test_check_symlink(self):
        ns = InterfaceStatistics()
        self.assertTrue(ns._check_symlink('lo', 'subsystem'))

    def test_check_type(self):
        ns = InterfaceStatistics()
        self.assertTrue(ns._check_type('lo', ("772", )))

    def test_check_uevent(self):
        ns = InterfaceStatistics()
        self.assertTrue(ns._check_uevent('lo', 'INTERFACE=lo'))

    def test_all_metrics(self):
        ns = InterfaceStatistics()
        ns.fill_metrics()
        self.assertEqual(ns.netdev_stat, _stat)

    def test_single_filter(self):
        _results = []
        for t in _devs_by_type:
            ns = InterfaceStatistics([t])
            ns.fill_metrics()
            # Devises properly filtered
            _results.append(_devs_by_type[t].sort() == list(ns.netdev_stat.keys()).sort())
            for d in _devs_by_type[t]:
                # Metrics properly readed
                _results.append(_stat[d] == ns.netdev_stat[d])
        self.assertTrue(False not in _results)

    def test_random_set(self):
        from random import choice, randint
        _devs = []
        _types = []
        _results = []
        for i in range(randint(1, len(_devs_by_type))):
            _new_type = choice(list(_devs_by_type.keys()))
            if _new_type not in _types:
                _types.append(_new_type)
        for t in _types:
            for d in _devs_by_type[t]:
                if d not in _devs:
                    _devs.append(d)
        ns = InterfaceStatistics(_types)
        ns.fill_metrics()
        _results.append(_devs.sort() == list(ns.netdev_stat.keys()).sort())
        for d in _devs:
            _results.append(_stat[d] == ns.netdev_stat[d])
        self.assertTrue(False not in _results)

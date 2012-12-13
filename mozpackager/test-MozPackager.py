import unittest
from MozPackager import MozPackager
import os
import datetime

test_build_mock_output="""'INFO: mock.py version 1.1.11 starting...
State Changed: init plugins
INFO: selinux disabled
State Changed: start
State Changed: lock buildroot
State Changed: clean
INFO: chroot (/var/lib/mock/epel-6-x86_64) unlocked and deleted
State Changed: unlock buildroot
State Changed: init
State Changed: lock buildroot
Mock Version: 1.1.11
INFO: Mock Version: 1.1.11
INFO: enabled root cache
State Changed: unpacking root cache
INFO: enabled yum cache
State Changed: cleaning yum metadata
INFO: enabled ccache
State Changed: running yum
State Changed: unlock buildroot
State Changed: end
'"""
class testMozPackager(unittest.TestCase):

    def setUp(self):
        self.os = 'RHEL'
        self.root = 'mozilla'
        self.version = '6'
        self.arch = 'x86_64'
        self.mp = MozPackager(self.os, self.version, self.arch, self.root)
        pass

    def test1_constructor(self):
        self.assertTrue(self.mp is not None)

    def test1_test_run_which(self):
        self.mp.build_mock()
        self.mp._run_which('bash')

        self.assertTrue(self.mp is not None)

    def test2_parse_build_status(self):
        status = self.mp._parse_build_status(test_build_mock_output)
        self.assertEqual(status, True)

    def test3_parse_build_status_bad(self):
        status = self.mp._parse_build_status('this\nis\nbad')
        self.assertEqual(status, False)

    def test4_install_packages(self):
        self.mp.build_mock()
        which_fpm = self.mp._run_which('fpm')
        self.assertEqual(
                which_fpm,
                '')
        self.mp._install_packages()
        which_fpm = self.mp._run_which('fpm')
        self.assertEqual(which_fpm, '/usr/bin/fpm')

        
if __name__ == '__main__':
    unittest.main()

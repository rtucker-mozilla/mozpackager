from test_utils import TestCase
from django.test import Client
from test_utils import RequestFactory
from test_utils import setup_test_environment
from django.core.urlresolvers import reverse
import os
from mozpackager.MozPackager import MozPackage
import models

setup_test_environment()


post_data = {
        'input_type': 'rpm',
        'arch_type': 'x86_64',
        'package_version': '1.0',
        'application_group': 'Applications/Internet',
        'install_package_name': 'dummy_package_name',
        'upload_package': 'dummy upload package text',
        'output_type': 'rpm',
        'rhel_version': '6',
        }
class TestMozPackage(TestCase):
    def setUp(self):
        self.upload_file_name = 'fibreutils-2.5-4.x86_64.rpm'
        self.post_data = post_data

    def testArchPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'arch_type': 'i386'})
        mp = MozPackage(r)
        self.assertEqual(mp.arch, 'i386')
        r = rf.post('/upload/', {'arch_type': 'x86_64'})
        mp = MozPackage(r)
        self.assertEqual(mp.arch, 'x86_64')

    def testOutputPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'output_type': 'deb'})
        mp = MozPackage(r)
        self.assertEqual(mp.output_type, 'deb')

    def testInputPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'input_type': 'tar-gz'})
        mp = MozPackage(r)
        self.assertEqual(mp.input_type, 'tar-gz')

    def testOSVersionPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'output_type': 'rpm'})
        mp = MozPackage(r)
        self.assertEqual(mp.output_type, 'rpm')
        self.assertEqual(mp.os, 'RHEL')

    def testPackageNamePost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'install_package_name': 'test-package-name'})
        mp = MozPackage(r)
        self.assertEqual(mp.install_package_name, 'test-package-name')

    def testPackageVersionPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'install_package_name': 'test-package-version'})
        mp = MozPackage(r)
        self.assertEqual(mp.install_package_name, 'test-package-version')

    def testPrefixDirPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'prefix_dir': 'test-prefix-dir'})
        mp = MozPackage(r)
        self.assertEqual(mp.prefix_dir, 'test-prefix-dir')

    def testApplicationGroupPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'application_group': 'test-application-group'})
        mp = MozPackage(r)
        self.assertEqual(mp.application_group, 'test-application-group')

    def testQueueGroupPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', self.post_data)
        mp = MozPackage(r)
        self.assertEqual(mp.queue, 'rhel-6-x86_64')

    def testRoutingKeyGroupPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', self.post_data)
        mp = MozPackage(r)
        self.assertEqual(mp.routing_key, 'rhel-6-x86_64.build')

    def testDependencyGroup(self):
        deps = ['testDep1', 'testDep2', 'testDep3']
        rf = RequestFactory()
        r = rf.post('/upload/', {'dependencies': deps})
        mp = MozPackage(r)
        self.assertEqual(len(mp.dependencies), 3)
        for i in range(0, len(deps) - 1):
            self.assertTrue(deps[i] in mp.dependencies)

    def testConflictsPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'conflicts': 'test-conflict-one'})
        mp = MozPackage(r)
        self.assertEqual(mp.conflicts, 'test-conflict-one')

    def testProvidesPost(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'provides': 'test-provides'})
        mp = MozPackage(r)
        self.assertEqual(mp.provides, 'test-provides')

    def testPackageURL(self):
        rf = RequestFactory()
        r = rf.post('/upload/', {'package_url': 'test-package_url'})
        mp = MozPackage(r)
        self.assertEqual(mp.package_url, 'test-package_url')

    def testUploadPackage(self):
        try:
            os.remove('/tmp/%s' % self.upload_file_name)
        except OSError:
            """
                The file does not exist, so it cannot be removed
            """
            pass
        self.assertEqual(os.path.exists(self.upload_file_name), False)
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.post_data['upload_package'] = open(cwd + '/fixtures/fibreutils-2.5-4.x86_64.rpm', 'rb')
        r = {}
        r['upload_package'] = open(cwd + '/fixtures/fibreutils-2.5-4.x86_64.rpm', 'rb')
        r['upload_package_file_name'] = 'fibreutils-2.5-4.x86_64.rpm'
        mp = MozPackage(r)
        self.assertEqual(mp.upload_package_file_name, self.upload_file_name)
        self.assertEqual(os.path.exists('/tmp/' + self.upload_file_name), True)
class RefactoredTestMozPackageFormCreate(TestCase):
    def setUp(self):
        self.post_data = {
                'arch_type': 'x86_64',
                'output_type': 'rpm',
                'rhel_version': '6',
                'input_type': 'python',
                'package': 'django-tastypie',
                'upload_package': None,
                'install_package_name': 'dummy_package_name',
                'install_package_name': 'django-tastypie',
                'package_version': '',
                'application_group': 'Applications/Internet',
                'dependency': ['depend1', 'depend2'],
                'conflicts': '',
                'provides': '',
                'package_url': '',
                'prefix_dir': '',
            }

    def tearDown(self):
        self.post_data = None

    def testCreatePackageFromPypiWithTwoDependencies(self):
        self.assertEqual(len(models.MozillaPackage.objects.all()), 0)
        c = Client()
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertEqual(len(models.MozillaPackage.objects.all()), 1)
        mp = models.MozillaPackage.objects.filter(package=self.post_data['package'])[0]
        self.assertEqual(mp.package, self.post_data['package'])
        self.assertEqual(mp.mozillapackagedependency_set.all()[0].name, self.post_data['dependency'][0])
        self.assertEqual(mp.mozillapackagedependency_set.all()[1].name, self.post_data['dependency'][1])

    def testCreatePackageFromPypiWithNoDependenciesBuildFile(self):
        models.MozillaPackage.objects.all().delete()
        self.assertEqual(len(models.MozillaPackage.objects.all()), 0)
        c = Client()
        """
            Clear out the dependency post object
        """
        del self.post_data['dependency']
        c.post('/en-US/create/', self.post_data, follow=True)
        self.assertEqual(len(models.MozillaPackage.objects.all()), 1)
        mp = models.MozillaPackage.objects.filter(package=self.post_data['package'])[0]
        self.assertEqual(mp.generate_build_string(), 'setarch x86_64 fpm -s python -t rpm django-tastypie')

    def testCreatePackageFromPypiWithTwoDependenciesBuildFile(self):
        models.MozillaPackage.objects.all().delete()
        self.assertEqual(len(models.MozillaPackage.objects.all()), 0)
        c = Client()
        c.post('/en-US/create/', self.post_data, follow=True)
        self.assertEqual(len(models.MozillaPackage.objects.all()), 1)
        mp = models.MozillaPackage.objects.filter(package=self.post_data['package'])[0]
        self.assertEqual(mp.generate_build_string(), 'setarch x86_64 fpm -s python -t rpm -d "depend1" -d "depend2" django-tastypie')

    def testRPMInputException(self):
        c = Client()
        del self.post_data['upload_package']
        self.post_data['input_type'] = 'rpm'
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertTrue('upload_package' in resp.context['form'].errors)
        self.assertEqual(resp.context['form'].errors['upload_package'][0], 'RPM input type requires an upload package')


class TestMozPackageForm(TestCase):
    def setUp(self):
        self.post_data = {
                'input_type': 'rpm',
                'arch_type': 'x86_64',
                'package_version': '1.0',
                'application_group': 'Applications/Internet',
                'install_package_name': 'dummy_package_name',
                'upload_package': 'dummy upload package text',
                'output_type': 'rpm',
                'rhel_version': '6',
                }


    def testPackageUploadFailure(self):
        c = Client()
        del self.post_data['upload_package']
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertTrue('upload_package' in resp.context['form'].errors)
        self.assertEqual(resp.context['form'].errors['upload_package'][0], 'RPM input type requires an upload package')

    def testPackageUploadFailure(self):
        c = Client()
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.post_data['upload_package'] = open(cwd + '/fixtures/fibreutils-2.5-4.x86_64.rpm', 'rb')
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertFalse('install_package_name' in resp.context['form'].errors)

    def testPackageNameRequiredNone(self):
        c = Client()
        del self.post_data['install_package_name']
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertTrue('install_package_name' in resp.context['form'].errors)
        self.assertEqual(resp.context['form'].errors['install_package_name'][0], 'Package Name Required')


    def testRhelVersionRequiredNone(self):
        c = Client()
        del self.post_data['rhel_version']
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertTrue('rhel_version' in resp.context['form'].errors)
        self.assertEqual(resp.context['form'].errors['rhel_version'][0], 'RHEL Version Required')


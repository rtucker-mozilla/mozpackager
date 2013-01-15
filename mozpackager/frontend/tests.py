from test_utils import TestCase
from django.test import Client
from test_utils import RequestFactory
from test_utils import setup_test_environment
from django.core.urlresolvers import reverse
import os
from mozpackager.MozPackager import MozPackage
import models
import json

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


class TestBuildSourceListAjax(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testURIExists(self):
        c = Client()
        mozilla_package_id = create_dummy_mozilla_package()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        self.assertEqual(resp.status_code, 200)

    def testSinglePythonSourceWithoutDeps(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',).save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], '')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')

    def testSinglePythonSourceWithSystemDep(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        dep = models.MozillaBuildSourceSystemDependency(
                mozilla_build_source = bs,
                name='systemdep = 1.1')
        dep.save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], 'systemdep = 1.1')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')

    def testSinglePythonSourceWithSystemDeps(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        dep = models.MozillaBuildSourceSystemDependency(
                mozilla_build_source = bs,
                name='systemdep = 1.1')
        dep.save()
        dep = models.MozillaBuildSourceSystemDependency(
                mozilla_build_source = bs,
                name='systemdep = 2.1')
        dep.save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], 'systemdep = 1.1, systemdep = 2.1')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')

    def testSinglePythonSourceWithPackageDep(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        dep = models.MozillaBuildSourcePackageDependency(
                mozilla_build_source = bs,
                name='systemdep = 1.1')
        dep.save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], 'systemdep = 1.1')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')

    def testSinglePythonSourceWithPackageDeps(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        dep = models.MozillaBuildSourcePackageDependency(
                mozilla_build_source = bs,
                name='systemdep = 1.1')
        dep.save()
        dep = models.MozillaBuildSourcePackageDependency(
                mozilla_build_source = bs,
                name='systemdep = 2.1')
        dep.save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], 'systemdep = 1.1, systemdep = 2.1')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')

    def testSinglePythonSourceWithSystemDeps(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',).save()

        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], '')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], '')
        self.assertEqual(resp_obj['status'], 'OK')
    def testMultiplePythonSourceWithoutDeps(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',).save()
        models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'foobar',
                build_type = 'python',).save()
        c = Client()
        resp = c.get('/en-US/get_build_sources/%s/' % mozilla_package_id, follow=True)
        resp_obj = json.loads(resp.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(len(resp_obj['sources']), 2)
        self.assertEqual(resp_obj['sources'][0]['build_source'], 'django-tastypie')
        self.assertEqual(resp_obj['sources'][0]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][0]['system_dependencies'], '')
        self.assertEqual(resp_obj['sources'][0]['package_dependencies'], '')
        self.assertEqual(resp_obj['sources'][1]['build_source'], 'foobar')
        self.assertEqual(resp_obj['sources'][1]['build_source_type'], 'python')
        self.assertEqual(resp_obj['sources'][1]['system_dependencies'], '')
        self.assertEqual(resp_obj['sources'][1]['package_dependencies'], '')

class TestAddBuildSource(TestCase):
    def setUp(self):
        self.uploaded_build_source_file_post_data = {
                'package_id': '1',
                'remote_package_name_input': '',
                'local_package_name_input': 'PackageName',
                'build_source': '1',
                'system_dependency[]': ['systemdep1 = 2.2', 'systemdep2 = 9.9'],
                'dependency[]': ['packagedep1 = 1.9', 'packagedep2 = 3.0'],
                }
        self.pypi_source_post_data = {
                'package_id': '1',
                'remote_package_name_input': 'django-tastypie',
                'local_package_name_input': '',
                'build_source': 'python',
                'system_dependency[]': ['systemdep1 = 2.2', 'systemdep2 = 9.9'],
                'dependency[]': ['packagedep1 = 1.9', 'packagedep2 = 3.0'],
                }

    def tearDown(self):
        self.post_data = None

    def testURIExists(self):
        c = Client()
        resp = c.get('/en-US/add_build_source/1/', follow=True)
        self.assertEqual(resp.status_code, 200)

    def testPYPIcreatebuildsourcewithdependencies(self):
        create_dummy_mozilla_package()
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 0)
        c = Client()
        resp = c.post('/en-US/add_build_source/1/', data=self.pypi_source_post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 1)
        build_source = models.MozillaBuildSource.objects.get(id=1)
        self.assertEqual(build_source.id, 1)
        self.assertEqual(build_source.remote_package_name, 'django-tastypie')
        self.assertEqual(build_source.build_type, 'python')
        self.assertEqual(len(build_source.mozillabuildsourcepackagedependency_set.all()), 2)
        self.assertEqual(len(build_source.mozillabuildsourcesystemdependency_set.all()), 2)

    def testcreatefromuploaddedbuildsourcewithdependencies(self):
        mozilla_package_id = create_dummy_mozilla_package()
        build_source_file_id = create_dummy_build_source_file(mozilla_package_id)
        self.uploaded_build_source_file_post_data['package_id'] = mozilla_package_id
        self.uploaded_build_source_file_post_data['build_source'] = build_source_file_id
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 0)
        c = Client()
        resp = c.post('/en-US/add_build_source/%s/' % mozilla_package_id, data=self.uploaded_build_source_file_post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 1)
        build_source = models.MozillaBuildSource.objects.all()[0]
        self.assertEqual(build_source.local_package_name, 'PackageName')
        self.assertEqual(len(build_source.mozillabuildsourcepackagedependency_set.all()), 2)
        self.assertEqual(len(build_source.mozillabuildsourcesystemdependency_set.all()), 2)

    def testPYPIcreatebuildsourcewithoutdependencies(self):
        """
            Remove the dependency objects
        """
        del self.pypi_source_post_data['system_dependency[]']
        del self.pypi_source_post_data['dependency[]']

        mozilla_package_id = create_dummy_mozilla_package()
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 0)
        c = Client()
        resp = c.post('/en-US/add_build_source/%s/' % mozilla_package_id, data=self.pypi_source_post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 1)
        build_source = models.MozillaBuildSource.objects.get(id=mozilla_package_id)
        self.assertEqual(build_source.id, mozilla_package_id)
        self.assertEqual(build_source.remote_package_name, 'django-tastypie')
        self.assertEqual(len(build_source.mozillabuildsourcepackagedependency_set.all()), 0)
        self.assertEqual(len(build_source.mozillabuildsourcesystemdependency_set.all()), 0)

def create_dummy_mozilla_package():
    mp = models.MozillaPackage()
    mp.name = 'TestPackage'
    mp.version = '1.1'
    mp.release = '1'
    mp.application_group = 'Development/Languages'
    mp.save()
    return mp.id


def create_dummy_build_source_file(mozilla_package_id):
    mp = models.MozillaPackage.objects.get(id = mozilla_package_id)
    tmp = models.MozillaBuildSourceFile()
    tmp.mozilla_package = mp
    tmp.save()
    return tmp.id


class TestMozillaPackageForm(TestCase):
    def setUp(self):
        self.post_data = {
                'vendor': 'Mozilla',
                'name': 'Package_Name',
                'application_group': 'Development/Languages',
                'version': '1.1.1',
                'release': '1',
                'package_url': 'https://www.mozilla.com/Package_Name/',
            }

    def tearDown(self):
        self.post_data = None

    def testCreatePackageWithValidData(self):
        self.assertEqual(len(models.MozillaPackage.objects.all()), 0)
        c = Client()
        resp = c.post('/en-US/create/', self.post_data, follow=True)
        self.assertEqual(len(models.MozillaPackage.objects.all()), 1)
        mp = models.MozillaPackage.objects.filter(name=self.post_data['name'])[0]

        """
            Iterate over all keys to confirm what comes out
            of the database is what went in
        """
        for k in self.post_data.iterkeys():
            self.assertEqual(getattr(mp, k), self.post_data[k])

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


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

class TestMozillaPackageBuild(TestCase):
    def setUp(self):
        """
            Create some dummy objects to be used throughout the tests
        """
        self.mozilla_package_id = create_dummy_mozilla_package()
        self.mp = models.MozillaPackage.objects.get(id=self.mozilla_package_id)
        self.bs = models.MozillaBuildSource(mozilla_package=self.mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        self.bs.save()

    def tearDown(self):
        self.mp = None
        self.bs = None

    def create_package_build(self):
        package_build = models.MozillaPackageBuild()
        package_build.mozilla_package = self.mp
        package_build.arch_type = 'x86_64'
        package_build.build_source = self.bs
        package_build.save()
        return package_build

    def test1_packagebuildcreates(self):
        pb = self.create_package_build()
        self.assertEqual(pb.arch_type, 'x86_64')
        self.assertEqual(pb.build_source, self.bs)


    def test2_packagebuild_mozillapackageattributes(self):
        pb = self.create_package_build()
        self.assertEqual(pb.mozilla_package.name, u'TestPackage')
        self.assertEqual(pb.mozilla_package.version, u'1.1')
        self.assertEqual(pb.mozilla_package.release, u'1')
        self.assertEqual(pb.mozilla_package.application_group,
                u'Development/Languages')


class TestBuildFromBuildSource(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testURIExists(self):
        c = Client()
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        resp = c.get('/en-US/build_from_build_source/%s/' % bs.id, follow=True)
        self.assertEqual(resp.status_code, 200)

    def testBuildFromSourceCreatesModelObject(self):
        self.assertEqual(len(models.MozillaPackageBuild.objects.all()), 0)
        c = Client()
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        post_data = {
                'arch_type': 'x86_64',
                'build_type': 'rpm',
                'test': 'true',
                }
        resp = c.post('/en-US/build_from_build_source/%s/' % bs.id, data=post_data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(models.MozillaPackageBuild.objects.all()), 1)

class TestDeleteBuildSource(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testURIExists(self):
        c = Client()
        mozilla_package_id = create_dummy_mozilla_package()
        resp = c.get('/en-US/delete_build_source/%s/' % mozilla_package_id, follow=True)
        self.assertEqual(resp.status_code, 200)

    def testDeleteBadBuildSource(self):
        c = Client()
        resp = c.get('/en-US/delete_build_source/%s/' % 1, follow=True)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['status'], 'FAIL')
        self.assertEqual(obj['message'], 'Could not find Build Source with id: 1')


    def testDeleteGoodBuildSource(self):
        mozilla_package_id = create_dummy_mozilla_package()
        mp = models.MozillaPackage.objects.get(id=mozilla_package_id)
        bs = models.MozillaBuildSource(mozilla_package=mp,
                remote_package_name = 'django-tastypie',
                build_type = 'python',)
        bs.save()
        c = Client()
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 1)
        resp = c.get('/en-US/delete_build_source/%s/' % bs.id, follow=True)
        self.assertEqual(resp.status_code, 200)
        obj = json.loads(resp.content)
        self.assertEqual(obj['status'], 'OK')
        self.assertEqual(obj['message'], 'Build Source Deleted')
        self.assertEqual(len(models.MozillaBuildSource.objects.all()), 0)

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



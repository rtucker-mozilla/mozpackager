from celery.decorators import task
from celery.registry import tasks
from celery.task import Task
from mozpackager.MozPackager import MozPackager
from mozpackager.Mock import Mock
from mozpackager.settings import BUILD_DIR, BUILD_LOG_DIR
from mozpackager.frontend import models
import json
import re
import subprocess
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded 
import commonware.log
import logging
import commonware.log
log = commonware.log.getLogger('celery')
@task(name='build_package')
def build_package(package_build_id=None):
    """
        Placeholder variable should_kill_mock
        Since I have implemented a timeout exception block
        I've not had to manually kill the mock environment.
        Should it become necessary to manually kill the mock,
        the variable will be the flag
    """
    should_kill_mock = False
    build_package = models.MozillaPackageBuild.objects.get(id=package_build_id)
    log.debug('Mozilla Package: %s' % build_package.mozilla_package)
    mock_environment = Mock(build_package)
    mock_environment.build_mock()
    mock_environment.install_packages()
    mock_environment.install_build_file()
    mock_environment.copyin_source_file()
    """
        Here we're copying in a new version of file.rb
        Pretty hacky, but works in the interim until
        the upstream version gets patched to function
        on ruby < 1.9
        On line 187 of build_scripts/file.rb I have commented out
        #buffer.force_encoding("BINARY") 
        force_encoding is new in Ruby 1.9
    """
    mock_environment.patch_arr_pm()
    """
        Set successful_build to false,
        only copy out the built package if
        this is true
    """
    successful_build = False
    build_status = 'Failed'
    try:
        mock_environment.compile_package()
        successful_build = True
    except TimeLimitExceeded:
        should_kill_mock = True
        print "TimeLimitExceeded Caught"
    except SoftTimeLimitExceeded:
        should_kill_mock = True
        print "SoftTimeLimitExceeded Caught"
    """
        Always capture and save the error_log
    """
    error_log = mock_environment.error_log
    build_package.add_log('ERROR', error_log)
    if successful_build:
        build_log = mock_environment.build_log
        path = mock_environment.build_path.lstrip('/')
        log.debug('Task: build_package. Path is %s' % path)
        if path != '' and path is not None:
            build_package.add_log('INFO', 'Built File %s' % path)
            build_status = 'Completed'
            build_package.add_log('INFO', build_log)
            mock_environment.copyout_built_package(path, BUILD_DIR)
        else:
            build_status = 'Failed'

        build_package.add_log('INFO', 'Build %s' % build_status)
        build_package.build_status = build_status
        build_package.build_package_name = path

    build_package.save()


@task(name='build_mock_environment')
def build_mock_environment(moz_package=None, task_id=None):
    should_kill_mock = False
    mp = MozPackager(moz_package)
    mp.build_mock()
    try:
        message, path, status = mp.build_package(source=moz_package.input_type,
                destination=moz_package.output_type,
                upload_package=moz_package.upload_package_file_name,
                package=moz_package.install_package_name,
                version=moz_package.package_version,
                dependencies=moz_package.dependencies,
                )
    except TimeLimitExceeded:
        should_kill_mock = True
        print "TimeLimitExceeded Caught"
    except SoftTimeLimitExceeded:
        should_kill_mock = True
        print "SoftTimeLimitExceeded Caught"

    if should_kill_mock:
        try:
            print "Exception caught"
        except OSError:
            """
                There is no mock to kill
            """
            pass
    try:
        print "Copying out log"
        mp.copyout('/tmp/log', '%s/%s' % (BUILD_LOG_DIR, moz_package.install_package_name))
        output_log = open('%s/%s' % (BUILD_LOG_DIR, moz_package.install_package_name), 'r').read()
    except Exception, e:
        output_log = ''
        print "Exception on copying out /tmp/log"
        print "%s" % (e)


    try:
        print "Copying out errors"
        mp.copyout('/tmp/errors', '%s/%s_errors' % (BUILD_LOG_DIR, moz_package.install_package_name))
        error_log = open('%s/%s_errors' % (BUILD_LOG_DIR, moz_package.install_package_name), 'r').read()
    except:
        error_log = ''
        print "Exception on copying out /tmp/errors"
    path = ''
    for line in output_log.split("\n"):
        try:
            obj = json.loads(line)
            if 'path' in obj:
                path = obj['path']
                path = re.sub('[/ ]', '', path)
        except ValueError:
            pass
    if path == '':
        build_status = 'Failed'
    else:
        build_status = 'Completed'

        mp.copyout(path, BUILD_DIR)

    package_model = models.MozillaPackage.objects.get(celery_id = task_id)
    if path != '':
        package_model.add_log('INFO', 'Mock Path %s' % path)
    package_model.celery_id = ''
    package_model.build_package_name = path
    package_model.build_status = build_status
    package_model.save()
    package_model.add_log('INFO', 'Build Completed')
    package_model.add_log('ERROR', error_log)
    if build_status == 'Completed':
        package_model.add_log('INFO', output_log)

tasks.register(build_mock_environment)
tasks.register(build_package)

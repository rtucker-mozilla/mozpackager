from celery.decorators import task
from celery.registry import tasks
from celery.task import Task
from mozpackager.MozPackager import MozPackager
from mozpackager.settings import BUILD_DIR
from mozpackager.frontend import models
import json
import re
import subprocess
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded 

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
        mp.copyout('/tmp/log', '/tmp/log')
        output_log = open('/tmp/log', 'r').read()
    except:
        output_log = ''
        print "Exception on copying out /tmp/log"


    try:
        mp.copyout('/tmp/errors', '/tmp/errors')
        error_log = open('/tmp/errors', 'r').read()
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
    """

    if message and path:
        mp.copyout(path, BUILD_DIR)
        mp.copyout('/tmp/log', '/tmp/')
        mp.copyout('/tmp/error', '/tmp/')
        package_model = models.MozillaPackage.objects.get(celery_id = task_id)

        ## Going to remove the celery id here, just so that we don't have
        ## to worry about ever getting a duplicate

    else:
        print "did not build"
    """

tasks.register(build_mock_environment)

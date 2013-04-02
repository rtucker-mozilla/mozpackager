#!/usr/bin/python
import subprocess
import os
import json
import sys

import manage

from mozpackager.settings import BUILD_SCRIPTS, BUILD_DIR
import mozpackager.frontend.models as models
SIGN_SCRIPT = 'sign_package.sh'
all_unsigned_packages = models.MozillaPackageBuild.objects.filter(
        is_signed=False,
        build_status='Completed',
        )
for unsigned_package in all_unsigned_packages:
    if unsigned_package.build_package_name:
        sign_command = os.path.join(BUILD_SCRIPTS, SIGN_SCRIPT)
        full_source_build_file = os.path.join(BUILD_DIR,
                unsigned_package.build_package_name)
        sign_command_list = [
                sign_command,
                full_source_build_file,
                ]
        p = subprocess.Popen(sign_command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)                                                                                                                                                                   
        output, errors = p.communicate()
        try:
            resp = json.loads(output.split("=====")[1])
            unsigned_package.add_log(
                    'SIGNING',
                    "STATUS: %s\n%s" % (resp['success'], resp['message'])
                    )
            if resp['success'] == 'OK':
                unsigned_package.is_signed = True
                unsigned_package.save()
        except:
            unsigned_package.add_log(
                    'SIGNING',
                    "STATUS: FAILURE\n Unable to parse json response"
                    )
sys.exit(0)

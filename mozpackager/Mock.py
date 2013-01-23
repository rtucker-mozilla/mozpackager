import subprocess
from mozpackager.settings import BUILD_DIR, BUILD_LOG_DIR
import json
class Mock:
    root = None
    mock = '/usr/bin/mock'
    _build_log_text = None
    _error_log_text = None


    def __init__(self, build_package):

        """
            Perhaps pull these dynamically at some point
            I've not seen this as necessary. Cross compilation
            has worked just fine when building on x86_64
        """

        self.arch = 'x86_64'
        self.root = 'mozilla-6-x86_64'
        self.build_package = build_package
        self.mozpackage = build_package.mozilla_package
        self.build_source = build_package.build_source
        self.required_install_packages = [
                'zeroinstall-injector',
                'ruby-devel',
                'python-devel',
                'rubygems',
                'python-setuptools',
                'rubygem-fpm',
                ]

    def build_mock(self, root=None, arch=None):
        """
            Builds a mock based environment
            example usage:
            /usr/bin/mock --root=mozilla-6-x86_64 --arch=x86_64 --init
        """

        scrub_mock = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--scrub=all']
        output, errors = self._run_command(scrub_mock)

        init_mock = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--init']
        output, errors = self._run_command(init_mock)
        print output, errors
        """
            status = self._parse_build_status(errors)
            Do something with status.
            Not sure if it's even useful at this point
        """

    def install_build_file(self):
        build_file_content = self.build_package.generate_build_file_content()
        fh = open('/tmp/build_package.sh', 'w')
        fh.write(build_file_content)
        fh.close()
        output, errors = self._copyin('/tmp/build_package.sh', '/')
        chmod_build_file = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--shell',
                'chmod 755 /build_package.sh',
                
                ]
        output, errors = self._run_command(chmod_build_file)
        print output, errors

    def _copyin(self, path, destination='/tmp/'):
        cmd = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--copyin',
                path,
                destination
                ]
        output, errors = self._run_command(cmd)
        return output, errors

    @property
    def build_log(self):
        """
            Cat the /tmp/log file
            Store in the class variable _build_log_text This content won't 
            change, so we'll use self._build_log_text as a cache
        """
        if not self._build_log_text:
            self._build_log_text = self._cat('/tmp/log')
        return self._build_log_text

    @property
    def error_log(self):
        """
            Cat the /tmp/error file
            Store in the class variable _error_log_text This content won't 
            change, so we'll use self._error_log_text as a cache
        """
        if not self._error_log_text:
            self._error_log_text = self._cat('/tmp/errors')
        return self._error_log_text

    @property
    def build_path(self):
        build_log = self.build_log
        path = None
        for line in build_log.split("\n"):
            try:
                obj = json.loads(line)
                path = obj['path']
            except:
                pass
        return path

    @property
    def build_message(self):
        build_log = self.build_log
        message = None
        for line in build_log.split("\n"):
            try:
                obj = json.loads(line)
                message = obj['message']
            except:
                pass
        return message

    def _cat(self, path):
        cmd = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--shell',
                'cat %s' % path,
                ]
        output, errors = self._run_command(cmd)
        return output

    def copyout_built_package(self, path, destination):
        self._copyout(path, destination)

    def patch_arr_pm(self):
        """
            Here we're copying in a new version of file.rb
            Pretty hacky, but works in the interim until
            the upstream version gets patched to function
            on ruby < 1.9
        """
        self._copyin('build_scripts/file.rb',
            '/usr/lib/ruby/gems/1.8/gems/arr-pm-0.0.7/lib/arr-pm/file.rb')
        self._copyin('build_scripts/rpm.rb',
            '/usr/lib/ruby/gems/1.8/gems/fpm-0.4.24/lib/fpm/package/rpm.rb')

    def copyin_source_file(self):
        upload_file = self.build_source.build_source_file
        if upload_file and upload_file != '':
            self._copyin('/tmp/%s' % upload_file, '/')

    def _copyout(self, path, destination='/tmp/'):
        cmd = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--copyout',
                path,
                destination
                ]
        output, errors = self._run_command(cmd)
        return output, errors

    def copyout_log(self):
        try:
            print "Copying out log"
            self._copyout('/tmp/log', '%s/%s' % (BUILD_LOG_DIR, self.mozpackage.install_package_name))
            output_log = open('%s/%s' % (BUILD_LOG_DIR, self.mozpackage.install_package_name), 'r').read()
        except Exception, e:
            output_log = ''
            print "Exception on copying out /tmp/log"
            print "%s" % (e)
        return output_log

    def copyout_error(self):
        try:
            print "Copying out error"
            self._copyout('/tmp/errors', '%s/%s_error' % (BUILD_LOG_DIR, self.mozpackage.install_package_name))
            output_log = open('%s/%s_error' % (BUILD_LOG_DIR, self.mozpackage.install_package_name), 'r').read()

        except Exception, e:
            output_log = ''
            print "Exception on copying out /tmp/error"
            print "%s" % (e)
        return output_log

    def install_packages(self, additional_packages = []):
        if len(self.build_source.mozillabuildsourcesystemdependency_set.all()) > 0:
            for dep in self.build_source.mozillabuildsourcesystemdependency_set.all():
                additional_packages.append(dep.name)
        else:
            additional_packages = []
        self._install_packages(self.required_install_packages + additional_packages)

    def compile_package(self):
        """
            He we'll copy in the file that will actually build the package
        """
        build_package = [
                self.mock,
                '--root=%s' % self.root,
                '--arch=%s' % self.arch,
                '--shell',
                '/build_package.sh',
                
                ]
        output, errors = self._run_command(build_package)

    def _install_packages(self, package_list):
        """
            package_list is just for testing
        """
        installed_count = 0
        for package in package_list:
            install = [
                        self.mock,
                        '-q',
                        '--root=%s' % self.root,
                        '--arch=%s' % self.arch,
                        '--install',
                        '%s' % package
                    ]
            """
                Lots of useless debugging
                @TODO: Remove
            """
            print "Installing Package %s" % package
            output, errors = self._run_command(install)
            print output, errors
            installed_count += 1
        """
            Lots of useless debugging
            @TODO: Remove
        """
        print output
        print errors

    def _run_command(self, command):
        p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                )
        output, errors = p.communicate()
        return output, errors

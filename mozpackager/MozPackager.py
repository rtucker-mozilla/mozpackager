import subprocess
from settings.local import BUILD_SCRIPTS
class MozPackage(object):
    """
        MozPackage is essentially just a class to encapsulate a request into a
        an object for the MozPackager.
    """
    arch = None
    output_type = None
    input_type = None
    os = None
    rhel_version = None
    deb_version = None
    install_package_name = None
    package_version = None
    prefix_dir = None
    application_group = None
    dependencies = []
    conflicts = None
    provides = None
    package_url = None
    upload_package = None
    upload_file_name = None
    queue = None
    routing_key = None
    version = None
    root = None
    root_prefix = 'mozilla'

    def __init__(self, request_dict):
        self.arch = request_dict.get('arch_type', None)
        self.output_type = request_dict.get('output_type', None)
        self.install_package_name = request_dict.get('install_package_name', None)
        self.package_version = request_dict.get('package_version', None)
        self.prefix_dir = request_dict.get('prefix_dir', None)
        self.application_group = request_dict.get('application_group', None)
        import pdb; pdb.set_trace()
        self.dependencies = request_dict.getlist('dependencies', None)
        print "Dependencies from request: " % self.dependencies
        self.conflicts = request_dict.get('conflicts', None)
        self.provides = request_dict.get('provides', None)
        self.package_url = request_dict.get('package_url', None)
        #self.upload_package = request.FILES.get('upload_package', None)
        self.input_type = request_dict.get('input_type', None)
        self.rhel_version = request_dict.get('rhel_version', None)
        self.upload_package_file_name = None
        if self.output_type == 'rpm':
            self.os = 'RHEL'
            self.version = self.rhel_version
        else:
            self.os = 'DEB'
            self.version = self.deb_version

    
        if self.os == 'RHEL':
            self.queue = 'rhel-%s-%s' % (self.version, self.arch)
            self.routing_key = '%s.build' % (self.queue)
            self.root = '%s-%s-%s' % (self.root_prefix,
                    self.version,
                    self.arch)

        if self.os == 'DEB':
            self.queue = 'deb-%s' % (self.arch)
            self.version = 6
            self.routing_key = '%s.build' % (self.queue)
            self.root = '%s-6-x86_64' % (self.root_prefix,)

    def __repr__(self):
        return '<MozPackage %s>' % (self.install_package_name)

    #def __getstate__(self):
    #    return self



    @property
    def package_name(self):
        return "%s-%s.%s.%s" % (
                self.install_package_name,
                self.version,
                self.arch,
                self.output_type
                )

class MozPackager:
    root = None
    arch = None
    os = None
    version = None
    mock = '/usr/bin/mock'
    required_install_packages = [
            'zeroinstall-injector',
            'ruby-devel',
            'python-devel',
            'rubygems',
            'python-setuptools',
            'rubygem-fpm',
            ]

    def __init__(self, mozpackage):

        self.os = mozpackage.os
        self.arch = mozpackage.arch
        self.build_arch = self.arch
        self.root = mozpackage.root
        #self.config = 'mozilla-%s-%s' % (mozpackage.version, mozpackage.arch)
        self.config = 'mozilla-6-x86_64'
        print "self.config is: %s" % self.config
        self.clean()

    def build_mock(self, root=None, arch=None):
        """
            Builds a mock based environment
            example usage:
            /usr/bin/mock --root=mozilla-6-x86_64 --arch=x86_64 --init
        """

        if root:
            self.root = root

        if arch:
            self.arch = arch

        self.arch = 'x86_64'

        #clean_mock = [
        #        self.mock,
        #        '--root=%s' % self.config,
        #        '--arch=%s' % self.arch,
        #        '--clean']
        #output, errors = self.run_command(clean_mock)

        scrub_mock = [
                self.mock,
                '--root=%s' % self.config,
                '--arch=%s' % self.arch,
                '--scrub=all']
        output, errors = self.run_command(scrub_mock)

        init_mock = [
                self.mock,
                '--root=%s' % self.config,
                '--arch=%s' % self.arch,
                '--init']
        output, errors = self.run_command(init_mock)
        status = self._parse_build_status(errors)
        """
            Check response of status. If true then we built
            the mock environment successfully
        """

        if status:
            """
                Now that we've successfully built the mock
                lets install our packages
            """
            self._install_packages(self.required_install_packages)
            init_mock = [
                    self.mock,
                    '--root=%s' % self.config,
                    '--arch=%s' % self.arch,
                    '--copyin',
                    '%s/build_package.sh' % BUILD_SCRIPTS,
                    '/'
                    
                    ]
            output, errors = self.run_command(init_mock)

    def execute_mock_cmd(self, cmd):
        print cmd
        cmd = [
                self.mock,
                '--root=%s' % self.config,
                '--arch=%s' % self.arch,
                '--shell',
                '%s' % (cmd),
                ]
        output, errors = self.run_command(cmd)
        return output, errors

    def build_package(self, source='python', destination='rpm', package=None,
            upload_package=None, version=None, task_id=None, dependencies=[]):
        """
            Builds the package inside of the mock environemtn
            Example CLI usage:
            /usr/bin/mock --root=mozilla-6-x86_64 --shell \
            'fpm -s <source> -t <destination> <package>'
        """
        import json
        message = None
        path = None
        status = 'Completed'
        #self.execute_mock_cmd('setarch %s' % self.arch)
        #self.execute_mock_cmd('setarch i386s')
        if version and version != '':
            version_string = ' -v %s ' % version
        else:
            version_string = ''

        dependency_string = ""
        if len(dependencies) > 0:
            for dependency in dependency_string:
                dependency_string = ' -d "%s" %s' % (dependency.name, dependency_string)

        print "Dependency String: %s" % dependency_string

        if package and not upload_package:
            cmd = '/build_package.sh setarch %s fpm -s %s -t %s -n %s %s %s %s' % (
                    self.build_arch,
                    source,
                    destination,
                    package,
                    version_string,
                    dependency_string,
                    package)
            output, errors = self.execute_mock_cmd(cmd)
            merged = output + errors
            for line in merged.split('\n'):
                try:
                    obj = json.loads(line)
                    message = obj['message']
                    path = obj['path']
                except:
                    pass
            if not message:
                status = 'Failed'
                path = ''
                message = 'Build Failed'

        if upload_package:
            cmd = [
                    self.mock,
                    '--root=%s' % self.config,
                    '--arch=%s' % self.arch,
                    '--copyin',
                    '/tmp/%s' % upload_package,
                    '/tmp/'
                    ]
            output, errors = self.run_command(cmd)
            if source == 'tar-gz':
                cmd = [
                        self.mock,
                        '--root=%s' % self.config,
                        '--arch=%s' % self.arch,
                        '--shell',
                        'mkdir /tmp/build',
                        ]
                output, errors = self.run_command(cmd)
                cmd = [
                        self.mock,
                        '--root=%s' % self.config,
                        '--arch=%s' % self.arch,
                        '--shell',
                        '/bin/tar zxf /tmp/%s -C /tmp/build/' % upload_package,
                        ]
                print cmd
                output, errors = self.run_command(cmd)
                print output
                cmd = [
                        self.mock,
                        '--root=%s' % self.config,
                        '--arch=%s' % self.arch,
                        '--shell',
                        '/build_package.sh setarch %s fpm -s dir -t %s -n package_test -v 1.0 -C /tmp/build ./' % (self.build_arch, destination),
                        ]
                print cmd
                output, errors = self.run_command(cmd)
                print output, errors
            if source == 'rpm':
                cmd = [
                        self.mock,
                        '--root=%s' % self.config,
                        '--arch=%s' % self.arch,
                        '--shell',
                        '/build_package.sh "setarch %s fpm -s rpm -t %s /tmp/%s"' % (self.build_arch, destination, upload_package),
                        ]
                print cmd
                output, errors = self.run_command(cmd)
                merged = output + errors
                for line in merged.split('\n'):
                    try:
                        obj = json.loads(line)
                        message = obj['message']
                        path = obj['path']
                        print path
                    except:
                        pass
            
        return message, path, status

    def copyout(self, path, destination='/tmp/'):
        cmd = [
                self.mock,
                '--root=%s' % self.config,
                '--arch=%s' % self.arch,
                '--copyout',
                path,
                destination
                ]
        output, errors = self.run_command(cmd)


    def _run_which(self, the_which):
        cmd = [
                self.mock,
                '-q',
                '--root=%s' % self.config,
                '--arch=%s' % self.arch,
                '--shell',
                'which %s' % the_which
                ]
        output, errors = self.run_command(cmd)
        return output.strip()

    def _parse_build_status(self, input_text):
        for l in input_text.split('\n'):
            print l
        return 'State Changed: end'  or 'Finish: run' in [l for l in input_text.split('\n')]

    def _install_packages(self, package_list = None):
        """
            package_list is just for testing
        """
        if not package_list:
            package_list = self.required_install_packages
        installed_count = 0
        for package in package_list:
            install = [
                        self.mock,
                        '-q',
                        '--root=%s' % self.config,
                        '--arch=%s' % self.arch,
                        '--install',
                        '%s' % package
                    ]
            print "Installing Package %s" % package
            output, errors = self.run_command(install)
            print output, errors
            installed_count += 1
        #install = [
        #            self.mock,
        #            '-q',
        #            '--root=%s' % self.config,
        #            '--arch=%s' % self.arch,
        #            '--shell',
        #            'gem install fpm',
        #        ]
        #output, errors = self.run_command(install)
        print output
        print errors
            #import pdb; pdb.set_trace()

    def clean(self):
            clean = [
                    self.mock,
                    '-q',
                    '--root=%s' % self.config,
                    '--arch=%s' % self.arch,
                    '--clean',
                ]
            output, errors = self.run_command(clean)



    def run_command(self, command):
        p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                )
        output, errors = p.communicate()
        return output, errors


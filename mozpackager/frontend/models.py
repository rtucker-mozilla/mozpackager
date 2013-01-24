from django.db import models
from django.db.models.query import QuerySet
import datetime
import re
from mozpackager.settings import MEDIA_URL
"""
    build_file_template will be the script
    that gets copied into the mock environment
    this will ultimately be what builds the package
    Getting the output logs out requires this to be
    the case unfortunately
"""
build_file_template = """#!/bin/bash
rm -rf /tmp/build
mkdir /tmp/build
%s 2> /tmp/errors 1> /tmp/log
"""
class MozillaBuildSourceFile(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', blank=False, null=False)
    source_file = models.FileField(upload_to='uploads/')
    input_type = models.CharField(max_length=128, default='')

    class Meta:
        db_table = 'mozilla_package_source_file'

    def get_absolute_url(self):
        return '%s%s' % (MEDIA_URL, self.source_file)

    def save(self, *args, **kwargs):
        super(MozillaBuildSourceFile, self).save(*args, **kwargs)


class MozillaBuildSource(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', blank=False, null=False)
    remote_package_name = models.CharField(max_length=128, blank=True, null=True)
    local_package_name = models.CharField(max_length=128, blank=True, null=True)
    build_source_file = models.ForeignKey('MozillaBuildSourceFile', blank=True, null=True)
    build_type = models.CharField(max_length=128, default='')

    def get_build_url(self):
        return '/en-US/build_source_build/%s/' % self.id

    def get_delete_url(self):
        return '/en-US/build_source_delete/%s/' % self.id

    @property
    def package_dependency_string(self):
        if len(self.mozillabuildsourcepackagedependency_set.all()) > 0:
            package_dependency_string = ", ".join([s.name for s in self.mozillabuildsourcepackagedependency_set.all()])
        else:
            package_dependency_string = ""
        return package_dependency_string

    @property
    def system_dependency_string(self):
        if len(self.mozillabuildsourcesystemdependency_set.all()) > 0:
            system_dependency_string = ", ".join([s.name for s in self.mozillabuildsourcesystemdependency_set.all()])
        else:
            system_dependency_string = ""
        return system_dependency_string

    class Meta:
        db_table = 'mozilla_build_source'

    def get_absolute_url(self):
        return '%s%s' % (MEDIA_URL, self.source_file)

    def save(self, *args, **kwargs):
        super(MozillaBuildSource, self).save(*args, **kwargs)

class MozillaBuildSourcePackageDependency(models.Model):
    mozilla_build_source = models.ForeignKey('MozillaBuildSource', null=False, blank=False)
    name = models.CharField(max_length=128)

    class Meta:
        db_table = 'mozilla_build_source_package_dependency'


class MozillaBuildSourceSystemDependency(models.Model):
    mozilla_build_source = models.ForeignKey('MozillaBuildSource', null=False, blank=False)
    name = models.CharField(max_length=128)

    class Meta:
        db_table = 'mozilla_build_source_system_dependency'

class MozillaPackage(models.Model):
    name = models.CharField(max_length=128)
    version = models.CharField(max_length=128)
    release = models.CharField(max_length=128)
    vendor = models.CharField(max_length=128, blank=True, null=True)
    package_url = models.CharField(max_length=128, blank=True, null=True)
    application_group = models.CharField(max_length=128)
    created_on = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'mozilla_package'
        unique_together = (
                'name',
                'version',

                )

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_on = datetime.datetime.now()
        self.updated_on = datetime.datetime.now()
        super(MozillaPackage, self).save(*args, **kwargs)


class MozillaPackageBuild(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', blank=False, null=False)
    build_source = models.ForeignKey('MozillaBuildSource', blank=False, null=False)
    arch_type = models.CharField(max_length=128)
    output_type = models.CharField(max_length=128)
    build_package_name = models.CharField(max_length=128, blank=True, null=True)
    build_status = models.CharField(max_length=128, blank=True, null=True)
    rhel_version = models.CharField(max_length=128)
    """
        package has the label Remote Package
    """
    package = models.CharField(max_length=128)
    created_on = models.DateTimeField(blank=True, null=True)
    completed_on = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    conflicts = models.CharField(max_length=128)
    provides = models.CharField(max_length=128)
    prefix_dir = models.CharField(max_length=128)
    celery_id = models.CharField(max_length=128, null=True, blank=True)
    search_fields = (
            'arch_type',
            'package'
        )

    @property
    def input_type(self):
        if self.build_source.build_type:
            self.build_source.build_type
        elif self.build_source.build_source_file.source_file:
            source_filename = str(self.build_source.build_source_file.source_file).replace('uploads/', '')
            if '.tar.gz' in source_filename:
                return 'tar-gz'
            elif '.rpm' in source_filename:
                return 'rpm'
            elif '.deb' in source_filename:
                return 'deb'
            elif '.zip' in source_filename:
                return 'zip'


    @property
    def package_version(self):
        return self.mozilla_package.version
    @property
    def upload_package_file_name(self):
        if self.build_source.build_source_file.source_file:
            return str(self.build_source.build_source_file.source_file).replace('uploads/', '')


    class Meta:
        db_table = 'mozilla_package_build'

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_on = datetime.datetime.now()
            self.build_status = 'Building'
        self.updated_on = datetime.datetime.now()
        super(MozillaPackageBuild, self).save(*args, **kwargs)

    def generate_build_string(self):
        """
            build_string will be our computed
            fpm command that builds the package
        """
        dependency_string = ""
        version_string = "-v %s" % self.package_version if self.package_version != '' else ""
        if self.build_source.mozillabuildsourcepackagedependency_set:
            for dep in self.build_source.mozillabuildsourcepackagedependency_set.all():
                dependency_string = "%s -d \"%s\"" % (dependency_string, dep.name)

        print self.input_type

        if self.input_type == 'python' or self.input_type == 'gem':
            build_string = "setarch %s fpm -s %s -t %s %s %s %s" % (
                    self.arch_type,
                    self.input_type,
                    self.output_type,
                    version_string,
                    dependency_string,
                    self.mozilla_package.name,
                    )
        elif self.input_type == 'rpm' or self.input_type =='deb':
            build_string = "setarch %s fpm -s %s -t %s %s %s %s" % (
                    self.arch_type,
                    'rpm',
                    self.output_type,
                    version_string,
                    dependency_string,
                    self.upload_package_file_name,
                    )
        elif self.input_type == 'tar-gz':
            build_string = 'mkdir /tmp/build;'
            build_string += '/bin/tar zxf /%s -C /tmp/build/;' % self.upload_package_file_name
            build_string += "setarch %s fpm -s dir -t %s %s %s -C /tmp/build -n \"%s\" ./" % (
                    self.arch_type,
                    self.output_type,
                    version_string,
                    dependency_string,
                    self.mozilla_package.name,
                    )
        else:
            print "Unknown input type %s" % self.input_type
        """
            Clean up the build string a bit to remove double spaces 
            that can get added if no version or dependencies
        """
        build_string = re.sub('\s+', ' ', build_string)
        print build_string
        return str(build_string)

    def generate_build_file_content(self):
        build_file_content = build_file_template % self.generate_build_string()
        return build_file_content

    def write_build_file(self):
        file_content = self.generate_build_file_content()
        return file_content

    def add_log(self, log_type, log_message):
        MozillaPackageLog(mozilla_package_build = self,
                log_type = log_type,
                log_message = log_message).save()


class MozillaPackageLog(models.Model):
    mozilla_package_build = models.ForeignKey('MozillaPackageBuild', null=False, blank=False)
    log_type = models.CharField(max_length=128)
    log_message = models.TextField()
    log_time = models.DateTimeField(blank = False, null=False, default=datetime.datetime.now)

    @property
    def log_message_to_html(self):
        """
            Here we want to take the log message and replace the
            newline characters with <br /> for html output
        """
        message_list = self.log_message.split("\n")
        return "<br />".join(message_list)

    class Meta:
        db_table = 'mozilla_package_log'



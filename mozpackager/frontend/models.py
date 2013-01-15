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
    input_type = models.CharField(max_length=128)

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
    build_type = models.CharField(max_length=128)

    class Meta:
        db_table = 'mozilla_build_source'

    def get_absolute_url(self):
        return '%s%s' % (MEDIA_URL, self.source_file)

    def save(self, *args, **kwargs):
        super(MozillaBuildSource, self).save(*args, **kwargs)

class MozillaPackageBuild(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', blank=False, null=False)
    arch_type = models.CharField(max_length=128)
    output_type = models.CharField(max_length=128)
    build_package_name = models.CharField(max_length=128, blank=True, null=True)
    build_status = models.CharField(max_length=128, blank=True, null=True)
    rhel_version = models.CharField(max_length=128)
    input_type = models.CharField(max_length=128)
    upload_package_file_name = models.CharField(max_length=255, blank=True, null=True)
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
    search_fields = (
            'arch_type',
            'package'
        )

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
        if self.mozillapackagedependency_set:
            for dep in self.mozillapackagedependency_set.all():
                dependency_string = "%s -d \"%s\"" % (dependency_string, dep.name)

        if self.input_type == 'python' or self.input_type == 'gem':
            build_string = "setarch %s fpm -s %s -t %s %s %s %s" % (
                    self.arch_type,
                    self.input_type,
                    self.output_type,
                    version_string,
                    dependency_string,
                    self.install_package_name,
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
                    self.install_package_name,
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


class MozillaPackageDependency(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackageBuild', null=False, blank=False)
    name = models.CharField(max_length=128)

    class Meta:
        db_table = 'mozilla_package_dependency'


class MozillaPackageSystemDependency(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackageBuild', null=False, blank=False)
    name = models.CharField(max_length=128)


    class Meta:
        db_table = 'mozilla_system_dependency'

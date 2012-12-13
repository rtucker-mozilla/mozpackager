from django.db import models
from django.db.models.query import QuerySet
import datetime

class MozillaPackage(models.Model):
    arch_type = models.CharField(max_length=128)
    output_type = models.CharField(max_length=128)
    build_package_name = models.CharField(max_length=128, blank=True, null=True)
    build_status = models.CharField(max_length=128, blank=True, null=True)
    rhel_version = models.CharField(max_length=128)
    input_type = models.CharField(max_length=128)
    package = models.CharField(max_length=128)
    prefix_dir = models.CharField(max_length=128)
    install_package_name = models.CharField(max_length=128)
    package_version = models.CharField(max_length=128)
    conflicts = models.CharField(max_length=128)
    provides = models.CharField(max_length=128)
    package_url = models.CharField(max_length=128)
    application_group = models.CharField(max_length=128)
    celery_id = models.CharField(max_length=128, blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    completed_on = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    search_fields = (
            'arch_type',
            'package'
        )

    class Meta:
        db_table = 'mozilla_package'

    def add_log(self, log_type, log_message):
        MozillaPackageLog(mozilla_package = self,
                log_type = log_type,
                log_message = log_message).save()

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_on = datetime.datetime.now()
            self.build_status = 'Building'
        self.updated_on = datetime.datetime.now()
        super(MozillaPackage, self).save(*args, **kwargs)

class MozillaPackageLog(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', null=False, blank=False)
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


class MozillaPackageDependency(models.Model):
    mozilla_package = models.ForeignKey('MozillaPackage', null=False, blank=False)
    name = models.CharField(max_length=128)

    class Meta:
        db_table = 'mozilla_package_dependency'

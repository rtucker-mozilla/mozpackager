from django import forms
import models
from tasks import build_mock_environment
from mozpackager.MozPackager import MozPackage
def handle_uploaded_file(f):
    with open('/tmp/%s' % f._get_name(), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return f._get_name()
application_groups = (
'Amusements/Games',
'Amusements/Graphics',
'Applications/Archiving',
'Applications/Communications',
'Applications/Databases',
'Applications/Editors',
'Applications/Emulators',
'Applications/Engineering',
'Applications/File',
'Applications/Internet',
'Applications/Multimedia',
'Applications/Productivity',
'Applications/Publishing',
'Applications/System',
'Applications/Text',
'Development/Debuggers',
'Development/Languages',
'Development/Libraries',
'Development/System',
'Development/Tools',
'Documentation',
'System Environment/Base',
'System Environment/Daemons',
'System Environment/Kernel',
'System Environment/Libraries',
'System Environment/Shells',
'User Interface/Desktops',
'User Interface/X',
'User Interface/X Hardware Support',
)
class PackageForm(forms.ModelForm):
    output_types = (
            ('rpm', 'RPM'),
            ('deb', 'DEB'),
            )
    rhel_versions = (
            ('6', '6'),
            ('5', '5'),
            )
    input_types = (
            ('python', 'pypi'),
            ('gem', 'gem'),
            ('rpm', 'rpm'),
            ('deb', 'deb'),
            ('tar-gz', '.tar.gz'),
            ('zip', '.zip'),
            )
    arch_types = (
            ('x86_64', 'x86_64'),
            ('i386', 'i386'),
            )
    arch_type = forms.ChoiceField(
            label='Architecture',
            choices=arch_types,
            required=True)
    output_type = forms.ChoiceField(
            choices=output_types,
            required=True)
    rhel_version = forms.ChoiceField(
            label='RHEL Version',
            choices=rhel_versions,
            required=False)
    input_type = forms.ChoiceField(
            label = 'Input Type',
            choices=input_types,
            required=True)
    package = forms.CharField(
            label = 'Remote Package Name',
            max_length=72,
            required=False)
    prefix_dir = forms.CharField(
            label = 'Prefix Directory',
            max_length=72,
            required=False)
    install_package_name = forms.CharField(
            label = 'Package Name',
            max_length=72,
            required=False)
    package_version = forms.CharField(
            label = 'Package Version',
            max_length=72,
            required=False)
    conflicts = forms.CharField(
            label = 'Conflicts',
            help_text = 'What does this package conflict with',
            max_length=72,
            required=False)
    provides = forms.CharField(
            label = 'Provides',
            help_text = 'What does this package provide',
            max_length=72,
            required=False)
    package_url = forms.CharField(
            label = 'Package Url',
            help_text = 'What is the url for this package',
            max_length=72,
            required=False)

    application_group = forms.ChoiceField(
            choices=zip(application_groups, application_groups),
            required=True)

    upload_package = forms.FileField(required=False)
    def save(self, *args, **kwargs):
        super(PackageForm, self).save(*args, **kwargs)



    def clean(self):
        require_version = False
        cleaned_data = super(PackageForm, self).clean()
        upload_package = cleaned_data.get('upload_package', None)
        output_type = cleaned_data.get('output_type', None)
        input_type = cleaned_data.get('input_type', None)
        package = cleaned_data.get('package', None)
        install_package_name = cleaned_data.get('install_package_name', None)
        package_version = cleaned_data.get('package_version', None)
        rhel_version = cleaned_data.get('rhel_version', None)

        if input_type == 'rpm' and not upload_package:
            self._errors['upload_package'] = self.error_class(['RPM input type requires an upload package'])
            del cleaned_data['upload_package']

        if not install_package_name and not package:
            self._errors['install_package_name'] = self.error_class(['Package Name Required'])
            del cleaned_data['install_package_name']
        elif not install_package_name and package:
            cleaned_data['install_package_name'] = package

        if not package_version and require_version:
            self._errors['package_version'] = self.error_class(['Package Version Required'])
            del cleaned_data['package_version']

        if not input_type:
            self._errors['input_type'] = self.error_class(['Remote Package input type requires an upload package'])
            del cleaned_data['input_type']

        if output_type == 'rpm' and not rhel_version:
            self._errors['rhel_version'] = self.error_class(['RHEL Version Required'])
            del cleaned_data['rhel_version']

        
        if upload_package and not cleaned_data['install_package_name']:
            self._errors['install_package_name'] = self.error_class(['Package Name Required'])
            del cleaned_data['upload_package']
        elif upload_package and cleaned_data['install_package_name']:
            cleaned_data['build_package_name'] = cleaned_data['install_package_name']
            cleaned_data['package'] = cleaned_data['install_package_name']
            handle_uploaded_file(upload_package)

        return cleaned_data
    
    class Meta:
        model = models.MozillaPackage

    def __init__(self, *args, **kwargs):
        super(PackageForm, self).__init__(*args, **kwargs)

    def process(self, moz_package, db_object):
        db_object.add_log('INFO', 'Build Started')
        if self.cleaned_data['upload_package']:
            moz_package.upload_package_file_name = self.cleaned_data['upload_package']._get_name()

        test = False
        if not test:
            result = build_mock_environment.apply_async(args=[],kwargs = { 'moz_package': moz_package},
                    queue=moz_package.queue,
                    routing_key=moz_package.routing_key)
            db_object.celery_id = result
            db_object.save()

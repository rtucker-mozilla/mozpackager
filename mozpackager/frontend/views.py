# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
import models
import forms
from mozpackager.MozPackager import MozPackage
from tasks import build_package
from mozpackager.settings import BUILD_DIR
from mozpackager.settings.local import README_PATH
from django.core.servers.basehttp import FileWrapper
import mimetypes
import os
from django.db.models import Q
import operator
import json
from django.views.decorators.csrf import csrf_exempt
import markdown2
import commonware.log
log = commonware.log.getLogger('playdoh')
#import logging
#log = logging.getLogger('mozpackager')

@csrf_exempt
def search(request):
    search = request.POST.get('search', None)
    packages = []
    if search:
        filters = [Q(**{"%s__icontains" % t: search})
                        for t in models.MozillaPackage.search_fields]
        packages = models.MozillaPackage.objects.filter(
                    reduce(operator.or_, filters)).order_by('-created_on')
    return render_to_response('search_results.html',
            { 
                'packages': packages
            },
            RequestContext(request) )

def detail(request, id):
    instance = get_object_or_404(models.MozillaPackage, id=id)
    try:
        dependencies = [n.name for n in instance.mozillapackagedependency_set.all()]
    except:
        dependencies= []
    try:
        system_dependencies = [n.name for n in instance.mozillapackagesystemdependency_set.all()]
    except:
        system_pendencies= []
    return render_to_response('package_detail.html',
            { 
                'dependencies': dependencies,
                'system_dependencies': system_dependencies,
                'package': instance },
            RequestContext(request) )

def get_build_sources(request, id):
    return_dict = {}
    try:
        mozilla_package = models.MozillaPackage.objects.get(id=id)
    except models.MozillaPackage.DoesNotExist:
        return_dict['status'] = 'FAIL'
        return_dict['message'] = 'Could not find Mozilla Package with id:%s' % id
        return HttpResponse(json.dumps(return_dict))
    return_dict['status'] = 'OK'
    return_dict['sources'] = []
    for source in mozilla_package.mozillabuildsource_set.all():
        tmp = {}
        tmp['id'] = source.id
        tmp['build_source_type'] = source.build_type
        tmp['build_source'] = source.remote_package_name
        tmp['system_dependencies'] = source.system_dependency_string
        tmp['package_dependencies'] = source.package_dependency_string
        tmp['remote_package_name'] = source.remote_package_name
        tmp['get_build_url'] = source.get_build_url()
        tmp['get_delete_url'] = source.get_delete_url()
        if source.build_source_file:
            tmp['build_source_file_name'] = str(source.build_source_file.source_file).replace("uploads/", "")
        else:
            tmp['build_source_file_name'] = ''
        return_dict['sources'].append(tmp)

    return HttpResponse(json.dumps(return_dict))

@csrf_exempt
def add_build_source(request, id):
    response_obj = {}
    response_obj['status'] = 'FAIL'
    try:
        mozilla_package = models.MozillaPackage.objects.get(id=id)
    except models.MozillaPackage.DoesNotExist:
        return HttpResponse('Could not find Mozilla Package with id:%s' % id)

    if request.method == 'POST':
        mozilla_build_source = models.MozillaBuildSource()
        mozilla_build_source.mozilla_package = mozilla_package
        mozilla_build_source.local_package_name = request.POST.get('local_package_name_input', None)
        mozilla_build_source.remote_package_name = request.POST.get('remote_package_name_input', None)
        build_source = request.POST.get('build_source', None)
        if build_source != 'gem' and build_source != 'python':
            build_source_file = models.MozillaBuildSourceFile.objects.get(id=request.POST.get('build_source'))
            mozilla_build_source.build_source_file = build_source_file
        else:
            mozilla_build_source.build_type = build_source
            mozilla_build_source.build_source_file = None
        mozilla_build_source.save()

        system_dependencies = request.POST.getlist('system_dependency[]', [])
        package_dependencies = request.POST.getlist('dependency[]', [])
        for p in system_dependencies:
            tmp = models.MozillaBuildSourceSystemDependency()
            tmp.mozilla_build_source = mozilla_build_source
            tmp.name = p
            tmp.save()

        for p in package_dependencies:
            tmp = models.MozillaBuildSourcePackageDependency()
            tmp.mozilla_build_source = mozilla_build_source
            tmp.name = p
            tmp.save()
        response_obj['status'] = 'OK'

    return HttpResponse(json.dumps(response_obj))

    #moz_package = get_object_or_404(models.MozillaPackage, id=id)


@csrf_exempt
def edit(request, id):
    instance = get_object_or_404(models.MozillaPackage, id=id)
    dependencies = []
    system_dependencies = []
    dependency_count = 0;
    system_dependency_count = 0;
    try:
        dependencies = [n.name for n in instance.mozillapackagedependency_set.all()]
    except:
        dependencies= []

    if request.method == "POST":
        #form = forms.PackageForm(request.POST, request.FILES, instance=instance)
        package_upload_form = forms.SourcePackageUploadForm(request.POST, request.FILES, prefix='package-upload')
        if package_upload_form.is_valid():
            cleaned_data = package_upload_form.clean()
            up = models.MozillaBuildSourceFile()
            up.mozilla_package = instance
            up.source_file = cleaned_data['source_file']
            up.input_type = cleaned_data['input_type']
            up.save()
            package_upload_form.save()

        #dependencies = request.POST.getlist('dependency')
        #if form.is_valid():
        #    mozilla_package = form.save()
        #    instance.mozillapackagedependency_set.all().delete()
        #    if dependencies:
        #        for dep in dependencies:
        #            if dep != '':
        #                models.MozillaPackageDependency(
        #                        mozilla_package = form.instance,
        #                        name = dep,
        #                        ).save()
        #    moz_package = MozPackage(request)
        #    form.process(moz_package)
        #    return HttpResponseRedirect(reverse('frontend.create'))
        #form = forms.PackageForm(request.POST, request.FILES)
    else:
        #form = forms.PackageForm(instance=instance)
        package_upload_form = forms.SourcePackageUploadForm(prefix='package-upload')

    return render_to_response('edit.html',
            { 
                #'form': form,
                'dependencies': dependencies,
                'package_upload_form': package_upload_form,
                'dependency_count': dependency_count,
                'system_dependencies': system_dependencies,
                'instance': instance,
                'system_dependency_count': system_dependency_count,
            },
            RequestContext(request) )
def querydict_to_dict(query_dict):
    request_dict = {}
    for k in query_dict.iterkeys():
        try:
            """
                Check to see if we've passed a list object
                through the request.POST object
                If so we want to make a list of it
            """
            request_dict[k] = query_dict.getlist(k)
        except AttributeError:
            """
                The request.POST[k] item is not a list
                set the dictionary object direct
            """
            request_dict[k] = query_dict[k]
    return request_dict

@csrf_exempt
def create(request):
    log.debug('Create Page Loaded')
    if request.method == "POST":
        log.debug('POST Received: %s' % request.POST)

        form = forms.MozillaPackageForm(request.POST, request.FILES)
        #import pdb; pdb.set_trace()
        if form.is_valid():
            form.save()
            mozilla_package = form.instance
            return HttpResponseRedirect(reverse('frontend.edit', kwargs={'id':form.instance.id}))
        form = forms.MozillaPackageForm(request.POST, request.FILES)
    else:
        form = forms.MozillaPackageForm()

    return render_to_response('create_package.html',
            { 'form': form,
              
              },
            RequestContext(request) )

@csrf_exempt
def create_orig(request):
    log.debug('Create Page Loaded')
    dependencies = []
    system_dependencies = []
    dependency_count = 0;
    system_dependency_count = 0;
    if request.method == "POST":
        log.debug('POST Received: %s' % request.POST)

        form = forms.PackageForm(request.POST, request.FILES)
        dependencies = request.POST.getlist('dependency')
        dependency_count = len(dependencies)
        system_dependencies = request.POST.getlist('system_dependency')
        system_dependency_count = len(system_dependencies)
        #import pdb; pdb.set_trace()
        if form.is_valid():
            form.save()
            mozilla_package = form.instance
            if dependencies:
                for dep in dependencies:
                    models.MozillaPackageDependency(
                            mozilla_package = mozilla_package,
                            name = dep,
                            ).save()
            if system_dependencies:
                for dep in system_dependencies:
                    models.MozillaPackageSystemDependency(
                            mozilla_package = mozilla_package,
                            name = dep,
                            ).save()
            #import pdb; pdb.set_trace()
            request_dict = querydict_to_dict(request.POST.copy())
            cleaned_data = form.cleaned_data
            if form.cleaned_data['upload_package']:
                mozilla_package.upload_package_file_name = form.cleaned_data['upload_package']._get_name()
                mozilla_package.save()
            result = build_package.apply_async(args=[],kwargs = { 'package_id': mozilla_package.id},
                    queue='rhel-6-x86_64',
                    routing_key='rhel-6-x86_64.build')
            mozilla_package.celery_id = result
            mozilla_package.save()
            #moz_package = MozPackage(request_dict)
            #form.process(moz_package, form.instance)
            return HttpResponseRedirect(reverse('frontend.list'))
        form = forms.PackageForm(request.POST, request.FILES)
    else:
        form = forms.PackageForm()

    return render_to_response('create_package.html',
            { 'form': form,
              'dependencies': dependencies,
              'dependency_count': dependency_count,
              'system_dependencies': system_dependencies,
              'system_dependency_count': system_dependency_count,
              
              },
            RequestContext(request) )
def list(request):
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    packages = models.MozillaPackage.objects.all().order_by('-created_on')
    paginator = Paginator(packages, 40)
    page = request.GET.get('page')
    try:
        packages = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        packages = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        packages = paginator.page(paginator.num_pages)
    return render_to_response('list.html',
            { 
                'packages': packages,
                'paginator': paginator,
            },
            RequestContext(request) )

def home(request):
    markup = markdown2.markdown_path(README_PATH)
    markup = fix_markup(markup)
    return render_to_response('home.html',
            { 
                'markup': markup,
            },
            RequestContext(request))
def fix_markup(markup):
    markup = markup.replace("{{{", "<pre>")
    markup = markup.replace("}}}", "</pre>")
    return markup

def serve_file(request, id):

    moz_package = get_object_or_404(models.MozillaPackage, id=id)
    filename = moz_package.build_package_name
    fullname = "%s/%s" % (BUILD_DIR, filename)
    try:
        f = file(fullname, "rb")
    except Exception, e:
        print e
        return page_not_found(request, template_name='404.html')
    try:
        wrapper = FileWrapper(f)
        response = HttpResponse(wrapper, mimetype=mimetypes.guess_type(filename)[0])
        response['Content-Length'] = os.path.getsize(fullname)
        response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response
    except Exception, e:
        return page_not_found(request, template_name='500.html')

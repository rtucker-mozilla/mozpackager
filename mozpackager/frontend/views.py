# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
import models
import forms
from mozpackager.MozPackager import MozPackage
from tasks import build_mock_environment
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

def search(request):
    search = request.GET.get('q', None)
    results = []
    if search:
        filters = [Q(**{"%s__icontains" % t: search})
                        for t in models.MozillaPackage.search_fields]
        packages = models.MozillaPackage.objects.filter(
                    reduce(operator.or_, filters))
        for p in packages:
            results.append({
                'name': p.package,
                'id': '/en-US/detail/%s/' % p.id,
                })
    return HttpResponse(json.dumps(results))

def detail(request, id):
    instance = get_object_or_404(models.MozillaPackage, id=id)
    try:
        dependencies = [n.name for n in instance.mozillapackagedependency_set.all()]
    except:
        dependencies= []
    return render_to_response('package_detail.html',
            { 
                'dependencies': dependencies,
                'package': instance },
            RequestContext(request) )
@csrf_exempt
def edit(request, id):
    instance = get_object_or_404(models.MozillaPackage, id=id)
    try:
        dependencies = [n.name for n in instance.mozillapackagedependency_set.all()]
    except:
        dependencies= []

    if request.method == "POST":
        form = forms.PackageForm(request.POST, request.FILES, instance=instance)
        dependencies = request.POST.getlist('dependency')
        if form.is_valid():
            mozilla_package = form.save()
            instance.mozillapackagedependency_set.all().delete()
            if dependencies:
                for dep in dependencies:
                    if dep != '':
                        models.MozillaPackageDependency(
                                mozilla_package = form.instance,
                                name = dep,
                                ).save()
            moz_package = MozPackage(request)
            form.process(moz_package)
            return HttpResponseRedirect(reverse('frontend.create'))
        form = forms.PackageForm(request.POST, request.FILES)
    else:
        form = forms.PackageForm(instance=instance)

    return render_to_response('create_package.html',
            { 'form': form, 'dependencies': dependencies},
            RequestContext(request) )
@csrf_exempt
def create(request):
    dependencies = []
    dependency_count = 0;
    if request.method == "POST":
        form = forms.PackageForm(request.POST, request.FILES)
        dependencies = request.POST.getlist('dependency')
        dependency_count = len(dependencies)
        if form.is_valid():
            mozilla_package = form.save()
            if dependencies:
                for dep in dependencies:
                    models.MozillaPackageDependency(
                            mozilla_package = form.instance,
                            name = dep,
                            ).save()
            request_dict = request.POST
            moz_package = MozPackage(request_dict)
            form.process(moz_package, form.instance)
            return HttpResponseRedirect(reverse('frontend.list'))
        form = forms.PackageForm(request.POST, request.FILES)
    else:
        form = forms.PackageForm()

    return render_to_response('create_package.html',
            { 'form': form,
              'dependencies': dependencies,
              'dependency_count': dependency_count,
              
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

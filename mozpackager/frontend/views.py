# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
import models
import forms
from tasks import add

def task_test(request):
    add.delay(1,1)
    return HttpResponse('ok')





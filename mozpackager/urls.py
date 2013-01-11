from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.simple import direct_to_template


from funfactory.monkeypatches import patch
patch()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    #(r'', include(urls)),
    #(r'', direct_to_template, {'template': 'index.html'}),
    #url(r'upload', 'mozpackager.frontend.views.upload', name='frontend.upload'),
    url(r'^$', 'mozpackager.frontend.views.home', name='frontend.home'),
    url(r'create', 'mozpackager.frontend.views.create', name='frontend.create'),
    url(r'edit/(?P<id>\d+)[/]', 'mozpackager.frontend.views.edit', name='frontend.edit'),
    url(r'detail/(?P<id>\d+)[/]', 'mozpackager.frontend.views.detail', name='frontend.detail'),
    url(r'download/(?P<id>\d+)[/]', 'mozpackager.frontend.views.serve_file', name='frontend.download'),
    url(r'list', 'mozpackager.frontend.views.list', name='frontend.list'),
    url(r'search', 'mozpackager.frontend.views.search', name='frontend.search'),
    
    # Generate a robots.txt
    (r'^robots\.txt$', 
        lambda r: HttpResponse(
            "User-agent: *\n%s: /" % 'Allow' if settings.ENGAGE_ROBOTS else 'Disallow' ,
            mimetype="text/plain"
        )
    )

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes':True}),

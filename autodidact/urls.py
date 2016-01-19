from django.conf.urls import include, url
from .views import *

urlpatterns = [
    url(r'^$', homepage, name='homepage'),
    url(r'^([^/]+)/$', course, name='course'),
    url(r'^([^/]+)/session/([0-9]+)/$', session, name='session'),
    url(r'^([^/]+)/session/([0-9]+)/assignment/([0-9]+)/$', assignment, name='assignment'),
]
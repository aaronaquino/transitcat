from django.conf.urls import url

from . import views

app_name = 'snapData'
urlpatterns = [
    url(r'^$', views.UploadOrLoadView.as_view(), name='index'),
    url(r'^upload/$', views.upload, name='upload'),
    url(r'^load/$', views.LoadView.as_view(), name='load'),
    url(r'^(?P<id>[0-9]+)/$', views.detail, name='detail'),
    url(r'^(?P<id>[0-9]+)/mergeGraphs$', views.mergeGraphs, name='mergeGraphs'),
    url(r'^(?P<id>[0-9]+)/updateFeeds$', views.updateFeeds, name='updateFeeds'),
    url(r'^(?P<id>[0-9]+)/map/$', views.map, name='map'),
    url(r'^(?P<id>[0-9]+)/map/(?P<stopid>[A-z0-9]+)/$', views.mapStop, name='mapStop'),
    url(r'^ajax/searchYelp/$', views.searchYelp, name='searchYelp'),
    url(r'^ajax/isochrone/$', views.isochrone, name='isochrone'),
    url(r'^ajax/criticality/$', views.criticality, name='criticality'),
]
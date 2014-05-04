#encoding=utf-8

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'goldencage.views',
    url(r'^apwcb/(?P<provider>\w+)/$', 'appwall_callback', name='wall_cb'),
    url(r'^alipaycb/$', 'alipay_callback', name='alipay_cb'),
    )

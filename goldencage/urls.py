# encoding=utf-8

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'goldencage.views',
    url(r'^apwcb/(?P<provider>\w+)/$', 'appwall_callback', name='wall_cb'),
    url(r'^alipaycb/$', 'alipay_callback', name='alipay_cb'),
    url(r'^alipaysign/$', 'alipay_sign', name='alipaysign'),
    url(r'^wechat/$', 'wechat', name='wechat'),
    url(r'^wechatpaypackage/$',
        'wechat_pay_gen_package', name='wechat_pay_gen_package'),
    url(r'^wechatcb/$',
        'wechat_pay_notify', name='wechat_pay_notify'),
    url(r'^wechatmpcb/$',
        'wechat_mp_pay_notify', name='wechat_mp_pay_notify'),
)

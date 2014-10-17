# encoding=utf-8

from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA

import base64
import hashlib
import urllib
import requests
import simplejson as json

from goldencage.models import AppWallLog
from goldencage.models import Charge
from goldencage import config
from goldencage.models import Coupon

from wechat.official import WxApplication, WxTextResponse, WxResponse

import logging
log = logging.getLogger(__name__)


def rsp(data=None):
    if data is None:
        data = {}
    ret = {'errcode': 0, 'errmsg': 'ok', 'data': data}
    ret = json.dumps(ret)
    return HttpResponse(ret)


def error_rsp(code, msg, data=None):
    if data is None:
        data = {}
    ret = {'errcode': code, 'errmsg': msg, 'data': data}
    ret = json.dumps(ret)
    return HttpResponse({'errcode': code, 'errmsg': msg, 'data': data})


waps_ips = ['219.234.85.238', '219.234.85.223',
            '219.234.85.211', '219.234.85.231',
            '127.0.0.1']


def waps_callback(request):
    ip = request.META.get("REMOTE_ADDR", None)

    if ip not in waps_ips and not request.GET.get('debug', None):
        return HttpResponseNotAllowed("incorrect IP address")
    wapslog = {}
    for key in request.GET.keys():
        wapslog[key] = request.GET[key]
    if AppWallLog.log(wapslog, provider='waps'):
        return HttpResponse(json.dumps(
            {"message": u"成功接收", "success": True}))
    else:
        return HttpResponse(json.dumps(
            {"message": u"无效数据", "success": False}))


def youmi_callback_adr(request):
    sign = request.GET.get('sig')
    if not sign:
        return HttpResponseForbidden("miss param 'sign'")

    keys = ['order', 'app', 'user', 'chn', 'ad', 'points']
    vals = [request.GET.get(k, '').encode('utf8').decode('utf8') for k in keys]
    vals.insert(0, settings.YOUMI_CALLBACK_SECRET_ADR)
    token = u'||'.join(vals)
    md5 = hashlib.md5()
    md5.update(token.encode('utf-8'))
    md5 = md5.hexdigest()
    _sign = md5[12:20]

    if sign != _sign:
        return HttpResponseForbidden("signature error")
    youmilog = {}
    for key in keys:
        youmilog[key] = request.GET[key]
    if AppWallLog.log(youmilog, provider='youmi_adr'):
        return HttpResponse('OK')
    else:
        return HttpResponseForbidden('already exist')

    return HttpResponseForbidden("Signature verification fail")


def youmi_callback_ios(request):
    sign = request.GET.get('sign')
    if not sign:
        return HttpResponseForbidden("miss param 'sign'")

    keys = request.GET.keys()
    keys.sort()

    src = ''.join(['%s=%s' %
                   (k, request.GET.get(k).encode('utf-8').decode('utf-8'))
                   for k in keys if k != 'sign'])
    src += settings.YOUMI_CALLBACK_SECRET
    md5 = hashlib.md5()
    md5.update(src.encode('utf-8'))
    _sign = md5.hexdigest()

    if sign != _sign:
        return HttpResponseForbidden("signature error")

    youmilog = {}
    for key in keys:
        youmilog[key] = request.GET[key]
    if AppWallLog.log(youmilog, provider='youmi_ios'):
        return HttpResponse('OK')
    else:
        return HttpResponseForbidden('already exist')

    return HttpResponseForbidden("Signature verification fail")


def dianjoy_callback_adr(request):
    token = request.GET.get('token')
    time_stamp = request.GET.get('time_stamp')
    md5 = hashlib.md5()
    md5.update(time_stamp + settings.GOLDENCAGE_DIANJOY_ANDROID_SECRET)
    sign = md5.hexdigest()
    if sign != token:
        return HttpResponseForbidden('token error')
    log = {}
    for key in request.GET.keys():
        log[key] = request.GET[key]
    if AppWallLog.log(log, provider='dianjoy_adr'):
        return HttpResponse('200')
    else:
        return HttpResponse('OK, But duplicate item')


def appwall_callback(request, provider):
    return {'waps': waps_callback,
            'youmi_ios': youmi_callback_ios,
            'youmi_adr': youmi_callback_adr,
            'dianjoy_adr': dianjoy_callback_adr,
            }[provider](request)

alipay_public_key = config.ALIPAY_PUBLIC_KEY


# 支付宝回调 ########

def verify_notify_id(notify_id):
    # 检查是否合法的notify_id, 检测该id是否已被成功处理过。

    url = 'https://mapi.alipay.com/gateway.do'
    params = {'service': 'notify_verify',
              'partner': settings.ALIPAY_PID,
              'notify_id': notify_id}
    log.info('start verify notify_id %s' % notify_id)
    try:
        rsp = requests.get(url, params=params, timeout=5)
    except:
        log.error('timeout verify notify_id %s' % notify_id)
        return False
    log.info('finish verify notifi_id %s' % notify_id)
    return rsp.status_code == 200 and rsp.text == 'true'


def verify_alipay_signature(sign_type, sign, params):
    if sign_type == 'RSA':
        return rsa_verify(params, sign)
    else:
        return True


def filter_para(paras):
    """过滤空值和签名"""
    for k, v in paras.items():
        if not v or k in ['sign', 'sign_type']:
            paras.pop(k)
    return paras


def create_link_string(paras, sort, encode):
    """对参数排序并拼接成query string的形式"""
    if sort:
        paras = sorted(paras.items(), key=lambda d: d[0])
    if encode:
        return urllib.urlencode(paras)
    else:
        if not isinstance(paras, list):
            paras = list(paras.items())
        ps = ''
        for p in paras:
            if ps:
                ps = '%s&%s=%s' % (ps, p[0], p[1])
            else:
                ps = '%s=%s' % (p[0], p[1])
        return ps


def rsa_verify(paras, sign):
    """对签名做rsa验证"""
    log.debug('init paras = %s' % paras)
    pub_key = RSA.importKey(config.ALIPAY_PUBLIC_KEY)
    paras = filter_para(paras)
    paras = create_link_string(paras, True, False)
    log.debug('type(paras) = %s paras = %s' % (type(paras), paras))
    verifier = PKCS1_v1_5.new(pub_key)
    data = SHA.new(paras.encode('utf-8'))
    return verifier.verify(data, base64.b64decode(sign))


@csrf_exempt
def alipay_callback(request):
    # 支付宝支付回调，先检查签名是否正确，再检查是否来自支付宝的请求。
    # 有效的回调，将更新用户的资产。
    keys = request.REQUEST.keys()
    data = {}
    for key in keys:
        data[key] = request.REQUEST[key]
    notify_id = data['notify_id']
    sign_type = data['sign_type']
    sign = data['sign']
    order_id = data['out_trade_no']

    log.info(u'alipay callback, order_id: %s , data: %s' % (order_id, data))

    nid = cache.get('ali_nid_' + hashlib.sha1(notify_id).hexdigest())
    if nid:
        log.info('duplicated notify, drop it')
        return HttpResponse('error')

    if verify_notify_id(notify_id) \
            and verify_alipay_signature(sign_type, sign, data) \
            and Charge.recharge(data, provider='alipay'):
        cache.set('ali_nid_' + hashlib.sha1(notify_id).hexdigest(),
                  order_id, 90000)  # notify_id 保存25小时。
        log.info('ali callback success')
        return HttpResponse('success')
    log.info('not a valid callback, ignore')
    return HttpResponse('error')


def rsa_sign(para_str):
    """对请求参数做rsa签名"""
    para_str = para_str.encode('utf-8')
    key = RSA.importKey(settings.ALIPAY_PRIVATE_KEY)
    h = SHA.new(para_str)
    signer = PKCS1_v1_5.new(key)
    return base64.b64encode(signer.sign(h))


@csrf_exempt
def alipay_sign(request):
    if request.method != 'POST':
        logging.error('equest.method != "POST"')
        return error_rsp(5099, 'error')

    log.debug('request.POST = %s' % request.POST)
    words = request.POST.get('words')
    if not words:
        logging.error('if not words')
        return error_rsp(5099, 'error')

    sign_type = request.POST.get('sign_type')
    if not sign_type:
        sign_type = 'RSA'

    if sign_type == 'RSA':
        en_str = rsa_sign(words)
    else:
        en_str = ''

    data = {'en_words': en_str}
    return rsp(data)


class WxEmptyResponse(WxResponse):

    def as_xml(self):
        return ''


class ChatView(WxApplication):
    SECRET_TOKEN = getattr(settings, 'GOLDENCAGE_WECHAT_TOKEN', '')
    BALANCE_UNIT_NAME = getattr(settings, 'GOLDENCAGE_BALANCE_UNIT_NAME',
                                u'金币')
    SUCCESS_MESSAGE_TEMPLATE = getattr(
        settings, 'GOLDENCAGE_COUPONE_SUCCESS_MESSAGE_TEMPLATE',
        u'您已获得了%d%s')

    def on_text(self, text):
        content = text.Content.lower()
        coupons = Coupon.objects.filter(disable=False, exchange_style='wechat')
        for cp in coupons:
            if content.startswith(cp.key):
                content = content.replace(cp.key, '').strip()
                result = cp.validate(content)
                if result:
                    return WxTextResponse(
                        self.SUCCESS_MESSAGE_TEMPLATE %
                        (cp.cost, self.BALANCE_UNIT_NAME), text)
                else:
                    return WxTextResponse(u'无效的兑换码,或已被兑换过。',
                                          text)
        return WxEmptyResponse(text)


@csrf_exempt
def wechat(request):
    """只处理文本，并且只处理一个命令。
    """
    app = ChatView()
    if request.method == 'GET':
        # 用于校验访问权限, 直接返回一字符串即可。
        rsp = app.process(request.GET)
        return HttpResponse(rsp)
    elif request.method == 'POST':
        rsp = app.process(request.GET, request.body)
        if not rsp:
            return HttpResponse('')
        return HttpResponse(rsp)

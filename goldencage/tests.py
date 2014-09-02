# encoding=utf-8

from django.test import TestCase
from django.test import Client
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.contrib.auth.models import User
from django.test.utils import override_settings

import hashlib
import time
from mock import Mock
import simplejson as json

from goldencage import views
from goldencage import config
from goldencage.models import task_done
from goldencage.models import appwalllog_done
from goldencage.models import payment_done
from goldencage.models import AppWallLog
from goldencage.models import Charge
from goldencage.models import ChargePlan
from goldencage.models import Task
from goldencage.models import Order


class OrderModelTest(TestCase):

    def test_get_real_id_without_prefix(self):
        self.assertEqual(999999999, Order.get_real_id(999999999))

    @override_settings(GOLDENCAGE_ORDER_ID_PREFIX=9)
    def test_get_real_id_prefix(self):
        self.assertEqual(999, Order.get_real_id(900000999))

    def test_get_order_id(self):
        order = Order()
        order.id = 100
        gid = order.gen_order_id()
        self.assertEqual(100, gid)

    @override_settings(GOLDENCAGE_ORDER_ID_PREFIX=9)
    def test_gen_order_id_prefix(self):
        order = Order()
        order.id = 100
        gid = order.gen_order_id()
        self.assertEqual(900000100, gid)

    @override_settings(GOLDENCAGE_ORDER_ID_PREFIX=9)
    def test_gen_order_id_prefix_repeat(self):
        order = Order()
        order.id = 999
        gid = order.gen_order_id()
        self.assertEqual(900000999, gid)


@skipIfCustomUser
class TaskModelTest(TestCase):

    def test_make_log_random(self):
        # 测试随机金币
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        task = Task(name='check in', key='check_in',
                    cost=10, cost_max=100)
        task.save()

        log = task.make_log(user)
        assert log.cost >= 10 and log.cost <= 100

    def test_make_log_infinity(self):
        # 测试随机金币
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        task = Task(name='check in', key='check_in',
                    cost=10)
        task.save()

        log = task.make_log(user)
        self.assertEqual(10, log.cost)
        log = task.make_log(user)
        self.assertEqual(10, log.cost)


@skipIfCustomUser
class AppWallCallbackTest(TestCase):

    def test_waps_callback(self):
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        data = {'adv_id': '1', 'app_id': 'theme',
                'key': user.pk, 'udid': 'myudid',
                'openudid': 'myopenid', 'bill': '2.0',
                'points': 200, 'ad_name': 'music talk'
                }
        appwalllog_done.send = Mock()
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['waps']), data)
        self.assertEqual(rsp.status_code, 200)
        appwalllog_done.send.assert_called_with(cost=200, user=user,
                                                sender=AppWallLog)

    def test_waps_callback_duplicate(self):
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        data = {'adv_id': '1', 'app_id': 'theme',
                'key': user.pk, 'udid': 'myudid',
                'openudid': 'myopenid', 'bill': '2.0',
                'points': 200, 'ad_name': 'music talk'
                }
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['waps']), data)
        self.assertEqual(rsp.status_code, 200)
        dt = json.loads(rsp.content)
        self.assertTrue(dt['success'])

        rsp = c.get(reverse('wall_cb', args=['waps']), data)
        self.assertEqual(rsp.status_code, 200)
        dt = json.loads(rsp.content)
        self.assertFalse(dt['success'])

    def test_waps_callback_invalid_ip(self):
        c = Client(REMOTE_ADDR='192.168.0.1')
        rsp = c.get(reverse('wall_cb', args=['waps']))
        self.assertEqual(rsp.status_code, 405)

    def create_youmi_ios_data(self, user):
        ts = int(time.time())
        return {'order': 'NO.1', 'app': 'my appid',
                'adid': '1', 'user': user.pk,
                'device': 'mydevice', 'chn': 0,
                'price': '4.9', 'points': 90,
                'time': ts, 'sig': 'xdref', 'ad': 'musictalk'
                }

    def test_youmi_ios_callback(self):
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        data = self.create_youmi_ios_data(user)
        keys = data.keys()
        keys.sort()
        appwalllog_done.send = Mock()
        src = ''.join(['%s=%s' % (k, unicode(data[k]).encode('utf-8'))
                       for k in keys])
        src += settings.YOUMI_CALLBACK_SECRET
        md5 = hashlib.md5()
        md5.update(src.encode('utf-8'))
        sign = md5.hexdigest()
        data['sign'] = sign
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['youmi_ios']), data)
        self.assertEqual(rsp.status_code, 200)
        appwalllog_done.send.assert_called_with(sender=AppWallLog,
                                                cost=90, user=user)

    def test_youmi_ios_missing_sign(self):
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['youmi_ios']))
        self.assertEqual(rsp.status_code, 403)

    def test_youmi_ios_invalidate_sign(self):
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        data = self.create_youmi_ios_data(user)
        data['sign'] = 'not a valid sign'
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['youmi_ios']), data)
        self.assertEqual(rsp.status_code, 403)

    def test_youmi_ios_duplicate(self):
        "同一个订单提交两次"
        user = User.objects.create_user('jeff', 'jeff@toraysoft.com', '123')
        data = self.create_youmi_ios_data(user)
        keys = data.keys()
        keys.sort()

        src = ''.join(['%s=%s' % (k, unicode(data[k]).encode('utf-8'))
                       for k in keys])
        src += settings.YOUMI_CALLBACK_SECRET
        md5 = hashlib.md5()
        md5.update(src.encode('utf-8'))
        sign = md5.hexdigest()
        data['sign'] = sign
        c = Client()
        rsp = c.get(reverse('wall_cb', args=['youmi_ios']), data)
        self.assertEqual(rsp.status_code, 200)
        # user = User.custom_objects.get(name=user.name)
        # self.assertEqual(user.balance, 90)

        rsp = c.get(reverse('wall_cb', args=['youmi_ios']), data)
        self.assertEqual(rsp.status_code, 403)


@skipIfCustomUser
class AlipayCallbackTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('jeff',
                                             'jeff@toraysoft.com', '123')
        self.plan = ChargePlan(name=u'plan1', code='plan1',
                               value=30, cost=750, coupon=50)
        self.plan.save()

    def create_payment_data(self):
        order = Order(user=self.user, plan=self.plan, value=30)
        order.save()
        return {'notify_time': '', 'notify_type': 'trade_status_sync',
                'notify_id': 'csdfo834jr', 'sign_type': 'RSA',
                'sign': 'no sign this time',
                'out_trade_no': order.pk, 'subject': u'多啦A梦',
                'payment_type': 1, 'trade_no': '2014112323e',
                'trade_status': 'TRADE_FINISHED', 'seller_id': '2088xx',
                'seller_email': 'toraysoft@gmail.com', 'buyer_id': '2088yy',
                'buyer_email': 'bbmyth@gmail.com', 'total_fee': 30,
                'quantity': 1, 'price': 30, 'body': u'不错的叮当主题哦',
                'gmt_create': '', 'gmt_payment': '',
                'is_total_fee_adjust': 'N', 'use_coupon': 'N', 'discount': '0'}

    def test_alipay_callback(self):
        # 正常流程, 第一次状态为等待付款，第二次为交易完成
        data = self.create_payment_data()
        c = Client()
        data['trade_status'] = 'WAIT_BUYER_PAY'
        payment_done.send = Mock()
        task_done.send = Mock()
        views.verify_notify_id = Mock(return_value=True)
        views.verify_alipay_signature = Mock(return_value=True)
        cache.set = Mock(return_value=None)

        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('success', rsp.content)
        self.assertEqual(payment_done.send.call_count, 0)
        self.assertEqual(task_done.send.call_count, 0)

        data['trade_status'] = 'TRADE_FINISHED'
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('success', rsp.content)
        cost = int(round(config.EXCHANGE_RATE * 30))
        payment_done.send.assert_called_with(sender=Charge,
                                             cost=cost, user=self.user)
        task_done.send.assert_called_with(sender=Task, cost=50,
                                          user=self.user)

    def test_alipay_callback_sign_error(self):
        # 签名错误
        data = self.create_payment_data()
        c = Client()
        views.verify_notify_id = Mock(return_value=True)
        views.verify_alipay_signature = Mock(return_value=False)
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('error', rsp.content)

    def test_alipay_callback_invalidate_request(self):
        # 非来自支付宝的请求
        data = self.create_payment_data()
        c = Client()
        views.verify_notify_id = Mock(return_value=False)
        views.verify_alipay_signature = Mock(return_value=True)
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('error', rsp.content)

    def test_alipay_notifyid_duplicated(self):
        # 重复收到同一个通知。通知ID同样。
        data = self.create_payment_data()
        views.verify_notify_id = Mock(return_value=True)
        views.verify_alipay_signature = Mock(return_value=True)

        cache.get = Mock(return_value=None)
        cache.set = Mock()
        payment_done.send = Mock()

        c = Client()
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('success', rsp.content)
        payment_done.send.assert_called_with(sender=Charge, cost=750,
                                             user=self.user)

        cache.get = Mock(return_value='123')
        payment_done.send = Mock()
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('error', rsp.content)

        self.assertTrue(cache.get.assert_called)
        self.assertEqual(0, payment_done.send.call_count)

    def test_alipay_callback_status_revert(self):
        # 同一个帐单，状态以先后不同的顺序回调。
        data = self.create_payment_data()
        data['trade_status'] = 'TRADE_FINISHED'
        views.verify_notify_id = Mock(return_value=True)
        views.verify_alipay_signature = Mock(return_value=True)
        cache.set = Mock(return_value=None)
        payment_done.send = Mock()
        c = Client()
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('success', rsp.content)

        self.assertEqual(1, payment_done.send.call_count)

        payment_done.send = Mock()
        data['trade_status'] = 'WAIT_BUYER_PAY'
        data['notify_id'] = 'another_notify'
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual(0, payment_done.send.call_count)
        self.assertEqual('success', rsp.content)
        self.assertEqual(2, cache.set.call_count)

    def test_alipay_callback_duplicated(self):
        # 同一个帐单，相同状态重复发送，将不会充值成功。
        data = self.create_payment_data()
        data['trade_status'] = 'WAIT_BUYER_PAY'

        views.verify_notify_id = Mock(return_value=True)
        views.verify_alipay_signature = Mock(return_value=True)
        cache.set = Mock()
        payment_done.send = Mock()
        c = Client()
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('success', rsp.content)

        data['notify_id'] = 'another_notify'
        rsp = c.get(reverse('alipay_cb'), data)
        self.assertEqual('error', rsp.content)

        self.assertEqual(1, cache.set.call_count)
        self.assertEqual(0, payment_done.send.call_count)

    def _test_signature(self):
        """ 测试之前，要去settings拷贝一个支付宝公钥
            或者不对这个做单元测试
        """
        settings.ALIPAY_PUBLIC_KEY = (
            ''
        )

        sign = (u"DoqHII4KFb5QRp5J/bAQPMI/1nJwHf8IcVHDZvvNR5CHCEmAkelExygYooWi"
                "yWchcBd2WHULCNtPKqFEWQALTynzUAkeF64zq9nyq8nzrVulwcKGnu+l"
                "ja6Sg+2EILb3o8RuFcPOL/YAD5y1FxjJBUM33Z+LDcWgb/+eSMDiTQk=")
        params = {
            u"seller_email": u"randotech@126.com",
            u"gmt_close": u"2014-09-02 11:37:03",
            u"sign": sign,
            u"subject": u"资助20元，赠送520金币",
            u"is_total_fee_adjust": u"N",
            u"gmt_create": u"2014-09-02 11:37:02",
            u"out_trade_no": u"117800",
            u"sign_type": u"RSA",
            u"price": u"20.00",
            u"buyer_email": u"mayuze13999087456@126.com",
            u"discount": u"0.00",
            u"trade_status": u"TRADE_FINISHED",
            u"gmt_payment": u"2014-09-02 11:37:03",
            u"trade_no": u"2014090200701660",
            u"seller_id": u"2088311247579029",
            u"use_coupon": u"N",
            u"payment_type": u"1",
            u"total_fee": u"20.00",
            u"notify_time": u"2014-09-02 11:37:41",
            u"buyer_id": u"2088502310925605",
            u"notify_id": u"be431b210180989044cc985639b2a8635c",
            u"notify_type": u"trade_status_sync",
            u"quantity": u"1"
        }
        print 'views %s' % views.verify_alipay_signature
        result = views.verify_alipay_signature('RSA', sign, params)
        self.assertEqual(True, result)


@skipIfCustomUser
class AlipaySignTest(TestCase):

    def setUp(self):
        pass

    def test_alipay_sign(self):
        # 测试用key
        settings.ALIPAY_PRIVATE_KEY = (
            '-----BEGIN RSA PRIVATE KEY-----\n'
            'MIICXAIBAAKBgQCxgCa64qPZ5IKudC+YdEDi2eyLbAtub2h1aBMmHj3hyc1Vdzjh'
            'HyUUt2rgJ7fQAnjNbypzOOWRjAuSsDhB3HfAdle7pJGU5HhVZEpVdNvvdErOMPj1'
            '9IXjTtSc2kBej3E4ETZB0CAbAo6vGzqN8B33NXwxJ6TE3rO/aPAI0SCnUQIDAQAB'
            'AoGAKWPKpDWJI5wHZQqutowVPVC3ueMd30iXQRldrbvLjkTyXoWIe+Y5TVVf1Jku'
            'YZDR/oV3jpqr3X6cjD4PQDxap+D/246GK+a+eDQDLfleb2RtKF1bl/6jqVcbHtnR'
            'kL0MNbYLkuneigVRCetAcGWRxv+BVVP9DYUBjAUq5GZyqAECQQDaFt64w0lj2Nq2'
            'Zb/izenEHX7d5QfsXL3tI1Mhxvzc2CznoTEQgMWgq8ayHd1KUW3KqtZqlrddxYYP'
            'OIAwHIQRAkEA0FsNqYpgU4VlzGzGrWuVq/JDdKYmWOjrk0UbIpKZtIZvvE5S06IV'
            'KJx2fnKh31riLhIJIqoewcaBVmKCV2QvQQJAfAf1su6dloOGH6XOc5bYFAkSVfAj'
            'iXFVMsCcTuF0fcUUBMfPt6sEulP3NOV3LQUSg+iU+RmuP05O5+kiPjp5gQJBALuG'
            'iBhkw+fIM2Q3LuYc43v7svzFIdR55rUIyLBoM9EIAn8AG4oA4nxHvlp2f/yQRuvi'
            'Lbi2VrJfID+Ir/lJ4UECQCgEcFtaNfdZMkQ7Icsw2xynaSJ/osQbpxcOwq4itZ56'
            'xs80ciaAm/uEY7lKiLMmMrjLLD9PBqsrTHa3bMIFaPw='
            '\n-----END RSA PRIVATE KEY-----')

        words = ('partner="2088311247579029"&seller_id="randotech@126.com"&'
                 'out_trade_no="P5IRN0A7B8P1BR7"&subject="珍珠项链"&'
                 'body="[2元包邮]韩版 韩国 流行饰品太阳花小巧雏菊 珍珠项链2M15"&'
                 'total_fee="10.00"&notify_url="http%3A%2F%2Fwwww.xxx.com"&'
                 'service="mobile.securitypay.pay"&_input_charset="utf-8"&'
                 'payment_type="1"&return_url="www.xxx.com"&it_b_pay="1d"&'
                 'show_url="www.xxx.com"')
        data = {'words': words}
        c = Client()
        rsp = c.post(reverse('alipaysign'), data)
        print rsp.content

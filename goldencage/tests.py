#encoding=utf-8

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
        sign = ("C5hIr/2XQM6eC4JE2bpKGXVHXQXyALYOMcVUQ7W2mjXVm0MggzEAxJGH"
                "MYMqPMdh+M9QVU9tNw2kfUn5qlSHspHgEULtHChNWN+rH+clCYYrERRNA"
                "m3AXUAawotknhtYDfzJTfpcQWmBqB+RU8YJtpsac+uOtsLc3YaiNvOd+1s=")
        params = {
            "seller_email":"randotech@126.com",
            "subject":u"资肋主题助手",
            "is_total_fee_adjust":"Y",
            "gmt_create":"2014-04-19 17:35:11",
            "out_trade_no":"12",
            "sign_type":"RSA",
            "body": u"资助主题助手, 让我们更好的为您服务。",
            "price":"0.10",
            "buyer_email":"bbmyth@gmail.com",
            "discount":"0.00",
            "trade_status":"WAIT_BUYER_PAY",
            "trade_no":"2014041956857959",
            "seller_id":"2088311247579029",
            "use_coupon":"N",
            "payment_type":"1",
            "total_fee":"0.10",
            "notify_time":"2014-04-19 17:35:11",
            "quantity":"1",
            "notify_id":"a1fbf729fd1824686d11bad2d9fa5f1d5a",
            "notify_type":"trade_status_sync",
            "buyer_id":"2088002802114592"
            }
        print 'views %s' % views.verify_alipay_signature
        result = views.verify_alipay_signature('RSA', sign, params)
        self.assertEqual(True, result)

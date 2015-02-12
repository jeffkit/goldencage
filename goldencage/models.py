# encoding=utf-8
from django.db import models
from django.db import IntegrityError
from django.conf import settings
from django.dispatch import Signal

from jsonfield import JSONField
import calendar
import time
from datetime import datetime
from goldencage import config
import random
import pytz
from hashlib import sha1

import logging
log = logging.getLogger(__name__)


task_done = Signal(providing_args=['cost', 'user'])
appwalllog_done = Signal(providing_args=['cost', 'user'])
payment_done = Signal(providing_args=['cost', 'user'])
apply_coupon = Signal(providing_args=['instance', 'cost', 'user'])


class Task(models.Model):
    name = models.CharField(u'任务名称', max_length=50)
    key = models.CharField(u'代码', max_length=50, unique=True)
    cost = models.IntegerField(u'金币', default=0)
    cost_max = models.IntegerField(
        u'最大金币', default=0,
        help_text=u'如不为0，实际所得为"金币"与"最大金币"之间的随机值')
    interval = models.IntegerField(
        u'时间间隔',
        default=0,
        help_text=u'两次任务之间的时间间隔（秒），0为不限')
    limit = models.IntegerField(
        u'次数上限',
        default=0,
        help_text=u'任务允许执行的最大次数，0为不限')
    daily = models.BooleanField(u'允许每天一次', default=False)

    def _save_log(self, user, valid=True, cost=None):
        if not cost:
            if self.cost_max > 0 and self.cost < self.cost_max:
                cost = random.randint(self.cost, self.cost_max)
        cost = cost or self.cost

        log = TaskLog(user=user, job=self, valid=valid,
                      cost=cost if valid else 0)
        log.save()
        if valid:
            task_done.send(sender=Task, cost=log.cost, user=user)
        return log

    def make_log(self, user, cost=None):
        last = TaskLog.objects.filter(
            user=user, job=self, valid=True).order_by('-create_time')

        if not last:
            return self._save_log(user, cost=cost)

        if self.limit > 0:
            if last.count() >= self.limit:
                return self._save_log(user, False, cost=cost)

        if self.interval > 0:
            last_time = calendar.timegm(last[0].create_time.timetuple())
            if (time.time() - last_time) <= self.interval:
                return self._save_log(user, False, cost=cost)
        if self.daily:
            d1 = datetime.now()
            d2 = last[0].create_time.replace(tzinfo=pytz.utc)\
                .astimezone(pytz.timezone(settings.TIME_ZONE))
            log.info('date 1 %s, date 2 %s' % (d1, d2))
            if d1.date() <= d2.date():
                return self._save_log(user, False, cost=cost)

        return self._save_log(user, cost=cost)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'任务类型'
        verbose_name_plural = u'任务类型'


class TaskLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    job = models.ForeignKey(Task)
    cost = models.IntegerField()
    create_time = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)

    class Meta:
        verbose_name = u'任务纪录'
        verbose_name_plural = u'任务纪录'


class AppWallLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    provider = models.CharField(max_length=20,
                                choices=(('youmi_ios', u'有米iOS'),
                                         ('youmi_adr', u'有米Android'),
                                         ('waps', u'万普'),
                                         ('dianjoy_adr', u'点乐'),
                                         ('qumi', u'趣米iOS'),
                                         ('qumi_adr', u'趣米Android')))
    identity = models.CharField(max_length=100)
    cost = models.IntegerField()
    product_id = models.CharField(max_length=100)
    product_name = models.CharField(max_length=100)
    create_time = models.DateTimeField(auto_now_add=True)
    valid = models.BooleanField(default=True)
    extra_data = JSONField(blank=True, null=True)

    class Meta:
        verbose_name = u'积分墙纪录'
        verbose_name_plural = u'积分墙纪录'

        unique_together = (('user', 'provider', 'identity'),)

    @classmethod
    def log(cls, data, provider):
        if provider not in config.APPWALLLOG_MAPPING:
            raise ValueError('unknown appwall provider')
        mapping = config.APPWALLLOG_MAPPING[provider]
        alog = AppWallLog(provider=provider)
        for key, value in mapping.iteritems():
            if isinstance(value, tuple):
                value = '_'.join([data.get(v, '') for v in value])
            else:
                value = data[value]
            if key in ('user_id', 'cost'):
                try:
                    value = int(value)
                except:
                    return True
            setattr(alog, key, value)
        alog.extra_data = data
        # 超出的唯一标识，将换成为sha1字符串再存储。
        if len(alog.identity) >= 100:
            alog.identity = sha1(alog.identity).hexdigest()
        try:
            alog.save()
            appwalllog_done.send(sender=cls, cost=alog.cost, user=alog.user)
            return alog
        except IntegrityError:
            return None


class ChargePlan(models.Model):
    name = models.CharField(u'标题', max_length=50)
    value = models.IntegerField(u'价值')
    cost = models.IntegerField(u'对应积分')
    coupon = models.IntegerField(u'赠送积分', default=0)
    valid = models.BooleanField(u'有效', default=True)
    code = models.CharField(u'商品代码', max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'充值套餐'
        verbose_name_plural = u'充值套餐'


class Order(models.Model):
    plan = models.ForeignKey(ChargePlan, verbose_name='套餐')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'用户')
    platform = models.CharField(u'支付平台', max_length=20)
    create_time = models.DateTimeField(auto_now_add=True)
    value = models.IntegerField(u'金额(单位：分)')
    status = models.IntegerField(default=0,
                                 choices=((0, u'已下订'), (1, u'已支付'),
                                          (2, u'过期未支付')))

    def __unicode__(self):
        return self.plan.name

    @classmethod
    def get_real_id(cls, oid):
        test_id = str(oid)
        if len(test_id) < 9:
            return oid

        prefix = getattr(settings, 'GOLDENCAGE_ORDER_ID_PREFIX', 0)
        if not prefix:
            return oid
        prefix = str(prefix)
        if not test_id.startswith(prefix):
            return oid

        return int(test_id[len(prefix):])

    def gen_order_id(self):
        prefix = getattr(settings, 'GOLDENCAGE_ORDER_ID_PREFIX', 0)
        if not prefix:
            return self.id
        try:
            prefix = int(prefix)
        except:
            return self.id

        prefix = str(prefix)
        rid = str(self.id)
        paddings = '0' * (9 - len(prefix) - len(rid))
        return int(prefix + paddings + rid)

    class Meta:
        verbose_name = u'订单'
        verbose_name_plural = u'订单'


class Charge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'用户')
    platform = models.CharField(u'充值平台', max_length=20)
    account = models.CharField(u'充值帐号', max_length=50)
    email = models.CharField(u'充值帐号email', max_length=50,
                             blank=True, null=True, db_index=True)
    value = models.IntegerField(u'充入金额(单位：分)')
    cost = models.IntegerField(u'价值积分')
    transaction_id = models.CharField(u'平台交易号', max_length=100)
    order_id = models.CharField(u'交易号', max_length=100, unique=True)
    create_time = models.DateTimeField(u'交易时间', auto_now_add=True)
    valid = models.BooleanField(u'是否有效', default=True)
    status = models.CharField(u'状态', max_length=50, blank=True, null=True)
    extra_data = JSONField(u'交易源数据', blank=True, null=True)

    class Meta:
        verbose_name = u'充值纪录'
        verbose_name_plural = u'充值纪录'

        unique_together = (('platform', 'transaction_id'),)

    def is_finish(self):
        return self.status == config.PAYMENT_FINISH[self.platform]

    def value_in_cent(self, value):
        return int(value * config.PAYMENT_SCALE[self.platform])

    @classmethod
    def recharge(cls, data, provider):

        def dispatch_signal(cost, user, plan, order):
            payment_done.send(sender=cls, cost=cost,
                              user=user)
            if plan and plan.coupon > 0:
                try:
                    task = Task.objects.get(key='__recharge')
                except Task.DoesNotExist:
                    task = Task(name=u'充值', key='__recharge')
                    task.save()
                task.make_log(user, cost=plan.coupon)
            order.status = 1
            order.save()

        if provider not in config.PAYMENT_MAPPING:
            raise ValueError('no mapping for %s' % provider)
        mapping = config.PAYMENT_MAPPING[provider]
        chg = Charge(platform=provider)
        for key, value in mapping.iteritems():
            value = data[value]
            if key == 'value':
                value = chg.value_in_cent(float(value))
            setattr(chg, key, value)
        chg.extra_data = data

        order = Order.objects.get(pk=Order.get_real_id(chg.order_id))

        if order.value != chg.value:
            log.info('Order.value = %s' % order.value)
            log.info('chg.value = %s' % chg.value)
            log.error(u'充值的金额与套餐不匹配，无效 %s' % chg.order_id)
            return None
        plan = order.plan
        chg.cost = plan.cost
        chg.user = order.user
        chg.valid = False

        result = Charge.objects.filter(platform=chg.platform,
                                       transaction_id=chg.transaction_id)
        if result:
            result = result[0]
            if result.status == chg.status:
                return None
            else:
                if result.is_finish():
                    # 已经完毕，这条旧通知是来晚了。忽略掉
                    return result

                # 还没完结，继续修改状态。
                if chg.is_finish():
                    result.valid = True
                    dispatch_signal(result.cost, result.user, plan, order)
                # 更新状态
                result.status = chg.status
                result.save()
                return result
        else:
            try:
                if chg.is_finish():
                    chg.valid = True
                    chg.save()
                    dispatch_signal(chg.cost, chg.user, plan, order)
                else:
                    # 怕signal的connect方出了错, 写两个save吧
                    chg.save()

                return chg
            except IntegrityError:
                return None


class Coupon(models.Model):

    """优惠券，用于各种活动兑换金币用。
    """
    name = models.CharField(u'名称', max_length=50)
    key = models.CharField(u'代码', max_length=50)
    cost = models.IntegerField(u'价值积分', default=0)
    disable = models.BooleanField(u'禁用', default=False)
    create_time = models.DateTimeField(auto_now_add=True)

    exchange_style = models.CharField(u'兑换方式', default=u'wechat',
                                      max_length=10)
    exchange_config = JSONField(blank=True, null=True)

    # 限制
    limit = models.IntegerField(u'每个限制次数', default=1,
                                help_text=u'值为0时不限')

    def generate(self, user, default=None):
        """为用户生成一张优惠券,
        """

        # 看看该优惠券是否限制次数，有限制，同时
        if self.limit:
            exchanges = Exchange.objects.filter(
                coupon=self, user=user, status='DONE').count()
            if exchanges >= self.limit:
                return None

        waitings = Exchange.objects.filter(
            coupon=self, user=user, status='WAITING')
        if waitings:
            return waitings[0]
        else:
            max_value = getattr(settings, 'GOLDENCAGE_COUPONCODE_MAX',
                                999999)
            code = default or random.randint(1000, max_value)
            while True:
                test = Exchange.objects.filter(exchange_code=str(code),
                                               coupon=self, status='WAITING')
                if not test:
                    break
                code = random.randint(1000, max_value)
            exchange = Exchange(coupon=self, user=user, cost=self.cost,
                                exchange_code=str(code))
            exchange.save()
            return exchange

    def validate(self, code, user=None):
        """ 验证优惠券
        """
        exchange = Exchange.objects.filter(
            coupon=self, exchange_code=code, status='WAITING')
        if not exchange:
            return False
        exchange = exchange[0]
        exchange.status = 'DONE'
        exchange.exchange_user = user
        exchange.cost = self.cost
        exchange.save()
        apply_coupon.send(sender=Coupon, instance=self,
                          cost=exchange.cost, user=exchange.user)
        return exchange

    class Meta:
        verbose_name = u'礼券'
        verbose_name_plural = u'礼券'

    def __unicode__(self):
        return self.name


class Exchange(models.Model):

    """优惠券兑换纪录
    """
    coupon = models.ForeignKey(Coupon, verbose_name=u'优惠券')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=u'用户')
    exchange_code = models.CharField(u'兑换码', max_length=50,
                                     blank=True, null=True,
                                     db_index=True)
    status = models.CharField(u'状态', max_length=10,
                              default='WAITING',
                              choices=(('WAITING', u'等待兑换'),
                                       ('DONE', u'兑换完成')))
    cost = models.IntegerField(u'获得积分', default=0)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    exchange_user = models.CharField(u'兑换用户', max_length=200,
                                     blank=True, null=True)

    class Meta:
        verbose_name = u'礼券兑换纪录'
        verbose_name_plural = u'礼券兑换纪录'

    def __unicode__(self):
        return self.coupon.name

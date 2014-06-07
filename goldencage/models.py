#encoding=utf-8
from django.db import models
from django.db import IntegrityError
from django.conf import settings
from django.dispatch import Signal

from jsonfield import JSONField
import calendar
import time
from goldencage import config
import random

task_done = Signal(providing_args=['cost', 'user'])
appwalllog_done = Signal(providing_args=['cost', 'user'])
payment_done = Signal(providing_args=['cost', 'user'])


class Task(models.Model):
    name = models.CharField(u'任务名称', max_length=50)
    key = models.CharField(u'代码', max_length=50, unique=True)
    cost = models.IntegerField(u'金币', default=0)
    cost_max = models.IntegerField(
        u'最大金币', default=0,
        help_text=u'如不为0，实际所得为"金币"与"最大金币"之间的随机值')
    interval = models.IntegerField(default=0)  # 有效间隔时间, 0为不限
    limit = models.IntegerField(default=0)  # 有效次数，0为不限

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
                                         ('waps', u'万普')))
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
                value = '_'.join([data[v] for v in value])
            else:
                value = data[value]
            if key in ('user_id', 'cost'):
                try:
                    value = int(value)
                except:
                    return True
            setattr(alog, key, value)
        alog.extra_data = data
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
                             blank=True, null=True)
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
                value = int(float(value) * 100)
            setattr(chg, key, value)
        chg.extra_data = data

        order = Order.objects.get(pk=Order.get_real_id(chg.order_id))
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
                if result.status == 'TRADE_FINISHED':
                    # 已经完毕，这条旧通知是来晚了。忽略掉
                    return result

                # 还没完结，继续修改状态。
                if chg.status == 'TRADE_FINISHED':
                    result.valid = True
                    dispatch_signal(result.cost, result.user, plan, order)
                # 更新状态
                result.status = chg.status
                result.save()
                return result
        else:
            try:
                chg.save()
                if chg.status == 'TRADE_FINISHED':
                    dispatch_signal(chg.cost, chg.user, plan, order)
                return chg
            except IntegrityError:
                return None

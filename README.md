goldencage
==========

通用移动应用积分管理模块 for Django

安装
----

 pip install goldencage

配置Django settings

添加到INSTLLED_APPS：

 	INSTALLED_APPS = (
    	...
    	'goldencage',
	    ...
	 )

配置参数
-------

在settings下加入以下参数：

YOUMI_CALLBACK_SECRET  有米iOS积分墙回调的密钥。

YOUMI_CALLBACK_SECRET_ADR 有米Android积分墙回调密钥。

GOLDENCAGE_DIANJOY_ANDROID_SECRET 点乐Android积分墙回调密钥。

ALIPAY_PID 支付宝的ParternerID

GOLDENCAGE_ORDER_ID_PREFIX ,订单前缀，仅支持数字。用于多个应用共享一个parternerID的情况，避免订单重复。

GOLDENCAGE_WECHAT_TOKEN, 微信兑换礼券时用，微信回调的token。

GOLDENCAGE_BALANCE_UNIT_NAME, 用户余额的单位名称，如金币，米币等。默认为金币。

GOLDENCAGE_COUPONCODE_MAX, 礼券码的最大值，派发礼券时将从1000至该值随机选择。默认为999999。

GOLDENCAGE_COUPONE_SUCCESS_MESSAGE_TEMPLATE, 积分兑换成功后的提示语模板，接受%d及%s两个参数。

配置url
-------
为支付宝的回调，有米、万普的积份墙回调配置url,goldencage已实现了回调的view，在goldencage.urls模块下面，直接引用即可：

 	urlpatterns = patterns(
    	'',
     	url(r'^admin/', include(admin.site.urls)),
    	url(r'^gc/', include('goldencage.urls')),
  	)

signal
------
用户完全积分墙的任务、使用支付宝充值之后，会发出以下signal，开发者需要响应这些signal，修改用户的信息。
task_done: 用户完成了一次任务，如签到，分享到朋友圈。

appwalllog_done:用户完成了一具积份墙任务。

payent_done: 用户完成了支付宝充值。

所有signal的处理函数都要接受三个参数：

sender: 信号发送者

cost：价值，数值型，具体意义视应用定，可以是金币数，也可能是购买到的时间。

user：用户。

apply_coupon: 领取了一张礼券，除上面的共同参数外，还有一个instanct参数：

instance， coupone的实例。

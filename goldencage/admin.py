#encoding=utf-8

from django.contrib import admin

from goldencage.models import Task
from goldencage.models import ChargePlan
from goldencage.models import TaskLog
from goldencage.models import Charge
from goldencage.models import Order
from goldencage.models import AppWallLog


class TaskLogAdmin(admin.ModelAdmin):
    list_display = ['job', 'cost', 'create_time', 'valid']
    list_filter = ('job', 'create_time')
    raw_id_fields = ('user',)
    list_select_related = False


class AppWallLogAdmin(admin.ModelAdmin):
    list_display = ['provider', 'cost', 'product_name', 'create_time', 'valid']
    list_filter = ('provider', 'create_time')
    raw_id_fields = ('user',)
    list_select_related = False


class OrderAdmin(admin.ModelAdmin):
    list_display = ('plan', 'value', 'status', 'create_time')
    list_filter = ('plan', 'create_time', 'status')
    raw_id_fields = ('user',)
    list_select_related = False


class ChargeAdmin(admin.ModelAdmin):
    list_display = ('user', 'account', 'email', 'value', 'cost',
                    'create_time', 'status')
    list_filter = ('create_time', 'status')
    raw_id_fields = ('user',)
    list_select_related = False


admin.site.register(Task, admin.ModelAdmin)
admin.site.register(ChargePlan, admin.ModelAdmin)
admin.site.register(TaskLog, TaskLogAdmin)
admin.site.register(Charge, ChargeAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(AppWallLog, AppWallLogAdmin)

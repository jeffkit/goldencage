# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Task'
        db.create_table(u'goldencage_task', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('cost', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('cost_max', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('interval', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('limit', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'goldencage', ['Task'])

        # Adding model 'TaskLog'
        db.create_table(u'goldencage_tasklog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('job', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['goldencage.Task'])),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('create_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'goldencage', ['TaskLog'])

        # Adding model 'AppWallLog'
        db.create_table(u'goldencage_appwalllog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('provider', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('identity', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('product_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('product_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('create_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('extra_data', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'goldencage', ['AppWallLog'])

        # Adding unique constraint on 'AppWallLog', fields ['user', 'provider', 'identity']
        db.create_unique(u'goldencage_appwalllog', ['user_id', 'provider', 'identity'])

        # Adding model 'ChargePlan'
        db.create_table(u'goldencage_chargeplan', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('coupon', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'goldencage', ['ChargePlan'])

        # Adding model 'Order'
        db.create_table(u'goldencage_order', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('plan', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['goldencage.ChargePlan'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('platform', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('create_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'goldencage', ['Order'])

        # Adding model 'Charge'
        db.create_table(u'goldencage_charge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('platform', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('account', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('value', self.gf('django.db.models.fields.IntegerField')()),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('transaction_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('order_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('create_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('extra_data', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'goldencage', ['Charge'])

        # Adding unique constraint on 'Charge', fields ['platform', 'transaction_id']
        db.create_unique(u'goldencage_charge', ['platform', 'transaction_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Charge', fields ['platform', 'transaction_id']
        db.delete_unique(u'goldencage_charge', ['platform', 'transaction_id'])

        # Removing unique constraint on 'AppWallLog', fields ['user', 'provider', 'identity']
        db.delete_unique(u'goldencage_appwalllog', ['user_id', 'provider', 'identity'])

        # Deleting model 'Task'
        db.delete_table(u'goldencage_task')

        # Deleting model 'TaskLog'
        db.delete_table(u'goldencage_tasklog')

        # Deleting model 'AppWallLog'
        db.delete_table(u'goldencage_appwalllog')

        # Deleting model 'ChargePlan'
        db.delete_table(u'goldencage_chargeplan')

        # Deleting model 'Order'
        db.delete_table(u'goldencage_order')

        # Deleting model 'Charge'
        db.delete_table(u'goldencage_charge')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'goldencage.appwalllog': {
            'Meta': {'unique_together': "(('user', 'provider', 'identity'),)", 'object_name': 'AppWallLog'},
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            'create_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identity': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'product_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'goldencage.charge': {
            'Meta': {'unique_together': "(('platform', 'transaction_id'),)", 'object_name': 'Charge'},
            'account': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            'create_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'extra_data': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'transaction_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        u'goldencage.chargeplan': {
            'Meta': {'object_name': 'ChargePlan'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            'coupon': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        u'goldencage.order': {
            'Meta': {'object_name': 'Order'},
            'create_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'plan': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['goldencage.ChargePlan']"}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        u'goldencage.task': {
            'Meta': {'object_name': 'Task'},
            'cost': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'cost_max': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'limit': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'goldencage.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            'create_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['goldencage.Task']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['goldencage']
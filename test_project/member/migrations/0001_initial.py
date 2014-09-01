# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'MyUser'
        db.create_table(u'member_myuser', (
            (u'customuser_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.CustomUser'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'member', ['MyUser'])


    def backwards(self, orm):
        # Deleting model 'MyUser'
        db.delete_table(u'member_myuser')


    models = {
        'auth.customuser': {
            'Meta': {'object_name': 'CustomUser'},
            'date_of_birth': ('django.db.models.fields.DateField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'member.myuser': {
            'Meta': {'object_name': 'MyUser', '_ormbases': ['auth.CustomUser']},
            u'customuser_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.CustomUser']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['member']
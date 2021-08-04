# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-02-19 23:07
from __future__ import unicode_literals

import jsonfield.fields

import django.db.models.deletion
from django.db import migrations, models


def create_initial_authors(apps, schema):
    Author = apps.get_model('testapp.Author')
    Author.objects.create(
        name="Fred Johnston",
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='testapp.Author')),
            ],
        ),
        migrations.CreateModel(
            name='Citation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('metadata', jsonfield.fields.JSONField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='testapp.Author')),
            ],
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=1000)),
                ('mobile', models.CharField(max_length=50)),
                ('address', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('primary_contact', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='testapp.Contact')),
            ],
        ),
        migrations.RunPython(code=create_initial_authors)
    ]
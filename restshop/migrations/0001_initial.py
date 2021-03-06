# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-20 22:32
from __future__ import unicode_literals

import datetime
from decimal import Decimal
from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.hstore
import django.contrib.postgres.fields.jsonb
import django.contrib.postgres.fields.ranges
from django.contrib.postgres.operations import HStoreExtension
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
import django_countries.fields
import djmoney.models.fields
import model_utils.fields
import restshop.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company', models.CharField(blank=True, default='', max_length=80, verbose_name='company')),
                ('first_name', models.CharField(max_length=80, verbose_name='first name')),
                ('last_name', models.CharField(max_length=80, verbose_name='last name')),
                ('street_address_1', models.TextField(verbose_name='street address line 1')),
                ('street_address_2', models.TextField(blank=True, default='', verbose_name='street address line 2')),
                ('postal_code', models.CharField(max_length=20, verbose_name='postal code')),
                ('city', models.CharField(max_length=80, verbose_name='city')),
                ('country', django_countries.fields.CountryField(blank=True, default='', max_length=2, verbose_name='country')),
                ('state', models.CharField(blank=True, default='', max_length=2, verbose_name='state')),
            ],
        ),
        migrations.CreateModel(
            name='DiscountBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default=restshop.models.generate_random_code, max_length=30, unique=True, verbose_name='code')),
                ('is_active', models.BooleanField(default=True, verbose_name='is active')),
                ('valid', django.contrib.postgres.fields.ranges.DateRangeField(default=(datetime.date.today, None), verbose_name='validity range')),
                ('allowed_uses', models.IntegerField(blank=True, help_text='Leave empty if there is no limit on the number of uses of this discount.', null=True, verbose_name='number of allowed uses')),
                ('used', models.IntegerField(default=0, verbose_name='number of times already used')),
                ('amount_currency', djmoney.models.fields.CurrencyField(choices=[('SEK', 'Swedish Krona')], default='SEK', editable=False, max_length=3)),
                ('amount', djmoney.models.fields.MoneyField(decimal_places=2, default=Decimal('0'), max_digits=18)),
            ],
            options={
                'verbose_name': 'discount',
                'verbose_name_plural': 'discounts',
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('pending', 'pending'), ('authorized', 'authorized'), ('captured', 'captured'), ('canceled', 'canceled'), ('refunded', 'refunded'), ('failed', 'failed')], default='pending', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('owed', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ('paid', models.DecimalField(decimal_places=2, default=0, max_digits=18)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='InvoiceEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('transaction_id', models.CharField(db_index=True, help_text='Unique ID identifying this payment in the foreign system.', max_length=50, verbose_name='transaction ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='JSON-encoded additional data about the event.', verbose_name='data')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='restshop.Invoice')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('cart', 'cart'), ('confirmed', 'confirmed'), ('paid', 'paid'), ('canceled', 'canceled'), ('completed', 'completed'), ('refunded', 'refunded')], default='cart', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('currency', djmoney.models.fields.CurrencyField(default='SEK', max_length=3)),
                ('email', models.EmailField(blank=True, default='', max_length=254, verbose_name='email address')),
                ('custom', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, verbose_name='custom order data')),
                ('billing_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='restshop.Address')),
                ('shipping_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='restshop.Address')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=128)),
                ('quantity', models.IntegerField()),
                ('item_type', models.CharField(choices=[('sku', 'sku'), ('discount', 'discount'), ('shipping_fee', 'shipping_fee'), ('invoice_fee', 'invoice_fee'), ('reminder_fee', 'reminder_fee'), ('interest_fee', 'interest_fee')], default='sku', max_length=12)),
                ('price', models.DecimalField(decimal_places=2, default=0, help_text='Line item price excl. tax', max_digits=18, verbose_name='line item price')),
                ('discount', models.DecimalField(decimal_places=2, default=0, help_text='Discount excl. tax', max_digits=18, verbose_name='line item discount')),
                ('vat', models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name='line item VAT')),
                ('vat_rate', models.DecimalField(decimal_places=2, default=0, max_digits=4, verbose_name='line item VAT rate %')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='restshop.Order')),
            ],
        ),
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(blank=True, null=True, verbose_name='start')),
                ('end', models.DateTimeField(blank=True, null=True, verbose_name='end')),
                ('amount_currency', djmoney.models.fields.CurrencyField(choices=[('SEK', 'Swedish Krona')], default='SEK', editable=False, max_length=3)),
                ('amount', djmoney.models.fields.MoneyField(decimal_places=2, default=Decimal('0.0'), max_digits=8, verbose_name='price excluding VAT')),
                ('is_sale', models.BooleanField(default=False, verbose_name='this is a sales price')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('active', models.BooleanField(default=True)),
                ('attributes', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=40), blank=True, default=list, help_text='These define the variations that will become available. One per line.', size=None)),
                ('caption', models.CharField(blank=True, default='', max_length=80)),
                ('description', models.TextField(blank=True, default='')),
                ('name', models.CharField(max_length=40)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StockKeepingUnit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('_active', models.BooleanField(default=True, verbose_name='active')),
                ('attributes', django.contrib.postgres.fields.hstore.HStoreField(default=dict)),
                ('initial_quantity', models.PositiveIntegerField(blank=True, null=True)),
                ('prices', models.ManyToManyField(related_name='products', to='restshop.Price')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skus', to='restshop.Product')),
            ],
            managers=[
                ('active', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='VAT',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(help_text='Description of your choosing to remember what this rate is used for', max_length=40, verbose_name='description')),
                ('rate', models.DecimalField(decimal_places=2, help_text='VAT rate %', max_digits=4)),
            ],
            options={
                'verbose_name': 'VAT rate',
                'verbose_name_plural': 'VAT rates',
            },
        ),
        migrations.AddField(
            model_name='price',
            name='vat',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='restshop.VAT', verbose_name='VAT'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='restshop.StockKeepingUnit', verbose_name='product'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='restshop.Order'),
        ),
        migrations.AlterUniqueTogether(
            name='stockkeepingunit',
            unique_together=set([('attributes', 'product')]),
        ),
        migrations.AlterUniqueTogether(
            name='orderitem',
            unique_together=set([('order', 'product')]),
        ),
    ]

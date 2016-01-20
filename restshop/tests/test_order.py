# -*- coding: utf-8 -*-
import decimal
from unittest import mock
from django.utils.http import urlencode

from rest_framework import test
from rest_framework.reverse import reverse

from restshop import signals, serializers
from restshop.models import Order
from .test_product import products_and_price


class OrderTest(test.APITestCase):

    def setUp(self):
        self.product = products_and_price()

    def test_create_order(self):
        order = Order.objects.create(
            email='tester@test.com',
        )
        self.assertEqual(
            'cart',
            order.status,
        )
        item = order.items.create(
            quantity=2,
            price='100.00',
            vat='25',
            discount='40'
        )
        self.assertEqual(
            decimal.Decimal('170.00'),
            order.amount,
        )
        self.assertEqual(
            1,
            order.items.count()
        )

    def test_order_api(self):
        custom_validator = mock.MagicMock()
        signals.validate_custom_order_field.connect(custom_validator)
        response = self.client.post(
            reverse('order-detail'),
            {
                'email': 'test@test.com',
                'items': [{
                    'quantity': 2,
                    'description': 'the product',
                    'price': '100.00',
                    'vat': '25.00',
                    'discount': '0.00',
                    'product': self.product.skus.all()[0].id
                }, {
                    'quantity': 1,
                    'description': 'the product',
                    'price': '100.00',
                    'vat': '25.00',
                    'discount': '50.00',
                    'product': self.product.skus.all()[1].id
                },],
                'custom': {
                    'accepts_toc': True,
                }
            },
            format='json'
        )
        self.assertEqual(
            201,
            response.status_code,
            response.content
        )
        self.assertEqual(
            decimal.Decimal('325.00'),
            response.data['amount']
        )
        custom_validator.assert_called_with(
            sender=serializers.OrderSerializer,
            signal=signals.validate_custom_order_field,
            value={'accepts_toc': True},
        )
        response = self.client.get(
            reverse('order-detail')
        )

    def test_add_remove_item(self):
        order = self.order_to_session()

        response = self.client.patch(
            reverse('order-detail'),
            {'items': [{
                'quantity': 1,
                'description': 'the product',
                'price': '100.00',
                'vat': '25.00',
                'vat_rate': '25.00',
                'discount': '50.00',
                'product': self.product.skus.all()[0].id
            }]}
        )
        self.assertEqual(
            200,
            response.status_code,
            response.content
        )
        self.assertEqual(
            response.data['amount'],
            decimal.Decimal('75.00')
        )
        order.refresh_from_db()
        self.assertEqual(
            1,
            order.items.all().count()
        )
        item = response.data['items'][0]
        self.assertEqual(
            item['description'],
            'the product',
            response.data,
        )
        response = self.client.delete(
            reverse('items-detail', args=[item['id']]),
        )
        self.assertEqual(204, response.status_code)
        response = self.client.get(
            reverse('order-detail'),
        )
        self.assertEqual(
            response.data['amount'],
            decimal.Decimal('0.00')
        )

    def order_to_session(self):
        order = Order.objects.create(
            email='tester@test.com',
        )
        session = self.client.session
        session['order_id'] = order.pk
        session.save()
        return order

    def test_invalid_item_values(self):
        response = self.client.post(
            reverse('order-detail'),
            {
                'email': 'test@test.com',
                'items': [{
                    'quantity': 2,
                    'description': 'the product',
                    'price': '110.00',
                    'vat': '20.00',
                    'discount': '0.00',
                    'product': self.product.skus.all()[0].id
                }]
            }
        )
        self.assertEqual(400, response.status_code)
        self.assertIn('price', response.data['items'][0])
        self.assertIn('vat', response.data['items'][0])

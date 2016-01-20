# -*- coding: utf-8 -*-
import decimal
from unittest import mock

from rest_framework import test
from rest_framework.reverse import reverse

from restshop import signals, views, serializers, exceptions, models
from paymentmethods.emailinvoice.models import EmailInvoice
from restshop.tests.test_product import products_and_price


class PaymentTests(test.APITestCase):

    def test_list_methods(self):
        response = self.client.get(
            reverse('paymentprovider-list')
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.data))
        self.assertEqual(
            'emailinvoice.emailinvoice',
            response.data[0]['key']
        )
        self.assertEqual(
            'Email Invoice',
            response.data[0]['name']
        )

    def test_nonexisting_method(self):
        response = self.client.post('/order/pay/paywith.me/', {})
        self.assertEqual(404, response.status_code)

    def test_pay(self):
        price = decimal.Decimal('150.00')
        vat = price * decimal.Decimal("0.25")
        product = products_and_price(price=price).skus.all()[2]
        order_paid_receiver_mock = mock.MagicMock()
        signals.order_paid.connect(order_paid_receiver_mock)
        order_data = {
            'email': 'test@test.com',
            'items': [{
                'quantity': 1,
                'price': str(price),
                'vat': vat,
                'description': 'purchase',
                'product': product.id,
            }]
        }
        response = self.client.post(
            reverse('order-detail'),
            order_data,
        )
        self.assertEqual(201, response.status_code, response.content)
        order_data = response.data
        response = self.client.post(
            reverse(
                'order-pay',
                args=['emailinvoice.emailinvoice']
            ),
            {
                'email': '',
                'order': order_data,
            }
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, order_paid_receiver_mock.call_count)

        order_data['items'][0]['quantity'] = 2
        response = self.client.post(
            reverse(
                'order-pay',
                args=['emailinvoice.emailinvoice']
            ),
            {
                'email': 'tester@test.com',
                'order': order_data,
            }
        )
        self.assertEqual(
            201,
            response.status_code,
            response.content
        )
        self.assertEqual(1, order_paid_receiver_mock.call_count)
        total = (price * 2 + vat * 2).quantize(decimal.Decimal('0.01'))
        self.assertEqual(str(total), response.data['owed'])
        self.assertEqual(str(total), response.data['paid'])
        invoice = EmailInvoice.objects.get()
        self.assertEqual(
            'tester@test.com',
            invoice.email,
        )
        self.assertEqual(
            total,
            invoice.owed,
        )
        order_paid_receiver_mock.assert_called_with(
            sender=views.InvoiceCreateView,
            invoice=invoice,
            signal=signals.order_paid,
        )
        self.assertEqual(
            models.Order.STATUS.paid,
            invoice.order.status
        )

    def test_pay_with_invalid_order_data(self):
        custom_validator = mock.MagicMock()
        custom_validator.side_effect = serializers.serializers.ValidationError('test error')
        signals.validate_custom_order_field.connect(
            custom_validator
        )
        custom = {'hej': 1}
        response = self.client.post(
            reverse(
                'order-pay',
                args=['emailinvoice.emailinvoice']
            ),
            {
                'email': 'tester@test.com',
                'order': {
                    'email': 'fel',
                    'custom': custom,
                },
            }
        )
        self.assertEqual(400, response.status_code)
        custom_validator.assert_called_once_with(
            sender=serializers.OrderSerializer,
            value=custom,
            signal=signals.validate_custom_order_field
        )


class TransactionTest(test.APITestCase):

    def setUp(self):
        self.product = products_and_price().skus.all()[0]
        self.order_data = {
            'email': 'test@test.com',
            'items': [{
                'quantity': 1,
                'price': str(self.product.price.amount),
                'vat': self.product.vat_amount,
                'description': 'purchase',
                'product': self.product.id,
            }]
        }

    def post_pay(self):
        return self.client.post(
            reverse(
                'order-pay',
                args=['emailinvoice.emailinvoice']
            ),
            {
                'email': 'test@test.com',
                'order': self.order_data,
            }
        )


    @mock.patch('paymentmethods.emailinvoice.models.EmailInvoice.authorize')
    def test_auth_throws(self, authmock):
        authmock.side_effect = exceptions.PaymentFailed()
        response = self.post_pay()
        self.assertEqual(402, response.status_code, response.content)
        order = models.Order.objects.get()
        self.assertEqual(order.STATUS.cart, order.status)


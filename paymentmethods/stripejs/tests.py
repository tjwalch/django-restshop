import decimal
from unittest import mock

from django.conf import settings
from django.test import modify_settings
from rest_framework import test
from rest_framework.reverse import reverse
import stripe

from restshop import serializers
from restshop.models import Order
from paymentmethods.stripejs.models import StripeInvoice
import restshop.exceptions
from restshop.tests.test_product import products_and_price


@modify_settings(INSTALLED_APPS={
    'append': 'restshop.paymentmethods.stripejs'
})
class StripeTest(test.APITestCase):

    def setUp(self):
        stripe.api_key = settings.STRIPE_API_KEY
        self.order = Order.objects.create(
            email='tester@test.com',
        )
        self.order.items.create(
            description='test purchase',
            price='1000',
            vat='250',
            quantity=3,
            product=products_and_price(1000).skus.all()[0]
        )
        session = self.client.session
        session['order_id'] = self.order.pk
        session.save()

    def get_token(self):
        return stripe.Token.create(card={
            "number": '4242424242424242',
            "exp_month": 12,
            "exp_year": 2016,
            "cvc": '123'
        }).id

    def test_pay(self):
        response = self.client.post(
            reverse(
                'order-pay',
                args=['stripejs.stripeinvoice']
            ),
            {
                'stripeToken': self.get_token(),
                'order': serializers.OrderSerializer(instance=self.order).data
            }
        )
        self.assertEqual(201, response.status_code, response.data)
        self.assertEqual(0,
                         decimal.Decimal(response.data['owed']) -
                         decimal.Decimal(response.data['paid']))
        order = Order.objects.get()
        self.assertEqual(
            Order.STATUS.completed,
            order.status
        )
        self.assertEqual(
            decimal.Decimal('3750.00'),
            order.invoices.all()[0].paid
        )

    @mock.patch('stripe.Charge.create')
    def test_card_error(self, create_mock):
        create_mock.side_effect = stripe.CardError('fail!', '', '402')
        si = StripeInvoice.objects.create(
            order=self.order,
            owed=self.order.amount,
            stripeToken=self.get_token(),
        )
        try:
            si.authorize()
        except restshop.exceptions.PaymentFailed as e:
            self.assertEqual('fail!', e.detail)
        else:
            self.assertRaises(restshop.exceptions.PaymentFailed, lambda: None)

    def test_cancel_auth(self):
        si = StripeInvoice.objects.create(
            order=self.order,
            owed=self.order.amount,
            stripeToken=self.get_token(),
        )
        self.assertRaises(
            restshop.exceptions.InvalidOperation,
            si.cancel_auth
        )
        self.assertTrue(si.authorize())
        self.assertTrue(si.cancel_auth())
        si.refresh_from_db()
        self.assertEqual(2, si.events.all().count())
        self.assertEqual(StripeInvoice.STATUS.canceled, si.status)

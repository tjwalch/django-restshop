# -*- coding: utf-8 -*-
from datetime import datetime
import decimal
import moneyed

from rest_framework import test
from django.core.exceptions import ValidationError
from rest_framework.reverse import reverse
from djasmine.testcase import JasmineRunnerTestCase

from restshop.models import Product, StockKeepingUnit, Price, VAT
from selenium.webdriver.phantomjs.webdriver import WebDriver


class ProductTest(test.APITestCase):

    def test_create_product_and_alternatives(self):
        product = Product.objects.create(
            attributes=['size'],
            name='TestCase',
            description='A tool to check things.'
        )
        StockKeepingUnit.objects.bulk_create(
            [
                StockKeepingUnit(
                    product=product,
                    attributes={
                        'size': size,
                    }
                ) for size in ('small', 'medium', 'large')
            ]
        )
        self.assertRaises(
            ValidationError,
            StockKeepingUnit(
                product=product,
                attributes={}
            ).clean
        )

    def test_prices(self):
        product = products_and_price()

        p = StockKeepingUnit.objects.get(
            product=product,
            attributes__size='large',
        )
        self.assertEqual(
            moneyed.Money(100, 'SEK'),
            p.price,
        )
        salesprice = Price.objects.create(
            amount=50,
            start=datetime(2015,11,1),
        )
        p = StockKeepingUnit.objects.get(
            product=product,
            attributes__size='small',
        )
        p.prices.add(salesprice)
        self.assertEqual(
            moneyed.Money(50, 'SEK'),
            p.price,
        )

    def test_product_view(self):
        product = products_and_price()
        response = self.client.get(
            reverse('product-list')
        )
        self.assertEqual(1, len(response.data))
        self.assertEqual(3, len(response.data[0]['skus']))
        self.assertEqual('100.00 Skr', response.data[0]['skus'][0]['price'])
        product.active = False
        product.save()
        response = self.client.get(
            reverse('product-list')
        )
        self.assertEqual(0, len(response.data))


def products_and_price(price=100):
    product = Product.objects.create(
        attributes=['size'],
        name='TestCase',
        description='A tool to check things.'
    )
    price = Price.objects.create(
        amount=price,
        vat=VAT.objects.create(
            description='standard',
            rate=decimal.Decimal('25.0')
        )
    )
    for size in ('small', 'medium', 'large'):
        a = StockKeepingUnit.objects.create(
            product=product,
            attributes={
                'size': size,
            },
        )
        a.prices.add(price)
    return product


class ProductJSTest(JasmineRunnerTestCase):
    webdriver = WebDriver

    def test_product_resource(self):
        products_and_price()
#        self.assertSpecPasses('product_test.spec.js')
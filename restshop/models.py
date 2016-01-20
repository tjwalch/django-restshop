# -*- coding: utf-8 -*-
import random
from datetime import date
import decimal
from stdnum import luhn

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.validators import KeysValidator
from django.contrib.postgres import fields as pg_fields
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel, TimeFramedModel, StatusModel
from model_utils.managers import QueryManager, InheritanceManager
from model_utils import Choices
from django_countries.fields import CountryField
from djmoney.models.fields import CurrencyField
from djmoney.models.fields import MoneyField

from restshop import fields


############## Products ##################
class Product(TimeStampedModel):
    active = models.BooleanField(
        default=True,
    )
    attributes = pg_fields.ArrayField(
        models.CharField(
            max_length=40,
            blank=True,
        ),
        help_text=_('These define the variations that will become available. One per line.'),
        blank=True,
        default=list,
    )
    caption = models.CharField(
        max_length=80,
        blank=True,
        default='',
    )
    description = models.TextField(
        blank=True,
        default='',
    )
    name = models.CharField(
        max_length=40,
    )

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        super().save(**kwargs)
        for sku in self.skus.all():
            attrs = sku.attributes.copy()
            for key in sku.attributes:
                if key not in self.attributes:
                    del attrs[key]
            if attrs != sku.attributes:
                sku.update(attributes=attrs)


#  "package_dimensions": null,
#  "shippable": true,
#    "images": [
# "url": null


class VAT(models.Model):
    description = models.CharField(
        _('description'),
        max_length=40,
        help_text=_('Description of your choosing to remember what this rate is used for'),
    )
    rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text=_('VAT rate %'),
    )

    class Meta:
        verbose_name = _('VAT rate')
        verbose_name_plural = _('VAT rates')

    def __str__(self):
        return '%s, %s%%' % (self.description, self.rate)


class Price(TimeFramedModel):
    amount = MoneyField(
        _('price excluding VAT'),
        max_digits=8,
        decimal_places=2,
    )
    vat = models.ForeignKey(
        VAT,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_('VAT'),
    )
    is_sale = models.BooleanField(
        _('this is a sales price'),
        default=False,
    )

    def __str__(self):
        return '%s (%s - %s)' % (self.amount, self.start, self.end)

    @property
    def vat_amount(self):
        if self.vat:
            return self.amount.amount * (self.vat.rate/100)
        else:
            return decimal.Decimal(0)


# SKU
class StockKeepingUnit(TimeStampedModel):
    _active = models.BooleanField(
        _('active'),
        default=True,
    )
    attributes = pg_fields.HStoreField(
        default=dict,
    )
#  "image": null,
    initial_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
 # "package_dimensions": null,
    product = models.ForeignKey(
        Product,
        related_name='skus',
    )
    prices = models.ManyToManyField(
        Price,
        related_name='products',
    )

    active = QueryManager(
        _active=True,
        product__active=True
    )
    objects = models.Manager()

    class Meta:
        unique_together = (
            ('attributes', 'product'),
        )

    def __str__(self):
        return str(self.product) + ': ' + '-'.join(
            self.attributes.values()
        )

    def delete(self, using=None, keep_parents=False):
        if self.orderitem_set.all().exists():
            self._active = False
            self.save(
                using=using,
                update_fields=['_active']
            )
            return 0
        else:
            return super().delete(using, keep_parents)

    @property
    def is_active(self):
        return self._active and self.product.active

    @cached_property
    def _price(self):
        return Price.timeframed.filter(
            products=self,
            amount_currency=settings.DEFAULT_CURRENCY,
        ).order_by(
            '-start',
            'id',
        ).last()

    @property
    def price(self):
        return (self._price is not None) and self._price.amount

    @property
    def vat_amount(self):
        return (self._price is not None) and self._price.vat_amount

    def clean(self):
        KeysValidator(
            keys=self.product.attributes,
            strict=True,
        )(self.attributes)


class Address(models.Model):
    company = models.CharField(
        _('company'),
        max_length=80,
        blank=True,
        default='',
    )
    first_name = models.CharField(
        _('first name'),
        max_length=80
    )
    last_name = models.CharField(
        _('last name'),
        max_length=80,
    )
    street_address_1 = models.TextField(
        _('street address line 1')
    )
    street_address_2 = models.TextField(
        _('street address line 2'),
        blank=True,
        default='',
    )
    postal_code = models.CharField(
        _('postal code'),
        max_length=20
    )
    city = models.CharField(
        _('city'),
        max_length=80
    )
    country = CountryField(
        _('country'),
        blank=True,
        default='',
    )
    state = models.CharField(
        _('state'),
        max_length=2,
        blank=True,
        default='',
    )


class Order(TimeStampedModel, StatusModel):
    STATUS = Choices(
        'cart',
        'confirmed',
        'paid',
        'canceled',
        'completed',
        'refunded',
    )
    billing_address = models.ForeignKey(
        Address,
        null=True,
        blank=True,
        related_name='+',
    )
    shipping_address = models.ForeignKey(
        Address,
        null=True,
        blank=True,
        related_name='+',
    )
    currency = CurrencyField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        verbose_name=_('user'),
        related_name='orders',
        on_delete=models.SET_NULL,
    )
    email = models.EmailField(
        _('email address'),
        blank=True,
        default='',
    )
    custom = pg_fields.JSONField(
        _('custom order data'),
        blank=True,
        default=dict,
    )

    def get_amount(self):
        zero = decimal.Decimal('0.00')
        return max((self.items.aggregate(
            sum=models.Sum(((
                models.F('price') +
                models.F('vat') -
                models.Func(
                    models.F('discount'),
                    function='ABS'
                )) * models.F('quantity')),
                output_field=models.DecimalField()
            )
        )['sum'] or zero), zero)
    get_amount.short_description = _('amount')
    amount = property(get_amount)

    def get_order_no(self):
        return (self.id * 10) + int(luhn.calc_check_digit(self.id))
    get_order_no.short_description = _('order number')
    order_no = property(get_order_no)

    def get_remainder(self):
        return self.amount - (self.invoices.filter(
            status__in=('authorized', 'captured')
        ).aggregate(
            sum=models.Sum(
                models.F('paid')
            )
        )['sum'] or decimal.Decimal('0.00'))
    get_remainder.short_description = _('remainder')
    remainder = property(get_remainder)


class OrderItemManager(QueryManager):

    def create(self, **kwargs):
        product = kwargs.get('product')
        if product:
            kwargs.setdefault('price', product.price)
            kwargs.setdefault('description', str(product))
        return super().create(**kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
    )
    description = models.CharField(
        max_length=128,
        blank=True,
    )
    quantity = models.IntegerField()
    item_types = Choices(
        'sku',
        'discount',
        'shipping_fee',
        'invoice_fee',
        'reminder_fee',
        'interest_fee',
    )
    item_type = models.CharField(
        max_length=max(len(i[0]) for i in item_types),
        default='sku',
        choices=item_types,
    )
    product = models.ForeignKey(
        StockKeepingUnit,
        verbose_name=_('product'),
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    price = fields.MoneyField(
        _('line item price'),
        default=0,
        help_text=_('Line item price excl. tax'),
    )
    discount = fields.MoneyField(
        _('line item discount'),
        default=0,
        help_text=_('Discount excl. tax'),
    )
    vat = fields.MoneyField(
        _('line item VAT'),
        default=0,
    )
    vat_rate = models.DecimalField(
        _('line item VAT rate %'),
        max_digits=4,
        decimal_places=2,
        default=0,
    )

    objects = OrderItemManager().select_related('order')

    class Meta:
        unique_together = (
            ('order', 'product'),
        )

    @property
    def amount(self):
        return (self.price +
                self.vat -
                abs(self.discount)
                ) * self.quantity


############## INVOICE (PAYMENT ATTEMPTS) ####################

class Invoice(TimeStampedModel, StatusModel):
    """An Invoice represents an attempt to retrieve payment from customer.

    """
    STATUS = Choices(
        'pending',
        'authorized',
        'captured',
        'canceled',
        'refunded',
        'failed',
    )
    order = models.ForeignKey(
        Order,
        related_name='invoices',
    )
    owed = fields.MoneyField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )
    paid = fields.MoneyField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    objects = InheritanceManager()

    def __str__(self):
        return str(self.name)

    def prepare(self):
        return False

    def authorize(self):
        return False

    def capture(self):
        return False

    def cancel_auth(self):
        return False

    def credit(self):
        return False

    def refund(self):
        return False


class InvoiceEvent(TimeStampedModel):
    """An event represents the result of trying to retrieve funds from customer or other action taken.
    Can be e g a payment or a refund
    """
    invoice = models.ForeignKey(
        Invoice,
        related_name='events',
    )
    transaction_id = models.CharField(
        _('transaction ID'),
        max_length=50,
        db_index=True,
        help_text=_(
            'Unique ID identifying this payment in the foreign system.'
        )
    )
    data = pg_fields.JSONField(
        _('data'),
        blank=True,
        help_text=_('JSON-encoded additional data about the event.'),
    )


############# DISCOUNTS #################

# Nearly all letters and digits, excluding those which can be easily confounded
RANDOM_CODE_CHARACTERS = (
    '23456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ')


def generate_random_code():
    return u''.join(random.sample(RANDOM_CODE_CHARACTERS, 10))


class AvailableDiscountsManager(InheritanceManager):

    pass


class DiscountBase(models.Model):
    code = models.CharField(
        _('code'),
        max_length=30,
        unique=True,
        default=generate_random_code,
    )
    is_active = models.BooleanField(
        _('is active'),
        default=True
    )
    valid = pg_fields.DateRangeField(
        _('validity range'),
        default=(
            date.today,
            None
        )
    )
    allowed_uses = models.IntegerField(
        _('number of allowed uses'),
        blank=True,
        null=True,
        help_text=_(
            'Leave empty if there is no limit on the number of uses'
            ' of this discount.'))
    used = models.IntegerField(
        _('number of times already used'),
        default=0
    )
    amount = MoneyField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    objects = InheritanceManager()

    class Meta:
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')

    def apply_to_order(self, order):
        raise NotImplementedError(
            'Subclasses need to provide an "apply_to_order" method.'
        )

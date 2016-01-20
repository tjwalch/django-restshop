# -*- coding: utf-8 -*-
import decimal
import functools
import uuid

import stripe
import stripe.error
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions as api_exceptions

from restshop import models as shopmodels
from restshop import exceptions


def stripe_errors_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except stripe.error.RateLimitError as e:
            raise api_exceptions.Throttled(detail=e._message)
        except stripe.error.APIConnectionError as e:
            raise exceptions.PaymentGatewayUnavailable(detail=e._message)
        except stripe.error.InvalidRequestError as e:
            raise api_exceptions.ValidationError(detail=e.json_body)
        except stripe.StripeError as e:
            raise exceptions.PaymentFailed(detail=e._message)
    return wrapper


class StripeInvoice(shopmodels.Invoice):

    name = _('Stripe')

    stripeToken = models.CharField(
        max_length=80,
    )
    idempotency_key = models.UUIDField(
        editable=False,
        default=uuid.uuid4,
    )

    def __init__(self, *args, **kwargs):
        stripe.api_key = settings.STRIPE_API_KEY
        super().__init__(*args, **kwargs)

    def save(self, **kwargs):
        self.idempotency_key = uuid.uuid4()
        super().save(**kwargs)

    @stripe_errors_handler
    def authorize(self):
        try:
            charge = stripe.Charge.create(
                amount=int(self.owed * 100),
                currency=str(self.order.currency),
                source=self.stripeToken,
                capture=False,
                description='',
                receipt_email=self.order.email,
                metadata={
                    'email': self.order.email,
                    'invoice_id': self.pk,
                },
                idempotency_key=str(self.idempotency_key),
            )
        except stripe.CardError as e:
            #TODO: log error
            self.status = self.STATUS.failed
            self.save()
            raise exceptions.PaymentFailed(detail=e._message)

        self.current_event = self.events.create(
            transaction_id=charge.id,
            data=charge.to_dict(),
        )
        if charge.status == 'succeeded' and charge.paid:
            self.status = self.STATUS.authorized
            self.paid = decimal.Decimal(charge.amount / 100)
        self.save()
        return True

    def capture(self):
        charge = stripe.Charge.retrieve(
            self.current_event.transaction_id
        )
        charge.capture(
            idempotency_key=str(self.idempotency_key),
        )
        self.current_event.data = charge.to_dict()
        self.current_event.save()
        if charge.captured:
            self.status = self.STATUS.captured
            self.save()
            return True
        return False

    def cancel_auth(self):
        if self.status != self.STATUS.authorized:
            raise exceptions.InvalidOperation(detail='Invalid operation')
        refund = stripe.Refund.create(
            charge=self.current_event.transaction_id,
            idempotency_key=str(self.idempotency_key),
        )
        self.events.create(
            transaction_id=refund.id,
            data=refund.to_dict(),
        )
        self.status = self.STATUS.canceled
        self.save()
        return True

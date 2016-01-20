# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, status


class RestShopException(exceptions.APIException):
    pass


class PaymentFailed(RestShopException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = _('payment unsuccessful')


class PaymentGatewayUnavailable(RestShopException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _('payment gateway unavailable')


class InvalidOperation(RestShopException):
    pass


class ResourceConflict(exceptions.ValidationError):
    status_code = status.HTTP_409_CONFLICT


class DoublePayment(RestShopException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('payment already started for this order')

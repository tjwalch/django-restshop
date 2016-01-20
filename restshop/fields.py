# -*- coding: utf-8 -*-
from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from model_utils import Choices


MoneyField = curry(
    models.DecimalField,
    max_digits=18,
    decimal_places=2,
)

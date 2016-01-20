# -*- coding: utf-8 -*-
from stdnum import luhn
from django.db import models
from django.utils.translation import ugettext_lazy as _
import restshop.models


class EmailInvoice(restshop.models.Invoice):

    name = _('Email Invoice')

    email = models.EmailField()
    billing_address = models.ForeignKey(
        restshop.models.Address,
        null=True,
        on_delete=models.PROTECT,
    )

    @property
    def invoice_no(self):
        return luhn.checksum()

    def authorize(self, **kwargs):
        self.paid=self.owed
        self.save()
        return True

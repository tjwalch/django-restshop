# -*- coding: utf-8 -*-
from django.dispatch import Signal


validate_custom_order_field = Signal(
    providing_args=[
        'value',
    ]
)


order_paid = Signal(
    providing_args=[
        'invoice',
    ]
)

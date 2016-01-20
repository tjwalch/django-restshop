# -*- coding: utf-8 -*-
import json
from django import forms
from django.contrib.postgres import forms as pg_forms
from restshop import models


class ProductForm(forms.ModelForm):

    class Meta:
        model = models.Product
        fields = (
            'name',
            'attributes',
            'description',
            'active',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attributes'].widget = forms.Textarea(attrs={})
        self.fields['attributes'].delimiter = '\n'

    def clean_attributes(self):
        delimiter = self.fields['attributes'].delimiter
        data = delimiter.join(
            self.cleaned_data['attributes']
        ).splitlines()
        return [p.strip() for p in data]


class SKUForm(forms.ModelForm):
    attributes = pg_forms.HStoreField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = models.StockKeepingUnit
        fields = (
            'initial_quantity',
            'prices',
            '_active',
            'attributes',
        )

    def clean(self):
        attrs = {field: self.cleaned_data.get(field, '')
                 for field in self.cleaned_data['product'].attributes}
        self.cleaned_data['attributes'] = json.dumps(attrs)
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            kwargs.setdefault('initial', {})
            for attr, value in instance.attributes.items():
                kwargs['initial'][attr] = value
        super().__init__(*args, **kwargs)

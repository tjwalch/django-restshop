from django.contrib import admin

from . import models
from django import forms as django_forms
from restshop import forms


class SKUInline(admin.TabularInline):
    model = models.StockKeepingUnit
    extra = 1
    form = forms.SKUForm

    def get_formset(self, request, obj=None, **kwargs):
        if obj:
            self.form = type(
                'DynSKUForm',
                (forms.SKUForm, ),
                {attr: django_forms.CharField(
                        label=attr,
                        max_length=100,
                        required=True
                    ) for attr in obj.attributes
                }
            )
        return super().get_formset(request, obj, **kwargs)


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    form = forms.ProductForm
    inlines = [SKUInline, ]
    list_display = (
        'name',
        'attributes',
    )


admin.site.register(models.VAT)


@admin.register(models.Price)
class PriceAdmin(admin.ModelAdmin):
    fields = list_display = list_editable = (
        'amount',
        'start',
        'end',
    )


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_no',
        'created',
        'modified',
        'amount',
        'remainder',
        'status',
    )
    list_filter = (
        'status',
    )
    inlines = (
        OrderItemInline,
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from rest_framework import serializers, fields
from restshop import signals, models


class SKUSerializer(serializers.ModelSerializer):
    price = serializers.CharField()

    class Meta:
        model = models.StockKeepingUnit
        fields = (
            'id',
            'attributes',
            'price',
            'vat_amount',
        )


class ProductSerializer(serializers.ModelSerializer):
    skus = SKUSerializer(many=True)

    class Meta:
        model = models.Product
        fields = (
            'id',
            'name',
            'description',
            'attributes',
            'skus',
        )


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=models.StockKeepingUnit.active,
        allow_null=True,
    )
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = models.OrderItem
        fields = (
            'id',
            'description',
            'quantity',
            'price',
            'vat',
            'discount',
            'product',
            'item_type',
        )

    def to_internal_value(self, data):
        """Workaround to enable updating nested items"""
        ret = super().to_internal_value(data)
        id_field = self.fields['id']
        id_value = id_field.get_value(data)
        if id_value != fields.empty:
            ret['id'] = id_value
        return ret

    def validate(self, attrs):
        if attrs.get('item_type', 'sku') == 'sku':
            product = attrs.get('product')
            if not product:
                raise serializers.ValidationError(
                    {'product': _("this field is required for sku items")}
                )
            errors = {}
            if attrs['price'] != product.price.amount:
                errors['price'] =  _('value does not match product catalogue price')
            if attrs['vat'] != product.vat_amount:
                errors['vat'] = _('value does not match product catalogue VAT amount')
            if errors:
                raise serializers.ValidationError(errors)

        return attrs


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    custom = serializers.DictField(required=False)

    class Meta:
        model = models.Order
        fields = (
            'currency',
            'email',
            'items',
            'amount',
            'custom',
        )
        read_only_fields = (
            'currency',
            'amount',
        )

    def create(self, validated_data):
        items = validated_data.pop('items', [])
        user = self.context['request'].user
        if user.is_authenticated():
            validated_data['user'] = user
        order = models.Order.objects.create(
            **validated_data
        )
        models.OrderItem.objects.bulk_create(
            models.OrderItem(order=order, **data) for data in items
        )
        return order

    def update(self, instance, validated_data):
        items = validated_data.pop('items', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        for item in items:
            id = item.pop('id', None)
            models.OrderItem.objects.update_or_create(
                order_id=instance.pk,
                id=id,
                defaults=item,
            )
        return instance

    def validate_custom(self, value):
        result = signals.validate_custom_order_field.send_robust(
            self.__class__,
            value=value,
        )
        errors = []
        for receiver, response in result:
            if isinstance(response, serializers.ValidationError):
                errors.extend(response.detail)
            elif isinstance(response, Exception):
                raise response
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def run_validation(self, data=fields.empty):
        # workaround to be able to use nested serializer in updates
        self._validated_data = super().run_validation(data)
        return self._validated_data


def invoiceserializer_factory(mdl):
    class InvoiceSerializer(serializers.ModelSerializer):
        order = OrderSerializer(required=True)

        class Meta:
            model = mdl

    return InvoiceSerializer

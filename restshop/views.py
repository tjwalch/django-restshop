# -*- coding: utf-8 -*-
from django.apps import apps
from django.db.models import Prefetch
from django.db import transaction

from rest_framework import (
    viewsets,
    mixins,
    generics,
    response,
    views,
)

from restshop import (
    serializers,
    signals,
    models,
    exceptions,
)


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        self.kwargs['pk'] = self.request.session.get('order_id')
        if self.request.method == 'GET':
            return models.Order.cart.prefetch_related(
                Prefetch(
                    'items',
                    models.OrderItem.objects.select_related(
                        'product',
                    ),
                )
            ) # no order in session -> 412 Precondition failed
        return models.Order.cart.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        self.request.session['order_id'] = instance.pk


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.OrderItemSerializer

    def get_queryset(self):
        return models.OrderItem.objects.filter(
            order_id=self.request.session.get('order_id'),
        )


class InvoiceCreateView(generics.CreateAPIView):

    def get_serializer_class(self):
        model = apps.get_model(
            *self.kwargs['model_label'].split('.')
        )
        return serializers.invoiceserializer_factory(
            model
        )

    # todo throttle
    @transaction.non_atomic_requests
    def perform_create(self, serializer):
        # maybe this order update part should be moved to serializer,,,
        try:
            order = serializer.fields['order'].update(
                models.Order.objects.get(
                    pk=self.request.session.get('order_id')
                ),
                serializer.validated_data['order'],
            )
            if order.status != models.Order.STATUS.cart:
                raise exceptions.DoublePayment()
        except models.Order.DoesNotExist:
            order = serializer.fields['order'].create(
                serializer.validated_data['order'],
            )
        invoice = serializer.save(
            order=order,
            owed=order.amount,
        )

        # Payment Flow
        def set_order_status(status):
            order.status = status
            order.save()

        with transaction.atomic():
            invoice.prepare()
            order.status = order.STATUS.confirmed
            invoice.authorize()
            set_order_status(order.STATUS.paid)
        try:
            signals.order_paid.send(
                sender=self.__class__,
                invoice=invoice,
            )
        except:  # Too wide?
            with transaction.atomic():
                invoice.cancel_auth()
                set_order_status(order.STATUS.canceled)
            raise
        else:
            with transaction.atomic():
                if invoice.capture():  # return false if actual capture is postponed, e g with bulk or invoice payments
                    set_order_status(order.STATUS.completed)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.ProductSerializer
    queryset = models.Product.objects.filter(
        active=True,
    ).prefetch_related(
        Prefetch(
            'skus',
            models.StockKeepingUnit.objects.filter(
                _active=True,
            )
        )
    )


class PaymentproviderListView(views.APIView):
    # the "params" empty dict is just for js convenience
    paymentproviders = [
        {'key': cls._meta.label_lower,
         'name': cls.name,
         'params': {}} for cls in
        models.Invoice.__subclasses__()
    ]

    def get(self, request):
        return response.Response(self.paymentproviders)

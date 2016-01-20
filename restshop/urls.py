# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import include, url
from rest_framework import routers
from restshop import views
from restshop.router import OrderActionsRouter

order_router = OrderActionsRouter()
order_router.register('order', views.OrderViewSet, base_name='order')
simple_router = routers.SimpleRouter()
simple_router.register('products', views.ProductViewSet)
simple_router.register('order/items', views.OrderItemViewSet, base_name='items')


urlpatterns = [
    url(r'order/invoices/(?P<model_label>' + r'|'.join(
                i['key'].replace('.', '\.') for i in
                views.PaymentproviderListView.paymentproviders
            ) + r')/',
        view=views.InvoiceCreateView.as_view(),
        name='order-pay'),
    url(r'', include(order_router.urls)),
    url(r'', include(simple_router.urls)),
    url(r'paymentproviders/$',
        views.PaymentproviderListView.as_view(),
        name='paymentprovider-list'),
]

if settings.DEV:
    urlpatterns += [
        url(r'djasmine/', include('djasmine.urls')),
    ]


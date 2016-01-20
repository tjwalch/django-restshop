# -*- coding: utf-8 -*-
from rest_framework import routers
from restshop import views


class OrderActionsRouter(routers.SimpleRouter):

    routes = [
        routers.Route(
            url=r'^{prefix}/$',
            mapping={
                'get': 'retrieve',
                'post': 'create',
                'patch': 'partial_update',
                'put': 'update',
            },
            name='{basename}-detail',
            initkwargs={'suffix': 'Detail'}
        ),
        routers.DynamicDetailRoute(
            url=r'^{prefix}/{methodnamehyphen}/$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
        routers.Route(
            url=r'{prefix}/pay/(?P<model_label>' + r'|'.join(
                i['key'].replace('.', '\.') for i in
                views.PaymentproviderListView.paymentproviders
            ) + r')/$',
            mapping={
                'post': 'pay',
            },
            name='{basename}-pay',
            initkwargs={'suffix': 'Detail'},
        )
    ]
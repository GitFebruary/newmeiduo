from django.conf.urls import url

from orders import views

urlpatterns = [
    url(r'^orders/settlement/$', views.OrdersShowGoodsView.as_view()),
    url(r'^orders/$', views.OrderSaveView.as_view()),
]
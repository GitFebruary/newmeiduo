from django.conf.urls import url
from goods import views
from rest_framework.routers import DefaultRouter

urlpatterns = [

    url(r'^categories/(?P<pk>\d+)/$', views.CategroiesView.as_view()),
    url(r'^categories/(?P<pk>\d+)/skus/$', views.SKUListView.as_view()),
]

router=DefaultRouter()
router.register('skus/search', views.SKUSearchView, base_name='skus_search')
urlpatterns += router.urls
from django.conf.urls import url
from oauth import views

urlpatterns = [
    url(r'^qq/authorization/', views.OauthLoginViewQQ.as_view()),
    url(r'^qq/user/', views.OauthView.as_view()),
]
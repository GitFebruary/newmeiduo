from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from users import views

urlpatterns = [
    # 发送短信验证
    url(r'^sms_codes/(?P<moblie>1[3-9]\d{9})/$', views.SmsCodeView.as_view()),

    # 校验用户名
    url(r'^usernames/(?P<username>\w+)/count/$', views.UserNameView.as_view()),

    # 校验手机号
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MoblieView.as_view()),

    # 注册
    url(r'^users/$', views.UserView.as_view()),

    # 登录
    url(r'^authorizations/$', views.UserLoginView.as_view()),

    # 显示用户信息
    url(r'^user/$', views.UserDetailView.as_view()),

    # 更新邮箱
    url(r'^email/$', views.EmailView.as_view()),

    # 校验邮箱有效性
    url(r'^emails/verification/$', views.EmailVerifyView.as_view()),

    # 保存用户浏览记录
    url(r'browse_histories/$', views.HistoriesView.as_view()),
]
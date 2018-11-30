from django_filters.conf import settings
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from QQLoginTool.QQtool import OAuthQQ
from rest_framework_jwt.settings import api_settings
from itsdangerous import TimedJSONWebSignatureSerializer as TJS
from oauth.models import OAuthQQUser
from oauth.serializers import OauthSerializers
# from settings.dev import QQ_CLIENT_ID, QQ_CLIENT_SECRET, QQ_REDIRECT_URI
from django.conf import settings

from users.utils import merge_cart_cookie_to_redis


class OauthLoginViewQQ(APIView):
    """
        构造qq登录的跳转链接

    """
    def get(self, request):

        # 获取前端发送的参数
        state = request.query_params.get('next', None)

        # 前端如果没有传递需要手动写入
        if state is None:
            state = '/'

        # 初始化QuathQQ对象
        qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET, redirect_uri=settings.QQ_REDIRECT_URI, state=state)

        # 构造qq登录页面的跳转链接
        login_url = qq.get_qq_url()

        # 返回结果
        return Response(
            {
            'login_url': login_url
            }
        )


class OauthView(CreateAPIView):

    def get(self, request):
        """
            获取openid
            思路分析:
            前端:
            1. 用户扫码成功之后,qq服务器会引导用户跳转到美多页面
            2. 前端通过js代码获取路径中的code(授权码)值, 并携带code值向后端发送请求
            后端:
            3. 获取code值,生成Access Token
        """
        # 获取code值
        AuthCode = request.query_params.get('code', None)

        # 判断AuthCode值是否存在
        if not AuthCode:
            return Response({'message': '缺少code值'}, status=400)

        # 通过code值获取token, 实例QQ对象
        qq = OAuthQQ(client_id=QQ_CLIENT_ID, client_secret=QQ_CLIENT_SECRET, redirect_uri=QQ_REDIRECT_URI, state='/')

        # 调用get_access_token方法获取token值
        access_token = qq.get_access_token(code=AuthCode)

        # 通过access_token获取openid
        openid = qq.get_open_id(access_token=access_token)

        # 判断操作
        try:
            # 查询表中是否有数据
            qq_user = OAuthQQUser.objects.get(openid=openid)
        except Exception as e:

            # 将openid进行加密操作,密文返回给前端
            tjs = TJS(settings.SECRET_KEY, 300)

            # 调用加密方法进行加密
            open_id = tjs.dumps({'openid': openid}).decode()

            # 报错,说明没有,跳转到绑定页面(access_token前端接收openid的变量)
            # 因为在绑定的时候需要openid与user一起绑定所以需要传递
            return Response({'access_token': open_id})

        else:
            # 没有报错说明已经绑定过,跳转到首页
            # 获取qq_user中的user对象
            user = qq_user.user
            # 因为是登录操作,所以需要生成token数据发送给前端
            # token加密
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            # user对象添加属性
            user.token = token

            response = Response(
                {
                    'token':token,
                    'username':user.username,
                    'user_id': user.id

                }
            )
            response = merge_cart_cookie_to_redis(request, response, user)
            return response


    # # 指明序列化器
    # serializer_class = OauthSerializers

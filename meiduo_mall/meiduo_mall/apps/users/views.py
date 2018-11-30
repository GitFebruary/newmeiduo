from random import randint
from django_redis import get_redis_connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework_jwt.views import ObtainJSONWebToken

from celery_tasks.sms.tasks import send_sms_code
from goods.models import SKU
from goods.serializers import SKUListSerializer
from users.serializers import UserSerializer, UserDetailSerializer, EmailSerializer, HistoriesSerializer
from users.models import User
from rest_framework.permissions import IsAuthenticated
from itsdangerous import TimedJSONWebSignatureSerializer as TJS
from django.conf import settings
import base64, pickle


# 发送短信视图
from users.utils import merge_cart_cookie_to_redis


class SmsCodeView(APIView):

    def get(self, request, moblie):

        """
        思路分析:
        01- 获取手机号, url获取
        02- 生成短信验证码
        03- 需要将生成的短信验证码与用户输入的短信验证码进行对比,并消除,所以需要保存到redis缓存中
        04- 发送短信验证码
        05- 返回数据
        :param request:
        :param moblie:
        :return:
        """

        # 生成验证码
        sms_code = "%06d" % randint(0, 999999)
        print(sms_code)
        # 创建连接到redis对象
        conn = get_redis_connection("sms_code")

        # 判断请求间隔是否在60秒之内
        flag = conn.get("sms_code_flag_" + moblie)
        if flag:
            return Response({'massage': "发送过于频繁"})

        # 保存到redis缓存中
        # 生成管道对象
        p = conn.pipeline()
        p.setex("sms_code_" + moblie, 300, sms_code)
        p.setex("sms_code_flag_" + moblie, 60, 123)
        p.execute()

        # # 保存验证码到redis缓存中
        # conn.setex("sms_code_" + moblie, 300, sms_code)
        # conn.setex("sms_code_flag_" + moblie, 60, 123)

        # # 发送短信
        # # 获取发送短信对象
        # ccp = CCP()
        # ccp.send_template_sms(moblie, [sms_code, '5'], 1)

        # 异步发送短信
        send_sms_code.delay(moblie, sms_code)

        # 返回结果
        return Response({'massage': 'OK'}, status=200)


# 验证用户名视图
class UserNameView(APIView):
    """
    请求方式: get
    请求路径: usernames/
    请求参数: name 路径传递
    返回结果: count
    思路分析:
        01- 获取请求参数
        02- 查询数据是否存在
        03- 返回结果
    """
    # 01 - 获取请求参数
    def get(self, request, username):
        # 02 - 查询数据是否存在
        count = User.objects.filter(username=username).count()
        # 03 - 返回结果
        return Response({'count': count})


# 验证手机号视图
class MoblieView(APIView):

    """
    请求方式: get
    请求路径: mobiles/
    请求参数: mobile 路径传递
    返回结果: count
    思路分析:
        01- 获取请求参数
        02- 查询数据是否存在
        03- 返回结果
    """
    # 01 - 获取请求参数
    def get(self, request, mobile):

        # 02 - 查询数据是否存在
        count = User.objects.filter(mobile=mobile).count()

        # 03 - 返回结果
        return Response({'count': count})


# 保存用户注册信息视图
class UserView(CreateAPIView):
    """
    请求方式: post
    请求路径: users/
    请求参数: mobile password password2 username sms_code allow 请求体
    返回结果: username mobile id
    思路分析:
        01- 获取请求参数
        02- 验证参数
        03- 反序列化保存数据
        04- 返回结果(序列化操作)
    """
    # 序列化器
    serializer_class = UserSerializer


# 显示用户信息视图
class UserDetailView(RetrieveAPIView):

    """
    请求方式: get
    请求路径: user
    请求参数: token
    返回结果: username mobile email email_active
    逻辑分析:
        获取请求参数
        查询对应user
        返回数据
    """

    # 获取token值,如果前端在请求头中携带了token值,那么配置文件中的JSONWebTokenAuthentication就会自动进行验证操作,并把user对象保存到request对象的其他属性中的user属性中
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# 更新邮箱视图
class EmailView(UpdateAPIView):

    serializer_class = EmailSerializer

    def get_object(self):

        return self.request.user


# 校验邮箱有效视图
class EmailVerifyView(APIView):

    """
    请求方式: get
    请求路径: emails/verification
    请求参数: token
    返回结果: ok
    思路分析:
        1. 获取token值
        2. 解密token值,获取用户值并查询
        3. 修改用户email.. 的值, 并保存
        4. 返回结果
    """
    # 获取前端数据
    def get(self, request):

        # 获取查询字符串数据
        token = request.query_params.get('token')

        # 解密操作,获取TJS对象
        tjs = TJS(settings.SECRET_KEY, 300)

        # 调用解密方法
        try:
            data = tjs.loads(token)
        except:
            return Response({'error': 'token值无效'})
        # 获取data中的值
        username = data['name']

        # 通过username获取对应的user
        user = User.objects.get(username=username)
        # user = self.request.user
        # 修改user中的值
        user.email_active = True
        user.save()

        # 返回数据给前端
        return Response({'message':'OK'})


# 保存用户浏览记录
class HistoriesView(CreateAPIView):

    serializer_class = HistoriesSerializer

    # 获取浏览记录方法
    def get(self, request):

        # 获取user对象
        user = request.user

        # 查询redis中的history
        conn = get_redis_connection('history')

        sku_ids = conn.lrange('history_%s'%user.id,0,6)

        # 查询数据对象
        skus = SKU.objects.filter(id__in=sku_ids)
        # 序列化返回
        ser = SKUListSerializer(skus, many=True)
        return Response(ser.data)


# 合并购物车视图
class UserLoginView(ObtainJSONWebToken):

    """
    接口分析
        请求方式: POST
        请求路径: authorizations/
        请求参数: token 登录时的数据
        返回结果: token user_id username
    思路分析
        1- 获取cookie中的数据
        2- 判断cookie中是否有数据, 如果没有直接返回
        3- 有数据, 进行解密操作
        4- 解密后判断解密后的字典是否为空, 如果为空直接返回
        5- 将数据拆分
            a. 字典对应的是redis中的hash类型
            b. 列表对应的是redis中的set类型
        6- 获取redis对象
        7- 将拆分后的数据保存到redis中的hash与set中
        8- 删除cookie中的数据
        9- 返回结果
    """
    # 重写登录时的post请求方法
    def post(self, request, *args, **kwargs):

        # 原有的登录功能不变,调用父类方法
        response = super().post(request, *args, **kwargs)
        # 获取user
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.object.get('user') or request.user

        response = merge_cart_cookie_to_redis(request, response, user)
        # 返回数据
        return response


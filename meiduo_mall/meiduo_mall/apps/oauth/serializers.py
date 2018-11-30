import re
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings
from oauth.models import OAuthQQUser
from users.models import User
from itsdangerous import TimedJSONWebSignatureSerializer as TJS
from django.conf import settings
from django_redis import get_redis_connection


# 定义保存用户序列化器
class OauthSerializers(serializers.ModelSerializer):
    # 指明字段
    # 反序列化字段
    sms_code = serializers.CharField(max_length=6, min_length=6, write_only=True)
    access_token = serializers.CharField(write_only=True)
    # 序列化字段
    user_id = serializers.IntegerField(read_only=True)
    token = serializers.CharField(read_only=True)

    mobile = serializers.CharField(max_length=11)

    class Meta:
        model = User
        fields = ('mobile', 'password', 'sms_code', 'access_token', 'username', 'user_id', 'token')
        # 选项参数
        extra_kwargs = {
            'password':{
                'write_only': True,
                'max_length': 20,
                'min_length': 8,
            },
            'username':{
                'read_only': True
            },
        }

    # 字段逻辑验证(手机号格式验证)
    def validate_mobile(self, value):
        # 这里手机号验证验证的是以及注册过的数据,所以只需要验证格式
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')

        return value

    # 字段逻辑验证
    def validate(self, attrs):
        # 验证access_token是否正确 即解密操作
        tjs = TJS(settings.SECRET_KEY, 300)
        try:
            # 调用解密方法
            data = tjs.loads(attrs['access_token'])
        except :
            raise serializers.ValidationError('无效的access_token值')

        # 取出openid
        openid = data.get('openid')
        # 添加到验证后的数据中
        attrs['openid'] = openid

        # 验证短信验证码
        # 1. 获取redis对象
        conn = get_redis_connection('sms_code')
        # 2. 获取短信验证码
        rel_sms_code = conn.get("sms_code_" + attrs['mobile'])
        # 3. 判断验证码是否过期
        if not rel_sms_code:
            raise serializers.ValidationError('短信验证码过期')
        # 4. 将redis中的验证码与用户输入的验证码进行比较
        if rel_sms_code.decode() != attrs['sms_code']:
            raise serializers.ValidationError('短信验证码有误')
        print(rel_sms_code)

        # 判断手机号对应的用户是否存在
        try:
            user = User.objects.get(mobile=attrs['mobile'])
        except:
            # 不存在,说明没有注册,进行注册操作,注册操作需要爱create方法中进行
            return attrs
        else:
            # 存在说明已经注册
            # 验证密码是否正确
            if not user.check_password(attrs['password']):
                raise serializers.ValidationError('密码错误')

            # 添加用户到以验证的数据中
            attrs['user'] = user
            # 返回添加了用户的已验证信息
            return attrs

    def create(self, validated_data):

        user = validated_data.get('user', None)
        # 判断用户是否注册过,通过validated_data是否有user值进行判断
        if not user:
            # 没有注册过进行注册操作
            user = User.objects.create_user(username=validated_data['mobile'], password=validated_data['password'], mobile=validated_data['mobile'])

        # 如果以及存在,进行绑定操作,也就是绑定openid
        OAuthQQUser.objects.create(user=user, openid=validated_data['openid'])

        # jwt加密
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # user中添加token值
        user.token=token
        user.user_id=user.id

        return user


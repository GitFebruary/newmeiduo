import re
from rest_framework import serializers
from django_redis import get_redis_connection
from goods.models import SKU
from users.models import User
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as TJS
from celery_tasks.emails.tasks import send_email


# 注册序列化器
class UserSerializer(serializers.ModelSerializer):
    sms_code = serializers.CharField(max_length=6, min_length=6, write_only=True)
    password2 = serializers.CharField(max_length=20, min_length=6, write_only=True)
    allow = serializers.CharField(write_only=True)
    # 定义一个字段,token字段是为了响应给前端,所以添加的
    token = serializers.CharField(read_only=True)

    # 根据模型类自动生成字段
    class Meta:
        model = User
        fields = ('username', 'password', 'mobile', 'id', 'sms_code', 'password2', 'allow', 'token')

    # 手动设置username约束
    extra_kwargs = {
        'password':{
            'max_length': 20,
            'min_length': 8,
            'write_only': True
        },
        'username':{
            'max_length': 20,
            'min_length': 5,
        },
    }

    # 单一验证协议操作
    def validate_allow(self, value):

        if not value == 'true':
            raise serializers.ValidationError('协议未通过')
        return value

    # 单一验证手机号格式操作
    def validate_mobile(self, value):

        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')

        return value

    def validate(self, attrs):
        # 验证密码是否一致
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次输入密码不一致')

        # 验证短信验证码是否一致
        # 获取redis连接对象
        conn = get_redis_connection('sms_code')

        # 获取redis中的值
        rel_sms_code = conn.get("sms_code_" + attrs['mobile'])

        # 判断是否过了有效期
        if not rel_sms_code:
            raise serializers.ValidationError('已过有效期')

        # 将前端输入的验证码与redis中的验证码进行比对, redis中获取的值为字节类型
        if not rel_sms_code.decode() == attrs['sms_code']:
            raise serializers.ValidationError('验证码错误')

        return attrs

    # 重写保存
    def create(self, validated_data):

        # 保存到数据库并返回结果
        user = User.objects.create_user(username=validated_data['username'], password=validated_data['password'], mobile=validated_data['mobile'])

        # token加密
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # user对象添加属性
        user.token = token

        return user


# 显示用户信息序列化器
class UserDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'mobile', 'email', 'email_active')


# 保存邮箱序列化器
class EmailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('email',)

    def update(self, instance, validated_data):

        # 更新
        instance.email = validated_data['email']
        instance.save()

        # 发送邮箱
        data = {'name': instance.username}
        # 加密
        tjs = TJS(settings.SECRET_KEY, 300)
        token = tjs.dumps(data).decode()

        send_email.delay(token, validated_data['email'])

        return instance


# 保存用户浏览记录
class HistoriesSerializer(serializers.Serializer):

    sku_id = serializers.IntegerField(min_value=1)

    def validate(self, attrs):

        try:
            # 判断sku_id对应的商品是否存在
            SKU.objects.get(id=attrs['sku_id'])
        except:
            raise serializers.ValidationError('商品不存在')

        return attrs

    def create(self, validated_data):

        # 建立redis连接
        conn = get_redis_connection('history')

        # 序列化器中获取user对象
        user = self.context['request'].user

        # 判断sku_id是否存储过,存储过删除
        conn.lrem('history_%s'%user.id, 0, validated_data['sku_id'])

        # 写入sku_id
        conn.lpush('history_%s'%user.id, validated_data['sku_id'])

        # 控制redis列表数量
        conn.ltrim('history_%s'%user.id, 0, 4)

        # 返回结果
        return validated_data
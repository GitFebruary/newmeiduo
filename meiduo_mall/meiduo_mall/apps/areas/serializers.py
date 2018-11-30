import re

from rest_framework import serializers
from areas.models import Area

# 省市区三级联动
from users.models import Address


class AreasSerializer(serializers.ModelSerializer):

    class Meta:
        model = Area
        fields = ('id', 'name')


# 添加收货地址
class AddressSerializer(serializers.ModelSerializer):
    city_id = serializers.IntegerField(write_only=True)
    district_id = serializers.IntegerField(write_only=True)
    province_id = serializers.IntegerField(write_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Address
        exclude = ('user',)

    # 验证手机号
    def validate_mobile(self, value):

        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')

        return value

    # 重写create
    def create(self, validated_data):

        request = self.context['request']
        user = request.user
        validated_data['user'] = user

        user = super().create(validated_data)

        return user
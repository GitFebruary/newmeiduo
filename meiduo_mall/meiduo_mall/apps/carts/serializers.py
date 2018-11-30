from rest_framework import serializers
from goods.models import SKU


# 保存购物车序列化器
class CartsSerializer(serializers.Serializer):

    count = serializers.IntegerField(min_value=1)
    sku_id = serializers.IntegerField(min_value=1)
    selected = serializers.BooleanField(default=True)

    # 校验
    def validate(self, attrs):

        try:
            # 校验商品是否存在
            sku = SKU.objects.get(id=attrs['sku_id'])
        except:
            raise serializers.ValidationError('商品不存在')

        # 校验库存是否足够
        if attrs['count'] > sku.stock:
            raise serializers.ValidationError('库存不足')

        return attrs


# 获取购物车序列化器
class CartsListSerializer(serializers.ModelSerializer):

    count = serializers.IntegerField(read_only=True, min_value=1)
    selected = serializers.BooleanField(read_only=True, default=True)

    class Meta:
        model = SKU
        fields = '__all__'


# 删除购物车序列化器
class CartsDeleteSerializer(serializers.Serializer):

    sku_id = serializers.IntegerField(min_value=1)

    # 校验
    def validate(self, attrs):

        try:
            # 校验商品是否存在
            SKU.objects.get(id=attrs['sku_id'])
        except:
            raise serializers.ValidationError('商品不存在')

        return attrs


# 全选按钮序列化器
class CartsSelectedSerialziers(serializers.Serializer):

    selected = serializers.BooleanField(default=True)
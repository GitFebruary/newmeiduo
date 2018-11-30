from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from goods.models import SKU
from orders.models import OrderInfo, OrderGoods
from datetime import datetime
from django_redis import get_redis_connection


class SKUSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SKU
        fields = '__all__'


# 订单页显示商品信息序列化器
class OrdersShowGoodsSerializer(serializers.Serializer):
    freight = serializers.DecimalField(max_digits=10, decimal_places=2)
    skus = SKUSerializer(many=True)


# 生成订单详情序列化器
class OrderSaveSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderInfo
        fields = ('address', 'pay_method', 'order_id')
        extra_kwargs = {
            'address':{
              'write_only': True
            },
            'pay_method': {
                'write_only': True
            },
            'order_id': {
                'read_only': True
            },
        }

    # def create(self, validated_data):
    #
    #     # 获取验证后的支付方式/地址
    #     address = validated_data['address']
    #     pay_method = validated_data['pay_method']
    #
    #     # 获取user对象
    #     user = self.context['request'].user
    #
    #     # 生成订单编号
    #     order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id
    #
    #     # 初始化订单详情表
    #     order = OrderInfo.objects.create(
    #         # 保存订单号
    #         order_id=order_id,
    #         # 保存地址
    #         address=address,
    #         # 下单用户
    #         user=user,
    #         # 商品总数
    #         total_count=0,
    #         total_amount=Decimal(0),
    #         freight=Decimal(10),
    #         pay_method=pay_method,
    #         status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM[
    #             'CASH'] else
    #         OrderInfo.ORDER_STATUS_ENUM['UNPAID']
    #     )
    #
    #     # 获取redis对象中的所以选中状态的商品
    #     conn = get_redis_connection('cart')
    #
    #     # 获取所有的sku_id与count
    #     sku_id_count = conn.hgetall('cart_%s' % user.id)
    #
    #     # 获取set中所有的数据
    #     sku_ids = conn.smembers('cart_selected_%s' % user.id)
    #
    #     # 将hash中的值转换类型保存到字典中
    #     cart = {}
    #     for sku_id, count in sku_id_count.items():
    #         cart[int(sku_id)] = int(count)
    #
    #     # 查询选中状态的商品对象
    #     skus = SKU.objects.filter(id__in=sku_ids)
    # 重写保存方法
    def create(self, validated_data):
        # 保存数据
        # 1、获取address和支付方式
        address = validated_data['address']
        pay_method = validated_data['pay_method']
        # 2、获取user
        user = self.context['request'].user
        # 3、生成订单编号
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id

        with transaction.atomic():
            # 设置保存点
            save_point = transaction.savepoint()
            try:
                # 4、初始化一个订单基本信息表，得到订单对象order
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal(0),
                    freight=Decimal(10),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM[
                        'CASH'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNPAID']

                )
                # 5、获取缓存中的选中状态的商品数据对象 skus
                conn = get_redis_connection('cart')
                # 获取hash数据sku_id count
                sku_id_count = conn.hgetall('cart_%s' % user.id)  # {10:1}
                cart = {}
                for sku_id, count in sku_id_count.items():
                    cart[int(sku_id)] = int(count)
                # 获取集合数据
                sku_ids = conn.smembers('cart_selected_%s' % user.id)
                # 查询选中状态的数据对象
                # skus = SKU.objects.filter(id__in=sku_ids)
                # 6、遍历商品对象 sku
                for sku_id in sku_ids:
                    while True:
                        sku = SKU.objects.get(id=sku_id)
                        old_stock = sku.stock
                        old_sales = sku.sales
                        sku_count = cart[sku.id]
                        if sku_count > old_stock:
                            raise serializers.ValidationError('库存不足')

                        # 7、更新sku商品对象的库存和销量
                        # sku.stock = old_stock - sku_count
                        # sku.sales = old_sales + sku_count
                        # sku.save()
                        new_stock = old_stock - sku_count
                        new_sales = sku.sales + sku_count
                        ret = SKU.objects.filter(id=sku_id, stock=old_stock).update(stock=new_stock, sales=new_sales)
                        if ret == 0:
                            continue

                        # 8、更新spu的总销量
                        sku.goods.sales += sku_count
                        sku.goods.save()
                        # 9、更新order商品总量和商品总价
                        order.total_amount += (sku.price * sku_count)
                        order.total_count += sku_count
                        # 10、生成商品订单表
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price

                        )
                        break
                # 运费添加
                order.total_amount += order.freight
                order.save()
            except:
                # 回滚到保存点
                transaction.savepoint_rollback(save_point)
            else:
                transaction.savepoint_commit(save_point)
                # 11、删除缓存选中状态的商品信息
                conn.hdel('cart_%s' % user.id, *sku_ids)
                conn.srem('cart_selected_%s' % user.id, *sku_ids)
                # 12、结果返回
                return order
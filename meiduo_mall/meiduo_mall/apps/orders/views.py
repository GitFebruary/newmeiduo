from decimal import Decimal
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from goods.models import SKU
from orders.serializers import OrdersShowGoodsSerializer, OrderSaveSerializer


# 订单页显示商品信息视图
class OrdersShowGoodsView(APIView):

    """
    获取订单详情:
        请求方式: GET
        请求路径: orders/settlement/
        请求参数: token
        返回结果: 单价 数量 名称 运费
    业务逻辑:
        1- 获取user对象的id值
        2- 根据id查询redis数据库中hash所保存的count值
        3- 查询redis中选中的商品, set中的值
        4- 查询set对应的商品的详情信息
        5- 商品对象中添加count值
        6- 生成运费
        7- 序列化返回商品信息
    """

    def get(self, request):

        # 获取uesr对象
        user = request.user

        # 建立redis连接,获取redis对象
        conn = get_redis_connection('cart')

        # 获取所有的sku_id与count
        sku_id_count = conn.hgetall('cart_%s' % user.id)

        # 获取set中所有的数据
        sku_ids = conn.smembers('cart_selected_%s' % user.id)

        # 将hash中的值转换类型保存到字典中
        cart = {}
        for sku_id, count in sku_id_count.items():
            cart[int(sku_id)] = int(count)

        # 查询选中状态的商品对象
        skus = SKU.objects.filter(id__in=sku_ids)

        # 给商品对象中添加count值
        for sku in skus:
            sku.count = cart[sku.id]
        # 生成运费
        freight = Decimal(10.00)

        # 序列化返回结果
        ser = OrdersShowGoodsSerializer({'freight':freight, 'skus':skus})

        return Response(ser.data)


# 保存订单详情视图
class OrderSaveView(CreateAPIView):

    """
    接口设计
        请求方式: POST
        请求路径: orders/
        请求参数: 支付方式 收货地址 商品系列通过user.id在redis中获取
        返回结果: 订单编号(订单id)
    业务逻辑:
        1- 获取前端请求参数
        2- 验证参数
        3- 保存数据
            a. 获取验证后的支付方式/收货地址
            b. 通过user.id获取redis中商品信息
            c. 生成订单编号
        4- 返回结果
    """
    serializer_class = OrderSaveSerializer









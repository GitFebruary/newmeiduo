from rest_framework.response import Response
from rest_framework.views import APIView
from django_redis import get_redis_connection
from carts.serializers import CartsSerializer, CartsListSerializer, CartsDeleteSerializer, CartsSelectedSerialziers
import pickle, base64
from goods.models import SKU


# 购物车
class CartsView(APIView):

    # 重写父类中的用户验证方法,不让jwt在请求前验证
    def perform_authentication(self, request):

        pass

    # 保存购物车
    def post(self, request):
        """
        接口分析:
            请求方式: post
            请求路径: cart
            请求参数: sku_id count selected (JWT token)
            返回结果: count
        思路分析:
            1- 获取前端传入数据
            2- 校验数据
            3- 判断用户的登录状态
            4- 已登录
                a. 获取redis对象
                b. 保存数据到hash中 sku_id count
                c. 保存数据到set中 sku_id(selected)
                d. 返回结果
            5- 未登录
                a. 获取cookie, 判断以前是否存储过
                b. 存储过,进行解密操作cookie{sku_id:{count, selected}}
                c. 未存储,定义一个空字典
                d. 通过sku_id获取对应的value,如果获取到说明以前存储过进行累加,
                e. 没有获取到,添加新的数据到字典中
                f. 对字典进行类型转换并加密
                g. 写入cookie
                h. 返回数据
        :param request:
        :return:
        """

        # 获取数据
        data = request.data
        # 获取序列化器
        ser = CartsSerializer(data=data)
        # 校验数据
        ser.is_valid()
        print(ser.errors)
        # 获取验证后的数据
        selected = ser.validated_data['selected']
        count = ser.validated_data['count']
        sku_id = ser.validated_data['sku_id']
        try:
            # 判断用户的登录状态
            user = request.user
        except:
            user=None
        # 已登录
        if user is not None:
            # 使用redis缓存进行保存数据
            conn = get_redis_connection('cart')
            # 保存数据到redis hash中
            conn.hincrby('cart_%s' % user.id, sku_id, count)
            if selected:
                # 保存选中的商品到redis set中
                conn.sadd('cart_selected_%s' % user.id, sku_id)
            # 返回结果
            return Response({'count': count})
        # 未登录
        else:
            # 获取response对象
            response = Response({'count': count})
            # 获取cookie
            cart_cookie = request.COOKIES.get('cart_cookie', None)
            # 判断cookie是否为空, 不为空解密
            if cart_cookie:
                # 解密
                cart = pickle.loads(base64.b64decode(cart_cookie))
            else:
                cart = {}
            # 判断用户之前是否存储过该商品
            sku = cart.get(sku_id)
            if sku:
                # 如果有进行累加
                count += int(sku['count'])
            # 字典中添加新数据
            cart[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将数据加密
            cart_cookie = base64.b64encode(pickle.dumps(cart)).decode()
            # 存入cookie中
            response.set_cookie('cart_cookie', cart_cookie, 60*60*24)
            return response

    # 获取购物车
    def get(self, request):
        """
        接口分析:
            请求方式: GET
            请求路径: cart/
            请求参数: token
            返回结果: 商品信息 数量 状态
        逻辑分析:
            1- 获取前端数据
            2- 判断用户登录状态
            3- 已登录
                a. 从redis缓存中hash中获取上该用户的商品信息
                b. 从redis缓存中set中获取商品的选中信息
                c. 进行格式统一, 统一为字典类型
            4- 未登录
                a. 从cookie中获取商品的信息,判断是否存储过
                b. 存储过进行解密
                c. 未存储过定义空字典
            5- 获取字典中的所以sku_id用来获取商品具体信息
            6- 进行序列化返回
        :param request:
        :return:
        """

        # 判断用户登录状态
        try:
            user = request.user
        except:
            user = None

        # 已登录
        if user is not None:
            # redis中获取
            conn = get_redis_connection('cart')

            # 获取redis 哈希hash中的sku_id count
            sku_id_count = conn.hgetall('cart_%s' % user.id)

            # 获取redis 集合set中的selected
            sku_ids = conn.smembers('cart_selected_%s' % user.id)

            # 统一格式为字典
            cart = {}
            for sku_id, count in sku_id_count.items():
                cart[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in sku_ids
                }
        # 未登录
        else:
            # cookie中获取
            cart_cookie = request.COOKIES.get('cart_cookie', None)

            # 判断cookie中是否有数据
            if cart_cookie:
                # 解密
                cart = pickle.loads(base64.b64decode(cart_cookie))
            else:
                cart = {}

        # 获取字典中的sku_id
        sku_id_list = cart.keys()

        # 根据sku_id找到对应的商品
        skus = SKU.objects.filter(id__in=sku_id_list)

        # 遍历得到每一个商品信息
        for sku in skus:
            sku.count = cart[sku.id]['count']
            sku.selected = cart[sku.id]['selected']
        # 序列化返回商品信息
        ser = CartsListSerializer(skus, many=True)

        return Response(ser.data)

    # 更新购物车
    def put(self, request):
        """
        接口分析:
            请求方式: PUT
            请求路径: cart
            请求参数: sku_id count selected (JWT token)
            返回结果: sku_id count selected
        思路分析:
            1- 获取前端传入数据
            2- 校验数据
            3- 判断用户的登录状态
            4- 已登录
                a. 获取redis对象
                b. 更新数据到hash中 sku_id count
                c. 更新数据到set中 sku_id(selected)
                d. 返回结果
            5- 未登录
                a. 获取cookie, 判断以前是否存储过
                b. 存储过,进行解密操作cookie{sku_id:{count, selected}}
                c. 未存储,定义一个空字典
                e. 添加新的数据到字典中
                f. 对字典进行类型转换并加密
                g. 写入cookie
                h. 返回数据
        :param request:
        :return:
        """

        # 获取数据
        data = request.data
        # 获取序列化器
        ser = CartsSerializer(data=data)
        # 校验数据
        ser.is_valid()
        print(ser.errors)
        # 获取验证后的数据
        selected = ser.validated_data['selected']
        count = ser.validated_data['count']
        sku_id = ser.validated_data['sku_id']
        try:
            # 判断用户的登录状态
            user = request.user
        except:
            user=None
        # 已登录
        if user is not None:
            # 使用redis缓存进行保存数据
            conn = get_redis_connection('cart')
            # 更新数据到redis hash中
            conn.hset('cart_%s' % user.id, sku_id, count)
            if selected:
                # 保存选中的商品到redis set中
                conn.sadd('cart_selected_%s' % user.id, sku_id)
            else:
                # 删除未选中的商品
                conn.srem('cart_selected_%s' % user.id, sku_id)
            # 返回结果
            return Response({'count': count})
        # 未登录
        else:
            # 获取response对象
            response = Response({'count': count})
            # 获取cookie
            cart_cookie = request.COOKIES.get('cart_cookie', None)
            # 判断cookie是否为空, 不为空解密
            if cart_cookie:
                # 解密
                cart = pickle.loads(base64.b64decode(cart_cookie))
            else:
                cart = {}
            # 字典中添加新数据
            cart[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将数据加密
            cart_cookie = base64.b64encode(pickle.dumps(cart)).decode()
            # 存入cookie中
            response.set_cookie('cart_cookie', cart_cookie, 60*60*24)
            return response

    # 删除购物车
    def delete(self, request):
        """
        接口分析:
            请求方式: delete
            请求路径: cart
            请求参数: sku_id (JWT token)
            返回结果: ok
        思路分析:
            1- 获取前端传入数据
            2- 校验数据
            3- 判断用户的登录状态
            4- 已登录
                a. 获取redis对象
                b. 删除hash中的数据 sku_id count
                c. 删除set中的数据 sku_id(selected)
                d. 返回结果
            5- 未登录
                a. 获取cookie, 判断以前是否存储过
                b. 存储过,进行解密操作cookie{sku_id:{count, selected}}
                c. 删除数据
                d. 加密数据到
                e. 写入cookie
                f. 返回数据
        :param request:
        :return:
        """

        # 获取数据
        data = request.data
        # 获取序列化器
        ser = CartsDeleteSerializer(data=data)
        # 校验数据
        ser.is_valid()
        print(ser.errors)
        # 获取验证后的数据
        sku_id = ser.validated_data['sku_id']
        try:
            # 判断用户的登录状态
            user = request.user
        except:
            user=None
        # 已登录
        if user is not None:
            # 使用redis缓存进行保存数据
            conn = get_redis_connection('cart')
            # 删除数据redis hash中
            conn.hdel('cart_%s' % user.id, sku_id)
            # 删除未选中的商品
            conn.srem('cart_selected_%s' % user.id, sku_id)
            # 返回结果
            return Response({'message': 'OK'})
        # 未登录
        else:
            # 获取response对象
            response = Response({'message': 'OK'})
            # 获取cookie
            cart_cookie = request.COOKIES.get('cart_cookie', None)
            # 判断cookie是否为空, 不为空解密
            if cart_cookie:
                # 解密
                cart = pickle.loads(base64.b64decode(cart_cookie))
                # 删除数据
                if sku_id in cart.keys():
                    del cart[sku_id]
                # 加密剩余数据
                cart_cookie = base64.b64encode(pickle.dumps(cart)).decode()
                # 存入cookie中
                response.set_cookie('cart_cookie', cart_cookie, 60*60*24)
            return response


# 购物车全选按钮
class CartsSelectionView(APIView):

    def perform_authentication(self, request):
        pass

    # 全选按钮视图
    def put(self, request):
        """
        接口分析:
            请求方式: PUT
            请求路径: cart/selection/
            请求参数: selected, token(JWT)
            返回结果: selected
        思路分析:
            1- 获取前端传入的参数
            2- 验证参数
            3- 判断用户登录状态
            4- 已登录
                获取redis对象
                修改set集合中的值
                返回结果
            5- 未登录
                获取cookie中的数据
                对数据进行解密操作
                更新数据
                将更新的数据进行加密
                添加到cookie
                返回数据
        :param request:
        :return:
        """
        # 获取前端传入的数据
        data = request.data

        # 验证数据
        ser = CartsSelectedSerialziers(data=data)
        ser.is_valid()
        print(ser.errors)
        selected = ser.validated_data['selected']
        # 判断用户登录状态
        try:
            user = request.user
        except:
            user = None

        # 已登录
        if user is not None:
            # 获取redis对象
            conn = get_redis_connection('cart')
            # 获取hash中所以的sku_id 与 count
            sku_id_count = conn.hgetall('cart_%s' % user.id)
            # 获取所有skuid
            sku_ids = sku_id_count.keys()
            # 判断前端传入的数据是 全选还是全不选
            if selected:
                conn.sadd('cart_selected_%s' % user.id, *sku_ids)
            else:
                conn.srem('cart_selected_%s' % user.id, *sku_ids)

            return Response({'selected': selected})
        # 未登录
        else:
            response = Response({'selected': selected})
            # 获取cookie中的值
            cart_cookie = request.COOKIES.get('cart_cookie', None)

            if cart_cookie:
                # 解密
                cart = pickle.loads(base64.b64decode(cart_cookie))

                # 字典写入新数据
                for sku_id, data in cart.items():
                    data['selected'] = selected

                # 将新数据加密
                cart_cookie = base64.b64encode(pickle.dumps(cart)).decode()

                # 写入cookie
                response.set_cookie('cart_cookie', cart_cookie, max_age=60 * 60 * 24)
            return response


import base64
import re
import pickle
from django_redis import get_redis_connection
from users.models import User
from django.contrib.auth.backends import ModelBackend


# 重写jwt自带的登录的获取数据方法
def jwt_response_payload_handler(token, user=None, request=None):

    response_data = {
        'token': token,
        'username': user.username,
        'user_id': user.id
    }

    return response_data


class UsernameMobileAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        try:
            # 判断传入的用户名是否是手机号
            if re.match(r'^1[3-9]\d{9}$', username):
                # 如果是手机号按照手机号进行查询
                user = User.objects.get(mobile=username)
            else:
                # 用户名进行查询
                user = User.objects.get(username=username)
        except Exception as e:
            user = None

        # 验证密码
        if user is not None and user.check_password(password):
            return user


# 合并购物车
def merge_cart_cookie_to_redis(request, response, user):
    # 获取cookie中的数据
    cart_cookie = request.COOKIES.get('cart_cookie', None)
    # 判断cookie是否为空
    if not cart_cookie:
        return response

    # 将不为空的cart_cookie数据解密
    cart = pickle.loads(base64.b64decode(cart_cookie))
    # 判断cart是否为空
    if cart is None:
        return response

    # 数据拆分, 定义空字典与空列表
    cart_dict = {}
    sku_ids = []
    sku_ids_none = []

    for sku_id, data in cart.items():
        # 存入字典
        cart_dict[sku_id] = data['count']
        # 判断选中状态
        if data['selected']:
            sku_ids.append(data['selected'])
        else:
            sku_ids_none.append(data['selected'])
    # 获取redis对象
    conn = get_redis_connection('cart')

    # 添加数据到hash
    conn.hmset('cart_%s' % user.id, cart_dict)
    # 添加数据到set
    if sku_ids:
        conn.sadd('cart_selected_%s' % user.id, *sku_ids)

    if sku_ids_none:
        conn.srem('cart_selected_%s' % user.id, *sku_ids_none)

    # 删除cookie
    response.delete_cookie('cart_cookie')

    return response
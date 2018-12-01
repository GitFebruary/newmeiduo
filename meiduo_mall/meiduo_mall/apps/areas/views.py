from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from areas.models import Area
from areas.serializers import AreasSerializer, AddressSerializer
from users.models import Address


# 查询显示省信息
class AreasView(CacheResponseMixin, ListAPIView):
    """
    请求方式: GET
    请求路径: /areas
    请求参数: 无
    返回结果: 省信息
    思路分析:
        1. 查询值为None的数据
        2. 返回数据
    """

    serializer_class = AreasSerializer
    queryset = Area.objects.filter(parent=None)


# 查询显示市区信息
class AreaView(CacheResponseMixin, ListAPIView):

    serializer_class = AreasSerializer

    def get_queryset(self):
        # 获取PK值
        pk = self.kwargs['pk']
        # 查询数据并返回
        return Area.objects.filter(parent_id=pk)


# 添加收货地址
class AddressView(CreateAPIView, ListAPIView):
    """
    添加收货地址:
    请求方式: post
    请求路径: addresses/
    请求参数: 省市区/姓名/详细地址/手机号/固定电话/邮箱
    返回结果: 保存后的地址信息
    思路分析:
        1. 获取前端传入的数据
        2. 校验前端传入的数据
        3. 进行保存操作
        4. 返回结果给前端
    """
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user, is_deleted=False)


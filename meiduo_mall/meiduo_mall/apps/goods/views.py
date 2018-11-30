from rest_framework.response import Response
from rest_framework.views import APIView
from goods.models import GoodsCategory, SKU
from rest_framework.generics import ListAPIView
from goods.serializers import SKUListSerializer, SKUSearchSerializer
from goods.utils import PageNum
from rest_framework.filters import OrderingFilter
from drf_haystack.viewsets import HaystackViewSet


class CategroiesView(APIView):
    """
        面包屑导航
    """

    def get(self, request, pk):
        # 根据ID查询三级分类对象
        cat3 = GoodsCategory.objects.get(id=pk)
        cat2 = cat3.parent
        cat1 = cat2.parent

        return Response(
            {
                'cat1':cat1.name,
                'cat2':cat2.name,
                'cat3':cat3.name,
            }
        )


class SKUListView(ListAPIView):

    """
        获取当前分类下的所以分类视图
    """

    serializer_class = SKUListSerializer
    pagination_class = PageNum
    filter_backends = [OrderingFilter]
    ordering_fields = ('create_time', 'sales','price')

    def get_queryset(self):
        pk = self.kwargs['pk']
        return SKU.objects.filter(category_id=pk)


class SKUSearchView(HaystackViewSet):

    index_models = [SKU]
    serializer_class = SKUSearchSerializer
    pagination_class = PageNum
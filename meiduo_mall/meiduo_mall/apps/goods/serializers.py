from rest_framework import serializers
from goods.models import SKU
from drf_haystack.serializers import HaystackSerializer
from goods.search_indexes import SKUIndex


class SKUListSerializer(serializers.ModelSerializer):

    class Meta:
        model = SKU
        fields = '__all__'


class SKUSearchSerializer(HaystackSerializer):

    class Meta:
        object = SKUListSerializer()
        index_classes=[SKUIndex]
        fields = ('text', 'object')






from haystack import indexes
from goods.models import SKU


class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    """
    商品索引类

    """

    # 指定索引字段
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):

        return SKU


    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_launched=True)
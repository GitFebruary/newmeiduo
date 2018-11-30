from django.contrib import admin
from goods import models
from celery_tasks.static_html.tasks import generate_static_list_search_html, generate_static_sku_detail_html


class GoodsAdmin(admin.ModelAdmin):
    """
        商品SPU表的后台管理器
    """
    list_display = ['id', 'name']

    # 点击admin站点中的保存方法触发此函数
    def save_model(self, request, obj, form, change):
        obj.save()
        generate_static_list_search_html.delay()

    # 点击admin站点中的删除方法触发此函数
    def delete_model(self, request, obj):
        generate_static_list_search_html.delay()


# 管理SKU表的管理器类
class SKUAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()

        generate_static_sku_detail_html.delay(obj.id)


# 将模型类注册到admin中,展示在admin站点中
admin.site.register(models.Goods, GoodsAdmin)
admin.site.register(models.SKU, SKUAdmin)
from celery import Celery
from meiduo_mall.libs.yuntongxun.sms import CCP

# 为celery使用django配置文件进行设置, 为了让django调用到celery,所以需要django的配置文件告诉给celery
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

# 创建celery应用
app = Celery('meiduo')

# app = Celery(broker="redis://127.0.0.1/3")

# 导入celery配置
app.config_from_object('celery_tasks.config')

# 自动注册celery任务, 会自动在目录下找到对应的tasks文件,所以文件名必须是tasks
app.autodiscover_tasks(['celery_tasks.sms', 'celery_tasks.emails', 'celery_tasks.static_html'])


# @app.task()
# def send_sms_code(moblie, sms_code):
#     ccp = CCP()
#     ccp.send_template_sms(moblie, [sms_code, '5'], 1)

# 启动celery
# 启动指令: celery -A celery_tasks.main worker -l info

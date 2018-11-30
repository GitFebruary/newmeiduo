from meiduo_mall.libs.yuntongxun.sms import CCP
from celery_tasks.main import app


# 异步发送短信
@app.task(name="send_sms_code")
# @app.task()
def send_sms_code(moblie, sms_code):
    ccp = CCP()
    ccp.send_template_sms(moblie, [sms_code, '5'], 1)




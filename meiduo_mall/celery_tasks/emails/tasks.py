from celery_tasks.main import app
from django.core.mail import send_mail
from django.conf import settings


@app.task(name='send_email')
def send_email(token, email):
    subject = "美多商城邮箱验证"
    verify_url = 'http://www.meiduo.site:8080/success_verify_email.html?token=' + token
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用美多商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s<a></p>' % (email, verify_url, verify_url)
    # 发送邮件方法
    send_mail(subject, '官方爸爸别封号,我是自己给自己发', settings.EMAIL_FROM, [email], html_message=html_message)
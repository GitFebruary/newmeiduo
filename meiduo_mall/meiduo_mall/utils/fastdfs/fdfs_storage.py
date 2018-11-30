from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FastDFSStorage(Storage):
    """
        django默认将文件存储在项目目录下,现在需要将文件存储到fastDFS文件系统中就需要重写django默认存储文件的类Storage
    """

    def __init__(self, base_url=None, client_conf=None):
        """
        初始化
        :param base_url: 用于构造图片完整路径使用，图片服务器的域名
        :param client_conf: FastDFS客户端配置文件的路径
        """
        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

    def _open(self, name, mode='rb'):
        # 打开文件方法,不需要django自带的打开文件的方法而是使用fastDFS中的方法
        pass

    # 保存文件方法
    def _save(self, name, content):

        # 获取fastDFS对象进行文件上传
        client = Fdfs_client(self.client_conf)
        # 获取上传之后的返回结果
        ret = client.upload_by_buffer(content.read())
        # 判断上传结果
        if ret['Status'] != 'Upload successed.':
            raise Exception('upload error')
        # 获取file_id
        file_id = ret['Remote file_id']
        # 返回file_id
        return file_id

    def url(self, name):
        # 拼接完整路径并返回
        return self.base_url + name

    def exists(self, name):
        # 判断文件是否存在,不需要django自带的方法去判断使用fastDFS进行判断
        return False
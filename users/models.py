from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    mobile = models.CharField(max_length=20, unique=True, blank=True)

    # 头像
    avatar = models.ImageField(upload_to='avatar%Y%m%d', blank=True)

    # 个人简介
    user_desc = models.TextField(max_length=500, blank=True)

    # 修改认证的字段
    USERNAME_FIELD = 'mobile'

    # 创建超级管理员必须输入的字段
    REQUIRED_FIELDS = ['username', 'email']

    # 内部类class Meta用于给model定义元数据
    class Meta:
        db_table = 'tb_user'  # 修改后默认的表名
        verbose_name = '用户信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.mobile

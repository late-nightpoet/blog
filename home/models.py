from django.db import models
from django.utils import timezone
# Create your models here.
from users.models import User


class ArticleCategory(models.Model):
    # 文章分类
    title = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'tb_category'
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name


class Article(models.Model):
    # 定义文章作者，author通过models.ForeignKey外键与内建User模型相连
    # 参数on_delete 用于指定数据删除方式，避免两个关联表数据不一致
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    # 文章标题图
    avatar = models.ImageField(upload_to='article/%Y%m%d', blank=True)
    # 文章栏目的’一对多‘外键
    category = models.ForeignKey(
        ArticleCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='article'
    )
    # 文章标签
    tags = models.CharField(max_length=20, blank=True)
    title = models.CharField(max_length=100, null=False, blank=False)
    summary = models.CharField(max_length=200, null=False, blank=False)
    content = models.TextField()
    total_views = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        # ordering指定模型返回数据排列顺序
        # ’-created'表明数据应该以倒序排列
        ordering = ('-created',)
        db_table = 'tb_article'
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name
    # 函数 __str__ 定义当调用对象的 str() 方法时的返回值内容
    # 它最常见的就是在Django管理后台中做为对象的显示值。因此应该总是为 __str__ 返回一个友好易读的字符串

    def __str__(self):
        return self.title + str(timezone.now())


class Comment(models.Model):
    content = models.TextField()
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'tb_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name

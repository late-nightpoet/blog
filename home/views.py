from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from home.models import ArticleCategory, Article, Comment
from django.http import HttpResponseNotFound
# Create your views here.


class IndexView(View):

    def get(self, request):
        cat_id = request.GET.get('cat_id', 1)
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 2)

        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseNotFound('没有此分类')

        # 获取博客分类信息
        categories = ArticleCategory.objects.all()

        # 分页数据
        articles = Article.objects.filter(
            category=category
        )

        # 创建分页器：每页N条
        paginator = Paginator(articles, page_size)
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')

        # 获取列表总页数
        total_page = paginator.num_pages

        context = {
            'categories': categories,
            'category': category,
            'articles': page_articles,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num,
        }

        return render(request, 'index.html', context=context)


class DetailView(View):

    def get(self, request):
        # detail/?id=xxx&page_num=xxx&page_size=xxx
        id = request.GET.get('id')
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 3)
        categories = ArticleCategory.objects.all()
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            article.total_views += 1
            article.save()

        hot_articles = Article.objects.order_by('-total_views')[:9]
        comments = Comment.objects.filter(
            article=article
        ).order_by('-created')
        total_count = comments.count()

        paginator = Paginator(comments, page_size)
        try:
            page_comments = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，返回404
            return HttpResponseNotFound('empty page')
        total_page = paginator.num_pages
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
            'hot_articles': hot_articles,
            'total_count': total_count,
            'comments': page_comments,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num,
        }
        return render(request, 'detail.html', context=context)

    def post(self, request):
        user = request.user
        if user and user.is_authenticated:
            id = request.POST.get('id')
            content = request.POST.get('content')

            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                return HttpResponseNotFound('没有此文章')

            Comment.objects.create(
                content=content,
                article=article,
                user=user
            )
            article.comment_count += 1
            article.save()
            # 拼接跳转路由
            path = reverse('home:detail')+'?id={}'.format(article.id)
            return redirect(path)
        else:
            return redirect(reverse('users:login'))

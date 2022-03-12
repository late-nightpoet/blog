import re

from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.http import HttpResponseBadRequest, HttpResponse

from home.models import ArticleCategory, Article
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from users.models import User
from django.db import DatabaseError
from django.shortcuts import redirect
from django.urls import reverse


# Create your views here.
class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request:请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        # 接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')

        # 校验参数
        # 校验参数是否齐全
        if not all([mobile, password, password2, smscode]):
            # return JsonResponse('code':)
            # 什么时候用JsonResponse，什么时候用HttpResponseBadRequest
            return HttpResponseBadRequest('缺少必传参数')
        # 校验mobile是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')
        # 校验password是否合法并且相同
        if not re.match(r'[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')

        # 短信验证码是否正确
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != sms_code_server.decode():
            # 为什么sms_code_server要使用decode方法
            return HttpResponseBadRequest('短信验证码错误')

        # 判断用户mobile是否唯一

        # 注册用户
        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        # 思考一下还可以用什么try except finally结构来获取错误

        # 实现状态保持
        login(request, user)

        # 响应注册结果
        # 这里返回的是HttpResponse而不是JsonResponse
        # return HttpResponse('注册成功，重定向到首页')
        response = redirect(reverse('home:index'))

        # 设置cookie
        # 登录状态，会话结束后自动过期
        response.set_cookie('is_login', True)
        response.set_cookie('username', user.username, max_age=1 * 24 * 3600)

        return response


class ImageCodeView(View):

    def get(self, request):
        # 获取前端参数
        uuid = request.GET.get('uuid')
        if uuid is None:
            return HttpResponseBadRequest('请求参数错误')
        # 获取验证码内容和验证码图片二进制数据
        text, image = captcha.generate_captcha()
        # 讲图片保存到redis中，并设置过期时间
        redis_conn = get_redis_connection('default')
        redis_conn.setex('img:%s' % uuid, 300, text)
        # 返回响应，将生成的图片以content_type为image/jpeg的形式返回给请求
        return HttpResponse(image, content_type='image/jpeg')


from django.http import JsonResponse
from utils.response_code import RETCODE
from random import randint
from libs.yuntongxun.sms import CCP
import logging

logger = logging.getLogger('django')


class SmsCodeView(View):

    def get(self, request):
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        mobile = request.GET.get('mobile')

        if not all([image_code_client, uuid, mobile]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})

        redis_conn = get_redis_connection('default')

        image_code_server = redis_conn.get('img:%s' % uuid)
        if image_code_server is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码失效'})
        # 删除图形验证码，避免恶意测试
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)

        # 对比图形验证码
        image_code_server = image_code_server.decode()  # bytes转字符串
        if image_code_client.lower() != image_code_server.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})

        # 生成短信验证码： 生成6位数验证码
        sms_code = '%06d' % randint(0, 999999)
        # 将验证码输出在控制台，方便调试
        logger.info(sms_code)

        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        # CCP().send_template_sms(mobile, [sms_code, 5], 1),先不发送短信

        return JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        if not all([mobile, password]):
            return HttpResponseBadRequest('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确手机号')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码最少8位，最长20位')

        # 认证登录用户
        user = authenticate(mobile=mobile, password=password)

        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')

        # 实现状态保持
        login(request, user)

        # 响应登录结果
        next_page = request.GET.get('next')
        if next_page:
            redirect(next_page)
        else:
            response = redirect(reverse('home:index'))

        # 设置保持状态周期
        if remember != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
            # 设置cookie
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=1 * 24 * 3600)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiray(None)

            response.set_cookie('is_login', True, max_age=14 * 24 * 3500)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


class LogoutView(View):

    def get(self, request):
        # 清理session
        logout(request)
        response = redirect(reverse('users:login'))
        response.delete_cookie('is_login')

        return response


class ForgetPasswordView(View):

    def get(self, request):

        return render(request, 'forget_password.html')

    def post(self, request):
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')

        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确手机号')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码最少8位，最长20位')

        if password != password2:
            return HttpResponseBadRequest('两次输入密码不一致')

        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != sms_code_server.decode():
            return HttpResponseBadRequest('短信验证码错误')

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 如果该手机不存在，则注册新用户
            try:
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception:
                return HttpResponseBadRequest('修改失败，请稍后再试')
        else:
            user.set_password(password)
            user.save()

        return HttpResponse('修改成功，请返回登录页面')


# LoginRequiredMixin
# 如果用户未登录的话，则会进行默认的跳转
# 默认的跳转连接是：accounts/login/?next=xxx
# 看不太懂
class UserCenterView(LoginRequiredMixin, View):

    def get(self, request):
        user = request.user

        # 组织模板渲染数据
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context=context)

    def post(self, request):
        # 为什么这里是request.user?而不是通过get方法得到
        user = request.user
        avatar = request.FILES.get('avatar')
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)

        # 修改数据库信息
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('更新失败，请稍后再试')

        # 返回响应，刷新页面
        response = redirect(reverse('users:center'))
        # 更新cookie信息
        response.set_cookie('username', user.username, max_age=30*24*3600)
        return response


class WriteBlogView(LoginRequiredMixin, View):

    def get(self, request):
        categories = ArticleCategory.objects.all()

        context = {
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        summary = request.POST.get('summary')
        content = request.POST.get('content')
        user = request.user

        if not all([avatar, title, category_id, tags, summary, content]):
            return HttpResponseBadRequest('参数不全')

        # 判断文章分类id数据是否正确
        try:
            article_category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist as e:
            logger.error(e)
            return HttpResponseBadRequest('没有此分类信息')

        try:
            article = Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                tags=tags,
                title=title,
                summary=summary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('发布失败，请稍后再试')

        return redirect(reverse('home:index'))

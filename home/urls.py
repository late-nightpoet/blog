from django.urls import path
from home.views import IndexView, DetailView

urlpatterns = [
    # as_view与as_view()的区别
    path('', IndexView.as_view(), name='index'),
    path('detail/', DetailView.as_view(), name='detail')
]
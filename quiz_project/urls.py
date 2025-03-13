from django.contrib import admin
from django.urls import path
from quiz import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.welcome, name='welcome'),
    path('quiz/', views.quiz, name='quiz'),
    path('get_question/', views.get_question, name='get_question'),
    path('save_answer/', views.save_answer, name='save_answer'),
    path('show_cheaters/', views.show_cheaters, name='show_cheaters'),
]
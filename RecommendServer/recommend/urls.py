from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    path('search/area', views.SearchAreaByQuery.as_view()),
    path('search/area/<int:cid>', views.searchAreaById),
    path('search/area/all/', views.getAllAreas),
    path('recommend/user', views.getRecommendsByUser),
    path('recommend/testset/', views.getTestSet),
    path('updateuser/join/', views.join),
    path('updateuser/log/', views.log),
]

urlpatterns = format_suffix_patterns(urlpatterns)
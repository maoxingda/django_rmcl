from . import views
from django.urls import path

app_name = 'rmcl'

urlpatterns = [
    path('sqlfile/change-list/refresh/', views.refresh_change_list, name='refresh_change_list'),
    path('sqlfile/<int:pk>/render/', views.render_sqlfile, name='render_sqlfile'),
]

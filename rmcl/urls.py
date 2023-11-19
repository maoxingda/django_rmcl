from . import views
from django.urls import path

app_name = 'rmcl'

urlpatterns = [
    path('sqlfile/change-list/refresh/'    , views.refresh_change_list, name = 'refresh_change_list'),
    path('task/<int:pk>/render/'           , views.render_sqlfile     , name = 'render_sqlfile'),
    path('task/<int:pk>/open_sqlfile/'     , views.open_sqlfile       , name = 'open_sqlfile'),
]

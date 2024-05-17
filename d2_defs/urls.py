from django.urls import path
from .views import UpdateDefinitionTablesView, GetTableContentView

app_name = 'd2_defs'

urlpatterns = [
    path('update-defs/', UpdateDefinitionTablesView.as_view(), name='update-defs'),
    path('get-def/<str:table_name>/', GetTableContentView.as_view(), name='get-table-content'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/nuevo/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/<int:pedido_id>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedidos/<int:pedido_id>/etapa/', views.agregar_etapa, name='agregar_etapa'),
    path('pedidos/<int:pedido_id>/evidencia/', views.agregar_evidencia, name='agregar_evidencia'),
    path('pedidos/<int:pedido_id>/avance/', views.actualizar_avance_pedido, name='actualizar_avance_pedido'),
    path('pedidos/<int:pedido_id>/consumo/', views.registrar_consumo, name='registrar_consumo'),

    path('inventario/', views.inventario, name='inventario'),
    path('inventario/nuevo/', views.crear_insumo, name='crear_insumo'),

    path('costurera/panel/', views.panel_costurera, name='panel_costurera'),

    path('consulta/', views.consulta_cliente, name='consulta_cliente'),
]

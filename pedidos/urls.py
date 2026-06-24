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

    path('costureras/', views.lista_costureras, name='lista_costureras'),
    path('costureras/nueva/', views.crear_costurera, name='crear_costurera'),
    path('costureras/<int:costurera_id>/editar/', views.editar_costurera, name='editar_costurera'),
    path('costureras/<int:costurera_id>/eliminar/', views.eliminar_costurera, name='eliminar_costurera'),

    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:cliente_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),

    path('costurera/panel/', views.panel_costurera, name='panel_costurera'),

    path('cliente/', views.inicio_cliente, name='inicio_cliente'),

    path('consulta/', views.consulta_cliente, name='consulta_cliente'),

    path('chatbot/', views.chatbot_responder, name='chatbot'),
]
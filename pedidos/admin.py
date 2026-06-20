from django.contrib import admin
from .models import Cliente, Costurera, Pedido, EtapaPedido, EvidenciaPedido, Insumo, ConsumoInsumo


class EtapaPedidoInline(admin.TabularInline):
    model = EtapaPedido
    extra = 1


class EvidenciaPedidoInline(admin.TabularInline):
    model = EvidenciaPedido
    extra = 1


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'cliente',
        'tipo_prenda',
        'costurera',
        'estado',
        'porcentaje_avance',
        'fecha_entrega_estimada',
    )
    search_fields = ('codigo', 'cliente__nombre')
    list_filter = ('estado', 'tipo_prenda', 'costurera')
    inlines = [EtapaPedidoInline, EvidenciaPedidoInline]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'celular', 'correo', 'direccion')
    search_fields = ('nombre', 'celular', 'correo')


@admin.register(Costurera)
class CostureraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especialidad', 'disponibilidad', 'activa', 'usuario')
    list_filter = ('activa',)
    search_fields = ('nombre', 'especialidad')


@admin.register(EtapaPedido)
class EtapaPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'nombre', 'estado', 'fecha')
    list_filter = ('estado',)
    search_fields = ('pedido__codigo', 'nombre')


@admin.register(EvidenciaPedido)
class EvidenciaPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'etapa', 'descripcion', 'fecha_subida')
    search_fields = ('pedido__codigo', 'descripcion')


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'stock_actual', 'stock_minimo', 'unidad', 'proveedor')
    list_filter = ('categoria', 'unidad')
    search_fields = ('nombre', 'proveedor')


@admin.register(ConsumoInsumo)
class ConsumoInsumoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'insumo', 'cantidad', 'fecha', 'observacion')
    search_fields = ('pedido__codigo', 'insumo__nombre')

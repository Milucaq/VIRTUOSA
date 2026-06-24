import io
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from pedidos.models import Cliente, Costurera, Insumo, Pedido, EvidenciaPedido
from pedidos.views import crear_etapas_estandar

CLIENTES = [
    {'nombre': 'Valeria Mendoza', 'celular': '987654321', 'correo': 'valeria.mendoza@example.com', 'direccion': 'Av. Larco 123, Miraflores'},
    {'nombre': 'Camila Rojas', 'celular': '912345678', 'correo': 'camila.rojas@example.com', 'direccion': 'Calle Los Sauces 45, San Borja'},
    {'nombre': 'Fernanda Castillo', 'celular': '998877665', 'correo': 'fernanda.castillo@example.com', 'direccion': 'Av. Salaverry 890, Jesus Maria'},
    {'nombre': 'Daniela Torres', 'celular': '955443322', 'correo': 'daniela.torres@example.com', 'direccion': 'Jr. Las Begonias 210, San Isidro'},
    {'nombre': 'Gabriela Soto', 'celular': '944556677', 'correo': 'gabriela.soto@example.com', 'direccion': 'Calle Las Magnolias 67, La Molina'},
]

COSTURERAS = [
    {'nombre': 'Rosa Quispe', 'especialidad': 'Vestidos de noche', 'disponibilidad': 'Tiempo completo'},
    {'nombre': 'Lucia Fernandez', 'especialidad': 'Blusas y enterizos', 'disponibilidad': 'Medio tiempo'},
    {'nombre': 'Carmen Huaman', 'especialidad': 'Faldas y acabados', 'disponibilidad': 'Tiempo completo'},
]

INSUMOS = [
    {'nombre': 'Seda natural blanca', 'categoria': 'Tela', 'unidad': 'm', 'stock_actual': 25, 'stock_minimo': 5, 'proveedor': 'Textiles Lima SAC'},
    {'nombre': 'Tul bordado', 'categoria': 'Tela', 'unidad': 'm', 'stock_actual': 10, 'stock_minimo': 4, 'proveedor': 'Importaciones Andina'},
    {'nombre': 'Encaje frances', 'categoria': 'Avio', 'unidad': 'm', 'stock_actual': 3, 'stock_minimo': 5, 'proveedor': 'Casa del Encaje'},
    {'nombre': 'Cierre invisible 20cm', 'categoria': 'Avio', 'unidad': 'und', 'stock_actual': 40, 'stock_minimo': 10, 'proveedor': 'Merceria Central'},
    {'nombre': 'Hilo de poliester', 'categoria': 'Hilo', 'unidad': 'rollo', 'stock_actual': 15, 'stock_minimo': 5, 'proveedor': 'Hilos del Sur'},
    {'nombre': 'Pedreria strass', 'categoria': 'Avio', 'unidad': 'und', 'stock_actual': 200, 'stock_minimo': 50, 'proveedor': 'Biauteria Andina'},
]

PEDIDOS = [
    {'codigo': 'VIR-2026-101', 'cliente': 'Valeria Mendoza', 'tipo_prenda': 'vestido_noche', 'costurera': 'Rosa Quispe', 'estado': 'en_proceso', 'avance': 55, 'dias_inicio': -10, 'dias_entrega': 12},
    {'codigo': 'VIR-2026-102', 'cliente': 'Camila Rojas', 'tipo_prenda': 'blusa_medida', 'costurera': 'Lucia Fernandez', 'estado': 'pendiente', 'avance': 10, 'dias_inicio': -2, 'dias_entrega': 18},
    {'codigo': 'VIR-2026-103', 'cliente': 'Fernanda Castillo', 'tipo_prenda': 'falda', 'costurera': 'Carmen Huaman', 'estado': 'finalizado', 'avance': 100, 'dias_inicio': -30, 'dias_entrega': -2},
    {'codigo': 'VIR-2026-104', 'cliente': 'Daniela Torres', 'tipo_prenda': 'enterizo', 'costurera': 'Rosa Quispe', 'estado': 'retrasado', 'avance': 40, 'dias_inicio': -25, 'dias_entrega': -5},
    {'codigo': 'VIR-2026-105', 'cliente': 'Gabriela Soto', 'tipo_prenda': 'vestido_noche', 'costurera': 'Lucia Fernandez', 'estado': 'en_proceso', 'avance': 70, 'dias_inicio': -15, 'dias_entrega': 5},
    {'codigo': 'VIR-2026-106', 'cliente': 'Valeria Mendoza', 'tipo_prenda': 'otro', 'costurera': 'Carmen Huaman', 'estado': 'entregado', 'avance': 100, 'dias_inicio': -45, 'dias_entrega': -15},
    {'codigo': 'VIR-2026-107', 'cliente': 'Camila Rojas', 'tipo_prenda': 'blusa_medida', 'costurera': None, 'estado': 'pendiente', 'avance': 0, 'dias_inicio': 0, 'dias_entrega': 20},
    {'codigo': 'VIR-2026-108', 'cliente': 'Fernanda Castillo', 'tipo_prenda': 'falda', 'costurera': 'Rosa Quispe', 'estado': 'en_proceso', 'avance': 30, 'dias_inicio': -5, 'dias_entrega': 15},
]


def _placeholder_image(texto, color):
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (600, 400), color=color)
    draw = ImageDraw.Draw(img)
    draw.text((30, 180), texto, fill='white')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return ContentFile(buffer.getvalue(), name=f'{texto.lower().replace(" ", "_")}.jpg')


class Command(BaseCommand):
    help = 'Carga datos de ejemplo (clientes, costureras, insumos y pedidos) para demostracion.'

    def handle(self, *args, **options):
        hoy = timezone.now().date()

        clientes = {}
        for data in CLIENTES:
            cliente, created = Cliente.objects.get_or_create(nombre=data['nombre'], defaults=data)
            clientes[data['nombre']] = cliente
            self.stdout.write(f"Cliente {'creado' if created else 'ya existia'}: {cliente.nombre}")

        costureras = {}
        for data in COSTURERAS:
            costurera, created = Costurera.objects.get_or_create(nombre=data['nombre'], defaults=data)
            costureras[data['nombre']] = costurera
            self.stdout.write(f"Costurera {'creada' if created else 'ya existia'}: {costurera.nombre}")

        for data in INSUMOS:
            insumo, created = Insumo.objects.get_or_create(nombre=data['nombre'], defaults=data)
            self.stdout.write(f"Insumo {'creado' if created else 'ya existia'}: {insumo.nombre}")

        pedidos_creados = []
        for data in PEDIDOS:
            if Pedido.objects.filter(codigo=data['codigo']).exists():
                self.stdout.write(f"Pedido ya existia: {data['codigo']}")
                continue

            pedido = Pedido.objects.create(
                codigo=data['codigo'],
                cliente=clientes[data['cliente']],
                tipo_prenda=data['tipo_prenda'],
                descripcion=f"Pedido de ejemplo - {data['tipo_prenda']}",
                fecha_inicio=hoy + timedelta(days=data['dias_inicio']),
                fecha_entrega_estimada=hoy + timedelta(days=data['dias_entrega']),
                costurera=costureras.get(data['costurera']) if data['costurera'] else None,
                estado=data['estado'],
                porcentaje_avance=data['avance'],
            )
            crear_etapas_estandar(pedido)
            pedidos_creados.append(pedido)
            self.stdout.write(self.style.SUCCESS(f'Pedido creado: {pedido.codigo}'))

        for pedido, texto, color in [
            (pedidos_creados[0] if pedidos_creados else None, 'Avance de confeccion', '#491b78'),
            (pedidos_creados[1] if len(pedidos_creados) > 1 else None, 'Prueba de talle', '#b86f8b'),
        ]:
            if not pedido:
                continue
            EvidenciaPedido.objects.create(
                pedido=pedido,
                imagen=_placeholder_image(texto, color),
                descripcion=texto,
            )
            self.stdout.write(self.style.SUCCESS(f'Evidencia de prueba subida para {pedido.codigo}'))

        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados correctamente.'))

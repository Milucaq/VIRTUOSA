import io
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from pedidos.models import Cliente, Costurera, Insumo, Pedido, EvidenciaPedido
from pedidos.views import crear_etapas_estandar, ETAPAS_ESTANDAR
from pedidos import historial

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
    # Pedidos con creado_en retroactivo: alimentan "Pedidos registrados por mes"
    # con varios meses de historia, y suman retrasos en mas costureras para
    # que "Pedidos retrasados por costurera" no dependa de un solo caso.
    {'codigo': 'VIR-2026-109', 'cliente': 'Gabriela Soto', 'tipo_prenda': 'enterizo', 'costurera': 'Lucia Fernandez', 'estado': 'retrasado', 'avance': 35, 'dias_inicio': -60, 'dias_entrega': -20, 'dias_creado': -65},
    {'codigo': 'VIR-2026-110', 'cliente': 'Daniela Torres', 'tipo_prenda': 'vestido_noche', 'costurera': 'Carmen Huaman', 'estado': 'retrasado', 'avance': 50, 'dias_inicio': -50, 'dias_entrega': -10, 'dias_creado': -55},
    {'codigo': 'VIR-2026-111', 'cliente': 'Valeria Mendoza', 'tipo_prenda': 'blusa_medida', 'costurera': 'Rosa Quispe', 'estado': 'retrasado', 'avance': 20, 'dias_inicio': -40, 'dias_entrega': -8, 'dias_creado': -45},
    {'codigo': 'VIR-2026-112', 'cliente': 'Camila Rojas', 'tipo_prenda': 'falda', 'costurera': 'Lucia Fernandez', 'estado': 'finalizado', 'avance': 100, 'dias_inicio': -90, 'dias_entrega': -60, 'dias_creado': -95},
    {'codigo': 'VIR-2026-113', 'cliente': 'Fernanda Castillo', 'tipo_prenda': 'otro', 'costurera': 'Carmen Huaman', 'estado': 'entregado', 'avance': 100, 'dias_inicio': -120, 'dias_entrega': -100, 'dias_creado': -125},
    {'codigo': 'VIR-2026-114', 'cliente': 'Gabriela Soto', 'tipo_prenda': 'vestido_noche', 'costurera': 'Rosa Quispe', 'estado': 'en_proceso', 'avance': 60, 'dias_inicio': -20, 'dias_entrega': 10, 'dias_creado': -25},
    {'codigo': 'VIR-2026-115', 'cliente': 'Daniela Torres', 'tipo_prenda': 'enterizo', 'costurera': None, 'estado': 'pendiente', 'avance': 0, 'dias_inicio': -3, 'dias_entrega': 25, 'dias_creado': -3},
    {'codigo': 'VIR-2026-116', 'cliente': 'Valeria Mendoza', 'tipo_prenda': 'falda', 'costurera': 'Carmen Huaman', 'estado': 'finalizado', 'avance': 100, 'dias_inicio': -150, 'dias_entrega': -130, 'dias_creado': -150},
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
            )
            crear_etapas_estandar(pedido)

            # El estado/avance ya no se fijan a mano: se marcan etapas como
            # completadas segun el 'avance' deseado y se deja que
            # Pedido.recalcular_progreso() derive el resto, igual que en el
            # flujo real de "Actualizar pedido". 'entregado' es la unica
            # excepcion porque esa confirmacion no se puede inferir solo.
            completadas_objetivo = round((data['avance'] / 100) * len(ETAPAS_ESTANDAR))
            for indice, etapa in enumerate(pedido.etapas.order_by('id')):
                if indice < completadas_objetivo:
                    etapa.estado = 'completado'
                    etapa.fecha = pedido.fecha_inicio
                    etapa.save(update_fields=['estado', 'fecha'])

            pedido.recalcular_progreso()
            if data['estado'] == 'entregado':
                pedido.estado = 'entregado'
            pedido.save()

            dias_creado = data.get('dias_creado')
            fecha_creacion = timezone.now()
            if dias_creado is not None:
                fecha_creacion = fecha_creacion + timedelta(days=dias_creado)
                Pedido.objects.filter(pk=pedido.pk).update(creado_en=fecha_creacion)

            coleccion = historial._get_coleccion()
            if coleccion is not None:
                coleccion.insert_one({
                    'pedido_id': pedido.id,
                    'codigo': pedido.codigo,
                    'tipo': 'creacion',
                    'detalle': 'Pedido registrado',
                    'usuario': 'admin',
                    'fecha': fecha_creacion,
                })

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

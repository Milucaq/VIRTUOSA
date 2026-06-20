from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from pedidos.models import Cliente, ConsumoInsumo, Costurera, EtapaPedido, EvidenciaPedido, Insumo, Pedido


class Command(BaseCommand):
    help = 'Carga datos realistas para la demo de Virtuosa Track.'

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin@virtuosa.pe'},
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password('Virtuosa2026!')
        admin.save()

        usuarios_costurera = {
            'sofia.costura': 'Sofia Ramos',
            'elena.alta': 'Elena Valdivia',
            'mariana.ajustes': 'Mariana Paredes',
        }

        usuarios = {}
        for username, nombre in usuarios_costurera.items():
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': nombre.split()[0], 'last_name': nombre.split()[-1]},
            )
            user.is_active = True
            user.set_password('Virtuosa2026!')
            user.save()
            usuarios[username] = user

        costureras_data = [
            ('Sofia Ramos', 'Vestidos de noche y bordados', 'Lunes a viernes, turno tarde', usuarios['sofia.costura']),
            ('Elena Valdivia', 'Sastreria femenina y acabados', 'Lunes a sabado, turno manana', usuarios['elena.alta']),
            ('Mariana Paredes', 'Arreglos personalizados', 'Martes a sabado, medio tiempo', usuarios['mariana.ajustes']),
        ]
        costureras = {}
        for nombre, especialidad, disponibilidad, usuario in costureras_data:
            costurera, _ = Costurera.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'especialidad': especialidad,
                    'disponibilidad': disponibilidad,
                    'activa': True,
                    'usuario': usuario,
                },
            )
            costureras[nombre] = costurera

        clientes_data = [
            ('Valeria Mendoza', '+51 987 334 120', 'valeria.mendoza@email.com', 'Miraflores, Lima', 'Cliente para evento corporativo.'),
            ('Camila Torres', '+51 946 112 884', 'camila.torres@email.com', 'San Isidro, Lima', 'Prefiere telas sostenibles.'),
            ('Luciana Salazar', '+51 995 221 640', 'luciana.salazar@email.com', 'Barranco, Lima', 'Solicita entrega antes del fin de semana.'),
            ('Andrea Castillo', '+51 999 801 345', 'andrea.castillo@email.com', 'Surco, Lima', 'Pedido para ceremonia civil.'),
            ('Renata Flores', '+51 933 554 902', 'renata.flores@email.com', 'La Molina, Lima', 'Requiere prueba presencial.'),
        ]
        clientes = {}
        for nombre, celular, correo, direccion, observaciones in clientes_data:
            cliente, _ = Cliente.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'celular': celular,
                    'correo': correo,
                    'direccion': direccion,
                    'observaciones': observaciones,
                },
            )
            clientes[nombre] = cliente

        today = date.today()
        pedidos_data = [
            {
                'codigo': 'VIR-2026-001',
                'cliente': clientes['Valeria Mendoza'],
                'tipo_prenda': 'vestido_noche',
                'descripcion': 'Vestido de noche en satén verde esmeralda con abertura lateral y escote drapeado.',
                'fecha_inicio': today - timedelta(days=12),
                'fecha_entrega_estimada': today + timedelta(days=4),
                'costurera': costureras['Sofia Ramos'],
                'estado': 'en_proceso',
                'porcentaje_avance': 72,
                'observaciones': 'Primera prueba aprobada. Pendiente ajuste de basta y cierre invisible.',
            },
            {
                'codigo': 'VIR-2026-002',
                'cliente': clientes['Camila Torres'],
                'tipo_prenda': 'blusa_medida',
                'descripcion': 'Blusa a medida en lino organico color marfil, manga francesa y cuello mao.',
                'fecha_inicio': today - timedelta(days=7),
                'fecha_entrega_estimada': today + timedelta(days=8),
                'costurera': costureras['Elena Valdivia'],
                'estado': 'en_proceso',
                'porcentaje_avance': 48,
                'observaciones': 'Corte finalizado. En proceso de ensamblaje.',
            },
            {
                'codigo': 'VIR-2026-003',
                'cliente': clientes['Luciana Salazar'],
                'tipo_prenda': 'falda',
                'descripcion': 'Falda midi plisada en crepé negro para evento formal.',
                'fecha_inicio': today - timedelta(days=5),
                'fecha_entrega_estimada': today + timedelta(days=1),
                'costurera': costureras['Mariana Paredes'],
                'estado': 'retrasado',
                'porcentaje_avance': 65,
                'observaciones': 'Retraso por cambio de pretina solicitado por cliente.',
            },
            {
                'codigo': 'VIR-2026-004',
                'cliente': clientes['Andrea Castillo'],
                'tipo_prenda': 'enterizo',
                'descripcion': 'Enterizo blanco de ceremonia civil con pantalón palazzo y detalle de encaje.',
                'fecha_inicio': today - timedelta(days=15),
                'fecha_entrega_estimada': today - timedelta(days=1),
                'costurera': costureras['Elena Valdivia'],
                'estado': 'finalizado',
                'porcentaje_avance': 100,
                'observaciones': 'Pedido listo para recojo. Control de calidad aprobado.',
            },
            {
                'codigo': 'VIR-2026-005',
                'cliente': clientes['Renata Flores'],
                'tipo_prenda': 'otro',
                'descripcion': 'Ajuste integral de vestido de gala: entalle, basta y refuerzo de tirantes.',
                'fecha_inicio': today - timedelta(days=2),
                'fecha_entrega_estimada': today + timedelta(days=5),
                'costurera': costureras['Mariana Paredes'],
                'estado': 'pendiente',
                'porcentaje_avance': 15,
                'observaciones': 'Medidas registradas. Falta confirmar prueba presencial.',
            },
        ]

        for data in pedidos_data:
            pedido, _ = Pedido.objects.update_or_create(
                codigo=data['codigo'],
                defaults=data,
            )
            self._crear_etapas(pedido)
            self._crear_evidencias(pedido)

        insumos = self._crear_insumos()
        self._crear_consumos(insumos)

        self.stdout.write(self.style.SUCCESS('Datos demo cargados correctamente.'))
        self.stdout.write('Usuarios demo: admin, sofia.costura, elena.alta, mariana.ajustes')
        self.stdout.write('Contrasena para todos: Virtuosa2026!')
        self.stdout.write('Codigos cliente: VIR-2026-001 a VIR-2026-005')

    def _crear_insumos(self):
        insumos_data = [
            ('Saten verde esmeralda', 'Tela principal', 'm', 8.50, 3.00, 'Textiles San Miguel'),
            ('Lino organico marfil', 'Tela sostenible', 'm', 2.00, 2.50, 'EcoTelas Peru'),
            ('Crepe negro premium', 'Tela principal', 'm', 5.75, 2.00, 'Casa Textil Lima'),
            ('Cierre invisible negro', 'Avio', 'und', 12.00, 5.00, 'Merceria Central'),
            ('Hilo poliester marfil', 'Hilo', 'und', 4.00, 6.00, 'Merceria Central'),
            ('Encaje floral blanco', 'Aplicacion', 'm', 1.25, 1.50, 'Encajes del Sur'),
        ]
        insumos = {}
        for nombre, categoria, unidad, stock_actual, stock_minimo, proveedor in insumos_data:
            insumo, _ = Insumo.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'categoria': categoria,
                    'unidad': unidad,
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo,
                    'proveedor': proveedor,
                },
            )
            insumos[nombre] = insumo
        return insumos

    def _crear_consumos(self, insumos):
        consumos_data = [
            ('VIR-2026-001', 'Saten verde esmeralda', 3.20, 'Corte inicial del vestido de noche.'),
            ('VIR-2026-001', 'Cierre invisible negro', 1.00, 'Cierre para espalda.'),
            ('VIR-2026-002', 'Lino organico marfil', 1.80, 'Corte de blusa a medida.'),
            ('VIR-2026-002', 'Hilo poliester marfil', 1.00, 'Costura principal y acabados.'),
            ('VIR-2026-004', 'Encaje floral blanco', 0.80, 'Detalle superior del enterizo.'),
        ]
        for codigo, insumo_nombre, cantidad, observacion in consumos_data:
            pedido = Pedido.objects.get(codigo=codigo)
            insumo = insumos[insumo_nombre]
            ConsumoInsumo.objects.get_or_create(
                pedido=pedido,
                insumo=insumo,
                defaults={
                    'cantidad': cantidad,
                    'observacion': observacion,
                },
            )

    def _crear_etapas(self, pedido):
        etapas_base = [
            ('Registro del pedido', 10),
            ('Toma de medidas', 25),
            ('Corte de tela', 45),
            ('Confeccion principal', 70),
            ('Prueba y ajustes', 85),
            ('Control de calidad', 100),
        ]

        for index, (nombre, umbral) in enumerate(etapas_base):
            if pedido.porcentaje_avance >= umbral:
                estado = 'completado'
                fecha = pedido.fecha_inicio + timedelta(days=index * 2)
                observacion = 'Etapa completada y registrada en el sistema.'
            elif pedido.porcentaje_avance >= max(0, umbral - 20):
                estado = 'en_proceso'
                fecha = None
                observacion = 'Etapa en ejecucion por la costurera asignada.'
            else:
                estado = 'pendiente'
                fecha = None
                observacion = 'Pendiente de iniciar.'

            EtapaPedido.objects.update_or_create(
                pedido=pedido,
                nombre=nombre,
                defaults={
                    'estado': estado,
                    'fecha': fecha,
                    'observacion': observacion,
                },
            )

    def _crear_evidencias(self, pedido):
        etapas = pedido.etapas.exclude(estado='pendiente').order_by('id')

        for index, etapa in enumerate(etapas):
            descripcion = f'Foto demo: {etapa.nombre.lower()} registrada.'
            if EvidenciaPedido.objects.filter(pedido=pedido, etapa=etapa, descripcion=descripcion).exists():
                continue

            imagen_demo = self._imagen_demo_para(pedido, etapa)
            if imagen_demo:
                EvidenciaPedido.objects.create(
                    pedido=pedido,
                    etapa=etapa,
                    imagen=imagen_demo,
                    descripcion=descripcion,
                )
                continue

            image = self._generar_captura_evidencia(pedido, etapa, index)
            buffer = BytesIO()
            image.save(buffer, format='JPEG')

            evidencia = EvidenciaPedido(
                pedido=pedido,
                etapa=etapa,
                descripcion=descripcion,
            )
            evidencia.imagen.save(
                f'{pedido.codigo.lower()}-{etapa.id}-captura.jpg',
                ContentFile(buffer.getvalue()),
                save=True,
            )

    def _imagen_demo_para(self, pedido, etapa):
        etapa_nombre = etapa.nombre.lower()

        if 'control' in etapa_nombre:
            filename = 'control_calidad.png'
        elif 'prueba' in etapa_nombre or 'ajustes' in etapa_nombre:
            filename = 'ajuste_falda.png'
        elif 'confeccion' in etapa_nombre:
            filename = 'costura_blusa.png'
        elif 'corte' in etapa_nombre:
            filename = 'corte_saten.png'
        elif pedido.tipo_prenda == 'vestido_noche':
            filename = 'corte_saten.png'
        elif pedido.tipo_prenda == 'blusa_medida':
            filename = 'costura_blusa.png'
        elif pedido.tipo_prenda == 'falda':
            filename = 'ajuste_falda.png'
        else:
            filename = 'control_calidad.png'

        relative_path = f'demo_evidencias/{filename}'
        absolute_path = Path(settings.MEDIA_ROOT) / relative_path
        if absolute_path.exists():
            return relative_path
        return None

    def _generar_captura_evidencia(self, pedido, etapa, index):
        colores = [
            ((248, 245, 246), (155, 79, 117), (239, 215, 228)),
            ((245, 247, 241), (91, 130, 96), (219, 237, 221)),
            ((246, 243, 237), (130, 99, 70), (234, 222, 204)),
            ((241, 245, 248), (66, 104, 128), (213, 229, 239)),
        ]
        fondo, principal, suave = colores[index % len(colores)]

        image = Image.new('RGB', (900, 650), color=fondo)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 900, 118), fill=principal)
        draw.text((40, 38), 'Virtuosa Track', fill=(255, 255, 255))
        draw.text((40, 158), f'Pedido: {pedido.codigo}', fill=(61, 37, 48))
        draw.text((40, 205), f'Cliente: {pedido.cliente.nombre}', fill=(61, 37, 48))
        draw.text((40, 252), f'Etapa: {etapa.nombre}', fill=(61, 37, 48))
        draw.text((40, 299), f'Estado: {etapa.get_estado_display()}', fill=principal)
        draw.text((40, 346), f'Avance general: {pedido.porcentaje_avance}%', fill=principal)

        draw.rounded_rectangle((520, 170, 815, 505), radius=18, fill=suave, outline=principal, width=4)
        draw.rectangle((575, 225, 760, 430), fill=fondo, outline=principal, width=3)
        draw.line((575, 290, 760, 290), fill=principal, width=3)
        draw.line((615, 225, 615, 430), fill=principal, width=3)
        draw.line((720, 225, 720, 430), fill=principal, width=3)
        draw.text((553, 535), 'Captura referencial de avance', fill=(80, 80, 80))

        draw.rectangle((40, 465, 430, 485), fill=suave)
        progress_width = int(390 * min(pedido.porcentaje_avance, 100) / 100)
        draw.rectangle((40, 465, 40 + progress_width, 485), fill=principal)
        draw.text((40, 515), etapa.observacion or 'Observacion registrada en la etapa.', fill=(80, 80, 80))

        return image

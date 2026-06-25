from functools import wraps
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth
from .models import Pedido, Costurera, Cliente, EtapaPedido, Insumo
from . import historial
from .forms import (
    PedidoForm,
    EtapaPedidoForm,
    EtapaActualForm,
    EvidenciaRapidaForm,
    NuevaObservacionForm,
    InsumoForm,
    ConsumoInsumoForm,
    CostureraForm,
    ClienteForm,
)


def admin_required(view_func):
    """Permite el acceso solo a usuarios staff (admin); a las costureras las
    manda directo a su panel en lugar de a las secciones de administración."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        return redirect('panel_costurera')
    return wrapper


ETAPAS_ESTANDAR = [
    'Registro del pedido',
    'Toma de medidas',
    'Corte de tela',
    'Confeccion principal',
    'Prueba y ajustes',
    'Control de calidad',
]


def crear_etapas_estandar(pedido):
    for index, nombre in enumerate(ETAPAS_ESTANDAR):
        estado = 'completado' if index == 0 else 'pendiente'
        EtapaPedido.objects.get_or_create(
            pedido=pedido,
            nombre=nombre,
            defaults={
                'estado': estado,
                'fecha': pedido.fecha_inicio if index == 0 else None,
                'observacion': 'Etapa generada automaticamente por el flujo de trazabilidad.',
            },
        )


@admin_required
def dashboard(request):
    total_en_proceso = Pedido.objects.filter(estado='en_proceso').count()
    total_finalizados = Pedido.objects.filter(estado='finalizado').count()
    total_retrasados = Pedido.objects.filter(estado='retrasado').count()
    total_clientes = Pedido.objects.values('cliente').distinct().count()

    avance_promedio = Pedido.objects.aggregate(
        promedio=Avg('porcentaje_avance')
    )['promedio'] or 0

    pedidos_recientes = Pedido.objects.order_by('-creado_en')[:6]
    proximos_vencer = Pedido.objects.exclude(
        estado__in=['finalizado', 'entregado']
    ).order_by('fecha_entrega_estimada')[:5]
    carga_costureras = Costurera.objects.annotate(
        pedidos_asignados=Count('pedido')
    ).order_by('-pedidos_asignados')[:5]

    retrasados_por_costurera = Costurera.objects.annotate(
        total_retrasados=Count('pedido', filter=Q(pedido__estado='retrasado'))
    ).filter(total_retrasados__gt=0).order_by('-total_retrasados')[:6]

    pedidos_por_mes = (
        Pedido.objects.annotate(mes=TruncMonth('creado_en'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    tiempo_por_etapa = historial.promedio_duracion_por_etapa()[:8]

    contexto = {
        'total_en_proceso': total_en_proceso,
        'total_finalizados': total_finalizados,
        'total_retrasados': total_retrasados,
        'total_clientes': total_clientes,
        'avance_promedio': round(avance_promedio),
        'pedidos_recientes': pedidos_recientes,
        'proximos_vencer': proximos_vencer,
        'carga_costureras': carga_costureras,
        'retrasados_labels': [c.nombre for c in retrasados_por_costurera],
        'retrasados_data': [c.total_retrasados for c in retrasados_por_costurera],
        'pedidos_mes_labels': [p['mes'].strftime('%b %Y') for p in pedidos_por_mes],
        'pedidos_mes_data': [p['total'] for p in pedidos_por_mes],
        'etapas_labels': [e['etapa'] for e in tiempo_por_etapa],
        'etapas_data': [e['horas_promedio'] for e in tiempo_por_etapa],
    }

    return render(request, 'pedidos/dashboard.html', contexto)


@admin_required
def crear_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            crear_etapas_estandar(pedido)
            pedido.recalcular_progreso()
            pedido.save()
            historial.registrar_evento(pedido, 'creacion', 'Pedido registrado', request.user)
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = PedidoForm()

    return render(request, 'pedidos/pedido_form.html', {'form': form})


@admin_required
def lista_pedidos(request):
    pedidos = Pedido.objects.select_related('cliente', 'costurera').order_by('-creado_en')
    estado = request.GET.get('estado')
    costurera_id = request.GET.get('costurera')
    q = request.GET.get('q')

    if estado:
        pedidos = pedidos.filter(estado=estado)
    if costurera_id:
        pedidos = pedidos.filter(costurera_id=costurera_id)
    if q:
        pedidos = pedidos.filter(Q(codigo__icontains=q) | Q(cliente__nombre__icontains=q))

    return render(request, 'pedidos/lista_pedidos.html', {
        'pedidos': pedidos,
        'costureras': Costurera.objects.filter(activa=True),
        'estados': Pedido.ESTADOS,
        'filtros': {
            'estado': estado or '',
            'costurera': costurera_id or '',
            'q': q or '',
        },
    })


@login_required
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    etapas = pedido.etapas.all().order_by('id')
    evidencias = pedido.evidencias.all().order_by('-fecha_subida')

    return render(request, 'pedidos/pedido_detail.html', {
        'pedido': pedido,
        'etapas': etapas,
        'evidencias': evidencias,
        'consumos': pedido.consumos.select_related('insumo').order_by('-fecha'),
        'historial_eventos': historial.obtener_historial(pedido.id),
        'observaciones_registradas': historial.obtener_observaciones(pedido.id),
    })


@login_required
def agregar_etapa(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        form = EtapaPedidoForm(request.POST)
        if form.is_valid():
            etapa = form.save(commit=False)
            etapa.pedido = pedido
            etapa.save()
            pedido.recalcular_progreso()
            pedido.save()
            historial.registrar_evento(pedido, 'etapa_agregada', etapa.nombre, request.user)
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = EtapaPedidoForm()

    return render(request, 'pedidos/etapa_form.html', {
        'form': form,
        'pedido': pedido,
    })


@login_required
def registrar_consumo(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        form = ConsumoInsumoForm(request.POST)
        if form.is_valid():
            consumo = form.save(commit=False)
            consumo.pedido = pedido
            consumo.save()
            insumo = consumo.insumo
            insumo.stock_actual = insumo.stock_actual - consumo.cantidad
            insumo.save()
            historial.registrar_evento(
                pedido,
                'consumo_registrado',
                f'{insumo.nombre}: -{consumo.cantidad} {insumo.get_unidad_display()}',
                request.user,
            )
            messages.success(request, f'Consumo registrado para {pedido.codigo}.')
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = ConsumoInsumoForm()

    return render(request, 'pedidos/consumo_form.html', {
        'form': form,
        'pedido': pedido,
    })


@login_required
def inventario(request):
    insumos = Insumo.objects.order_by('categoria', 'nombre')
    total_stock_bajo = sum(1 for insumo in insumos if insumo.stock_bajo)

    return render(request, 'pedidos/inventario.html', {
        'insumos': insumos,
        'total_stock_bajo': total_stock_bajo,
    })


@admin_required
def crear_insumo(request):
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventario')
    else:
        form = InsumoForm()

    return render(request, 'pedidos/insumo_form.html', {'form': form})


@admin_required
def lista_costureras(request):
    costureras = Costurera.objects.annotate(
        pedidos_asignados=Count('pedido')
    ).order_by('nombre')

    return render(request, 'pedidos/costurera_list.html', {
        'costureras': costureras,
    })


@admin_required
def crear_costurera(request):
    if request.method == 'POST':
        form = CostureraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Costurera registrada correctamente.')
            return redirect('lista_costureras')
    else:
        form = CostureraForm()

    return render(request, 'pedidos/costurera_form.html', {'form': form})


@admin_required
def editar_costurera(request, costurera_id):
    costurera = get_object_or_404(Costurera, id=costurera_id)

    if request.method == 'POST':
        form = CostureraForm(request.POST, instance=costurera)
        if form.is_valid():
            form.save()
            messages.success(request, 'Costurera actualizada correctamente.')
            return redirect('lista_costureras')
    else:
        form = CostureraForm(instance=costurera)

    return render(request, 'pedidos/costurera_form.html', {
        'form': form,
        'costurera': costurera,
    })


@admin_required
def eliminar_costurera(request, costurera_id):
    costurera = get_object_or_404(Costurera, id=costurera_id)

    if request.method == 'POST':
        nombre = costurera.nombre
        costurera.delete()
        messages.success(request, f'Costurera {nombre} eliminada.')
        return redirect('lista_costureras')

    return render(request, 'pedidos/costurera_confirm_delete.html', {
        'costurera': costurera,
    })


@admin_required
def lista_clientes(request):
    clientes = Cliente.objects.annotate(
        pedidos_realizados=Count('pedido')
    ).order_by('nombre')

    return render(request, 'pedidos/cliente_list.html', {
        'clientes': clientes,
    })


@admin_required
def crear_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente registrado correctamente.')
            return redirect('lista_clientes')
    else:
        form = ClienteForm()

    return render(request, 'pedidos/cliente_form.html', {'form': form})


@admin_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'pedidos/cliente_form.html', {
        'form': form,
        'cliente': cliente,
    })


@admin_required
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    pedidos_asociados = Pedido.objects.filter(cliente=cliente).count()

    if request.method == 'POST':
        nombre = cliente.nombre
        cliente.delete()
        messages.success(request, f'Cliente {nombre} eliminado.')
        return redirect('lista_clientes')

    return render(request, 'pedidos/cliente_confirm_delete.html', {
        'cliente': cliente,
        'pedidos_asociados': pedidos_asociados,
    })


@login_required
def panel_costurera(request):
    costurera = None

    try:
        costurera = Costurera.objects.get(usuario=request.user)
        pedidos = Pedido.objects.filter(costurera=costurera).order_by('-creado_en')
    except Costurera.DoesNotExist:
        if request.user.is_staff:
            pedidos = Pedido.objects.exclude(
                estado__in=['finalizado', 'entregado']
            ).order_by('fecha_entrega_estimada')
        else:
            pedidos = Pedido.objects.none()

    return render(request, 'pedidos/panel_costurera.html', {
        'costurera': costurera,
        'pedidos': pedidos,
    })


def _es_responsable_del_pedido(user, pedido):
    if user.is_staff:
        return True
    return bool(pedido.costurera and pedido.costurera.usuario_id == user.id)


@login_required
def actualizar_progreso_pedido(request, pedido_id):
    """Pantalla unica para mover el progreso de un pedido: avanzar la etapa
    actual, subir evidencia opcional y anotar observaciones. Las etapas ya
    completadas quedan bloqueadas (no se puede retroceder) y solo la etapa
    vigente es editable. El % de avance y el estado general ya no se escriben
    a mano aqui,
    se derivan de las etapas via Pedido.recalcular_progreso()."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    etapas = list(pedido.etapas.order_by('id'))
    etapa_actual = next((e for e in etapas if e.estado != 'completado'), None)

    if request.method == 'POST':
        etapa_form = EtapaActualForm(request.POST, prefix='etapa') if etapa_actual else None
        evidencia_form = EvidenciaRapidaForm(request.POST, request.FILES, prefix='evidencia')
        obs_form = NuevaObservacionForm(request.POST, prefix='obs')

        if (etapa_form is None or etapa_form.is_valid()) and evidencia_form.is_valid() and obs_form.is_valid():
            if etapa_actual:
                etapa_actual.estado = etapa_form.cleaned_data['estado']
                if etapa_actual.estado == 'completado' and not etapa_actual.fecha:
                    etapa_actual.fecha = timezone.now().date()
                etapa_actual.save(update_fields=['estado', 'fecha'])

            pedido.recalcular_progreso()
            pedido.save()

            if evidencia_form.cleaned_data.get('imagen'):
                evidencia = evidencia_form.save(commit=False)
                evidencia.pedido = pedido
                evidencia.save()

            texto_obs = obs_form.cleaned_data.get('texto')
            if texto_obs:
                historial.registrar_evento(pedido, 'observacion', texto_obs, request.user)

            historial.registrar_evento(
                pedido,
                'avance_actualizado',
                f'{pedido.get_estado_display()} · {pedido.porcentaje_avance}%',
                request.user,
            )
            messages.success(request, f'Progreso del pedido {pedido.codigo} actualizado.')
            if request.user.is_staff:
                return redirect('detalle_pedido', pedido_id=pedido.id)
            return redirect('panel_costurera')
    else:
        etapa_form = EtapaActualForm(prefix='etapa', initial={'estado': etapa_actual.estado if etapa_actual and etapa_actual.estado != 'pendiente' else 'en_proceso'}) if etapa_actual else None
        evidencia_form = EvidenciaRapidaForm(prefix='evidencia')
        obs_form = NuevaObservacionForm(prefix='obs')

    return render(request, 'pedidos/avance_pedido_form.html', {
        'pedido': pedido,
        'etapas': etapas,
        'etapa_actual': etapa_actual,
        'etapa_form': etapa_form,
        'evidencia_form': evidencia_form,
        'obs_form': obs_form,
    })


@login_required
@require_POST
def marcar_entregado(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if not _es_responsable_del_pedido(request.user, pedido):
        messages.error(request, 'No tienes permiso para marcar este pedido como entregado.')
        return redirect('detalle_pedido', pedido_id=pedido.id)

    if pedido.estado != 'finalizado':
        messages.error(request, 'El pedido debe estar finalizado (todas las etapas completadas) antes de marcarlo como entregado.')
        return redirect('detalle_pedido', pedido_id=pedido.id)

    pedido.estado = 'entregado'
    pedido.save()
    historial.registrar_evento(pedido, 'avance_actualizado', 'Entregado al cliente', request.user)
    messages.success(request, f'Pedido {pedido.codigo} marcado como entregado.')
    return redirect('detalle_pedido', pedido_id=pedido.id)


@ensure_csrf_cookie
def consulta_cliente(request):
    pedido = None
    codigo = request.GET.get('codigo')

    if codigo:
        pedido = (
            Pedido.objects
            .filter(codigo__iexact=codigo)
            .select_related('cliente')
            .prefetch_related('etapas', 'evidencias')
            .first()
        )

    return render(request, 'pedidos/consulta_cliente.html', {
        'pedido': pedido,
        'codigo': codigo,
        'base_template': 'base.html' if request.user.is_authenticated else 'cliente_base.html',
    })


# === Chatbot del cliente (hibrido: reglas + IA) ===
import json as _json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from . import chatbot


@require_POST
def chatbot_responder(request):
    """Recibe {'mensaje': '...'} por POST y devuelve {'respuesta','codigo'}."""
    try:
        body = _json.loads(request.body.decode('utf-8'))
        mensaje = body.get('mensaje', '')
    except (ValueError, AttributeError):
        mensaje = ''
    return JsonResponse(chatbot.responder_detallado(mensaje))


@ensure_csrf_cookie
def inicio_cliente(request):
    """Pagina publica de bienvenida con el chat como entrada (Opcion A)."""
    return render(request, 'cliente/inicio.html')

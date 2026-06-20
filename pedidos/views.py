from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from .models import Pedido, Costurera, EtapaPedido, Insumo
from .forms import (
    PedidoForm,
    EtapaPedidoForm,
    EvidenciaPedidoForm,
    AvancePedidoForm,
    InsumoForm,
    ConsumoInsumoForm,
)


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


@login_required
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

    contexto = {
        'total_en_proceso': total_en_proceso,
        'total_finalizados': total_finalizados,
        'total_retrasados': total_retrasados,
        'total_clientes': total_clientes,
        'avance_promedio': round(avance_promedio),
        'pedidos_recientes': pedidos_recientes,
        'proximos_vencer': proximos_vencer,
        'carga_costureras': carga_costureras,
    }

    return render(request, 'pedidos/dashboard.html', contexto)


@login_required
def crear_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            crear_etapas_estandar(pedido)
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = PedidoForm()

    return render(request, 'pedidos/pedido_form.html', {'form': form})


@login_required
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
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = EtapaPedidoForm()

    return render(request, 'pedidos/etapa_form.html', {
        'form': form,
        'pedido': pedido,
    })


@login_required
def agregar_evidencia(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        form = EvidenciaPedidoForm(request.POST, request.FILES)
        if form.is_valid():
            evidencia = form.save(commit=False)
            evidencia.pedido = pedido
            evidencia.save()
            return redirect('detalle_pedido', pedido_id=pedido.id)
    else:
        form = EvidenciaPedidoForm()

    return render(request, 'pedidos/evidencia_form.html', {
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


@login_required
def crear_insumo(request):
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventario')
    else:
        form = InsumoForm()

    return render(request, 'pedidos/insumo_form.html', {'form': form})


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


@login_required
def actualizar_avance_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        form = AvancePedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, f'Avance del pedido {pedido.codigo} actualizado.')
            return redirect('panel_costurera')
    else:
        form = AvancePedidoForm(instance=pedido)

    return render(request, 'pedidos/avance_pedido_form.html', {
        'form': form,
        'pedido': pedido,
    })


def consulta_cliente(request):
    pedido = None
    codigo = request.GET.get('codigo')

    if codigo:
        pedido = Pedido.objects.filter(codigo__iexact=codigo).first()

    return render(request, 'pedidos/consulta_cliente.html', {
        'pedido': pedido,
        'codigo': codigo,
    })

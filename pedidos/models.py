from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=120)
    celular = models.CharField(max_length=20)
    correo = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Costurera(models.Model):
    nombre = models.CharField(max_length=120)
    especialidad = models.CharField(max_length=120, blank=True, null=True)
    disponibilidad = models.CharField(max_length=120, blank=True, null=True)
    activa = models.BooleanField(default=True)
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('finalizado', 'Finalizado'),
        ('retrasado', 'Retrasado'),
        ('entregado', 'Entregado'),
    ]

    TIPOS_PRENDA = [
        ('vestido_noche', 'Vestido de noche'),
        ('blusa_medida', 'Blusa a medida'),
        ('falda', 'Falda'),
        ('enterizo', 'Enterizo'),
        ('otro', 'Otro'),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo_prenda = models.CharField(max_length=50, choices=TIPOS_PRENDA)
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    fecha_entrega_estimada = models.DateField()
    costurera = models.ForeignKey(
        Costurera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente')
    porcentaje_avance = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generar_codigo(cls):
        year = timezone.now().year
        prefix = f'VIR-{year}-'
        ultimo = cls.objects.filter(codigo__startswith=prefix).order_by('-codigo').first()

        if ultimo:
            try:
                siguiente = int(ultimo.codigo.split('-')[-1]) + 1
            except ValueError:
                siguiente = 1
        else:
            siguiente = 1

        return f'{prefix}{siguiente:03d}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.cliente.nombre}"


class Insumo(models.Model):
    UNIDADES = [
        ('m', 'Metros'),
        ('und', 'Unidades'),
        ('rollo', 'Rollos'),
    ]

    nombre = models.CharField(max_length=120)
    categoria = models.CharField(max_length=80)
    unidad = models.CharField(max_length=20, choices=UNIDADES, default='und')
    stock_actual = models.DecimalField(max_digits=8, decimal_places=2)
    stock_minimo = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    proveedor = models.CharField(max_length=120, blank=True, null=True)

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo

    def __str__(self):
        return self.nombre


class ConsumoInsumo(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='consumos')
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='consumos')
    cantidad = models.DecimalField(max_digits=8, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    observacion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.pedido.codigo} - {self.insumo.nombre}"


class EtapaPedido(models.Model):
    ESTADOS_ETAPA = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('completado', 'Completado'),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='etapas')
    nombre = models.CharField(max_length=120)
    estado = models.CharField(max_length=30, choices=ESTADOS_ETAPA, default='pendiente')
    fecha = models.DateField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.pedido.codigo} - {self.nombre}"


class EvidenciaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='evidencias')
    etapa = models.ForeignKey(
        EtapaPedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    imagen = models.ImageField(upload_to='evidencias/')
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidencia {self.pedido.codigo}"

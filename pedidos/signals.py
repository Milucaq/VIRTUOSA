import logging

import requests
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Pedido

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def _enviar_correo_brevo(asunto, mensaje, destinatario):
    """Envia el correo via la API HTTPS de Brevo en vez de SMTP: Render
    bloquea los puertos salientes 587/465, lo que dejaba la conexion SMTP
    colgada hasta tumbar el worker de gunicorn por timeout."""
    if not settings.BREVO_API_KEY:
        return

    try:
        respuesta = requests.post(
            BREVO_API_URL,
            headers={
                'api-key': settings.BREVO_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={
                'sender': {'email': settings.DEFAULT_FROM_EMAIL},
                'to': [{'email': destinatario}],
                'subject': asunto,
                'textContent': mensaje,
            },
            timeout=10,
        )
        respuesta.raise_for_status()
    except Exception:
        logger.warning('No se pudo enviar el correo de notificación vía Brevo.', exc_info=True)


ESTADOS_NOTIFICABLES = {'retrasado', 'finalizado', 'entregado'}
ESTADOS_TODO_COMPLETADO = {'finalizado', 'entregado'}


@receiver(post_save, sender=Pedido)
def _sincronizar_etapas_con_avance(sender, instance, created, **kwargs):
    """Marca las etapas del pedido como completado/en_proceso/pendiente en
    proporcion al porcentaje_avance general, para que la linea de tiempo del
    detalle de pedido no se quede congelada en su estado inicial."""
    if created:
        return

    etapas = list(instance.etapas.order_by('id'))
    total = len(etapas)
    if not total:
        return

    if instance.estado in ESTADOS_TODO_COMPLETADO:
        completadas = total
    else:
        completadas = round((instance.porcentaje_avance / 100) * total)
        completadas = max(0, min(completadas, total))

    hoy = timezone.now().date()
    for index, etapa in enumerate(etapas):
        if index < completadas:
            nuevo_estado = 'completado'
        elif index == completadas and instance.porcentaje_avance > 0:
            nuevo_estado = 'en_proceso'
        else:
            nuevo_estado = 'pendiente'

        if etapa.estado == nuevo_estado:
            continue

        etapa.estado = nuevo_estado
        if nuevo_estado == 'completado' and not etapa.fecha:
            etapa.fecha = hoy
        etapa.save(update_fields=['estado', 'fecha'])


@receiver(pre_save, sender=Pedido)
def _capturar_estado_anterior(sender, instance, **kwargs):
    """Guarda el estado que tenia el pedido antes de este save, para poder
    comparar en post_save y detectar si realmente cambio."""
    if not instance.pk:
        instance._estado_anterior = None
        return

    try:
        instance._estado_anterior = Pedido.objects.get(pk=instance.pk).estado
    except Pedido.DoesNotExist:
        instance._estado_anterior = None


@receiver(post_save, sender=Pedido)
def _notificar_cambio_estado(sender, instance, created, **kwargs):
    estado_anterior = getattr(instance, '_estado_anterior', None)

    if created or estado_anterior == instance.estado:
        return
    if instance.estado not in ESTADOS_NOTIFICABLES:
        return
    if not settings.NOTIFICATION_EMAIL:
        return

    asunto = f'Virtuosa Track · Pedido {instance.codigo} ahora está "{instance.get_estado_display()}"'
    mensaje = (
        f'El pedido {instance.codigo} ({instance.cliente.nombre}) cambió de estado:\n'
        f'  {estado_anterior} -> {instance.estado}\n\n'
        f'Avance actual: {instance.porcentaje_avance}%\n'
        f'Entrega estimada: {instance.fecha_entrega_estimada}\n'
    )

    _enviar_correo_brevo(asunto, mensaje, settings.NOTIFICATION_EMAIL)

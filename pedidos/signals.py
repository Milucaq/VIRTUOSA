import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Pedido

logger = logging.getLogger(__name__)

ESTADOS_NOTIFICABLES = {'retrasado', 'finalizado'}


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

    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [settings.NOTIFICATION_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.warning('No se pudo enviar el correo de notificación.', exc_info=True)

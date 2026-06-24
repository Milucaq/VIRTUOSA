import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_client = None


def _get_coleccion():
    """Devuelve la colección de Mongo, o None si no está configurada/disponible.
    El historial es un complemento de trazabilidad: si Mongo falla, no debe
    romper el flujo principal de pedidos (que vive en la base relacional)."""
    global _client

    if not settings.MONGO_URI:
        return None

    if _client is None:
        try:
            import pymongo
            _client = pymongo.MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        except Exception:
            logger.warning('No se pudo conectar a MongoDB para el historial.', exc_info=True)
            return None

    return _client[settings.MONGO_DB_NAME]['historial_pedidos']


def registrar_evento(pedido, tipo, detalle='', usuario=None):
    coleccion = _get_coleccion()
    if coleccion is None:
        return

    try:
        coleccion.insert_one({
            'pedido_id': pedido.id,
            'codigo': pedido.codigo,
            'tipo': tipo,
            'detalle': detalle,
            'usuario': usuario.get_username() if usuario and usuario.is_authenticated else None,
            'fecha': timezone.now(),
        })
    except Exception:
        logger.warning('No se pudo registrar el evento de historial en MongoDB.', exc_info=True)


def promedio_duracion_por_etapa():
    """Calcula, para cada etapa, el tiempo promedio (en horas) transcurrido
    desde el evento anterior del pedido hasta que esa etapa se registró.
    Sirve para detectar cuellos de botella en el proceso de confección."""
    coleccion = _get_coleccion()
    if coleccion is None:
        return []

    try:
        eventos = list(
            coleccion.find({'tipo': {'$in': ['creacion', 'etapa_agregada']}})
            .sort([('pedido_id', 1), ('fecha', 1)])
        )
    except Exception:
        logger.warning('No se pudo calcular la duración por etapa desde MongoDB.', exc_info=True)
        return []

    duraciones_por_etapa = {}
    evento_anterior_por_pedido = {}

    for evento in eventos:
        pedido_id = evento['pedido_id']
        anterior = evento_anterior_por_pedido.get(pedido_id)

        if anterior is not None and evento['tipo'] == 'etapa_agregada':
            horas = (evento['fecha'] - anterior['fecha']).total_seconds() / 3600
            nombre = evento.get('detalle') or 'Etapa sin nombre'
            duraciones_por_etapa.setdefault(nombre, []).append(horas)

        evento_anterior_por_pedido[pedido_id] = evento

    resultado = [
        {'etapa': nombre, 'horas_promedio': round(sum(valores) / len(valores), 1)}
        for nombre, valores in duraciones_por_etapa.items()
    ]
    return sorted(resultado, key=lambda item: -item['horas_promedio'])


def obtener_historial(pedido_id, limite=20):
    coleccion = _get_coleccion()
    if coleccion is None:
        return []

    try:
        return list(
            coleccion.find({'pedido_id': pedido_id})
            .sort('fecha', -1)
            .limit(limite)
        )
    except Exception:
        logger.warning('No se pudo leer el historial desde MongoDB.', exc_info=True)
        return []

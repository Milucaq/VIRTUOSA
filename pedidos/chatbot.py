"""
Chatbot hibrido para la consulta de pedidos de clientes (Virtuosa).

Estrategia:
1. REGLAS (siempre funcionan, sin internet): detectamos el codigo del pedido en
   el mensaje, consultamos la base de datos y armamos una respuesta exacta.
   Tambien respondemos preguntas frecuentes con respuestas predefinidas.
2. IA (opcional): si hay un token de Hugging Face configurado, le pedimos al
   modelo que REDACTE de forma natural usando SOLO los datos reales del pedido.
   Si la IA falla o no esta configurada, devolvemos la respuesta por reglas.

De esta forma el bot nunca inventa datos y nunca se queda "mudo" en una demo.
"""

import re
import json
import urllib.request
import urllib.error

from django.conf import settings

from .models import Pedido


# ---------------------------------------------------------------------------
# 1) REGLAS: extraer codigo y construir la respuesta factual desde la BD
# ---------------------------------------------------------------------------

# Acepta "VIR-2026-001", "vir 2026 1", "VIR2026001", etc.
CODIGO_REGEX = re.compile(r'vir[\s\-_]*(\d{4})[\s\-_]*(\d{1,4})', re.IGNORECASE)


def extraer_codigo(mensaje):
    """Devuelve el codigo normalizado tipo 'VIR-2026-001' o None."""
    match = CODIGO_REGEX.search(mensaje or '')
    if not match:
        return None
    anio, numero = match.group(1), match.group(2)
    return f'VIR-{anio}-{int(numero):03d}'


def buscar_pedido(codigo):
    if not codigo:
        return None
    return (
        Pedido.objects
        .filter(codigo__iexact=codigo)
        .select_related('cliente')
        .prefetch_related('etapas')
        .first()
    )


def datos_pedido(pedido):
    """Empaqueta los datos reales del pedido (la 'verdad' para el modelo)."""
    etapas = list(pedido.etapas.all().order_by('id'))
    etapa_actual = next((e for e in etapas if e.estado == 'en_proceso'), None)
    completadas = [e for e in etapas if e.estado == 'completado']

    return {
        'codigo': pedido.codigo,
        'cliente': pedido.cliente.nombre,
        'prenda': pedido.get_tipo_prenda_display(),
        'estado': pedido.get_estado_display(),
        'avance': pedido.porcentaje_avance,
        'entrega_estimada': pedido.fecha_entrega_estimada.strftime('%d/%m/%Y'),
        'etapa_actual': etapa_actual.nombre if etapa_actual else (
            completadas[-1].nombre if completadas else 'Registro del pedido'
        ),
        'observacion': pedido.observaciones or '',
    }


def respuesta_reglas_pedido(d):
    """Respuesta determinista a partir de los datos del pedido."""
    texto = (
        f"Tu pedido {d['codigo']} ({d['prenda']}) esta en estado "
        f"\"{d['estado']}\" con un avance del {d['avance']}%. "
        f"Actualmente se encuentra en la etapa de {d['etapa_actual'].lower()}. "
        f"La entrega estimada es el {d['entrega_estimada']}."
    )
    if d['observacion']:
        texto += f" Nota del equipo: {d['observacion']}"
    return texto


# Preguntas frecuentes (sin pedido). Palabras clave -> respuesta.
FAQS = [
    (('cuanto', 'demora', 'tiempo', 'tarda', 'cuando estara', 'cuando esta'),
     "Los tiempos dependen del tipo de prenda y la complejidad. Si me das el codigo "
     "de tu pedido (por ejemplo VIR-2026-001) te digo la fecha estimada exacta."),
    (('precio', 'costo', 'cuanto cuesta', 'tarifa', 'pagar'),
     "Los precios se cotizan segun la prenda y los materiales. Para una cotizacion "
     "personalizada, comunicate con el equipo de Virtuosa."),
    (('horario', 'atienden', 'abren', 'cierran'),
     "Puedes consultar el avance de tu pedido aqui las 24 horas ingresando tu codigo. "
     "Para atencion presencial, contacta directamente con el taller."),
    (('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches'),
     "Hola, soy el asistente de Virtuosa. Puedo ayudarte a consultar el avance de tu "
     "pedido. Escribeme tu codigo, por ejemplo: VIR-2026-001."),
    (('gracias', 'muchas gracias'),
     "Con gusto. Si necesitas algo mas sobre tu pedido, aqui estoy."),
]


def respuesta_faq(mensaje):
    m = (mensaje or '').lower()
    for claves, respuesta in FAQS:
        if any(c in m for c in claves):
            return respuesta
    return None


# ---------------------------------------------------------------------------
# 2) IA (opcional): redactar de forma natural con un modelo de Hugging Face
# ---------------------------------------------------------------------------

def redactar_con_ia(mensaje_usuario, datos):
    """
    Pide al modelo que redacte una respuesta amable usando SOLO 'datos'.
    Devuelve el texto del modelo, o None si no hay token o algo falla.
    """
    token = getattr(settings, 'HF_TOKEN', '')
    if not token:
        return None  # sin token -> usamos reglas

    modelo = getattr(settings, 'HF_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
    url = 'https://router.huggingface.co/v1/chat/completions'

    contexto = json.dumps(datos, ensure_ascii=False) if datos else 'sin datos de pedido'
    system = (
        "Eres el asistente virtual de Virtuosa, un taller de alta costura. "
        "Respondes en espanol, con tono calido, breve y profesional. "
        "Usa UNICAMENTE la informacion del pedido que se te entrega; no inventes "
        "datos, fechas ni estados. Si no hay datos del pedido, pide amablemente el "
        "codigo (formato VIR-2026-001). No reveles informacion interna ni de otros clientes."
    )
    user = (
        f"Datos reales del pedido (en JSON): {contexto}\n\n"
        f"Mensaje del cliente: {mensaje_usuario}\n\n"
        f"Redacta una respuesta breve y amable basada solo en esos datos."
    )

    payload = json.dumps({
        'model': modelo,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.3,
        'max_tokens': 220,
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data['choices'][0]['message']['content'].strip()
    except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError):
        # Cualquier fallo de red, cuota agotada o respuesta inesperada -> reglas
        return None


# ---------------------------------------------------------------------------
# 3) Orquestador: une reglas + IA
# ---------------------------------------------------------------------------

def responder_detallado(mensaje):
    """
    Devuelve un dict {'respuesta': str, 'codigo': str|None}.
    'codigo' solo se rellena cuando se encontro un pedido real (para enlazar
    al detalle desde el chat).
    """
    mensaje = (mensaje or '').strip()
    if not mensaje:
        return {'respuesta': (
            "Hola, soy el asistente de Virtuosa. Escribeme el codigo de tu "
            "pedido (por ejemplo VIR-2026-001) y te cuento como va."), 'codigo': None}

    codigo = extraer_codigo(mensaje)

    if codigo:
        pedido = buscar_pedido(codigo)
        if not pedido:
            return {'respuesta': (
                f"No encontre ningun pedido con el codigo {codigo}. "
                f"Verifica el codigo o comunicate con Virtuosa."), 'codigo': None}
        datos = datos_pedido(pedido)
        texto_ia = redactar_con_ia(mensaje, datos)
        return {'respuesta': texto_ia or respuesta_reglas_pedido(datos),
                'codigo': pedido.codigo}

    faq = respuesta_faq(mensaje)
    if faq:
        return {'respuesta': faq, 'codigo': None}

    texto_ia = redactar_con_ia(mensaje, None)
    return {'respuesta': texto_ia or (
        "Puedo ayudarte a consultar el avance de tu pedido. Escribeme tu codigo, "
        "por ejemplo: VIR-2026-001."), 'codigo': None}


def responder(mensaje):
    """Compatibilidad: devuelve solo el texto."""
    return responder_detallado(mensaje)['respuesta']
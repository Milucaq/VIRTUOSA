from django import forms
from .models import Cliente, Costurera, Pedido, EtapaPedido, EvidenciaPedido, Insumo, ConsumoInsumo


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'


class CostureraForm(forms.ModelForm):
    class Meta:
        model = Costurera
        fields = '__all__'


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            'cliente',
            'tipo_prenda',
            'descripcion',
            'fecha_inicio',
            'fecha_entrega_estimada',
            'costurera',
            'estado',
            'porcentaje_avance',
            'observaciones',
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_entrega_estimada': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }


class EtapaPedidoForm(forms.ModelForm):
    class Meta:
        model = EtapaPedido
        fields = [
            'nombre',
            'estado',
            'fecha',
            'observacion',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'observacion': forms.Textarea(attrs={'rows': 3}),
        }


class EtapaEstadoForm(forms.ModelForm):
    """Una fila del formset de 'Actualizar pedido': solo el estado de la
    etapa es editable ahi, el resto (nombre, fecha) se muestra de solo lectura."""
    class Meta:
        model = EtapaPedido
        fields = ['estado']


class EvidenciaRapidaForm(forms.ModelForm):
    """Subida de foto opcional dentro de 'Actualizar pedido': a diferencia
    de EvidenciaPedidoForm, la imagen no es obligatoria porque no siempre
    hay una foto nueva cada vez que se actualizan etapas."""
    class Meta:
        model = EvidenciaPedido
        fields = ['imagen', 'descripcion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imagen'].required = False


class ObservacionesPedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }


class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = [
            'nombre',
            'categoria',
            'unidad',
            'stock_actual',
            'stock_minimo',
            'proveedor',
        ]


class ConsumoInsumoForm(forms.ModelForm):
    class Meta:
        model = ConsumoInsumo
        fields = [
            'insumo',
            'cantidad',
            'observacion',
        ]

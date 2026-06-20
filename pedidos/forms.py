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


class EvidenciaPedidoForm(forms.ModelForm):
    class Meta:
        model = EvidenciaPedido
        fields = [
            'etapa',
            'imagen',
            'descripcion',
        ]


class AvancePedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            'estado',
            'porcentaje_avance',
            'observaciones',
        ]
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

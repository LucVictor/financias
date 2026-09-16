from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import CartaoCredito, CompraCartao, FaturaCartao


class CartaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CartaoCredito
        fields = ['nome', 'banco_emissor', 'limite_total', 'dia_fechamento', 'dia_vencimento', 'ativo']


class CompraForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CompraCartao
        fields = [
            'cartao', 'descricao', 'estabelecimento', 'categoria', 'valor_total',
            'data_compra', 'forma_pagamento', 'num_parcelas', 'valor_parcela',
        ]
        widgets = {
            'data_compra': forms.DateInput(attrs={'type': 'date'}),
            'valor_parcela': forms.TextInput(attrs={'placeholder': 'Calculado automaticamente'}),
        }

    def clean(self):
        cleaned = super().clean()
        forma = cleaned.get('forma_pagamento')
        parcelas = cleaned.get('num_parcelas') or 1
        if forma == 'parcelada' and parcelas <= 1:
            raise forms.ValidationError('Informe o número de parcelas (maior que 1) para compras parceladas.')
        return cleaned


class FaturaPagamentoForm(BootstrapFormMixin, forms.Form):
    data_pagamento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    valor_pago = forms.DecimalField(max_digits=15, decimal_places=2)
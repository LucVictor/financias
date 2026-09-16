from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import Divida


class DividaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Divida
        fields = [
            'descricao', 'credor', 'valor_total', 'valor_pago', 'data_vencimento',
            'num_parcelas', 'valor_parcela', 'para_pagamento', 'ativa', 'observacoes',
        ]
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }
from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import Ativo, ProventoRecebido


class AtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Ativo
        fields = [
            'ticker', 'tipo', 'quantidade', 'preco_medio', 'preco_atual',
            'dividend_yield_mensal', 'fonte_preco', 'ativo', 'observacoes',
        ]


class ProventoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProventoRecebido
        fields = ['ativo', 'valor', 'data', 'tipo']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}
from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import AplicacaoCDB, TaxaCDI


class TaxaCDIForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TaxaCDI
        fields = ['valor_anual', 'data_inicio']
        widgets = {'data_inicio': forms.DateInput(attrs={'type': 'date'})}


class AplicacaoCDBForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AplicacaoCDB
        fields = [
            'instituicao', 'valor_aplicado', 'data_aplicacao', 'data_vencimento',
            'percentual_cdi', 'observacoes', 'ativo',
        ]
        widgets = {
            'data_aplicacao': forms.DateInput(attrs={'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
        }
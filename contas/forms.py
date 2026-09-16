from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import Banco, Movimentacao


class BancoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Banco
        fields = ['nome', 'tipo_conta', 'saldo_atual', 'observacoes', 'ativo']


class MovimentacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Movimentacao
        fields = ['conta', 'descricao', 'categoria', 'valor', 'data', 'tipo', 'observacoes']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }
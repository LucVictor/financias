from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import ContaPoupanca, MovimentacaoPoupanca


class ContaPoupancaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContaPoupanca
        fields = [
            'nome', 'instituicao', 'saldo_atual', 'usar_regra_selic',
            'taxa_fixa_mensal', 'taxa_selic_anual', 'ativo',
        ]


class MovimentacaoPoupancaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MovimentacaoPoupanca
        fields = ['conta', 'tipo', 'valor', 'data', 'descricao']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}
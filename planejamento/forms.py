from django import forms
from django.utils import timezone

from sistema_financas.helpers import BootstrapFormMixin

from .models import ObjetivoFinanceiro


class ObjetivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ObjetivoFinanceiro
        fields = [
            'nome', 'descricao', 'valor_final', 'valor_inicial',
            'taxa_rendimento_pct', 'data_inicio', 'data_conclusao',
        ]
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'type': 'date'}),
            'valor_final': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'valor_inicial': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'taxa_rendimento_pct': forms.NumberInput(attrs={'step': '0.001', 'min': '0'}),
        }
        help_texts = {
            'valor_final': 'Valor total que deseja atingir.',
            'valor_inicial': 'Valor já destinado (fictício, sem movimentação bancária).',
            'taxa_rendimento_pct': 'Taxa mensal estimada do rendimento (ex.: 0.5 para poupança).',
            'data_inicio': 'Mês de início dos aportes.',
            'data_conclusao': 'Mês em que o objetivo deve ser atingido.',
        }

    def clean(self):
        dados = super().clean()
        if dados.get('data_inicio') and dados.get('data_conclusao'):
            if dados['data_conclusao'] <= dados['data_inicio']:
                self.add_error('data_conclusao', 'A data de conclusão deve ser posterior ao início.')
        if dados.get('valor_final') and dados['valor_final'] <= 0:
            self.add_error('valor_final', 'O valor final deve ser maior que zero.')
        return dados


class AporteMensalForm(forms.ModelForm):
    class Meta:
        model = ObjetivoFinanceiro
        fields = []

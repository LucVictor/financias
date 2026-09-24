from decimal import Decimal

from django import forms

from contas.models import Banco
from sistema_financas.helpers import BootstrapFormMixin
from .models import (
    ContaPeriodica,
    PagamentoAvulso,
    RecebimentoAvulso,
    RecebimentoPeriodico,
)


class ContaPeriodicaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContaPeriodica
        fields = [
            'descricao', 'valor_esperado', 'dia_do_mes', 'recorrência', 'categoria',
            'conta_pagamento_padrao', 'cartao_pagamento_padrao', 'ativo', 'observacoes',
        ]


class RecebimentoPeriodicoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RecebimentoPeriodico
        fields = [
            'descricao', 'valor_esperado', 'dia_do_mes', 'recorrência', 'categoria',
            'conta_destino_padrao', 'ativo', 'observacoes',
        ]


class RecebimentoAvulsoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RecebimentoAvulso
        fields = [
            'descricao', 'valor', 'data_prevista', 'conta_destino', 'observacoes',
        ]
        widgets = {'data_prevista': forms.DateInput(attrs={'type': 'date'})}


class PagamentoAvulsoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PagamentoAvulso
        fields = [
            'descricao', 'valor', 'data_pagamento', 'conta_pagamento', 'observacoes',
        ]
        widgets = {'data_pagamento': forms.DateInput(attrs={'type': 'date'})}


class BaixaContaForm(BootstrapFormMixin, forms.Form):
    MEIO_CHOICES = [
        ('conta', 'Pagamento em conta bancária'),
        ('cartao', 'Pago com cartão de crédito'),
        ('dinheiro', 'Pago em dinheiro/outro'),
    ]
    meio = forms.ChoiceField(choices=MEIO_CHOICES, initial='conta')
    conta = forms.ModelChoiceField(
        queryset=Banco.objects.filter(ativo=True),
        required=False,
    )
    data_efetiva = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    valor = forms.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))


class BaixaRecebimentoForm(BootstrapFormMixin, forms.Form):
    conta = forms.ModelChoiceField(
        queryset=Banco.objects.filter(ativo=True),
        required=False,
    )
    data_efetiva = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    valor = forms.DecimalField(max_digits=15, decimal_places=2)
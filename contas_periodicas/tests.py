from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contas.models import Banco
from contas_periodicas.models import (
    ContaPeriodica,
    OcorrenciaContaPeriodica,
    PagamentoAvulso,
)


class BaixaContaPeriodicaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='x')
        self.client.force_login(self.user)
        self.banco = Banco.objects.create(nome='Banco Teste', saldo_atual=Decimal('1000.00'))
        self.conta = ContaPeriodica.objects.create(
            descricao='Internet',
            valor_esperado=Decimal('100.00'),
            dia_do_mes=5,
            recorrência='mensal',
            ativo=True,
            conta_pagamento_padrao=self.banco,
        )
        self.ocorrencia = OcorrenciaContaPeriodica.objects.create(
            conta_periodica=self.conta,
            data_vencimento=date(2026, 9, 5),
            valor=Decimal('100.00'),
        )

    def _payload(self, valor, decisao=None):
        data = {
            'meio': 'conta',
            'conta': self.banco.pk,
            'data_efetiva': timezone.localdate().strftime('%Y-%m-%d'),
            'valor': str(valor),
        }
        if decisao:
            data['decisao'] = decisao
        return data

    def test_baixa_integral_marca_paga_sem_confirmacao(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('100.00'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'paga')
        self.assertEqual(self.ocorrencia.valor_pago, Decimal('100.00'))
        self.assertEqual(PagamentoAvulso.objects.count(), 0)
        self.banco.refresh_from_db()
        self.assertEqual(self.banco.saldo_atual, Decimal('900.00'))

    def test_baixa_parcial_pede_decisao_sem_aplicar(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('40.00'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'restante_pendente')
        self.assertContains(resp, 'encerrar')
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'a_pagar')
        self.assertEqual(self.ocorrencia.valor_pago, Decimal('0'))
        self.assertEqual(PagamentoAvulso.objects.count(), 0)
        self.banco.refresh_from_db()
        self.assertEqual(self.banco.saldo_atual, Decimal('1000.00'))

    def test_baixa_parcial_restante_vira_novo_pagamento(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('40.00', decisao='restante_pendente'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'paga')
        self.assertEqual(self.ocorrencia.valor_pago, Decimal('40.00'))
        restante = PagamentoAvulso.objects.get()
        self.assertEqual(restante.valor, Decimal('60.00'))
        self.assertNotEqual(restante.status, 'pago')
        self.assertEqual(restante.data_pagamento, timezone.localdate())
        self.banco.refresh_from_db()
        self.assertEqual(self.banco.saldo_atual, Decimal('960.00'))

    def test_baixa_parcial_encerra_conta_com_valor_pago(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('40.00', decisao='encerrar'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'paga')
        self.assertEqual(self.ocorrencia.valor_pago, Decimal('40.00'))
        self.assertEqual(PagamentoAvulso.objects.count(), 0)
        self.banco.refresh_from_db()
        self.assertEqual(self.banco.saldo_atual, Decimal('960.00'))

    def test_baixa_valor_zero_rejeitado(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('0'))
        self.assertEqual(resp.status_code, 200)
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'a_pagar')
        self.assertEqual(PagamentoAvulso.objects.count(), 0)

    def test_baixa_maior_que_valor_cadastrado_marca_paga(self):
        url = reverse('contas_periodicas:baixa_conta', args=[self.ocorrencia.pk])
        resp = self.client.post(url, self._payload('120.00'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.ocorrencia.refresh_from_db()
        self.assertEqual(self.ocorrencia.status, 'paga')
        self.assertEqual(self.ocorrencia.valor_pago, Decimal('120.00'))
        self.assertEqual(PagamentoAvulso.objects.count(), 0)


class BaixaPagamentoAvulsoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='x')
        self.client.force_login(self.user)
        self.banco = Banco.objects.create(nome='Banco Teste', saldo_atual=Decimal('1000.00'))
        self.avulso = PagamentoAvulso.objects.create(
            descricao='Multa',
            valor=Decimal('100.00'),
            data_pagamento=date(2026, 9, 10),
            conta_pagamento=self.banco,
        )

    def _payload(self, valor, decisao=None):
        data = {
            'meio': 'conta',
            'conta': self.banco.pk,
            'data_efetiva': timezone.localdate().strftime('%Y-%m-%d'),
            'valor': str(valor),
        }
        if decisao:
            data['decisao'] = decisao
        return data

    def test_baixa_parcial_restante_vira_novo_pagamento(self):
        url = reverse('contas_periodicas:baixa_pagamento_avulso', args=[self.avulso.pk])
        resp = self.client.post(url, self._payload('40.00', decisao='restante_pendente'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.avulso.refresh_from_db()
        self.assertEqual(self.avulso.status, 'pago')
        self.assertEqual(self.avulso.valor_pago, Decimal('40.00'))
        restante = PagamentoAvulso.objects.exclude(pk=self.avulso.pk).get()
        self.assertEqual(restante.valor, Decimal('60.00'))
        self.assertTrue(restante.data_pagamento <= timezone.localdate())
        self.banco.refresh_from_db()
        self.assertEqual(self.banco.saldo_atual, Decimal('960.00'))

    def test_baixa_parcial_encerra_com_valor_pago(self):
        url = reverse('contas_periodicas:baixa_pagamento_avulso', args=[self.avulso.pk])
        resp = self.client.post(url, self._payload('40.00', decisao='encerrar'))
        self.assertRedirects(resp, reverse('contas_periodicas:home'))
        self.avulso.refresh_from_db()
        self.assertEqual(self.avulso.status, 'pago')
        self.assertEqual(self.avulso.valor_pago, Decimal('40.00'))
        self.assertEqual(PagamentoAvulso.objects.count(), 1)
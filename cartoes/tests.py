from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cartoes.models import CartaoCredito, CompraCartao, FaturaCartao, ParcelaCompra
from cartoes.services import get_or_create_fatura


class CompraCrudTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='x')
        self.client.force_login(self.user)
        self.cartao = CartaoCredito.objects.create(
            nome='Nubank',
            banco_emissor='Nubank',
            limite_total=Decimal('5000.00'),
            dia_fechamento=1,
            dia_vencimento=10,
        )

    def _compra(self, descricao='Notebook', valor='300.00', parcelas=3):
        return CompraCartao.objects.create(
            cartao=self.cartao,
            descricao=descricao,
            categoria='Eletrônicos',
            valor_total=Decimal(valor),
            data_compra=date(2026, 9, 5),
            forma_pagamento='parcelada',
            num_parcelas=parcelas,
        )

    def _payload(self, compra, **overrides):
        dados = {
            'cartao': self.cartao.pk,
            'descricao': compra.descricao,
            'categoria': compra.categoria,
            'valor_total': str(compra.valor_total),
            'data_compra': compra.data_compra.strftime('%Y-%m-%d'),
            'forma_pagamento': compra.forma_pagamento,
            'num_parcelas': str(compra.num_parcelas),
            'valor_parcela': str(compra.valor_parcela),
        }
        dados.update(overrides)
        return dados

    def test_editar_compra_com_mudanca_estrutural_regenera_parcelas(self):
        compra = self._compra()
        url = reverse('cartoes:editar_compra', args=[compra.pk])
        resp = self.client.post(url, self._payload(
            compra,
            descricao='Notebook Pro',
            valor_total='600.00',
            valor_parcela='',
        ))
        self.assertRedirects(resp, reverse('cartoes:detalhe', args=[self.cartao.pk]))
        compra.refresh_from_db()
        self.assertEqual(compra.descricao, 'Notebook Pro')
        self.assertEqual(compra.valor_total, Decimal('600.00'))
        self.assertEqual(compra.valor_parcela, Decimal('200.00'))
        parcelas = list(compra.parcelas.order_by('numero_parcela'))
        self.assertEqual(len(parcelas), 3)
        self.assertEqual([p.valor for p in parcelas], [Decimal('200.00')] * 3)

    def test_editar_compra_sem_mudanca_estrutural_nao_toca_parcelas(self):
        compra = self._compra()
        compra.parcelas.filter(numero_parcela=1).update(status='paga')
        compra_id = compra.pk
        url = reverse('cartoes:editar_compra', args=[compra.pk])
        resp = self.client.post(url, self._payload(compra, descricao='Notebook Gamer'))
        self.assertRedirects(resp, reverse('cartoes:detalhe', args=[self.cartao.pk]))
        compra.refresh_from_db()
        self.assertEqual(compra.descricao, 'Notebook Gamer')
        parcelas = list(compra.parcelas.order_by('numero_parcela'))
        self.assertEqual(len(parcelas), 3)
        self.assertEqual(parcelas[0].status, 'paga')
        self.assertNotEqual(parcelas[1].status, 'paga')
        pagas_originais = ParcelaCompra.objects.filter(compra_id=compra_id, status='paga').count()
        self.assertEqual(pagas_originais, 1)

    def test_editar_compra_recalcula_e_preserva_parcelas_pagas(self):
        compra = self._compra()
        compra.parcelas.filter(numero_parcela=1).update(status='paga')
        url = reverse('cartoes:editar_compra', args=[compra.pk])
        resp = self.client.post(url, self._payload(
            compra,
            valor_total='600.00',
            valor_parcela='',
        ))
        self.assertRedirects(resp, reverse('cartoes:detalhe', args=[self.cartao.pk]))
        compra.refresh_from_db()
        parcelas = list(compra.parcelas.order_by('numero_parcela'))
        self.assertEqual(len(parcelas), 3)
        self.assertEqual(parcelas[0].valor, Decimal('200.00'))
        self.assertEqual(parcelas[0].status, 'paga')
        self.assertEqual(parcelas[1].status, 'a_vencer')

    def test_editar_compra_bloqueia_reducao_abaixo_parcelas_pagas(self):
        compra = self._compra(parcelas=4)
        compra.parcelas.filter(numero_parcela__in=[1, 2, 3]).update(status='paga')
        url = reverse('cartoes:editar_compra', args=[compra.pk])
        resp = self.client.post(url, self._payload(compra, num_parcelas='2'))
        self.assertEqual(resp.status_code, 200)
        compra.refresh_from_db()
        self.assertEqual(compra.num_parcelas, 4)
        self.assertEqual(compra.parcelas.count(), 4)

    def test_excluir_compra_remove_parcelas_e_atualiza_faturas(self):
        compra = self._compra()
        for ano, mes in [(2026, 10), (2026, 11), (2026, 12)]:
            get_or_create_fatura(self.cartao, ano, mes)
        self.assertEqual(self.cartao.faturas.get(ano=2026, mes=10).valor_total, Decimal('100.00'))

        url = reverse('cartoes:excluir_compra', args=[compra.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse('cartoes:detalhe', args=[self.cartao.pk]))
        self.assertFalse(CompraCartao.objects.filter(pk=compra.pk).exists())
        self.assertEqual(ParcelaCompra.objects.filter(compra_id=compra.pk).count(), 0)
        self.assertEqual(self.cartao.faturas.get(ano=2026, mes=10).valor_total, Decimal('0'))
        self.assertEqual(self.cartao.faturas.get(ano=2026, mes=11).valor_total, Decimal('0'))

    def test_detalhe_fatura_futura_sem_registro_cria_na_hora(self):
        compra = self._compra()
        url = reverse('cartoes:detalhe', args=[self.cartao.pk]) + '?fatura=2026-11'
        self.assertFalse(FaturaCartao.objects.filter(cartao=self.cartao, ano=2026, mes=11).exists())
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, compra.descricao)
        fatura = FaturaCartao.objects.get(cartao=self.cartao, ano=2026, mes=11)
        self.assertEqual(fatura.valor_total, Decimal('100.00'))
        self.assertEqual(fatura.parcelas.count(), 1)
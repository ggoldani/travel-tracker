"""Testes do parser do travel-tracker (strings reais capturadas ao vivo)."""
import unittest
import probe


class TestParseMulti(unittest.TestCase):
    def test_brl_nbsp_roundtrip(self):
        # output real do GF: \xa0 como texto literal (dupla-escapado)
        s = ["R$\\xa08.561", "R$\\xa09.438"]
        self.assertEqual(probe.parse_multi(s), [("BRL", 8561.0), ("BRL", 9438.0)])

    def test_brl_nbsp_unicode(self):
        s = ["R$\xa08.561"]
        self.assertEqual(probe.parse_multi(s), [("BRL", 8561.0)])

    def test_eur_inteiro(self):
        s = ["€\xa075", "€\xa0447", "€\xa0499"]
        self.assertEqual(probe.parse_multi(s),
                         [("EUR", 75.0), ("EUR", 447.0), ("EUR", 499.0)])

    def test_eur_ptbr_decimal(self):
        # pt-BR: virgula de 2 digitos = decimal
        s = ["€\xa01.234,56", "€\xa0999,90"]
        self.assertEqual(probe.parse_multi(s),
                         [("EUR", 1234.56), ("EUR", 999.9)])

    def test_eur_enus_leak_milhar(self):
        # leak en-US: virgula de 3 digitos sem dot = milhar
        s = ["€\xa01,234"]
        self.assertEqual(probe.parse_multi(s), [("EUR", 1234.0)])

    def test_eur_dot_e_virgula(self):
        s = ["€\xa01.234,56"]
        self.assertEqual(probe.parse_multi(s), [("EUR", 1234.56)])

    def test_usd(self):
        s = ["US$ 1.234,56"]
        self.assertEqual(probe.parse_multi(s), [("USD", 1234.56)])

    def test_filtro_lixo_mediana(self):
        # 545 vs lista ~8500: filtrado pelo filter_junk (so voo/min)
        s = ["R$\\xa0545", "R$\\xa08.561", "R$\\xa08.674", "R$\\xa09.438"]
        pairs = probe.parse_multi(s)
        vals = [v for _, v in probe.filter_junk(pairs)]
        self.assertNotIn(545.0, vals)
        # hotel NAO filtra (spread legitimo)
        self.assertIn(545.0, [v for _, v in pairs])

    def test_hotel_sem_gate_spread_legitimo(self):
        s = ["€\xa075", "€\xa0447", "€\xa0499"]
        self.assertEqual(len(probe.parse_multi(s)), 3)

    def test_ignora_curto(self):
        s = ["R$ 10"]
        self.assertEqual(probe.parse_multi(s), [])

    def test_multiplos_formatos_mistos(self):
        s = ["€\xa080", "€\xa01.234,56", "R$\\xa05.176"]
        out = probe.parse_multi(s)
        self.assertIn(("EUR", 80.0), out)
        self.assertIn(("EUR", 1234.56), out)
        self.assertIn(("BRL", 5176.0), out)


class TestHealth(unittest.TestCase):
    def test_health_tick_ok_e_fail(self):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        old_base = probe.BASE
        try:
            probe.BASE = tmp
            h = probe.health_tick("x", True)
            self.assertEqual(h["consecutive_fails"], 0)
            h = probe.health_tick("x", False)
            self.assertEqual(h["consecutive_fails"], 1)
            h = probe.health_tick("x", False)
            self.assertEqual(h["consecutive_fails"], 2)
            h = probe.health_tick("x", True)
            self.assertEqual(h["consecutive_fails"], 0)
            h = probe.health_tick("d", False, dormant=True)
            self.assertTrue(h["dormant"])
        finally:
            probe.BASE = old_base
            shutil.rmtree(tmp)


class TestGhDateLabel(unittest.TestCase):
    def test_label_agosto_2027(self):
        import datetime
        d = datetime.date(2027, 8, 1)
        self.assertEqual(probe._gh_date_label(d), "domingo, 1 de agosto de 2027")
        d2 = datetime.date(2027, 8, 8)
        self.assertEqual(probe._gh_date_label(d2), "domingo, 8 de agosto de 2027")


if __name__ == "__main__":
    unittest.main()

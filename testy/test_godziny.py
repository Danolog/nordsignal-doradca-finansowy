"""Straznicy agregacji godzin (art. 12 ust. 3)."""
from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import godziny, magazyn

OD, DO = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz(tmp_path / "g.db")
    magazyn.zapisz_godziny(polaczenie, data=date(2026, 9, 5),
                           rodzaj_czynnosci="pozyskiwanie klientow",
                           pkwiu="46.19.10.0", liczba_godzin=Decimal("120"), opis="")
    magazyn.zapisz_godziny(polaczenie, data=date(2026, 9, 20),
                           rodzaj_czynnosci="raporty i rekomendacje",
                           pkwiu="74.90.19.0", liczba_godzin=Decimal("40"), opis="")
    return polaczenie


def test_agregat_rozdziela_godziny_per_pkwiu(p):
    pozycje = godziny.agreguj(p, OD, DO)
    assert len(pozycje) == 2
    assert {x.pkwiu for x in pozycje} == {"46.19.10.0", "74.90.19.0"}


def test_agregat_nie_gubi_zadnej_godziny(p):
    """Kontrola licznosci: 120 + 40 = 160, tyle ile wpisano."""
    assert sum(x.godziny for x in godziny.agreguj(p, OD, DO)) == Decimal("160")


def test_agregat_przelicza_godziny_na_kwote(p):
    pozycje = {x.pkwiu: x for x in godziny.agreguj(p, OD, DO)}
    assert pozycje["46.19.10.0"].netto == Decimal("8400.00")   # 120 x 70
    assert pozycje["74.90.19.0"].netto == Decimal("2800.00")   # 40 x 70


def test_rozklad_pokazuje_proporcje_rodzajow(p):
    r = godziny.rozklad(p, OD, DO)
    assert r["pozyskiwanie klientow"] == Decimal("120")
    assert r["raporty i rekomendacje"] == Decimal("40")


def test_pusty_okres_daje_pusty_wynik_nie_wyjatek(p):
    assert godziny.agreguj(p, date(2027, 1, 1), date(2027, 1, 31)) == []
    assert godziny.rozklad(p, date(2027, 1, 1), date(2027, 1, 31)) == {}


def test_kazdy_rodzaj_czynnosci_ma_sugerowane_pkwiu():
    """Kontrola licznosci: dziesiec pozycji odwzorowujacych par. 3 ust. 2 umowy."""
    assert len(godziny.RODZAJE_CZYNNOSCI) == 10
    assert all(v and v[0].isdigit() for v in godziny.RODZAJE_CZYNNOSCI.values())

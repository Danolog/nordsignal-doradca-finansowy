"""Straznicy porownania form opodatkowania (specyfikacja par. 6c).

Wartosci odniesienia policzone przy projektowaniu 2026-08-25 i zapisane
w specyfikacji. Tolerancja 2 zl - formuly skali i liniowego sa uproszczone,
wiec test pilnuje rzedu wielkosci i KIERUNKU roznicy, nie grosza.
"""
from decimal import Decimal

import pytest

from silnik.rdzen import formy


def _mapa(przychod, miesiecy=12):
    return {f.nazwa: f for f in formy.porownaj_formy(Decimal(przychod), miesiecy)}


def test_2027_pelny_rok_134400():
    w = _mapa("134400")
    assert abs(w["ryczalt 8,5%"].razem - Decimal("42123")) <= 2
    assert abs(w["skala"].razem - Decimal("42890")) <= 2
    assert abs(w["liniowy"].razem - Decimal("48681")) <= 2
    assert abs(w["ryczalt 15%"].razem - Decimal("49032")) <= 2


def test_2027_z_prowizja_164400():
    w = _mapa("164400")
    assert abs(w["ryczalt 8,5%"].razem - Decimal("44673")) <= 2
    assert abs(w["skala"].razem - Decimal("53445")) <= 2
    assert abs(w["ryczalt 15%"].razem - Decimal("53532")) <= 2


def test_skala_wygrywa_na_przychodzie_czesciowym_2026():
    """Wrzesien-grudzien 2026: skala tansza od spornego ryczaltu 8,5%
    o okolo 872 zl - dzieki kwocie wolnej."""
    w = _mapa("44800", miesiecy=4)
    assert w["skala"].razem < w["ryczalt 8,5%"].razem
    assert abs(w["skala"].razem - Decimal("11897")) <= 2
    assert abs(w["ryczalt 8,5%"].razem - Decimal("12769")) <= 2


def test_ryczalt_wygrywa_gdy_prowizja_ruszy():
    """Punkt zwrotny: powyzej ok. 150 tys. skala wpada w drugi prog."""
    w = _mapa("164400")
    assert w["ryczalt 8,5%"].razem < w["skala"].razem


def test_roznica_85_kontra_15_wieksza_niz_roznica_ryczalt_kontra_skala():
    """Wniosek, dla ktorego ten modul w ogole powstal: wybor formy wazy mniej
    niz kwalifikacja PKWiU - ale jest bezsporny, a kwalifikacja sporna."""
    w = _mapa("134400")
    roznica_stawek = w["ryczalt 15%"].razem - w["ryczalt 8,5%"].razem
    roznica_form = abs(w["skala"].razem - w["ryczalt 8,5%"].razem)
    assert roznica_stawek > roznica_form
    assert roznica_stawek > Decimal("6000")
    assert roznica_form < Decimal("1000")


def test_kazda_forma_niesie_zastrzezenia():
    for f in formy.porownaj_formy(Decimal("134400")):
        assert f.zastrzezenia, f"{f.nazwa} bez zastrzezen"


def test_liniowy_oznaczony_jako_oparty_na_niezweryfikowanym_limicie():
    """Pozycja 12.1: limit 14 100 zl przypisany przez dwa serwisy do roznych lat."""
    w = _mapa("134400")
    assert any("niezweryfikowan" in z.lower() for z in w["liniowy"].zastrzezenia)


def test_zwracane_sa_wszystkie_cztery_formy():
    """Kontrola licznosci."""
    assert len(formy.porownaj_formy(Decimal("134400"))) == 4


def test_razem_domyka_sie_ze_skladnikow():
    for f in formy.porownaj_formy(Decimal("134400")):
        assert f.razem == f.pit + f.zdrowotna + f.spoleczne
        assert f.do_dyspozycji == Decimal("134400") - f.razem

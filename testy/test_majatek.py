"""Strazniki bilansu: aktywa minus zobowiazania.

To jest regula o konsekwencji zewnetrznej, nie uklad graficzny — liczba
mowi uzytkownikowi, czy po splacie wszystkiego zostaje mu cokolwiek.
Odwrocenie znaku daje wynik dodatni przy dlugu przewyzszajacym majatek,
czyli komunikat doslownie odwrotny do prawdy.
"""

from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import majatek


def _aktywa(*kwoty) -> pd.DataFrame:
    return pd.DataFrame([{"nazwa_aktywa": f"a{n}", "kategoria": "inne",
                          "wartosc": Decimal(k)}
                         for n, k in enumerate(kwoty)])


def _dlugi(*kwoty) -> pd.DataFrame:
    return pd.DataFrame([{"nazwa": f"d{n}", "kapital": Decimal(k),
                          "rata_minimalna": Decimal("100")}
                         for n, k in enumerate(kwoty)])


def test_dlug_wiekszy_od_majatku_daje_wartosc_ujemna():
    """Stan Darka 2026-08-25: poduszka 5 000, kredyt 43 000."""
    bilans = majatek.bilans(_aktywa("5000.0"), _dlugi("43000.0"))
    assert bilans.netto == Decimal("-38000.00")
    assert bilans.aktywa == Decimal("5000.00")
    assert bilans.zobowiazania == Decimal("43000.00")


def test_majatek_wiekszy_od_dlugu_daje_wartosc_dodatnia():
    bilans = majatek.bilans(_aktywa("100000", "20000"), _dlugi("43000"))
    assert bilans.netto == Decimal("77000.00")


def test_skladniki_sumuja_sie_do_netto():
    """Podpis kafla wymienia skladniki, kwota pokazuje netto — jesli licza
    sie osobno, moga sie rozjechac i uzytkownik zobaczy sprzecznosc."""
    bilans = majatek.bilans(_aktywa("1234.56", "78.90"), _dlugi("999.99"))
    assert bilans.netto == bilans.aktywa - bilans.zobowiazania


def test_puste_tabele_daja_zero_a_nie_blad():
    """Pusta baza to normalny stan pierwszego uruchomienia, nie awaria."""
    bilans = majatek.bilans(pd.DataFrame(), pd.DataFrame())
    assert bilans.netto == Decimal("0.00")
    assert bilans.aktywa == Decimal("0.00")
    assert bilans.zobowiazania == Decimal("0.00")


def test_sam_dlug_bez_majatku_liczy_sie_normalnie():
    bilans = majatek.bilans(pd.DataFrame(), _dlugi("43000"))
    assert bilans.netto == Decimal("-43000.00")


@pytest.mark.parametrize("kwoty,oczekiwane", [
    (("0.333", "0.333", "0.334"), Decimal("1.00")),
    (("0.005",), Decimal("0.01")),
])
def test_kwoty_zaokraglone_do_groszy(kwoty, oczekiwane):
    """Bez zaokraglenia jawnego ta sama suma pokazuje sie inaczej
    w kwocie i w podpisie."""
    bilans = majatek.bilans(_aktywa(*kwoty), pd.DataFrame())
    assert bilans.aktywa == oczekiwane
    assert bilans.netto == oczekiwane

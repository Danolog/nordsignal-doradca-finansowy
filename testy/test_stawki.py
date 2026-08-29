"""Straznicy rejestru stawek.

Dwa pierwsze pilnuja WARTOSCI zweryfikowanych u zrodla.
Dwa kolejne pilnuja SPOSOBU LICZENIA - i to one sa wazniejsze, bo wartosci
zmienia sie raz w roku, a bledny sposob liczenia zostaje na zawsze.
"""
from decimal import Decimal

import pytest

from silnik.rdzen import stawki


def test_progi_zdrowotnej_zgodne_ze_zrodlem():
    """biznes.gov.pl/pl/portal/001052, aktualizacja 28.01.2026, odczyt 2026-08-25."""
    assert stawki.skladka_zdrowotna(Decimal("0.60")) == Decimal("498.35")
    assert stawki.skladka_zdrowotna(Decimal("1.00")) == Decimal("830.58")
    assert stawki.skladka_zdrowotna(Decimal("1.80")) == Decimal("1495.04")


def test_podstawy_zdrowotnej_zgodne_ze_zrodlem():
    """Podstawa zaokraglana PRZED naliczeniem 9% - tak liczy ZUS."""
    assert stawki.podstawa_zdrowotnej(Decimal("0.60")) == Decimal("5537.18")
    assert stawki.podstawa_zdrowotnej(Decimal("1.00")) == Decimal("9228.64")
    assert stawki.podstawa_zdrowotnej(Decimal("1.80")) == Decimal("16611.55")


def test_skladniki_spolecznych_zgodne_ze_zrodlem():
    """biznes.gov.pl/pl/portal/00274, aktualizacja 11.02.2026, odczyt 2026-08-25."""
    s = stawki.skladki_spoleczne(z_chorobowa=True)
    assert s["emerytalna"] == Decimal("1103.27")
    assert s["rentowa"] == Decimal("452.16")
    assert s["chorobowa"] == Decimal("138.47")
    assert s["wypadkowa"] == Decimal("94.39")
    assert s["fp_fs"] == Decimal("138.47")


def test_suma_spolecznych_liczona_ze_skladnikow_nie_przepisana():
    """Ograniczenie globalne 3: zaokraglamy KAZDY skladnik osobno, potem sumujemy.

    Bez tego: 5652 * 0.3409 = 1926.7668 -> 1926.77, czyli o grosz za duzo.
    ZUS zaokragla per skladka: 1103.27+452.16+138.47+94.39+138.47 = 1926.76.

    Ten test jest tez powodem, dla ktorego nie przepisujemy sum ze stron
    rzadowych: pobrana tabela opisywala 1926,76 zl raz jako kwote
    "bez chorobowego", gdy arytmetyka skladnikow daje ja Z chorobowym.
    """
    s = stawki.skladki_spoleczne(z_chorobowa=True)
    assert stawki.suma_spolecznych(z_chorobowa=True) == sum(s.values())
    assert stawki.suma_spolecznych(z_chorobowa=True) == Decimal("1926.76")
    assert stawki.suma_spolecznych(z_chorobowa=False) == Decimal("1788.29")


def test_bez_chorobowej_suma_nie_zawiera_chorobowej():
    """Kontrola dwustronna: nie tylko suma sie zgadza, ale i skladnik znika."""
    assert "chorobowa" not in stawki.skladki_spoleczne(z_chorobowa=False)
    assert "chorobowa" in stawki.skladki_spoleczne(z_chorobowa=True)


@pytest.mark.parametrize("klucz", ["zdrowotna", "spoleczne", "ryczalt", "skala_liniowy"])
def test_kazda_grupa_stawek_ma_zrodlo_z_data_odczytu(klucz):
    z = stawki.ZRODLA[klucz]
    assert z.url.startswith("https://")
    assert z.data_odczytu is not None


def test_zrodla_pokrywaja_wszystkie_grupy():
    """Kontrola licznosci przez ZBIOR KLUCZY, nie przez sama liczbe.

    Liczba mowi „ile", zbior mowi „ktore" — i przy podmianie jednego zrodla
    na inne liczba zostaje ta sama, a pokrycie sie zmienia.
    `vat` doszlo 2026-08-25 razem z terminami platnosci (Zadanie 22b).
    `skala` doszlo 2026-08-27 razem z silnikiem skali (Z58) — jako WARUNEK
    UKONCZENIA, bo drugi silnik podatkowy bez pokrycia mechanizmem, ktory ma
    pierwszy, jest gorszy niz jego brak. Uwaga: `skala_liniowy` wskazuje
    strone o ODLICZENIU zdrowotnej, czyli nie o progach skali — to dwa rozne
    zrodla i dlatego dwa klucze.
    """
    assert set(stawki.ZRODLA) == {"zdrowotna", "spoleczne", "ryczalt",
                                  "skala", "skala_liniowy", "vat"}


def test_limit_odliczenia_oznaczony_jako_niezweryfikowany():
    """Pozycja 12.1 specyfikacji - dwa serwisy rzadowe przypisuja 14 100 zl
    do roznych lat. Etykieta jest dopuszczalna; udawanie sprawdzonego nie jest."""
    assert stawki.LIMIT_ODLICZENIA_ZDROWOTNEJ_NIEZWERYFIKOWANY == Decimal("14100")
    assert stawki.ZRODLA["skala_liniowy"].niezweryfikowane != []

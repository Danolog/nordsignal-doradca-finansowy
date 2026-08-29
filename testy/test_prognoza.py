"""Straznicy prognozy rocznej.

Wachlarz godzin, nie jedna liczba: umowa nie gwarantuje wolumenu w zadna
strone (par. 6 ust. 2), wiec prognoza podajaca jedna date przeciecia progu
bylaby falszywym spokojem.
"""
from decimal import Decimal

import pytest

from silnik.rdzen import prezentacja, prognoza

STAWKA = Decimal("70")


@pytest.mark.parametrize("godziny, miesiac", [
    (80, 11), (120, 8), (160, 6), (200, 5), (240, 4),
])
def test_wachlarz_miesiaca_przeciecia_progu_60k(godziny, miesiac):
    """Wartosci policzone i zweryfikowane przy projektowaniu 2026-08-25.
    Kazda godzina ponad 160 przesuwa przeciecie WCZESNIEJ."""
    p = prognoza.prognozuj(Decimal(godziny), STAWKA, miesiecy=12)
    assert p[0].prog == 2
    assert p[0].miesiac == miesiac


def test_2026_wrzesien_grudzien_nie_przecina_progu():
    """160 h x 70 zl x 4 miesiace = 44 800 zl, czyli caly rok ponizej 60 tys."""
    p = prognoza.prognozuj(Decimal("160"), STAWKA, miesiecy=4)
    assert p[0].miesiac is None
    assert p[0].przychod_narastajaco == Decimal("44800")


def test_wzrost_skladki_po_przecieciu_pierwszego_progu():
    """830,58 - 498,35 = 332,23 zl miesiecznie. Liczone z rejestru, nie wpisane."""
    p = prognoza.prognozuj(Decimal("160"), STAWKA, miesiecy=12)
    assert p[0].wzrost_skladki == Decimal("332.23")


def test_wzrost_skladki_po_przecieciu_drugiego_progu():
    """1495,04 - 830,58 = 664,46 zl miesiecznie."""
    p = prognoza.prognozuj(Decimal("400"), STAWKA, miesiecy=12)
    assert p[1].prog == 3
    assert p[1].wzrost_skladki == Decimal("664.46")


def test_prog_300k_poza_zasiegiem_samej_podstawy():
    """Wymagalby okolo 357 h miesiecznie - specyfikacja par. 6a."""
    p = prognoza.prognozuj(Decimal("160"), STAWKA, miesiecy=12)
    assert p[1].prog == 3
    assert p[1].miesiac is None


def test_przychod_poczatkowy_przesuwa_przeciecie():
    """Kontrola dwustronna: przy 50 tys. juz na koncie prog wypada w miesiacu 1."""
    p = prognoza.prognozuj(Decimal("160"), STAWKA, miesiecy=12,
                           przychod_poczatkowy=Decimal("50000"))
    assert p[0].miesiac == 1


def test_wachlarz_zwraca_wpis_dla_kazdego_wariantu():
    """Kontrola licznosci."""
    warianty = [Decimal(g) for g in (80, 120, 160, 200, 240)]
    w = prognoza.wachlarz(warianty, STAWKA, miesiecy=12)
    assert set(w) == set(warianty)
    assert all(len(v) == 2 for v in w.values())


# --- ostrzezenie progowe --------------------------------------------------

def test_ostrzezenie_gdy_blizej_progu_niz_jedna_faktura():
    assert prognoza.ostrzezenie_progowe(Decimal("55000"), Decimal("11200")) is not None
    assert prognoza.ostrzezenie_progowe(Decimal("20000"), Decimal("11200")) is None


def test_ostrzezenie_podaje_ile_brakuje_i_o_ile_wzrosnie_skladka():
    tekst = prognoza.ostrzezenie_progowe(Decimal("55000"), Decimal("11200"))
    assert "5\u00a0000,00" in tekst      # brakujaca kwota do progu
    assert "60\u00a0000,00" in tekst     # sam prog
    assert "332,23" in tekst             # wzrost skladki miesiecznej


def test_separator_tysiecy_to_spacja_nierozdzielajaca_nie_zwykla():
    """Polska typografia nie pozwala zlamac liczby na koncu wiersza.

    Test istnieje, zeby ta decyzja byla decyzja, a nie niewidzialnym znakiem,
    ktory ktos przy nastepnej edycji zastapi zwykla spacja i nikt nie zauwazy.

    ZMIANA Z51, jawnie: stara asercja brzmiala `prognoza.SEPARATOR_TYSIECY ==
    "\u00a0"`. Nosnik separatora przeniosl sie do `rdzen/prezentacja.py` —
    do Z51 stal w DWOCH kopiach (`rdzen/prognoza.py` i `pulpit/wspolne.py`),
    a druga miala znak wklejony doslownie. Polowa behawioralna testu
    („zwykla spacja NIE wystepuje w tekscie ostrzezenia") zostaje bez zmian
    i dalej pilnuje wyjscia tego modulu.
    """
    assert prezentacja.SEPARATOR_TYSIECY == "\u00a0"
    tekst = prognoza.ostrzezenie_progowe(Decimal("55000"), Decimal("11200"))
    assert "5 000" not in tekst          # zwykla spacja NIE wystepuje


def test_brak_ostrzezenia_po_przecieciu_ostatniego_progu():
    assert prognoza.ostrzezenie_progowe(Decimal("400000"), Decimal("11200")) is None

"""Straznicy silnika podatkowego.

Kazdy odpowiada pozycji z tabeli mutacji w specyfikacji par. 10.
Wartosci odniesienia policzone recznie i sprawdzone w tescie przekrojowym
na koncu pliku - zeby bledna zmiana w jednym miejscu nie przeszla dlatego,
ze poprawiono pod nia oczekiwanie w tescie czastkowym.
"""
from decimal import Decimal

import pytest

from silnik.rdzen import podatki, stawki

NETTO = Decimal("11200.00")
VAT23 = Decimal("0.23")
R85 = Decimal("0.085")


def _policz(przychod="0.00", naliczone=False, netto=NETTO, stawka=R85):
    return podatki.policz_ryczalt(
        kwota_netto=netto,
        stawka_ryczaltu=stawka,
        stawka_vat=VAT23,
        przychod_narastajaco=Decimal(przychod),
        skladki_juz_naliczone_w_miesiacu=naliczone,
    )


# --- progi ----------------------------------------------------------------

def test_prog_liczony_po_osiagnieciu_nie_po_przekroczeniu():
    """Odczyt ostrozniejszy, pozycja 12.2 specyfikacji.

    Tabela zrodlowa mowi "od 60 tys.", tekst obok "przekroczyly 60 tys.".
    Rowne 60 000 -> wyzszy prog, wyzsza rezerwa.
    """
    assert podatki.prog_dla_przychodu(Decimal("59999.99")) == 1
    assert podatki.prog_dla_przychodu(Decimal("60000.00")) == 2
    assert podatki.prog_dla_przychodu(Decimal("299999.99")) == 2
    assert podatki.prog_dla_przychodu(Decimal("300000.00")) == 3


def test_miesiac_przekroczenia_wchodzi_juz_na_wyzszy_prog():
    """Cytat ze zrodla: "Jesli w ktorym miesiacu przekroczysz kwote przychodow,
    to skladke ZA TEN MIESIAC musisz rozliczyc od podstawy wymiaru
    obowiazujacej dla kolejnego progu przychodow".

    55 000 narastajaco + faktura 11 200 = 66 200 -> prog 2 juz w tym miesiacu.
    """
    w = _policz(przychod="55000.00")
    assert w.prog_zdrowotnej == 2
    assert w.zdrowotna == Decimal("830.58")


def test_prog_liczony_z_faktura_a_nie_bez_niej():
    """Kontrola dwustronna do testu wyzej: bez doliczenia faktury bylby prog 1."""
    assert podatki.prog_dla_przychodu(Decimal("55000.00")) == 1


# --- odliczenia -----------------------------------------------------------

def test_odliczenie_polowy_zdrowotnej_nie_calosci():
    w = _policz()
    oczekiwana = NETTO - w.spoleczne - stawki.do_groszy(w.zdrowotna / 2)
    assert w.podstawa_ryczaltu == oczekiwana
    assert w.podstawa_ryczaltu == Decimal("9024.06")


def test_spoleczne_odliczane_w_calosci():
    w = _policz()
    assert w.spoleczne == Decimal("1926.76")


# --- rezerwa raz w miesiacu ----------------------------------------------

def test_rezerwa_zus_naliczana_raz_w_miesiacu():
    """Druga faktura w tym samym miesiacu nie odklada skladek po raz drugi
    ani nie odlicza ich po raz drugi od podstawy."""
    druga = _policz(przychod="11200.00", naliczone=True)
    assert druga.zdrowotna == Decimal("0.00")
    assert druga.spoleczne == Decimal("0.00")
    assert druga.podstawa_ryczaltu == NETTO


def test_pierwsza_faktura_w_miesiacu_naklada_pelne_skladki():
    """Kontrola dwustronna: bez niej test wyzej przeszedlby przy skladkach
    zawsze rownych zeru."""
    pierwsza = _policz()
    assert pierwsza.zdrowotna > 0
    assert pierwsza.spoleczne > 0


# --- zaokraglenia ---------------------------------------------------------

def test_pit_zaokraglony_do_pelnych_zlotych():
    """Art. 63 Ordynacji podatkowej."""
    w = _policz()
    assert w.pit == w.pit.quantize(Decimal("1"))
    assert w.pit == Decimal("767")


def test_vat_liczony_od_netto():
    assert _policz().vat == Decimal("2576.00")


# --- zalozenia ------------------------------------------------------------

def test_zalozenia_zawsze_niepuste_i_nazywaja_uproszczenia():
    """Liczba bez widocznych zalozen udaje precyzje, ktorej nie ma."""
    z = _policz().zalozenia
    assert len(z) >= 4
    assert any("60 000" in x for x in z)          # rozstrzygniecie granicy progu
    assert any("zapłacone" in x for x in z)       # rezerwa kontra skladka zaplacona
    assert any("naliczon" in x for x in z)        # VAT nie zna strony naliczonej
    assert any("2026-08-25" in x for x in z)      # data odczytu stawek


# --- przekrojowy ----------------------------------------------------------

def test_przekrojowy_faktura_11200_na_8_5_procent():
    """Wszystkie liczby jednego wyliczenia naraz, policzone recznie:

    netto      11 200,00
    VAT 23%     2 576,00
    zdrowotna     498,35   (prog 1, przychod narastajaco 11 200 < 60 000)
    spoleczne   1 926,76   (duzy ZUS z chorobowa)
    podstawa    9 024,06   = 11 200 - 1 926,76 - 249,18
    PIT               767  = 9 024,06 x 8,5% = 767,0451 -> pelne zlote
    zostaje     8 007,89   = 11 200 - 498,35 - 1 926,76 - 767
    """
    w = _policz()
    assert w.vat == Decimal("2576.00")
    assert w.zdrowotna == Decimal("498.35")
    assert w.spoleczne == Decimal("1926.76")
    assert w.podstawa_ryczaltu == Decimal("9024.06")
    assert w.pit == Decimal("767")
    assert w.do_dyspozycji == Decimal("8007.89")
    assert w.prog_zdrowotnej == 1


def test_suma_sie_domyka():
    """Kontrola licznosci na poziomie arytmetyki: nic nie ginie i nic nie przybywa."""
    w = _policz()
    assert w.kwota_netto == w.zdrowotna + w.spoleczne + w.pit + w.do_dyspozycji


@pytest.mark.parametrize("stawka, pit", [
    ("0.085", "767"), ("0.12", "1083"), ("0.15", "1354"),
])
def test_pit_dla_roznych_stawek_ryczaltu(stawka, pit):
    """Podstawa ta sama, zmienia sie tylko stawka - roznica 8,5 kontra 15 procent
    to 587 zl na jednej fakturze."""
    assert _policz(stawka=Decimal(stawka)).pit == Decimal(pit)

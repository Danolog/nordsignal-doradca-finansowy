"""Strazniki mostu faktura -> budzet osobisty (Zadanie 24).

Decyzja Darka D1 (2026-08-25): UJECIE KASOWE. Jedno konto obsluguje firme
i dom, JDG nie jest spolka — pieniadze sa osobiste od chwili wplywu. Faktura
zaplacona wchodzi wiec do budzetu jako przychod w kwocie BRUTTO, w dacie
WPLYWU, a VAT, ZUS i ryczalt sa osobnymi wydatkami w miesiacu zaplaty.

Dwie rzeczy, ktore te straznicy trzymaja za gardlo:
  1. data WPLYWU, nie wystawienia — faktura platna 14 dni pokazywalaby
     pieniadze o dwa tygodnie za wczesnie;
  2. brak podwojnego liczenia — druga proba przeniesienia tej samej faktury
     nie moze utworzyc drugiego przychodu.
"""

from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import budzet, magazyn


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 8, 25), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    return polaczenie


def _faktura(polaczenie):
    return magazyn.wczytaj_faktury(polaczenie).iloc[0]


# --- przeniesienie --------------------------------------------------------

def test_zaplacona_faktura_tworzy_przychod_BRUTTO(p):
    """Na konto wplywa netto RAZEM z VAT-em. Przychod w kwocie netto ukrylby
    2 576 zl, ktore realnie na koncie leza — i ktore trzeba oddac urzedowi."""
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=int(_faktura(p)["id"]),
                                     data_wplywu=date(2026, 9, 10))
    wpisy = magazyn.wczytaj_wpisy(p)
    assert len(wpisy) == 1
    assert wpisy.iloc[0]["typ"] == budzet.TYP_PRZYCHODY
    assert wpisy.iloc[0]["kwota"] == Decimal("13776.00")


def test_wpis_ma_date_WPLYWU_nie_wystawienia(p):
    """Faktura z 25 sierpnia zaplacona 10 wrzesnia to przychod WRZESNIA.
    Data wystawienia kazalaby budzetowi sierpnia pokazac pieniadze,
    ktorych w sierpniu na koncie nie bylo."""
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=int(_faktura(p)["id"]),
                                     data_wplywu=date(2026, 9, 10))
    assert magazyn.wczytaj_wpisy(p).iloc[0]["data"] == date(2026, 9, 10)


def test_wpis_wskazuje_numer_faktury(p):
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=int(_faktura(p)["id"]),
                                     data_wplywu=date(2026, 9, 10))
    assert "FV/1/2026" in magazyn.wczytaj_wpisy(p).iloc[0]["szczegoly"]


def test_druga_proba_nie_tworzy_drugiego_przychodu(p):
    """Podwojne liczenie przychodu zawyza „do alokacji" o cala fakture."""
    numer = int(_faktura(p)["id"])
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 10))
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 11))
    assert len(magazyn.wczytaj_wpisy(p)) == 1


# --- prawda o przeniesieniu -----------------------------------------------

def test_skasowanie_wpisu_przywraca_stan_nieprzeniesiona(p):
    """PRAWDA O PRZENIESIENIU TO ISTNIENIE WPISU, NIE ZNACZNIK. Wpis mozna
    skasowac recznie w zakladce Budzet; gdyby liczyl sie sam znacznik,
    faktura zostalaby „przeniesiona" bez przychodu nigdzie — czyli pieniadze
    znikneleyby cicho."""
    numer = int(_faktura(p)["id"])
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 10))
    assert magazyn.czy_przeniesiona(p, faktura_id=numer) is True

    magazyn.usun_wpis(p, wpis_id=int(magazyn.wczytaj_wpisy(p).iloc[0]["id"]))
    assert magazyn.czy_przeniesiona(p, faktura_id=numer) is False


def test_po_skasowaniu_wpisu_mozna_przeniesc_ponownie(p):
    numer = int(_faktura(p)["id"])
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 10))
    magazyn.usun_wpis(p, wpis_id=int(magazyn.wczytaj_wpisy(p).iloc[0]["id"]))
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 12))
    assert len(magazyn.wczytaj_wpisy(p)) == 1
    assert magazyn.wczytaj_wpisy(p).iloc[0]["data"] == date(2026, 9, 12)


def test_data_zaplaty_zapisuje_sie_przy_fakturze(p):
    numer = int(_faktura(p)["id"])
    magazyn.oznacz_fakture_zaplacona(p, faktura_id=numer,
                                     data_wplywu=date(2026, 9, 10))
    assert _faktura(p)["data_zaplaty"] == date(2026, 9, 10)


def test_swiezo_wystawiona_faktura_jest_nieprzeniesiona(p):
    assert magazyn.czy_przeniesiona(p, faktura_id=int(_faktura(p)["id"])) is False
    assert _faktura(p)["data_zaplaty"] in (None, "")


# --- straznik zrodlowy starego interfejsu — NIEPRZENIESIONY -----------------
#
# Stal tu straznik czytajacy `pulpit/jdg.py` — zakladke starego interfejsu
# NiceGUI. Nie przenosi sie: `pulpit/` jest wygaszany razem z cala poprzednia
# aplikacja (PRD rozdz. 15), a nowy interfejs (`interfejs/`) ma wlasne ekrany
# i wlasnych straznikow, pisanych przez wykonawce ekranu.
#
# CO PRZEZ TO PRZESTAJE DZIALAC — nikt nie pilnuje, ze ekran faktur wola `oznacz_fakture_zaplacona`
# i `czy_przeniesiona`. Sama funkcja jest przetestowana; NIEPILNOWANE jest
# to, czy interfejs ja wola. Wraca z ekranem Firma.
#
# Zrodlo zostaje w `../AI CFO/testy/test_faktura_do_budzetu.py` i tam nadal dziala.

"""Strazniki ewidencji kosztow JDG (Zadanie 23).

Decyzja Darka D2 (2026-08-25): koszty maja wlasna tabele w zakladce JDG,
a kazdy koszt tworzy automatycznie wydatek `Firmowe` w budzecie. Powod:
jedno konto obsluguje firme i dom, wiec zakup firmowy jest realnym wyplywem
z tego samego rachunku, co czynsz.

GRANICA PODATKOWA, ktora te straznicy pilnuja: przy RYCZALCIE od przychodow
ewidencjonowanych koszt NIE pomniejsza podatku dochodowego — podstawa jest
przychod, nie dochod. Ewidencja kosztow sluzy TYLKO obrazowi pieniedzy
i VAT-owi naliczonemu. Test `test_koszt_nie_rusza_ryczaltu_ani_zus`
zamienia to zdanie ze specyfikacji w rzecz sprawdzalna.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn, podatki
from testy import pomocnicze


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz()


def _faktura(polaczenie) -> None:
    """FV 1/2026 Darka: VAT 2 576,00, ZUS 2 425,11, ryczalt 767,00."""
    magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 8, 25), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")


# --- zapis kosztu ---------------------------------------------------------

def test_koszt_tworzy_dokladnie_jeden_wydatek_firmowy(p):
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    wpisy = magazyn.wczytaj_wpisy(p)
    assert len(wpisy) == 1
    assert wpisy.iloc[0]["typ"] == budzet.TYP_WYDATKI
    assert wpisy.iloc[0]["kategoria"] == "Firmowe"


def test_wydatek_jest_na_kwote_BRUTTO_nie_netto(p):
    """Z konta wyplywa netto RAZEM z VAT-em. Wpis na kwote netto zanizylby
    wydatki o VAT, ktory realnie zaplaciles — i „do alokacji" pokazywaloby
    pieniadze, ktorych juz nie ma."""
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    assert magazyn.wczytaj_wpisy(p).iloc[0]["kwota"] == Decimal("4920.00")


def test_wpis_niesie_opis_kosztu(p):
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="ksiegowosc",
                         kwota_netto=Decimal("200.00"),
                         kwota_vat=Decimal("46.00"))
    assert "ksiegowosc" in magazyn.wczytaj_wpisy(p).iloc[0]["szczegoly"]


def test_koszty_wracaja_jako_decimal(p):
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    koszty = magazyn.wczytaj_koszty(p)
    assert koszty.iloc[0]["kwota_netto"] == Decimal("4000.00")
    assert isinstance(koszty.iloc[0]["kwota_vat"], Decimal)


# --- kasowanie ------------------------------------------------------------

def test_skasowanie_kosztu_kasuje_powiazany_wydatek(p):
    """Jedno dzialanie, jedno znaczenie. Osierocony wydatek `Firmowe` bez
    kosztu to podwojne liczenie przy nastepnym wpisie tej samej faktury."""
    numer = magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                                 kwota_netto=Decimal("4000.00"),
                                 kwota_vat=Decimal("920.00"))
    magazyn.usun_koszt(p, koszt_id=numer)
    assert len(magazyn.wczytaj_koszty(p)) == 0
    assert len(magazyn.wczytaj_wpisy(p)) == 0


def test_kasowanie_kosztu_gdy_wpis_juz_znikl_nie_wybucha(p):
    """Wpis mozna skasowac recznie w zakladce Budzet. Kasowanie kosztu ma
    wtedy dojsc do konca, a nie przerwac sie w polowie."""
    numer = magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                                 kwota_netto=Decimal("4000.00"),
                                 kwota_vat=Decimal("920.00"))
    magazyn.usun_wpis(p, wpis_id=int(magazyn.wczytaj_wpisy(p).iloc[0]["id"]))
    magazyn.usun_koszt(p, koszt_id=numer)
    assert len(magazyn.wczytaj_koszty(p)) == 0


# --- wplyw na rezerwe -----------------------------------------------------
#
# Z55: rezerwa liczy ZUS z MIESIECY dzialalnosci. Okres to jeden miesiac
# (sierpien 2026), wiec liczby ponizej zostaja te same — skladka za jeden
# miesiac to dokladnie 2 425,11 zl. Zmienil sie POWOD tej liczby, nie ona.

DZIALALNOSC_OD = date(2026, 8, 1)
KONIEC_SIERPNIA = date(2026, 8, 31)


def _rezerwa(polaczenie, koszty):
    return podatki.rezerwa_na_podatki(
        magazyn.wczytaj_faktury(polaczenie), koszty,
        magazyn.wczytaj_wpisy(polaczenie),
        dzialalnosc_od=DZIALALNOSC_OD, dzis=KONIEC_SIERPNIA,
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))



def test_koszt_pomniejsza_vat_do_zaplaty(p):
    _faktura(p)
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    r = _rezerwa(p, magazyn.wczytaj_koszty(p))
    assert r.vat_naliczony == Decimal("920.00")
    assert r.vat_do_zaplaty == Decimal("1656.00")


def test_koszt_nie_rusza_ryczaltu_ani_zus(p):
    """GRANICA Z par. 3 SPECYFIKACJI. Przy ryczalcie podstawa jest PRZYCHOD,
    nie dochod — koszt nie obniza podatku dochodowego ani skladek. Kazdy
    przyszly pomysl, zeby bylo inaczej, zaczerwieni ten test."""
    _faktura(p)
    bez = _rezerwa(p, pd.DataFrame())
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    z_kosztem = _rezerwa(p, magazyn.wczytaj_koszty(p))
    assert z_kosztem.podatek_dochodowy == bez.podatek_dochodowy == Decimal("767.00")
    assert z_kosztem.zus == bez.zus == Decimal("2425.11")


# --- prog z Zadania 22a zamkniety -----------------------------------------

def test_koszty_sa_juz_parametrem_obowiazkowym():
    """Zadanie 22a zostawilo `koszty=None` z jawnym progiem: „przy dodaniu
    tabeli koszty_jdg wartosc domyslna znika". Tabela jest — prog domkniety,
    zeby pominiecie kosztow przestalo byc mozliwe przez przeoczenie."""
    with pytest.raises(TypeError):
        podatki.rezerwa_na_podatki(pd.DataFrame())


def test_schemat_zna_tabele_kosztow(p):
    tabele = pomocnicze.tabele_w_bazie(p)
    assert "koszty_jdg" in tabele
    assert p.execute(
        "SELECT wersja FROM wersja_schematu WHERE jedyny"
    ).fetchone()[0] == magazyn.WERSJA_SCHEMATU

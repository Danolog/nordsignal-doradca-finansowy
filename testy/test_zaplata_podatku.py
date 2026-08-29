"""Strazniki podpowiedzi „ile i kiedy zaplacic" (Zadanie 25).

Rezerwa liczona jako saldo (D3) spada dopiero wtedy, gdy zaplata trafi do
budzetu jako wydatek w kategorii `Podatki i ZUS`. Zeby to nie bylo cwiczeniem
z pamieci, zakladka JDG pokazuje ROZBICIE saldo na trzy daniny z terminami
i pozwala zapisac zaplate jednym przyciskiem.

Rozbicie liczy sie z tego samego nosnika, co kafel Pulpitu
(`podatki.rezerwa_na_podatki`) — inaczej dwie liczby na dwoch ekranach
rozjechalyby sie przy pierwszej poprawce.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn, podatki


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


#: Dzialalnosc od sierpnia 2026, patrzymy na koniec sierpnia — JEDEN miesiac
#: skladek. Liczby w tym pliku zostaja bez zmian po Z55 i to nie przypadek:
#: skladka za jeden miesiac to dokladnie 2 425,11 zl, czyli tyle, ile niosla
#: kolumna `zaplacony_zus` tej faktury. Zmienil sie POWOD tej liczby, nie ona.
DZIALALNOSC_OD = date(2026, 8, 1)
KONIEC_SIERPNIA = date(2026, 8, 31)


def _rezerwa(polaczenie):
    return podatki.rezerwa_na_podatki(magazyn.wczytaj_faktury(polaczenie),
                                      magazyn.wczytaj_koszty(polaczenie),
                                      magazyn.wczytaj_wpisy(polaczenie),
                                      dzialalnosc_od=DZIALALNOSC_OD,
                                      dzis=KONIEC_SIERPNIA,
                                      forma="RYCZALT",
                                      stawka_ryczaltu=Decimal("0.085"))


# --- rozbicie do zaplaty --------------------------------------------------

def test_rozbicie_wymienia_trzy_daniny_z_terminami(p):
    pozycje = podatki.do_zaplaty(_rezerwa(p), date(2026, 9, 5),
                                magazyn.wczytaj_wpisy(p))
    assert [x.nazwa for x in pozycje] == ["Ryczałt", "ZUS", "VAT"]
    assert [str(x.kwota) for x in pozycje] == ["767.00", "2425.11", "1656.00"] \
        or [str(x.kwota) for x in pozycje] == ["767.00", "2425.11", "2576.00"]


def test_rozbicie_sumuje_sie_do_naliczonych(p):
    """Suma pozycji MUSI byc rowna kwocie z kafla. Rozjazd oznacza, ze jedno
    z dwoch miejsc liczy po swojemu — dokladnie ta wada, ktora Zadanie 22a
    zlikwidowalo przy rezerwie."""
    r = _rezerwa(p)
    pozycje = podatki.do_zaplaty(r, date(2026, 9, 5),
                                 magazyn.wczytaj_wpisy(p))
    assert sum((x.kwota for x in pozycje), Decimal("0.00")) == r.naliczone_razem


def test_vat_w_rozbiciu_jest_juz_po_odliczeniu(p):
    """Pozycja VAT ma pokazywac to, co realnie przelewasz — czyli nalezny
    minus naliczony, nie sam nalezny."""
    magazyn.zapisz_koszt(p, data=date(2026, 8, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    vat = next(x for x in podatki.do_zaplaty(
        _rezerwa(p), date(2026, 9, 5), magazyn.wczytaj_wpisy(p))
        if x.nazwa == "VAT")
    assert vat.kwota == Decimal("1656.00")


def test_kazda_pozycja_niesie_swoj_termin(p):
    pozycje = podatki.do_zaplaty(_rezerwa(p), date(2026, 9, 5),
                                magazyn.wczytaj_wpisy(p))
    vat = next(x for x in pozycje if x.nazwa == "VAT")
    zus = next(x for x in pozycje if x.nazwa == "ZUS")
    assert vat.termin == date(2026, 9, 25)
    assert zus.termin == date(2026, 9, 21)   # 20.09.2026 to niedziela


def test_zaplacone_do_zera_znika_z_rozbicia(p):
    """Pozycja na 0,00 zl to szum. Po zaplaceniu wszystkiego lista ma byc pusta,
    a nie pelna zer."""
    magazyn.zapisz_wpis(p, data=date(2026, 9, 20), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("5768.11"), szczegoly="wszystko")
    assert podatki.do_zaplaty(_rezerwa(p), date(2026, 9, 5),
                                magazyn.wczytaj_wpisy(p)) == []


def test_czesciowa_zaplata_zdejmuje_od_najwczesniejszego_terminu(p):
    """Placisz po kolei: najpierw to, co ma najblizszy termin. Rozliczenie
    zaplaty od najdalszego terminu pokazywaloby jako niezaplacone to,
    co wlasnie zaplaciles."""
    magazyn.zapisz_wpis(p, data=date(2026, 9, 20), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("767.00"), szczegoly="ryczalt")
    nazwy = [x.nazwa for x in podatki.do_zaplaty(_rezerwa(p), date(2026, 9, 5),
                                magazyn.wczytaj_wpisy(p))]
    assert "Ryczałt" not in nazwy
    assert nazwy == ["ZUS", "VAT"]


def test_nadplata_nie_daje_pozycji_ujemnych(p):
    magazyn.zapisz_wpis(p, data=date(2026, 9, 20), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("9999.00"), szczegoly="z gorka")
    assert podatki.do_zaplaty(_rezerwa(p), date(2026, 9, 5),
                                magazyn.wczytaj_wpisy(p)) == []


def test_zaplata_podpisana_nazwa_daniny_zdejmuje_TE_danine(p):
    """WADA WYKRYTA KLIKANIEM 2026-08-25, nie testem. Kliknięcie „Zapłacone"
    przy Ryczalcie zapisywalo wydatek, ale rozliczenie szlo od najblizszego
    terminu — a ten mial VAT. Zniknelo wiec 767 zl z VAT-u, Ryczalt zostal,
    i przycisk mowil co innego, niz robil.

    Zaplata podpisana nazwa daniny idzie na TE danine, niezaleznie od tego,
    ktory termin jest blizszy."""
    magazyn.zapisz_wpis(p, data=date(2026, 8, 25), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("767.00"),
                        szczegoly="Ryczałt, termin 2026-09-21")
    # 25 sierpnia: najblizszy termin ma VAT (25.08), nie Ryczalt (21.09).
    pozycje = podatki.do_zaplaty(_rezerwa(p), date(2026, 8, 25),
                                 magazyn.wczytaj_wpisy(p))
    nazwy = {x.nazwa: x.kwota for x in pozycje}
    assert "Ryczałt" not in nazwy, "zaplata trafila w niewlasciwa danine"
    assert nazwy["VAT"] == Decimal("2576.00"), "VAT zostal ruszony bez powodu"


def test_nadwyzka_zaplaty_daniny_nie_przechodzi_na_inna(p):
    """Zaplaciles za duzo ryczaltu — to nadplata rycza tu, nie zaliczka na VAT.
    Przelanie nadwyzki na inna danine pokazywaloby VAT jako czesciowo
    zaplacony, choc urzad nie widzial ani zlotowki."""
    magazyn.zapisz_wpis(p, data=date(2026, 8, 25), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("5000.00"),
                        szczegoly="Ryczałt, termin 2026-09-21")
    nazwy = {x.nazwa: x.kwota for x in
             podatki.do_zaplaty(_rezerwa(p), date(2026, 8, 25),
                                magazyn.wczytaj_wpisy(p))}
    assert nazwy["VAT"] == Decimal("2576.00")
    assert nazwy["ZUS"] == Decimal("2425.11")


# --- trzy strazniki zrodlowe starego interfejsu — NIEPRZENIESIONE ----------
#
# Staly tu trzy strazniki czytajace `pulpit/jdg.py`, zakladke starego
# interfejsu NiceGUI: `test_zakladka_jdg_pokazuje_rozbicie`, `test_interfejs_nie_przypisuje_kwoty_do_miesiaca_rozliczeniowego`, `test_prognoza_progu_zdrowotnej_nie_jest_pokazywana`.
# Nie przenosza sie — `pulpit/` jest wygaszany razem z poprzednia aplikacja
# (PRD rozdz. 15), a nowy interfejs ma wlasne ekrany i wlasnych straznikow.
#
# CO PRZEZ TO PRZESTAJE DZIALAC. NIEPILNOWANE zostaja trzy reguly interfejsu:
#   (a) ekran firmy wola `podatki.do_zaplaty` i zapisuje zaplate pod
#       `KATEGORIA_PODATKI`;
#   (b) ekran NIE przypisuje kwoty daniny do miesiaca rozliczeniowego
#       (saldo nie sledzi okresow — D3);
#   (c) prognoza progu zdrowotnej NIE jest pokazywana z ekranu
#       (decyzja Darka 2026-08-26, godz. 00:08).
# Regula (c) jest decyzja o tym, co widzi uzytkownik, wiec wraca jako wymog
# do ekranu Firma. Same funkcje silnika sa przetestowane wyzej; niepilnowane
# jest wylacznie OKABLOWANIE.
#
# Zrodlo zostaje w `../AI CFO/testy/test_zaplata_podatku.py` i tam dziala.

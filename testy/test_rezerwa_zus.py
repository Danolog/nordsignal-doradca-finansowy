"""Strazniki rezerwy ZUS liczonej z MIESIECY DZIALALNOSCI, nie z faktur (Z55).

Wada zamykana tym zadaniem, zmierzona 2026-08-26. `rezerwa_na_podatki`
sumowala kolumne `przychody_jdg.zaplacony_zus`, czyli mierzyla LICZBE FAKTUR,
a nie liczbe miesiecy. Miesiac bez zlecenia nie naliczal skladki. Przy trzech
miesiacach dzialalnosci i dwoch fakturach dawalo to **4 850,22 zl zamiast
7 275,33 zl** — brakowalo pelnej skladki za jeden miesiac.

To nie byl blad arytmetyki, tylko POMIAR NIEWLASCIWEJ RZECZY. Kolumna
`zaplacony_zus` odpowiada na pytanie „co mi zostaje z tej faktury"; rezerwa
pyta „ile mam odlozyc". Obie liczby sa poprawne i MAJA PRAWO sie roznic —
wada polegala na pokazaniu jednej pod etykieta drugiej. Dlatego kolumna
ZOSTAJE w tabeli jako zapis historyczny rozbicia faktury.

Skladka za jeden miesiac na progu 1: 498,35 (zdrowotna) + 1 926,76
(spoleczne z chorobowa) = 2 425,11 zl. Zrodlo: `rdzen.stawki`, zero kwot
zaszytych w tym pliku poza wynikami przekrojowymi.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import podatki, stawki

#: Skladka za miesiac na progu 1 — liczona ze stawek, nie przepisana.
MIESIAC_PROG_1 = (stawki.skladka_zdrowotna(stawki.PROGI_ZDROWOTNEJ[0].mnoznik)
                  + stawki.suma_spolecznych(z_chorobowa=True))


def _faktury(*trojki) -> pd.DataFrame:
    """(data, netto, vat, zus, zysk) — kolumny jak w tabeli przychody_jdg."""
    return pd.DataFrame([
        {"data": d, "kwota_netto": Decimal(n), "kwota_vat": Decimal(v),
         "zaplacony_zus": Decimal(z), "zysk_netto": Decimal(y)}
        for d, n, v, z, y in trojki
    ])


# --- sedno: miesiace, nie faktury ----------------------------------------

def test_TRZY_miesiace_dwie_faktury_daja_TRZY_skladki():
    """Kryterium odbioru planu Z55, dokladnie w jego brzmieniu:
    dzialalnosc od 2026-09, data 2026-11-30, faktury we wrzesniu i listopadzie
    → rezerwa ZUS = 3 x skladka, nie 2 x."""
    faktury = _faktury(
        ("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89"),
        ("2026-11-10", "11200.00", "2576.00", "2425.11", "8007.89"))
    s = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 9, 1), do=date(2026, 11, 30), forma="RYCZALT")

    assert s.miesiace == 3, "pomiar zobaczyl inna liczbe miesiecy niz trzy"
    assert s.razem == 3 * MIESIAC_PROG_1
    assert s.razem == Decimal("7275.33")
    assert s.razem != Decimal("4850.22"), "to jest liczba PRZED naprawa"


def test_miesiac_BEZ_faktury_podnosi_rezerwe():
    """Kryterium odbioru planu Z55. Kontrola dwustronna do testu wyzej:
    ta sama jedna faktura, dwa rozne okresy dzialalnosci."""
    faktury = _faktury(("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89"))
    jeden = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 9, 1), do=date(2026, 9, 30), forma="RYCZALT")
    dwa = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 9, 1), do=date(2026, 10, 31), forma="RYCZALT")

    assert jeden.miesiace == 1 and dwa.miesiace == 2
    assert dwa.razem > jeden.razem
    assert dwa.razem - jeden.razem == MIESIAC_PROG_1


def test_BRAK_faktur_nie_zeruje_skladek():
    """Skladke placi sie za miesiac dzialalnosci, nie za miesiac przychodu.
    To jest cala roznica miedzy stara regula a nowa."""
    s = podatki.skladki_zus_za_miesiace(
        pd.DataFrame(), od=date(2026, 9, 1), do=date(2026, 11, 30),
        forma="RYCZALT")
    assert s.miesiace == 3
    assert s.razem == 3 * MIESIAC_PROG_1


# --- zdrowotna wedlug progu TEGO miesiaca --------------------------------

def test_zdrowotna_ROSNIE_po_przekroczeniu_progu():
    """Prog zdrowotnej zalezy od przychodu narastajaco — a ten rosnie w trakcie
    roku. Skladka za grudzien moze byc wyzsza niz za styczen i to nie jest blad.
    Stala skladka przez caly rok zanizylaby rezerwe u kazdego, kto przekroczy
    60 tys."""
    faktury = _faktury(
        ("2026-01-15", "70000.00", "16100.00", "2425.11", "50000.00"))
    s = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 1, 1), do=date(2026, 2, 28), forma="RYCZALT")

    assert s.progi == (2, 2), f"progi miesiecy: {s.progi}"
    assert s.zdrowotna == 2 * stawki.skladka_zdrowotna(
        stawki.PROGI_ZDROWOTNEJ[1].mnoznik)


def test_prog_liczy_sie_NARASTAJACO_a_nie_z_miesiaca():
    """Kontrola dwustronna: prog ma zalezec od sumy od poczatku roku,
    nie od przychodu samego miesiaca. Trzy faktury po 25 tys. przekraczaja
    60 tys. dopiero razem."""
    faktury = _faktury(
        ("2026-01-15", "25000.00", "5750.00", "2425.11", "20000.00"),
        ("2026-02-15", "25000.00", "5750.00", "2425.11", "20000.00"),
        ("2026-03-15", "25000.00", "5750.00", "2425.11", "20000.00"))
    s = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 1, 1), do=date(2026, 3, 31), forma="RYCZALT")
    assert s.progi == (1, 1, 2), f"progi miesiecy: {s.progi}"


def test_przelom_roku_ZERUJE_narastajaco():
    """Prog liczy sie w roku kalendarzowym. Przychod z grudnia nie podnosi
    skladki styczniowej — inaczej po dobrym roku rezerwa startowalaby
    od najwyzszego progu."""
    faktury = _faktury(
        ("2026-06-15", "200000.00", "46000.00", "2425.11", "150000.00"))
    s = podatki.skladki_zus_za_miesiace(
        faktury, od=date(2026, 12, 1), do=date(2027, 1, 31), forma="RYCZALT")
    assert s.progi == (2, 1), f"progi miesiecy: {s.progi}"


def test_pomiar_WIDZI_kazdy_miesiac_z_osobna():
    """Kontrola licznosci wymagana przez plan: test asertuje LICZBE MIESIECY
    widzianych przez pomiar, nie tylko kwote. Pomiar, do ktorego nic nie
    dociera, zameldowalby sukces kwota zero."""
    s = podatki.skladki_zus_za_miesiace(
        pd.DataFrame(), od=date(2026, 1, 1), do=date(2026, 12, 31),
        forma="RYCZALT")
    assert s.miesiace == 12
    assert len(s.progi) == 12, "kazdy miesiac ma miec wlasny odczyt progu"


def test_ODWROCONE_daty_sa_bledem():
    with pytest.raises(podatki.BladMagazynu):
        podatki.skladki_zus_za_miesiace(
            pd.DataFrame(), od=date(2026, 12, 1), do=date(2026, 9, 1),
            forma="RYCZALT")


# --- wpiecie w rezerwe ----------------------------------------------------

def test_rezerwa_bierze_ZUS_z_miesiecy_a_nie_z_kolumny_faktury():
    """Straznik wiazacy: gdyby ktos wrocil do `_suma(faktury, 'zaplacony_zus')`,
    ta sama faktura dalaby 2 425,11 zamiast 7 275,33."""
    faktury = _faktury(
        ("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89"),
        ("2026-11-10", "11200.00", "2576.00", "2425.11", "8007.89"))
    r = podatki.rezerwa_na_podatki(
        faktury, pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=date(2026, 9, 1), dzis=date(2026, 11, 30),
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))

    assert r.zus == Decimal("7275.33")
    assert r.miesiace_zus == 3


def test_rezerwa_BEZ_daty_dzialalnosci_nie_udaje_ze_wie():
    """`miesiace_zus is None` to JEDYNY dyskryminator „nie liczylem ZUS".
    Sama kwota zero znaczylaby „skladek nie ma" — czyli najlepszy mozliwy
    stan pokazany przy braku wiedzy (D11)."""
    faktury = _faktury(("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89"))
    r = podatki.rezerwa_na_podatki(
        faktury, pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=None, dzis=date(2026, 11, 30),
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))

    assert r.miesiace_zus is None
    assert r.zastrzezenia, "brak ZUS ma byc NAZWANY, nie przemilczany"
    assert any("dzialalnos" in z.lower() or "działalnoś" in z.lower()
               for z in r.zastrzezenia)


def test_rezerwa_Z_data_nie_niesie_zastrzezenia_o_ZUS():
    """Kontrola dwustronna: zastrzezenie ma sie pojawiac tylko wtedy, gdy jest
    czego zastrzegac. Zastrzezenie przy kazdym uruchomieniu przestaje sie czytac."""
    faktury = _faktury(("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89"))
    r = podatki.rezerwa_na_podatki(
        faktury, pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=date(2026, 9, 1), dzis=date(2026, 9, 30),
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))
    assert r.zastrzezenia == ()


# --- zbieracz: czy w ogole podaje date silnikowi -------------------------
# M209 PRZEZYLA pierwszy przebieg mutacyjny. `rezerwa_z_bazy` to jedyna droga,
# ktora wszystkie cztery ekrany maja do rezerwy — a gdyby przestala podawac
# date dzialalnosci, kazdy z nich pokazalby rezerwe zanizona o pelne skladki,
# przy zielonej suicie. Straznik „doradca i pulpit podaja te sama kwote" tego
# nie lapie, bo obie strony wolaja TEN SAM zbieracz: porownuje rzecz z nia sama.

def test_zbieracz_PODAJE_silnikowi_date_z_bazy(tmp_path):
    from silnik.rdzen import magazyn

    p = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_dzialalnosc_od(p, date(2026, 9, 1))
    magazyn.zapisz_fakture(
        p, data=date(2026, 9, 10), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")

    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")

    r = podatki.rezerwa_z_bazy(p, dzis=date(2026, 11, 30))
    assert r.miesiace_zus == 3, "zbieracz nie podal daty rozpoczecia dzialalnosci"
    assert r.zus == Decimal("7275.33")

    # ZMIANA Z59: zbieracz czyta z bazy takze FORME, a zaczep migracyjny
    # wpisuje na 2026 SKALE. Bez jawnego przestawienia na ryczalt ten test
    # mierzylby skladke zdrowotna liczona OD DOCHODU, nie z progu przychodu —
    # czyli inna liczbe, i to poprawnie. Straznik formy w zbieraczu: nizej.
    assert r.forma == magazyn.FORMA_RYCZALT
    p.close()


def test_zbieracz_BEZ_daty_w_bazie_melduje_nie_wiem(tmp_path):
    """Kontrola dwustronna: zbieracz ma podawac to, co jest w bazie —
    takze wtedy, gdy nie ma tam nic."""
    from silnik.rdzen import magazyn

    p = magazyn.zmigruj_i_polacz()
    r = podatki.rezerwa_z_bazy(p, dzis=date(2026, 11, 30))
    assert r.miesiace_zus is None
    assert r.zastrzezenia
    p.close()


def test_zbieracz_PODAJE_silnikowi_takze_FORME_z_bazy(tmp_path):
    """Siostra testu wyzej, dolozona w Z59. Zbieracz jest jedyna droga
    czterech ekranow do rezerwy — gdyby przestal podawac forme, kazdy z nich
    liczylby ryczaltem takze osobie na skali, przy zielonej suicie."""
    from silnik.rdzen import magazyn

    p = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_dzialalnosc_od(p, date(2026, 9, 1))
    r = podatki.rezerwa_z_bazy(p, dzis=date(2026, 11, 30))
    assert r.forma == magazyn.FORMA_SKALA, \
        "zbieracz nie przeczytal formy z bazy (zaczep wpisuje SKALE na 2026)"
    assert r.nazwa_podatku == "PIT"

    magazyn.zapisz_forme(p, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu="0.085")
    r2 = podatki.rezerwa_z_bazy(p, dzis=date(2026, 11, 30))
    assert r2.forma == magazyn.FORMA_RYCZALT, "kontrola dwustronna"
    assert r2.nazwa_podatku == "Ryczałt"
    p.close()


def test_data_rozpoczecia_w_PRZYSZLOSCI_nie_wysypuje_rezerwy():
    """Wada znaleziona w Z59 strazniikiem EKRANU, nie testem jednostkowym.

    „Zaczynam 1 wrzesnia" to prawdziwy stan uzytkownika, a nie pomylka.
    `miesiace_dzialalnosci` zostaje surowe (odwrocone daty to blad — kryterium
    odbioru Z54), ale rezerwa ma to obsluzyc jako ZERO MIESIECY z nazwanym
    zastrzezeniem. Do naprawy wyjatek wysypywal caly kafelek Pulpitu.

    Wada przezyla przebiegi mutacyjne Z54 i Z55, bo zaden test nie wpisywal
    daty przyszlej — mutacja sprawdza kod, ktory jest, nie stan, ktorego
    nikt nie wywolal.
    """
    r = podatki.rezerwa_na_podatki(
        _faktury(("2026-09-10", "11200.00", "2576.00", "2425.11", "8007.89")),
        pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=date(2026, 12, 1), dzis=date(2026, 9, 30),
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))

    assert r.miesiace_zus == 0
    assert r.zus == Decimal("0.00")
    assert r.zastrzezenia, "zero miesiecy ma byc NAZWANE, nie przemilczane"
    assert "przyszło" in " ".join(r.zastrzezenia)
    assert r.naliczone_razem > 0, "VAT i podatek dochodowy maja sie policzyc"


def test_odwrocone_daty_W_FUNKCJI_dalej_sa_bledem():
    """Kontrola dwustronna: naprawa wyzej nie ma prawa zluzowac funkcji.
    Kryterium odbioru Z54 zostaje w mocy."""
    import pytest as _pytest
    from silnik.rdzen import magazyn as _magazyn
    with _pytest.raises(_magazyn.BladMagazynu):
        podatki.miesiace_dzialalnosci(date(2026, 12, 1), date(2026, 9, 1))

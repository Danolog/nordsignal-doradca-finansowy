# -*- coding: utf-8 -*-
"""Dwie luki kontraktu domkniete w Z7b — obie z rodziny „zero zamiast nie wiem".

Wspolny tryb awarii: **aplikacja podaje NAJLEPSZA MOZLIWA ODPOWIEDZ wtedy, gdy
nie wie nic**. To ta sama klasa wady co forma opodatkowania zgadnieta wartoscia
domyslna — i dlatego obie luki weszly do v1, a nie do dlugu.

LUKA 1 — `DanePlynnosci.liczbaPozycjiCoMnieCzeka` bylo golym `int`.
Przy odmowie prognozy `CoMnieCzeka.pozycje` ma wartosc domyslna `()`, wiec
`len(...)` dawalo **0**, a ekran mowil „Co mnie czeka — 0 pozycji". Zero czyta
sie jako *„policzylem i nic Cie nie czeka"*, a znaczylo *„nie policzylem"*.

LUKA 2 — `DaneKsiegowania` nie mialo `ostatnieSprawdzenie`.
Stopka odpowiada na pytanie „czy to, co widze, jest aktualne". Plynnosc
odpowiadala, Ksiegowanie mowilo „nie wiem" — o fakcie, ktory aplikacja ZNALA.
Dwa ekrany, dwie odpowiedzi na jedno pytanie.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from silnik import ekran_ksiegowanie, ekran_plynnosc, kontrakt
from silnik.rdzen import co_mnie_czeka, magazyn, prezentacja
from silnik.rdzen import prognoza_plynnosci as pp
from api import kwoty

DZIS = date(2026, 10, 6)


@pytest.fixture
def baza(tmp_path):
    p = magazyn.polacz(tmp_path / "t.db")
    yield p
    p.close()


def _ekran_plynnosci(*, czeka, prognoza=None, kotwica=None):
    """Sklada `DanePlynnosci` z podanego stanu — bez bazy.

    Wprost przez `zbuduj`, a nie przez `zbierz`, SWIADOMIE: przedmiotem
    testu jest REGULA ODWZOROWANIA `CoMnieCzeka` -> kontrakt, a nie to,
    czy baza da sie odczytac. Test przez baze mierzylby oba naraz i przy
    czerwieni nie mowilby, co pekло.
    """
    return ekran_plynnosc.zbuduj(
        prognoza=prognoza or pp.Prognoza(stan=pp.STAN_NIE_WIEM, dni=None),
        kotwica=kotwica, czeka=czeka, przebieg=None, dzis=DZIS,
        okno_dni=45, napis_kwoty=kwoty.kwota)


# --- LUKA 1: „nie policzylem" kontra „policzylem i nie ma" ---------------

def test_przy_ODMOWIE_prognozy_liczba_pozycji_to_NIE_WIEM_a_nie_zero():
    dane = _ekran_plynnosci(czeka=co_mnie_czeka.CoMnieCzeka(
        stan=pp.STAN_NIE_WIEM))
    assert dane.liczbaPozycjiCoMnieCzeka is None, (
        f"przy odmowie prognozy wyszlo {dane.liczbaPozycjiCoMnieCzeka!r} — "
        f"zero czyta sie jako: policzylem i nic nie czeka")


def test_przy_POLICZONEJ_prognozie_i_pustej_liscie_to_ZERO_a_nie_nie_wiem():
    """KONTROLA DWUSTRONNA — bez niej wystarczyloby zwracac `None` zawsze
    i test wyzej przechodzilby z zupelnie zlego powodu. „Policzylem i nic
    Cie nie czeka" jest odpowiedzia PRAWDZIWA i ma dojechac do ekranu."""
    dane = _ekran_plynnosci(czeka=co_mnie_czeka.CoMnieCzeka(
        stan=pp.STAN_POLICZONA, pozycje=(), pilnych=0))
    assert dane.liczbaPozycjiCoMnieCzeka == 0, (
        f"policzona prognoza z pusta lista dala "
        f"{dane.liczbaPozycjiCoMnieCzeka!r} zamiast 0")


def test_przy_POLICZONEJ_prognozie_liczba_zgadza_sie_z_dlugoscia_listy():
    """Kontrola licznosci: bez niej `0` z testu wyzej i „liczba zawsze zero"
    sa nieodroznialne."""
    pozycje = tuple(
        co_mnie_czeka.Pozycja(
            data=date(2026, 10, 10 + i), nazwa=f"P{i}",
            rodzaj=pp.RODZAJ_PLAN, kwota=Decimal("-100.00"),
            saldo_po=Decimal("1000.00"), dni_do=4 + i, pilna=False)
        for i in range(3))
    dane = _ekran_plynnosci(czeka=co_mnie_czeka.CoMnieCzeka(
        stan=pp.STAN_POLICZONA, pozycje=pozycje, pilnych=0))
    assert dane.liczbaPozycjiCoMnieCzeka == 3


def test_kontrakt_DOPUSZCZA_brak_wiedzy_po_obu_stronach():
    """Typ ma nie klamac: gdyby pole zostalo `int`, `None` bylo by wartoscia
    poza kontraktem i nastepny wykonawca zbudowalby na gwarancji, ktorej
    nie ma."""
    import dataclasses
    pole = next(p for p in dataclasses.fields(kontrakt.DanePlynnosci)
                if p.name == "liczbaPozycjiCoMnieCzeka")
    assert "None" in str(pole.type), str(pole.type)


# --- LUKA 2: jeden fakt, jedna odpowiedz na obu ekranach -----------------

def test_ksiegowanie_NIE_ZNA_straznika_gdy_ten_nigdy_nie_dzialal(baza):
    """`None` = nigdy nie dzialal. Zamiana na zdanie o sprawdzeniu bylaby
    zdaniem o czyms, czego nie bylo (regula D11)."""
    dane = ekran_ksiegowanie.zbierz(baza, dzis=DZIS, napis_kwoty=kwoty.kwota)
    assert dane.ostatnieSprawdzenie is None


def test_OBA_ekrany_mowia_o_strazniku_DOKLADNIE_to_samo(baza):
    """Sedno luki 2. Nie „podobnie" — DOKLADNIE to samo, bo zdanie sklada
    jeden nosnik (`prezentacja.podpis_straznika`), a nie kazdy ekran u siebie."""
    magazyn.zapisz_przebieg_straznika(
        baza, kiedy=datetime(2026, 10, 6, 6, 0), stan_prognozy=pp.STAN_POLICZONA,
        pierwszy_dzien_ujemny=None, pilnych=0, powod=None, zrodla="test",
        komunikat="nic pilnego", powiadomiono=False)

    ksiegowanie = ekran_ksiegowanie.zbierz(
        baza, dzis=DZIS, napis_kwoty=kwoty.kwota)
    przebieg = magazyn.ostatni_przebieg_straznika(baza)
    assert przebieg is not None, "kontrola licznosci: przebieg sie nie zapisal"
    z_nosnika = prezentacja.podpis_straznika(przebieg, DZIS)

    assert ksiegowanie.ostatnieSprawdzenie == z_nosnika
    assert ksiegowanie.ostatnieSprawdzenie, "zdanie jest puste"

    plynnosc = _ekran_plynnosci(czeka=co_mnie_czeka.CoMnieCzeka(
        stan=pp.STAN_NIE_WIEM))
    plynnosc_z_przebiegiem = ekran_plynnosc.zbuduj(
        prognoza=pp.Prognoza(stan=pp.STAN_NIE_WIEM, dni=None), kotwica=None,
        czeka=co_mnie_czeka.CoMnieCzeka(stan=pp.STAN_NIE_WIEM),
        przebieg=przebieg, dzis=DZIS, okno_dni=45, napis_kwoty=kwoty.kwota)
    assert plynnosc_z_przebiegiem.ostatnieSprawdzenie == \
        ksiegowanie.ostatnieSprawdzenie, \
        "dwa ekrany mowia co innego o jednym fakcie — luka wrocila"
    assert plynnosc.ostatnieSprawdzenie is None, \
        "kontrola dwustronna: bez przebiegu Plynnosc tez ma milczec"


# --- higiena: typ przestal klamac ---------------------------------------

@pytest.mark.parametrize("ksztalt,pole", [
    ("PozycjaKsiegi", "dopisek"),
    ("WierszSkutku", "wyjasnienie"),
])
def test_pola_opcjonalne_przychodza_jako_null_a_nie_znikaja(ksztalt, pole):
    """W `kontrakt.ts` staly jako `x?: T`, czyli „klucza moze nie byc".
    Python wysyla je ZAWSZE, z wartoscia `null`. Typ obiecywal cos, czego
    kontrakt nie robi — a nastepny wykonawca buduje na obietnicy."""
    import dataclasses
    klasa = getattr(kontrakt, ksztalt)
    assert pole in {p.name for p in dataclasses.fields(klasa)}
    wzorzec = (__import__("pathlib").Path(__file__).resolve().parent.parent
               / "interfejs" / "lib" / "kontrakt.ts").read_text(encoding="utf-8")
    assert f"{pole}?:" not in wzorzec, (
        f"`{pole}?` wrocilo do wzorca — typ znowu obiecuje, ze klucza moze "
        f"nie byc, a Python wysyla go zawsze")
    assert f"{pole}: string | null" in wzorzec

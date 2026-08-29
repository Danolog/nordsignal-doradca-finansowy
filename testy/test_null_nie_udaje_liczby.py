# -*- coding: utf-8 -*-
"""Straznik W3-3: „nie wiem" nie moze wygladac jak liczba — przy KAZDYM sterowniku.

CO PILNUJE. `magazyn.wczytaj_zobowiazania` normalizuje `NaN` na `None`.
Powod zapisany w kodzie: `bool(float('nan'))` to **True**, a `bool(Decimal(0))`
to **False**, wiec naiwne `if wiersz["oprocentowanie"]:` dziala DOKLADNIE
ODWROTNIE, niz brzmi — „nie wiem" uznaje za wartosc, a realne 0% Aliora
za brak danych.

DLACZEGO TEN PLIK ISTNIEJE OBOK `test_oprocentowanie.py`. Tamten straznik
(`test_NaN_nie_udaje_wartosci_w_warunku`) opisuje JEDEN DZISIEJSZY PRZYPADEK:
dwa wiersze, jeden z zerem, jeden bez wartosci, kolumna `TEXT` w SQLite.
Ten opisuje ZACHOWANIE — kontrakt, ktory ma zostac prawdziwy takze wtedy,
gdy sterownik zacznie oddawac co innego.

Ma to znaczenie, bo ksztalt odczytu ZALEZY OD ZAWARTOSCI. Pomiar 2026-08-29
(pandas 3.0.5) na tej samej kolumnie:

    same NULL-e, kolumna TEXT   -> dtype object,  wartosci None
    NULL obok '0', kolumna TEXT -> dtype str,     wartosci '0' i NaN
    NULL obok 0, kolumna NUMERIC-> dtype float64, wartosci 0.0 i NaN

Pierwszy przypadek dzisiejszego straznika NIE OBEJMUJE, a trzeci to stan PO
migracji na PostgreSQL — `pd.read_sql` ma `coerce_float=True` w wartosci
domyslnej, wiec `Decimal` z psycopg wroci jako liczba zmiennoprzecinkowa,
a `NULL` jako `NaN`. Normalizacja zostaje wiec potrzebna **z innego powodu
niz dzis**: dzis broni przed napisem obok `NaN`, po migracji przed kolumna
w calosci zmiennoprzecinkowa.

STAN PO MIGRACJI JEST TU WYTWORZONY, NIE ZALOZONY —
`test_odczyt_z_kolumny_NUMERYCZNEJ_tez_nie_przepuszcza_NaN` podstawia
sterownik oddajacy taka wlasnie ramke i przepuszcza ja przez prawdziwa
`wczytaj_zobowiazania`.
"""
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import magazyn


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz(tmp_path / "test.db")
    yield polaczenie
    polaczenie.close()


def _zobowiazanie(polaczenie, nazwa, oprocentowanie):
    magazyn.zapisz_zobowiazanie(polaczenie, nazwa=nazwa,
                                kapital=Decimal("1000.00"),
                                rata_minimalna=Decimal("100.00"),
                                oprocentowanie=oprocentowanie)


def _wymagaj_kontraktu(ramka) -> int:
    """Kontrakt kolumny `oprocentowanie`, niezaleznie od sterownika.

    Zwraca liczbe obejrzanych wierszy — sprawdzenie, do ktorego nic nie
    dociera, melduje sukces.
    """
    assert "oprocentowanie" in ramka.columns
    obejrzane = 0
    for wartosc in ramka["oprocentowanie"]:
        assert not (isinstance(wartosc, float) and wartosc != wartosc), (
            f"NaN przeciekl do odczytu jako {wartosc!r} — w warunku `if` jest "
            f"PRAWDZIWY, wiec brak danych udaje wartosc")
        if wartosc is None:
            pass  # „nie wiem" — jedyny dozwolony ksztalt braku danych
        else:
            assert magazyn.oprocentowanie_z_wiersza(wartosc) is not None, (
                f"wartosc {wartosc!r} nie jest ani None, ani liczba")
        obejrzane += 1
    return obejrzane


# --- 1. trzy sklady zawartosci, trzy rozne ksztalty odczytu ---------------

SKLADY = {
    "same_nieznane": [None, None, None],
    "mieszany": [Decimal("0"), None, Decimal("9")],
    "same_znane": [Decimal("0"), Decimal("9"), Decimal("12.5")],
}


@pytest.mark.parametrize("sklad", sorted(SKLADY))
def test_kontrakt_trzyma_sie_przy_KAZDYM_skladzie_kolumny(p, sklad):
    """Ksztalt ramki zalezy od zawartosci, wiec straznik musi objac wszystkie
    trzy sklady. Sam sklad mieszany — jedyny objety dotychczas — zostawia
    dwie trzecie zachowania bez straznika."""
    wartosci = SKLADY[sklad]
    for numer, wartosc in enumerate(wartosci):
        _zobowiazanie(p, f"{sklad}-{numer}", wartosc)
    ramka = magazyn.wczytaj_zobowiazania(p)
    assert len(ramka) == len(wartosci), "kontrola licznosci"
    assert _wymagaj_kontraktu(ramka) == len(wartosci)
    # ROZROZNIENIE, nie sama nieobecnosc NaN: zero to wartosc, brak to brak.
    odczytane = [magazyn.oprocentowanie_z_wiersza(w)
                 for w in ramka["oprocentowanie"]]
    assert odczytane == [None if w is None else Decimal(str(w))
                         for w in wartosci], (
        f"sklad {sklad}: odczytano {odczytane}, zapisano {wartosci}")


def test_zero_i_brak_NIE_ROZNIA_sie_prawdziwoscia(p):
    """Sedno wady. Gdyby rozroznienie opieralo sie na `if wartosc:`, oba
    stany bylyby nie do odroznienia — a ich pomylenie odwraca znaczenie."""
    _zobowiazanie(p, "Alior 0%", Decimal("0"))
    _zobowiazanie(p, "nieznane", None)
    zero, brak = [w["oprocentowanie"] for _, w in
                  magazyn.wczytaj_zobowiazania(p).iterrows()]
    assert magazyn.oprocentowanie_z_wiersza(zero) == Decimal("0")
    assert magazyn.oprocentowanie_z_wiersza(brak) is None
    assert not bool(Decimal("0")), (
        "zalozenie: realna wartosc 0% jest w warunku FALSZYWA — dlatego "
        "prawdziwosc nie moze byc kryterium")


# --- 2. czy niebezpieczenstwo jest realne, czy tylko opisane --------------

def test_BEZ_normalizacji_NaN_faktycznie_WRACA(p):
    """Pomiar, nie przypuszczenie: surowy odczyt tej samej tabeli oddaje NaN.

    Bez tego testu straznik wyzej moglby byc zielony dlatego, ze `NaN` nigdy
    nie powstaje — czyli pilnowac niczego.
    """
    _zobowiazanie(p, "Alior 0%", Decimal("0"))
    _zobowiazanie(p, "nieznane", None)
    surowa = pd.read_sql("SELECT * FROM zobowiazania ORDER BY id", p)
    braki = [w for w in surowa["oprocentowanie"]
             if isinstance(w, float) and w != w]
    assert len(braki) == 1, (
        f"surowy odczyt mial oddac dokladnie jeden NaN, oddal "
        f"{[repr(w) for w in surowa['oprocentowanie']]}")
    assert bool(braki[0]) is True, (
        "i ten NaN jest w warunku PRAWDZIWY — na tym polega pulapka")


# --- 3. stan PO MIGRACJI, wytworzony podstawionym sterownikiem ------------

def test_odczyt_z_kolumny_NUMERYCZNEJ_tez_nie_przepuszcza_NaN(p, monkeypatch):
    """Kolumna `oprocentowanie NUMERIC(6,3)` (`schemat.sql:179`) plus
    `coerce_float=True` da ramke W CALOSCI zmiennoprzecinkowa. Podstawiamy
    dokladnie taka ramke pod prawdziwa `wczytaj_zobowiazania`.

    Tu wlasnie widac, ze normalizacja zostaje potrzebna po migracji — i to
    z innego powodu niz dzis.
    """
    po_migracji = pd.DataFrame({
        "id": [1, 2, 3],
        "nazwa": ["Alior", "nieznane", "Revolut"],
        "kapital": [Decimal("7034.72"), Decimal("100.00"), Decimal("51234.00")],
        "rata_minimalna": [Decimal("319.76"), Decimal("10.00"), Decimal("1305.05")],
        "oprocentowanie": pd.Series([0.0, float("nan"), 9.0], dtype="float64"),
    })
    assert pd.api.types.is_float_dtype(po_migracji["oprocentowanie"]), (
        "zalozenie testu: kolumna ma byc w calosci zmiennoprzecinkowa")

    monkeypatch.setattr(pd, "read_sql", lambda *a, **k: po_migracji.copy())
    ramka = magazyn.wczytaj_zobowiazania(p)

    assert len(ramka) == 3, "kontrola licznosci"
    assert _wymagaj_kontraktu(ramka) == 3
    odczytane = [magazyn.oprocentowanie_z_wiersza(w)
                 for w in ramka["oprocentowanie"]]
    assert odczytane == [Decimal("0"), None, Decimal("9")], odczytane
    assert odczytane[0] is not None and odczytane[1] is None, (
        "zero i brak maja pozostac rozroznialne takze po migracji")


# --- 4. ksztalty, ktore moze oddac STEROWNIK — wyliczone, nie zgadniete ---

KSZTALTY_STEROWNIKA = [
    (None, None, "psycopg na NULL"),
    (float("nan"), None, "pandas po coerce_float na NULL"),
    ("", None, "pusty napis z formularza"),
    ("   ", None, "sam odstep z formularza"),
    (Decimal("0"), Decimal("0"), "psycopg na NUMERIC 0"),
    ("0", Decimal("0"), "SQLite TEXT '0'"),
    (0.0, Decimal("0"), "pandas float64 0.0"),
    (9.0, Decimal("9"), "pandas float64 9.0"),
    ("12.5", Decimal("12.5"), "SQLite TEXT '12.5'"),
]


@pytest.mark.parametrize("wejscie,oczekiwane,skad", KSZTALTY_STEROWNIKA)
def test_oprocentowanie_z_wiersza_ROZUMIE_kazdy_ksztalt(wejscie, oczekiwane, skad):
    """Jeden nosnik odczytu — `magazyn.oprocentowanie_z_wiersza` — ma dawac
    ten sam werdykt niezaleznie od tego, ktory sterownik podal wartosc."""
    assert magazyn.oprocentowanie_z_wiersza(wejscie) == oczekiwane, skad


def test_lista_ksztaltow_OBEJMUJE_oba_werdykty():
    """Kontrola licznosci listy wyzej: gdyby zawierala same braki albo same
    wartosci, parametryzacja meldowalaby sukces, sprawdzajac jedna galaz."""
    braki = [k for k in KSZTALTY_STEROWNIKA if k[1] is None]
    liczby = [k for k in KSZTALTY_STEROWNIKA if k[1] is not None]
    assert len(braki) == 4 and len(liczby) == 5, (
        f"{len(braki)} brakow i {len(liczby)} liczb — lista przestala "
        f"obejmowac obie galezie")
    assert len(KSZTALTY_STEROWNIKA) == 9

# -*- coding: utf-8 -*-
"""STRAZNICY REJESTRU STAWEK.

Kazdy test tutaj jest przywolywany jako dowod, ze regula jest pilnowana —
wiec kazdy ma udokumentowana mutacje, ktora go czerwieni (CLAUDE.md §3.8).
Mutacje spisane w `testy/MUTACJE.md` razem z data i nazwa testu, ktory padl.
"""

import datetime as dt
from decimal import Decimal as D

import pytest

from wiedza.rejestr import BrakStawki, Stawka, obowiazujaca

WCZORAJ = dt.date(2026, 1, 1)
DZIS = dt.date(2026, 9, 1)


def _stawka(**nadpisz) -> Stawka:
    pola = dict(
        klucz="zus.podstawa_spolecznych", wartosc=D("5652.00"), jednostka="zl",
        obowiazuje_od=WCZORAJ, obowiazuje_do=None,
        zrodlo_url="https://biznes.gov.pl", data_odczytu=WCZORAJ,
        status="zatwierdzona", zatwierdzil="Darek", data_zatwierdzenia=WCZORAJ,
    )
    pola.update(nadpisz)
    return Stawka(**pola)


# --- granica miedzy propozycja a wartoscia obowiazujaca --------------------

def test_propozycja_automatu_NIE_dociera_do_silnika():
    """Najwazniejszy straznik tego modulu.

    Gdyby wiersz `proponowana` wchodzil do rachunku, czujka aktow prawnych
    stalaby sie droga, ktora maszyna wpisuje stawke do przelewu — dokladnie
    ten mechanizm, ktory w rownoleglej wersji aplikacji zwracal akty zmyslone.
    """
    propozycja = _stawka(wartosc=D("9999.00"), status="proponowana",
                         zatwierdzil=None, data_zatwierdzenia=None)
    with pytest.raises(BrakStawki):
        obowiazujaca([propozycja], "zus.podstawa_spolecznych", DZIS)


def test_wycofana_NIE_dociera_do_silnika():
    wycofana = _stawka(status="wycofana", zatwierdzil=None, data_zatwierdzenia=None)
    with pytest.raises(BrakStawki):
        obowiazujaca([wycofana], "zus.podstawa_spolecznych", DZIS)


def test_zatwierdzona_bez_podpisu_NIE_POWSTAJE():
    """Status ma znaczyc 'czlowiek to potwierdzil', a nie 'ktos ustawil pole'."""
    with pytest.raises(ValueError, match="podpis"):
        _stawka(zatwierdzil=None, data_zatwierdzenia=None)


def test_brak_stawki_MOWI_o_czekajacych_propozycjach():
    """Komunikat ma prowadzic do dzialania, nie tylko oznajmiac brak.

    Bez tego uzytkownik widzi 'brak stawki' i nie wie, ze wystarczy jedno
    klikniecie w Ustawieniach.
    """
    propozycja = _stawka(status="proponowana", zatwierdzil=None,
                         data_zatwierdzenia=None)
    with pytest.raises(BrakStawki, match="propozycje do zatwierdzenia"):
        obowiazujaca([propozycja], "zus.podstawa_spolecznych", DZIS)


# --- okres obowiazywania --------------------------------------------------

def test_rachunek_za_wrzesien_liczy_sie_stawka_wrzesniowa():
    """Stawka zmieniona w pazdzierniku NIE przepisuje historii.

    To jest powod, dla ktorego rejestr jest tabela z okresem, a nie stala
    w pliku: kwota za wrzesien ma zostac ta sama kwota takze w marcu.
    """
    stara = _stawka(wartosc=D("5652.00"), obowiazuje_od=dt.date(2026, 1, 1),
                    obowiazuje_do=dt.date(2026, 9, 30))
    nowa = _stawka(wartosc=D("6100.00"), obowiazuje_od=dt.date(2026, 10, 1))
    assert obowiazujaca([stara, nowa], "zus.podstawa_spolecznych",
                        dt.date(2026, 9, 15)).wartosc == D("5652.00")
    assert obowiazujaca([stara, nowa], "zus.podstawa_spolecznych",
                        dt.date(2026, 10, 15)).wartosc == D("6100.00")


def test_stawka_PO_WYGASNIECIU_nie_obowiazuje():
    """Luka wykryta mutacja M4 (2026-08-29), nie czytaniem kodu.

    Przed dopisaniem tego testu koniec okresu obowiazywania NIE MIAL ani
    jednego straznika: mutacja kasujaca warunek `obowiazuje_do` przechodzila
    przez cala suite na zielono. Test o wrzesniu jej nie lapal, bo tam
    stawke przyszla odsiewa kontrola POCZATKU okresu, nie konca.

    Skutek bez tego straznika: stawka uchylona ustawa liczylaby kwoty
    w nieskonczonosc, a rejestr wygladalby na zadbany.
    """
    wygasla = _stawka(obowiazuje_od=dt.date(2025, 1, 1),
                      obowiazuje_do=dt.date(2025, 12, 31))
    with pytest.raises(BrakStawki):
        obowiazujaca([wygasla], "zus.podstawa_spolecznych", DZIS)


def test_stawka_sprzed_okresu_obowiazywania_NIE_obowiazuje():
    przyszla = _stawka(obowiazuje_od=dt.date(2027, 1, 1))
    with pytest.raises(BrakStawki):
        obowiazujaca([przyszla], "zus.podstawa_spolecznych", DZIS)


# --- pulapka jednostek ----------------------------------------------------

def test_procent_i_ulamek_daja_TE_SAMA_stope():
    """Zamkniecie pulapki, ktora w poprzedniej aplikacji dawala blad stukrotny."""
    w_procentach = _stawka(klucz="k", wartosc=D("9"), jednostka="procent")
    w_ulamku = _stawka(klucz="k", wartosc=D("0.09"), jednostka="ulamek")
    assert w_procentach.wartosc_jako_ulamek == w_ulamku.wartosc_jako_ulamek


def test_kwota_w_zlotych_ODMAWIA_udawania_stopy():
    """Zwrocenie czegokolwiek byloby gorsze niz blad: 5652 jako stopa daje
    liczbe, ktora wyglada na wynik."""
    kwota = _stawka(jednostka="zl")
    with pytest.raises(ValueError, match="nie jest stopa"):
        _ = kwota.wartosc_jako_ulamek


# --- zasilenie poczatkowe -------------------------------------------------

def test_zasilenie_poczatkowe_NIE_MA_ani_jednej_zatwierdzonej():
    """Przeniesienie liczby z pliku do pliku nie jest jej sprawdzeniem."""
    from wiedza import stawki_poczatkowe as sp
    zatwierdzone = [s for s in sp.WSZYSTKIE if s.status == "zatwierdzona"]
    assert zatwierdzone == [], (
        f"{len(zatwierdzone)} stawek weszlo jako zatwierdzone bez podpisu Darka"
    )


def test_kazda_stawka_poczatkowa_NIESIE_zrodlo_i_date():
    from wiedza import stawki_poczatkowe as sp
    for s in sp.WSZYSTKIE:
        assert s.zrodlo_url.startswith("https://"), f"{s.klucz}: brak zrodla"
        assert s.data_odczytu is not None, f"{s.klucz}: brak daty odczytu"


def test_skladki_zaokraglane_OSOBNO_daja_1926_76():
    """Dowod arytmetyczny reguly z PRD §8.2.

    Suma skladnikow zaokraglanych osobno: 1 926,76. Suma niezaokraglonych,
    zaokraglona na koncu: 1 926,77. Grosz — ale w przelewie do urzedu.
    """
    from decimal import ROUND_HALF_UP

    from wiedza import stawki_poczatkowe as sp

    podstawa = D("5652.00")
    stopy = [s for s in sp.SPOLECZNE if s.klucz != "zus.podstawa_spolecznych"]

    osobno = sum(
        (podstawa * s.wartosc_jako_ulamek).quantize(D("0.01"), ROUND_HALF_UP)
        for s in stopy
    )
    razem = sum(podstawa * s.wartosc_jako_ulamek for s in stopy).quantize(
        D("0.01"), ROUND_HALF_UP
    )

    assert osobno == D("1926.76")
    assert razem == D("1926.77")
    assert osobno != razem, "roznica znikla — regula zaokraglania przestala mieć znaczenie"

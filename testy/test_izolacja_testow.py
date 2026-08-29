# -*- coding: utf-8 -*-
"""STRAZNIK IZOLACJI TESTOW (W5, 2026-08-29).

LUKA NAZWANA PRZEZ WYKONAWCE W4 I DOMKNIETA TUTAJ. Ze kazdy test dostaje
wlasna przestrzen nazw (`conftest.przestrzen_testowa`), bylo widac WYLACZNIE
z zieleni calej suity — nie bylo testu, ktory by sie zaczerwienil, gdyby
izolacja zniknela. Dwa testy dzielace tabele nie musza zderzyc sie od razu,
wiec awaria byla by PRZERYWANA i przypisana do zlego miejsca: czerwieni sie
test, ktory nic zlego nie zrobil, a przyczyna siedzi w tescie obok.

CO ODROZNIA „IZOLACJA ZNIKNELA" OD „KTOS INNY PISZE DO TEJ SAMEJ BAZY".
To jest sedno tego pliku, nie szczegol. Zmierzone w tej firmie: wspoldzielona
baza testowa daje FALSZYWE CZERWONE — same limity czasu, zero asercji — a taki
straznik uczy zespol ignorowac wlasne czerwone. Rozroznienie idzie po NUMERZE
PROCESU w nazwie przestrzeni (`test_<pid>_<numer>`):

  * przestrzen z NASZYM numerem procesu -> nasza sprawa, asercja twarda;
  * przestrzen z CUDZYM numerem procesu -> rownolegly przebieg innego agenta;
    liczymy ja i wypisujemy w komunikacie, ale NIGDY nie czerwienimy sie na
    niej. Cudzy przebieg nie jest wada naszego kodu.

TRZY AWARIE, KAZDA ZE SWOIM TESTEM (mutacje w `testy/MUTACJE.md`, W5):
  * numer procesu wypada z nazwy -> dwa rownolegle przebiegi wchodza sobie
    w tabele (`test_przestrzen_NIESIE_numer_TEGO_procesu`);
  * licznik przestaje rosnac -> dwa testy jednego procesu dziela tabele
    (`test_KAZDY_test_dostaje_INNA_przestrzen`);
  * sprzatanie nie kasuje przestrzeni -> baza puchnie, a nastepny test widzi
    cudze wiersze (`test_przestrzen_POPRZEDNIEGO_testu_ZNIKNELA`).

KONTROLA LICZNOSCI PRZY KAZDEJ ASERCJI. Straznik, do ktorego nic nie dociera,
melduje sukces: zapytanie o przestrzenie, ktore nie zwrocilo nawet NASZEJ
wlasnej, jest slepe — i wtedy „nie ma pozostalosci" nie znaczy nic.
"""
from __future__ import annotations

import os
import re

import pytest

from testy import pomocnicze

#: `test_<pid>_<numer>` — jedyny nosnik ksztaltu nazwy jest w `conftest.py`;
#: tutaj stoi jego rozbiorka, nie druga definicja.
KSZTALT = re.compile(r"^test_(\d+)_(\d+)$")

#: Nazwy przestrzeni widziane przez kolejne testy TEGO pliku. Kolejnosc
#: w pliku jest kolejnoscia uruchomienia, wiec lista rosnie w czasie.
_WIDZIANE: list[str] = []

#: Slad zostawiony przez pierwszy test i szukany przez drugi.
TABELA_SLADU = "slad_izolacji"
_SLAD_ZOSTAWIONY = {"tak": False}


def _moja_przestrzen(polaczenie) -> str:
    return polaczenie.execute("SELECT current_schema()").fetchone()[0]


def _przestrzenie_testowe(polaczenie) -> tuple[list[str], list[str]]:
    """Wszystkie przestrzenie o ksztalcie testowym, rozdzielone na nasze
    i cudze. Rozdzial idzie po numerze procesu — patrz naglowek."""
    nasze, cudze = [], []
    moj = str(os.getpid())
    for (nazwa,) in polaczenie.execute(
            "SELECT schema_name FROM information_schema.schemata"
            " WHERE schema_name LIKE 'test\\_%'").fetchall():
        dopasowanie = KSZTALT.match(nazwa)
        if not dopasowanie:
            continue
        (nasze if dopasowanie.group(1) == moj else cudze).append(nazwa)
    return nasze, cudze


@pytest.fixture
def surowe():
    polaczenie = pomocnicze.polaczenie_surowe()
    try:
        yield polaczenie
    finally:
        polaczenie.close()


def test_przestrzen_NIESIE_numer_TEGO_procesu(surowe):
    """Bez numeru procesu dwa rownolegle przebiegi — takze dwoch roznych
    agentow — zakladaja przestrzen o tej samej nazwie i kasuja sobie tabele
    w trakcie cudzego testu. To jest ta awaria, ktora daje same limity czasu."""
    nazwa = _moja_przestrzen(surowe)
    _WIDZIANE.append(nazwa)
    dopasowanie = KSZTALT.match(nazwa)
    assert dopasowanie is not None, (
        f"test pracuje w przestrzeni {nazwa!r}, ktora nie ma ksztaltu "
        f"`test_<pid>_<numer>` — izolacja per test nie dziala albo dziala "
        f"inaczej, niz mowi `conftest.przestrzen_testowa`")
    assert dopasowanie.group(1) == str(os.getpid()), (
        f"przestrzen {nazwa!r} niesie numer procesu {dopasowanie.group(1)}, "
        f"a ten proces ma {os.getpid()}. Bez wlasnego numeru dwa rownolegle "
        f"przebiegi wchodza sobie w tabele.")
    assert nazwa != "public", "test pracuje w przestrzeni domyslnej bazy"


def test_KAZDY_test_dostaje_INNA_przestrzen(surowe):
    """Licznik, ktory przestal rosnac, daje dwa testy w jednej przestrzeni."""
    nazwa = _moja_przestrzen(surowe)
    assert _WIDZIANE, (
        "ten test nie widzial zadnej nazwy z testu poprzedniego — kontrola "
        "licznosci: bez niej porownanie z pusta lista jest zielone zawsze")
    assert nazwa not in _WIDZIANE, (
        f"ten test pracuje w przestrzeni {nazwa!r}, w ktorej pracowal juz "
        f"test wczesniejszy ({_WIDZIANE}). Testy dziela tabele.")
    _WIDZIANE.append(nazwa)


def test_moja_przestrzen_startuje_PUSTA(surowe):
    """Wiersz zostawiony przez test obok jest gorszy niz brak testu:
    czerwieni sie wtedy ten, ktory nic zlego nie zrobil."""
    assert pomocnicze.tabele_w_bazie(surowe) == set(), (
        f"przestrzen tego testu ma tabele, zanim test cokolwiek zrobil: "
        f"{sorted(pomocnicze.tabele_w_bazie(surowe))}")


def test_ZOSTAWIAM_slad_dla_testu_ponizej(surowe):
    """Polowa pary. Sam nic nie pilnuje — jego wartosc jest w tescie nizej."""
    surowe.execute(f"CREATE TABLE {TABELA_SLADU} (co TEXT)")
    surowe.execute(f"INSERT INTO {TABELA_SLADU} VALUES ('nie ma prawa "
                   f"przezyc granicy testu')")
    surowe.commit()
    assert TABELA_SLADU in pomocnicze.tabele_w_bazie(surowe), (
        "slad nie powstal — test ponizej mierzylby wtedy nieobecnosc czegos, "
        "czego nigdy nie bylo")
    _SLAD_ZOSTAWIONY["tak"] = True


def test_SLAD_z_testu_powyzej_NIE_PRZESZEDL_granicy(surowe):
    """Druga polowa pary — i jedyne miejsce, ktore mierzy przeciek WPROST."""
    assert _SLAD_ZOSTAWIONY["tak"], (
        "test zostawiajacy slad nie wykonal sie — ten straznik mierzy wtedy "
        "pustke i melduje sukces (kontrola licznosci)")
    assert TABELA_SLADU not in pomocnicze.tabele_w_bazie(surowe), (
        f"tabela {TABELA_SLADU!r} zalozona przez test POWYZEJ jest widoczna "
        f"w tym tescie — izolacja per test nie dziala")


def test_przestrzen_POPRZEDNIEGO_testu_ZNIKNELA(surowe):
    """Sprzatanie, ktore nie kasuje, zostawia baze pelna cudzych tabel —
    i predzej czy pozniej nazwa sie powtorzy."""
    nasze, cudze = _przestrzenie_testowe(surowe)
    moja = _moja_przestrzen(surowe)
    assert moja in nasze, (
        f"zapytanie o przestrzenie nie widzi nawet WLASNEJ ({moja}) — "
        f"przyrzad jest slepy, a „nie ma pozostalosci\" nie znaczy nic")
    pozostalosci = sorted(set(nasze) & set(_WIDZIANE))
    assert pozostalosci == [], (
        f"przestrzenie testow, ktore juz sie skonczyly, nadal stoja w bazie: "
        f"{pozostalosci}. Sprzatanie `conftest.przestrzen_testowa` nie kasuje. "
        f"(Rownolegle przebiegi innych procesow: {len(cudze)} — te nie sa "
        f"przedmiotem tej asercji.)")


def test_CUDZE_przestrzenie_NIE_czerwienia_tego_pliku(surowe):
    """Rozroznienie awarii od halasu, postawione wprost jako asercja.

    Wspoldzielona baza testowa produkuje falszywe czerwone. Ten test mowi,
    ze zaden straznik w tym pliku nie patrzy na cudze przestrzenie: nasze
    rozpoznajemy po numerze procesu, cudze wylacznie liczymy.
    """
    nasze, cudze = _przestrzenie_testowe(surowe)
    moj = str(os.getpid())
    assert all(KSZTALT.match(n).group(1) == moj for n in nasze), (
        "do zbioru „nasze\" trafila przestrzen z cudzym numerem procesu — "
        "rozroznienie nie dziala i straznik zaczal mierzyc cudza prace")
    assert all(KSZTALT.match(n).group(1) != moj for n in cudze), (
        "do zbioru „cudze\" trafila NASZA przestrzen — straznik przestal by "
        "wtedy widziec wlasny przeciek")
    assert len(nasze) >= 1, (
        "kontrola licznosci: rozdzial na nasze i cudze nie widzi ani jednej "
        "naszej przestrzeni, wiec nie zostal wykonany na niczym")

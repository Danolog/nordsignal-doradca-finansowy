# -*- coding: utf-8 -*-
"""Sciezka importu, izolacja bazy testowej i trzy oslony globalne suity.

DLACZEGO OSLONY STOJA TU, A NIE W SILNIKU. `silnik/rdzen/` nie ma wiedziec,
czy dziala pod pytestem. Magazyn wystawia PUSTA liste `STRAZNICY_ADRESU`
i to `conftest.py` zaklada w niej straznika — produkcja nie zaklada zadnego.

IZOLACJA: PRZESTRZEN NAZW NA TEST, NIE PLIK NA TEST (W4, 2026-08-29).
Do podmiany sterownika kazdy test dostawal wlasny plik SQLite w katalogu
tymczasowym — izolacja byla darmowa i pelna. PostgreSQL pliku nie ma, wiec
izolacja musi byc zbudowana. Kazdy test dostaje WLASNA PRZESTRZEN NAZW
(`test_<pid>_<numer>`) w bazie testowej; przestrzen jest kasowana po tescie.
Nazwa niesie numer procesu, wiec dwa rownolegle przebiegi — takze dwoch
roznych agentow — nie wchodza sobie w tabele. Zmierzone w tej firmie:
wspoldzielona baza testowa produkuje FALSZYWE CZERWONE (same limity czasu,
zero asercji), a to jest gorsze niz brak testu.

SUITA BEZ BAZY MA SIE CZERWIENIC, NIE POMIJAC. To jest bramka, nie szczegol:
zmierzone w tej firmie, ze suita konczaca sie kodem 0 z „N skipped" wyglada
jak sukces i przezyly pod nia TRZY strazniki-atrapy. Dlatego brak bazy jest
tu bledem zbierania testow (`pytest.UsageError`) — suita nie startuje i mowi,
czego brakuje, zamiast pokazac zielen o niczym.

TRZY OSLONY, KAZDA ZAMYKA ZMIERZONA AWARIE:

1. STRAZNIK ADRESU BAZY. Warunek pracy bez udzialu Darka brzmi: agenty
   pracuja na kopii, produkcyjna baze otwiera wylacznie gotowa aplikacja.
   Do W4 straznik porownywal SCIEZKE PLIKU sprowadzona przez `Path.resolve()`
   z dwiema znanymi sciezkami. Adres polaczenia takiej postaci kanonicznej
   nie ma, wiec straznik dziala inaczej i jest przy tym SZERSZY: odmawia
   KAZDEGO adresu, ktory nie prowadzi na te maszyne, i kazdej nazwy bazy
   spoza bazy testowej. Nazwana granica: rozpoznanie idzie po nazwie serwera
   (`magazyn.czy_lokalny`), wiec tunel wystawiony pod inna nazwa na maszynie
   lokalnej przeszedlby jako lokalny.

2. BRAK WYJSCIA DO SIECI. `weryfikacja.sprawdz()` odpytuje piec stron
   rzadowych z limitem 20 s kazda. Wyjatek dziedziczy z `BaseException`
   SWIADOMIE: `sprawdz` lapie `except Exception` i zamienilaby proba wyjscia
   w grzeczny raport NIEDOSTEPNE — test wyszedlby poza oslone i zameldowal
   sukces.

3. PODRECZNY ZAPIS W KATALOGU TYMCZASOWYM. Prawdziwy `~/.cache/ai-cfo/
   weryfikacja.json` ma waznosc 24 godzin, wiec ta sama asercja przechodzi
   przed polnoca i czerwieni sie po niej. Bez tej oslony straznik jest
   ZEGAREM, nie straznikiem.
"""

import os
import pathlib
import sys

import pytest

KORZEN = pathlib.Path(__file__).resolve().parent.parent
if str(KORZEN) not in sys.path:
    sys.path.insert(0, str(KORZEN))
# Strazniki ekranow wolaja wspolne `testy/pomocnicze.py`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import psycopg  # noqa: E402
from psycopg import conninfo as psycopg_conninfo  # noqa: E402

from silnik.rdzen import magazyn  # noqa: E402

#: Zmienna wskazujaca baze, w ktorej wolno zakladac przestrzenie testowe.
#: OSOBNA od `DATABASE_URL` swiadomie: gdyby suita brala adres produkcyjny
#: znaleziony w srodowisku, wystarczylby jeden `export` w cudzej powloce,
#: zeby testy zaczely zakladac i kasowac przestrzenie w bazie Darka.
ZMIENNA_BAZY_TESTOWEJ = "DATABASE_URL_TESTY"

#: Nazwy baz, ktorych suita NIE otworzy nawet na maszynie lokalnej.
#: `doradca` to baza robocza aplikacji — ta, ktora Darek oglada na ekranie.
BAZY_ZABRONIONE = ("doradca", "cfo", "postgres")


def _adres_bazy_testowej() -> str:
    surowy = os.environ.get(ZMIENNA_BAZY_TESTOWEJ, "").strip()
    if not surowy:
        raise pytest.UsageError(
            f"Suita nie ma bazy PostgreSQL. Ustaw {ZMIENNA_BAZY_TESTOWEJ} na "
            f"adres bazy WYLACZNIE testowej, na przyklad\n"
            f"  export {ZMIENNA_BAZY_TESTOWEJ}="
            f"'postgresql://postgres:HASLO@localhost:5434/doradca_test'\n"
            f"Suita CELOWO nie pomija testow bez bazy: przebieg konczacy sie "
            f"kodem 0 z „N skipped\" wyglada jak sukces, a nie jest nim.")
    czesci = psycopg_conninfo.conninfo_to_dict(surowy)
    if not magazyn.czy_lokalny(czesci.get("host")):
        raise pytest.UsageError(
            f"{ZMIENNA_BAZY_TESTOWEJ} wskazuje serwer {czesci.get('host')!r}, "
            f"czyli NIE te maszyne. Testy zakladaja i kasuja przestrzenie nazw "
            f"— na bazie produkcyjnej byloby to kasowanie danych Darka.")
    if str(czesci.get("dbname", "")).lower() in BAZY_ZABRONIONE:
        raise pytest.UsageError(
            f"{ZMIENNA_BAZY_TESTOWEJ} wskazuje baze {czesci.get('dbname')!r}, "
            f"a to baza robocza aplikacji. Zaloz osobna baze testowa.")
    return surowy


ADRES_TESTOWY = _adres_bazy_testowej()

#: Licznik przestrzeni w tym procesie. Razem z numerem procesu daje nazwe,
#: ktorej nie wytworzy zaden rownolegly przebieg.
_LICZNIK = {"n": 0}


def _nigdy_baza_nietestowa(adres: str) -> None:
    """Straznik zakladany w `magazyn.STRAZNICY_ADRESU` — NASTEPCA straznika sciezki.

    CO PILNUJE: ze zaden test nie otworzy bazy spoza bazy testowej. Rozpoznanie
    idzie po `host` i `dbname` rozlozonych PARSEREM STEROWNIKA, a nie po
    porownaniu napisow — inaczej ten sam adres zapisany z innym porzadkiem
    parametrow przeszedlby obok bramki.
    """
    czesci = magazyn._czesci_adresu(adres)
    if not magazyn.czy_lokalny(czesci.get("host")):
        raise magazyn.BladMagazynu(
            f"Test probuje otworzyc baze na serwerze {czesci.get('host')!r} — "
            f"to nie jest ta maszyna, wiec to jest baza produkcyjna albo "
            f"cudza. Wskaz baze testowa zmienna {ZMIENNA_BAZY_TESTOWEJ}.")
    if str(czesci.get("dbname", "")).lower() in BAZY_ZABRONIONE:
        raise magazyn.BladMagazynu(
            f"Test probuje otworzyc baze robocza aplikacji "
            f"({czesci.get('dbname')}). To sa realne dane Darka. Uzyj bazy "
            f"testowej wskazanej zmienna {ZMIENNA_BAZY_TESTOWEJ}.")


magazyn.STRAZNICY_ADRESU.append(_nigdy_baza_nietestowa)


def adres_przestrzeni(nazwa: str) -> str:
    """Adres bazy testowej ustawiony na WSKAZANA przestrzen nazw.

    Przestrzen jedzie w adresie, a nie w poleceniu `SET search_path`, bo
    `polacz()` otwiera NOWE polaczenie przy kazdym wywolaniu — polecenie
    wykonane na jednym polaczeniu nie dotyczylo by nastepnego.
    """
    return psycopg_conninfo.make_conninfo(
        ADRES_TESTOWY, options=f"-c search_path={nazwa}")


@pytest.fixture(autouse=True)
def przestrzen_testowa(request, monkeypatch):
    """WLASNA przestrzen nazw na kazdy test — nastepca „wlasny plik na test".

    Zaklada przestrzen, wskazuje ja przez `DATABASE_URL` i kasuje po tescie.
    Test, ktory nie tknie bazy, placi za to jednym `CREATE SCHEMA` i jednym
    `DROP SCHEMA` — zmierzone: ponizej progu widocznosci wobec calej suity.
    """
    _LICZNIK["n"] += 1
    nazwa = f"test_{os.getpid()}_{_LICZNIK['n']}"
    with psycopg.connect(ADRES_TESTOWY, autocommit=True) as p:
        p.execute(f"DROP SCHEMA IF EXISTS {nazwa} CASCADE")
        p.execute(f"CREATE SCHEMA {nazwa}")
    adres = adres_przestrzeni(nazwa)
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, adres)
    monkeypatch.delenv(magazyn.ZMIENNA_BAZY_BEZPOSREDNIEJ, raising=False)
    monkeypatch.delenv(magazyn.ZMIENNA_BAZY_BEZPOSREDNIEJ_NEON,
                       raising=False)

    # POLACZENIA OTWARTE PRZEZ TEST SA ZAMYKANE PRZY SPRZATANIU — i to nie
    # jest higiena. Zmierzone 2026-08-29: plik SQLite znikal razem z katalogiem
    # tymczasowym, wiec test, ktory zapomnial zamknac polaczenie, nie kosztowal
    # nic. W PostgreSQL takie polaczenie trzyma BLOKADE na tabelach, a
    # `DROP SCHEMA` czeka na nia BEZ KONCA — suita wieszala sie na trzecim
    # tescie zamiast dac czerwony wynik. `_otworz_surowo` jest jedynym szwem,
    # przez ktory magazyn otwiera polaczenie, wiec wystarczy sledzic ten jeden.
    otwarte: list = []
    prawdziwy = magazyn._otworz_surowo

    def sledzone(a):
        polaczenie = prawdziwy(a)
        otwarte.append(polaczenie)
        return polaczenie

    monkeypatch.setattr(magazyn, "_otworz_surowo", sledzone)
    try:
        yield adres
    finally:
        for polaczenie in otwarte:
            try:
                polaczenie.close()
            except Exception:  # pragma: no cover - sprzatanie ma nie wybuchac
                pass
        with psycopg.connect(ADRES_TESTOWY, autocommit=True) as p:
            # Limit czekania na blokade zamiast czekania w nieskonczonosc:
            # sprzatanie ma powiedziec, ze czegos nie umie, a nie zawiesic
            # caly przebieg.
            p.execute("SET lock_timeout = '10s'")
            try:
                # Razem z przestrzenia testu znikaja kopie ZROBIONE Z NIEJ —
                # inaczej baza testowa zbieralaby po jednej przestrzeni na
                # kazdy test dotykajacy migracji.
                do_skasowania = [nazwa] + [
                    w[0] for w in p.execute(
                        "SELECT schema_name FROM information_schema.schemata"
                        " WHERE schema_name LIKE %s",
                        (magazyn.PRZEDROSTEK_KOPII + nazwa + "_%",)).fetchall()]
                for schemat in do_skasowania:
                    p.execute(f"DROP SCHEMA IF EXISTS {schemat} CASCADE")
            except psycopg.errors.LockNotAvailable as e:
                raise AssertionError(
                    f"Nie da sie posprzatac przestrzeni {nazwa}: ktos trzyma "
                    f"blokade. Najczestsza przyczyna to polaczenie otwarte "
                    f"z pominieciem `magazyn._otworz_surowo` (np. gole "
                    f"`psycopg.connect`) i niezamkniete przez test. "
                    f"Szczegol: {e}") from e


@pytest.fixture
def baza(przestrzen_testowa) -> str:
    """Adres wlasnej, pustej bazy tego testu. Nazwa krotka, bo uzywana wszedzie."""
    return przestrzen_testowa


class BladWyjsciaDoSieci(BaseException):
    """Dziedziczy z `BaseException`, nie z `Exception` — patrz naglowek."""


def _bez_wyjscia_do_sieci(url: str) -> str:
    raise BladWyjsciaDoSieci(
        f"Test bez znacznika `siec` probuje wyjsc do sieci: {url}. "
        f"Podstaw `weryfikacja._pobierz` we wlasnym tescie albo oznacz go "
        f"znacznikiem `siec` (pytest -m siec).")


@pytest.fixture(autouse=True)
def bez_sieci(request, monkeypatch):
    if request.node.get_closest_marker("siec"):
        return
    from silnik.rdzen import weryfikacja

    monkeypatch.setattr(weryfikacja, "_pobierz", _bez_wyjscia_do_sieci)


@pytest.fixture(autouse=True)
def bez_podrecznego_zapisu(request, tmp_path, monkeypatch):
    sciezka = tmp_path / "weryfikacja.json"
    if request.node.get_closest_marker("siec"):
        return sciezka
    from silnik.rdzen import weryfikacja

    monkeypatch.setattr(weryfikacja, "SCIEZKA_CACHE", sciezka)
    return sciezka


# --- CZEGO NIE PRZENIESIONO Z POPRZEDNIKA — i co przez to nie jest pilnowane
#
# Pozycja obowiazkowa (CLAUDE.md §3.11). Wypisana przy przenosinach, nie po.
#
# 1. `test_ekran_playwright.py` (2 testy) — straznik BEHAWIORALNY: uruchamial
#    stara aplikacje NiceGUI na wlasnym porcie i czytal liczbe z wyrenderowanej
#    strony. Nie przenosi sie, bo uruchamia `app.py` poprzednika i stoi na
#    pliku `cfo_database.db-wzorzec-2026-08-28` spoza tego repozytorium.
#    NIEPILNOWANE: ze liczba na ekranie rowna sie wynikowi silnika dla tych
#    samych danych. To jest wlasnie ta klasa wady, ktorej straznik zrodlowy
#    NIE lapie (zmierzone u poprzednika: podmiana argumentu `rezerwa` na
#    `Decimal("0")` zawyzyla naglowek o 5 768,11 zl i przeszla 532 testy).
#    NASTEPCA W TYM PROJEKCIE: bramka odwzorowania `porownaj-z-makieta.mjs`
#    porownuje WYGLAD, nie LICZBE — luka zostaje otwarta do zadania Z7,
#    ktorego bramka brzmi „prognoza po wpisie jest inna niz przed".
#
# 2. `test_wzorzec_nastawy.py` (5 testow) — straznik TRESCI bazy-wzorca:
#    pilnowal, ze wzorzec niesie skale (nie ryczalt), date rozpoczecia
#    dzialalnosci 2026-09-01 i zadnej faktury sprzed tej daty. Nie przenosi
#    sie, bo stal na tym samym pliku wzorca spoza repozytorium i wolal stala
#    z pliku wyzej. NIEPILNOWANE: ze dane, na ktorych odbieramy ekrany, opisuja
#    sytuacje Darka. NASTEPCA: migracja danych (PRD §6.5) — jej bramka odbioru
#    ma przejac te piec asercji na wlasnych danych tego projektu.
#
# 3. Dziesiec straznikow ZRODLOWYCH starego interfejsu (`pulpit/*.py`) —
#    opisane przy miejscu, z ktorego zostaly zdjete:
#    `test_zobowiazania_majatek.py` (6), `test_zaplata_podatku.py` (3),
#    `test_faktura_do_budzetu.py` (1).
#
# Wszystkie trzy grupy ZOSTAJA zywe w `../AI CFO/testy/` do konca wygaszania.

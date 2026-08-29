# -*- coding: utf-8 -*-
"""Sciezka importu + trzy oslony globalne suity.

DLACZEGO OSLONY STOJA TU, A NIE W SILNIKU. `silnik/rdzen/` nie ma wiedziec,
czy dziala pod pytestem. Magazyn wystawia PUSTA liste `STRAZNICY_SCIEZKI`
i to `conftest.py` zaklada w niej straznika — produkcja nie zaklada zadnego.

TRZY OSLONY, KAZDA ZAMYKA ZMIERZONA AWARIE:

1. STRAZNIK SCIEZKI BAZY. Warunek pracy bez udzialu Darka brzmi: agenty
   pracuja na kopii, produkcyjna baze otwiera wylacznie gotowa aplikacja.
   Bez tego straznika byla to obietnica bez mechanizmu. Straznik obejmuje
   DWIE sciezki, nie jedna: baze domyslna tego projektu ORAZ baze produkcyjna
   poprzednika (`../AI CFO/cfo_database.db`) — ta druga lezy jeden katalog
   obok, ma realne dane Darka, a `AI_CFO_BAZA` potrafi w nia wskazac.

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

import pathlib
import sys

import pytest

KORZEN = pathlib.Path(__file__).resolve().parent.parent
if str(KORZEN) not in sys.path:
    sys.path.insert(0, str(KORZEN))
# Strazniki ekranow wolaja wspolne `testy/pomocnicze.py`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from silnik.rdzen import magazyn  # noqa: E402

#: Baza produkcyjna poprzednika — realne dane Darka, jeden katalog obok.
#: `../AI CFO` zostaje uruchamialny do konca przenosin, wiec jego plik zyje.
BAZA_POPRZEDNIKA = (KORZEN.parent / "AI CFO" / "cfo_database.db")


def _nigdy_baza_produkcyjna(sciezka: pathlib.Path) -> None:
    zabronione = [magazyn.SCIEZKA_DOMYSLNA, BAZA_POPRZEDNIKA]
    for zla in zabronione:
        try:
            if sciezka.resolve() != zla.resolve():
                continue
        except OSError:
            continue
        raise magazyn.BladMagazynu(
            f"Test probuje otworzyc baze PRODUKCYJNA ({zla}). "
            f"To sa realne dane Darka. Wskaz kopie zmienna "
            f"{magazyn.ZMIENNA_BAZY} albo podaj sciezke jawnie: "
            f"polacz(tmp_path / 'test.db').")


magazyn.STRAZNICY_SCIEZKI.append(_nigdy_baza_produkcyjna)


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

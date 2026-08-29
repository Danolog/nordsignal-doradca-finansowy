# -*- coding: utf-8 -*-
"""Strażnicy rozdziału „otwórz" od „zmigruj" (W2, 2026-08-29).

CO PILNUJE TEN PLIK — i dlaczego samo `grep` by nie wystarczyło.
Do W2 `magazyn.polacz()` stawiało cały schemat przy każdym wywołaniu, a
połączenie jest zależnością NA ŻĄDANIE HTTP (`api/wspolne.polaczenie`).
Zmierzone sondą `sqlite3.set_trace_callback` na świeżej bazie **przed**
rozdzieleniem: **98 poleceń SQL, z czego 59 piszących** (15 × `CREATE`,
44 × `INSERT`). Po rozdzieleniu: **1 polecenie, `PRAGMA user_version`, odczyt.**

`grep` na nazwie funkcji NIE wystarcza jako dowód: DDL wchodziło do `polacz()`
przez wywołania w środku (`_dopisz_kolumny`, `zasiej_kategorie`, …), więc plik
mógłby nie zawierać ani jednego słowa `CREATE` i nadal stawiać czternaście
tabel. Dlatego strażnik mierzy **to, co dotarło do sterownika**, a nie kształt
źródła.

KONTROLA LICZNOŚCI JEST TU POZYCJĄ OBOWIĄZKOWĄ. Sprawdzenie „zero poleceń
piszących" jest **prawdziwe także wtedy, gdy sonda nie widziała niczego** —
i wtedy nie strzeże niczego. Każdy pomiar poniżej mówi więc najpierw, ILE
poleceń w ogóle zobaczył.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.index import aplikacja
from silnik.rdzen import magazyn

#: Pierwsze słowo polecenia, które ZMIENIA bazę — dane albo schemat.
PISZACE = ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")

#: Ile tabel ma pełny schemat. Ta sama liczba co w `test_schemat_dwa_dialekty`
#: (`ILE_TABEL`) — tam jako porównanie dwóch napisów DDL, tu jako liczba
#: poleceń, które NAPRAWDĘ dotarły do sterownika.
ILE_TABEL = 14


def _slowo(polecenie: str) -> str:
    return polecenie.strip().split()[0].upper() if polecenie.strip() else ""


def _podsluchaj(monkeypatch, czynnosc):
    """Wykonuje `czynnosc` i zwraca (wynik, lista poleceń SQL, które padły).

    Podsłuch zakładany na `sqlite3.connect`, bo `polacz()` otwiera połączenie
    samo — nie da się podpiąć `set_trace_callback` z zewnątrz po fakcie.
    """
    zapis: list[str] = []
    prawdziwy = sqlite3.connect

    def podsluchujacy(*a, **k):
        polaczenie = prawdziwy(*a, **k)
        polaczenie.set_trace_callback(zapis.append)
        return polaczenie

    monkeypatch.setattr(sqlite3, "connect", podsluchujacy)
    wynik = czynnosc()
    monkeypatch.setattr(sqlite3, "connect", prawdziwy)
    return wynik, zapis


@pytest.fixture
def baza(tmp_path) -> pathlib.Path:
    return tmp_path / "w2.db"


# --- 1. polacz() otwiera i tylko otwiera ----------------------------------

def test_polacz_NIE_WYKONUJE_ani_jednego_polecenia_piszacego(baza, monkeypatch):
    """Sedno W2, zmierzone na sterowniku, nie odczytane ze źródła."""
    magazyn.zmigruj(baza)

    polaczenie, polecenia = _podsluchaj(
        monkeypatch, lambda: magazyn.polacz(baza))
    polaczenie.close()

    # KONTROLA LICZNOŚCI: bez niej asercja niżej jest prawdziwa także dla
    # sondy, do której nic nie dotarło. To dokładnie ta klasa strażnika-atrapy,
    # która przy zielonej suicie nie strzeże niczego (M5 z przebiegu W1).
    assert len(polecenia) == 1, \
        f"polacz() ma wykonać DOKŁADNIE jeden odczyt; wykonał {len(polecenia)}: {polecenia}"
    assert "user_version" in polecenia[0].lower(), \
        f"jedyne polecenie `polacz()` ma być odczytem wersji; było: {polecenia[0]!r}"

    piszace = [p for p in polecenia if _slowo(p) in PISZACE]
    assert piszace == [], \
        f"polacz() wykonało {len(piszace)} poleceń piszących: {piszace}"


def test_polacz_ODMAWIA_otwarcia_bazy_niezmigrowanej(baza):
    """§3.7: awaria do stanu użytecznego — mówi, czego brakuje i co zrobić.

    NASTĘPCA SAMOCZYNNEJ MIGRACJI. Bez tej odmowy proces, który zapomniał
    zawołać migrację, wstałby na bazie bez tabel — i to jest jedyny sygnał,
    jaki po W2 zostaje.
    """
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.polacz(baza)

    tresc = str(blad.value)
    assert "zmigruj" in tresc, f"odmowa ma powiedzieć, CO uruchomić: {tresc}"
    assert str(baza) in tresc, f"odmowa ma powiedzieć, KTÓRA baza: {tresc}"


def test_polacz_PRZYJMUJE_baze_zmigrowana(baza):
    """Kontrola dwustronna do testu wyżej: odmowa nie może być bezwarunkowa."""
    magazyn.zmigruj(baza)
    polaczenie = magazyn.polacz(baza)
    try:
        assert magazyn._wersja_bazy(polaczenie) == magazyn.WERSJA_SCHEMATU
    finally:
        polaczenie.close()


# --- 2. zmigruj() nadal MIGRUJE -------------------------------------------

def test_zmigruj_STAWIA_pelny_schemat_i_zasiewa(baza, monkeypatch):
    """Sedno bramki W2: rozdzielenie nie może zgubić samej migracji.

    Łatwo rozdzielić tak, że migracja przestaje działać w ogóle, a suita jest
    zielona, bo fikstura stawia schemat inaczej. Ten test liczy polecenia,
    które NAPRAWDĘ dotarły do sterownika.
    """
    raport, polecenia = _podsluchaj(
        monkeypatch, lambda: magazyn.zmigruj(baza))

    create_table = [p for p in polecenia if re.match(r"\s*CREATE TABLE", p, re.I)]
    zasiew = [p for p in polecenia if _slowo(p) == "INSERT"]

    assert len(create_table) == ILE_TABEL, \
        f"migracja ma postawić {ILE_TABEL} tabel, postawiła {len(create_table)}"
    assert len(zasiew) >= 40, \
        f"migracja ma zasiać słowniki; poleceń INSERT było {len(zasiew)}"

    assert raport.wersja_przed == 0
    assert raport.wersja_po == magazyn.WERSJA_SCHEMATU
    assert raport.tabel == ILE_TABEL
    assert raport.kategorii > 0, "zasiew kategorii nic nie wpisał"
    assert raport.stawek > 0, "zasiew rejestru stawek nic nie wpisał"


def test_zmigruj_ZOSTAWIA_baze_gotowa_do_zapisu(baza):
    """Kontrola skutku, nie samego przebiegu: po migracji da się pisać."""
    magazyn.zmigruj(baza)
    polaczenie = magazyn.polacz(baza)
    try:
        magazyn.zapisz_wpis(polaczenie, data=date(2026, 9, 10), typ="Wydatki",
                            kategoria="Zakupy", kwota=Decimal("12.34"))
        df = magazyn.wczytaj_wpisy(polaczenie)
        assert len(df) == 1
        assert df["kwota"].iloc[0] == Decimal("12.34")
        assert isinstance(df["kwota"].iloc[0], Decimal), \
            "kwota ma wracać typem dziesiętnym (§3.1)"
    finally:
        polaczenie.close()


# --- 3. wołający, który polegał na samoczynności --------------------------

def test_start_aplikacji_MIGRUJE_baze(tmp_path, monkeypatch):
    """JEDYNY produkcyjny wołający `polacz()` to zależność na żądanie.

    Po W2 migracja należy do uchwytu cyklu życia aplikacji
    (`api.index.cykl_zycia`). `TestClient` uruchamia ten uchwyt WYŁĄCZNIE
    w postaci `with` — pozostałe testy HTTP w tym repozytorium budują klienta
    gołym wywołaniem i migrują sobie same w fiksturze, więc uchwytu NIE
    dotykają. Ten test jest jedynym miejscem, które go wykonuje.
    """
    cel = tmp_path / "start.db"
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, str(cel))
    assert not cel.exists(), "test ma startować z bazy, której nie ma"

    with TestClient(aplikacja) as klient:
        odpowiedz = klient.get("/api/ksiegowanie?dzis=2026-10-05")

    assert odpowiedz.status_code == 200, \
        f"po starcie aplikacji żądanie ma przejść; było {odpowiedz.status_code}: {odpowiedz.text}"
    assert cel.exists(), "start aplikacji nie założył bazy"

    surowe = sqlite3.connect(str(cel))
    try:
        wersja = surowe.execute("PRAGMA user_version").fetchone()[0]
        tabel = surowe.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    finally:
        surowe.close()
    assert wersja == magazyn.WERSJA_SCHEMATU
    assert tabel == ILE_TABEL, f"start postawił {tabel} tabel zamiast {ILE_TABEL}"


def test_bez_startu_zadanie_ODMAWIA_zamiast_pokazac_zera(tmp_path, monkeypatch):
    """Co się stanie, gdy migracji nikt nie wywoła — pytanie z bramki W2.

    Klient budowany BEZ `with` nie uruchamia uchwytu cyklu życia. Baza zostaje
    niezmigrowana. Żądanie ma wtedy odmówić i powiedzieć, co uruchomić —
    nigdy pokazać zer.
    """
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, str(tmp_path / "bez-startu.db"))
    klient = TestClient(aplikacja)

    odpowiedz = klient.get("/api/ksiegowanie?dzis=2026-10-05")

    assert odpowiedz.status_code == 400, \
        f"żądanie na niezmigrowanej bazie ma odmówić, było {odpowiedz.status_code}"
    assert "zmigruj" in odpowiedz.json()["detail"], \
        f"odmowa ma nieść instrukcję: {odpowiedz.json()}"


def test_warstwa_sieciowa_NIE_MIGRUJE_na_zadanie():
    """`api/` nie ma prawa wołać `zmigruj_i_polacz` — to powrót wady W2.

    Strażnik ŹRÓDŁOWY, świadomie: chodzi o kształt zależności, nie o zachowanie
    jednego żądania. Zachowania pilnują dwa testy wyżej.
    """
    pliki = sorted(pathlib.Path("api").glob("*.py"))
    assert len(pliki) >= 5, \
        f"strażnik ma czytać całe `api/`; zobaczył {len(pliki)} plików"

    winne = [str(p) for p in pliki if "zmigruj_i_polacz" in p.read_text(encoding="utf-8")]
    assert winne == [], \
        f"warstwa sieciowa migruje na żądanie — pełny DDL na każde żądanie: {winne}"

    wspolne = pathlib.Path("api/wspolne.py").read_text(encoding="utf-8")
    assert "magazyn.polacz()" in wspolne, \
        "zależność na żądanie ma wołać samo otwarcie"


# --- 4. `_zdejmij_kolumny` — operacja nieodwracalna ------------------------

def test_kolumna_naraz_dopisywana_i_zdejmowana_JEST_ODMOWA(monkeypatch, baza):
    """Jedyna zmierzona droga do cichej utraty danych w tym module.

    Wpis `("zobowiazania", "oprocentowanie")` stał w obu krotkach naraz po
    odwróceniu decyzji Z43 (2026-08-28). `_dopisz_kolumny` odtwarzało kolumnę,
    `_zdejmij_kolumny` kasowało ją razem z wartością wpisaną przez Darka —
    przy każdym otwarciu bazy, po cichu i przy zielonej suicie.

    Po W2 sprzeczność jest ODMOWĄ przed pierwszym `DROP COLUMN`, nie
    komentarzem w kodzie.
    """
    monkeypatch.setattr(magazyn, "_ZDEJMOWANE_KOLUMNY",
                        (("zobowiazania", "oprocentowanie"),))

    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zmigruj(baza)

    tresc = str(blad.value)
    assert "zobowiazania.oprocentowanie" in tresc
    assert "nieodwracalne" in tresc.lower()


def test_zdejmowanie_kolumn_NIE_BIEGNIE_przy_otwarciu(baza, monkeypatch):
    """Zmiana wagi wady: z „przy każdym żądaniu HTTP" na „przy migracji".

    Sprzeczna krotka ustawiana PO migracji: gdyby `polacz()` nadal wołało
    `_zdejmij_kolumny`, odmowa padłaby tutaj.
    """
    magazyn.zmigruj(baza)
    monkeypatch.setattr(magazyn, "_ZDEJMOWANE_KOLUMNY",
                        (("zobowiazania", "oprocentowanie"),))

    polaczenie = magazyn.polacz(baza)
    try:
        kolumny = {w[1] for w in
                   polaczenie.execute("PRAGMA table_info(zobowiazania)")}
        assert "oprocentowanie" in kolumny, \
            "otwarcie bazy zdjęło kolumnę — `_zdejmij_kolumny` nadal biegnie w `polacz()`"
    finally:
        polaczenie.close()

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
from datetime import date
from decimal import Decimal

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.index import aplikacja
from silnik.rdzen import magazyn
from testy import pomocnicze

#: Pierwsze słowo polecenia, które ZMIENIA bazę — dane albo schemat.
PISZACE = ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")

#: Ile tabel ma pełny schemat. Ta sama liczba co w `test_schemat_wobec_bazy`
#: (`ILE_TABEL`) — tam jako porównanie napisu DDL z katalogiem serwera, tu
#: jako liczba poleceń, które NAPRAWDĘ dotarły do sterownika.
#: Piętnaście od W4: dochodzi `wersja_schematu`, następca `PRAGMA user_version`.
ILE_TABEL = 15


def _slowo(polecenie: str) -> str:
    return polecenie.strip().split()[0].upper() if polecenie.strip() else ""


def _podsluchaj(monkeypatch, czynnosc):
    """Wykonuje `czynnosc` i zwraca (wynik, lista poleceń SQL, które padły).

    SONDA PO W4: podmieniona metoda `execute` na kursorze psycopg. Poprzednik
    używał `sqlite3.set_trace_callback` — haka, którego psycopg NIE MA. Miejsce
    podsłuchu jest jednak lepsze niż poprzednio: kursor widzi KAŻDE polecenie,
    także te wysłane z połączenia otwartego wewnątrz `zmigruj()`, którego
    z zewnątrz nie da się dotknąć.
    """
    zapis: list[str] = []
    prawdziwy = psycopg.Cursor.execute

    def podsluchujacy(self, query, params=None, **k):
        zapis.append(query if isinstance(query, str) else query.decode())
        return prawdziwy(self, query, params, **k)

    monkeypatch.setattr(psycopg.Cursor, "execute", podsluchujacy)
    try:
        wynik = czynnosc()
    finally:
        monkeypatch.setattr(psycopg.Cursor, "execute", prawdziwy)
    return wynik, zapis


# --- 1. polacz() otwiera i tylko otwiera ----------------------------------

def test_polacz_NIE_WYKONUJE_ani_jednego_polecenia_piszacego(baza, monkeypatch):
    """Sedno W2, zmierzone na sterowniku, nie odczytane ze źródła."""
    magazyn.zmigruj()

    polaczenie, polecenia = _podsluchaj(
        monkeypatch, lambda: magazyn.polacz())
    polaczenie.close()

    # KONTROLA LICZNOŚCI: bez niej asercja niżej jest prawdziwa także dla
    # sondy, do której nic nie dotarło. To dokładnie ta klasa strażnika-atrapy,
    # która przy zielonej suicie nie strzeże niczego (M5 z przebiegu W1).
    # DWA odczyty, nie jeden — i to jest różnica policzona, nie przeoczona:
    # `PRAGMA user_version` była JEDNYM poleceniem, bo wersja siedziała
    # w nagłówku pliku. Po W4 wersja mieszka w tabeli, więc `_wersja_bazy`
    # pyta najpierw katalog systemowy („czy ta tabela w ogóle jest"), a potem
    # samą tabelę. Obie odpowiedzi są ODCZYTAMI.
    assert len(polecenia) == 2, \
        f"polacz() ma wykonać DOKŁADNIE dwa odczyty; wykonał {len(polecenia)}: {polecenia}"
    assert "information_schema.tables" in polecenia[0], \
        f"pierwsze polecenie ma pytać, czy tabela wersji istnieje: {polecenia[0]!r}"
    assert "wersja_schematu" in polecenia[1], \
        f"drugie polecenie ma odczytać wersję; było: {polecenia[1]!r}"

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
        magazyn.polacz()

    tresc = str(blad.value)
    assert "zmigruj" in tresc, f"odmowa ma powiedzieć, CO uruchomić: {tresc}"
    assert magazyn.adres_bez_hasla(baza) in tresc, \
        f"odmowa ma powiedzieć, KTÓRA baza: {tresc}"


def test_polacz_PRZYJMUJE_baze_zmigrowana(baza):
    """Kontrola dwustronna do testu wyżej: odmowa nie może być bezwarunkowa."""
    magazyn.zmigruj()
    polaczenie = magazyn.polacz()
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
        monkeypatch, lambda: magazyn.zmigruj())

    # LICZYMY WYSTĄPIENIA, NIE POLECENIA — i to jest zmiana W4, nie obejście.
    # `executescript` sterownika SQLite dzielił napis na osobne polecenia,
    # więc sonda widziała piętnaście wywołań. psycopg wysyła cały napis DDL
    # JAKO JEDNO polecenie, bo serwer sam potrafi wykonać ich ciąg. Sonda
    # widzi więc jedno wywołanie z piętnastoma `CREATE TABLE` w środku —
    # ta sama treść, inny podział. Liczba wystąpień jest tu miarą tego, co
    # DOTARŁO DO SERWERA; gdyby napis przyszedł okrojony, spadłaby.
    razem = "\n".join(polecenia)
    create_table = re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)",
                              razem, re.I)
    zasiew = [p for p in polecenia if _slowo(p) == "INSERT"]

    assert len(create_table) == ILE_TABEL, \
        (f"migracja ma postawić {ILE_TABEL} tabel, w poleceniach było ich "
         f"{len(create_table)}: {sorted(create_table)}")
    assert len(set(create_table)) == ILE_TABEL, \
        f"tabele się powtarzają: {sorted(create_table)}"
    assert len(zasiew) >= 40, \
        f"migracja ma zasiać słowniki; poleceń INSERT było {len(zasiew)}"

    assert raport.wersja_przed == 0
    assert raport.wersja_po == magazyn.WERSJA_SCHEMATU
    assert raport.tabel == ILE_TABEL
    assert raport.kategorii > 0, "zasiew kategorii nic nie wpisał"
    assert raport.stawek > 0, "zasiew rejestru stawek nic nie wpisał"


def test_zmigruj_ZOSTAWIA_baze_gotowa_do_zapisu(baza):
    """Kontrola skutku, nie samego przebiegu: po migracji da się pisać."""
    magazyn.zmigruj()
    polaczenie = magazyn.polacz()
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
    surowe = pomocnicze.polaczenie_surowe()
    try:
        assert pomocnicze.tabele_w_bazie(surowe) == set(), \
            "test ma startować z bazy, w której nie ma ani jednej tabeli"
    finally:
        surowe.close()

    with TestClient(aplikacja) as klient:
        odpowiedz = klient.get("/api/ksiegowanie?dzis=2026-10-05")

    assert odpowiedz.status_code == 200, \
        f"po starcie aplikacji żądanie ma przejść; było {odpowiedz.status_code}: {odpowiedz.text}"

    surowe = pomocnicze.polaczenie_surowe()
    try:
        wersja = surowe.execute(
            "SELECT wersja FROM wersja_schematu WHERE jedyny").fetchone()[0]
        tabele = pomocnicze.tabele_w_bazie(surowe)
    finally:
        surowe.close()
    assert wersja == magazyn.WERSJA_SCHEMATU
    assert len(tabele) == ILE_TABEL, \
        f"start postawił {len(tabele)} tabel zamiast {ILE_TABEL}"


def test_bez_startu_zadanie_ODMAWIA_zamiast_pokazac_zera(tmp_path, monkeypatch):
    """Co się stanie, gdy migracji nikt nie wywoła — pytanie z bramki W2.

    Klient budowany BEZ `with` nie uruchamia uchwytu cyklu życia. Baza zostaje
    niezmigrowana. Żądanie ma wtedy odmówić i powiedzieć, co uruchomić —
    nigdy pokazać zer.
    """
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
        magazyn.zmigruj()

    tresc = str(blad.value)
    assert "zobowiazania.oprocentowanie" in tresc
    assert "nieodwracalne" in tresc.lower()


def test_zdejmowanie_kolumn_NIE_BIEGNIE_przy_otwarciu(baza, monkeypatch):
    """Zmiana wagi wady: z „przy każdym żądaniu HTTP" na „przy migracji".

    Sprzeczna krotka ustawiana PO migracji: gdyby `polacz()` nadal wołało
    `_zdejmij_kolumny`, odmowa padłaby tutaj.
    """
    magazyn.zmigruj()
    monkeypatch.setattr(magazyn, "_ZDEJMOWANE_KOLUMNY",
                        (("zobowiazania", "oprocentowanie"),))

    polaczenie = magazyn.polacz()
    try:
        assert "oprocentowanie" in pomocnicze.kolumny_tabeli(
            polaczenie, "zobowiazania"), \
            "otwarcie bazy zdjęło kolumnę — `_zdejmij_kolumny` nadal biegnie w `polacz()`"
    finally:
        polaczenie.close()

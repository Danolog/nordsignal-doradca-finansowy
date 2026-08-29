# -*- coding: utf-8 -*-
"""Strażnicy tabeli `rejestr_stawek` w bazie SQLite (schemat 12).

DLACZEGO TA TABELA W OGÓLE MA STRAŻNIKÓW. Do 2026-08-29 rejestr istniał jako
kształt bez tabeli: `wiedza/rejestr.py` niósł napis SQL w dialekcie
PostgreSQL, `wiedza/stawki_poczatkowe.py` niósł 19 wartości, a baza, na której
aplikacja stoi, nie miała ani jednego wiersza. Zatwierdzenie stawki przez
człowieka nie zmieniało wtedy żadnej liczby, bo nie było gdzie jej zapisać.

CO KAŻDY STRAŻNIK TU WIDZI — liczba stoi w asercji, nie w nazwie. Pusta baza
jest dla strażników groźna: test, który nic nie znalazł, bo nic nie ma,
przechodzi tak samo jak test, który sprawdził i potwierdził. Dlatego przy
każdej asercji o zawartości stoi obok kontrola liczności.
"""
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from silnik.rdzen import magazyn
from wiedza import rejestr, stawki_poczatkowe

KORZEN = Path(__file__).resolve().parent.parent


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz(tmp_path / "rejestr.db")


def _kolumny_z_napisu(sql: str) -> set[str]:
    """Nazwy kolumn wycięte z `CREATE TABLE rejestr_stawek (...)`.

    Bierze wyłącznie pierwszy człon każdej linii wewnątrz nawiasu i pomija
    linie zaczynające się od `CONSTRAINT`, `--` i `CREATE`. Świadomie prosto:
    parser bogatszy niż napis, który parsuje, sam zaczyna być miejscem wady.
    """
    ciało = sql.split("rejestr_stawek (", 1)[1].split("\n);", 1)[0]
    nazwy = set()
    for linia in ciało.splitlines():
        linia = linia.strip()
        if not linia or linia.startswith(("--", "CONSTRAINT", "CREATE", ")")):
            continue
        dopasowanie = re.match(r"([a-z_]+)\s", linia)
        if dopasowanie:
            nazwy.add(dopasowanie.group(1))
    return nazwy


# --- jeden nośnik nazw kolumn, dwa dialekty -------------------------------

def test_oba_dialekty_niosa_DOKLADNIE_kolumny_z_jednego_nosnika():
    """Świadomy drugi nośnik (§3.2) — dopuszczalny WYŁĄCZNIE z tym strażnikiem.

    `SCHEMAT` jest w dialekcie PostgreSQL, `SCHEMAT_SQLITE` w dialekcie bazy,
    która dziś naprawdę działa. Rozjazd między nimi nie objawiłby się błędem —
    objawiłby się kolumną, która jest po jednej stronie i której nie ma po
    drugiej, czyli danymi ginącymi przy migracji na PostgreSQL.

    KONTROLA LICZNOŚCI: obie strony muszą coś zobaczyć. Parser, który zwrócił
    pusty zbiór, porównałby pustkę z pustką i zameldował zgodność.
    """
    pg = _kolumny_z_napisu(rejestr.SCHEMAT)
    lite = _kolumny_z_napisu(rejestr.SCHEMAT_SQLITE)
    assert len(pg) >= 10, f"parser wyciął z dialektu PostgreSQL {len(pg)} kolumn"
    assert len(lite) >= 10, f"parser wyciął z dialektu SQLite {len(lite)} kolumn"
    assert pg == set(rejestr.KOLUMNY)
    assert lite == set(rejestr.KOLUMNY)


# --- tabela powstaje i ma dane --------------------------------------------

def test_swieza_baza_MA_tabele_rejestru(p):
    tabele = {w[0] for w in p.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "rejestr_stawek" in tabele


def test_rejestr_dostaje_WSZYSTKIE_pozycje_zasilenia(p):
    """Liczność po obu stronach, nie „są jakieś wiersze".

    Porównanie z `len(WSZYSTKIE)` samo w sobie byłoby tautologią, gdyby moduł
    zasilenia był pusty — stąd druga asercja o liczbie większej od zera.
    """
    ile_w_module = len(stawki_poczatkowe.WSZYSTKIE)
    assert ile_w_module > 0, "moduł zasilenia jest pusty — nie ma czego wsiać"
    ile_w_bazie = p.execute("SELECT COUNT(*) FROM rejestr_stawek").fetchone()[0]
    assert ile_w_bazie == ile_w_module


def test_ZADNA_stawka_nie_jest_zatwierdzona(p):
    """Reguła twarda §3.4: automat proponuje, człowiek zatwierdza.

    Droga maszynowa do statusu `zatwierdzona` nie istnieje. Ten strażnik
    czerwieni się w chwili, w której ktoś ją zbuduje.
    """
    stany = magazyn.policz_stawki(p)
    assert sum(stany.values()) > 0, "rejestr pusty — nie ma czego sprawdzać"
    assert stany["zatwierdzona"] == 0
    assert stany["wycofana"] == 0
    assert stany["proponowana"] == sum(stany.values())


def test_wczytane_stawki_niosa_Decimal_a_nie_liczbe_zmiennoprzecinkowa(p):
    """§3.1. Napis „0.1952" podany do `float()` daje liczbę i ciszę."""
    wczytane = magazyn.wczytaj_stawki(p)
    assert len(wczytane) == len(stawki_poczatkowe.WSZYSTKIE)
    assert all(isinstance(s.wartosc, Decimal) for s in wczytane)
    assert all(isinstance(s.obowiazuje_od, date) for s in wczytane)


def test_wczytane_stawki_maja_zrodlo_i_date_odczytu(p):
    """Stawka bez metryki pochodzenia jest liczbą z nieznanego źródła (§3.7)."""
    wczytane = magazyn.wczytaj_stawki(p)
    assert len(wczytane) > 0
    bez_zrodla = [s.klucz for s in wczytane if not s.zrodlo_url]
    assert bez_zrodla == []


def test_jawna_watpliwosc_przezywa_droge_do_bazy(p):
    """Pole `niezweryfikowane` jest jedynym miejscem, w którym rozjazd źródeł
    zostaje wypowiedziany. Zgubione po drodze zamienia wątpliwość w pewność."""
    ile_w_module = sum(1 for s in stawki_poczatkowe.WSZYSTKIE
                       if s.niezweryfikowane)
    assert ile_w_module > 0, "zasilenie nie niesie żadnej wątpliwości"
    ile_w_bazie = p.execute(
        "SELECT COUNT(*) FROM rejestr_stawek "
        "WHERE niezweryfikowane IS NOT NULL AND niezweryfikowane <> ''"
    ).fetchone()[0]
    assert ile_w_bazie == ile_w_module


# --- więzy ----------------------------------------------------------------

def test_baza_ODRZUCA_zatwierdzona_bez_podpisu(p):
    """`zatwierdzona_ma_podpis` — jedyny mechanizm, który nie wpuści do rachunku
    stawki bez podpisu człowieka. SQLite egzekwuje `CHECK` bez żadnej `PRAGMA`,
    inaczej niż klucze obce."""
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        p.execute(
            "INSERT INTO rejestr_stawek (klucz, wartosc, jednostka,"
            " obowiazuje_od, zrodlo_url, data_odczytu, status)"
            " VALUES ('test.klucz','1','zl','2026-01-01','http://x','2026-01-01',"
            " 'zatwierdzona')")


def test_baza_ODRZUCA_nieznany_stan(p):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        p.execute(
            "INSERT INTO rejestr_stawek (klucz, wartosc, jednostka,"
            " obowiazuje_od, zrodlo_url, data_odczytu, status)"
            " VALUES ('test.klucz','1','zl','2026-01-01','http://x','2026-01-01',"
            " 'wpisana-recznie')")


def test_baza_PRZYJMUJE_zatwierdzona_z_podpisem(p):
    """Kontrola dwustronna: więz ma odrzucać brak podpisu, a nie wszystko."""
    p.execute(
        "INSERT INTO rejestr_stawek (klucz, wartosc, jednostka, obowiazuje_od,"
        " zrodlo_url, data_odczytu, status, zatwierdzil, data_zatwierdzenia)"
        " VALUES ('test.klucz','1','zl','2026-01-01','http://x','2026-01-01',"
        " 'zatwierdzona','Darek','2026-01-02')")
    p.commit()
    assert magazyn.policz_stawki(p)["zatwierdzona"] == 1


# --- powtórne otwarcie ----------------------------------------------------

def test_ponowne_otwarcie_NIE_DUBLUJE_rejestru(tmp_path):
    """`polacz` wykonuje zasiew przy KAŻDYM otwarciu bazy."""
    sciezka = tmp_path / "dwa-razy.db"
    magazyn.zmigruj_i_polacz(sciezka).close()
    drugie = magazyn.zmigruj_i_polacz(sciezka)
    ile = drugie.execute("SELECT COUNT(*) FROM rejestr_stawek").fetchone()[0]
    assert ile == len(stawki_poczatkowe.WSZYSTKIE)


def test_zasiew_NIE_WSKRZESZA_propozycji_po_zatwierdzeniu(tmp_path):
    """Sedno idempotencji po trójce BEZ statusu.

    Gdyby warunek obecności zawierał `status = 'proponowana'`, to po podpisie
    Darka ta sama wartość wróciłaby przy następnym starcie aplikacji jako
    druga propozycja — obok tej samej liczby już zatwierdzonej. Człowiek
    zatwierdzałby ją w kółko.
    """
    sciezka = tmp_path / "podpisana.db"
    polaczenie = magazyn.zmigruj_i_polacz(sciezka)
    przed = polaczenie.execute("SELECT COUNT(*) FROM rejestr_stawek").fetchone()[0]
    polaczenie.execute(
        "UPDATE rejestr_stawek SET status='zatwierdzona', zatwierdzil='Darek',"
        " data_zatwierdzenia='2026-09-01' WHERE klucz='vat.stawka_podstawowa'")
    polaczenie.commit()
    polaczenie.close()

    drugie = magazyn.zmigruj_i_polacz(sciezka)
    po = drugie.execute("SELECT COUNT(*) FROM rejestr_stawek").fetchone()[0]
    assert przed > 0
    assert po == przed
    assert drugie.execute(
        "SELECT COUNT(*) FROM rejestr_stawek WHERE klucz='vat.stawka_podstawowa'"
    ).fetchone()[0] == 1


# --- dług jawny: dane są, konsumenta nie ma -------------------------------

def test_rejestr_MA_dane_i_NIE_MA_konsumenta():
    """STRAŻNIK PROGU, nie strażnik poprawności — i dlatego jego czerwień jest
    DOBRĄ wiadomością.

    Stan na 2026-08-29: rejestr ma 19 pozycji w bazie, a silnik nadal liczy
    ze stałych w `silnik/rdzen/stawki.py`. To jest dług nazwany w PRD §5
    i w nagłówku `magazyn.zasiej_rejestr_stawek`. Ten test pilnuje, żeby dług
    nie zniknął po cichu w żadną stronę:

    * gdy ktoś podepnie silnik pod rejestr — test padnie i wymusi zdjęcie
      opisu długu z PRD i z magazynu;
    * gdy ktoś usunie rejestr — padną strażnicy wyżej.

    KONTROLA LICZNOŚCI: przeszukiwane pliki są liczone. Wyszukiwanie, do
    którego nie dotarł żaden plik, zwróciłoby „zero konsumentów" i zameldowało
    sukces przy skasowanym katalogu `silnik/`.
    """
    pliki = sorted((KORZEN / "silnik").rglob("*.py")) + \
        sorted((KORZEN / "api").rglob("*.py"))
    assert len(pliki) >= 20, f"przeszukano tylko {len(pliki)} plików"

    wolajace = []
    for plik in pliki:
        if plik.name == "magazyn.py":
            continue  # magazyn JEST warstwą trwałości rejestru, nie konsumentem
        tresc = plik.read_text(encoding="utf-8")
        if "wczytaj_stawki" in tresc or "rejestr.obowiazujaca" in tresc:
            wolajace.append(plik.name)

    assert wolajace == [], (
        "Rejestr stawek dostał konsumenta w silniku: "
        f"{wolajace}. To jest DOBRA zmiana — ale wymaga zdjęcia opisu długu "
        "z `docs/PRD.md` §5 i z nagłówka `magazyn.zasiej_rejestr_stawek`, "
        "bo od tej chwili twierdzenie 'rejestr nie ma konsumenta' jest fałszem."
    )

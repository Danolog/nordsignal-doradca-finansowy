# -*- coding: utf-8 -*-
"""STRAZNIK DWOCH NOSNIKOW SCHEMATU BAZY (W1, 2026-08-29).

CO PILNUJE. Schemat bazy zyje w dwoch kopiach i to jest SWIADOMY dlug
(CLAUDE.md §3.2), dopuszczalny wylacznie ze strazikiem i jawnym progiem:

  * dialekt SQLite  — `magazyn._SCHEMAT` + `rejestr.SCHEMAT_SQLITE`;
    to nosnik ZYWY, z niego stoi baza, na ktorej aplikacja dzis liczy;
  * dialekt PostgreSQL — `silnik.baza.schemat_postgresql()`, czyli
    `silnik/baza/schemat.sql` + `rejestr.SCHEMAT`; to cel migracji.

PROG KONSOLIDACJI, JAWNY: drugi nosnik znika w chwili, w ktorej aplikacja
przestanie otwierac SQLite. Do tego czasu kazdy rozjazd ma czerwienic ten plik.

DLACZEGO NIE WYSTARCZY POROWNAC NAZW KOLUMN. Do 2026-08-29 nic nie pilnowalo
tych dwoch napisow. Pomiar tym samym przyrzadem na commicie `0b282cc` dal
DWADZIESCIA CZTERY miejsca rozjazdu (plan sesji mowil o dziewieciu); po
domknieciu W1 zostaje ich DZIEWIEC i kazde jest wpisane do rejestru nizej.
Najgrozniejsze z zamknietych NIE BYLY brakiem kolumny:
  * `data_obowiazku_vat NOT NULL` po stronie PostgreSQL przy pisarzu, ktory
    tej kolumny nie wypelnia — po migracji padl by KAZDY zapis faktury;
  * `forma_opodatkowania` dopuszczajaca `LINIOWY`, ktorego `forma_na_rok`
    odrzuca — baza wpuszczala stan, na ktorym rachunek wybucha;
  * `pkwiu DEFAULT ''` obok `_wymagaj_pkwiu`, ktore pustego PKWiU nie wpuszcza.
Straznik porownujacy same nazwy przeszedlby przez wszystkie trzy na zielono.
Dlatego porownanie idzie po TYPIE, OBOWIAZKOWOSCI, WARTOSCI DOMYSLNEJ
i DZIEDZINIE WARTOSCI.

KONTROLA LICZNOSCI STOI PRZY KAZDEJ ASERCJI. Porownanie pustego zbioru
z pustym zbiorem jest zielone i bezwartosciowe — a parser, ktory z jakiegos
powodu nic nie wycial, produkuje dokladnie taki zbior. Liczby ponizej stoja
w asercjach, nie w nazwach testow.

CZEGO TEN PLIK NIE SPRAWDZA — wypisane, zeby cisza nie uchodzila za zgode.
Lista jest w naglowku `testy/porownanie_schematu.py`. Najwazniejsze: tresc
wiezu `CHECK` innego niz `IN (...)` porownuje sie po NAZWIE, nie po tresci,
a kolumny i warunek indeksu czesciowego nie sa porownywane wcale.
"""
from __future__ import annotations

import pytest

from silnik import baza
from silnik.rdzen import budzet, magazyn
from testy import porownanie_schematu as ps
from wiedza import rejestr

#: Ile tabel ma miec schemat. Trzynascie przeniesionych z poprzednika plus
#: `rejestr_stawek` (PRD §6.2). Liczba stoi tutaj, zeby test nie mogl
#: zameldowac zgodnosci, porownujac dwa puste zbiory.
ILE_TABEL = 14

#: Najmniejsza liczba kolumn, ktore porownanie ma faktycznie odwiedzic.
#: Pomiar z 2026-08-29 dal 95; prog 90 zostawia miejsce na drobne zmiany
#: i nadal czerwieni sie, gdy parser przestanie cokolwiek widziec.
NAJMNIEJ_KOLUMN = 90

#: Ile kolumn trzyma pieniadze — pomiar `_KWOTOWE` z 2026-08-29: dziewiec
#: tabel, SZESNASCIE kolumn. `docs/plan-chmura-2026-08-29.md` (wiersz 60)
#: twierdzi "17 kolumn" — nosnik pomylil sie o jedna.
ILE_KOLUMN_KWOTOWYCH = 16

#: Ile wiezow jednoznacznosci niesie schemat — pomiar z 2026-08-29: cztery
#: (`przychody_jdg.numer_faktury`, `kategorie(typ,nazwa)`,
#: `plan_budzetu(rok,miesiac,typ,kategoria,opis)`, `cele.nazwa`).
ILE_WIEZOW_JEDNOZNACZNOSCI = 4

#: WIEZY WYLACZNIE PO STRONIE PostgreSQL — swiadome, kazdy z powodem.
#: To jest REJESTR, nie wyjatek zbiorczy: dopisanie siodmego wiezu bez
#: dopisania go tutaj czerwieni `test_wiezy_TYLKO_PostgreSQL_sa_te_z_rejestru`.
WIEZY_TYLKO_POSTGRESQL = {
    # SQLite trzyma kwoty NAPISEM, wiec `kwota >= 0` porownywalo by napisy
    # ("9" > "10"). Regule egzekwuje `magazyn.zapisz_wpis` (kwota dodatnia).
    ("wpisy_budzetu", "kwota_bez_znaku"),
    ("zobowiazania", "oprocentowanie_sensowne"),
    # Egzekwowane w Pythonie przy zapisie planu. Do SQLite dolozylyby sie bez
    # przeszkody — PROG: przy najblizszej przebudowie `plan_budzetu`.
    ("plan_budzetu", "miesiac_sensowny"),
    ("plan_budzetu", "dzien_sensowny"),
    # Egzekwowane w `magazyn.zapisz_forme` (stawka tylko przy ryczalcie).
    ("forma_opodatkowania", "stawka_tylko_przy_ryczalcie"),
}

#: INDEKSY WYLACZNIE PO STRONIE PostgreSQL — trzy, kazdy z powodem.
INDEKSY_TYLKO_POSTGRESQL = {
    # Wydajnosc, nie poprawnosc.
    "wpisy_po_dacie",
    "wpisy_do_rachunku",
    # POPRAWNOSC (D-30): rachunek rozliczeniowy moze byc tylko jeden.
    # SQLite uniosloby ten indeks. PROG: przy pierwszym wierszu majatku
    # o kategorii "rachunek rozliczeniowy" wpisanym poza formularzem.
    "majatek_jeden_rozliczeniowy",
}


@pytest.fixture(scope="module")
def dialekty():
    lite = ps.parsuj(magazyn._SCHEMAT + "\n" + rejestr.SCHEMAT_SQLITE)
    pg = ps.parsuj(baza.schemat_postgresql())
    return lite, pg


# --- kontrola licznosci: przyrzad w ogole cos widzi ------------------------

def test_parser_WIDZI_oba_napisy_a_nie_porownuje_pustki(dialekty):
    """Bez tego kazda asercja nizej jest tautologia.

    Straznik porownujacy pusty zbior z pustym zbiorem jest zielony i nie
    strzeze niczego. Ten test jest kontrola licznosci dla calego pliku.
    """
    lite, pg = dialekty
    assert len(lite) == ILE_TABEL, (
        f"dialekt SQLite: parser wyciagnal {len(lite)} tabel, ma byc {ILE_TABEL} "
        f"({sorted(lite)})")
    assert len(pg) == ILE_TABEL, (
        f"dialekt PostgreSQL: parser wyciagnal {len(pg)} tabel, ma byc "
        f"{ILE_TABEL} ({sorted(pg)})")
    for nazwa, tabela in list(lite.items()) + list(pg.items()):
        assert tabela.kolumny, f"tabela {nazwa} wyszla z parsera bez kolumn"
    # Kontrola dwustronna: parser nie sprawdza sam siebie. Liczba polecen
    # `CREATE TABLE` liczy sie osobnym wyrazeniem, nie przez `parsuj`.
    napis_lite = magazyn._SCHEMAT + "\n" + rejestr.SCHEMAT_SQLITE
    napis_pg = baza.schemat_postgresql()
    assert ps.ile_polecen_create_table(napis_lite) == len(lite), (
        f"napis SQLite niesie {ps.ile_polecen_create_table(napis_lite)} polecen "
        f"CREATE TABLE, a parser zbudowal {len(lite)} tabel")
    assert ps.ile_polecen_create_table(napis_pg) == len(pg), (
        f"napis PostgreSQL niesie {ps.ile_polecen_create_table(napis_pg)} polecen "
        f"CREATE TABLE, a parser zbudowal {len(pg)} tabel")


def test_zlozenie_PostgreSQL_NIESIE_rejestr_stawek(dialekty):
    """Sam `schemat.sql` niesie trzynascie tabel — i to jest decyzja.

    `rejestr_stawek` mieszka w `wiedza/rejestr.py`, bo tam mieszka regula
    "silnik czyta wylacznie stawki zatwierdzone". Baza postawiona z samego
    pliku wygladalaby na kompletna i nie miala ani jednej stawki.
    """
    _, pg = dialekty
    z_pliku = ps.parsuj(baza.PLIK_SCHEMATU.read_text(encoding="utf-8"))
    assert len(z_pliku) == ILE_TABEL - 1, (
        f"`schemat.sql` niesie {len(z_pliku)} tabel, ma niesc {ILE_TABEL - 1}")
    assert "rejestr_stawek" not in z_pliku
    assert "rejestr_stawek" in pg


# --- rdzen: te same tabele i te same kolumny ------------------------------

def test_oba_dialekty_MAJA_te_same_tabele(dialekty):
    lite, pg = dialekty
    assert set(lite) == set(pg), (
        f"tylko SQLite: {sorted(set(lite) - set(pg))}; "
        f"tylko PostgreSQL: {sorted(set(pg) - set(lite))}")


def test_oba_dialekty_MAJA_te_same_kolumny(dialekty):
    """Rozjazd nazw nie objawia sie bledem — objawia sie kolumna, ktorej po
    migracji nie ma, i zapisem, ktory pada dopiero u Darka."""
    lite, pg = dialekty
    sprawdzonych = 0
    roznice = []
    for nazwa in sorted(set(lite) & set(pg)):
        a, b = set(lite[nazwa].kolumny), set(pg[nazwa].kolumny)
        sprawdzonych += len(a | b)
        if a != b:
            roznice.append(f"{nazwa}: tylko SQLite {sorted(a - b)}, "
                           f"tylko PostgreSQL {sorted(b - a)}")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownanie odwiedzilo {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert roznice == [], "; ".join(roznice)


# --- typ, obowiazkowosc, wartosc domyslna, dziedzina ----------------------

def test_TYPY_kolumn_odpowiadaja_sobie_rodzina_po_rodzinie(dialekty):
    """`NUMERIC` po jednej stronie ma miec `TEXT` po drugiej, `BOOLEAN` —
    `INTEGER`. Typ zmiennoprzecinkowy nie ma odpowiednika w ogole (§3.1)."""
    lite, pg = dialekty
    sprawdzonych = 0
    bledy = []
    for nazwa in sorted(set(lite) & set(pg)):
        for k in sorted(set(lite[nazwa].kolumny) & set(pg[nazwa].kolumny)):
            sprawdzonych += 1
            r = ps.rodzina(pg[nazwa].kolumny[k].typ)
            oczekiwany = ps.ODPOWIEDNIK_SQLITE.get(r)
            if oczekiwany is None:
                bledy.append(f"{nazwa}.{k}: typ PostgreSQL "
                             f"{pg[nazwa].kolumny[k].typ!r} -> rodzina {r}")
                continue
            faktyczny = ps.typ_sqlite(lite[nazwa].kolumny[k])
            if faktyczny != oczekiwany:
                bledy.append(f"{nazwa}.{k}: SQLite {faktyczny!r}, PostgreSQL "
                             f"{pg[nazwa].kolumny[k].typ!r} (rodzina {r} "
                             f"wymaga {oczekiwany!r})")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownano typy {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert bledy == [], "; ".join(bledy)


def test_OBOWIAZKOWOSC_kolumn_jest_ta_sama(dialekty):
    """Ten wymiar zlapal `data_obowiazku_vat NOT NULL` przy pisarzu, ktory
    tej kolumny nie wypelnia — wiez odrzucalby KAZDY zapis faktury."""
    lite, pg = dialekty
    sprawdzonych = 0
    bledy = []
    for nazwa in sorted(set(lite) & set(pg)):
        for k in sorted(set(lite[nazwa].kolumny) & set(pg[nazwa].kolumny)):
            sprawdzonych += 1
            a = lite[nazwa].kolumny[k].obowiazkowa
            b = pg[nazwa].kolumny[k].obowiazkowa
            if a != b:
                bledy.append(f"{nazwa}.{k}: SQLite NOT NULL={a}, "
                             f"PostgreSQL NOT NULL={b}")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownano obowiazkowosc {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert bledy == [], "; ".join(bledy)


def test_WARTOSCI_DOMYSLNE_sa_te_same(dialekty):
    """Wartosc domyslna po jednej stronie to cicha odpowiedz na pytanie,
    ktorego druga strona nie zadaje. `pkwiu DEFAULT ''` bylo dziura obok
    `_wymagaj_pkwiu`, ktore pustego PKWiU nie wpuszcza."""
    lite, pg = dialekty
    sprawdzonych = 0
    bledy = []
    for nazwa in sorted(set(lite) & set(pg)):
        for k in sorted(set(lite[nazwa].kolumny) & set(pg[nazwa].kolumny)):
            sprawdzonych += 1
            a = lite[nazwa].kolumny[k].domyslna
            b = pg[nazwa].kolumny[k].domyslna
            if not ps.porownaj_domyslna(
                    a, b, rodzina_kolumny=ps.rodzina(pg[nazwa].kolumny[k].typ)):
                bledy.append(f"{nazwa}.{k}: SQLite DEFAULT {a!r}, "
                             f"PostgreSQL DEFAULT {b!r}")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownano wartosci domyslne {sprawdzonych} kolumn, "
        f"prog {NAJMNIEJ_KOLUMN}")
    assert bledy == [], "; ".join(bledy)


def test_DZIEDZINY_WARTOSCI_sa_te_same(dialekty):
    """Zbior wartosci dopuszczonych przez `CHECK (kolumna IN (...))`.

    Ten wymiar zlapal `LINIOWY` — forme, ktora baza wpuszczala, a ktorej
    `forma_na_rok` nie przyjmuje.
    """
    lite, pg = dialekty
    porownanych = 0
    bledy = []
    for nazwa in sorted(set(lite) & set(pg)):
        for k in sorted(set(lite[nazwa].kolumny) & set(pg[nazwa].kolumny)):
            a = lite[nazwa].kolumny[k].dziedzina
            b = pg[nazwa].kolumny[k].dziedzina
            if a is None and b is None:
                continue
            porownanych += 1
            if a != b:
                bledy.append(f"{nazwa}.{k}: SQLite {a}, PostgreSQL {b}")
    assert porownanych >= 5, (
        f"porownano {porownanych} dziedzin wyliczeniowych, spodziewane co "
        "najmniej piec (zrodlo wpisu, forma, typ kategorii, status stawki, "
        "jednostka stawki)")
    assert bledy == [], "; ".join(bledy)


# --- dziedzina formy: jeden nosnik, nie dwie listy ------------------------

def test_dziedzina_formy_ZGADZA_SIE_z_FORMY_ZAPISYWALNE(dialekty):
    """CLAUDE.md §2: ryczalt jest WADA, nie wartoscia domyslna, a forma,
    ktorej rachunek nie obsluguje, nie ma prawa dac sie zapisac.

    Lista w `CHECK` jest swiadomym drugim nosnikiem `FORMY_ZAPISYWALNE`.
    PROG KONSOLIDACJI: przy pierwszej zmianie zbioru form — wtedy oba napisy
    SQL generuje sie z tej krotki.
    """
    lite, pg = dialekty
    zapisywalne = tuple(sorted(magazyn.FORMY_ZAPISYWALNE))
    assert len(zapisywalne) >= 2, "zbior form zapisywalnych jest pusty albo jednoelementowy"
    for etykieta, dialekt in (("SQLite", lite), ("PostgreSQL", pg)):
        dziedzina = dialekt["forma_opodatkowania"].kolumny["forma"].dziedzina
        assert dziedzina is not None, (
            f"{etykieta}: `forma_opodatkowania.forma` nie ma wiezu dziedziny — "
            "baza wpuscilaby kazdy napis, w tym forme, ktorej silnik nie zna")
        assert dziedzina == zapisywalne, (
            f"{etykieta}: baza dopuszcza {dziedzina}, a `forma_na_rok` przyjmuje "
            f"wylacznie {zapisywalne}")
    assert magazyn.FORMA_NIEROZSTRZYGNIETA not in zapisywalne, (
        "`NIEROZSTRZYGNIETA` jest stanem ODCZYTU (brak wpisu), nie wartoscia "
        "do zapisania — w dziedzinie bazy nie ma prawa stac")


def test_dziedzina_typu_kategorii_ZGADZA_SIE_z_budzet_TYPY(dialekty):
    """Drugi nosnik `budzet.TYPY`, tez z progiem: przy pierwszej zmianie
    zbioru typow napis SQL generuje sie z krotki."""
    _, pg = dialekty
    typy = tuple(sorted(budzet.TYPY))
    assert len(typy) == 3, f"`budzet.TYPY` ma {len(typy)} pozycji, spodziewane trzy"
    assert pg["kategorie"].kolumny["typ"].dziedzina == typy


# --- kwoty: nigdy typ zmiennoprzecinkowy ---------------------------------

def test_KAZDA_kolumna_kwotowa_jest_NUMERYCZNA_po_stronie_PostgreSQL(dialekty):
    """CLAUDE.md §3.1. `REAL` w sciezce kwoty gubi grosze po cichu.

    Nosnikiem odpowiedzi "ktora kolumna trzyma pieniadze" jest `_KWOTOWE`
    w `magazyn.py` — ten sam, z ktorego `_wczytaj` robi `Decimal`.

    LUKA NAZWANA: `_KWOTOWE` nie jest pelna lista kolumn liczbowych.
    `forma_opodatkowania.stawka_ryczaltu` i `zobowiazania.oprocentowanie`
    przechodza przez `Decimal` recznie, poza `_wczytaj`, wiec tego testu nie
    dotycza. Domyka je od drugiej strony
    `test_ZADNA_kolumna_nie_uzywa_typu_zmiennoprzecinkowego`.
    """
    _, pg = dialekty
    sprawdzonych = 0
    bledy = []
    for tabela, kolumny in magazyn._KWOTOWE.items():
        assert tabela in pg, f"`_KWOTOWE` wskazuje tabele {tabela}, ktorej nie ma"
        for k in kolumny:
            sprawdzonych += 1
            if k not in pg[tabela].kolumny:
                bledy.append(f"{tabela}.{k}: kolumna kwotowa bez odpowiednika")
                continue
            if ps.rodzina(pg[tabela].kolumny[k].typ) != "kwota":
                bledy.append(f"{tabela}.{k}: typ {pg[tabela].kolumny[k].typ!r} "
                             "nie jest typem dziesietnym")
    assert sprawdzonych == ILE_KOLUMN_KWOTOWYCH, (
        f"sprawdzono {sprawdzonych} kolumn kwotowych, pomiar z 2026-08-29 "
        f"dal {ILE_KOLUMN_KWOTOWYCH}")
    assert bledy == [], "; ".join(bledy)


def test_ZADNA_kolumna_nie_uzywa_typu_zmiennoprzecinkowego(dialekty):
    """Kontrola dwustronna do testu wyzej: tamten pyta, czy kwoty sa
    dziesietne, ten — czy gdziekolwiek indziej nie wszedl typ zmiennoprzecinkowy."""
    _, pg = dialekty
    sprawdzonych = 0
    winne = []
    for nazwa, tabela in pg.items():
        for k, kolumna in tabela.kolumny.items():
            sprawdzonych += 1
            if ps.rodzina(kolumna.typ) == "ZMIENNOPRZECINKOWA":
                winne.append(f"{nazwa}.{k} ({kolumna.typ})")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"przejrzano {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert winne == [], "; ".join(winne)


# --- wiezy i indeksy: rejestr roznic swiadomych ---------------------------

def test_UNIQUE_jest_ten_sam_po_obu_stronach(dialekty):
    lite, pg = dialekty
    porownanych = 0
    bledy = []
    for nazwa in sorted(set(lite) & set(pg)):
        porownanych += len(lite[nazwa].unikalne | pg[nazwa].unikalne)
        if lite[nazwa].unikalne != pg[nazwa].unikalne:
            bledy.append(f"{nazwa}: SQLite {sorted(lite[nazwa].unikalne)}, "
                         f"PostgreSQL {sorted(pg[nazwa].unikalne)}")
    assert porownanych == ILE_WIEZOW_JEDNOZNACZNOSCI, (
        f"porownano {porownanych} wiezow jednoznacznosci, pomiar z 2026-08-29 "
        f"dal {ILE_WIEZOW_JEDNOZNACZNOSCI} — liczba inna znaczy, ze parser "
        "widzi co innego niz wtedy")
    assert bledy == [], "; ".join(bledy)


def test_wiezy_TYLKO_PostgreSQL_sa_te_z_rejestru(dialekty):
    """Rozjazd swiadomy musi byc WYPISANY, nie przemilczany (§3.2).

    Siodmy wiez dolozony po stronie PostgreSQL bez wpisu do rejestru
    czerwieni ten test — i o to chodzi.
    """
    lite, pg = dialekty
    assert WIEZY_TYLKO_POSTGRESQL, "rejestr roznic swiadomych jest pusty"
    tylko_pg = {(n, w) for n in pg for w in pg[n].wiezy
                if w not in lite.get(n, ps.Tabela(n)).wiezy}
    tylko_lite = {(n, w) for n in lite for w in lite[n].wiezy
                  if w not in pg.get(n, ps.Tabela(n)).wiezy}
    assert tylko_pg == WIEZY_TYLKO_POSTGRESQL, (
        f"nie w rejestrze: {sorted(tylko_pg - WIEZY_TYLKO_POSTGRESQL)}; "
        f"w rejestrze, ale juz nie w schemacie: "
        f"{sorted(WIEZY_TYLKO_POSTGRESQL - tylko_pg)}")
    assert tylko_lite == set(), (
        f"wiezy wylacznie po stronie SQLite: {sorted(tylko_lite)} — "
        "PostgreSQL jest celem migracji i nie ma prawa byc slabszy")


def test_indeksy_TYLKO_PostgreSQL_sa_te_z_rejestru():
    lite = ps.indeksy(magazyn._SCHEMAT + "\n" + rejestr.SCHEMAT_SQLITE)
    pg = ps.indeksy(baza.schemat_postgresql())
    assert pg, "parser nie zobaczyl ani jednego indeksu po stronie PostgreSQL"
    assert pg - lite == INDEKSY_TYLKO_POSTGRESQL, (
        f"nie w rejestrze: {sorted(pg - lite - INDEKSY_TYLKO_POSTGRESQL)}; "
        f"w rejestrze, ale juz nie w schemacie: "
        f"{sorted(INDEKSY_TYLKO_POSTGRESQL - (pg - lite))}")
    assert lite - pg == set(), (
        f"indeksy wylacznie po stronie SQLite: {sorted(lite - pg)}")


# --- swieza baza faktycznie odrzuca forme spoza dziedziny -----------------

def test_swieza_baza_ODRZUCA_forme_spoza_dwojki(tmp_path):
    """Wiez z napisu ma dzialac w bazie, nie tylko wygladac w pliku.

    Bez tego testu `CHECK` w `_SCHEMAT` bylby deklaracja — a straznik
    porownujacy napisy potwierdzalby zgodnosc dwoch martwych liter.
    """
    import sqlite3

    polaczenie = magazyn.zmigruj_i_polacz(tmp_path / "forma.db")
    with pytest.raises(sqlite3.IntegrityError):
        polaczenie.execute(
            "INSERT INTO forma_opodatkowania (rok, forma) VALUES (?,?)",
            (2031, "LINIOWY"))
    polaczenie.rollback()
    # Kontrola dwustronna: wiez ma odrzucac `LINIOWY`, a nie wszystko.
    polaczenie.execute(
        "INSERT INTO forma_opodatkowania (rok, forma) VALUES (?,?)",
        (2031, magazyn.FORMA_SKALA))
    assert polaczenie.execute(
        "SELECT forma FROM forma_opodatkowania WHERE rok = 2031"
    ).fetchone()[0] == magazyn.FORMA_SKALA


def test_swieza_baza_PRZYJMUJE_kazdy_typ_z_budzet_TYPY(tmp_path):
    """Kontrola dwustronna do wiezu `typ_znany` — i pulapka normalizacji.

    "Oszczędności" stoi w trzech miejscach: w `budzet.TYPY`, w napisie SQL
    wiezu i w danych. Gdyby ktorekolwiek z nich bylo w innej postaci zapisu
    znakow (na macOS ta sama litera z ogonkiem ma dwa rownowazne zapisy),
    wiez odrzucalby POPRAWNY typ, a straznik porownujacy napisy nadal bylby
    zielony. Ten test pyta baze, nie napis.
    """
    polaczenie = magazyn.zmigruj_i_polacz(tmp_path / "typy.db")
    assert len(budzet.TYPY) == 3
    for i, typ in enumerate(budzet.TYPY):
        polaczenie.execute(
            "INSERT INTO kategorie (typ, nazwa) VALUES (?,?)",
            (typ, f"kontrola-{i}"))
    polaczenie.commit()
    wstawione = polaczenie.execute(
        "SELECT COUNT(*) FROM kategorie WHERE nazwa LIKE 'kontrola-%'"
    ).fetchone()[0]
    assert wstawione == len(budzet.TYPY)

# -*- coding: utf-8 -*-
"""STRAZNIK SCHEMATU WOBEC DZIALAJACEJ BAZY (W4, 2026-08-29).

NASTEPCA `test_schemat_dwa_dialekty.py`, KTORY DOMYKA JEGO NAZWANA LUKE.

CO PILNOWAL POPRZEDNIK I DLACZEGO PRZESTAL. Schemat zyl w dwoch kopiach —
dialekt SQLite (`magazyn._SCHEMAT` + `rejestr.SCHEMAT_SQLITE`) i dialekt
PostgreSQL (`silnik.baza.schemat_postgresql()`) — a poprzednik porownywal je
kolumna po kolumnie. To byl SWIADOMY dlug z jawnym progiem: „drugi nosnik
znika w chwili, w ktorej aplikacja przestanie otwierac SQLite". W4 podmienilo
sterownik, wiec drugi nosnik zostal skasowany i porownywac nie ma czego.

LUKA, KTORA POPRZEDNIK MIAL I NAZYWAL: **porownywal DWA NAPISY, nie dwie
dzialajace bazy**. Blad skladni w `schemat.sql` przeszedlby przez wszystkie
siedemnascie jego testow na zielono — parser czytal tekst i nie probowal go
wykonac. Ten plik porownuje NAPIS DDL z BAZA POSTAWIONA Z TEGO NAPISU:
kazda asercja ma po jednej stronie tekst, po drugiej katalog systemowy
PostgreSQL. Napis, ktorego serwer nie przyjmie, czerwieni sie w fiksturze —
czyli zanim dojdzie do jakiejkolwiek asercji.

KONTROLA LICZNOSCI STOI PRZY KAZDEJ ASERCJI. Porownanie pustego zbioru
z pustym jest zielone i bezwartosciowe — a parser albo zapytanie do katalogu,
ktore z jakiegos powodu nic nie zwrocilo, produkuje dokladnie taki zbior.
Liczby stoja w asercjach, nie w nazwach testow.

CZEGO TEN PLIK NIE SPRAWDZA — wypisane, zeby cisza nie uchodzila za zgode:
  * TRESCI wiezu `CHECK` innego niz `IN (...)` — porownujemy NAZWY wiezow
    i dziedziny wyliczeniowe, nie wyrazenia logiczne;
  * kolumn i warunku indeksu czesciowego — tylko nazwe indeksu;
  * zachowania `REFERENCES ... ON DELETE` — istnienie klucza obcego owszem,
    zachowanie przy kasowaniu nie.
"""
from __future__ import annotations

import pytest

from silnik import baza
from silnik.rdzen import budzet, magazyn
from testy import porownanie_schematu as ps
from wiedza import rejestr

#: Ile tabel ma schemat. Trzynascie przeniesionych z poprzednika, plus
#: `rejestr_stawek` (PRD §6.2), plus `wersja_schematu` — nastepca
#: `PRAGMA user_version`, ktora w PostgreSQL nie istnieje (W4).
ILE_TABEL = 15

#: Najmniejsza liczba kolumn, ktore porownanie ma faktycznie odwiedzic.
#: Pomiar z 2026-08-29 po W4 dal 97; prog 90 zostawia miejsce na drobne
#: zmiany i nadal czerwieni sie, gdy przyrzad przestanie cokolwiek widziec.
NAJMNIEJ_KOLUMN = 90

#: Ile kolumn trzyma pieniadze — pomiar `_KWOTOWE` z 2026-08-29: dziewiec
#: tabel, SZESNASCIE kolumn. `docs/plan-chmura-2026-08-29.md` (wiersz 60)
#: twierdzi „17 kolumn"; nosnik pomylil sie o jedna.
ILE_KOLUMN_KWOTOWYCH = 16

#: Ile wiezow jednoznacznosci niesie schemat — pomiar z 2026-08-29 po W4:
#: piec. Cztery sprzed W4 (`przychody_jdg.numer_faktury`,
#: `kategorie(typ,nazwa)`, `plan_budzetu(rok,miesiac,typ,kategoria,opis)`,
#: `cele.nazwa`) plus `wersja_schematu.jedyny` jako klucz glowny nowej tabeli.
#: `numer_faktury` dostal przy tym NAZWE WLASNA — patrz `WIEZ_NUMER_FAKTURY`.
ILE_WIEZOW_JEDNOZNACZNOSCI = 4


@pytest.fixture(scope="function")
def zywa(baza_zmigrowana):
    """Para: (schemat sparsowany z NAPISU, schemat odczytany z BAZY)."""
    return ps.parsuj(baza.schemat_postgresql()), baza_zmigrowana


@pytest.fixture
def baza_zmigrowana():
    """Baza POSTAWIONA z napisu DDL — i odczytana z katalogu systemowego.

    To jest cala roznica wobec poprzednika: napis nie jest tu przedmiotem
    porownania, tylko drogą do przedmiotu. Napis, ktorego serwer nie przyjmie,
    wywraca fiksture.
    """
    polaczenie = magazyn.zmigruj_i_polacz()
    try:
        yield _odczytaj_z_katalogu(polaczenie)
    finally:
        polaczenie.close()


def _odczytaj_z_katalogu(polaczenie) -> dict[str, ps.Tabela]:
    """Schemat tak, jak go widzi SERWER. Nie napis, nie nasz parser."""
    tabele: dict[str, ps.Tabela] = {}
    for nazwa, in polaczenie.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = current_schema() AND table_type='BASE TABLE'"
    ).fetchall():
        tabele[nazwa] = ps.Tabela(nazwa)
    for tabela, kolumna, typ, nullable, domyslna in polaczenie.execute(
            "SELECT table_name, column_name, data_type, is_nullable,"
            " column_default FROM information_schema.columns"
            " WHERE table_schema = current_schema()").fetchall():
        if tabela not in tabele:
            continue
        tabele[tabela].kolumny[kolumna] = ps.Kolumna(
            nazwa=kolumna, typ=typ, obowiazkowa=(nullable == "NO"),
            domyslna=domyslna, dziedzina=None)
    for tabela, wiez, rodzaj, definicja in polaczenie.execute(
            "SELECT c.conrelid::regclass::text, c.conname, c.contype,"
            " pg_get_constraintdef(c.oid)"
            " FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace"
            " WHERE n.nspname = current_schema()").fetchall():
        if tabela not in tabele:
            continue
        if rodzaj == "u":
            kolumny = definicja[definicja.index("(") + 1:definicja.rindex(")")]
            # Sortowane, tak samo jak po stronie napisu: KOLEJNOSC kolumn
            # w wiezie jednoznacznosci nie zmienia tego, co wiez odrzuca,
            # a rozjazd kolejnosci daje falszywe czerwone.
            tabele[tabela].unikalne.add(
                tuple(sorted(k.strip() for k in kolumny.split(","))))
        if rodzaj == "c":
            tabele[tabela].wiezy.add(wiez)
            dziedzina = ps.dziedzina_z_bazy(definicja)
            if dziedzina:
                kolumna = ps.kolumna_wiezu_z_bazy(definicja)
                if kolumna in tabele[tabela].kolumny:
                    stara = tabele[tabela].kolumny[kolumna]
                    tabele[tabela].kolumny[kolumna] = ps.Kolumna(
                        nazwa=stara.nazwa, typ=stara.typ,
                        obowiazkowa=stara.obowiazkowa, domyslna=stara.domyslna,
                        dziedzina=dziedzina)
    return tabele


# --- 0. LUKA POPRZEDNIKA: napis DDL ma sie WYKONAC ------------------------

def test_napis_DDL_DA_SIE_wykonac_a_nie_tylko_sparsowac(baza_zmigrowana):
    """DOMKNIECIE LUKI W1, wypisanej w naglowku poprzednika.

    Poprzednik porownywal dwa napisy: blad skladni po stronie PostgreSQL
    przechodzil przez wszystkie jego testy, bo nikt tego napisu nie wykonywal.
    Ta fikstura wykonuje go na dzialajacym serwerze — i to jest jedyny powod,
    dla ktorego reszta tego pliku cokolwiek znaczy.
    """
    assert len(baza_zmigrowana) == ILE_TABEL, (
        f"baza postawiona z `schemat_postgresql()` ma {len(baza_zmigrowana)} "
        f"tabel, ma miec {ILE_TABEL}: {sorted(baza_zmigrowana)}")
    for nazwa, tabela in baza_zmigrowana.items():
        assert tabela.kolumny, f"tabela {nazwa} stoi w bazie bez kolumn"


def test_zlozenie_NIESIE_rejestr_stawek_ktorego_nie_ma_w_pliku(baza_zmigrowana):
    """Sam `schemat.sql` niesie CZTERNASCIE tabel — i to jest decyzja.

    `rejestr_stawek` mieszka w `wiedza/rejestr.py`, bo tam mieszka regula
    „silnik czyta wylacznie stawki zatwierdzone". Baza postawiona z samego
    pliku wygladalaby na kompletna i nie miala ani jednej stawki.
    """
    z_pliku = ps.parsuj(baza.PLIK_SCHEMATU.read_text(encoding="utf-8"))
    assert len(z_pliku) == ILE_TABEL - 1, (
        f"`schemat.sql` niesie {len(z_pliku)} tabel, ma niesc {ILE_TABEL - 1}")
    assert "rejestr_stawek" not in z_pliku
    assert "rejestr_stawek" in baza_zmigrowana
    assert "rejestr_stawek" in ps.parsuj(rejestr.SCHEMAT)


# --- 1. napis a baza: te same tabele i te same kolumny --------------------

def test_NAPIS_i_BAZA_maja_te_same_tabele(zywa):
    napis, w_bazie = zywa
    assert set(napis) == set(w_bazie), (
        f"tylko w napisie DDL: {sorted(set(napis) - set(w_bazie))}; "
        f"tylko w bazie: {sorted(set(w_bazie) - set(napis))}")
    assert len(napis) == ILE_TABEL


def test_NAPIS_i_BAZA_maja_te_same_kolumny(zywa):
    """Rozjazd nazw nie objawia sie bledem — objawia sie kolumna, ktorej
    w bazie nie ma, i zapisem, ktory pada dopiero u Darka."""
    napis, w_bazie = zywa
    sprawdzonych, roznice = 0, []
    for nazwa in sorted(set(napis) & set(w_bazie)):
        a, b = set(napis[nazwa].kolumny), set(w_bazie[nazwa].kolumny)
        sprawdzonych += len(a | b)
        if a != b:
            roznice.append(f"{nazwa}: tylko w napisie {sorted(a - b)}, "
                           f"tylko w bazie {sorted(b - a)}")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownanie odwiedzilo {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert roznice == [], "; ".join(roznice)


def test_OBOWIAZKOWOSC_kolumn_jest_ta_sama_w_napisie_i_w_bazie(zywa):
    """Ten wymiar zlapal w W1 `data_obowiazku_vat NOT NULL` przy pisarzu,
    ktory tej kolumny nie wypelnia — wiez odrzucalby KAZDY zapis faktury."""
    napis, w_bazie = zywa
    sprawdzonych, bledy = 0, []
    for nazwa in sorted(set(napis) & set(w_bazie)):
        for k in sorted(set(napis[nazwa].kolumny) & set(w_bazie[nazwa].kolumny)):
            sprawdzonych += 1
            a = napis[nazwa].kolumny[k].obowiazkowa
            b = w_bazie[nazwa].kolumny[k].obowiazkowa
            if a != b:
                bledy.append(f"{nazwa}.{k}: napis NOT NULL={a}, baza NOT NULL={b}")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownano obowiazkowosc {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert bledy == [], "; ".join(bledy)


def test_RODZINY_TYPOW_zgadzaja_sie_z_tym_co_zalozyl_serwer(zywa):
    """Napis mowi `NUMERIC(14,2)`, serwer oddaje `numeric` — porownujemy
    RODZINE, nie zapis. Typ zmiennoprzecinkowy nie ma rodziny dopuszczalnej."""
    napis, w_bazie = zywa
    sprawdzonych, bledy = 0, []
    for nazwa in sorted(set(napis) & set(w_bazie)):
        for k in sorted(set(napis[nazwa].kolumny) & set(w_bazie[nazwa].kolumny)):
            sprawdzonych += 1
            a = ps.rodzina(napis[nazwa].kolumny[k].typ)
            b = ps.rodzina(_uprosc(w_bazie[nazwa].kolumny[k].typ))
            if a != b:
                bledy.append(f"{nazwa}.{k}: napis {a}, baza {b} "
                             f"({w_bazie[nazwa].kolumny[k].typ})")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"porownano typy {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert bledy == [], "; ".join(bledy)


#: Nazwy typow, ktorymi katalog systemowy odpowiada na nasze zapisy.
#: `BIGSERIAL` nie jest typem, tylko skrotem — serwer zaklada `bigint`
#: z licznikiem, wiec katalog nigdy nie powie „bigserial".
_ODPOWIEDZI_KATALOGU = {
    "bigint": "BIGINT", "integer": "INT", "smallint": "SMALLINT",
    "numeric": "NUMERIC", "text": "TEXT", "date": "DATE", "boolean": "BOOLEAN",
    "timestamp with time zone": "TIMESTAMPTZ",
    "double precision": "DOUBLE", "real": "REAL",
    "character varying": "VARCHAR", "character": "CHAR",
}


def _uprosc(typ_z_katalogu: str) -> str:
    return _ODPOWIEDZI_KATALOGU.get(typ_z_katalogu, typ_z_katalogu)


# --- 2. dziedziny wartosci: zbior odczytany Z BAZY ------------------------

def test_dziedzina_formy_W_BAZIE_zgadza_sie_z_FORMY_ZAPISYWALNE(baza_zmigrowana):
    """CLAUDE.md §2: ryczalt jest WADA, nie wartoscia domyslna, a forma,
    ktorej rachunek nie obsluguje, nie ma prawa dac sie zapisac.

    Zbior czytany Z WIEZU ZALOZONEGO W BAZIE, nie z napisu: napis mogl by
    obiecywac wiez, ktorego serwer nie zalozyl.
    """
    zapisywalne = tuple(sorted(magazyn.FORMY_ZAPISYWALNE))
    assert len(zapisywalne) >= 2, "zbior form zapisywalnych jest jednoelementowy"
    dziedzina = baza_zmigrowana["forma_opodatkowania"].kolumny["forma"].dziedzina
    assert dziedzina is not None, (
        "`forma_opodatkowania.forma` nie ma w BAZIE wiezu dziedziny — baza "
        "wpuscilaby kazdy napis, w tym forme, ktorej silnik nie zna")
    assert dziedzina == zapisywalne, (
        f"baza dopuszcza {dziedzina}, a `forma_na_rok` przyjmuje wylacznie "
        f"{zapisywalne}")
    assert magazyn.FORMA_NIEROZSTRZYGNIETA not in zapisywalne, (
        "`NIEROZSTRZYGNIETA` jest stanem ODCZYTU (brak wpisu), nie wartoscia "
        "do zapisania — w dziedzinie bazy nie ma prawa stac")


def test_dziedzina_typu_kategorii_W_BAZIE_zgadza_sie_z_budzet_TYPY(baza_zmigrowana):
    typy = tuple(sorted(budzet.TYPY))
    assert len(typy) == 3, f"`budzet.TYPY` ma {len(typy)} pozycji, spodziewane trzy"
    assert baza_zmigrowana["kategorie"].kolumny["typ"].dziedzina == typy


def test_baza_ODRZUCA_forme_spoza_dwojki(baza_zmigrowana):
    """Kontrola BEHAWIORALNA obok kontroli opisowej. Wiez, ktory istnieje
    w katalogu, a niczego nie odrzuca, nie jest wiezem."""
    import psycopg

    polaczenie = magazyn.polacz()
    try:
        with pytest.raises(psycopg.errors.CheckViolation):
            polaczenie.execute(
                "INSERT INTO forma_opodatkowania (rok, forma)"
                " VALUES (2099, 'LINIOWY')")
    finally:
        polaczenie.close()


# --- 3. kwoty: nigdy typ zmiennoprzecinkowy, sprawdzone W BAZIE -----------

def test_KAZDA_kolumna_kwotowa_JEST_NUMERYCZNA_w_bazie(baza_zmigrowana):
    """CLAUDE.md §3.1. Typ zmiennoprzecinkowy w sciezce kwoty gubi grosze.

    Nosnikiem odpowiedzi „ktora kolumna trzyma pieniadze" jest `_KWOTOWE`
    w `magazyn.py` — ten sam, z ktorego `_wczytaj` robi `Decimal`.

    LUKA NAZWANA: `_KWOTOWE` nie jest pelna lista kolumn liczbowych.
    `forma_opodatkowania.stawka_ryczaltu` i `zobowiazania.oprocentowanie`
    przechodza przez `Decimal` recznie, poza `_wczytaj`. Domyka je od drugiej
    strony `test_ZADNA_kolumna_w_bazie_nie_jest_zmiennoprzecinkowa`.
    """
    sprawdzonych, bledy = 0, []
    for tabela, kolumny in magazyn._KWOTOWE.items():
        assert tabela in baza_zmigrowana, (
            f"`_KWOTOWE` wskazuje tabele {tabela}, ktorej w bazie nie ma")
        for k in kolumny:
            sprawdzonych += 1
            if k not in baza_zmigrowana[tabela].kolumny:
                bledy.append(f"{tabela}.{k}: kolumna kwotowa bez odpowiednika")
                continue
            typ = _uprosc(baza_zmigrowana[tabela].kolumny[k].typ)
            if ps.rodzina(typ) != "kwota":
                bledy.append(f"{tabela}.{k}: typ w bazie {typ!r} nie jest "
                             "typem dziesietnym")
    assert sprawdzonych == ILE_KOLUMN_KWOTOWYCH, (
        f"sprawdzono {sprawdzonych} kolumn kwotowych, pomiar z 2026-08-29 "
        f"dal {ILE_KOLUMN_KWOTOWYCH}")
    assert bledy == [], "; ".join(bledy)


def test_ZADNA_kolumna_w_bazie_nie_jest_zmiennoprzecinkowa(baza_zmigrowana):
    """Kontrola dwustronna do testu wyzej: tamten pyta, czy kwoty sa
    dziesietne, ten — czy gdziekolwiek indziej nie wszedl typ, ktory gubi
    grosze."""
    sprawdzonych, winne = 0, []
    for nazwa, tabela in baza_zmigrowana.items():
        for k, kolumna in tabela.kolumny.items():
            sprawdzonych += 1
            if ps.rodzina(_uprosc(kolumna.typ)) == "ZMIENNOPRZECINKOWA":
                winne.append(f"{nazwa}.{k} ({kolumna.typ})")
    assert sprawdzonych >= NAJMNIEJ_KOLUMN, (
        f"przejrzano {sprawdzonych} kolumn, prog {NAJMNIEJ_KOLUMN}")
    assert winne == [], "; ".join(winne)


# --- 4. wiezy jednoznacznosci i nazwa wiezu numeru faktury ----------------

def test_UNIQUE_w_bazie_jest_ten_sam_co_w_napisie(zywa):
    napis, w_bazie = zywa
    porownanych, bledy = 0, []
    for nazwa in sorted(set(napis) & set(w_bazie)):
        porownanych += len(napis[nazwa].unikalne)
        if napis[nazwa].unikalne != w_bazie[nazwa].unikalne:
            bledy.append(f"{nazwa}: napis {sorted(napis[nazwa].unikalne)}, "
                         f"baza {sorted(w_bazie[nazwa].unikalne)}")
    assert porownanych == ILE_WIEZOW_JEDNOZNACZNOSCI, (
        f"porownano {porownanych} wiezow jednoznacznosci, pomiar z 2026-08-29 "
        f"dal {ILE_WIEZOW_JEDNOZNACZNOSCI}")
    assert bledy == [], "; ".join(bledy)


def test_wiez_numeru_faktury_MA_NAZWE_ktora_zna_kod(baza_zmigrowana):
    """Znalezisko W3 domkniete w W4.

    Bez nazwy wlasnej PostgreSQL nadalby temu wiezowi nazwe automatyczna
    `przychody_jdg_numer_faktury_key`, w ktorej PRZYPADKIEM siedzi napis
    „numer_faktury" — i dawne dopasowanie po TRESCI komunikatu sterownika
    przezyloby migracje przypadkiem, wiszac na nazwie, ktorej nikt nie wybral.
    """
    unikalne = baza_zmigrowana["przychody_jdg"].unikalne
    assert unikalne == {("numer_faktury",)}, unikalne
    assert magazyn.WIEZ_NUMER_FAKTURY != "przychody_jdg_numer_faktury_key", (
        "kod rozpoznaje wiez po nazwie AUTOMATYCZNEJ — czyli po nazwie, "
        "ktorej nikt nie wybral")


def test_nazwa_wiezu_z_KODU_zgadza_sie_z_nazwa_z_BAZY():
    """Swiadomy drugi nosnik nazwy wiezu, z jawnym progiem.

    Nazwa stoi w `silnik/baza/schemat.sql` (tam zaklada ja baza) i w
    `magazyn.WIEZ_NUMER_FAKTURY` (tam kod ja rozpoznaje). Zawolac napisu DDL
    z Pythona nie da sie bez wykonania go, wiec kopia zostaje — ale rozjazd
    ma czerwienic TEN test, a nie objawiac sie zdaniem „Zapis odrzucony przez
    baze" u Darka.

    PROG KONSOLIDACJI: gdy nazwy wiezow zaczna powstawac z Pythona.
    """
    polaczenie = magazyn.zmigruj_i_polacz()
    try:
        nazwy = {w[0] for w in polaczenie.execute(
            "SELECT conname FROM pg_constraint c"
            " JOIN pg_namespace n ON n.oid = c.connamespace"
            " WHERE n.nspname = current_schema() AND c.contype = 'u'"
        ).fetchall()}
    finally:
        polaczenie.close()
    assert nazwy, "w bazie nie ma ANI JEDNEGO wiezu jednoznacznosci"
    assert magazyn.WIEZ_NUMER_FAKTURY in nazwy, (
        f"kod rozpoznaje duplikat faktury po wiezie "
        f"{magazyn.WIEZ_NUMER_FAKTURY!r}, a baza zna wiezy: {sorted(nazwy)}")


# --- 5. indeksy ------------------------------------------------------------

#: Indeksy, ktorych nie zaklada zaden `PRIMARY KEY` ani `UNIQUE` — trzy,
#: kazdy z powodem. `wpisy_po_dacie` i `wpisy_do_rachunku`: wydajnosc.
#: `majatek_jeden_rozliczeniowy`: POPRAWNOSC (D-30) — rachunek rozliczeniowy
#: moze byc tylko jeden, bo od jego salda rusza prognoza.
#: `rejestr_stawek_jedna_obowiazujaca`: POPRAWNOSC — dwie zatwierdzone
#: wartosci tego samego klucza na ten sam dzien to blad danych, nie konflikt
#: do rozstrzygniecia w kodzie.
INDEKSY_JAWNE = {
    "wpisy_po_dacie",
    "wpisy_do_rachunku",
    "majatek_jeden_rozliczeniowy",
    "rejestr_stawek_jedna_obowiazujaca",
}


def test_INDEKSY_z_napisu_STOJA_w_bazie():
    """Indeks zapowiedziany w napisie, a niezalozony w bazie, nie objawia sie
    bledem — objawia sie dwoma rachunkami rozliczeniowymi i prognoza, ktora
    rusza od kwoty, ktorej Darek na wydatki nie ma."""
    z_napisu = ps.indeksy(baza.schemat_postgresql())
    assert z_napisu == INDEKSY_JAWNE, (
        f"napis DDL zaklada {sorted(z_napisu)}, rejestr mowi "
        f"{sorted(INDEKSY_JAWNE)}")
    polaczenie = magazyn.zmigruj_i_polacz()
    try:
        w_bazie = {w[0] for w in polaczenie.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
        ).fetchall()}
    finally:
        polaczenie.close()
    assert len(w_bazie) >= len(INDEKSY_JAWNE), (
        f"w bazie stoi {len(w_bazie)} indeksow — mniej niz jawnych")
    assert INDEKSY_JAWNE <= w_bazie, (
        f"zapowiedziane, a niezalozone: {sorted(INDEKSY_JAWNE - w_bazie)}")


def test_indeks_jednego_rozliczeniowego_NAPRAWDE_odrzuca_drugi():
    """Kontrola BEHAWIORALNA: indeks, ktory istnieje i niczego nie odrzuca,
    nie jest bramka. Ta reguła ma w kodzie drugiego straznika
    (`magazyn._wymagaj_jednego_rozliczeniowego`) i to jest swiadome —
    kod mowi CZLOWIEKOWI, co zrobic, baza pilnuje wierszy wpisanych obok
    formularza."""
    import psycopg
    from decimal import Decimal

    polaczenie = magazyn.zmigruj_i_polacz()
    try:
        polaczenie.execute(
            "INSERT INTO majatek (nazwa_aktywa, kategoria, wartosc)"
            " VALUES ('mBank', %s, %s)",
            (magazyn.KATEGORIA_RACHUNEK_ROZLICZENIOWY, Decimal("100.00")))
        polaczenie.commit()
        with pytest.raises(psycopg.errors.UniqueViolation):
            polaczenie.execute(
                "INSERT INTO majatek (nazwa_aktywa, kategoria, wartosc)"
                " VALUES ('Revolut', %s, %s)",
                (magazyn.KATEGORIA_RACHUNEK_ROZLICZENIOWY, Decimal("50.00")))
    finally:
        polaczenie.close()

"""Trwałość danych — SQLite za wąskim interfejsem.

Interfejs jest wąski celowo: SQL nie wychodzi poza ten moduł. To warunek
późniejszej podmiany SQLite na Postgresa bez ruszania reszty rdzenia — a więc
warunek opcji „port na FastAPI + Next.js później".

Kwoty przechowywane jako TEXT, nie REAL. `float` gubi grosze przy podróży do
bazy i z powrotem, a to jest aplikacja podatkowa.

Reguły o tym, CO wolno zapisać (trzy typy wpisu, kategoria ze słownika),
mieszkają w Pythonie, nie w więzach SQL. Powód jest zmierzony, nie estetyczny:
`PRAGMA foreign_keys` w SQLite jest domyślnie WYŁĄCZONA i działa per
połączenie, więc klucz obcy zadeklarowany w schemacie nie robi nic. Więz,
którego usunięcie nie zmienia niczego obserwowalnego, nie da się zaczerwienić
mutacją — a to znaczy, że nie jest strażnikiem (CLAUDE.md §8 v1.17).
"""

import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from silnik.rdzen import budzet, stawki
from wiedza import rejestr as rejestr_wiedzy
from wiedza import stawki_poczatkowe

#: KORZEN projektu — patrz komentarz w `konfiguracja.py`: po przeniesieniu
#: do `silnik/rdzen/` modul lezy dwa poziomy nizej niz w poprzedniku.
KORZEN_PROJEKTU = Path(__file__).resolve().parents[2]
SCIEZKA_DOMYSLNA = KORZEN_PROJEKTU / "cfo_database.db"

#: Zmienna srodowiskowa wskazujaca baze. Powod istnienia (Z52): mandat pracy
#: bez udzialu Darka stoi na warunku „agenty pracuja na KOPII bazy, nigdy na
#: `cfo_database.db`" — a do Z52 ten warunek byl obietnica bez mechanizmu.
ZMIENNA_BAZY = "AI_CFO_BAZA"

#: Strazniki rozwiazanej sciezki. W produkcji **pusta** — `rdzen/` nie ma
#: wiedziec, czy dziala pod pytestem (granica pilnowana przez
#: `testy/test_granice.py`). Straznika zaklada `conftest.py`: pod pytestem
#: rozwiazanie sie na baze produkcyjna jest bledem, nie ostrzezeniem.
STRAZNICY_SCIEZKI: list = []


@dataclass(frozen=True)
class OpisBazy:
    """Ktora baze otwarto i czy jest to baza domyslna.

    Jeden nosnik dla dwoch konsumentow: paska aplikacji (Z52) i punktu
    koncowego `/api/stan` (Z65). Drugi konsument ma to ZAWOLAC, nie policzyc
    jeszcze raz — inaczej pasek i API moglyby powiedziec co innego o tej samej
    bazie w tej samej chwili.
    """

    sciezka: Path
    domyslna: bool


def _rozwiaz_sciezke() -> Path:
    """Sama arytmetyka: `AI_CFO_BAZA` albo `SCIEZKA_DOMYSLNA`. BEZ straznikow.

    Rozdzielone od `sciezka_bazy()` swiadomie. Testy sprawdzajace samo
    rozwiazywanie musza umiec zobaczyc wynik „sciezka produkcyjna" — a gdyby
    robily to przez `sciezka_bazy()`, musialyby zdjac bramke. Straznik, ktorego
    trzeba wylaczyc, zeby go sprawdzic, nie jest w tym momencie straznikiem:
    pierwsza wersja tych testow zdejmowala go fikstura i przy mutacji „ignoruj
    zmienna" otworzylaby produkcyjna baze przy zdjetej bramce (Z52, 2026-08-27).

    Zmienna czytana przy KAZDYM wywolaniu, nie przy imporcie: `app.py` wczytuje
    `.env` na poziomie modulu, a proces potomny okna natywnego importuje go
    od nowa.
    """
    surowa = os.environ.get(ZMIENNA_BAZY, "").strip()
    return Path(surowa).expanduser() if surowa else SCIEZKA_DOMYSLNA


def sciezka_bazy() -> Path:
    """Ktora baze otwieramy — JEDYNY nosnik tej odpowiedzi, razem z bramka.

    Kolejnosc: jawny argument `polacz(sciezka=...)` (uzywaja go wszystkie
    testy) > `AI_CFO_BAZA` > `SCIEZKA_DOMYSLNA`.
    """
    sciezka = _rozwiaz_sciezke()
    for straznik in STRAZNICY_SCIEZKI:
        straznik(sciezka)
    return sciezka


def opis_bazy(sciezka: Path | None = None) -> OpisBazy:
    """Rozwiazana sciezka razem z odpowiedzia „czy to baza domyslna"."""
    if sciezka is None:
        sciezka = sciezka_bazy()
    return OpisBazy(sciezka=sciezka,
                    domyslna=sciezka.resolve() == SCIEZKA_DOMYSLNA.resolve())

#: Wersja schematu stemplowana w bazie. Podnoszona przy każdej zmianie
#: nieodwracalnej — dziś (12): tabela `rejestr_stawek` plus trzy kolumny
#: z PRD §6.3 (`wpisy_budzetu.zrodlo`, `kategorie.niezbedna`,
#: `przychody_jdg.data_obowiazku_vat`). Poprzednio (11): wynik przebiegu
#: strażnika w tle, tabela `przebiegi_straznika` (Z71).
WERSJA_SCHEMATU = 12

#: Klucze tabeli `ustawienia`. Rdzeń przechowuje nieprzezroczysty napis i nie
#: wie, co on znaczy — nazwy motywów mieszkają w warstwie interfejsu.
KLUCZ_MOTYW = "motyw"

#: Data rozpoczecia (albo wznowienia) dzialalnosci gospodarczej. Nosnik liczby
#: miesiecy, za ktore nalezy sie ZUS — do Z55 rezerwa liczyla je z FAKTUR,
#: wiec miesiac bez zlecenia nie naliczal skladki (4 850,22 zl zamiast
#: 7 275,33 zl przy trzech miesiacach i dwoch fakturach).
KLUCZ_DZIALALNOSC_OD = "dzialalnosc_od"

#: Nastawy prognozy plynnosci (E4, R17). Wolumen godzin uznany za PEWNY
#: i wolumen realny, plus stawka godzinowa. Przechowywane jako nieprzezroczyste
#: napisy — znaczenie i wartosci startowe nalezą do `rdzen/prognoza_plynnosci`,
#: bo to on odpowiada na pytanie „co znaczy brak tej nastawy".
KLUCZ_WOLUMEN_OSTROZNY = "prognoza_wolumen_ostrozny"
KLUCZ_WOLUMEN_REALNY = "prognoza_wolumen_realny"
KLUCZ_STAWKA_GODZINOWA = "prognoza_stawka_godzinowa"

#: Formy opodatkowania — TRZY stany, nie dwa (decyzja D8 planu formy).
#: `NIEROZSTRZYGNIETA` jest stanem ODCZYTU (brak wpisu), nie wartoscia do
#: zapisania: wartosc domyslna, ktora udaje wybor, jest gorsza niz brak
#: wartosci. Aplikacja formy sprzed zawieszenia dzialalnosci NIE ZNA.
FORMA_NIEROZSTRZYGNIETA = "NIEROZSTRZYGNIETA"
FORMA_SKALA = "SKALA"
FORMA_RYCZALT = "RYCZALT"

#: Formy, ktore wolno ZAPISAC. `NIEROZSTRZYGNIETA` swiadomie poza zbiorem.
FORMY_ZAPISYWALNE = (FORMA_SKALA, FORMA_RYCZALT)

#: Rok, na ktory zaczep migracyjny wpisuje forme wynikajaca z ustalenia §0
#: planu formy: Darek byl na zasadach ogolnych przed zawieszeniem, a milczenie
#: do 20.10.2026 utrwala skale. To WPIS, nie wartosc domyslna kodu — rok 2027
#: zostaje pusty i zachowuje sie jak NIEROZSTRZYGNIETA.
ROK_ZACZEPU_FORMY = 2026

#: Kolumny trzymające kwoty — konwertowane na Decimal przy odczycie.
_KWOTOWE = {
    "przychody_jdg": ["kwota_netto", "stawka_vat", "kwota_vat",
                      "stawka_ryczaltu", "zaplacony_zus", "zysk_netto"],
    "wpisy_budzetu": ["kwota"],
    "koszty_jdg": ["kwota_netto", "kwota_vat"],
    "plan_budzetu": ["kwota_planowana"],
    "cele_oszczednosciowe": ["kwota_docelowa"],
    "zobowiazania": ["kapital", "rata_minimalna"],
    "majatek": ["wartosc"],
    "godziny": ["liczba_godzin"],
    "stan_konta": ["kwota"],
}

#: UWAGA: `wydatki_osobiste` świadomie NIE MA w tym schemacie. `polacz()`
#: wykonuje `_SCHEMAT` przy KAŻDYM otwarciu bazy, więc tabela pozostawiona tu
#: wracałaby po każdej migracji — pusta i wyglądająca jak prawdziwa.
_SCHEMAT = """
CREATE TABLE IF NOT EXISTS przychody_jdg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    numer_faktury TEXT NOT NULL UNIQUE,
    kwota_netto TEXT NOT NULL,
    stawka_vat TEXT NOT NULL,
    kwota_vat TEXT NOT NULL,
    pkwiu TEXT NOT NULL,
    stawka_ryczaltu TEXT NOT NULL,
    zaplacony_zus TEXT NOT NULL,
    zysk_netto TEXT NOT NULL,
    stawki_wersja TEXT NOT NULL,
    data_zaplaty TEXT,
    -- PRD §6.3 p.3, decyzja D-35: VAT liczy sie MEMORIALOWO — obowiazek
    -- powstaje z chwila WYSTAWIENIA faktury, nie jej zaplaty. NULL znaczy
    -- "nie wiem" i jest stanem faktur sprzed tej kolumny; nowe faktury
    -- dostaja date przy zapisie.
    data_obowiazku_vat TEXT,
    wpis_budzetu_id INTEGER
);
CREATE TABLE IF NOT EXISTS wpisy_budzetu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL, typ TEXT NOT NULL, kategoria TEXT NOT NULL,
    kwota TEXT NOT NULL, szczegoly TEXT NOT NULL DEFAULT '',
    -- PRD §6.3 p.2. BRAMKA POPRAWNOSCI, nie metadana dla porzadku:
    -- do rachunku podatkowego wchodza wylacznie wiersze o zrodle innym niz
    -- 'historia-2025'. Bez tej kolumny "wgrac historie" i "nie liczyc jej
    -- do podatku" sa dwiema regulami w dwoch miejscach.
    zrodlo TEXT NOT NULL DEFAULT 'recznie',
    CONSTRAINT zrodlo_znane CHECK (zrodlo IN ('recznie','historia-2025','import'))
);
CREATE TABLE IF NOT EXISTS plan_budzetu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rok INTEGER NOT NULL, miesiac INTEGER NOT NULL, typ TEXT NOT NULL,
    kategoria TEXT NOT NULL, kwota_planowana TEXT NOT NULL,
    powtarzalna INTEGER NOT NULL DEFAULT 0,
    do_roku INTEGER, do_miesiaca INTEGER,
    opis TEXT NOT NULL DEFAULT '',
    dzien INTEGER,
    co_ile_miesiecy INTEGER NOT NULL DEFAULT 1,
    UNIQUE(rok, miesiac, typ, kategoria, opis)
);
CREATE TABLE IF NOT EXISTS kategorie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    typ TEXT NOT NULL, nazwa TEXT NOT NULL,
    kolejnosc INTEGER NOT NULL DEFAULT 0, aktywna INTEGER NOT NULL DEFAULT 1,
    -- PRD §6.3 p.1: czy kategoria liczy sie do progu poduszki. Bez niej prog
    -- poduszki jest PRZEDZIALEM 29 651–63 649 zl, nie liczba. NULL znaczy
    -- "Darek jeszcze nie rozstrzygnal" — stan rozny od "nie jest niezbedna".
    niezbedna INTEGER,
    UNIQUE(typ, nazwa),
    -- W1 (2026-08-29): dziedzina typu kategorii zwezona do `budzet.TYPY`.
    -- Regule egzekwuje dzis `magazyn._wymagaj_typu`, ale slownik kategorii
    -- zasiewa sie i migruje takze poza ta funkcja. Piaty nazwany rozjazd
    -- (baza swieza dostaje wiez, robocza nie) — PROG jak przy `zrodlo_znane`.
    CONSTRAINT typ_znany CHECK (typ IN ('Przychody','Wydatki','Oszczędności'))
);
CREATE TABLE IF NOT EXISTS cele_oszczednosciowe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL UNIQUE, kategoria TEXT NOT NULL,
    kwota_docelowa TEXT NOT NULL, termin TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ustawienia (
    klucz TEXT PRIMARY KEY, wartosc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS zobowiazania (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa TEXT NOT NULL, kapital TEXT NOT NULL, rata_minimalna TEXT NOT NULL,
    oprocentowanie TEXT
);
CREATE TABLE IF NOT EXISTS majatek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa_aktywa TEXT NOT NULL, kategoria TEXT NOT NULL, wartosc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS godziny (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL, rodzaj_czynnosci TEXT NOT NULL, pkwiu TEXT NOT NULL,
    liczba_godzin TEXT NOT NULL, opis TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS forma_opodatkowania (
    rok INTEGER PRIMARY KEY,
    forma TEXT NOT NULL,
    stawka_ryczaltu TEXT,
    -- W1 (2026-08-29): dziedzina formy zwezona do tego, co silnik UNIESIE.
    -- `forma_na_rok` odrzuca kazda wartosc spoza `FORMY_ZAPISYWALNE`, wiec
    -- baza dopuszczajaca wiecej dopuszczala stan, na ktorym rachunek wybucha.
    -- Lista wartosci jest SWIADOMYM drugim nosnikiem `FORMY_ZAPISYWALNE` —
    -- pilnuje jej `testy/test_schemat_dwa_dialekty.py`.
    --
    -- CZWARTY NAZWANY ROZJAZD, dokladnie ten sam co przy `zrodlo_znane`:
    -- `CREATE TABLE IF NOT EXISTS` nie rusza tabeli, ktora juz jest, a
    -- `ALTER TABLE` w SQLite nie potrafi dolozyc `CHECK`. Wiez dostaje wiec
    -- baza SWIEZA; baza robocza sprzed tej zmiany zostaje bez niego.
    -- Roznica dotyczy WYLACZNIE odrzucania wartosci spoza dwojki i nie
    -- zmienia zadnej liczby. PROG: wiez jest po obu stronach od przejscia
    -- na PostgreSQL (`silnik/baza/schemat.sql` juz go niesie).
    CONSTRAINT forma_znana CHECK (forma IN ('SKALA','RYCZALT'))
);
CREATE TABLE IF NOT EXISTS stan_konta (
    data TEXT PRIMARY KEY,
    kwota TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS koszty_jdg (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL, opis TEXT NOT NULL,
    kwota_netto TEXT NOT NULL, kwota_vat TEXT NOT NULL,
    wpis_budzetu_id INTEGER
);
CREATE TABLE IF NOT EXISTS przebiegi_straznika (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kiedy TEXT NOT NULL,
    stan_prognozy TEXT NOT NULL,
    pierwszy_dzien_ujemny TEXT,
    pilnych INTEGER NOT NULL,
    powod TEXT,
    zrodla TEXT NOT NULL,
    komunikat TEXT NOT NULL,
    powiadomiono INTEGER NOT NULL DEFAULT 0
);
"""


class BladMagazynu(Exception):
    """Błąd zapisu lub odczytu, z komunikatem po polsku zamiast śladu wyjątku."""


@dataclass(frozen=True)
class RaportMigracji:
    """Wynik wchłonięcia starej tabeli wydatków — trzy liczby i zdanie.

    Nigdy wartość logiczna i nigdy słowo „gotowe": migracja, która nic nie
    przeniosła, ma to powiedzieć liczbą, a nie schować za wartością prawdziwą.
    """

    przed: int
    przeniesione: int
    po: int
    komunikat: str


def _tabele(polaczenie) -> set[str]:
    return {w[0] for w in polaczenie.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


#: Kolumny dokladane do tabel, ktore juz istnieja. (tabela, kolumna, typ)
_DOPISYWANE_KOLUMNY = (
    ("przychody_jdg", "data_zaplaty", "TEXT"),
    ("przychody_jdg", "wpis_budzetu_id", "INTEGER"),
    # Z42: `rok`/`miesiac` zmieniaja znaczenie dla wiersza z `powtarzalna = 1`
    # (staja sie POCZATKIEM obowiazywania). `DEFAULT 0` jest jedynym nosnikiem
    # decyzji Darka nr 2 z 2026-08-26: kazdy wiersz sprzed migracji — w tym 41
    # pozycji z importu arkusza — zostaje pozycja jednorazowa.
    ("plan_budzetu", "powtarzalna", "INTEGER NOT NULL DEFAULT 0"),
    ("plan_budzetu", "do_roku", "INTEGER"),
    ("plan_budzetu", "do_miesiaca", "INTEGER"),
    # D9, zlecenie Darka 2026-08-28 godz. 19:38. Bez `NOT NULL` i bez
    # `DEFAULT`: istniejace wiersze maja dostac NULL, czyli „nie wiem".
    # `DEFAULT '0'` wpisalby wszystkim ZEROWE oprocentowanie — czyli
    # odpowiedz, ktorej nikt nie udzielil, nieodrozninalna od Aliora, ktory
    # naprawde ma 0%.
    ("zobowiazania", "oprocentowanie", "TEXT"),
    # TRZY KOLUMNY Z PRD §6.3, dolozone 2026-08-29 (schemat 12).
    #
    # ROZJAZD NAZWANY, NIE UKRYTY. `ALTER TABLE ADD COLUMN` w SQLite nie
    # potrafi dolozyc wiezu `CHECK`, wiec w bazie, ktora JUZ ISTNIEJE,
    # `zrodlo` dostaje wartosc domyslna bez wiezu `zrodlo_znane`; w bazie
    # swiezej wiez jest, bo idzie z `_SCHEMAT`. Roznica dotyczy WYLACZNIE
    # odrzucania wartosci spoza trojki i nie zmienia zadnej liczby.
    # PROG: wiez wraca po obu stronach przy przejsciu na PostgreSQL
    # (`silnik/baza/schemat.sql` juz go niesie). Pilnuje tego
    # `testy/test_trzy_kolumny.py::test_swieza_baza_ODRZUCA_zrodlo_spoza_trojki`.
    #
    # DRUGI ROZJAZD, TEZ NAZWANY: wiersze sprzed tej migracji dostaja
    # `zrodlo = 'recznie'` — w bazie ROBOCZEJ znaczy to, ze 204 wpisy
    # historii 2025 wygladaja jak wpisane recznie. Nie ma to dzis skutku,
    # bo kolumna NIE MA JESZCZE KONSUMENTA (zero odczytow w silniku).
    # PROG: przy pierwszym konsumencie `zrodlo` baza robocza wymaga
    # jednorazowego oznaczenia historii — albo konsument filtruje po dacie.
    # Baza PRODUKCYJNA problemu nie ma: startuje pusta (decyzja 2026-08-29).
    ("wpisy_budzetu", "zrodlo", "TEXT NOT NULL DEFAULT 'recznie'"),
    # NULL znaczy "Darek jeszcze nie rozstrzygnal". Wartosc domyslna 0 albo 1
    # bylaby odpowiedzia, ktorej nikt nie udzielil — ta sama klasa wady co
    # forma opodatkowania zgadnieta wartoscia domyslna.
    ("kategorie", "niezbedna", "INTEGER"),
    # Bez `NOT NULL`: `ALTER TABLE ADD COLUMN ... NOT NULL` bez wartosci
    # domyslnej SQLite odrzuca, a data domyslna bylaby ZMYSLENIEM daty
    # obowiazku podatkowego. NULL = "nie wiem" i tak zostaje faktura z bazy
    # roboczej.
    #
    # SPROSTOWANIE W1 (2026-08-29): do tego dnia stalo tu, ze
    # `silnik/baza/schemat.sql` niesie `NOT NULL` i ze jest to "trzeci
    # nazwany rozjazd, ktory znika przy migracji". To bylo nieprawdziwe
    # w skutkach: `zapisz_fakture` tej kolumny NIE WYPELNIA, wiec wiez po
    # stronie PostgreSQL nie wymuszal by daty, tylko odrzucal KAZDY zapis
    # faktury. Wiez zdjety z `schemat.sql`; oba nosniki maja tu teraz
    # kolumne dopuszczajaca NULL i pilnuje tego
    # `testy/test_schemat_dwa_dialekty.py::test_OBOWIAZKOWOSC_kolumn_jest_ta_sama`.
    # PROG POWROTU WIEZU: pierwszy pisarz, ktory te date wyliczy.
    ("przychody_jdg", "data_obowiazku_vat", "TEXT"),
)


#: Kolumny ZDEJMOWANE z tabel, ktore juz istnieja. (tabela, kolumna)
#: Osobna krotka od `_DOPISYWANE_KOLUMNY`, bo to operacja NIEODWRACALNA —
#: `ALTER TABLE DROP COLUMN` kasuje dane kolumny bez sladu.
_ZDEJMOWANE_KOLUMNY: tuple[tuple[str, str], ...] = (
    # PUSTA — i to jest stan docelowy, nie przeoczenie.
    #
    # Stal tu wpis `("zobowiazania", "oprocentowanie")` z Z43 (decyzja Darka
    # 2026-08-26: „zobowiazanie niesie wylacznie kapital i rate; oprocentowanie
    # nie wchodzi do zadnej liczby, wiec jest martwe"). Uzasadnienie bylo
    # trafne WTEDY. Darek odwrocil te decyzje 2026-08-28 (godz. 19:38): pole
    # wraca, zeby dane zaczely sie zbierac pod plasterek, ktory je policzy.
    #
    # Wpis MUSIAL stad zniknac, a nie tylko zostac zrownowazony dopisaniem
    # kolumny: `_zdejmij_kolumny` biegnie PO `_dopisz_kolumny` przy KAZDYM
    # otwarciu bazy i jest NIEODWRACALNE. Zostawiony tutaj kasowalby
    # oprocentowanie wpisane przez Darka przy kazdym starcie aplikacji, po
    # cichu i przy zielonej suicie. Pilnuje tego
    # `test_kolumna_PRZEZYWA_ponowne_otwarcie_bazy`.
)


def _zdejmij_kolumny(polaczenie) -> None:
    """Usuwa kolumny wycofane z modelu. NIEODWRACALNE — dane kolumny znikaja.

    Zostawienie martwej kolumny bylo by drugim nosnikiem: tabela dalej
    niosla by wartosc, ktorej nikt nie liczy, a ktora wyglada jak dana.
    """
    for tabela, kolumna in _ZDEJMOWANE_KOLUMNY:
        istniejace = {w[1] for w in
                      polaczenie.execute(f"PRAGMA table_info({tabela})")}
        if kolumna in istniejace:
            polaczenie.execute(f"ALTER TABLE {tabela} DROP COLUMN {kolumna}")


def _dopisz_kolumny(polaczenie) -> None:
    """Dokłada brakujące kolumny do tabel, które już istnieją.

    `CREATE TABLE IF NOT EXISTS` NIE rusza tabeli, która jest — nowa kolumna
    w `_SCHEMAT` powstaje więc wyłącznie w świeżej bazie, a w bazie z danymi
    nie powstałaby nigdy. Bez tego kroku migracja wygląda na wykonaną
    (wersja schematu się podnosi), a kolumny nie ma i zapis pada dopiero
    przy pierwszym użyciu.
    """
    for tabela, kolumna, typ in _DOPISYWANE_KOLUMNY:
        istniejace = {w[1] for w in
                      polaczenie.execute(f"PRAGMA table_info({tabela})")}
        if kolumna not in istniejace:
            polaczenie.execute(
                f"ALTER TABLE {tabela} ADD COLUMN {kolumna} {typ}")


#: Kolumny `plan_budzetu` po Z48, w kolejnosci zapisu.
_KOLUMNY_PLANU = ("rok", "miesiac", "typ", "kategoria", "kwota_planowana",
                  "powtarzalna", "do_roku", "do_miesiaca", "opis", "dzien",
                  "co_ile_miesiecy")


def _przebuduj_plan_budzetu(polaczenie) -> None:
    """Przenosi `plan_budzetu` na schemat Z48: opis, dzien, cykl.

    Przebudowa, a nie `ALTER TABLE`, bo zmienia sie WIEZ: dotad jedna pozycja
    na (rok, miesiac, typ, kategoria), teraz ta sama czworka PLUS opis —
    dzieki temu w jednej kategorii miesci sie „Kredyt Revolut" i „Kredyt
    Alior". SQLite nie potrafi zdjac wiezu w miejscu; trzeba nowej tabeli.

    Wiersze sprzed migracji dostaja pusty opis (pozycja bezimienna, taka jak
    z importu arkusza) i cykl miesieczny — czyli zachowuja sie dokladnie jak
    dotad. Kontrola licznosci jest w tescie migracji: ile wierszy przed,
    tyle po.
    """
    kolumny = {w[1] for w in polaczenie.execute("PRAGMA table_info(plan_budzetu)")}
    if not kolumny or "opis" in kolumny:
        return
    stare = ", ".join(k for k in _KOLUMNY_PLANU
                      if k in kolumny)
    polaczenie.executescript(f"""
        ALTER TABLE plan_budzetu RENAME TO plan_budzetu_stary;
        CREATE TABLE plan_budzetu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rok INTEGER NOT NULL, miesiac INTEGER NOT NULL, typ TEXT NOT NULL,
            kategoria TEXT NOT NULL, kwota_planowana TEXT NOT NULL,
            powtarzalna INTEGER NOT NULL DEFAULT 0,
            do_roku INTEGER, do_miesiaca INTEGER,
            opis TEXT NOT NULL DEFAULT '',
            dzien INTEGER,
            co_ile_miesiecy INTEGER NOT NULL DEFAULT 1,
            UNIQUE(rok, miesiac, typ, kategoria, opis)
        );
        INSERT INTO plan_budzetu ({stare})
            SELECT {stare} FROM plan_budzetu_stary;
        DROP TABLE plan_budzetu_stary;
    """)
    polaczenie.commit()


#: Ile razy wiecej miejsca niz waga bazy musi byc wolne, zeby migracja ruszyla.
#: Dwa: jeden na kopie, jeden na przebudowe tabeli w trakcie migracji
#: (`_przebuduj_plan_budzetu` trzyma przez chwile obie wersje naraz).
ZAPAS_MIEJSCA = 2


def _teraz() -> datetime:
    """Szew czasu — wydzielony, zeby test mogl ustalic nazwe kopii."""
    return datetime.now()


def _wolne_miejsce(katalog: Path) -> int:
    """Szew pomiaru — wydzielony, zeby dalo sie sprawdzic sciezke braku miejsca.

    Bez niego jedyny sposob na jej sprawdzenie to zapelnienie dysku.
    """
    return shutil.disk_usage(katalog).free


def _kopia_przed_migracja(polaczenie, sciezka: Path) -> Path | None:
    """Kopiuje plik bazy, gdy zaraz ruszy migracja schematu. Zwraca sciezke kopii.

    Warunek jest podwojny: plik **istnieje i ma dane** oraz jego wersja jest
    **nizsza** niz ta, ktora zna kod. Kopia przy kazdym otwarciu zasypalaby
    katalog i przestalaby cokolwiek znaczyc.

    Powod istnienia (specyfikacja §7.6): do Z53 kopii nie robil kod, tylko
    czlowiek — osiem razy, pamietajac za kazdym razem. Pierwsza migracja,
    ktora to cwiczy, to schemat 8 z Z60.

    Nazwa bierze sie z OTWIERANEJ bazy, nie ze stalej: od Z52 aplikacja bywa
    uruchamiana na kopii roboczej i stala nazwalaby plik, ktorego tu nie ma.
    """
    if not sciezka.exists() or sciezka.stat().st_size == 0:
        return None
    wersja = polaczenie.execute("PRAGMA user_version").fetchone()[0]
    if wersja >= WERSJA_SCHEMATU:
        return None

    waga = sciezka.stat().st_size
    wolne = _wolne_miejsce(sciezka.parent)
    if wolne < waga * ZAPAS_MIEJSCA:
        raise BladMagazynu(
            f"Za malo miejsca na dysku, zeby zrobic kopie bazy przed migracja "
            f"schematu {wersja} → {WERSJA_SCHEMATU}. Baza wazy {waga} bajtow, "
            f"potrzeba {waga * ZAPAS_MIEJSCA}, wolne jest {wolne}. "
            f"Migracja NIE zostala rozpoczeta — baza jest nietknieta. "
            f"Zwolnij miejsce i uruchom ponownie.")

    stempel = _teraz().strftime("%Y-%m-%d-%H%M")
    cel = sciezka.with_name(f"{sciezka.name}-kopia-przed-migracja-{stempel}")
    shutil.copy2(sciezka, cel)
    return cel


def _zaczep_formy(polaczenie) -> None:
    """Wpisuje forme na rok zaczepu, gdy tabela jest PUSTA.

    Warunek jest „tabela pusta", nie „brak wiersza na 2026": gdyby Darek
    skasowal wpis na 2026 swiadomie, ponowne wpisanie go przy nastepnym
    otwarciu byloby nadpisaniem jego decyzji. Gdyby z kolei zaczep pisal przy
    kazdym otwarciu, zmiana formy cofalaby sie po restarcie i wygladalo by to
    jak niezapisany formularz.
    """
    if polaczenie.execute("SELECT COUNT(*) FROM forma_opodatkowania") \
            .fetchone()[0]:
        return
    polaczenie.execute(
        "INSERT INTO forma_opodatkowania (rok, forma) VALUES (?,?)",
        (ROK_ZACZEPU_FORMY, FORMA_SKALA))
    polaczenie.commit()


def _sprawdz_wersje(polaczenie) -> None:
    """Odmawia otwarcia bazy nowszej niż ten kod.

    Bez tego starszy checkout na zmigrowanej bazie odtworzyłby przez `_SCHEMAT`
    pustą tabelę i pokazał na pulpicie 0,00 zł. Cicha zła liczba jest gorsza
    niż odmowa — dlatego wersja stoi w bazie i jest sprawdzana przy otwarciu.
    """
    wersja = polaczenie.execute("PRAGMA user_version").fetchone()[0]
    if wersja > WERSJA_SCHEMATU:
        raise BladMagazynu(
            f"Baza jest w wersji schematu {wersja}, a ten kod zna "
            f"{WERSJA_SCHEMATU}. Uruchamiasz starszą wersję aplikacji na "
            "nowszej bazie — odmawiam otwarcia, bo pokazałbym Ci zera zamiast "
            "Twoich danych."
        )


def polacz(sciezka: Path | None = None) -> sqlite3.Connection:
    """Otwiera bazę, tworząc plik, tabele i słownik kategorii, jeśli ich nie ma.

    Brak pliku to normalny stan początkowy, nie awaria.

    Bez argumentu pyta `sciezka_bazy()` — jeden nośnik odpowiedzi „którą bazę
    otwieramy" (Z52). Argument zostaje i wygrywa ze zmienną środowiskową:
    używają go wszystkie testy, każdy na własnym pliku w katalogu tymczasowym.
    """
    if sciezka is None:
        sciezka = sciezka_bazy()
    try:
        # `check_same_thread=False`: narzędzia doradcy wykonują się w PULI
        # WĄTKÓW SDK, a nie w wątku, który otworzył bazę. Sterownik sqlite3
        # blokuje to domyślnie — blokadą własną, nie biblioteki C. Zdjęcie jej
        # jest bezpieczne, bo moduł zgłasza tryb SERIALIZED (`threadsafety == 3`),
        # czyli synchronizację bierze na siebie sam SQLite. Założenie jest
        # nazwane i pilnowane testem: `test_sterownik_sqlite_jest_w_trybie_szeregowanym`.
        polaczenie = sqlite3.connect(str(sciezka), check_same_thread=False)
        _sprawdz_wersje(polaczenie)
        # Kopia PRZED czymkolwiek, co pisze: `_dopisz_kolumny`,
        # `_zdejmij_kolumny` (NIEODWRACALNE) i `_przebuduj_plan_budzetu`.
        _kopia_przed_migracja(polaczenie, Path(sciezka))
        tabele_przed = _tabele(polaczenie)
        polaczenie.executescript(_SCHEMAT)
        # Rejestr stawek WOLA swoj napis z `wiedza/`, nie powtarza go tutaj.
        # Tabela z liczbami z prawa ma mieszkac tam, gdzie mieszka regula
        # „silnik czyta wylacznie zatwierdzone" (CLAUDE.md §3.3).
        polaczenie.executescript(rejestr_wiedzy.SCHEMAT_SQLITE)
        _dopisz_kolumny(polaczenie)
        _zdejmij_kolumny(polaczenie)
        _przebuduj_plan_budzetu(polaczenie)
        _zaczep_formy(polaczenie)
        if "wydatki_osobiste" in tabele_przed:
            wchlon_wydatki_osobiste(polaczenie)
        zasiej_kategorie(polaczenie)
        zasiej_rejestr_stawek(polaczenie)
        polaczenie.execute(f"PRAGMA user_version = {WERSJA_SCHEMATU}")
        polaczenie.commit()
        return polaczenie
    except sqlite3.Error as e:
        raise BladMagazynu(
            f"Nie udało się otworzyć bazy danych pod ścieżką {sciezka}. "
            f"Sprawdź, czy katalog istnieje i czy masz prawo zapisu. Szczegół: {e}"
        ) from e


# --- migracja i zasiew ----------------------------------------------------

def _liczba_wydatkow_w_budzecie(polaczenie) -> int:
    if "wpisy_budzetu" not in _tabele(polaczenie):
        return 0
    return polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu WHERE typ = ?",
        (budzet.TYP_WYDATKI,)).fetchone()[0]


def wchlon_wydatki_osobiste(polaczenie) -> RaportMigracji:
    """Przenosi `wydatki_osobiste` do `wpisy_budzetu` jako typ „Wydatki" i kasuje
    tabelę źródłową.

    Nośnikiem stanu „już wchłonięte" jest NIEOBECNOŚĆ tabeli w bazie, nie flaga
    obok. Dzięki temu powtórne wywołanie jest bezpieczne i mówi wprost, że nie
    miało czego przenosić.
    """
    if "wydatki_osobiste" not in _tabele(polaczenie):
        po = _liczba_wydatkow_w_budzecie(polaczenie)
        return RaportMigracji(
            przed=0, przeniesione=0, po=po,
            komunikat="Tabela wydatki_osobiste nie istnieje — przeniesiono "
                      f"0 wierszy, w budżecie jest ich {po}.")

    przed = polaczenie.execute("SELECT COUNT(*) FROM wydatki_osobiste") \
        .fetchone()[0]
    juz_bylo = _liczba_wydatkow_w_budzecie(polaczenie)

    if przed and "wpisy_budzetu" not in _tabele(polaczenie):
        raise BladMagazynu(
            f"Tabela wpisy_budzetu nie istnieje, a wydatki_osobiste ma {przed} "
            "wierszy. Odmawiam migracji, bo dane nie mają dokąd trafić.")

    if przed:
        polaczenie.execute(
            "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, szczegoly) "
            "SELECT data, ?, kategoria, kwota, '' FROM wydatki_osobiste",
            (budzet.TYP_WYDATKI,))

    po = _liczba_wydatkow_w_budzecie(polaczenie)
    if po != juz_bylo + przed:
        # Wycofanie JAWNE, nie przypadkowe (Z53). Do Z53 komunikat obiecywał
        # „Zmiany wycofane", a wycofywał je dopiero sterownik przy zamknięciu
        # połączenia — pierwszy `commit()` z kodu obok zatwierdziłby niepełną
        # migrację pod zdaniem mówiącym, że jej nie ma.
        polaczenie.rollback()
        raise BladMagazynu(
            f"Migracja zgubiła albo zdublowała wiersze: przed {przed}, w "
            f"budżecie było {juz_bylo}, po migracji {po}. Zmiany wycofane.")

    polaczenie.execute("DROP TABLE wydatki_osobiste")
    polaczenie.commit()
    return RaportMigracji(
        przed=przed, przeniesione=przed, po=po,
        komunikat=f"Przeniesiono {przed} z {przed} wierszy; wydatków w "
                  f"budżecie po migracji: {po}.")


def zasiej_kategorie(polaczenie) -> int:
    """Wsiewa startowy słownik kategorii. Zwraca liczbę faktycznie dodanych.

    `INSERT OR IGNORE` po parze (typ, nazwa) — powtórne uruchomienie nie
    duplikuje, a kategoria usunięta świadomie przez użytkownika **nie wraca**
    przy następnym starcie... o ile została usunięta trwale. Dezaktywowana
    zostaje dezaktywowana, bo wiersz nadal istnieje.
    """
    dodane = 0
    for typ, nazwy in budzet.KATEGORIE_STARTOWE.items():
        for kolejnosc, nazwa in enumerate(nazwy):
            kursor = polaczenie.execute(
                "INSERT OR IGNORE INTO kategorie (typ, nazwa, kolejnosc, aktywna)"
                " VALUES (?,?,?,1)", (typ, nazwa, kolejnosc))
            dodane += kursor.rowcount if kursor.rowcount > 0 else 0
    polaczenie.commit()
    return dodane


# --- rejestr stawek: liczby pochodzace z prawa ----------------------------
#
# DLACZEGO TA TABELA W OGOLE POWSTAJE. Do 2026-08-29 `wiedza/` bylo procedura
# nad pustym miejscem: rejestr mial ksztalt, stany, wiezy i zasilenie
# poczatkowe, ale ZERO tabeli w bazie i ZERO konsumentow. Zmierzone tego dnia:
# `grep -rn wiedza silnik/ api/` dawalo jedno trafienie i bylo nim slowo
# w komentarzu. Skutek dla czlowieka: zatwierdzenie stawki nie zmienialoby
# zadnej liczby na ekranie, bo nie bylo gdzie jej zapisac.
#
# CZEGO TA ZMIANA NIE ROBI, POWIEDZIANE WPROST. Silnik NADAL liczy
# z `silnik/rdzen/stawki.py` — 28 stalych. Rejestr ma od dzis dane i nie ma
# konsumenta liczacego. PROG DOMKNIECIA: przy pierwszej zmianie ktorejkolwiek
# wartosci w `silnik/rdzen/stawki.py` albo w `wiedza/stawki_poczatkowe.py`
# — bo wtedy dwa nosniki tej samej liczby zaczna sie rozjezdzac, a rozjazd
# wyjdzie na jaw dopiero w kwocie przelewu. Pilnuje tego
# `testy/test_rejestr_sqlite.py::test_rejestr_MA_dane_i_NIE_MA_konsumenta`.

def zasiej_rejestr_stawek(polaczenie) -> int:
    """Wsiewa zasilenie poczatkowe rejestru. Zwraca liczbe faktycznie dodanych.

    WSZYSTKO WCHODZI JAKO `proponowana`. Nie ma tu galezi tworzacej wiersz
    `zatwierdzona` i to nie jest przeoczenie: przeniesienie liczby z pliku do
    tabeli nie jest jej sprawdzeniem, a `zatwierdzona` ma znaczyc „czlowiek to
    potwierdzil". Droga maszynowa do zatwierdzenia NIE ISTNIEJE (CLAUDE.md §3.4).

    IDEMPOTENCJA po trojce (klucz, obowiazuje_od, wartosc), bez statusu.
    Bez `status` swiadomie: po tym, jak Darek zatwierdzi stawke, jej status
    przestaje byc `proponowana` — warunek z `status` uznalby ja za nieobecna
    i wsialby propozycje jeszcze raz, obok tej samej wartosci juz podpisanej.
    """
    dodane = 0
    for s in stawki_poczatkowe.WSZYSTKIE:
        istnieje = polaczenie.execute(
            "SELECT 1 FROM rejestr_stawek "
            "WHERE klucz = ? AND obowiazuje_od = ? AND wartosc = ?",
            (s.klucz, s.obowiazuje_od.isoformat(), str(s.wartosc))).fetchone()
        if istnieje:
            continue
        polaczenie.execute(
            "INSERT INTO rejestr_stawek (klucz, wartosc, jednostka,"
            " obowiazuje_od, obowiazuje_do, podstawa_prawna, zrodlo_url,"
            " data_odczytu, status, zatwierdzil, data_zatwierdzenia,"
            " niezweryfikowane, opis) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (s.klucz, str(s.wartosc), s.jednostka, s.obowiazuje_od.isoformat(),
             None if s.obowiazuje_do is None else s.obowiazuje_do.isoformat(),
             s.podstawa_prawna, s.zrodlo_url, s.data_odczytu.isoformat(),
             s.status, s.zatwierdzil,
             None if s.data_zatwierdzenia is None
             else s.data_zatwierdzenia.isoformat(),
             s.niezweryfikowane, s.opis))
        dodane += 1
    polaczenie.commit()
    return dodane


def _stawka_z_wiersza(w) -> "rejestr_wiedzy.Stawka":
    """Wiersz bazy -> `Stawka`. Kwota przez `Decimal`, daty przez `date`.

    Konwersja tutaj, a nie u wolajacego: napis „0.1952" pomnozony przez
    podstawe daje w Pythonie blad typu, ale ten sam napis podany do `float()`
    daje liczbe zmiennoprzecinkowa i cisze — a to jest aplikacja podatkowa
    (CLAUDE.md §3.1).
    """
    return rejestr_wiedzy.Stawka(
        klucz=w[0], wartosc=Decimal(str(w[1])), jednostka=w[2],
        obowiazuje_od=date.fromisoformat(w[3]),
        obowiazuje_do=None if w[4] is None else date.fromisoformat(w[4]),
        podstawa_prawna=w[5], zrodlo_url=w[6],
        data_odczytu=date.fromisoformat(w[7]), status=w[8],
        zatwierdzil=w[9],
        data_zatwierdzenia=None if w[10] is None else date.fromisoformat(w[10]),
        niezweryfikowane=w[11], opis=w[12] or "")


def wczytaj_stawki(polaczenie, status: str | None = None) -> list:
    """Stawki z rejestru. Bez filtru — WSZYSTKIE, razem z propozycjami.

    Filtr `status` jest tu dla ekranu Ustawien, ktory pokazuje propozycje.
    Silnik ma wolac `wiedza.rejestr.obowiazujaca`, a nie filtrowac sam —
    tamta funkcja jest jedynym nosnikiem reguly „licz wylacznie
    z zatwierdzonych" i ma zostac jedynym.
    """
    sql = ("SELECT klucz, wartosc, jednostka, obowiazuje_od, obowiazuje_do,"
           " podstawa_prawna, zrodlo_url, data_odczytu, status, zatwierdzil,"
           " data_zatwierdzenia, niezweryfikowane, opis FROM rejestr_stawek")
    parametry: tuple = ()
    if status is not None:
        if status not in rejestr_wiedzy.STANY:
            raise BladMagazynu(
                f"Nieznany stan stawki: {status!r}. Dozwolone: "
                + ", ".join(rejestr_wiedzy.STANY) + ".")
        sql += " WHERE status = ?"
        parametry = (status,)
    sql += " ORDER BY klucz, obowiazuje_od"
    return [_stawka_z_wiersza(w)
            for w in polaczenie.execute(sql, parametry).fetchall()]


def policz_stawki(polaczenie) -> dict[str, int]:
    """Ile stawek w kazdym stanie. Slownik ma ZAWSZE wszystkie trzy klucze.

    Brakujacy klucz kazalby kazdemu wolajacemu pisac `.get(..., 0)` — czyli
    powtarzac decyzje „brak znaczy zero" w kazdym miejscu z osobna. Tu ta
    decyzja zapada raz.
    """
    wynik = {stan: 0 for stan in rejestr_wiedzy.STANY}
    for stan, ile in polaczenie.execute(
            "SELECT status, COUNT(*) FROM rejestr_stawek GROUP BY status"):
        wynik[stan] = ile
    return wynik


# --- wspólne pomocnicze ---------------------------------------------------

def _wymagaj_pkwiu(pkwiu: str) -> str:
    """Art. 12 ust. 3: ewidencja musi pozwalać przypisać przychód do rodzaju
    działalności. Bez PKWiU to nie jest ewidencja w rozumieniu przepisu."""
    if not str(pkwiu).strip():
        raise BladMagazynu(
            "Pole PKWiU jest wymagane i nie może być puste. Bez niego ewidencja "
            "nie pozwala przypisać przychodu do rodzaju działalności, a to jest "
            "ustawowy warunek stosowania różnych stawek (art. 12 ust. 3)."
        )
    return str(pkwiu).strip()


def _wymagaj_typu(typ: str) -> str:
    """Trzy dozwolone typy wpisu — jedyne miejsce, gdzie ta reguła jest sprawdzana."""
    if typ not in budzet.TYPY:
        raise BladMagazynu(
            f"Nieznany typ wpisu: {typ!r}. Dozwolone są wyłącznie: "
            + ", ".join(budzet.TYPY) + "."
        )
    return typ


def _wymagaj_kategorii(polaczenie, typ: str, kategoria: str) -> str:
    """Kategoria musi istnieć w słowniku, w TYM SAMYM typie, i być aktywna.

    Para (typ, nazwa), nie sama nazwa: `Inne` jest jednocześnie kategorią
    przychodu i wydatku, a to dwie różne pozycje budżetu.
    """
    kategoria = str(kategoria).strip()
    wiersz = polaczenie.execute(
        "SELECT aktywna FROM kategorie WHERE typ = ? AND nazwa = ?",
        (typ, kategoria)).fetchone()
    if wiersz is None:
        raise BladMagazynu(
            f"Kategoria {kategoria!r} nie istnieje w typie {typ!r}. Dodaj ją "
            "w zakładce Ustawienia albo wybierz jedną z istniejących."
        )
    if not wiersz[0]:
        raise BladMagazynu(
            f"Kategoria {kategoria!r} jest nieaktywna — nie przyjmuję do niej "
            "nowych wpisów. Przywróć ją w zakładce Ustawienia."
        )
    return kategoria


def _zapisz(polaczenie, sql: str, wartosci: tuple) -> int:
    try:
        kursor = polaczenie.execute(sql, wartosci)
        polaczenie.commit()
        return kursor.lastrowid
    except sqlite3.IntegrityError as e:
        if "numer_faktury" in str(e):
            raise BladMagazynu(
                f"Faktura o tym numerze już jest w bazie ({wartosci[1]}). "
                "Numery faktur muszą być niepowtarzalne."
            ) from e
        raise BladMagazynu(f"Zapis odrzucony przez bazę. Szczegół: {e}") from e
    except sqlite3.Error as e:
        raise BladMagazynu(f"Nie udało się zapisać danych. Szczegół: {e}") from e


def _wczytaj(polaczenie, tabela: str, warunek: str = "", parametry: tuple = ()) -> pd.DataFrame:
    try:
        df = pd.read_sql(f"SELECT * FROM {tabela} {warunek}", polaczenie,
                         params=parametry)
    except Exception as e:
        raise BladMagazynu(f"Nie udało się odczytać tabeli {tabela}. Szczegół: {e}") from e
    for kolumna in _KWOTOWE.get(tabela, []):
        if kolumna in df.columns:
            df[kolumna] = df[kolumna].map(lambda x: Decimal(str(x)) if x is not None else None)
    return df


# --- przychody ------------------------------------------------------------

def zapisz_fakture(polaczenie, *, data: date, numer_faktury: str,
                   kwota_netto: Decimal, stawka_vat: Decimal, kwota_vat: Decimal,
                   pkwiu: str, stawka_ryczaltu: Decimal, zaplacony_zus: Decimal,
                   zysk_netto: Decimal, stawki_wersja: str) -> int:
    pkwiu = _wymagaj_pkwiu(pkwiu)
    if not str(numer_faktury).strip():
        raise BladMagazynu("Numer faktury jest wymagany — bez niego nie odróżnisz "
                           "dwóch faktur wystawionych tego samego dnia.")
    return _zapisz(polaczenie,
        "INSERT INTO przychody_jdg (data, numer_faktury, kwota_netto, stawka_vat,"
        " kwota_vat, pkwiu, stawka_ryczaltu, zaplacony_zus, zysk_netto, stawki_wersja)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (data.isoformat(), str(numer_faktury).strip(), str(kwota_netto),
         str(stawka_vat), str(kwota_vat), pkwiu, str(stawka_ryczaltu),
         str(zaplacony_zus), str(zysk_netto), stawki_wersja))


def wczytaj_faktury(polaczenie, od: date | None = None, do: date | None = None) -> pd.DataFrame:
    if od and do:
        return _wczytaj(polaczenie, "przychody_jdg",
                        "WHERE data >= ? AND data <= ? ORDER BY data, id",
                        (od.isoformat(), do.isoformat()))
    return _wczytaj(polaczenie, "przychody_jdg", "ORDER BY data, id")


def czy_skladki_naliczone_w_miesiacu(polaczenie, rok: int, miesiac: int) -> bool:
    """Czy w tym miesiącu któraś faktura odłożyła już rezerwę na ZUS.

    Faktura z zerowym ZUS-em NIE ustawia tej flagi — to właśnie druga faktura
    w miesiącu, która składek już nie nalicza.
    """
    prefiks = f"{rok:04d}-{miesiac:02d}"
    df = _wczytaj(polaczenie, "przychody_jdg", "WHERE data LIKE ?", (prefiks + "%",))
    if df.empty:
        return False
    return bool((df["zaplacony_zus"] > Decimal("0")).any())


def przychod_narastajaco(polaczenie, rok: int) -> Decimal:
    """Suma przychodów netto od początku roku — podstawa ustalenia progu zdrowotnej."""
    df = _wczytaj(polaczenie, "przychody_jdg", "WHERE data LIKE ?", (f"{rok:04d}-%",))
    if df.empty:
        return Decimal("0.00")
    return sum(df["kwota_netto"], Decimal("0.00"))


# --- godziny --------------------------------------------------------------

def zapisz_godziny(polaczenie, *, data: date, rodzaj_czynnosci: str, pkwiu: str,
                   liczba_godzin: Decimal, opis: str = "") -> int:
    pkwiu = _wymagaj_pkwiu(pkwiu)
    return _zapisz(polaczenie,
        "INSERT INTO godziny (data, rodzaj_czynnosci, pkwiu, liczba_godzin, opis)"
        " VALUES (?,?,?,?,?)",
        (data.isoformat(), rodzaj_czynnosci, pkwiu, str(liczba_godzin), opis))


def wczytaj_godziny(polaczenie, od: date | None = None, do: date | None = None) -> pd.DataFrame:
    if od and do:
        return _wczytaj(polaczenie, "godziny",
                        "WHERE data >= ? AND data <= ? ORDER BY data, id",
                        (od.isoformat(), do.isoformat()))
    return _wczytaj(polaczenie, "godziny", "ORDER BY data, id")


# --- wpisy budżetu --------------------------------------------------------

def zapisz_wpis(polaczenie, *, data: date, typ: str, kategoria: str,
                kwota: Decimal, szczegoly: str = "") -> int:
    """Jeden wpis budżetu. Kwota zawsze DODATNIA — znak niesie `typ`.

    Gdyby znak siedział w kwocie, każde zestawienie musiałoby zgadywać, czy
    liczba jest już ze znakiem, czy jeszcze nie.
    """
    typ = _wymagaj_typu(typ)
    kategoria = _wymagaj_kategorii(polaczenie, typ, kategoria)
    if Decimal(str(kwota)) < 0:
        raise BladMagazynu(
            f"Kwota wpisu nie może być ujemna ({kwota}). Kierunek wynika "
            f"z typu wpisu, nie ze znaku liczby.")
    return _zapisz(polaczenie,
        "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, szczegoly)"
        " VALUES (?,?,?,?,?)",
        (data.isoformat(), typ, kategoria, str(kwota), szczegoly))


def wczytaj_wpisy(polaczenie, *, od: date | None = None, do: date | None = None,
                  typ: str | None = None) -> pd.DataFrame:
    """Wpisy budżetu, z opcjonalnym filtrem po zakresie dat i po typie.

    Filtr `typ` jest tu nie dla wygody: po wchłonięciu starej tabeli wydatków
    ta jedna tabela trzyma przychody, wydatki i oszczędności naraz. Sumowanie
    jej bez filtru daje liczbę, która wygląda jak wydatki i nią nie jest.
    """
    warunki, parametry = [], []
    if od is not None:
        warunki.append("data >= ?")
        parametry.append(od.isoformat())
    if do is not None:
        warunki.append("data <= ?")
        parametry.append(do.isoformat())
    if typ is not None:
        warunki.append("typ = ?")
        parametry.append(_wymagaj_typu(typ))
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "wpisy_budzetu",
                    f"{gdzie} ORDER BY data, id", tuple(parametry))


def usun_wpis(polaczenie, *, wpis_id: int) -> None:
    """Kasuje JEDEN wpis budżetu, po identyfikatorze.

    Bez tego pomyłkowo wpisana kwota zostaje w bazie na zawsze i psuje każde
    zestawienie, w którym się pojawia. Brak wiersza o podanym numerze jest
    błędem, nie cichą zgodą — inaczej pomyłka w numerze wygląda jak sukces.
    """
    kursor = polaczenie.execute("DELETE FROM wpisy_budzetu WHERE id = ?",
                                (int(wpis_id),))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma wpisu o numerze {wpis_id} — nic nie skasowałem.")
    polaczenie.commit()


def zmien_wpis(polaczenie, *, wpis_id: int, data: date, typ: str,
               kategoria: str, kwota: Decimal, szczegoly: str = "") -> None:
    """Poprawia istniejacy wpis W MIEJSCU — nie kasuje i nie tworzy nowego.

    Kasowanie z ponownym zapisem zmienialoby numer wpisu, a numer jest
    kluczem zaznaczenia w tabeli historii: uzytkownik poprawilby kwote
    i stracil zaznaczenie wiersza, ktory wlasnie edytowal.

    Walidacja jest ta sama co przy zapisie i z tego samego powodu: wpis
    poprawiony omijajacy slownik kategorii byloby furtka wokol reguly,
    ktorej `zapisz_wpis` pilnuje od poczatku.
    """
    typ = _wymagaj_typu(typ)
    kategoria = _wymagaj_kategorii(polaczenie, typ, kategoria)
    if Decimal(str(kwota)) < 0:
        raise BladMagazynu(
            f"Kwota wpisu nie może być ujemna ({kwota}). Kierunek wynika "
            f"z typu wpisu, nie ze znaku liczby.")
    kursor = polaczenie.execute(
        "UPDATE wpisy_budzetu SET data = ?, typ = ?, kategoria = ?, "
        "kwota = ?, szczegoly = ? WHERE id = ?",
        (data.isoformat(), typ, kategoria, str(kwota), szczegoly,
         int(wpis_id)))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma wpisu o numerze {wpis_id} — nic nie zmieniłem.")
    polaczenie.commit()


# --- plan budżetu ---------------------------------------------------------

def zapisz_plan(polaczenie, *, rok: int, miesiac: int, typ: str, kategoria: str,
                kwota_planowana: Decimal, opis: str = "", dzien=None,
                powtarzalna: int = 0, co_ile_miesiecy: int = 1) -> str:
    """Plan na jeden miesiąc i jedną kategorię. Powtórny zapis NADPISUJE.

    Zwraca „nowa" albo „nadpisana" — zachowanie bez zmian, ale wołający ma
    prawo wiedzieć, że coś zastąpił. Import ten wynik ignoruje; interfejs nie,
    bo cicha podmiana z komunikatem sukcesu kosztowała Darka ratę kredytu
    (2026-08-26).

    Więz `UNIQUE(rok, miesiac, typ, kategoria)` jest tu właściwym nośnikiem,
    bo to niezmiennik składowania (jeden plan na pozycję), a nie reguła
    produktowa — i czyni ponowny import planu bezpiecznym.
    """
    typ = _wymagaj_typu(typ)
    kategoria = str(kategoria).strip()
    opis = str(opis or "").strip()
    dzien = _wymagaj_dnia(dzien)
    co_ile_miesiecy = _wymagaj_cyklu(co_ile_miesiecy)
    istnieje = polaczenie.execute(
        "SELECT 1 FROM plan_budzetu WHERE rok = ? AND miesiac = ? "
        "AND typ = ? AND kategoria = ? AND opis = ?",
        (int(rok), int(miesiac), typ, kategoria, opis)).fetchone()
    try:
        polaczenie.execute(
            "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria,"
            " kwota_planowana, opis, dzien, powtarzalna, co_ile_miesiecy)"
            " VALUES (?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(rok, miesiac, typ, kategoria, opis)"
            " DO UPDATE SET kwota_planowana = excluded.kwota_planowana,"
            " dzien = excluded.dzien, powtarzalna = excluded.powtarzalna,"
            " co_ile_miesiecy = excluded.co_ile_miesiecy",
            (rok, miesiac, typ, kategoria, str(kwota_planowana), opis, dzien,
             int(powtarzalna), co_ile_miesiecy))
        polaczenie.commit()
    except sqlite3.Error as e:
        raise BladMagazynu(f"Nie udało się zapisać planu. Szczegół: {e}") from e
    return "nadpisana" if istnieje else "nowa"


def usun_plan(polaczenie, *, rok: int, miesiac: int, typ: str,
              kategoria: str, opis: str = "") -> None:
    """Kasuje JEDNA pozycje planu, wskazana pelna czworka.

    Czworka, nie sama kategoria: ta sama kategoria wystepuje w kazdym
    miesiacu, wiec kasowanie po nazwie zabraloby plan z calego roku przy
    jednym klknieciu. Brak wiersza jest bledem, nie cicha zgoda — inaczej
    pomylka w miesiacu wyglada jak sukces.
    """
    typ = _wymagaj_typu(typ)
    kursor = polaczenie.execute(
        "DELETE FROM plan_budzetu WHERE rok = ? AND miesiac = ? "
        "AND typ = ? AND kategoria = ? AND opis = ?",
        (int(rok), int(miesiac), typ, str(kategoria).strip(),
         str(opis or "").strip()))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma pozycji planu {kategoria!r} ({typ}) na "
            f"{int(rok):04d}-{int(miesiac):02d} — nic nie skasowałem.")
    polaczenie.commit()


def _wymagaj_dnia(dzien):
    """Dzień miesiąca albo nic. 32. dnia miesiąca nie ma.

    Dzień większy niż długość miesiąca (np. 31 w lutym) jest dopuszczalny
    i znaczy „ostatni dzień" — inaczej rachunek płatny 31. trzeba by wpisywać
    dwa razy, raz dla lutego.
    """
    if dzien in (None, ""):
        return None
    numer = int(dzien)
    if not 1 <= numer <= 31:
        raise BladMagazynu(
            f"Nie ma takiego dnia miesiąca ({dzien}). Podaj liczbę 1–31 "
            f"albo zostaw puste.")
    return numer


def _wymagaj_cyklu(co_ile) -> int:
    """Co ile miesięcy pozycja wraca. 1 = co miesiąc, 2 = co drugi."""
    # `co_ile or 1` zamienialoby ZERO w jedynke i walidacja nigdy by go nie
    # zobaczyla — stad jawne sprawdzenie pustki zamiast falszywosci.
    numer = 1 if co_ile in (None, "") else int(co_ile)
    if numer < 1:
        raise BladMagazynu(
            f"Cykl nie może być krótszy niż jeden miesiąc (podano {co_ile}).")
    return numer


def _obowiazujaca_regula(polaczenie, *, rok: int, miesiac: int, typ: str,
                         kategoria: str, opis: str = ""):
    """Wiersz planu obowiazujacy w miesiacu M dla pozycji (typ, kategoria, opis).

    Ten sam wybor co `budzet.plan_na_miesiac`, tylko w SQL — bo magazyn musi
    znac `id` wiersza, zeby go zamknac albo skasowac, a rozwijacz zwraca
    ramke do czytania. Regula rozstrzygania jest jedna i mieszka w module
    budzetu; tu jest jej zapytanie, nie druga wersja.

    `rok * 12 + miesiac - 1` to ta sama os absolutna co w rozwijaczu — bez niej
    listopad 2026 nie obowiazywalby w styczniu 2027.
    """
    punkt = int(rok) * 12 + (int(miesiac) - 1)
    return polaczenie.execute(
        "SELECT id, rok, miesiac, powtarzalna, co_ile_miesiecy "
        "FROM plan_budzetu "
        "WHERE typ = ? AND kategoria = ? AND opis = ? "
        "AND rok * 12 + miesiac - 1 <= ? "
        "AND (powtarzalna = 1 OR rok * 12 + miesiac - 1 = ?) "
        "AND (powtarzalna = 0 OR do_roku IS NULL "
        "     OR do_roku * 12 + do_miesiaca - 1 >= ?) "
        "AND (powtarzalna = 0 "
        "     OR (? - (rok * 12 + miesiac - 1)) % co_ile_miesiecy = 0) "
        "ORDER BY rok * 12 + miesiac - 1 DESC LIMIT 1",
        (typ, str(kategoria).strip(), str(opis or "").strip(),
         punkt, punkt, punkt, punkt)).fetchone()


def _miesiac_wczesniej(rok: int, miesiac: int) -> tuple[int, int]:
    """`M − 1` na osi absolutnej: styczen 2027 daje grudzien 2026."""
    poprzedni = int(rok) * 12 + (int(miesiac) - 1) - 1
    return poprzedni // 12, poprzedni % 12 + 1


def ustal_regule_planu(polaczenie, *, rok: int, miesiac: int, typ: str,
                       kategoria: str, kwota_planowana: Decimal,
                       opis: str = "", dzien=None,
                       co_ile_miesiecy: int = 1) -> str:
    """Ustawia pozycje planu obowiazujaca OD miesiaca M do odwolania.

    Zwraca napis mowiacy, CO SIE STALO — „nowa", „zaktualizowana" albo
    „zwersjonowana" — a nie wartosc logiczna. Wolajacy (i test) musza
    odroznic zmiane kwoty od zalozenia nowej reguly, bo komunikat dla Darka
    jest w kazdym z tych przypadkow inny.

    Trzy przypadki, wszystkie wynikajace z decyzji nr 3 Darka („zmiana dziala
    od wskazanego miesiaca w przod"):
    - nic nie obowiazuje w M -> nowa regula od M;
    - obowiazujaca startuje DOKLADNIE w M -> zmiana kwoty w miejscu;
    - obowiazujaca startuje WCZESNIEJ -> zamkniecie jej na M−1 i nowy wiersz
      od M. Nadpisanie kwoty w starym wierszu zmienialoby takze miesiace
      zamkniete, ktorych Darek juz nie oglada.
    """
    typ = _wymagaj_typu(typ)
    kategoria = str(kategoria).strip()
    opis = str(opis or "").strip()
    dzien = _wymagaj_dnia(dzien)
    co_ile_miesiecy = _wymagaj_cyklu(co_ile_miesiecy)
    obowiazujaca = _obowiazujaca_regula(polaczenie, rok=rok, miesiac=miesiac,
                                        typ=typ, kategoria=kategoria,
                                        opis=opis)
    wstaw = ("INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
             "kwota_planowana, powtarzalna, opis, dzien, co_ile_miesiecy) "
             "VALUES (?,?,?,?,?,1,?,?,?)")
    dane = (int(rok), int(miesiac), typ, kategoria, str(kwota_planowana),
            opis, dzien, co_ile_miesiecy)
    try:
        if obowiazujaca is None:
            polaczenie.execute(wstaw, dane)
            wynik = "nowa"
        elif (obowiazujaca[1], obowiazujaca[2]) == (int(rok), int(miesiac)):
            polaczenie.execute(
                "UPDATE plan_budzetu SET kwota_planowana = ?, powtarzalna = 1, "
                "do_roku = NULL, do_miesiaca = NULL, dzien = ?, "
                "co_ile_miesiecy = ? WHERE id = ?",
                (str(kwota_planowana), dzien, co_ile_miesiecy,
                 obowiazujaca[0]))
            wynik = "zaktualizowana"
        else:
            do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
            polaczenie.execute(
                "UPDATE plan_budzetu SET do_roku = ?, do_miesiaca = ? "
                "WHERE id = ?", (do_roku, do_miesiaca, obowiazujaca[0]))
            polaczenie.execute(wstaw, dane)
            wynik = "zwersjonowana"
        polaczenie.commit()
        return wynik
    except sqlite3.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie udało się ustalić reguły planu. Szczegół: {e}") from e


#: Co znaczy klikniecie kosza przy pozycji powtarzalnej. Dwie odpowiedzi,
#: bo to dwie rozne czynnosci: „pomylilem sie w tym miesiacu" i „ta pozycja
#: juz mnie nie dotyczy".
ZAKRES_TEN_I_NASTEPNE = "ten_i_nastepne"
ZAKRES_TYLKO_TEN = "tylko_ten"
ZAKRESY_KASOWANIA = (ZAKRES_TEN_I_NASTEPNE, ZAKRES_TYLKO_TEN)


def _nastepne_wystapienie(rok: int, miesiac: int, co_ile: int) -> tuple[int, int]:
    """Miesiac, w ktorym pozycja wraca po pominieciu jednego wystapienia.

    `+ co_ile`, nie `+ 1`: rachunek co dwa miesiace po pominieciu wraca po
    DWOCH miesiacach. Inaczej pominiecie przestawialoby caly rytm.
    """
    punkt = int(rok) * 12 + (int(miesiac) - 1) + max(int(co_ile), 1)
    return punkt // 12, punkt % 12 + 1


def zakoncz_plan(polaczenie, *, rok: int, miesiac: int, typ: str,
                 kategoria: str, opis: str = "",
                 zakres: str = ZAKRES_TEN_I_NASTEPNE) -> str:
    """Konczy pozycje planu OD miesiaca M — kosz w oknie miesiaca M.

    Zwraca „skasowana" albo „zamknieta", bo to dwie rozne rzeczy: pozycja
    zalozona w tym miesiacu znika bez sladu, a regula ciagnaca sie z wczesniej
    zostaje w bazie zamknieta na M−1 i nadal obowiazuje w przeszlosci.

    Brak obowiazujacej reguly jest bledem, nie cicha zgoda — inaczej pomylka
    w miesiacu wyglada jak sukces, dokladnie jak w `usun_plan`.
    """
    typ = _wymagaj_typu(typ)
    kategoria = str(kategoria).strip()
    opis = str(opis or "").strip()
    obowiazujaca = _obowiazujaca_regula(polaczenie, rok=rok, miesiac=miesiac,
                                        typ=typ, kategoria=kategoria,
                                        opis=opis)
    if zakres not in ZAKRESY_KASOWANIA:
        raise BladMagazynu(
            f"Nieznany zakres kasowania: {zakres!r}. Dostępne: "
            + ", ".join(ZAKRESY_KASOWANIA) + ".")
    if obowiazujaca is None:
        raise BladMagazynu(
            f"Nie ma pozycji planu {(opis or kategoria)!r} ({typ}) "
            f"obowiązującej na {int(rok):04d}-{int(miesiac):02d} — "
            f"nic nie zakończyłem.")

    numer, start_rok, start_miesiac, powtarzalna, co_ile = obowiazujaca
    zaczyna_sie_tutaj = (start_rok, start_miesiac) == (int(rok), int(miesiac))

    if zakres == ZAKRES_TYLKO_TEN and powtarzalna:
        # Pominiecie JEDNEGO wystapienia wyrazamy istniejacymi kolumnami:
        # regula konczy sie przed tym miesiacem, a nowa zaczyna od nastepnego
        # wystapienia w cyklu. Zadnej tabeli wyjatkow — mniej pojec i te same
        # strazniki co przy zmianie kwoty od miesiaca.
        wraca_rok, wraca_miesiac = _nastepne_wystapienie(rok, miesiac, co_ile)
        wiersz = polaczenie.execute(
            "SELECT kwota_planowana, dzien, do_roku, do_miesiaca "
            "FROM plan_budzetu WHERE id = ?", (numer,)).fetchone()
        if zaczyna_sie_tutaj:
            polaczenie.execute(
                "UPDATE plan_budzetu SET rok = ?, miesiac = ? WHERE id = ?",
                (wraca_rok, wraca_miesiac, numer))
        else:
            do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
            polaczenie.execute(
                "UPDATE plan_budzetu SET do_roku = ?, do_miesiaca = ? "
                "WHERE id = ?", (do_roku, do_miesiaca, numer))
            polaczenie.execute(
                "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
                "kwota_planowana, powtarzalna, opis, dzien, co_ile_miesiecy, "
                "do_roku, do_miesiaca) VALUES (?,?,?,?,?,1,?,?,?,?,?)",
                (wraca_rok, wraca_miesiac, typ, kategoria, wiersz[0], opis,
                 wiersz[1], co_ile, wiersz[2], wiersz[3]))
        polaczenie.commit()
        return "pominieta"

    if zaczyna_sie_tutaj or not powtarzalna:
        polaczenie.execute("DELETE FROM plan_budzetu WHERE id = ?", (numer,))
        wynik = "skasowana"
    else:
        do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
        polaczenie.execute(
            "UPDATE plan_budzetu SET do_roku = ?, do_miesiaca = ? WHERE id = ?",
            (do_roku, do_miesiaca, numer))
        wynik = "zamknieta"
    polaczenie.commit()
    return wynik


def kopiuj_plan(polaczenie, *, z_roku: int, z_miesiaca: int,
                do_roku: int, do_miesiaca: int) -> tuple[int, int]:
    """Przenosi pozycje planu na inny miesiac. Zwraca (skopiowane, pominiete).

    NIE nadpisuje pozycji juz istniejacych w miesiacu docelowym — reczna
    poprawka jest cenniejsza niz kopia.

    Dwie liczby zamiast jednej, bo "skopiowano 12" nie odroznia pelnego
    przeniesienia od takiego, ktore ominelo polowe pozycji. Sprawdzenie,
    do ktorego nic nie dociera, melduje sukces.
    """
    zrodlo = polaczenie.execute(
        "SELECT typ, kategoria, kwota_planowana FROM plan_budzetu "
        "WHERE rok = ? AND miesiac = ?",
        (int(z_roku), int(z_miesiaca))).fetchall()
    skopiowane = pominiete = 0
    for typ, kategoria, kwota in zrodlo:
        istnieje = polaczenie.execute(
            "SELECT 1 FROM plan_budzetu WHERE rok = ? AND miesiac = ? "
            "AND typ = ? AND kategoria = ?",
            (int(do_roku), int(do_miesiaca), typ, kategoria)).fetchone()
        if istnieje:
            pominiete += 1
            continue
        polaczenie.execute(
            "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
            "kwota_planowana) VALUES (?,?,?,?,?)",
            (int(do_roku), int(do_miesiaca), typ, kategoria, kwota))
        skopiowane += 1
    polaczenie.commit()
    return skopiowane, pominiete


def wczytaj_plan(polaczenie, rok: int | None = None,
                 miesiac: int | None = None) -> pd.DataFrame:
    warunki, parametry = [], []
    if rok is not None:
        warunki.append("rok = ?")
        parametry.append(rok)
    if miesiac is not None:
        warunki.append("miesiac = ?")
        parametry.append(miesiac)
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "plan_budzetu",
                    f"{gdzie} ORDER BY rok, miesiac, typ, kategoria",
                    tuple(parametry))


# --- słownik kategorii ----------------------------------------------------

def wczytaj_kategorie(polaczenie, typ: str | None = None,
                      tylko_aktywne: bool = False) -> pd.DataFrame:
    warunki, parametry = [], []
    if typ is not None:
        warunki.append("typ = ?")
        parametry.append(_wymagaj_typu(typ))
    if tylko_aktywne:
        warunki.append("aktywna = 1")
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "kategorie",
                    f"{gdzie} ORDER BY typ, kolejnosc, nazwa", tuple(parametry))


def dodaj_kategorie(polaczenie, *, typ: str, nazwa: str) -> int:
    typ = _wymagaj_typu(typ)
    nazwa = str(nazwa).strip()
    if not nazwa:
        raise BladMagazynu("Nazwa kategorii nie może być pusta.")
    istnieje = polaczenie.execute(
        "SELECT 1 FROM kategorie WHERE typ = ? AND nazwa = ?",
        (typ, nazwa)).fetchone()
    if istnieje:
        raise BladMagazynu(
            f"Kategoria {nazwa!r} już istnieje w typie {typ!r}.")
    kolejnosc = polaczenie.execute(
        "SELECT COALESCE(MAX(kolejnosc), -1) + 1 FROM kategorie WHERE typ = ?",
        (typ,)).fetchone()[0]
    return _zapisz(polaczenie,
        "INSERT INTO kategorie (typ, nazwa, kolejnosc, aktywna) VALUES (?,?,?,1)",
        (typ, nazwa, kolejnosc))


def zmien_nazwe_kategorii(polaczenie, *, typ: str, stara: str, nowa: str) -> int:
    """Zmienia nazwę w słowniku ORAZ we wpisach i w planie, w jednej transakcji.

    Podmiana wyłącznie w słowniku zostawiłaby wpisy wskazujące na kategorię,
    której już nie ma — wypadłyby ze wszystkich zestawień przy zielonej suicie.
    Zwraca liczbę przepisanych wpisów.
    """
    typ = _wymagaj_typu(typ)
    stara, nowa = str(stara).strip(), str(nowa).strip()
    if not nowa:
        raise BladMagazynu("Nowa nazwa kategorii nie może być pusta.")
    if polaczenie.execute("SELECT 1 FROM kategorie WHERE typ = ? AND nazwa = ?",
                          (typ, stara)).fetchone() is None:
        raise BladMagazynu(f"Kategoria {stara!r} nie istnieje w typie {typ!r}.")
    if stara != nowa and polaczenie.execute(
            "SELECT 1 FROM kategorie WHERE typ = ? AND nazwa = ?",
            (typ, nowa)).fetchone() is not None:
        raise BladMagazynu(
            f"Kategoria {nowa!r} już istnieje w typie {typ!r} — nazwy w obrębie "
            "typu muszą być niepowtarzalne.")
    try:
        polaczenie.execute(
            "UPDATE kategorie SET nazwa = ? WHERE typ = ? AND nazwa = ?",
            (nowa, typ, stara))
        kursor = polaczenie.execute(
            "UPDATE wpisy_budzetu SET kategoria = ? WHERE typ = ? AND kategoria = ?",
            (nowa, typ, stara))
        przepisane = kursor.rowcount
        polaczenie.execute(
            "UPDATE plan_budzetu SET kategoria = ? WHERE typ = ? AND kategoria = ?",
            (nowa, typ, stara))
        polaczenie.commit()
        return przepisane
    except sqlite3.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie udało się zmienić nazwy kategorii. Szczegół: {e}") from e


def ustaw_aktywnosc_kategorii(polaczenie, *, typ: str, nazwa: str,
                              aktywna: bool) -> None:
    """Dezaktywacja zamiast kasowania: kategoria znika z list wyboru, a wpisy
    i plan zostają nietknięte. Historia ma zostać prawdziwa."""
    typ = _wymagaj_typu(typ)
    kursor = polaczenie.execute(
        "UPDATE kategorie SET aktywna = ? WHERE typ = ? AND nazwa = ?",
        (1 if aktywna else 0, typ, str(nazwa).strip()))
    if kursor.rowcount == 0:
        raise BladMagazynu(f"Kategoria {nazwa!r} nie istnieje w typie {typ!r}.")
    polaczenie.commit()


def policz_wpisy_kategorii(polaczenie, *, typ: str, nazwa: str) -> int:
    return polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu WHERE typ = ? AND kategoria = ?",
        (_wymagaj_typu(typ), str(nazwa).strip())).fetchone()[0]


def usun_kategorie_trwale(polaczenie, *, typ: str, nazwa: str) -> None:
    """Kasuje wiersz słownika — wyłącznie gdy nie ma do niego ani jednego wpisu.

    Kategoria z historią nie znika nigdy; od tego jest dezaktywacja.
    """
    typ = _wymagaj_typu(typ)
    nazwa = str(nazwa).strip()
    ile = policz_wpisy_kategorii(polaczenie, typ=typ, nazwa=nazwa)
    if ile:
        raise BladMagazynu(
            f"Kategoria {nazwa!r} ma {ile} wpisów i nie zostanie skasowana — "
            "historia musi zostać prawdziwa. Użyj dezaktywacji: kategoria "
            "zniknie z list wyboru, a wpisy zostaną.")
    kursor = polaczenie.execute(
        "DELETE FROM kategorie WHERE typ = ? AND nazwa = ?", (typ, nazwa))
    if kursor.rowcount == 0:
        raise BladMagazynu(f"Kategoria {nazwa!r} nie istnieje w typie {typ!r}.")
    polaczenie.commit()


# --- cele oszczędnościowe -------------------------------------------------

def zapisz_cel(polaczenie, *, nazwa: str, kategoria: str,
               kwota_docelowa: Decimal, termin: date) -> int:
    """Cel musi wskazywać kategorię typu „Oszczędności".

    Cel wskazujący kategorię wydatku liczyłby postęp z pieniędzy **wydanych** —
    pasek pokazywałby, że zbierasz na wakacje, im więcej wydajesz na zakupy.
    """
    kategoria = _wymagaj_kategorii(polaczenie, budzet.TYP_OSZCZEDNOSCI, kategoria)
    nazwa = str(nazwa).strip()
    if not nazwa:
        raise BladMagazynu("Nazwa celu jest wymagana.")
    if Decimal(str(kwota_docelowa)) <= 0:
        raise BladMagazynu(
            f"Kwota docelowa musi być dodatnia (podano {kwota_docelowa}).")
    if polaczenie.execute("SELECT 1 FROM cele_oszczednosciowe WHERE nazwa = ?",
                          (nazwa,)).fetchone():
        raise BladMagazynu(f"Cel o nazwie {nazwa!r} już istnieje.")
    return _zapisz(polaczenie,
        "INSERT INTO cele_oszczednosciowe (nazwa, kategoria, kwota_docelowa, termin)"
        " VALUES (?,?,?,?)",
        (nazwa, kategoria, str(kwota_docelowa), termin.isoformat()))


def wczytaj_cele(polaczenie) -> pd.DataFrame:
    return _wczytaj(polaczenie, "cele_oszczednosciowe", "ORDER BY termin, nazwa")


def usun_cel(polaczenie, *, cel_id: int) -> None:
    kursor = polaczenie.execute(
        "DELETE FROM cele_oszczednosciowe WHERE id = ?", (int(cel_id),))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(f"Nie ma celu o numerze {cel_id} — nic nie skasowałem.")
    polaczenie.commit()


# --- ustawienia -----------------------------------------------------------

def ustaw_ustawienie(polaczenie, klucz: str, wartosc: str) -> None:
    try:
        polaczenie.execute(
            "INSERT INTO ustawienia (klucz, wartosc) VALUES (?,?)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc",
            (str(klucz), str(wartosc)))
        polaczenie.commit()
    except sqlite3.Error as e:
        raise BladMagazynu(f"Nie udało się zapisać ustawienia. Szczegół: {e}") from e


@dataclass(frozen=True)
class FormaRoku:
    """Forma opodatkowania obowiazujaca w danym roku — jeden z TRZECH stanow."""

    rok: int
    forma: str
    stawka_ryczaltu: Decimal | None


def zapisz_forme(polaczenie, *, rok: int, forma: str,
                 stawka_ryczaltu: "Decimal | str | None" = None) -> None:
    """Zapisuje wybor formy na rok. Forma spoza zbioru jest BLEDEM.

    Cichy zapis nieznanej formy dalby stan, ktorego silnik nie umie obsluzyc —
    i wyszlo by to dopiero przy liczeniu, czyli daleko od miejsca wpadki.
    """
    if forma not in FORMY_ZAPISYWALNE:
        raise BladMagazynu(
            f"Nieznana forma opodatkowania: {forma!r}. Dozwolone: "
            + ", ".join(FORMY_ZAPISYWALNE)
            + f". Stan {FORMA_NIEROZSTRZYGNIETA!r} powstaje z BRAKU wpisu "
              "i nie zapisuje sie go jawnie.")
    if forma == FORMA_RYCZALT and stawka_ryczaltu is None:
        raise BladMagazynu(
            "Ryczalt bez stawki to forma, ktorej nie da sie policzyc. "
            "Podaj stawke ryczaltu.")
    if forma != FORMA_RYCZALT and stawka_ryczaltu is not None:
        raise BladMagazynu(
            f"Stawka ryczaltu nie ma znaczenia przy formie {forma!r}. "
            "Zapisana zostalaby polem, ktore ktos pozniej przeczyta "
            "i uzna za obowiazujace.")
    try:
        polaczenie.execute(
            "INSERT INTO forma_opodatkowania (rok, forma, stawka_ryczaltu)"
            " VALUES (?,?,?)"
            " ON CONFLICT(rok) DO UPDATE SET forma = excluded.forma,"
            " stawka_ryczaltu = excluded.stawka_ryczaltu",
            (int(rok), forma,
             None if stawka_ryczaltu is None else str(stawka_ryczaltu)))
        polaczenie.commit()
    except sqlite3.Error as e:
        raise BladMagazynu(
            f"Nie udalo sie zapisac formy opodatkowania. Szczegol: {e}") from e


def forma_na_rok(polaczenie, rok: int) -> FormaRoku:
    """Forma obowiazujaca w danym roku — TRZY stany (decyzja D8).

    Brak wpisu daje `NIEROZSTRZYGNIETA`, a **nie** ryczalt ani skale. Dwie
    kolejne wersje planu zgadywaly tu wartosc domyslna — v0.2 ryczalt, v0.3
    skale — i obie sie mylily, tylko w przeciwne strony. Aplikacja formy
    sprzed zawieszenia dzialalnosci NIE ZNA i nie ma jej skad wziac.

    Precedens we wlasnym kodzie: `weryfikacja.sprawdz` przy wyniku ROZBIEZNE
    blokuje formularz faktury zamiast liczyc z niepewnych stawek.
    """
    wiersz = polaczenie.execute(
        "SELECT forma, stawka_ryczaltu FROM forma_opodatkowania WHERE rok = ?",
        (int(rok),)).fetchone()
    if wiersz is None:
        return FormaRoku(rok=int(rok), forma=FORMA_NIEROZSTRZYGNIETA,
                         stawka_ryczaltu=None)
    forma, stawka = wiersz
    if forma not in FORMY_ZAPISYWALNE:
        raise BladMagazynu(
            f"W bazie stoi nieznana forma opodatkowania na rok {rok}: "
            f"{forma!r}. Popraw ja w Ustawieniach. Nie zgaduje, bo stan "
            f"'mam zla forme' i stan 'nie mam formy' to dwie rozne rzeczy.")
    return FormaRoku(rok=int(rok), forma=forma,
                     stawka_ryczaltu=None if stawka is None else Decimal(stawka))


def zapisz_dzialalnosc_od(polaczenie, od: date) -> None:
    """Zapisuje date rozpoczecia dzialalnosci w formacie ISO (RRRR-MM-DD)."""
    ustaw_ustawienie(polaczenie, KLUCZ_DZIALALNOSC_OD, date.fromisoformat(
        od.isoformat() if isinstance(od, date) else str(od)).isoformat())


def odczytaj_dzialalnosc_od(polaczenie) -> "date | None":
    """Data rozpoczecia dzialalnosci albo `None`, gdy nikt jej nie podal.

    `None` znaczy „NIE WIEM", nie „zero miesiecy". Zero zamienilo by brak
    wiedzy w rezerwe ZUS rowna zeru — czyli w najlepszy mozliwy stan pokazany
    wtedy, gdy nie wiadomo nic. Ta sama regula co D11.

    Wpis uszkodzony jest BLEDEM, nie cichym brakiem: „mam zla date" i „nie mam
    daty" to dwa rozne stany i drugi z nich milczy zamiast krzyczec.
    """
    surowa = odczytaj_ustawienie(polaczenie, KLUCZ_DZIALALNOSC_OD)
    if surowa is None:
        return None
    try:
        return date.fromisoformat(surowa)
    except ValueError as e:
        raise BladMagazynu(
            f"Data rozpoczecia dzialalnosci zapisana w bazie jest nieczytelna: "
            f"{surowa!r}. Oczekiwany format to RRRR-MM-DD. Popraw ja "
            f"w Ustawieniach. Szczegol: {e}") from e


def zapisz_ustawienia_prognozy(polaczenie, *, ostrozny, realny,
                               stawka) -> None:
    """Nastawy prognozy. `None` zapisuje sie jako PUSTY NAPIS, nie kasuje wpisu.

    Rozroznienie jest cala trescia R17: **brak wpisu** znaczy „jeszcze nie
    decydowalem" i bierze wartosc startowa; **pusty wpis** znaczy „nie uznaje
    zadnego wolumenu za pewny" i prognoza wtedy ODMAWIA obu linii. Skasowanie
    wpisu zamienialoby drugi stan w pierwszy — czyli ciche przywrocenie
    wartosci, ktora uzytkownik wlasnie odrzucil.
    """
    for klucz, wartosc in ((KLUCZ_WOLUMEN_OSTROZNY, ostrozny),
                           (KLUCZ_WOLUMEN_REALNY, realny),
                           (KLUCZ_STAWKA_GODZINOWA, stawka)):
        ustaw_ustawienie(polaczenie, klucz,
                         "" if wartosc is None else str(wartosc))


def odczytaj_liczbe_ustawienia(polaczenie, klucz: str,
                               domyslna: Decimal) -> "Decimal | None":
    """Nastawa liczbowa — JEDEN nosnik reguly „brak, pusto, albo liczba".

    Brak wpisu → `domyslna`. Pusty wpis → `None` (wyczyszczone swiadomie).
    Wpis nieliczbowy → BLAD: „mam zla wartosc" i „nie mam wartosci" to dwa
    rozne stany, a drugi z nich milczy zamiast krzyczec (ta sama regula co
    przy dacie rozpoczecia dzialalnosci, Z54).
    """
    surowa = odczytaj_ustawienie(polaczenie, klucz)
    if surowa is None:
        return Decimal(domyslna)
    if not str(surowa).strip():
        return None
    try:
        return Decimal(str(surowa).strip())
    except InvalidOperation as e:
        raise BladMagazynu(
            f"Nastawa {klucz!r} zapisana w bazie nie jest liczba: {surowa!r}. "
            f"Popraw ja w Ustawieniach. Szczegol: {e}") from e


def odczytaj_ustawienie(polaczenie, klucz: str,
                        domyslna: str | None = None) -> str | None:
    wiersz = polaczenie.execute(
        "SELECT wartosc FROM ustawienia WHERE klucz = ?", (str(klucz),)).fetchone()
    return wiersz[0] if wiersz else domyslna


# --- kotwica prognozy: stan konta ----------------------------------------

def _wymagaj_kwoty(kwota, co: str) -> Decimal:
    """Kwota, ktora WOLNO miec ujemna. Napis nieliczbowy jest bledem TUTAJ.

    Bez tego napis wchodzi do bazy jako TEXT, wraca przez `_KWOTOWE` i wysypuje
    sie dopiero przy liczeniu — czyli daleko od miejsca wpadki, w prognozie,
    ktora wygladalaby na policzona.
    """
    try:
        return Decimal(str(kwota))
    except (InvalidOperation, ValueError) as e:
        raise BladMagazynu(
            f"{co} musi byc kwota, a dostalem {kwota!r}. Podaj liczbe "
            f"(znak minus jest dozwolony).") from e


def zapisz_stan_konta(polaczenie, *, data: date, kwota: Decimal) -> None:
    """Odczyt stanu konta z danego dnia — kotwica prognozy (E7, R11).

    Kwota MOZE byc ujemna i jest jedyna taka w tej bazie. Konto na debecie to
    realny stan konta, a nie blad wpisu; `_wymagaj_nieujemnej` broni czego
    innego — tam kierunek niesie TYP pozycji, tu znak jest czescia odczytu.

    Ten sam dzien NADPISUJE: dwa stany konta na jedna date to nie historia,
    tylko sprzecznosc. Historia biegnie po dniach, nie po poprawkach.
    """
    kwota = _wymagaj_kwoty(kwota, "Stan konta")
    try:
        polaczenie.execute(
            "INSERT INTO stan_konta (data, kwota) VALUES (?,?)"
            " ON CONFLICT(data) DO UPDATE SET kwota = excluded.kwota",
            (data.isoformat(), str(kwota)))
        polaczenie.commit()
    except sqlite3.Error as e:
        raise BladMagazynu(
            f"Nie udalo sie zapisac stanu konta. Szczegol: {e}") from e


@dataclass(frozen=True)
class OdczytSalda:
    """Stan rachunku rozliczeniowego odczytany danego dnia.

    DATA JEST TU ISTOTNA I DLATEGO ODCZYT JEST ZRODLEM, a pozycja majatku
    pochodna. Os prognozy zaczyna sie od tej daty, a straznik swiezosci (R18)
    mowi „stan konta jest z dnia X". Pozycja majatku daty nie ma — gdyby to
    ona byla zrodlem, date trzeba by ZMYSLIC i prognoza udawalaby swiezosc.
    """

    data: date
    kwota: Decimal


def ostatni_odczyt_salda(polaczenie) -> "OdczytSalda | None":
    """Obowiazujacy odczyt salda — JEDEN nosnik reguly „najnowszy wygrywa".

    Wolaja to dwa miejsca: `prognoza_plynnosci.ostatnia_kotwica` (punkt startu
    osi) i `wczytaj_majatek` (wartosc rachunku rozliczeniowego). Gdyby kazde
    liczylo po swojemu, „najnowszy" znaczyloby dwie rozne rzeczy przy pierwszej
    zmianie sortowania.

    `None` znaczy „nie bylo zadnego odczytu" — nie zero.
    """
    historia = wczytaj_kotwice(polaczenie)
    if historia.empty:
        return None
    wiersz = historia.iloc[0]
    return OdczytSalda(data=date.fromisoformat(str(wiersz["data"])),
                       kwota=Decimal(str(wiersz["kwota"])))


def wczytaj_kotwice(polaczenie) -> pd.DataFrame:
    """Cala historia odczytow stanu konta, OD NAJNOWSZEGO.

    Kolejnosc jest regula, nie wygoda: pierwszy wiersz to kotwica
    obowiazujaca. Historia zostaje, bo kotwica z 1 sierpnia zestawiona
    z prognoza na 1 wrzesnia i kotwica z 1 wrzesnia to jedyny sposob,
    w jaki ta prognoza moze kiedykolwiek udowodnic, ze jest skalibrowana.
    """
    return _wczytaj(polaczenie, "stan_konta", "ORDER BY data DESC")


# --- przebiegi strażnika w tle --------------------------------------------

#: Pola przebiegu strażnika zadeklarowane w schemacie jako `NOT NULL`.
#: JEDEN NOŚNIK tej listy — i tym razem naprawdę (sprostowanie Z73p3).
#:
#: Pierwsza wersja trzymała tu **nazwy do komunikatu** („stan prognozy", ze
#: spacją), więc stała nie nadawała się do użycia w teście — i lista miała
#: TRZY nośniki: tę stałą, krotkę wartości sparowaną z nią pozycyjnie przez
#: `zip`, oraz literał w `testy/test_straznik.py`. Komentarz twierdził
#: „walidacja czyta, zamiast powtarzać"; walidacja czytała nazwy, a zbiór
#: walidowanych WARTOŚCI powtarzała.
#:
#: Nazwy są tu teraz **nazwami argumentów**, żeby test wołał tę stałą zamiast
#: przepisywać ją z podkreśleniami. Zdanie po polsku powstaje z nich przy
#: składaniu komunikatu (`_` → spacja), a nie odwrotnie.
POLA_PRZEBIEGU_WYMAGANE = ("stan_prognozy", "zrodla", "komunikat")

#: Nazwa stanu prognozy, przy ktorym — i WYLACZNIE przy ktorym — wolno
#: zapisac `pilnych=None`.
#:
#: SWIADOMY DRUGI NOSNIK, nazwany wprost. Nosnikiem tej nazwy jest
#: `prognoza_plynnosci.STAN_NIE_WIEM`; zawolac go stad NIE DA SIE, bo
#: `prognoza_plynnosci` importuje `magazyn` i import w druga strone bylby
#: cyklem. v1.17 dopuszcza drugi nosnik wylacznie ze straznikiem i progiem,
#: oba sa:
#:   * straznik: `test_STALA_nie_wiem_magazynu_ZGADZA_SIE_z_nosnikiem_prognozy`
#:     pada, gdy napisy sie rozjada (mutacja M411);
#:   * prog konsolidacji: gdy `prognoza_plynnosci` przestanie importowac
#:     `magazyn` albo nazwy stanow wyjda do trzeciego, wspolnego modulu —
#:     wtedy ta stala znika i zostaje wolanie.
STAN_PROGNOZY_NIE_WIEM = "nie_wiem"


def zapisz_przebieg_straznika(polaczenie, *, kiedy: datetime,
                              stan_prognozy: str,
                              pierwszy_dzien_ujemny: "date | None",
                              pilnych: "int | None", powod: "str | None",
                              zrodla: str,
                              komunikat: str, powiadomiono: bool) -> None:
    """Wynik jednego przebiegu strażnika w tle — JEDYNY zapis tego procesu.

    Klucz sztuczny, nie znacznik czasu: dwa przebiegi tej samej sekundy
    (przebieg z harmonogramu i przebieg uruchomiony ręcznie) muszą zostać
    dwoma wierszami. Klucz na `kiedy` zamieniłby je w jeden i pomiar „ile razy
    strażnik biegł" kłamałby, nie przestając odpowiadać.

    `powiadomiono` jest DOWODEM, nie ozdobą (§5.4): brak powiadomienia znaczy
    naraz „nic pilnego" i „nie zadziałałem", a te dwa stany wymagają innej
    reakcji.

    BEZ `str()` NA POLACH `NOT NULL`. Pierwsza wersja owijała `stan_prognozy`,
    `zrodla` i `komunikat` w `str()`, co **neutralizowało wiąz bazy**: `None`
    zapisywał się jako napis „None" — wiersz przechodził, a pasek na ekranie
    (Z77) pokazałby słowo „None" jako zdanie o stanie finansów. To gorsze niż
    cisza, bo **wygląda na odpowiedź**. Zamiast tego jawna odmowa z komunikatem
    po polsku; niech wołający dowie się, czego nie podał.

    `pilnych=None` ZNACZY „nie liczyłem" i zapisuje się jako `0` — świadomie,
    z jawną STRATĄ INFORMACJI. `CoMnieCzeka.pilnych` ma typ `int | None`,
    a kolumna jest `INTEGER NOT NULL`; rozróżnienie „nie liczyłem" od
    „policzyłem i jest zero" niesie **kolumna `stan_prognozy`**, nie ta.
    Bez tej konwersji `int(None)` wywracał zapis wyjątkiem, więc przy stanie
    „nie wiem" strażnik w tle nie zapisałby przebiegu **w ogóle** — a ekran
    pokazałby wtedy „NIGDY nie działał", czyli ostrzeżenie o czymś, co się
    nie stało, przy jednoczesnym braku ostrzeżenia o tym, co się stało.
    """
    # ODWZOROWANIE nazwa→wartość, nie dwie równoległe sekwencje. `zip` bez
    # `strict=True` skraca do krótszej **bez słowa**: czwarte pole `NOT NULL`
    # dopisane do stałej, a zapomniane w krotce wartości, dałoby walidację,
    # która to pole pomija — i strażnika, który tego nie zauważy. Brak wpisu
    # daje tutaj `KeyError`, czyli awarię głośną zamiast cichego pominięcia.
    # `pilnych=None` ZNACZY „nie liczylem" i wolno je zapisac jako `0`
    # TYLKO w parze ze stanem „nie wiem" — bo tylko wtedy rozroznienie,
    # ktore ginie w tej kolumnie, niesie kolumna obok. Kazda inna para jest
    # sprzecznoscia wolajacego: „nie liczylem, ale prognoza policzona".
    # Bez tej bramki `podpis_straznika` mowilby „nic pilnego nie znalazl"
    # o przebiegu, ktory niczego nie policzyl. Straznik:
    # `test_pilnych_None_przy_stanie_POLICZONA_to_ODMOWA_nie_ciche_zero`
    # (mutacja M410).
    if pilnych is None and stan_prognozy != STAN_PROGNOZY_NIE_WIEM:
        raise BladMagazynu(
            f"Nie zapisze przebiegu straznika: liczba pilnych pozycji nie "
            f"zostala policzona, a stan prognozy brzmi "
            f"„{str(stan_prognozy).replace('_', ' ')}”. Brak liczby "
            f"wolno zapisac jako zero tylko przy stanie „nie wiem”, "
            f"bo wtedy rozroznienie niesie druga kolumna. Inaczej pasek powie "
            f"„nic pilnego nie znalazl” o przebiegu, ktory nic "
            f"nie policzyl.")

    wartosci = {"stan_prognozy": stan_prognozy, "zrodla": zrodla,
                "komunikat": komunikat}
    for nazwa in POLA_PRZEBIEGU_WYMAGANE:
        if wartosci[nazwa] is None:
            raise BladMagazynu(
                f"Nie zapisze przebiegu straznika: brakuje wymaganego pola "
                f"{nazwa.replace('_', ' ')}. To pole jest wymagane, a zapisane "
                f"jako napis None trafiloby na pasek jako zdanie o stanie "
                f"finansow - falszywa odpowiedz jest gorsza od ciszy.")
    polaczenie.execute(
        "INSERT INTO przebiegi_straznika (kiedy, stan_prognozy, "
        "pierwszy_dzien_ujemny, pilnych, powod, zrodla, komunikat, "
        "powiadomiono) VALUES (?,?,?,?,?,?,?,?)",
        (kiedy.isoformat(timespec="seconds"), stan_prognozy,
         None if pierwszy_dzien_ujemny is None else pierwszy_dzien_ujemny.isoformat(),
         # `0 if ... is None`, NIE `pilnych or 0`. Zapis ma pokazywac, ze to
         # konwersja stanu „nie wiem", a nie zabezpieczenie przed wartoscia
         # falszywa — `or 0` zamieniloby przy okazji kazde inne zero
         # i czytelnik nie odroznilby intencji. Straznik:
         # `test_zapis_przy_stanie_NIE_WIEM_kladzie_ZERO_zamiast_wybuchac`
         # (mutacja M399).
         0 if pilnych is None else int(pilnych),
         powod, zrodla, komunikat, int(bool(powiadomiono))))
    polaczenie.commit()


def ostatni_przebieg_straznika(polaczenie) -> "dict | None":
    """Ostatni przebieg albo `None`. `None` znaczy „NIGDY nie działał" —
    nie „działał i nic nie znalazł". Zero wierszy to brak wiedzy, a brak
    wiedzy nie udaje dobrej wiadomości (reguła D11)."""
    wiersz = polaczenie.execute(
        "SELECT kiedy, stan_prognozy, pierwszy_dzien_ujemny, pilnych, powod, "
        "zrodla, komunikat, powiadomiono FROM przebiegi_straznika "
        "ORDER BY kiedy DESC, id DESC LIMIT 1").fetchone()
    if wiersz is None:
        return None
    return {"kiedy": wiersz[0], "stan_prognozy": wiersz[1],
            "pierwszy_dzien_ujemny": wiersz[2], "pilnych": int(wiersz[3]),
            "powod": wiersz[4], "zrodla": wiersz[5], "komunikat": wiersz[6],
            "powiadomiono": bool(wiersz[7])}


# --- zobowiązania i majątek -----------------------------------------------

def _wymagaj_nieujemnej(kwota: Decimal, co: str) -> Decimal:
    """Kierunek wynika z rodzaju pozycji, nie ze znaku liczby.

    Ta sama regula co przy wpisach budzetu: dlug wpisany ze znakiem minus
    podnosilby wartosc netto zamiast ja obnizac, i wygladalby na majatek.
    """
    wartosc = Decimal(str(kwota))
    if wartosc < 0:
        raise BladMagazynu(
            f"{co} nie może być ujemne ({kwota}). Kierunek wynika z rodzaju "
            f"pozycji, nie ze znaku liczby.")
    return wartosc


#: Gorna granica oprocentowania rocznego w procentach. NIE jest to granica
#: prawna (odsetki maksymalne to 2 x (stopa referencyjna NBP + 3,5 pp), dzis
#: rzad kilkunastu procent) — celowo, bo prawo sie zmienia, a bramka wpisana
#: pod dzisiejsza stope odrzucalaby jutro dane prawdziwe. To granica
#: POMYLKI POLA: najczestszy blad w tym formularzu to wpisanie tu kwoty raty
#: (1 305,05) albo kapitalu (51 234), a nie stopy. Kazda z nich przekracza
#: 100 z ogromnym zapasem; zadne realne oprocentowanie kredytu nie.
OPROCENTOWANIE_MAKS = Decimal("100")


def _wymagaj_oprocentowania(wartosc) -> str | None:
    """Oprocentowanie roczne w procentach albo `None` = NIE WIEM.

    `None` i `Decimal("0")` to DWIE ROZNE odpowiedzi i rozroznienie siedzi
    w typie, nie w komentarzu: pusta wartosc idzie do bazy jako `NULL`, zero
    jako napis `"0"`. Kredyt nieoprocentowany (Alior, 0%) jest realnym stanem
    i nie ma prawa wygladac jak kredyt, o ktory nikt nie zapytal (regula D11).
    """
    if wartosc is None or (isinstance(wartosc, str) and not wartosc.strip()):
        return None
    try:
        liczba = Decimal(str(wartosc))
    except (ArithmeticError, ValueError) as e:
        raise BladMagazynu(
            f"Oprocentowanie {wartosc!r} nie jest liczba. Podaj stope roczna "
            f"w procentach, na przyklad 9 albo 9,5 — albo zostaw puste, "
            f"jesli jej nie znasz.") from e
    if liczba < 0:
        raise BladMagazynu(
            f"Oprocentowanie nie może być ujemne ({liczba}). Jeśli kredyt jest "
            f"nieoprocentowany, wpisz 0; jeśli nie znasz stopy, zostaw puste — "
            f"to dwie różne odpowiedzi i aplikacja je rozróżnia.")
    if liczba > OPROCENTOWANIE_MAKS:
        raise BladMagazynu(
            f"Oprocentowanie {liczba}% przekracza {OPROCENTOWANIE_MAKS}% i jest "
            f"prawie na pewno pomyłką pola — to miejsce na stopę roczną "
            f"w procentach, nie na kwotę raty ani na kapitał.")
    return str(liczba)


def _wymagaj_nazwy(nazwa: str, co: str) -> str:
    tekst = str(nazwa or "").strip()
    if not tekst:
        raise BladMagazynu(f"{co} nie może być puste.")
    return tekst


def zapisz_zobowiazanie(polaczenie, *, nazwa: str, kapital: Decimal,
                        rata_minimalna: Decimal,
                        oprocentowanie: "Decimal | None" = None) -> int:
    """Zobowiazanie niesie WYLACZNIE kapital do splaty i rate miesieczna.

    OPROCENTOWANIE WROCILO 2026-08-28 (D9, zlecenie Darka godz. 19:38),
    po tym jak decyzja z 2026-08-26 (Z43) zdjela je jako martwe. Tamto
    uzasadnienie — „nie wchodzi do zadnej liczby" — bylo trafne wtedy
    i przestalo obowiazywac: pole sluzy teraz ZBIERANIU danych pod plasterek,
    ktory je policzy. Nadal **nic z tej wartosci nie liczymy**.

    `oprocentowanie=None` znaczy NIE WIEM i jest stanem dopuszczalnym;
    `Decimal("0")` znaczy zero procent i jest odpowiedzia. To dwie rozne
    rzeczy — patrz `_wymagaj_oprocentowania`.
    """
    nazwa = _wymagaj_nazwy(nazwa, "Nazwa zobowiązania")
    kapital = _wymagaj_nieujemnej(kapital, "Kapitał")
    rata_minimalna = _wymagaj_nieujemnej(rata_minimalna, "Rata")
    oprocentowanie = _wymagaj_oprocentowania(oprocentowanie)
    return _zapisz(polaczenie,
        "INSERT INTO zobowiazania (nazwa, kapital, rata_minimalna,"
        " oprocentowanie) VALUES (?,?,?,?)",
        (nazwa, str(kapital), str(rata_minimalna), oprocentowanie))


def zmien_zobowiazanie(polaczenie, *, zobowiazanie_id: int, nazwa: str,
                       kapital: Decimal, rata_minimalna: Decimal,
                       oprocentowanie: "Decimal | None" = None) -> None:
    """Poprawia zobowiazanie w miejscu, po NUMERZE wiersza.

    Numer, nie nazwa: dwa kredyty wolno nazwac tak samo, wiec poprawka po
    nazwie trafialaby w oba. Walidacja ta sama co przy zapisie — wpis
    poprawiony omijajacy regule bylby furtka wokol niej.
    """
    nazwa = _wymagaj_nazwy(nazwa, "Nazwa zobowiązania")
    kapital = _wymagaj_nieujemnej(kapital, "Kapitał")
    rata_minimalna = _wymagaj_nieujemnej(rata_minimalna, "Rata")
    # Poprawka MUSI umiec wyczyscic do „nie wiem": inaczej omylkowo wpisane
    # 0% zostaje na zawsze, bo formularz nie ma jak cofnac odpowiedzi.
    oprocentowanie = _wymagaj_oprocentowania(oprocentowanie)
    kursor = polaczenie.execute(
        "UPDATE zobowiazania SET nazwa = ?, kapital = ?, rata_minimalna = ?, "
        "oprocentowanie = ? WHERE id = ?",
        (nazwa, str(kapital), str(rata_minimalna), oprocentowanie,
         int(zobowiazanie_id)))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma zobowiązania o numerze {zobowiazanie_id} — nic nie zmieniłem.")
    polaczenie.commit()


def usun_zobowiazanie(polaczenie, *, zobowiazanie_id: int) -> None:
    """Kasuje JEDNO zobowiazanie po numerze. Brak wiersza jest bledem.

    Cisza przy pomylce w numerze wyglada jak sukces — ta sama regula co
    w `usun_plan`.
    """
    kursor = polaczenie.execute("DELETE FROM zobowiazania WHERE id = ?",
                                (int(zobowiazanie_id),))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma zobowiązania o numerze {zobowiazanie_id} — nic nie skasowałem.")
    polaczenie.commit()


def wczytaj_zobowiazania(polaczenie) -> pd.DataFrame:
    """Zobowiazania. `oprocentowanie` wraca jako `None` albo napis z liczba.

    NORMALIZACJA NIE JEST KOSMETYKA. `pd.read_sql` zamienia SQL-owy `NULL`
    na `NaN` — czyli `float`, ktory w warunku `if` jest **PRAWDZIWY**, podczas
    gdy `Decimal("0")` jest **FALSZYWY**. Naiwne `if wiersz["oprocentowanie"]:`
    dzialaloby wiec dokladnie ODWROTNIE, niz brzmi: „nie wiem" traktowaloby
    jak wartosc, a realne 0% Aliora jak brak danych. Zamieniamy `NaN` na
    `None` TUTAJ, w jednym miejscu, zamiast liczyc na czujnosc kazdego ekranu.
    Pilnuje tego `test_NaN_nie_udaje_wartosci_w_warunku`.
    """
    ramka = _wczytaj(polaczenie, "zobowiazania", "ORDER BY id")
    if "oprocentowanie" in ramka.columns:
        # `dtype=object` jest WARUNKIEM, nie ozdoba: w kolumnie typu
        # zmiennoprzecinkowego pandas zamienia wstawione `None` z powrotem
        # na `NaN` i normalizacja cicho znika.
        ramka["oprocentowanie"] = pd.Series(
            [None if w is None or (isinstance(w, float) and w != w) else w
             for w in ramka["oprocentowanie"]],
            index=ramka.index, dtype=object)
    return ramka


def oprocentowanie_z_wiersza(wartosc) -> "Decimal | None":
    """Jeden nosnik odczytu oprocentowania: `None` = NIE WIEM, reszta liczba.

    Ekrany i narzedzia wolaja to zamiast sprawdzac po swojemu — bo „po swojemu"
    znaczy zwykle `if wartosc:`, a to myli 0% z brakiem danych.
    """
    if wartosc is None or (isinstance(wartosc, float) and wartosc != wartosc):
        return None
    if isinstance(wartosc, str) and not wartosc.strip():
        return None
    return Decimal(str(wartosc))


#: Kategorie aktywow, ktore sa RACHUNKAMI BANKOWYMI, a nie rzeczami.
#: Nosnik jest tutaj, a lista na ekranie je WOLA — powtorzone rozjechalyby sie
#: przy pierwszej zmianie, a konto zapisane z ekranu przestaloby byc
#: rozpoznawane przez regule licznosci nizej.
#:
#: Rozroznienie powstalo 2026-08-28 (D10), gdy Darek zapowiedzial dodanie
#: WSZYSTKICH swoich kont do majatku. Do tej pory nic nie odrozanialo
#: aktywa-rachunku od aktywa-rzeczy.
KATEGORIA_RACHUNEK_ROZLICZENIOWY = "rachunek rozliczeniowy"
KATEGORIA_RACHUNEK = "rachunek"
KATEGORIE_RACHUNKOW = (KATEGORIA_RACHUNEK_ROZLICZENIOWY, KATEGORIA_RACHUNEK)


def czy_rachunek(kategoria) -> bool:
    """Czy ta kategoria opisuje konto bankowe, a nie rzecz. Jeden nosnik."""
    return str(kategoria) in KATEGORIE_RACHUNKOW


def _wymagaj_jednego_rozliczeniowego(polaczenie, kategoria: str,
                                     pomijajac: "int | None" = None) -> None:
    """Rachunek rozliczeniowy moze byc DOKLADNIE JEDEN.

    To nie jest porzadek dla porzadku. Kotwica prognozy to saldo JEDNEGO
    konta — tego, z ktorego wychodza wydatki. Dwa konta tak oznaczone czynia
    pytanie „ktore" nierozstrzygalnym, a najblizsza odpowiedz, po ktora ktos
    siegnie, to suma sald. Suma sald NIE JEST kotwica: prognoza ruszylaby od
    kwoty, ktorej Darek na wydatki nie ma.

    `pomijajac` to numer poprawianego wiersza — bez tego wiersz bylby swoim
    wlasnym duplikatem i nie dalo by sie zmienic na nim nawet kwoty.
    """
    if str(kategoria) != KATEGORIA_RACHUNEK_ROZLICZENIOWY:
        return
    warunek = "WHERE kategoria = ?"
    parametry: list = [KATEGORIA_RACHUNEK_ROZLICZENIOWY]
    if pomijajac is not None:
        warunek += " AND id <> ?"
        parametry.append(int(pomijajac))
    istniejace = polaczenie.execute(
        f"SELECT nazwa_aktywa FROM majatek {warunek}", parametry).fetchall()
    if istniejace:
        nazwy = ", ".join(w[0] for w in istniejace)
        raise BladMagazynu(
            f"Rachunek rozliczeniowy może być tylko jeden, a jest już: {nazwy}. "
            f"To konto, z którego wychodzą wydatki i od którego rusza prognoza. "
            f"Pozostałe konta zapisz jako „{KATEGORIA_RACHUNEK}” albo najpierw "
            f"zmień kategorię tamtego.")


def zapisz_aktywo(polaczenie, *, nazwa_aktywa: str, kategoria: str,
                  wartosc: Decimal) -> int:
    nazwa_aktywa = _wymagaj_nazwy(nazwa_aktywa, "Nazwa aktywa")
    wartosc = _wymagaj_nieujemnej(wartosc, "Wartość aktywa")
    _wymagaj_jednego_rozliczeniowego(polaczenie, kategoria)
    return _zapisz(polaczenie,
        "INSERT INTO majatek (nazwa_aktywa, kategoria, wartosc) VALUES (?,?,?)",
        (nazwa_aktywa, kategoria, str(wartosc)))


def _odmow_zmiany_salda_rozliczeniowego(polaczenie, kategoria, wartosc) -> None:
    """Kwoty rachunku rozliczeniowego nie zmienia sie w majatku, tylko odczytem.

    Bez tej odmowy edycja bylaby PO CICHU IGNOROWANA: `wczytaj_majatek`
    nadpisuje ta wartosc ostatnim odczytem, wiec Darek wpisalby liczbe,
    zapisal i zobaczyl poprzednia. Odmowa mowi, GDZIE ta liczbe zmienic —
    milczace zignorowanie byloby gorsze od bledu.

    Blokujemy KWOTE, nie caly wiersz: nazwe i kategorie wolno poprawiac.
    """
    if str(kategoria) != KATEGORIA_RACHUNEK_ROZLICZENIOWY:
        return
    odczyt = ostatni_odczyt_salda(polaczenie)
    if odczyt is None or Decimal(str(wartosc)) == odczyt.kwota:
        return
    raise BladMagazynu(
        f"Salda rachunku rozliczeniowego nie zmienia się tutaj. Ta pozycja "
        f"pokazuje ostatni odczyt stanu konta ({odczyt.kwota} zł z dnia "
        f"{odczyt.data.isoformat()}) — jedna liczba wpisywana raz. Żeby ją "
        f"zmienić, zapisz nowy odczyt stanu konta; nazwę i kategorię tego "
        f"wiersza możesz poprawić normalnie.")


def zmien_aktywo(polaczenie, *, aktywo_id: int, nazwa_aktywa: str,
                 kategoria: str, wartosc: Decimal) -> None:
    """Poprawia aktywo w miejscu, po numerze wiersza — jak `zmien_zobowiazanie`."""
    nazwa_aktywa = _wymagaj_nazwy(nazwa_aktywa, "Nazwa aktywa")
    wartosc = _wymagaj_nieujemnej(wartosc, "Wartość aktywa")
    _wymagaj_jednego_rozliczeniowego(polaczenie, kategoria, pomijajac=aktywo_id)
    _odmow_zmiany_salda_rozliczeniowego(polaczenie, kategoria, wartosc)
    kursor = polaczenie.execute(
        "UPDATE majatek SET nazwa_aktywa = ?, kategoria = ?, wartosc = ? "
        "WHERE id = ?",
        (nazwa_aktywa, str(kategoria), str(wartosc), int(aktywo_id)))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma aktywa o numerze {aktywo_id} — nic nie zmieniłem.")
    polaczenie.commit()


def usun_aktywo(polaczenie, *, aktywo_id: int) -> None:
    kursor = polaczenie.execute("DELETE FROM majatek WHERE id = ?",
                                (int(aktywo_id),))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma aktywa o numerze {aktywo_id} — nic nie skasowałem.")
    polaczenie.commit()


def wczytaj_majatek(polaczenie) -> pd.DataFrame:
    """Aktywa. Wartosc RACHUNKU ROZLICZENIOWEGO pochodzi z ostatniego odczytu
    salda, a nie z wlasnej kopii liczby.

    ROZSTRZYGNIECIE 2026-08-28 (D10), po pytaniu Darka: „w takim razie ta kwota
    to 9995 zlotych. Taka kwota znajduje sie na rachunku biezacym i w majatku
    bedzie dodana jako wartosc rachunku biezacego". Jedno konto, jedna liczba,
    dwa miejsca UZYCIA — wiec wpisywana RAZ.

    Do tej pory to samo saldo stalo w dwoch wpisach i rozjechalo sie o piec
    groszy (9 995,00 kontra 9 995,05), zanim ktokolwiek zauwazyl. Przy kilku
    kontach — a Darek dodaje wszystkie — rozjazd bylby regula, nie wyjatkiem.

    Gdy odczytu jeszcze nie bylo, zostaje wartosc wpisana recznie: inaczej
    „dodam wszystkie konta" bylo by zablokowane wymogiem, ktorego nie ma czym
    spelnic. Odczyt dotyczy WYLACZNIE rachunku rozliczeniowego — pozostale
    konta niosa wlasne wyceny.
    """
    ramka = _wczytaj(polaczenie, "majatek", "ORDER BY id")
    odczyt = ostatni_odczyt_salda(polaczenie)
    if odczyt is None or ramka.empty or "kategoria" not in ramka.columns:
        return ramka
    # `Decimal`, NIE napis. `_wczytaj` konwertuje kolumny kwotowe na `Decimal`
    # (`_KOLUMNY_KWOTOWE`), a konsumenci sumuja je wprost: `sum(kwoty,
    # Decimal("0"))` w naglowku kolumny majatku. Wstawiony tu napis wywracal
    # CALA stara aplikacje bledem „unsupported operand: Decimal and str" —
    # zlapal to straznik czytajacy wyrenderowany ekran, nie testy jednostkowe,
    # bo one pisaly `Decimal(str(wartosc))` i dzialaly na obu typach.
    ramka["wartosc"] = pd.Series(
        [odczyt.kwota
         if str(k) == KATEGORIA_RACHUNEK_ROZLICZENIOWY else w
         for k, w in zip(ramka["kategoria"], ramka["wartosc"])],
        index=ramka.index, dtype=object)
    return ramka


# --- koszty JDG -----------------------------------------------------------

def zapisz_koszt(polaczenie, *, data: date, opis: str,
                 kwota_netto: Decimal, kwota_vat: Decimal) -> int:
    """Zapisuje koszt firmowy I tworzy odpowiadający mu wydatek w budżecie.

    DWA ZAPISY, JEDNO ZNACZENIE. Jedno konto obsługuje firmę i dom, więc zakup
    firmowy jest realnym wypływem z tego samego rachunku, co czynsz — i musi
    być widoczny w budżecie, inaczej „do alokacji" pokazuje pieniądze, których
    już nie ma.

    Wydatek idzie na kwotę **brutto**: z konta wypływa netto razem z VAT-em.
    Że ten VAT wróci przy rozliczeniu, mówi osobno rezerwa podatkowa
    (`podatki.rezerwa_na_podatki`), a nie zaniżony wydatek.

    Klucz utworzonego wpisu ląduje w `wpis_budzetu_id`. **Prawdą o powiązaniu
    jest istnienie wpisu, nie sam znacznik** — `usun_koszt` sprawdza, czy wpis
    jeszcze jest, zamiast ufać kolumnie.
    """
    brutto = stawki.do_groszy(Decimal(str(kwota_netto)) + Decimal(str(kwota_vat)))
    wpis_id = zapisz_wpis(polaczenie, data=data, typ=budzet.TYP_WYDATKI,
                          kategoria=budzet.KATEGORIA_KOSZTY_JDG,
                          kwota=brutto, szczegoly=f"Koszt JDG: {opis}")
    return _zapisz(polaczenie,
        "INSERT INTO koszty_jdg (data, opis, kwota_netto, kwota_vat,"
        " wpis_budzetu_id) VALUES (?,?,?,?,?)",
        (data.isoformat(), opis, str(kwota_netto), str(kwota_vat), wpis_id))


def wczytaj_koszty(polaczenie) -> pd.DataFrame:
    return _wczytaj(polaczenie, "koszty_jdg", "ORDER BY data DESC, id DESC")


def usun_koszt(polaczenie, *, koszt_id: int) -> None:
    """Kasuje koszt razem z jego wydatkiem w budżecie.

    Osierocony wydatek `Firmowe` bez kosztu wygląda jak zwykły zakup i przy
    następnym wpisie tego samego rachunku policzy się drugi raz.

    Wpis mógł już zniknąć — użytkownik ma prawo skasować go ręcznie
    w zakładce Budżet. Kasowanie kosztu ma wtedy dojść do końca, a nie
    przerwać się w połowie i zostawić koszt bez wpisu ani wpisu bez kosztu.
    """
    wiersz = polaczenie.execute(
        "SELECT wpis_budzetu_id FROM koszty_jdg WHERE id = ?",
        (koszt_id,)).fetchone()
    if wiersz is None:
        return
    if wiersz[0] is not None:
        polaczenie.execute("DELETE FROM wpisy_budzetu WHERE id = ?", (wiersz[0],))
    polaczenie.execute("DELETE FROM koszty_jdg WHERE id = ?", (koszt_id,))
    polaczenie.commit()


# --- most: faktura zapłacona -> przychód w budżecie ------------------------

def czy_przeniesiona(polaczenie, *, faktura_id: int) -> bool:
    """Czy faktura ma w budżecie SWÓJ ISTNIEJĄCY wpis przychodu.

    PRAWDĄ O PRZENIESIENIU JEST ISTNIENIE WPISU, NIE ZNACZNIK. Wpis wolno
    skasować ręcznie w zakładce Budżet; gdyby liczył się sam znacznik,
    faktura zostałaby oznaczona jako przeniesiona, a przychodu nie byłoby
    nigdzie — pieniądze zniknęłyby cicho, bez żadnego błędu.
    """
    wiersz = polaczenie.execute(
        "SELECT wpis_budzetu_id FROM przychody_jdg WHERE id = ?",
        (faktura_id,)).fetchone()
    if wiersz is None or wiersz[0] is None:
        return False
    return polaczenie.execute(
        "SELECT 1 FROM wpisy_budzetu WHERE id = ?", (wiersz[0],)
    ).fetchone() is not None


def oznacz_fakture_zaplacona(polaczenie, *, faktura_id: int,
                             data_wplywu: date) -> int | None:
    """Zapisuje datę wpływu i tworzy przychód w budżecie na kwotę BRUTTO.

    UJĘCIE KASOWE (decyzja D1). Na konto wpływa netto razem z VAT-em i to
    jest kwota, którą realnie masz; że część należy do urzędu, mówi osobno
    rezerwa podatkowa, a nie zaniżony przychód.

    Data to dzień WPŁYWU, nie wystawienia — faktura płatna za 14 dni
    pokazywałaby pieniądze o dwa tygodnie za wcześnie, w budżecie miesiąca,
    w którym ich na koncie nie było.

    Druga próba nie tworzy drugiego przychodu: podwyższyłaby „do alokacji"
    o całą fakturę i zachęciła do wydania pieniędzy, których nie ma.
    """
    if czy_przeniesiona(polaczenie, faktura_id=faktura_id):
        return None
    wiersz = polaczenie.execute(
        "SELECT numer_faktury, kwota_netto, kwota_vat FROM przychody_jdg"
        " WHERE id = ?", (faktura_id,)).fetchone()
    if wiersz is None:
        raise BladMagazynu(f"Nie ma faktury o numerze wewnętrznym {faktura_id}.")

    numer, netto, vat = wiersz
    brutto = stawki.do_groszy(Decimal(str(netto)) + Decimal(str(vat)))
    wpis_id = zapisz_wpis(polaczenie, data=data_wplywu,
                          typ=budzet.TYP_PRZYCHODY,
                          kategoria=budzet.KATEGORIA_PRZYCHOD_JDG,
                          kwota=brutto, szczegoly=f"Faktura {numer}")
    polaczenie.execute(
        "UPDATE przychody_jdg SET data_zaplaty = ?, wpis_budzetu_id = ?"
        " WHERE id = ?", (data_wplywu.isoformat(), wpis_id, faktura_id))
    polaczenie.commit()
    return wpis_id


def koszty_netto_w_roku(polaczenie, rok: int) -> Decimal:
    """Suma kosztów uzyskania przychodu za rok, w kwotach NETTO.

    NETTO, nie brutto: dla podatnika VAT kosztem jest kwota netto, bo VAT
    naliczony wraca osobno przez rozliczenie VAT. Użycie brutto zawyżyłoby
    koszt o podatek, który nie jest kosztem — i przechyliłoby porównanie form
    przeciw ryczałtowi mocniej, niż wynika z przepisów.
    """
    df = wczytaj_koszty(polaczenie)
    if df.empty:
        return Decimal("0.00")
    w_roku = df[df["data"].astype(str).str.startswith(f"{rok:04d}-")]
    return stawki.do_groszy(
        sum((Decimal(str(x)) for x in w_roku["kwota_netto"]), Decimal("0.00")))

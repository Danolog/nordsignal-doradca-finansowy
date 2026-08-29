"""Trwałość danych — PostgreSQL za wąskim interfejsem.

Interfejs jest wąski celowo: SQL nie wychodzi poza ten moduł. To ten warunek
pozwolił podmienić sterownik (W4, 2026-08-29) bez ruszania reszty rdzenia:
`api/` nie ma ani jednego literału SQL, a `interfejs/` nie importuje magazynu.

KWOTY: kolumna `NUMERIC`, w Pythonie `Decimal`. Nigdy typ zmiennoprzecinkowy —
`float` gubi grosze przy podróży do bazy i z powrotem, a to jest aplikacja
podatkowa (CLAUDE.md §3.1). Sterownik psycopg oddaje `NUMERIC` jako `Decimal`
sam; `_wczytaj` mimo to normalizuje kolumny z `_KWOTOWE`, bo ramka danych
potrafi zamienić typ przy składaniu (patrz `_ramka`).

DATY: kolumna `DATE`, w Pythonie `datetime.date`. Koniec porównań dat na
napisach — dlatego `czy_skladki_naliczone_w_miesiacu` i `przychod_narastajaco`
pytają zakresem, a nie wzorcem `LIKE` na prefiksie (ten przestał działać
razem z typem `TEXT`).

FLAGI: kolumna `BOOLEAN`, w Pythonie `bool` albo `None`. `kategorie.niezbedna`
jest TRÓJSTANEM (`None` = „Darek jeszcze nie rozstrzygnął") i to rozróżnienie
niesie typ, nie komentarz.

WIĘZY KLUCZA OBCEGO DZIAŁAJĄ — inaczej niż u poprzednika. W SQLite
`PRAGMA foreign_keys` jest domyślnie WYŁĄCZONA i działa per połączenie, więc
klucz obcy zadeklarowany w schemacie nie robił nic; PostgreSQL egzekwuje go
zawsze. Reguły o tym, CO wolno zapisać (trzy typy wpisu, kategoria ze
słownika), zostają mimo to w Pythonie — tam mieszka zdanie dla człowieka.

ROZPOZNAWANIE NARUSZEŃ PO NAZWIE WIĘZU, NIE PO TREŚCI KOMUNIKATU. Do W4
`_zapisz` sprawdzało `if "numer_faktury" in str(e)`. Napis „numer_faktury"
występuje także w automatycznej nazwie, którą PostgreSQL nadałby więzowi bez
nazwy własnej (`przychody_jdg_numer_faktury_key`) — zdanie dla człowieka
wisiałoby więc na nazwie, której nikt nie wybrał. Dlatego więz ma teraz nazwę
własną (`numer_faktury_niepowtarzalny`, `silnik/baza/schemat.sql`), a kod
czyta `e.diag.constraint_name`. Strażnik:
`testy/test_komunikat_duplikatu_faktury.py`.
"""

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import psycopg
from psycopg import conninfo as psycopg_conninfo
from psycopg.rows import dict_row

from silnik import baza as baza_schematu
from silnik.rdzen import budzet, stawki
from wiedza import rejestr as rejestr_wiedzy
from wiedza import stawki_poczatkowe

#: Zmienna srodowiskowa wskazujaca baze — adres polaczenia, nie sciezka pliku.
#: Nazwa jest ta sama, ktorej uzywa Vercel i `.env.example`, wiec produkcja
#: i praca lokalna czytaja JEDEN klucz.
#:
#: CO PRZEZ ZMIANE NA ADRES OSLABLO (pozycja jawna, §3.11): straznik
#: `STRAZNICY_ADRESU` nie ma juz `Path.resolve()`, ktore sprowadzalo kazdy
#: zapis sciezki do jednej postaci. Ten sam serwer da sie zapisac na kilka
#: sposobow (`localhost`, `127.0.0.1`, `::1`, gniazdo systemowe, inny port
#: tego samego tunelu), a porownanie napisow tego nie widzi. Nastepca jest
#: czesciowy: adres rozkladamy na czesci `psycopg.conninfo.conninfo_to_dict`
#: — czyli parserem sterownika, nie wlasnym — i straznik oglada `host`,
#: `port` i `dbname` osobno. To lapie kazdy zapis, ktory sterownik rozumie
#: tak samo; NIE lapie dwoch roznych nazw tego samego serwera.
ZMIENNA_BAZY = "DATABASE_URL"

#: Zmienne z polaczeniem BEZPOSREDNIM (z pominieciem puli). Migracja schematu
#: idzie tedy, jesli ktoras jest ustawiona: pula polaczen Neona nie utrzymuje
#: sesji miedzy poleceniami DDL. Brak obu znaczy „uzyj tego samego adresu".
#:
#: DWIE NAZWY, NIE JEDNA — i to nie jest niechlujstwo. `.env.example` niesie
#: nasza nazwe (`DATABASE_URL_BEZPOSREDNI`), a Neon wstrzykuje do Vercela
#: swoja (`DATABASE_URL_UNPOOLED`) i tej drugiej nie da sie przemianowac
#: u zrodla. Czytanie tylko naszej znaczyloby, ze migracja idzie na produkcji
#: PRZEZ PULE — czyli po drodze, ktora nie utrzymuje sesji miedzy poleceniami
#: i przerywa migracje w losowym miejscu. Rozjazd nazw zostal zmierzony
#: 2026-08-29 przy stawianiu bazy produkcyjnej.
ZMIENNA_BAZY_BEZPOSREDNIEJ = "DATABASE_URL_BEZPOSREDNI"
ZMIENNA_BAZY_BEZPOSREDNIEJ_NEON = "DATABASE_URL_UNPOOLED"

#: Strazniki rozwiazanego adresu. W produkcji **pusta** — `rdzen/` nie ma
#: wiedziec, czy dziala pod pytestem (granica pilnowana przez
#: `testy/test_granice.py`). Straznika zaklada `conftest.py`: pod pytestem
#: rozwiazanie sie na baze produkcyjna jest bledem, nie ostrzezeniem.
STRAZNICY_ADRESU: list = []

@dataclass(frozen=True)
class OpisBazy:
    """Ktora baze otwarto i czy jest to baza produkcyjna.

    Jeden nosnik dla dwoch konsumentow: paska aplikacji (Z52) i punktu
    koncowego `/api/stan` (Z65). Drugi konsument ma to ZAWOLAC, nie policzyc
    jeszcze raz — inaczej pasek i API moglyby powiedziec co innego o tej samej
    bazie w tej samej chwili.

    `adres` jest ADRESEM BEZ HASLA — skladany z czesci, ktore zwrocil parser
    sterownika. Haslo nie ma prawa trafic na ekran ani do dziennika
    (CLAUDE.md §8, „nigdy wartosc sekretu w dowodzie").
    """

    adres: str
    domyslna: bool


def _czesci_adresu(adres: str) -> dict:
    """Adres rozlozony na czesci PARSEREM STEROWNIKA, nie wlasnym.

    Wlasny parser bylby drugim nosnikiem odpowiedzi „do ktorego serwera to
    prowadzi" — a rozjazd z parserem, ktory naprawde otwiera polaczenie,
    znaczylby, ze straznik oglada inny adres niz sterownik.
    """
    try:
        return psycopg_conninfo.conninfo_to_dict(adres)
    except psycopg.ProgrammingError as e:
        raise BladMagazynu(
            f"Adres bazy jest nieczytelny dla sterownika. Oczekiwany ksztalt "
            f"to `postgresql://uzytkownik:haslo@serwer:port/nazwa`. "
            f"Szczegol: {e}") from e


def adres_bez_hasla(adres: str) -> str:
    """`serwer:port/nazwa` — tyle, ile wolno pokazac czlowiekowi i zapisac.

    JEDEN NOSNIK tej odpowiedzi. Kazde miejsce, ktore mowi „ktora baze
    otwarto" (komunikat odmowy, pasek, `/api/stan`), wola stad — inaczej
    pierwsza kopia, ktora zapomni odsiac haslo, wypisze je na ekran.
    """
    czesci = _czesci_adresu(adres)
    serwer = czesci.get("host") or "gniazdo-systemowe"
    port = czesci.get("port")
    nazwa = czesci.get("dbname") or "?"
    return f"{serwer}:{port}/{nazwa}" if port else f"{serwer}/{nazwa}"


def _rozwiaz_adres() -> str:
    """Sama arytmetyka: `DATABASE_URL`. BEZ straznikow i BEZ wartosci domyslnej.

    Rozdzielone od `adres_bazy()` swiadomie. Testy sprawdzajace samo
    rozwiazywanie musza umiec zobaczyc wynik „adres produkcyjny" — a gdyby
    robily to przez `adres_bazy()`, musialyby zdjac bramke. Straznik, ktorego
    trzeba wylaczyc, zeby go sprawdzic, nie jest w tym momencie straznikiem
    (Z52, 2026-08-27).

    WARTOSCI DOMYSLNEJ NIE MA I TO JEST DECYZJA. Poprzednik mial `cfo_database.db`
    obok kodu, wiec brak zmiennej znaczyl „otworz plik w repozytorium". Adres
    zgadniety prowadzilby do serwera, ktorego nikt nie wskazal — a wtedy
    „patrzylem w niewlasciwa baze i wygladalo dobrze" wraca tylnymi drzwiami.
    Brak zmiennej jest ODMOWA z instrukcja (§3.7).

    Zmienna czytana przy KAZDYM wywolaniu, nie przy imporcie: proces potomny
    wczytuje `.env` od nowa.
    """
    surowy = os.environ.get(ZMIENNA_BAZY, "").strip()
    if not surowy:
        raise BladMagazynu(
            f"Nie wiem, ktora baze otworzyc: zmienna srodowiskowa "
            f"{ZMIENNA_BAZY} jest pusta albo jej nie ma. Ustaw ja na adres "
            f"polaczenia PostgreSQL — wzor stoi w `.env.example`. "
            f"Nie zgaduje adresu, bo baza zgadnieta wyglada tak samo jak "
            f"wlasciwa i pokazalaby Ci cudze liczby albo zera.")
    return surowy


def adres_bazy() -> str:
    """Ktora baze otwieramy — JEDYNY nosnik tej odpowiedzi, razem z bramka.

    Kolejnosc: jawny argument `polacz(adres=...)` > `DATABASE_URL`.
    """
    adres = _rozwiaz_adres()
    for straznik in STRAZNICY_ADRESU:
        straznik(adres)
    return adres


def adres_migracji(adres: "str | None" = None) -> str:
    """Adres, ktorym idzie DDL. `DATABASE_URL_BEZPOSREDNI`, gdy jest.

    Pula polaczen Neona nie utrzymuje sesji miedzy poleceniami, a migracja
    schematu jest jedna sesja od poczatku do konca. Gdy zmiennej nie ma —
    a tak jest przy bazie lokalnej — uzywamy tego samego adresu.
    """
    if adres is not None:
        return adres
    for zmienna in (ZMIENNA_BAZY_BEZPOSREDNIEJ, ZMIENNA_BAZY_BEZPOSREDNIEJ_NEON):
        bezposredni = os.environ.get(zmienna, "").strip()
        if bezposredni:
            for straznik in STRAZNICY_ADRESU:
                straznik(bezposredni)
            return bezposredni
    return adres_bazy()


def opis_bazy(adres: "str | None" = None) -> OpisBazy:
    """Rozwiazany adres razem z odpowiedzia „czy to baza produkcyjna".

    „Produkcyjna" znaczy tu: serwer NIE jest maszyna lokalna. Poprzednik
    porownywal sciezke pliku z jedna stala; adres takiej stalej nie ma —
    baza produkcyjna stoi u dostawcy i jej nazwa moze sie zmienic, a to, co
    ja odroznia, to fakt, ze nie jest na tym laptopie.
    """
    if adres is None:
        adres = adres_bazy()
    czesci = _czesci_adresu(adres)
    return OpisBazy(adres=adres_bez_hasla(adres),
                    domyslna=not czy_lokalny(czesci.get("host")))


#: Nazwy, pod ktorymi PostgreSQL slucha na TEJ maszynie. Adres spoza tej listy
#: prowadzi do serwera, ktorego na tym laptopie nie ma — czyli do produkcji
#: albo do cudzej bazy. Pusty `host` znaczy gniazdo systemowe, czyli lokalnie.
NAZWY_LOKALNE = ("localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal")


def czy_lokalny(serwer: "str | None") -> bool:
    """Czy ten serwer stoi na tej maszynie — JEDEN nosnik tej odpowiedzi.

    LUKA NAZWANA: rozpoznanie idzie po NAZWIE, nie po adresie sieciowym.
    Tunel wystawiony pod inna nazwa na `127.0.0.1` przejdzie jako lokalny,
    a `localhost` przekierowany w `/etc/hosts` na serwer zdalny — takze.
    Sprowadzanie nazwy do adresu wymagaloby zapytania do systemu nazw przy
    kazdym otwarciu bazy; tego nie robimy.
    """
    if serwer is None or not str(serwer).strip():
        return True
    return str(serwer).strip().lower() in NAZWY_LOKALNE

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

#: NAZWY TABEL — wyprowadzone z napisu DDL, nie wypisane recznie.
#: Recznie wypisana lista rozjechalaby sie przy pierwszej dolozonej tabeli
#: i to `_wczytaj` odmawialby odczytu z tabeli, ktora naprawde istnieje.
_TABELE_ZNANE = frozenset(re.findall(
    r"CREATE TABLE IF NOT EXISTS\s+(\w+)",
    baza_schematu.schemat_postgresql()))

# KONTROLA LICZNOSCI PRZY IMPORCIE. Zbior pusty — bo ktos zmienil ksztalt
# napisu DDL — zamienilby bramke w `_wczytaj` w blokade wszystkiego, a przy
# innym ulozeniu kodu w bramke, ktora przepuszcza wszystko. Jedno i drugie
# wychodzi na jaw dopiero u Darka; tu wychodzi przy imporcie.
assert len(_TABELE_ZNANE) >= 14, (
    f"z napisu DDL wyszlo {len(_TABELE_ZNANE)} nazw tabel — schemat ma ich "
    f"co najmniej czternascie")

#: JEDEN NOSNIK SCHEMATU — `silnik/baza/schemat_postgresql()`.
#:
#: Do W4 stal tutaj drugi napis DDL (`_SCHEMAT`, dialekt SQLite) i to byl
#: SWIADOMY dlug z jawnym progiem: „drugi nosnik znika w chwili, w ktorej
#: aplikacja przestanie otwierac SQLite" (straznik W1). Ta chwila nadeszla —
#: napis skasowany, prog domkniety. Nastepca straznika:
#: `testy/test_schemat_wobec_bazy.py`.
#:
#: `wydatki_osobiste` swiadomie NIE MA w schemacie: tabela pozostawiona tam
#: wracalaby po kazdej migracji — pusta i wygladajaca jak prawdziwa.


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
    """NASZE tabele — z katalogu systemowego, w BIEZACEJ przestrzeni nazw.

    `current_schema()`, a nie cala baza: testy izoluja sie przestrzenia nazw
    (`conftest.py`), wiec pytanie „ile tabel" bez tego ograniczenia liczyloby
    tabele wszystkich rownolegle biegnacych testow naraz.

    Poprzednik odsiewal tu `sqlite_sequence` — tabele, ktora sterownik zakladal
    sam. PostgreSQL trzyma liczniki `BIGSERIAL` w obiektach osobnego rodzaju
    (sekwencjach), wiec `information_schema.tables` ich nie pokazuje i nie ma
    czego odsiewac.
    """
    return {w[0] for w in polaczenie.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
    ).fetchall()}


def _kolumny(polaczenie, tabela: str) -> set[str]:
    """Nazwy kolumn tabeli — NASTEPCA `PRAGMA table_info`.

    Zwraca ZBIOR NAZW, a nie wiersze: poprzednik siegal po `w[1]`, czyli po
    pozycje w wierszu `PRAGMA`, a `information_schema.columns` ma inny uklad
    kolumn. Numer pozycji byl nosnikiem wiedzy o ksztalcie wyniku sterownika
    — i to jest dokladnie ta wiedza, ktora podmiana sterownika uniewaznia.
    """
    return {w[0] for w in polaczenie.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = current_schema() AND table_name = %s",
        (tabela,)).fetchall()}


#: Kolumny dokladane do tabel, ktore juz istnieja. (tabela, kolumna, typ)
_DOPISYWANE_KOLUMNY = (
    ("przychody_jdg", "data_zaplaty", "DATE"),
    ("przychody_jdg", "wpis_budzetu_id", "BIGINT REFERENCES wpisy_budzetu(id) ON DELETE SET NULL"),
    # Z42: `rok`/`miesiac` zmieniaja znaczenie dla wiersza z `powtarzalna = 1`
    # (staja sie POCZATKIEM obowiazywania). `DEFAULT 0` jest jedynym nosnikiem
    # decyzji Darka nr 2 z 2026-08-26: kazdy wiersz sprzed migracji — w tym 41
    # pozycji z importu arkusza — zostaje pozycja jednorazowa.
    ("plan_budzetu", "powtarzalna", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("plan_budzetu", "do_roku", "INT"),
    ("plan_budzetu", "do_miesiaca", "INT"),
    # D9, zlecenie Darka 2026-08-28 godz. 19:38. Bez `NOT NULL` i bez
    # `DEFAULT`: istniejace wiersze maja dostac NULL, czyli „nie wiem".
    # `DEFAULT '0'` wpisalby wszystkim ZEROWE oprocentowanie — czyli
    # odpowiedz, ktorej nikt nie udzielil, nieodrozninalna od Aliora, ktory
    # naprawde ma 0%.
    ("zobowiazania", "oprocentowanie", "NUMERIC(6,3)"),
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
    ("kategorie", "niezbedna", "BOOLEAN"),
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
    # `testy/test_schemat_wobec_bazy.py::test_OBOWIAZKOWOSC_kolumn_jest_ta_sama_w_napisie_i_w_bazie`.
    # PROG POWROTU WIEZU: pierwszy pisarz, ktory te date wyliczy.
    ("przychody_jdg", "data_obowiazku_vat", "DATE"),
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


def _wymagaj_niesprzecznych_kolumn() -> None:
    """Odmawia, gdy ta sama kolumna jest naraz DOPISYWANA i ZDEJMOWANA.

    To nie jest higiena — to jedyna zmierzona droga do CICHEJ UTRATY DANYCH
    w tym module. Wpis `("zobowiazania", "oprocentowanie")` stal w obu
    krotkach naraz po tym, jak Darek odwrocil decyzje Z43 (2026-08-28):
    `_dopisz_kolumny` odtwarzalo kolumne, a `_zdejmij_kolumny` kasowalo ja
    razem z wpisanym oprocentowaniem — przy KAZDYM otwarciu bazy, po cichu
    i przy zielonej suicie.

    Sprzecznosc jest tu BLEDEM, nie ostrzezeniem: `ALTER TABLE DROP COLUMN`
    jest nieodwracalne, wiec jedyny moment, w ktorym da sie jeszcze cokolwiek
    zrobic, jest PRZED nim.
    """
    dopisywane = {(tab, kol) for tab, kol, _ in _DOPISYWANE_KOLUMNY}
    sprzeczne = sorted(dopisywane & set(_ZDEJMOWANE_KOLUMNY))
    if sprzeczne:
        opis = ", ".join(f"{tab}.{kol}" for tab, kol in sprzeczne)
        raise BladMagazynu(
            f"Kolumna jest naraz dopisywana i zdejmowana: {opis}. "
            f"Migracja NIE zostala rozpoczeta — baza jest nietknieta. "
            f"`ALTER TABLE DROP COLUMN` jest nieodwracalne, wiec skasowalbym "
            f"dane kolumny, ktora ten sam kod chwile wczesniej odtworzyl. "
            f"Rozstrzygnij, ktora z dwoch krotek `_DOPISYWANE_KOLUMNY` / "
            f"`_ZDEJMOWANE_KOLUMNY` niesie decyzje, i usun wpis z drugiej.")


def _zdejmij_kolumny(polaczenie) -> None:
    """Usuwa kolumny wycofane z modelu. NIEODWRACALNE — dane kolumny znikaja.

    Zostawienie martwej kolumny bylo by drugim nosnikiem: tabela dalej
    niosla by wartosc, ktorej nikt nie liczy, a ktora wyglada jak dana.

    Od W2 (2026-08-29) biegnie WYLACZNIE z `zmigruj()`, a nie przy kazdym
    otwarciu bazy — czyli raz przy starcie procesu, nie raz na zadanie HTTP.
    """
    _wymagaj_niesprzecznych_kolumn()
    for tabela, kolumna in _ZDEJMOWANE_KOLUMNY:
        if kolumna in _kolumny(polaczenie, tabela):
            polaczenie.execute(
                f"ALTER TABLE {tabela} DROP COLUMN {kolumna}")


def _dopisz_kolumny(polaczenie) -> None:
    """Dokłada brakujące kolumny do tabel, które już istnieją.

    `CREATE TABLE IF NOT EXISTS` NIE rusza tabeli, która jest — nowa kolumna
    w schemacie powstaje więc wyłącznie w świeżej bazie, a w bazie z danymi
    nie powstałaby nigdy. Bez tego kroku migracja wygląda na wykonaną
    (wersja schematu się podnosi), a kolumny nie ma i zapis pada dopiero
    przy pierwszym użyciu.

    CO SIĘ ZMIENIŁO W W4 (i czego to NIE znaczy). Baza produkcyjna PostgreSQL
    startuje PUSTA (decyzja Darka 2026-08-29), więc dostaje wszystkie kolumny
    od razu z `CREATE TABLE` i żaden wpis z `_DOPISYWANE_KOLUMNY` się dziś nie
    wykonuje. Krotka ZOSTAJE mimo to — razem z bramką sprzeczności — bo to
    mechanizm dla KAŻDEJ kolejnej kolumny, nie pamiątka po SQLite. Typy w niej
    przeniesiono na dialekt PostgreSQL: gdyby mechanizm kiedyś ruszył ze
    starymi typami, założyłby kolumnę `TEXT` tam, gdzie schemat ma `DATE`,
    i rozjazd wyszedłby dopiero przy odczycie.
    """
    for tabela, kolumna, typ in _DOPISYWANE_KOLUMNY:
        if kolumna not in _kolumny(polaczenie, tabela):
            polaczenie.execute(
                f"ALTER TABLE {tabela} ADD COLUMN {kolumna} {typ}")


#: Kolumny `plan_budzetu` po Z48, w kolejnosci zapisu.
_KOLUMNY_PLANU = ("rok", "miesiac", "typ", "kategoria", "kwota_planowana",
                  "powtarzalna", "do_roku", "do_miesiaca", "opis", "dzien",
                  "co_ile_miesiecy")


def _przebuduj_plan_budzetu(polaczenie) -> None:
    """Przenosi `plan_budzetu` na schemat Z48: opis, dzien, cykl.

    W SQLite trzeba było zbudować tabelę od nowa, bo więzu `UNIQUE` nie da się
    tam zdjąć w miejscu. PostgreSQL potrafi to jednym `ALTER TABLE`, więc
    przebudowa zeszła do dwóch poleceń: zdjęcie starego więzu i założenie
    nowego, szerszego o `opis`. Wiersze zostają na miejscu — nie ma przenosin,
    więc nie ma czego zgubić po drodze.

    Wiersze sprzed migracji mają pusty opis (pozycja bezimienna, taka jak
    z importu arkusza) i cykl miesięczny — czyli zachowują się dokładnie jak
    dotąd.
    """
    kolumny = _kolumny(polaczenie, "plan_budzetu")
    if not kolumny or "opis" in kolumny:
        return
    polaczenie.execute(
        "ALTER TABLE plan_budzetu ADD COLUMN opis TEXT NOT NULL DEFAULT ''")
    for nazwa, typ in (("dzien", "INT"),
                       ("co_ile_miesiecy", "INT NOT NULL DEFAULT 1")):
        if nazwa not in kolumny:
            polaczenie.execute(
                f"ALTER TABLE plan_budzetu ADD COLUMN {nazwa} {typ}")
    stary = polaczenie.execute(
        "SELECT conname FROM pg_constraint"
        " WHERE conrelid = 'plan_budzetu'::regclass AND contype = 'u'"
    ).fetchall()
    for (nazwa,) in stary:
        polaczenie.execute(f"ALTER TABLE plan_budzetu DROP CONSTRAINT {nazwa}")
    polaczenie.execute(
        "ALTER TABLE plan_budzetu ADD CONSTRAINT"
        " plan_budzetu_rok_miesiac_typ_kategoria_opis_key"
        " UNIQUE (rok, miesiac, typ, kategoria, opis)")
    polaczenie.commit()


#: Przedrostek przestrzeni nazw, w ktorej mieszka kopia sprzed migracji.
#: Pelna nazwa to przedrostek + nazwa KOPIOWANEJ przestrzeni + znacznik czasu
#: co do minuty — na przyklad `kopia_przed_migracja_public_2026_08_29_1434`.
#:
#: DLACZEGO NAZWA KOPIOWANEJ PRZESTRZENI JEST W NAZWIE KOPII. Przestrzenie
#: nazw leza obok siebie w bazie, nie jedna w drugiej — kopia przestrzeni A
#: i kopia przestrzeni B zrobione w tej samej minucie walczylyby o te sama
#: nazwe. W produkcji jest jedna przestrzen i problem nie istnieje; w suicie
#: testow kazdy test ma wlasna i problem pojawil sie natychmiast (zmierzone
#: 2026-08-29). Nazwa mowi przy okazji, CO zostalo skopiowane — a to jest
#: pierwsze pytanie, ktore ktos zada, gdy przyjdzie odtwarzac.
PRZEDROSTEK_KOPII = "kopia_przed_migracja_"

#: Tabele, ktore niosa STAN MECHANIZMU, nie dane Darka. Kopiuje sie je razem
#: z reszta (kopia ma byc pelna), ale nie licza sie do odpowiedzi na pytanie
#: „czy jest co stracic".
TABELE_SLUZBOWE = frozenset({"wersja_schematu"})


def _przestrzen(polaczenie) -> str:
    """Nazwa przestrzeni, w ktorej pracuje to polaczenie. Jeden nosnik."""
    return polaczenie.execute("SELECT current_schema()").fetchone()[0]


def _teraz() -> datetime:
    """Szew czasu — wydzielony, zeby test mogl ustalic nazwe kopii."""
    return datetime.now()


def _policz_wiersze(polaczenie, tabele, przestrzen: "str | None" = None) -> dict:
    """Ile wierszy w kazdej z tabel — KONTROLA LICZNOSCI kopii.

    Bez niej „kopia powstala" znaczy tylko „polecenia nie wybuchly". Kopia
    czternastu PUSTYCH tabel wyglada dokladnie tak samo jak kopia danych.
    """
    wynik = {}
    for tabela in sorted(tabele):
        pelna = f"{przestrzen}.{tabela}" if przestrzen else tabela
        wynik[tabela] = polaczenie.execute(
            f"SELECT COUNT(*) FROM {pelna}").fetchone()[0]
    return wynik


def _kopia_przed_migracja(polaczenie) -> "str | None":
    """Kopiuje CALA zawartosc bazy, gdy zaraz ruszy migracja schematu.

    NASTEPCA KOPII PLIKU (W4, 2026-08-29) — pozycja obowiazkowa §3.11.
    Do W4 kopia powstawala przez `shutil.copy2` obok pliku `.db`. Baza nie
    jest juz plikiem, wiec ta droga PRZESTALA ISTNIEC. Zastepnik powstaje
    w tym samym zadaniu, nie „pozniej": bramka „kopia zapasowa przed kazda
    zmiana danych" raz juz w tej firmie zablokowala sama siebie, bo zdolnosc
    tworzenia kopii zniknela jako skutek uboczny innej decyzji.

    JAK: nowa przestrzen nazw (`kopia_przed_migracja_RRRR-MM-DD-GGMM`) i w niej
    `CREATE TABLE ... AS SELECT *` z kazdej tabeli. Zwraca nazwe przestrzeni.

    DLACZEGO TAK, A NIE `pg_dump`:
      * `pg_dump` jest PROGRAMEM ZEWNETRZNYM — nie ma go ani w tym srodowisku
        (`which pg_dump` nic nie zwraca), ani w funkcji Vercela, wiec kopia
        istnialaby wylacznie na laptopie i wylacznie wtedy, gdy ktos doinstaluje
        klienta PostgreSQL. Bramka, ktora dziala tylko czasami, nie jest bramka;
      * galaz Neona jest warstwa OBOK, nie zamiast: robi ja czlowiek albo
        mandat v1.15, dotyczy calego projektu i nie wie, ze wlasnie rusza
        migracja. Ta kopia zna dokladnie ten moment.

    CZEGO TA KOPIA NIE DAJE, POWIEDZIANE WPROST: lezy w TEJ SAMEJ bazie.
    Chroni przed zla migracja — czyli przed tym, przed czym chronila kopia
    pliku — ale nie przed utrata calej bazy. Przed tym chroni galaz Neona
    (`prod-backup-*`), robiona osobno.

    Warunek jest podwojny, tak jak byl: baza **ma tabele i ma w nich dane**
    oraz jej wersja jest **nizsza** niz ta, ktora zna kod. Kopia przy kazdym
    otwarciu zasypalaby baze i przestalaby cokolwiek znaczyc.
    """
    tabele = _tabele(polaczenie)
    if not tabele:
        return None
    if _wersja_bazy(polaczenie) >= WERSJA_SCHEMATU:
        return None
    licznosc = _policz_wiersze(polaczenie, tabele)
    # PYTANIE BRZMI „czy jest co stracic", a nie „czy sa jakies wiersze".
    # `wersja_schematu` niesie JEDEN wiersz zawsze — gdyby liczyl sie do tej
    # sumy, kopia powstawalaby takze dla bazy ze schematem i zerem danych,
    # a kopia czternastu pustych tabel wyglada tak samo jak kopia danych
    # i zasmieca liste, na ktorej ktos pozniej szuka ratunku.
    if not sum(ile for tabela, ile in licznosc.items()
               if tabela not in TABELE_SLUZBOWE):
        return None

    # ZNACZNIK CZASU PODKRESLENIAMI, NIE MYSLNIKAMI. Nazwa przestrzeni jest
    # identyfikatorem SQL: mysinik czyta sie tam jako operator odejmowania
    # i `CREATE SCHEMA` odmawia. Cudzyslow rozwiazalby to formalnie, ale
    # nazwa z cudzyslowem wymaga cudzyslowu w KAZDYM pozniejszym uzyciu —
    # a wystarczy jedno zapomniane, zeby odtworzenie z kopii nie znalazlo
    # tabeli w chwili, w ktorej jest najbardziej potrzebne.
    nazwa = (PRZEDROSTEK_KOPII + _przestrzen(polaczenie) + "_"
             + _teraz().strftime("%Y_%m_%d_%H%M"))
    istnieje = polaczenie.execute(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
        (nazwa,)).fetchone()
    if istnieje:
        raise BladMagazynu(
            f"Kopia {nazwa} juz istnieje. Migracja NIE zostala rozpoczeta — "
            f"baza jest nietknieta. Nadpisanie kopii skasowaloby jedyny stan, "
            f"do ktorego dalo by sie wrocic. Zmien nazwe albo skasuj stara "
            f"kopie swiadomie.")
    try:
        polaczenie.execute(f"CREATE SCHEMA {nazwa}")
        for tabela in sorted(tabele):
            polaczenie.execute(
                f"CREATE TABLE {nazwa}.{tabela} AS TABLE {tabela}")
        polaczenie.commit()
    except psycopg.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie udalo sie zrobic kopii bazy przed migracja schematu "
            f"{_wersja_bazy(polaczenie)} → {WERSJA_SCHEMATU}. Migracja NIE "
            f"zostala rozpoczeta — baza jest nietknieta. Szczegol: {e}") from e

    # KONTROLA LICZNOSCI PO SKOPIOWANIU. Bez niej „kopia zrobiona" znaczy
    # tylko „polecenia nie wybuchly" — a kopia, do ktorej nic nie doszlo,
    # melduje sukces dokladnie tak samo jak kopia pelna.
    po = _policz_wiersze(polaczenie, tabele, przestrzen=nazwa)
    if po != licznosc:
        rozjazd = {t: (licznosc[t], po.get(t)) for t in licznosc
                   if licznosc[t] != po.get(t)}
        polaczenie.execute(f"DROP SCHEMA {nazwa} CASCADE")
        polaczenie.commit()
        raise BladMagazynu(
            f"Kopia przed migracja zgubila wiersze (tabela: przed, w kopii): "
            f"{rozjazd}. Kopia skasowana, migracja NIE zostala rozpoczeta — "
            f"baza jest nietknieta.")
    return nazwa


def odtworz_z_kopii(polaczenie, nazwa_kopii: str) -> dict:
    """Wgrywa zawartosc kopii z powrotem do tabel roboczych. Zwraca licznosc.

    DRUGA POLOWA KOPII. Kopia, ktorej nikt nie potrafi odtworzyc, jest
    plikiem, nie kopia — a „umiem odtworzyc" bez wykonywalnej drogi jest
    deklaracja, nie dowodem. Strażnik:
    `testy/test_kopia_przed_migracja.py::test_kopia_DA_SIE_odtworzyc`.

    CO PRZEZ TO PRZESTANIE DZIALAC (wolajacy ma to wiedziec PRZED, nie po):
    zawartosc tabel roboczych ZNIKA i zastepuje ja zawartosc kopii. Wiersze
    dopisane po zrobieniu kopii sa tracone. Dlatego to jest osobna funkcja
    wolana swiadomie, a nie galaz w `zmigruj()`.
    """
    istnieje = polaczenie.execute(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
        (nazwa_kopii,)).fetchone()
    if not istnieje:
        raise BladMagazynu(
            f"Nie ma kopii o nazwie {nazwa_kopii}. Dostepne: "
            + (", ".join(kopie(polaczenie)) or "zadna") + ".")
    tabele = {w[0] for w in polaczenie.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
        (nazwa_kopii,)).fetchall()}
    try:
        with polaczenie.transaction():
            for tabela in sorted(tabele):
                polaczenie.execute(f"DELETE FROM {tabela}")
            for tabela in sorted(tabele):
                polaczenie.execute(
                    f"INSERT INTO {tabela} SELECT * FROM {nazwa_kopii}.{tabela}")
    except psycopg.Error as e:
        raise BladMagazynu(
            f"Odtworzenie z kopii {nazwa_kopii} nie doszlo do konca — nic "
            f"nie zostalo zmienione. Szczegol: {e}") from e
    return _policz_wiersze(polaczenie, tabele)


def kopie(polaczenie) -> list[str]:
    """Nazwy kopii TEJ przestrzeni, od najstarszej. Jeden nosnik tej listy.

    Kopie cudzych przestrzeni nie sa tu widoczne — pytanie brzmi „do jakiego
    stanu MOJEJ bazy da sie wrocic", a nie „ile kopii lezy w tej instancji".
    """
    return [w[0] for w in polaczenie.execute(
        "SELECT schema_name FROM information_schema.schemata"
        " WHERE schema_name LIKE %s ORDER BY schema_name",
        (PRZEDROSTEK_KOPII + _przestrzen(polaczenie) + "_%",)).fetchall()]


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
        "INSERT INTO forma_opodatkowania (rok, forma) VALUES (%s,%s)",
        (ROK_ZACZEPU_FORMY, FORMA_SKALA))
    polaczenie.commit()


def _wersja_bazy(polaczenie) -> int:
    """JEDEN nośnik odpowiedzi „w jakiej wersji schematu jest ta baza".

    NASTEPCA `PRAGMA user_version` (W4). PostgreSQL nie ma miejsca na wlasna
    liczbe przy pliku bazy — bo nie ma pliku. Wersja mieszka wiec w tabeli
    `wersja_schematu` (JEDEN wiersz, wiez `CHECK (jedyny)` pilnuje, ze drugi
    sie nie da wpisac).

    Baza bez tej tabeli jest baza w wersji ZERO — czyli taka, ktorej nikt
    jeszcze nie zmigrowal. Zero, a nie blad: to normalny stan poczatkowy.
    """
    if "wersja_schematu" not in _tabele(polaczenie):
        return 0
    wiersz = polaczenie.execute(
        "SELECT wersja FROM wersja_schematu WHERE jedyny").fetchone()
    return wiersz[0] if wiersz else 0


def _ostempluj_wersje(polaczenie, wersja: int) -> None:
    """Zapisuje wersje schematu. Jeden wiersz, nadpisywany."""
    polaczenie.execute(
        "INSERT INTO wersja_schematu (jedyny, wersja) VALUES (TRUE, %s)"
        " ON CONFLICT (jedyny) DO UPDATE SET wersja = excluded.wersja",
        (int(wersja),))


def _sprawdz_wersje(polaczenie, wersja: int | None = None) -> None:
    """Odmawia otwarcia bazy nowszej niż ten kod.

    Bez tego starszy checkout na zmigrowanej bazie odtworzyłby przez schemat
    pustą tabelę i pokazał na pulpicie 0,00 zł. Cicha zła liczba jest gorsza
    niż odmowa — dlatego wersja stoi w bazie i jest sprawdzana przy otwarciu.
    """
    wersja = _wersja_bazy(polaczenie) if wersja is None else wersja
    if wersja > WERSJA_SCHEMATU:
        raise BladMagazynu(
            f"Baza jest w wersji schematu {wersja}, a ten kod zna "
            f"{WERSJA_SCHEMATU}. Uruchamiasz starszą wersję aplikacji na "
            "nowszej bazie — odmawiam otwarcia, bo pokazałbym Ci zera zamiast "
            "Twoich danych."
        )


def _wymagaj_zmigrowanej(polaczenie, adres, wersja: int | None = None) -> None:
    """Odmawia otwarcia bazy, której schemat jest STARSZY niż ten kod.

    NASTĘPCA SAMOCZYNNEJ MIGRACJI (W2, 2026-08-29). Do tej zmiany `polacz()`
    migrowało bazę samo, przy każdym otwarciu — czyli przy każdym żądaniu HTTP
    (`api/wspolne.py`), bo połączenie jest brane na żądanie. Po rozdzieleniu
    migracja jest osobnym, świadomym wywołaniem; gdyby nikt jej nie wywołał,
    aplikacja wstałaby na bazie bez tabel i pokazała zera zamiast odmowy.

    Dlatego odmowa jest tutaj, a nie w warstwie sieciowej: to jedyne miejsce,
    przez które przechodzi KAŻDE otwarcie bazy. §3.7 — awaria do stanu
    użytecznego: mówi, czego brakuje i co zrobić.

    Komunikat niesie adres BEZ HASLA — jeden nosnik tej reguly stoi
    w `adres_bez_hasla`.
    """
    wersja = _wersja_bazy(polaczenie) if wersja is None else wersja
    if wersja == WERSJA_SCHEMATU:
        return
    raise BladMagazynu(
        f"Baza pod adresem {adres_bez_hasla(adres)} jest w wersji schematu "
        f"{wersja}, a ten kod zna {WERSJA_SCHEMATU} — odmawiam otwarcia, bo "
        f"pokazałbym Ci zera zamiast Twoich danych albo wywrócił się na "
        f"pierwszym zapisie. Migracja nie dzieje się już sama przy otwarciu "
        f"(W2): uruchom ją świadomie — `magazyn.zmigruj()` albo "
        f"`./.venv/bin/python -m silnik.rdzen.magazyn` — a potem powtórz "
        f"tę operację. Kopia bazy powstanie przed migracją.")


@dataclass(frozen=True)
class RaportMigracjiSchematu:
    """Wynik jednego przebiegu `zmigruj()` — liczby, nigdy wartość logiczna.

    Ta sama zasada co w `RaportMigracji`: migracja, która nic nie zrobiła, ma
    to powiedzieć liczbą. „Gotowe" nie odróżnia bazy postawionej od bazy,
    której nikt nie tknął.
    """

    adres: str
    wersja_przed: int
    wersja_po: int
    kopia: "str | None"
    tabel: int
    kategorii: int
    stawek: int
    wchloniete: "RaportMigracji | None"


def _otworz_surowo(adres: str) -> "psycopg.Connection":
    """Samo otwarcie polaczenia. Bez schematu, bez zasiewu, bez wersji.

    CO ZNIKNELO RAZEM ZE STEROWNIKIEM SQLite: `check_same_thread=False`.
    Tamten sterownik blokowal uzycie polaczenia w innym watku wlasna blokada
    i trzeba ja bylo zdejmowac, zeby narzedzia doradcy mogly czytac z puli
    watkow SDK. psycopg takiej blokady nie ma — polaczenie wolno przekazac
    miedzy watkami, byle nie uzywac go z dwoch naraz. Nasza warstwa sieciowa
    bierze polaczenie NA ZADANIE (`api/wspolne.polaczenie`), wiec dwoch
    uzytkownikow jednego polaczenia nie ma.
    """
    try:
        return psycopg.connect(adres)
    except psycopg.Error as e:
        raise BladMagazynu(
            f"Nie udało się otworzyć bazy danych pod adresem "
            f"{adres_bez_hasla(adres)}. Sprawdź, czy serwer działa i czy "
            f"poświadczenia są aktualne. Szczegół: {e}"
        ) from e


def polacz(adres: "str | None" = None) -> "psycopg.Connection":
    """OTWIERA BAZĘ I TYLKO OTWIERA. Zero DDL, zero zasiewu, zero stempla.

    ROZDZIELENIE „OTWÓRZ" OD „ZMIGRUJ" (W2, 2026-08-29). Do tej zmiany ta
    funkcja stawiała cały schemat przy każdym wywołaniu: **98 poleceń SQL,
    z czego 59 piszących** (15 × `CREATE TABLE`, 44 × `INSERT` zasiewu) —
    zmierzone sondą na świeżej bazie. A połączenie jest brane NA ŻĄDANIE HTTP
    (`api/wspolne.polaczenie`), nie na proces. Przy pliku SQLite było to
    niewidoczne; przy PostgreSQL byłby to pełny DDL na każdym żądaniu.

    Migracja mieszka teraz w `zmigruj()` i jest wywoływana świadomie — raz,
    przy starcie procesu (`api/index.py`).

    Baza niezmigrowana NIE jest tu po cichu naprawiana: `polacz()` **odmawia
    otwarcia** i mówi, co uruchomić (`_wymagaj_zmigrowanej`). Cicha zła liczba
    jest gorsza niż odmowa.

    Bez argumentu pyta `adres_bazy()` — jeden nośnik odpowiedzi „którą bazę
    otwieramy". Argument zostaje i wygrywa ze zmienną środowiskową.
    """
    if adres is None:
        adres = adres_bazy()
    polaczenie = _otworz_surowo(adres)
    try:
        # JEDEN odczyt wersji na otwarcie — obie bramki dostają tę samą liczbę.
        # Dwa odczyty byłyby drugim nośnikiem odpowiedzi „w jakim stanie jest
        # ta baza" i kosztowałyby dwa obiegi do serwera.
        wersja = _wersja_bazy(polaczenie)
        _sprawdz_wersje(polaczenie, wersja)
        _wymagaj_zmigrowanej(polaczenie, adres, wersja)
    except BaseException:
        # Odmowa nie zostawia otwartego polaczenia. Bez tego kazde nieudane
        # otwarcie trzymalo by sesje na serwerze do konca zycia procesu —
        # a liczba sesji jest u dostawcy zasobem z limitem.
        polaczenie.close()
        raise
    return polaczenie


def zmigruj(adres: "str | None" = None) -> RaportMigracjiSchematu:
    """Stawia schemat i zasiewa słowniki. ŚWIADOME, JEDNORAZOWE WYWOŁANIE.

    Wszystko, co `polacz()` robiło do W2 poza samym otwarciem: kopia przed
    migracją, napis DDL, dopisanie i zdjęcie kolumn, przebudowa planu, zaczep
    formy, wchłonięcie starej tabeli wydatków, dwa zasiewy i stempel wersji.

    SCHEMAT WOLA JEDEN NOSNIK — `silnik.baza.schemat_postgresql()`, ktory
    sklada `silnik/baza/schemat.sql` z `wiedza/rejestr.SCHEMAT`. Do W4 stal
    tu drugi napis DDL w dialekcie SQLite; jego prog konsolidacji brzmial
    „znika, gdy aplikacja przestanie otwierac SQLite" i wlasnie zadzialal.

    IDZIE POLACZENIEM BEZPOSREDNIM, z pominieciem puli (`adres_migracji`):
    pula nie utrzymuje sesji miedzy poleceniami, a migracja jest jedna sesja
    od poczatku do konca.

    OTWIERA I ZAMYKA WŁASNE POŁĄCZENIE — nie przyjmuje cudzego i nie oddaje
    swojego. Gdyby oddawała, ktoś trzymałby połączenie „po migracji" i różnica
    między „otwarte" a „zmigrowane" wróciłaby tylnymi drzwiami.

    Jest bezpieczna w powtórzeniu (`CREATE TABLE IF NOT EXISTS`, zasiewy pod
    warunkiem pustki), ale kosztuje kilkadziesiąt poleceń SQL — nie należy do
    ścieżki żądania.
    """
    adres = adres_migracji(adres)
    polaczenie = _otworz_surowo(adres)
    try:
        _sprawdz_wersje(polaczenie)
        wersja_przed = _wersja_bazy(polaczenie)
        # Kopia PRZED czymkolwiek, co pisze: `_dopisz_kolumny`,
        # `_zdejmij_kolumny` (NIEODWRACALNE) i `_przebuduj_plan_budzetu`.
        kopia = _kopia_przed_migracja(polaczenie)
        tabele_przed = _tabele(polaczenie)
        # KOLEJNOSC: tabele -> brakujace kolumny -> indeksy. Indeks czesciowy
        # `wpisy_do_rachunku` ma warunek na kolumnie `zrodlo`, ktorej baza
        # sprzed schematu 12 NIE MA — a `CREATE TABLE IF NOT EXISTS` jej nie
        # dokłada. Napis wykonany w calosci wywracal cala migracje na indeksie
        # (zmierzone 2026-08-29 na strazniku migracji ze schematu 11).
        tabele_ddl, indeksy_ddl = baza_schematu.tabele_i_indeksy()
        polaczenie.execute(tabele_ddl)
        polaczenie.commit()
        _dopisz_kolumny(polaczenie)
        _zdejmij_kolumny(polaczenie)
        _przebuduj_plan_budzetu(polaczenie)
        polaczenie.execute(indeksy_ddl)
        polaczenie.commit()
        _zaczep_formy(polaczenie)
        wchloniete = None
        if "wydatki_osobiste" in tabele_przed:
            wchloniete = wchlon_wydatki_osobiste(polaczenie)
        kategorii = zasiej_kategorie(polaczenie)
        stawek = zasiej_rejestr_stawek(polaczenie)
        _ostempluj_wersje(polaczenie, WERSJA_SCHEMATU)
        polaczenie.commit()
        return RaportMigracjiSchematu(
            adres=adres_bez_hasla(adres),
            wersja_przed=wersja_przed,
            wersja_po=_wersja_bazy(polaczenie),
            kopia=kopia,
            tabel=len(_tabele(polaczenie)),
            kategorii=kategorii,
            stawek=stawek,
            wchloniete=wchloniete,
        )
    except psycopg.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Migracja schematu bazy {adres_bez_hasla(adres)} nie doszła do "
            f"końca. Szczegół: {e}") from e
    finally:
        polaczenie.close()


def zmigruj_i_polacz(adres: "str | None" = None) -> "psycopg.Connection":
    """Migracja, a zaraz po niej otwarcie — DLA TESTÓW I NARZĘDZI Z WIERSZA POLECEŃ.

    NIE DO UŻYCIA W ŚCIEŻCE ŻĄDANIA HTTP. Wołanie tego na żądanie odtwarza
    dokładnie tę wadę, którą W2 zdejmuje: pełny DDL przy każdym żądaniu.
    Pilnuje tego strażnik `testy/test_otworz_a_zmigruj.py::
    test_warstwa_sieciowa_NIE_MIGRUJE_na_zadanie`, który czyta źródło `api/`.
    """
    zmigruj(adres)
    return polacz(adres)


# --- migracja i zasiew ----------------------------------------------------

def _liczba_wydatkow_w_budzecie(polaczenie) -> int:
    if "wpisy_budzetu" not in _tabele(polaczenie):
        return 0
    return polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu WHERE typ = %s",
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
            "SELECT data, %s, kategoria, kwota, '' FROM wydatki_osobiste",
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
                "INSERT INTO kategorie (typ, nazwa, kolejnosc, aktywna)"
                " VALUES (%s,%s,%s,TRUE)"
                " ON CONFLICT (typ, nazwa) DO NOTHING",
                (typ, nazwa, kolejnosc))
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
# `testy/test_rejestr_ddl.py::test_rejestr_MA_dane_i_NIE_MA_konsumenta`.

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
            "WHERE klucz = %s AND obowiazuje_od = %s AND wartosc = %s",
            (s.klucz, s.obowiazuje_od, s.wartosc)).fetchone()
        if istnieje:
            continue
        polaczenie.execute(
            "INSERT INTO rejestr_stawek (klucz, wartosc, jednostka,"
            " obowiazuje_od, obowiazuje_do, podstawa_prawna, zrodlo_url,"
            " data_odczytu, status, zatwierdzil, data_zatwierdzenia,"
            " niezweryfikowane, opis) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (s.klucz, s.wartosc, s.jednostka, s.obowiazuje_od,
             s.obowiazuje_do,
             s.podstawa_prawna, s.zrodlo_url, s.data_odczytu,
             s.status, s.zatwierdzil, s.data_zatwierdzenia,
             s.niezweryfikowane, s.opis))
        dodane += 1
    polaczenie.commit()
    return dodane


def _stawka_z_wiersza(w: dict) -> "rejestr_wiedzy.Stawka":
    """Wiersz bazy -> `Stawka`. Wiersz jest SLOWNIKIEM, nie krotka.

    DLACZEGO PO NAZWIE, A NIE PO NUMERZE (W4). Do podmiany sterownika stalo tu
    trzynascie odczytow `w[0]`…`w[12]`, sparowanych z recznie wypisana
    kolejnoscia kolumn w `SELECT` nizej. Dopisanie kolumny W SRODKU listy
    przesuwalo wszystkie nastepne o jeden i kazda wartosc ladowala w sasiednim
    polu — bez wyjatku, bez czerwonego testu, po cichu. Numer pozycji byl
    drugim nosnikiem kolejnosci kolumn; nazwa jest pierwszym i jedynym.

    Konwersji typow prawie tu nie ma i to jest skutek migracji: kolumna
    `NUMERIC` wraca jako `Decimal`, a `DATE` jako `date`, prosto ze sterownika.
    Zostaje `opis` — bo `NULL` w opisie ma znaczyc pusty napis, nie brak.
    """
    return rejestr_wiedzy.Stawka(
        klucz=w["klucz"], wartosc=w["wartosc"], jednostka=w["jednostka"],
        obowiazuje_od=w["obowiazuje_od"], obowiazuje_do=w["obowiazuje_do"],
        podstawa_prawna=w["podstawa_prawna"], zrodlo_url=w["zrodlo_url"],
        data_odczytu=w["data_odczytu"], status=w["status"],
        zatwierdzil=w["zatwierdzil"],
        data_zatwierdzenia=w["data_zatwierdzenia"],
        niezweryfikowane=w["niezweryfikowane"], opis=w["opis"] or "")


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
        sql += " WHERE status = %s"
        parametry = (status,)
    sql += " ORDER BY klucz, obowiazuje_od"
    with polaczenie.cursor(row_factory=dict_row) as kursor:
        kursor.execute(sql, parametry)
        return [_stawka_z_wiersza(w) for w in kursor.fetchall()]


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


def wymagaj_typu(typ: str) -> str:
    """Trzy dozwolone typy wpisu — jedyne miejsce, gdzie ta reguła jest sprawdzana."""
    if typ not in budzet.TYPY:
        raise BladMagazynu(
            f"Nieznany typ wpisu: {typ!r}. Dozwolone są wyłącznie: "
            + ", ".join(budzet.TYPY) + "."
        )
    return typ


def wymagaj_kategorii(polaczenie, typ: str, kategoria: str) -> str:
    """Kategoria musi istnieć w słowniku, w TYM SAMYM typie, i być aktywna.

    Para (typ, nazwa), nie sama nazwa: `Inne` jest jednocześnie kategorią
    przychodu i wydatku, a to dwie różne pozycje budżetu.

    PUBLICZNA OD W9b. Trasa `POST /api/plan` musi sprawdzić kategorię
    **przed** zapisem, a `ustal_regule_planu` tego nie robi — jest wołane
    także przez import arkusza, który zasiewa słownik i plan w jednym
    przebiegu. Warstwa ekranu woła więc ten sam, jedyny nośnik reguły
    zamiast pytać bazę po swojemu. Bez tego `kategoria=None` z żądania HTTP
    trafiało do bazy jako pozycja planu o nazwie „None": kwota w planie,
    której żaden wpis nigdy nie wykona, i której nie widać jako błędu.
    """
    kategoria = str(kategoria).strip()
    wiersz = polaczenie.execute(
        "SELECT aktywna FROM kategorie WHERE typ = %s AND nazwa = %s",
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


#: Nazwa wiezu jednoznacznosci numeru faktury — JEDEN NOSNIK po stronie kodu.
#: Drugi nosnik tej nazwy stoi w `silnik/baza/schemat.sql` (tam ja zaklada
#: baza) i jest SWIADOMY: napisu DDL nie da sie stad zawolac bez wykonania go.
#: PROG KONSOLIDACJI: gdy nazwy wiezow zaczna powstawac z Pythona.
#: Straznik rozjazdu: `testy/test_komunikat_duplikatu_faktury.py::
#: test_nazwa_wiezu_z_KODU_zgadza_sie_z_nazwa_z_BAZY` (mutacja M-W4-2).
WIEZ_NUMER_FAKTURY = "numer_faktury_niepowtarzalny"


def _zapisz(polaczenie, sql: str, wartosci: tuple) -> "int | None":
    """Jeden zapis wraz z zatwierdzeniem. Zwraca numer wstawionego wiersza.

    NUMER PRZEZ `RETURNING id`, NIE PRZEZ `lastrowid` (W4). psycopg nie ma
    odpowiednika `lastrowid` — a nawet gdyby miał, byłby to numer „ostatniego
    zapisu na tym połączeniu", czyli odpowiedź na inne pytanie niż „jaki numer
    dostał TEN wiersz". Kto pyta o numer, ten dopisuje `RETURNING id` do
    swojego polecenia; kto nie pyta — dostaje `None`, nie zgadywaną liczbę.

    ROZPOZNANIE DUPLIKATU IDZIE PO NAZWIE WIEZU, NIE PO TRESCI KOMUNIKATU.
    Do W4 stalo tu `if "numer_faktury" in str(e)`. Ten napis wystepuje takze
    w automatycznej nazwie, ktora PostgreSQL nadalby wiezowi bez nazwy
    wlasnej — warunek przezylby migracje PRZYPADKIEM. `e.diag.constraint_name`
    jest odpowiedzia samego serwera na pytanie „ktory wiez", a nie zdaniem,
    ktore ktos moze przeredagowac.
    """
    try:
        kursor = polaczenie.execute(sql, wartosci)
        wiersz = kursor.fetchone() if kursor.description else None
        polaczenie.commit()
        return wiersz[0] if wiersz else None
    except psycopg.errors.UniqueViolation as e:
        polaczenie.rollback()
        if e.diag.constraint_name == WIEZ_NUMER_FAKTURY:
            raise BladMagazynu(
                f"Faktura o tym numerze już jest w bazie ({wartosci[1]}). "
                "Numery faktur muszą być niepowtarzalne."
            ) from e
        raise BladMagazynu(f"Zapis odrzucony przez bazę. Szczegół: {e}") from e
    except psycopg.errors.IntegrityError as e:
        polaczenie.rollback()
        raise BladMagazynu(f"Zapis odrzucony przez bazę. Szczegół: {e}") from e
    except psycopg.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(f"Nie udało się zapisać danych. Szczegół: {e}") from e


def _ramka(polaczenie, sql: str, parametry: tuple = ()) -> pd.DataFrame:
    """JEDYNA droga odczytu do ramki danych — nastepca `pd.read_sql`.

    DLACZEGO NIE `pd.read_sql` (W4). Biblioteka ramek obsluguje SUROWE
    polaczenie wylacznie dla sterownika SQLite; dla kazdego innego chce
    obiektu SQLAlchemy. Gorsze od ostrzezenia jest jednak to, co robi po
    drodze: `coerce_float` ma wartosc domyslna „prawda", wiec `Decimal`
    oddany przez psycopg wracal by jako liczba ZMIENNOPRZECINKOWA i gubil
    grosze przy zielonej suicie (zmierzone 2026-08-29 na pandas 3.0.5:
    `read_sql` domyslnie -> dtype float64; `coerce_float=False` -> dtype
    object). To jest dokladnie awaria, dla ktorej zbudowano cala konstrukcje
    kwotowa tego modulu.

    Zamiast tego: kursor oddajacy wiersze jako slowniki i ramka skladana
    z `dtype=object`. Zaden krok nie ma okazji zamienic typu.

    TO JEST SZEW, KTORY PODGLADA STRAZNIK. `testy/test_kwoty_pozostaja_dziesietne.py`
    podmienia te funkcje, zeby zobaczyc ramke TAK, JAK WYSZLA ZE STEROWNIKA —
    przed naprawa typu w `_wczytaj`. Do W4 podgladal `pd.read_sql`; przy
    podmianie sterownika wykryl WLASNE OSLEPIENIE i padl z komunikatem
    „szpieg nie zobaczyl ani jednego odczytu" (mutacja M10). Podglad zostal
    PRZENIESIONY tutaj, a nie wyciszony.
    """
    with polaczenie.cursor(row_factory=dict_row) as kursor:
        kursor.execute(sql, parametry)
        wiersze = kursor.fetchall()
        nazwy = [k.name for k in kursor.description] if kursor.description else []
    return pd.DataFrame(wiersze, columns=nazwy, dtype=object)


def _wczytaj(polaczenie, tabela: str, warunek: str = "",
             parametry: tuple = ()) -> pd.DataFrame:
    """Cala tabela (albo jej wycinek) jako ramka, z kwotami w typie dziesietnym.

    NAZWA TABELI JEST LITERALEM Z KODU, NIE DANYMI OD WOLAJACEGO — sprawdzone
    2026-08-29: czternascie z czternastu wywolan podaje napis wpisany tutaj
    w module. Zeby to przestalo byc obietnica, `_wczytaj` odmawia tabeli spoza
    schematu: `_TABELE_ZNANE` jest jedynym zbiorem dopuszczalnych nazw.
    Wzorzec „nazwa tabeli wklejona do napisu SQL" WYGLADA jak dziura na tyle,
    ze warto go domknac przy okazji, nawet gdy dziura nie istnieje.

    `SELECT *` ZOSTAJE — ŚWIADOMIE, z nazwaniem miny. Kolumna dolozona przez
    `ALTER TABLE` ladowala u poprzednika NA KONCU w bazie starej, a W SRODKU
    w swiezej; kod ratowal sie tym, ze siega po NAZWIE, nie po numerze
    pozycji. Po W4 ta mina jest rozbrojona z dwoch stron naraz:
      * ramka powstaje z wierszy-slownikow (`_ramka`), wiec kolejnosc kolumn
        nie ma zadnego wplywu na to, co gdzie wyladuje;
      * jedyne miejsce, ktore czytalo po NUMERZE pozycji — `_stawka_z_wiersza`,
        trzynascie odczytow `w[0]`…`w[12]` — czyta teraz po nazwie.
    Wypisanie kolumn wprost byloby za to DRUGIM NOSNIKIEM listy kolumn obok
    `schemat.sql` i rozjechaloby sie przy pierwszej dolozonej kolumnie.
    """
    if tabela not in _TABELE_ZNANE:
        raise BladMagazynu(
            f"Nieznana tabela: {tabela!r}. Odczyt idzie wylacznie do tabel "
            f"ze schematu: " + ", ".join(sorted(_TABELE_ZNANE)) + ".")
    try:
        df = _ramka(polaczenie, f"SELECT * FROM {tabela} {warunek}", parametry)
    except psycopg.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie udało się odczytać tabeli {tabela}. Szczegół: {e}") from e
    for kolumna in _KWOTOWE.get(tabela, []):
        if kolumna in df.columns:
            df[kolumna] = df[kolumna].map(
                lambda x: Decimal(str(x)) if x is not None else None)
    return df


# --- przychody ------------------------------------------------------------

def zapisz_fakture(polaczenie, *, data: date, numer_faktury: str,
                   kwota_netto: Decimal, stawka_vat: Decimal, kwota_vat: Decimal,
                   pkwiu: str, zaplacony_zus: Decimal,
                   zysk_netto: Decimal, stawki_wersja: str,
                   stawka_ryczaltu: "Decimal | None" = None) -> int:
    """Jedna faktura sprzedazy. Zwraca jej numer wewnetrzny.

    `stawka_ryczaltu` JEST OPCJONALNA I `None` ZNACZY „NIE DOTYCZY" (W4,
    domkniecie dlugu odlozonego imiennie do tego zadania). Do W4 kolumna byla
    obowiazkowa, a Darek jest na SKALI — przy skali stawka ryczaltu nie
    istnieje, wiec jedyna droga do spelnienia wiezu bylo wpisanie ZERA. Zero
    jest odpowiedzia („ryczalt zero procent"), a nie brakiem odpowiedzi;
    kolumna wypelniana zerem produkowala slad, ktory KLAMIE o tym, czym
    policzono fakture. To ta sama regula, ktora w `forma_opodatkowania`
    trzyma `stawka_ryczaltu` pusta przy skali.

    Kolumna nie ma dzis ZADNEGO czytelnika w silniku (zmierzone 2026-08-29:
    wszystkie odczyty `stawka_ryczaltu` ida z `forma_opodatkowania`), wiec
    zmiana nie rusza zadnej liczby — rusza to, co faktura o sobie mowi.
    """
    pkwiu = _wymagaj_pkwiu(pkwiu)
    if not str(numer_faktury).strip():
        raise BladMagazynu("Numer faktury jest wymagany — bez niego nie odróżnisz "
                           "dwóch faktur wystawionych tego samego dnia.")
    return _zapisz(polaczenie,
        "INSERT INTO przychody_jdg (data, numer_faktury, kwota_netto, stawka_vat,"
        " kwota_vat, pkwiu, stawka_ryczaltu, zaplacony_zus, zysk_netto, stawki_wersja)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (data, str(numer_faktury).strip(), kwota_netto,
         stawka_vat, kwota_vat, pkwiu, stawka_ryczaltu,
         zaplacony_zus, zysk_netto, stawki_wersja))


def wczytaj_faktury(polaczenie, od: date | None = None, do: date | None = None) -> pd.DataFrame:
    if od and do:
        return _wczytaj(polaczenie, "przychody_jdg",
                        "WHERE data >= %s AND data <= %s ORDER BY data, id",
                        (od, do))
    return _wczytaj(polaczenie, "przychody_jdg", "ORDER BY data, id")


def _granice_miesiaca(rok: int, miesiac: int) -> tuple:
    """Pierwszy dzien miesiaca i pierwszy dzien nastepnego — JEDEN nosnik.

    NASTEPCA WZORCA `data LIKE '2026-09%'` (W4). Wzorzec dzialal, dopoki data
    byla NAPISEM. Kolumna jest teraz typu `DATE`, wiec porownanie idzie
    zakresem — i przy okazji przestaje byc przeszukaniem calej tabeli.

    Zakres jest polotwarty (`>= od AND < do`), a nie `BETWEEN`: `BETWEEN`
    z ostatnim dniem miesiaca wymagalby liczenia, ile ten miesiac ma dni,
    czyli drugiego miejsca na pomylke.
    """
    return (date(rok, miesiac, 1),
            date(rok + 1, 1, 1) if miesiac == 12 else date(rok, miesiac + 1, 1))


def czy_skladki_naliczone_w_miesiacu(polaczenie, rok: int, miesiac: int) -> bool:
    """Czy w tym miesiącu któraś faktura odłożyła już rezerwę na ZUS.

    Faktura z zerowym ZUS-em NIE ustawia tej flagi — to właśnie druga faktura
    w miesiącu, która składek już nie nalicza.
    """
    od, do = _granice_miesiaca(rok, miesiac)
    df = _wczytaj(polaczenie, "przychody_jdg",
                  "WHERE data >= %s AND data < %s", (od, do))
    if df.empty:
        return False
    return bool((df["zaplacony_zus"] > Decimal("0")).any())


def przychod_narastajaco(polaczenie, rok: int) -> Decimal:
    """Suma przychodów netto od początku roku — podstawa ustalenia progu zdrowotnej."""
    df = _wczytaj(polaczenie, "przychody_jdg",
                  "WHERE data >= %s AND data < %s",
                  (date(rok, 1, 1), date(rok + 1, 1, 1)))
    if df.empty:
        return Decimal("0.00")
    return sum(df["kwota_netto"], Decimal("0.00"))


# --- godziny --------------------------------------------------------------

def zapisz_godziny(polaczenie, *, data: date, rodzaj_czynnosci: str, pkwiu: str,
                   liczba_godzin: Decimal, opis: str = "") -> int:
    pkwiu = _wymagaj_pkwiu(pkwiu)
    return _zapisz(polaczenie,
        "INSERT INTO godziny (data, rodzaj_czynnosci, pkwiu, liczba_godzin, opis)"
        " VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (data, rodzaj_czynnosci, pkwiu, liczba_godzin, opis))


def wczytaj_godziny(polaczenie, od: date | None = None, do: date | None = None) -> pd.DataFrame:
    if od and do:
        return _wczytaj(polaczenie, "godziny",
                        "WHERE data >= %s AND data <= %s ORDER BY data, id",
                        (od, do))
    return _wczytaj(polaczenie, "godziny", "ORDER BY data, id")


# --- wpisy budżetu --------------------------------------------------------

#: Zapis wpisu budzetu — JEDEN napis SQL dla obu wolajacych.
_SQL_WPISU = ("INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota,"
              " szczegoly) VALUES (%s,%s,%s,%s,%s) RETURNING id")


def _przygotuj_wpis(polaczenie, *, data: date, typ: str, kategoria: str,
                    kwota: Decimal, szczegoly: str = "") -> tuple:
    """Sprawdza reguly wpisu budzetu i zwraca (sql, wartosci). NIC NIE ZAPISUJE.

    JEDEN NOSNIK REGUL, DWIE POLITYKI ZATWIERDZANIA (W4). `zapisz_wpis`
    zapisuje i zatwierdza od razu; `zapisz_koszt` i `oznacz_fakture_zaplacona`
    wolaja to samo WEWNATRZ wspolnej transakcji z drugim zapisem, zeby nie
    zostawic osieroconego wpisu, gdy drugi zapis padnie.

    Rozdzielenie jest tutaj, a nie w znaczniku „nie zatwierdzaj" przewleczonym
    przez `zapisz_wpis` i `_zapisz`: taki znacznik musialby przejsc przez dwie
    funkcje i przy pierwszym zapomnieniu dawalby ciche zatwierdzenie w srodku
    cudzej transakcji.
    """
    typ = wymagaj_typu(typ)
    kategoria = wymagaj_kategorii(polaczenie, typ, kategoria)
    if Decimal(str(kwota)) < 0:
        raise BladMagazynu(
            f"Kwota wpisu nie może być ujemna ({kwota}). Kierunek wynika "
            f"z typu wpisu, nie ze znaku liczby.")
    return _SQL_WPISU, (data, typ, kategoria, kwota, szczegoly)


def zapisz_wpis(polaczenie, *, data: date, typ: str, kategoria: str,
                kwota: Decimal, szczegoly: str = "") -> int:
    """Jeden wpis budżetu. Kwota zawsze DODATNIA — znak niesie `typ`.

    Gdyby znak siedział w kwocie, każde zestawienie musiałoby zgadywać, czy
    liczba jest już ze znakiem, czy jeszcze nie.
    """
    sql, wartosci = _przygotuj_wpis(polaczenie, data=data, typ=typ,
                                    kategoria=kategoria, kwota=kwota,
                                    szczegoly=szczegoly)
    return _zapisz(polaczenie, sql, wartosci)


def wczytaj_wpisy(polaczenie, *, od: date | None = None, do: date | None = None,
                  typ: str | None = None) -> pd.DataFrame:
    """Wpisy budżetu, z opcjonalnym filtrem po zakresie dat i po typie.

    Filtr `typ` jest tu nie dla wygody: po wchłonięciu starej tabeli wydatków
    ta jedna tabela trzyma przychody, wydatki i oszczędności naraz. Sumowanie
    jej bez filtru daje liczbę, która wygląda jak wydatki i nią nie jest.
    """
    warunki, parametry = [], []
    if od is not None:
        warunki.append("data >= %s")
        parametry.append(od)
    if do is not None:
        warunki.append("data <= %s")
        parametry.append(do)
    if typ is not None:
        warunki.append("typ = %s")
        parametry.append(wymagaj_typu(typ))
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "wpisy_budzetu",
                    f"{gdzie} ORDER BY data, id", tuple(parametry))


def usun_wpis(polaczenie, *, wpis_id: int) -> None:
    """Kasuje JEDEN wpis budżetu, po identyfikatorze.

    Bez tego pomyłkowo wpisana kwota zostaje w bazie na zawsze i psuje każde
    zestawienie, w którym się pojawia. Brak wiersza o podanym numerze jest
    błędem, nie cichą zgodą — inaczej pomyłka w numerze wygląda jak sukces.
    """
    kursor = polaczenie.execute("DELETE FROM wpisy_budzetu WHERE id = %s",
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
    typ = wymagaj_typu(typ)
    kategoria = wymagaj_kategorii(polaczenie, typ, kategoria)
    if Decimal(str(kwota)) < 0:
        raise BladMagazynu(
            f"Kwota wpisu nie może być ujemna ({kwota}). Kierunek wynika "
            f"z typu wpisu, nie ze znaku liczby.")
    kursor = polaczenie.execute(
        "UPDATE wpisy_budzetu SET data = %s, typ = %s, kategoria = %s, "
        "kwota = %s, szczegoly = %s WHERE id = %s",
        (data, typ, kategoria, kwota, szczegoly,
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
    typ = wymagaj_typu(typ)
    kategoria = str(kategoria).strip()
    opis = str(opis or "").strip()
    dzien = _wymagaj_dnia(dzien)
    co_ile_miesiecy = _wymagaj_cyklu(co_ile_miesiecy)
    istnieje = polaczenie.execute(
        "SELECT 1 FROM plan_budzetu WHERE rok = %s AND miesiac = %s "
        "AND typ = %s AND kategoria = %s AND opis = %s",
        (int(rok), int(miesiac), typ, kategoria, opis)).fetchone()
    try:
        polaczenie.execute(
            "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria,"
            " kwota_planowana, opis, dzien, powtarzalna, co_ile_miesiecy)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " ON CONFLICT(rok, miesiac, typ, kategoria, opis)"
            " DO UPDATE SET kwota_planowana = excluded.kwota_planowana,"
            " dzien = excluded.dzien, powtarzalna = excluded.powtarzalna,"
            " co_ile_miesiecy = excluded.co_ile_miesiecy",
            (rok, miesiac, typ, kategoria, str(kwota_planowana), opis, dzien,
             bool(powtarzalna), co_ile_miesiecy))
        polaczenie.commit()
    except psycopg.Error as e:
        polaczenie.rollback()
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
    typ = wymagaj_typu(typ)
    kursor = polaczenie.execute(
        "DELETE FROM plan_budzetu WHERE rok = %s AND miesiac = %s "
        "AND typ = %s AND kategoria = %s AND opis = %s",
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
        "WHERE typ = %s AND kategoria = %s AND opis = %s "
        "AND rok * 12 + miesiac - 1 <= %s "
        "AND (powtarzalna OR rok * 12 + miesiac - 1 = %s) "
        "AND (NOT powtarzalna OR do_roku IS NULL "
        "     OR do_roku * 12 + do_miesiaca - 1 >= %s) "
        # `MOD(...)`, a NIE operator `%`. psycopg czyta `%` w napisie
        # zapytania jako poczatek znacznika parametru i odmawia wykonania
        # („incomplete placeholder"). Podwojenie (`%%`) tez by dzialalo, ale
        # rozniloby sie od tego, co widac w dzienniku serwera — a to jest
        # miejsce, w ktorym ktos pozniej szuka bledu.
        "AND (NOT powtarzalna "
        "     OR MOD(%s - (rok * 12 + miesiac - 1), co_ile_miesiecy) = 0) "
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
    typ = wymagaj_typu(typ)
    kategoria = str(kategoria).strip()
    opis = str(opis or "").strip()
    dzien = _wymagaj_dnia(dzien)
    co_ile_miesiecy = _wymagaj_cyklu(co_ile_miesiecy)
    obowiazujaca = _obowiazujaca_regula(polaczenie, rok=rok, miesiac=miesiac,
                                        typ=typ, kategoria=kategoria,
                                        opis=opis)
    wstaw = ("INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
             "kwota_planowana, powtarzalna, opis, dzien, co_ile_miesiecy) "
             "VALUES (%s,%s,%s,%s,%s,TRUE,%s,%s,%s)")
    dane = (int(rok), int(miesiac), typ, kategoria, str(kwota_planowana),
            opis, dzien, co_ile_miesiecy)
    try:
        if obowiazujaca is None:
            polaczenie.execute(wstaw, dane)
            wynik = "nowa"
        elif (obowiazujaca[1], obowiazujaca[2]) == (int(rok), int(miesiac)):
            polaczenie.execute(
                "UPDATE plan_budzetu SET kwota_planowana = %s, powtarzalna = TRUE, "
                "do_roku = NULL, do_miesiaca = NULL, dzien = %s, "
                "co_ile_miesiecy = %s WHERE id = %s",
                (str(kwota_planowana), dzien, co_ile_miesiecy,
                 obowiazujaca[0]))
            wynik = "zaktualizowana"
        else:
            do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
            polaczenie.execute(
                "UPDATE plan_budzetu SET do_roku = %s, do_miesiaca = %s "
                "WHERE id = %s", (do_roku, do_miesiaca, obowiazujaca[0]))
            polaczenie.execute(wstaw, dane)
            wynik = "zwersjonowana"
        polaczenie.commit()
        return wynik
    except psycopg.Error as e:
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
    typ = wymagaj_typu(typ)
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
            "FROM plan_budzetu WHERE id = %s", (numer,)).fetchone()
        if zaczyna_sie_tutaj:
            polaczenie.execute(
                "UPDATE plan_budzetu SET rok = %s, miesiac = %s WHERE id = %s",
                (wraca_rok, wraca_miesiac, numer))
        else:
            do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
            polaczenie.execute(
                "UPDATE plan_budzetu SET do_roku = %s, do_miesiaca = %s "
                "WHERE id = %s", (do_roku, do_miesiaca, numer))
            polaczenie.execute(
                "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
                "kwota_planowana, powtarzalna, opis, dzien, co_ile_miesiecy, "
                "do_roku, do_miesiaca) VALUES (%s,%s,%s,%s,%s,TRUE,%s,%s,%s,%s,%s)",
                (wraca_rok, wraca_miesiac, typ, kategoria, wiersz[0], opis,
                 wiersz[1], co_ile, wiersz[2], wiersz[3]))
        polaczenie.commit()
        return "pominieta"

    if zaczyna_sie_tutaj or not powtarzalna:
        polaczenie.execute("DELETE FROM plan_budzetu WHERE id = %s", (numer,))
        wynik = "skasowana"
    else:
        do_roku, do_miesiaca = _miesiac_wczesniej(rok, miesiac)
        polaczenie.execute(
            "UPDATE plan_budzetu SET do_roku = %s, do_miesiaca = %s WHERE id = %s",
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

    NAPRAWIONE W W9b — ZMIERZONA WADA PIENIEZNA, nie porzadki.
    Do W9b ta funkcja czytala WIERSZE miesiaca zrodlowego (`WHERE rok = …
    AND miesiac = …`), a nie POZYCJE OBOWIAZUJACE w tym miesiacu. Roznica
    powstala w Z42, gdy pozycja planu stala sie REGULA obowiazujaca od
    swojego miesiaca do odwolania: od tej pory miesiac bez ani jednego
    wlasnego wiersza ma pelny plan, a wiersze zrodla nie sa tym, co
    uzytkownik widzi. Do tego sprawdzenie „czy juz jest" pomijalo `opis`,
    a kopia gubila `opis`, `dzien`, `powtarzalna` i `co_ile_miesiecy`.

    Zmierzony skutek (2026-08-29, przez `POST /api/plan/kopiuj`): listopad
    z planem 2 284,81 zl zlozonym z regul pazdziernikowych po kopii mial
    **3 589,86 zl** — przybyla druga pozycja „Kredyty" z pusta nazwa,
    a „Czesne" stracilo dzien platnosci (25 -> brak). Plan urosl o 1 305,05 zl,
    ktorych nikt nie zaplanowal, i zwrocil „skopiowane 2, pominiete 1",
    czyli meldunek sukcesu.

    Po naprawie zrodlo i cel czyta ten sam nosnik co ekran —
    `budzet.plan_na_miesiac` — a tozsamosc pozycji jest pelna trojka
    (typ, kategoria, opis), tak jak wszedzie indziej w tym module.
    Granice okresu (`do_roku`, `do_miesiaca`) NIE sa kopiowane: regula
    zamknieta kiedys w przeszlosci nie ma prawa przyjsc do nowego miesiaca
    juz zamknieta.
    """
    caly = wczytaj_plan(polaczenie)
    zrodlo = budzet.plan_na_miesiac(caly, int(z_roku), int(z_miesiaca))
    cel = budzet.plan_na_miesiac(caly, int(do_roku), int(do_miesiaca))
    juz_sa = {(w["typ"], w["kategoria"], str(w.get("opis", "") or ""))
              for _, w in cel.iterrows()} if not cel.empty else set()
    skopiowane = pominiete = 0
    if not zrodlo.empty:
        for _, w in zrodlo.iterrows():
            klucz = (w["typ"], w["kategoria"], str(w.get("opis", "") or ""))
            if klucz in juz_sa:
                pominiete += 1
                continue
            dzien = w.get("dzien")
            polaczenie.execute(
                "INSERT INTO plan_budzetu (rok, miesiac, typ, kategoria, "
                "kwota_planowana, opis, dzien, powtarzalna, co_ile_miesiecy) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (int(do_roku), int(do_miesiaca), klucz[0], klucz[1],
                 str(w["kwota_planowana"]), klucz[2],
                 None if dzien is None or pd.isna(dzien) else int(dzien),
                 bool(w.get("powtarzalna", False)),
                 int(w.get("co_ile_miesiecy", 1) or 1)))
            skopiowane += 1
    polaczenie.commit()
    return skopiowane, pominiete


def wczytaj_plan(polaczenie, rok: int | None = None,
                 miesiac: int | None = None) -> pd.DataFrame:
    warunki, parametry = [], []
    if rok is not None:
        warunki.append("rok = %s")
        parametry.append(rok)
    if miesiac is not None:
        warunki.append("miesiac = %s")
        parametry.append(miesiac)
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "plan_budzetu",
                    f"{gdzie} ORDER BY rok, miesiac, typ, kategoria",
                    tuple(parametry))


def wczytaj_pozycje_planu(polaczenie, *, plan_id: int) -> dict:
    """JEDEN wiersz planu, po numerze. Zwraca slownik kolumn.

    DLACZEGO TO ISTNIEJE (W9b). Warstwa sieciowa dostaje z ekranu NUMER
    pozycji — bo to on jest tym, co uzytkownik klika — a `ustal_regule_planu`
    i `zakoncz_plan` rozpoznaja pozycje przez czworke
    (typ, kategoria, opis, miesiac). Ktos musi zamienic jedno na drugie
    i musi to byc miejsce, ktore rozmawia z baza. Wolajacy, ktory
    przefiltrowalby sobie ramke `wczytaj_plan`, bylby DRUGIM nosnikiem
    odpowiedzi „ktora to pozycja".

    BRAK WIERSZA JEST BLEDEM, nie pusta odpowiedzia — dokladnie jak
    w `usun_wpis` i `zakoncz_plan`. Numer, ktorego nie ma, to zwykle pozycja
    zakonczona w innym oknie przegladarki; cicha zgoda kazalaby uzytkownikowi
    wierzyc, ze zmienil cos, czego juz nie ma.
    """
    ramka = _wczytaj(polaczenie, "plan_budzetu", "WHERE id = %s",
                     (int(plan_id),))
    if ramka.empty:
        raise BladMagazynu(
            f"Nie ma pozycji planu o numerze {plan_id}. Odśwież ekran — "
            f"mogła zostać zakończona gdzie indziej.")
    return {kolumna: ramka.iloc[0][kolumna] for kolumna in ramka.columns}


# --- słownik kategorii ----------------------------------------------------

def wczytaj_kategorie(polaczenie, typ: str | None = None,
                      tylko_aktywne: bool = False) -> pd.DataFrame:
    warunki, parametry = [], []
    if typ is not None:
        warunki.append("typ = %s")
        parametry.append(wymagaj_typu(typ))
    if tylko_aktywne:
        warunki.append("aktywna")
    gdzie = ("WHERE " + " AND ".join(warunki)) if warunki else ""
    return _wczytaj(polaczenie, "kategorie",
                    f"{gdzie} ORDER BY typ, kolejnosc, nazwa", tuple(parametry))


def dodaj_kategorie(polaczenie, *, typ: str, nazwa: str) -> int:
    typ = wymagaj_typu(typ)
    nazwa = str(nazwa).strip()
    if not nazwa:
        raise BladMagazynu("Nazwa kategorii nie może być pusta.")
    istnieje = polaczenie.execute(
        "SELECT 1 FROM kategorie WHERE typ = %s AND nazwa = %s",
        (typ, nazwa)).fetchone()
    if istnieje:
        raise BladMagazynu(
            f"Kategoria {nazwa!r} już istnieje w typie {typ!r}.")
    kolejnosc = polaczenie.execute(
        "SELECT COALESCE(MAX(kolejnosc), -1) + 1 FROM kategorie WHERE typ = %s",
        (typ,)).fetchone()[0]
    return _zapisz(polaczenie,
        "INSERT INTO kategorie (typ, nazwa, kolejnosc, aktywna)"
        " VALUES (%s,%s,%s,TRUE) RETURNING id",
        (typ, nazwa, kolejnosc))


def zmien_nazwe_kategorii(polaczenie, *, typ: str, stara: str, nowa: str) -> int:
    """Zmienia nazwę w słowniku ORAZ we wpisach i w planie, w jednej transakcji.

    Podmiana wyłącznie w słowniku zostawiłaby wpisy wskazujące na kategorię,
    której już nie ma — wypadłyby ze wszystkich zestawień przy zielonej suicie.
    Zwraca liczbę przepisanych wpisów.
    """
    typ = wymagaj_typu(typ)
    stara, nowa = str(stara).strip(), str(nowa).strip()
    if not nowa:
        raise BladMagazynu("Nowa nazwa kategorii nie może być pusta.")
    if polaczenie.execute("SELECT 1 FROM kategorie WHERE typ = %s AND nazwa = %s",
                          (typ, stara)).fetchone() is None:
        raise BladMagazynu(f"Kategoria {stara!r} nie istnieje w typie {typ!r}.")
    if stara != nowa and polaczenie.execute(
            "SELECT 1 FROM kategorie WHERE typ = %s AND nazwa = %s",
            (typ, nowa)).fetchone() is not None:
        raise BladMagazynu(
            f"Kategoria {nowa!r} już istnieje w typie {typ!r} — nazwy w obrębie "
            "typu muszą być niepowtarzalne.")
    try:
        polaczenie.execute(
            "UPDATE kategorie SET nazwa = %s WHERE typ = %s AND nazwa = %s",
            (nowa, typ, stara))
        kursor = polaczenie.execute(
            "UPDATE wpisy_budzetu SET kategoria = %s WHERE typ = %s AND kategoria = %s",
            (nowa, typ, stara))
        przepisane = kursor.rowcount
        polaczenie.execute(
            "UPDATE plan_budzetu SET kategoria = %s WHERE typ = %s AND kategoria = %s",
            (nowa, typ, stara))
        polaczenie.commit()
        return przepisane
    except psycopg.Error as e:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie udało się zmienić nazwy kategorii. Szczegół: {e}") from e


def ustaw_aktywnosc_kategorii(polaczenie, *, typ: str, nazwa: str,
                              aktywna: bool) -> None:
    """Dezaktywacja zamiast kasowania: kategoria znika z list wyboru, a wpisy
    i plan zostają nietknięte. Historia ma zostać prawdziwa."""
    typ = wymagaj_typu(typ)
    kursor = polaczenie.execute(
        "UPDATE kategorie SET aktywna = %s WHERE typ = %s AND nazwa = %s",
        (bool(aktywna), typ, str(nazwa).strip()))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(f"Kategoria {nazwa!r} nie istnieje w typie {typ!r}.")
    polaczenie.commit()


def policz_wpisy_kategorii(polaczenie, *, typ: str, nazwa: str) -> int:
    return polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu WHERE typ = %s AND kategoria = %s",
        (wymagaj_typu(typ), str(nazwa).strip())).fetchone()[0]


def usun_kategorie_trwale(polaczenie, *, typ: str, nazwa: str) -> None:
    """Kasuje wiersz słownika — wyłącznie gdy nie ma do niego ani jednego wpisu.

    Kategoria z historią nie znika nigdy; od tego jest dezaktywacja.
    """
    typ = wymagaj_typu(typ)
    nazwa = str(nazwa).strip()
    ile = policz_wpisy_kategorii(polaczenie, typ=typ, nazwa=nazwa)
    if ile:
        raise BladMagazynu(
            f"Kategoria {nazwa!r} ma {ile} wpisów i nie zostanie skasowana — "
            "historia musi zostać prawdziwa. Użyj dezaktywacji: kategoria "
            "zniknie z list wyboru, a wpisy zostaną.")
    kursor = polaczenie.execute(
        "DELETE FROM kategorie WHERE typ = %s AND nazwa = %s", (typ, nazwa))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(f"Kategoria {nazwa!r} nie istnieje w typie {typ!r}.")
    polaczenie.commit()


# --- cele oszczędnościowe -------------------------------------------------

def zapisz_cel(polaczenie, *, nazwa: str, kategoria: str,
               kwota_docelowa: Decimal, termin: date) -> int:
    """Cel musi wskazywać kategorię typu „Oszczędności".

    Cel wskazujący kategorię wydatku liczyłby postęp z pieniędzy **wydanych** —
    pasek pokazywałby, że zbierasz na wakacje, im więcej wydajesz na zakupy.
    """
    kategoria = wymagaj_kategorii(polaczenie, budzet.TYP_OSZCZEDNOSCI, kategoria)
    nazwa = str(nazwa).strip()
    if not nazwa:
        raise BladMagazynu("Nazwa celu jest wymagana.")
    if Decimal(str(kwota_docelowa)) <= 0:
        raise BladMagazynu(
            f"Kwota docelowa musi być dodatnia (podano {kwota_docelowa}).")
    if polaczenie.execute("SELECT 1 FROM cele_oszczednosciowe WHERE nazwa = %s",
                          (nazwa,)).fetchone():
        raise BladMagazynu(f"Cel o nazwie {nazwa!r} już istnieje.")
    return _zapisz(polaczenie,
        "INSERT INTO cele_oszczednosciowe (nazwa, kategoria, kwota_docelowa, termin)"
        " VALUES (%s,%s,%s,%s) RETURNING id",
        (nazwa, kategoria, kwota_docelowa, termin))


def wczytaj_cele(polaczenie) -> pd.DataFrame:
    return _wczytaj(polaczenie, "cele_oszczednosciowe", "ORDER BY termin, nazwa")


def usun_cel(polaczenie, *, cel_id: int) -> None:
    kursor = polaczenie.execute(
        "DELETE FROM cele_oszczednosciowe WHERE id = %s", (int(cel_id),))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(f"Nie ma celu o numerze {cel_id} — nic nie skasowałem.")
    polaczenie.commit()


# --- ustawienia -----------------------------------------------------------

def ustaw_ustawienie(polaczenie, klucz: str, wartosc: str) -> None:
    try:
        polaczenie.execute(
            "INSERT INTO ustawienia (klucz, wartosc) VALUES (%s,%s)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc",
            (str(klucz), str(wartosc)))
        polaczenie.commit()
    except psycopg.Error as e:
        polaczenie.rollback()
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
            " VALUES (%s,%s,%s)"
            " ON CONFLICT(rok) DO UPDATE SET forma = excluded.forma,"
            " stawka_ryczaltu = excluded.stawka_ryczaltu",
            (int(rok), forma,
             None if stawka_ryczaltu is None else str(stawka_ryczaltu)))
        polaczenie.commit()
    except psycopg.Error as e:
        polaczenie.rollback()
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
        "SELECT forma, stawka_ryczaltu FROM forma_opodatkowania WHERE rok = %s",
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
        "SELECT wartosc FROM ustawienia WHERE klucz = %s", (str(klucz),)).fetchone()
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
            "INSERT INTO stan_konta (data, kwota) VALUES (%s,%s)"
            " ON CONFLICT(data) DO UPDATE SET kwota = excluded.kwota",
            (data, kwota))
        polaczenie.commit()
    except psycopg.Error as e:
        polaczenie.rollback()
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
        "powiadomiono) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (kiedy, stan_prognozy,
         pierwszy_dzien_ujemny,
         # `0 if ... is None`, NIE `pilnych or 0`. Zapis ma pokazywac, ze to
         # konwersja stanu „nie wiem", a nie zabezpieczenie przed wartoscia
         # falszywa — `or 0` zamieniloby przy okazji kazde inne zero
         # i czytelnik nie odroznilby intencji. Straznik:
         # `test_zapis_przy_stanie_NIE_WIEM_kladzie_ZERO_zamiast_wybuchac`
         # (mutacja M399).
         0 if pilnych is None else int(pilnych),
         powod, zrodla, komunikat, bool(powiadomiono)))
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
        " oprocentowanie) VALUES (%s,%s,%s,%s) RETURNING id",
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
        "UPDATE zobowiazania SET nazwa = %s, kapital = %s, rata_minimalna = %s, "
        "oprocentowanie = %s WHERE id = %s",
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
    kursor = polaczenie.execute("DELETE FROM zobowiazania WHERE id = %s",
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
    warunek = "WHERE kategoria = %s"
    parametry: list = [KATEGORIA_RACHUNEK_ROZLICZENIOWY]
    if pomijajac is not None:
        warunek += " AND id <> %s"
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
        "INSERT INTO majatek (nazwa_aktywa, kategoria, wartosc)"
        " VALUES (%s,%s,%s) RETURNING id",
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
        "UPDATE majatek SET nazwa_aktywa = %s, kategoria = %s, wartosc = %s "
        "WHERE id = %s",
        (nazwa_aktywa, str(kategoria), str(wartosc), int(aktywo_id)))
    if kursor.rowcount == 0:
        polaczenie.rollback()
        raise BladMagazynu(
            f"Nie ma aktywa o numerze {aktywo_id} — nic nie zmieniłem.")
    polaczenie.commit()


def usun_aktywo(polaczenie, *, aktywo_id: int) -> None:
    kursor = polaczenie.execute("DELETE FROM majatek WHERE id = %s",
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
    sql_wpisu, wartosci = _przygotuj_wpis(
        polaczenie, data=data, typ=budzet.TYP_WYDATKI,
        kategoria=budzet.KATEGORIA_KOSZTY_JDG, kwota=brutto,
        szczegoly=f"Koszt JDG: {opis}")
    try:
        with polaczenie.transaction():
            wpis_id = polaczenie.execute(sql_wpisu, wartosci).fetchone()[0]
            return polaczenie.execute(
                "INSERT INTO koszty_jdg (data, opis, kwota_netto, kwota_vat,"
                " wpis_budzetu_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (data, opis, kwota_netto, kwota_vat, wpis_id)).fetchone()[0]
    except psycopg.Error as e:
        raise BladMagazynu(
            f"Nie udało się zapisać kosztu. Ani koszt, ani wydatek w budżecie "
            f"nie zostały zapisane. Szczegół: {e}") from e


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
        "SELECT wpis_budzetu_id FROM koszty_jdg WHERE id = %s",
        (koszt_id,)).fetchone()
    if wiersz is None:
        return
    if wiersz[0] is not None:
        polaczenie.execute("DELETE FROM wpisy_budzetu WHERE id = %s", (wiersz[0],))
    polaczenie.execute("DELETE FROM koszty_jdg WHERE id = %s", (koszt_id,))
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
        "SELECT wpis_budzetu_id FROM przychody_jdg WHERE id = %s",
        (faktura_id,)).fetchone()
    if wiersz is None or wiersz[0] is None:
        return False
    return polaczenie.execute(
        "SELECT 1 FROM wpisy_budzetu WHERE id = %s", (wiersz[0],)
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
        " WHERE id = %s", (faktura_id,)).fetchone()
    if wiersz is None:
        raise BladMagazynu(f"Nie ma faktury o numerze wewnętrznym {faktura_id}.")

    numer, netto, vat = wiersz
    brutto = stawki.do_groszy(Decimal(str(netto)) + Decimal(str(vat)))
    sql_wpisu, wartosci = _przygotuj_wpis(
        polaczenie, data=data_wplywu, typ=budzet.TYP_PRZYCHODY,
        kategoria=budzet.KATEGORIA_PRZYCHOD_JDG, kwota=brutto,
        szczegoly=f"Faktura {numer}")
    try:
        with polaczenie.transaction():
            wpis_id = polaczenie.execute(sql_wpisu, wartosci).fetchone()[0]
            polaczenie.execute(
                "UPDATE przychody_jdg SET data_zaplaty = %s,"
                " wpis_budzetu_id = %s WHERE id = %s",
                (data_wplywu, wpis_id, faktura_id))
    except psycopg.Error as e:
        raise BladMagazynu(
            f"Nie udało się oznaczyć faktury jako zapłaconej. Ani przychód "
            f"w budżecie, ani data wpływu nie zostały zapisane. "
            f"Szczegół: {e}") from e
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


if __name__ == "__main__":  # pragma: no cover - narzedzie wiersza polecen
    # `./.venv/bin/python -m silnik.rdzen.magazyn` — migracja recznie, bez
    # stawiania calej aplikacji. Ten sam adres co w produkcji (`adres_bazy()`),
    # wypisany BEZ HASLA.
    _raport = zmigruj()
    print(f"Baza: {_raport.adres}")
    print(f"Wersja schematu: {_raport.wersja_przed} -> {_raport.wersja_po}")
    print(f"Tabel: {_raport.tabel} | kategorii dosianych: {_raport.kategorii} "
          f"| stawek dosianych: {_raport.stawek}")
    print(f"Kopia przed migracja: {_raport.kopia or 'nie byla potrzebna'}")

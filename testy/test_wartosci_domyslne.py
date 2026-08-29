# -*- coding: utf-8 -*-
"""STRAZNIK WARTOSCI DOMYSLNYCH KOLUMN (W5, 2026-08-29).

DLACZEGO TEN PLIK ISTNIEJE — ZNALEZISKO AUDYTU W5, NIE POMYSL.
Do W4 wartosci domyslnych pilnowal `test_schemat_dwa_dialekty.py::
test_WARTOSCI_DOMYSLNE_sa_te_same` — porownywal `DEFAULT` kolumna po kolumnie
miedzy dwoma dialektami schematu, z progiem „co najmniej 90 kolumn". W4 zdjelo
ten plik razem z drugim dialektem i **nie dalo mu nastepcy**: po podmianie
sterownika `testy/porownanie_schematu.py::porownaj_domyslna` nie ma ANI JEDNEGO
wolajacego (pomiar: `grep -rn porownaj_domyslna testy silnik api wiedza
migracja` -> jedno trafienie, sama definicja).

PRZEDMIOT ISTNIEJE — to nie jest test, ktory stracil temat. Baza niesie
22 wartosci domyslne (pomiar 2026-08-29), a **trzy kolumny nie maja jej
SWIADOMIE** i powod stoi przy kazdej w `silnik/baza/schemat.sql`. To wlasnie
ta klasa wady, ktora zlapal poprzednik: `pkwiu DEFAULT ''` obok
`magazyn._wymagaj_pkwiu`, ktore pustego PKWiU nie wpuszcza — wartosc domyslna
byla obejsciem wlasnej reguly pisarza.

POMIAR, KTORY TEN PLIK ZAMYKA (2026-08-29, mutacja M-A1): dopisanie
`DEFAULT ''` do `przychody_jdg.pkwiu` w `schemat.sql` dalo **993 passed** —
zero czerwonych. Reguly nie pilnowalo NIC.

DLACZEGO POROWNANIE „NAPIS DDL vs BAZA" TU NIE WYSTARCZA. Baza jest stawiana
Z TEGO NAPISU, wiec obie strony zmieniaja sie razem i porownanie jest
tautologia — zielone takze po mutacji. Drugi punkt odniesienia musi wiec byc
NIEZALEZNY: jest nim rejestr `OCZEKIWANE` nizej. To NIE jest drugi nosnik
reguly (§3.2) — to jest straznik, ktorego jedynym zadaniem jest wymusic
SWIADOMA decyzje przy kazdej zmianie wartosci domyslnej. Zmiana rejestru bez
zmiany schematu czerwieni sie tak samo jak zmiana schematu bez rejestru.

KONTROLA LICZNOSCI STOI PRZY KAZDEJ ASERCJI. Zapytanie do katalogu, ktore
z jakiegos powodu nic nie zwrocilo, porownuje pustke z pustka i melduje
sukces — zmierzone w tej sesji cztery razy.

CZEGO TEN PLIK NIE SPRAWDZA, zeby cisza nie uchodzila za zgode:
  * czy wartosc domyslna jest SENSOWNA — pilnuja tego strazniki zachowania
    (`test_trzy_kolumny.py::test_zapis_wpisu_bez_podania_zrodla_daje_recznie`);
  * wartosci domyslnych kolumn dokladanych `ALTER TABLE` na starej bazie poza
    `_DOPISYWANE_KOLUMNY` — droga migracyjna ma wlasnych straznikow;
  * numeru sekwencji — porownujemy FAKT bycia sekwencja, nie jej stan.
"""
from __future__ import annotations

import pytest

from silnik.rdzen import magazyn
from testy import pomocnicze

#: Wartosci domyslne odczytane z POSTAWIONEJ bazy, pomiar 2026-08-29.
#: Klucz `tabela.kolumna`, wartosc — wyrazenie z katalogu systemowego
#: sprowadzone do postaci porownywalnej (`_normalizuj`).
OCZEKIWANE = {
    "cele_oszczednosciowe.id": "SEKWENCJA",
    "godziny.id": "SEKWENCJA",
    "godziny.opis": "''::text",
    "kategorie.id": "SEKWENCJA",
    "kategorie.kolejnosc": "0",
    "kategorie.aktywna": "true",
    "koszty_jdg.id": "SEKWENCJA",
    "majatek.id": "SEKWENCJA",
    "plan_budzetu.id": "SEKWENCJA",
    "plan_budzetu.powtarzalna": "false",
    "plan_budzetu.opis": "''::text",
    "plan_budzetu.co_ile_miesiecy": "1",
    "przebiegi_straznika.id": "SEKWENCJA",
    "przebiegi_straznika.powiadomiono": "false",
    "przychody_jdg.id": "SEKWENCJA",
    "rejestr_stawek.id": "SEKWENCJA",
    "rejestr_stawek.opis": "''::text",
    "wersja_schematu.jedyny": "true",
    "wpisy_budzetu.id": "SEKWENCJA",
    "wpisy_budzetu.szczegoly": "''::text",
    "wpisy_budzetu.zrodlo": "'recznie'::text",
    "zobowiazania.id": "SEKWENCJA",
}

#: Kolumny, ktore wartosci domyslnej NIE MAJA I MIEC NIE MOGA — z powodem.
#: Powod jest czescia asercji, nie ozdoba: komunikat ma powiedziec, DLACZEGO
#: dopisanie `DEFAULT` jest wada, a nie tylko ze rejestr sie nie zgadza.
BEZ_DOMYSLNEJ_SWIADOMIE = {
    ("przychody_jdg", "pkwiu"):
        "`magazyn._wymagaj_pkwiu` odrzuca pusty napis powolujac sie na art. 12 "
        "ust. 3. Wartosc domyslna wpuszcza wiersz, ktorego pisarz nigdy by nie "
        "zapisal — obejscie wlasnej reguly (schemat.sql, decyzja W1).",
    ("godziny", "pkwiu"):
        "ten sam powod co w `przychody_jdg.pkwiu` — `_wymagaj_pkwiu` stoi na "
        "obu drogach zapisu (schemat.sql, decyzja W1).",
    ("przebiegi_straznika", "kiedy"):
        "`magazyn.zapisz_przebieg_straznika` podaje `kiedy` zawsze i jawnie. "
        "`DEFAULT now()` byloby drugim nosnikiem odpowiedzi „kiedy straznik "
        "biegl\" i ostemplowaloby przenoszone wiersze godzina MIGRACJI "
        "zamiast godzina przebiegu (schemat.sql, decyzja W1).",
    ("przychody_jdg", "data_obowiazku_vat"):
        "D-35, VAT memorialowo: NULL znaczy „nie wiem\", a nie „dzis\". "
        "Wartosc domyslna zamienilaby brak wiedzy w zgadniecie i wciagnela "
        "fakture do zlego okresu VAT.",
}

#: Ile kolumn ma odwiedzic pomiar. Pomiar 2026-08-29: 97. Prog zostawia
#: miejsce na drobne zmiany i czerwieni sie, gdy przyrzad przestanie widziec.
NAJMNIEJ_KOLUMN = 90


def _normalizuj(wyrazenie: str) -> str:
    """Sekwencja `BIGSERIAL` niesie nazwe sekwencji, ktora zalezy od tabeli
    i od przestrzeni nazw testu — porownujemy FAKT, nie napis."""
    return "SEKWENCJA" if wyrazenie.startswith("nextval(") else wyrazenie


@pytest.fixture
def domyslne_z_bazy():
    """Mapa `tabela.kolumna -> DEFAULT` odczytana z katalogu systemowego
    bazy postawionej w tym tescie. Druga wartosc: ile kolumn odwiedzono."""
    magazyn.zmigruj_i_polacz().close()
    polaczenie = pomocnicze.polaczenie_surowe()
    try:
        wiersze = polaczenie.execute(
            "SELECT table_name, column_name, column_default"
            " FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " ORDER BY table_name, ordinal_position").fetchall()
    finally:
        polaczenie.close()
    mapa = {f"{t}.{k}": _normalizuj(d) for t, k, d in wiersze if d is not None}
    return mapa, len(wiersze)


def test_przyrzad_WIDZI_kolumny_a_nie_porownuje_pustki(domyslne_z_bazy):
    """Kontrola licznosci. Bez niej zapytanie do zlej przestrzeni nazw
    porownywaloby pusty slownik z pustym i bylo zielone."""
    mapa, odwiedzonych = domyslne_z_bazy
    assert odwiedzonych >= NAJMNIEJ_KOLUMN, (
        f"pomiar odwiedzil {odwiedzonych} kolumn, prog {NAJMNIEJ_KOLUMN} — "
        f"zapytanie prawdopodobnie poszlo do innej przestrzeni nazw")
    assert len(OCZEKIWANE) >= 20, (
        f"rejestr oczekiwanych ma {len(OCZEKIWANE)} pozycji — pusty albo "
        f"okrojony rejestr zgadza sie z KAZDA baza")


def test_ZBIOR_kolumn_z_wartoscia_domyslna_jest_TEN_z_rejestru(domyslne_z_bazy):
    """Kolumna, ktora dostala wartosc domyslna po cichu, i kolumna, ktora ja
    po cichu stracila — obie czerwienia ten test, obie po nazwie."""
    mapa, _ = domyslne_z_bazy
    dolozone = sorted(set(mapa) - set(OCZEKIWANE))
    znikniete = sorted(set(OCZEKIWANE) - set(mapa))
    assert dolozone == [], (
        f"kolumny maja w bazie wartosc domyslna, o ktorej rejestr nie wie: "
        f"{[f'{k} = {mapa[k]}' for k in dolozone]}. Jesli to swiadoma decyzja "
        f"— dopisz ja do OCZEKIWANE razem z powodem.")
    assert znikniete == [], (
        f"kolumny straciły wartosc domyslna, ktora rejestr im przypisuje: "
        f"{znikniete}. Zapis pomijajacy te kolumne zachowa sie inaczej niz "
        f"dotad.")


def test_TRESC_kazdej_wartosci_domyslnej_jest_TA_z_rejestru(domyslne_z_bazy):
    """`DEFAULT TRUE` zamienione na `DEFAULT FALSE` nie zmienia ZBIORU kolumn
    — zmienia zachowanie zapisu, ktory tej kolumny nie podaje."""
    mapa, _ = domyslne_z_bazy
    porownanych = 0
    bledy = []
    for klucz, oczekiwana in sorted(OCZEKIWANE.items()):
        if klucz not in mapa:
            continue  # brak kolumny lapie test wyzej, po nazwie
        porownanych += 1
        if mapa[klucz] != oczekiwana:
            bledy.append(f"{klucz}: baza ma {mapa[klucz]!r}, "
                         f"rejestr {oczekiwana!r}")
    assert porownanych >= 20, (
        f"porownano tresc {porownanych} wartosci domyslnych, spodziewane co "
        f"najmniej dwadziescia")
    assert bledy == [], "; ".join(bledy)


@pytest.mark.parametrize(
    "tabela,kolumna", sorted(BEZ_DOMYSLNEJ_SWIADOMIE),
    ids=lambda x: x if isinstance(x, str) else str(x))
def test_kolumna_bez_wartosci_domyslnej_NADAL_jej_nie_ma(
        domyslne_z_bazy, tabela, kolumna):
    """ZNALEZISKO W5 — dokladnie ta reguła nie miala straznika.

    Mutacja M-A1 (2026-08-29): `pkwiu TEXT NOT NULL` -> `... NOT NULL
    DEFAULT ''` w `schemat.sql` dawala 993 passed. Ten test na tej mutacji
    pada i mowi, KTORA kolumna i DLACZEGO to jest wada.
    """
    mapa, _ = domyslne_z_bazy
    klucz = f"{tabela}.{kolumna}"
    assert klucz not in mapa, (
        f"{klucz} dostala wartosc domyslna {mapa.get(klucz)!r}, a nie ma "
        f"prawa jej miec: {BEZ_DOMYSLNEJ_SWIADOMIE[(tabela, kolumna)]}")


def test_kolumny_BEZ_domyslnej_ISTNIEJA_a_nie_tylko_powinny(domyslne_z_bazy):
    """Kontrola licznosci do testu wyzej — i jego dwustronna kontrola.

    Test „klucza nie ma w mapie" jest zielony takze wtedy, gdy nie ma samej
    KOLUMNY: literowka w nazwie tabeli daje straznika, do ktorego nic nie
    dociera. Zmierzone w tej sesji cztery razy.
    """
    magazyn.zmigruj_i_polacz().close()
    polaczenie = pomocnicze.polaczenie_surowe()
    try:
        for tabela, kolumna in sorted(BEZ_DOMYSLNEJ_SWIADOMIE):
            assert kolumna in pomocnicze.kolumny_tabeli(polaczenie, tabela), (
                f"straznik pilnuje wartosci domyslnej kolumny {tabela}."
                f"{kolumna}, ktorej w bazie NIE MA — pilnuje wiec niczego")
    finally:
        polaczenie.close()

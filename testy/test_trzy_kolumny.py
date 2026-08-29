# -*- coding: utf-8 -*-
"""Strażnicy trzech kolumn z PRD §6.3 (schemat 12, 2026-08-29).

Każda z trzech ma za sobą decyzję, nie pomysł:

* `wpisy_budzetu.zrodlo` — bramka poprawności. Bez niej „wgrać historię" i „nie
  liczyć jej do podatku" są dwiema regułami w dwóch miejscach.
* `kategorie.niezbedna` — bez niej próg poduszki jest PRZEDZIAŁEM
  29 651–63 649 zł, a nie liczbą.
* `przychody_jdg.data_obowiazku_vat` — D-35, VAT memoriałowo.

DLACZEGO DOKŁADAMY JE TERAZ. Baza produkcyjna startuje pusta 1 IX 2026
(decyzja Darka 2026-08-29), więc to jest najtańsza chwila w całym życiu
projektu: nie ma danych do przeniesienia.

TRZY ROZJAZDY, WSZYSTKIE NAZWANE — opisane przy `_DOPISYWANE_KOLUMNY`
w `silnik/rdzen/magazyn.py`. Testy niżej pilnują ich granic, a nie udają,
że rozjazdów nie ma.
"""
from datetime import date
from decimal import Decimal

import pytest

import psycopg

from silnik import baza
from silnik.rdzen import budzet, magazyn
from testy import pomocnicze

TRZY = (
    ("wpisy_budzetu", "zrodlo"),
    ("kategorie", "niezbedna"),
    ("przychody_jdg", "data_obowiazku_vat"),
)


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz()


def _kolumny(polaczenie, tabela: str) -> set[str]:
    return pomocnicze.kolumny_tabeli(polaczenie, tabela)


def _stara_baza(*, wpisow: int):
    """Baza w kształcie schematu 11 — BEZ trzech kolumn, Z danymi.

    Odtwarza kształt bazy roboczej (kopii poprzednika), na której zespół
    dziś buduje. Bez tego strażnik migracji sprawdzałby wyłącznie ścieżkę
    świeżej bazy, czyli tę, która i tak jest łatwa.
    """
    polaczenie = pomocnicze.polaczenie_surowe()
    polaczenie.execute("""
        CREATE TABLE wpisy_budzetu (
            id BIGSERIAL PRIMARY KEY,
            data DATE NOT NULL, typ TEXT NOT NULL, kategoria TEXT NOT NULL,
            kwota NUMERIC(14,2) NOT NULL,
            szczegoly TEXT NOT NULL DEFAULT '');
        CREATE TABLE kategorie (
            id BIGSERIAL PRIMARY KEY,
            typ TEXT NOT NULL, nazwa TEXT NOT NULL,
            kolejnosc INT NOT NULL DEFAULT 0,
            aktywna BOOLEAN NOT NULL DEFAULT TRUE, UNIQUE (typ, nazwa));
        CREATE TABLE wersja_schematu (
            jedyny BOOLEAN PRIMARY KEY DEFAULT TRUE, wersja INT NOT NULL,
            CONSTRAINT naprawde_jedyny CHECK (jedyny));
    """)
    for i in range(wpisow):
        polaczenie.execute(
            "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota) "
            "VALUES (%s,%s,%s,%s)",
            (date(2025, 1, i + 1), budzet.TYP_WYDATKI, "Zakupy",
             Decimal("100.00")))
    polaczenie.execute(
        "INSERT INTO wersja_schematu (jedyny, wersja) VALUES (TRUE, 11)")
    polaczenie.commit()
    polaczenie.close()


# --- świeża baza ----------------------------------------------------------

def test_swieza_baza_MA_wszystkie_trzy_kolumny(p):
    """Kontrola liczności: pętla ma zobaczyć trzy pary, nie zero."""
    assert len(TRZY) == 3
    brakujace = [(t, k) for t, k in TRZY if k not in _kolumny(p, t)]
    assert brakujace == []


def test_swieza_baza_ODRZUCA_zrodlo_spoza_trojki(p):
    """Więz `zrodlo_znane` — czwarta wartość byłaby regułą bez nośnika.

    ROZJAZD ZAMKNIĘTY W W4 (2026-08-29). Do podmiany sterownika ten więz był
    WYŁĄCZNIE w bazie świeżej: `ALTER TABLE ADD COLUMN` w SQLite nie potrafi
    dołożyć `CHECK`, więc baza istniejąca dostawała kolumnę bez więzu. Próg
    brzmiał „więz wraca po obu stronach przy przejściu na PostgreSQL" —
    i wrócił: `ALTER TABLE ADD COLUMN` w PostgreSQL przyjmuje `CHECK`, a baza
    produkcyjna i tak startuje pusta, więc obu ścieżek pilnuje jeden schemat.
    """
    with pytest.raises(psycopg.errors.CheckViolation):
        p.execute(
            "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, zrodlo)"
            " VALUES ('2026-09-01','Wydatki','Zakupy','10.00','skądinąd')")


def test_swieza_baza_PRZYJMUJE_trzy_znane_zrodla(p):
    """Kontrola dwustronna: więz ma odrzucać nieznane, a nie wszystko."""
    for i, zrodlo in enumerate(("recznie", "historia-2025", "import")):
        p.execute(
            "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, zrodlo)"
            " VALUES (%s,%s,%s,%s,%s)",
            (f"2026-09-0{i + 1}", "Wydatki", "Zakupy", "10.00", zrodlo))
    p.commit()
    assert p.execute("SELECT COUNT(DISTINCT zrodlo) FROM wpisy_budzetu"
                     ).fetchone()[0] == 3


def test_zapis_wpisu_bez_podania_zrodla_daje_recznie(p):
    """Wartość domyślna jest DECYZJĄ: wpis powstały z formularza jest ręczny.

    Gdyby domyślną było `historia-2025`, każdy wpis Darka wypadałby z rachunku
    podatkowego po cichu.
    """
    magazyn.zapisz_wpis(p, data=date(2026, 9, 10), typ=budzet.TYP_WYDATKI,
                        kategoria="Zakupy", kwota=Decimal("123.45"))
    assert p.execute("SELECT zrodlo FROM wpisy_budzetu").fetchone()[0] == "recznie"


def test_niezbedna_startuje_jako_NIE_WIEM_a_nie_jako_nie(p):
    """NULL i 0 to dwa różne stany. Zero znaczyłoby „Darek rozstrzygnął, że nie",
    a nikt tego nie rozstrzygnął — to ta sama klasa wady co forma opodatkowania
    zgadnięta wartością domyślną."""
    wiersze = p.execute("SELECT niezbedna FROM kategorie").fetchall()
    assert len(wiersze) > 0, "słownik kategorii pusty — nie ma czego sprawdzać"
    assert all(w[0] is None for w in wiersze)


def test_data_obowiazku_vat_startuje_pusta_a_nie_zgadnieta(p):
    """Data domyślna byłaby ZMYŚLENIEM daty powstania obowiązku podatkowego."""
    magazyn.zapisz_fakture(
        p, data=date(2026, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    assert p.execute(
        "SELECT data_obowiazku_vat FROM przychody_jdg").fetchone()[0] is None


# --- baza istniejąca: migracja bez utraty wierszy -------------------------

def test_stara_baza_DOSTAJE_kolumny_bez_utraty_wierszy(tmp_path):
    """Liczność po obu stronach, tabela po tabeli — nie „wygląda dobrze".

    Kształt bazy roboczej: schemat 11 z danymi. To ta ścieżka, którą przejdzie
    kopia bazy poprzednika przy pierwszym otwarciu nowym kodem.
    """
    sciezka = tmp_path / "stara.db"
    _stara_baza(wpisow=17)

    polaczenie = magazyn.zmigruj_i_polacz()
    assert polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 17
    assert "zrodlo" in _kolumny(polaczenie, "wpisy_budzetu")
    assert "niezbedna" in _kolumny(polaczenie, "kategorie")


def test_stara_baza_znaczy_wiersze_sprzed_migracji_jako_RECZNE(tmp_path):
    """ROZJAZD NAZWANY, NIE UKRYTY — i dlatego ma własnego strażnika.

    W bazie roboczej 204 wpisy historii 2025 dostaną `zrodlo = 'recznie'`,
    czyli etykietę „wpisane ręcznie". To NIEPRAWDA o tych danych.

    DLACZEGO MIMO TO TAK: alternatywą byłoby zgadywanie po dacie, czyli
    migracja danych — a Darek jej zakazał (2026-08-29). Skutku dziś nie ma,
    bo kolumna NIE MA KONSUMENTA (pilnuje tego
    `test_rejestr_ddl.py` dla rejestru; dla `zrodlo` — test niżej).

    PRÓG: przy pierwszym konsumencie `zrodlo` baza robocza wymaga
    jednorazowego oznaczenia historii albo konsument filtruje po dacie.
    Baza PRODUKCYJNA problemu nie ma: startuje pusta.
    """
    sciezka = tmp_path / "historia.db"
    _stara_baza(wpisow=5)
    polaczenie = magazyn.zmigruj_i_polacz()
    zrodla = {w[0] for w in polaczenie.execute(
        "SELECT DISTINCT zrodlo FROM wpisy_budzetu")}
    assert zrodla == {"recznie"}


def test_stara_baza_dostaje_kolumne_BEZ_wiezu_i_to_jest_nazwane(tmp_path):
    """Drugi rozjazd: `ALTER TABLE ADD COLUMN` nie dokłada `CHECK`.

    Ten test NIE jest życzeniem — jest opisem stanu faktycznego. Gdyby SQLite
    kiedyś nauczył się dokładać więzy przy `ALTER`, test padnie i wtedy
    zniknie akapit o rozjeździe w `magazyn._DOPISYWANE_KOLUMNY`.
    """
    sciezka = tmp_path / "bez-wiezu.db"
    _stara_baza(wpisow=1)
    polaczenie = magazyn.zmigruj_i_polacz()
    polaczenie.execute(
        "INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, zrodlo)"
        " VALUES ('2026-09-01','Wydatki','Zakupy','10.00','skądinąd')")
    polaczenie.commit()
    assert polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu WHERE zrodlo = 'skądinąd'"
    ).fetchone()[0] == 1


# --- strażnik wykryty mutacją M4: dwie drogi, jedna asercja ---------------

def test_SAM_schemat_swiezej_bazy_NIESIE_trzy_kolumny():
    """DOŁOŻONY PO MUTACJI, KTÓRA PRZESZŁA NA ZIELONO (2026-08-29).

    Mutacja M4 zdjęła `niezbedna INTEGER,` ze schematu świeżej bazy i **cała
    suita 918 testów została zielona**. Powód: kolumna ma DWIE drogi do bazy —
    napis DDL (baza świeża) i `_DOPISYWANE_KOLUMNY` (baza istniejąca) —
    a migracja wykonuje obie. Test pytający „czy kolumna jest po otwarciu
    bazy" nie odróżnia, którą drogą przyszła, więc zdjęcie jednej z nich
    było dla niego niewidoczne.

    Ten test stawia bazę z SAMEGO napisu DDL, w osobnej przestrzeni nazw
    i z pominięciem migracji. Dzięki temu mutacja zdejmująca kolumnę z jednego
    nośnika czerwieni się natychmiast, a nie dopiero wtedy, gdy ktoś zdejmie
    oba.

    CO TEN TEST WIDZI: trzy pary z `TRZY`, sprawdzane w pętli po tabelach,
    z jawną kontrolą, że pętla czegoś dotknęła.
    """
    polaczenie = pomocnicze.polaczenie_surowe()
    polaczenie.execute("CREATE SCHEMA sam_napis")
    polaczenie.execute("SET search_path TO sam_napis")
    polaczenie.execute(baza.schemat_postgresql())
    sprawdzone = 0
    brakujace = []
    for tabela, kolumna in TRZY:
        istniejace = pomocnicze.kolumny_tabeli(polaczenie, tabela)
        assert istniejace, f"tabela {tabela} nie powstała z napisu DDL"
        sprawdzone += 1
        if kolumna not in istniejace:
            brakujace.append(f"{tabela}.{kolumna}")
    assert sprawdzone == 3
    assert brakujace == [], (
        f"napis DDL nie niesie kolumn: {brakujace}. "
        "Świeża baza dostałaby je tylko przez `_DOPISYWANE_KOLUMNY`, "
        "czyli ścieżką przewidzianą dla baz ISTNIEJĄCYCH."
    )

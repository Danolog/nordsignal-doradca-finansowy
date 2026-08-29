# -*- coding: utf-8 -*-
"""Straznik W3-1: kwota wraca z bazy jako liczba DZIESIETNA, nie zmiennoprzecinkowa.

CO PILNUJE. `magazyn._wczytaj` czyta kazda tabele przez `pd.read_sql` i dopiero
POTEM zamienia kolumny z `_KWOTOWE` na `Decimal`. Dzis kolumny kwotowe sa w
SQLite typu `TEXT`, wiec sterownik oddaje NAPIS i po drodze nie ma czego
zepsuc. Po migracji na PostgreSQL (`silnik/baza/schemat.sql`) beda typu
`NUMERIC`, a psycopg odda `Decimal`.

DLACZEGO TO NIE JEST TEORIA. `pandas.read_sql` ma parametr `coerce_float`
o wartosci domyslnej **True** i jego dzialanie zmierzono w tym projekcie
2026-08-29 na pandas 3.0.5: gdy sterownik oddaje `Decimal`, ramka wraca jako
`float64`. Pomiar (sterownik SQLite z konwerterem oddajacym `Decimal`, czyli
ten sam ksztalt wejscia, ktory da psycopg na `NUMERIC`):

    surowy kursor: [('Decimal', Decimal('7034.72')), ...]
    read_sql domyslnie -> dtypes: {'kwota': dtype('float64')}
    coerce_float=False -> dtypes: {'kwota': dtype('O')}

Ten sam eksperyment stoi nizej jako `test_sterownik_oddajacy_Decimal_*` — nie
jako cytat z raportu, tylko jako wykonywalny przypadek.

DLACZEGO TEST SPRAWDZA `type()`, A NIE WARTOSC. Wszystkie dotychczasowe
asercje kwotowe w tej suicie maja ksztalt `Decimal(str(x))`, ktory przechodzi
IDENTYCZNIE na napisie, na `Decimal` i na `float` — bo `str(float)` daje
najkrotszy zapis wracajacy do tej samej liczby. Zamiana typu jest wiec dla nich
NIEWIDOCZNA. Pilnuje tego `test_asercja_przez_Decimal_str_JEST_slepa`.

Nagłowek `magazyn.py:7-8` mowi, po co zbudowano cala konstrukcje kwotowa:
„`float` gubi grosze przy podrozy do bazy i z powrotem, a to jest aplikacja
podatkowa". Ten plik jest jej straznikiem — do tej pory nie miala zadnego.

CZEGO TEN STRAZNIK NIE OBEJMUJE (pozycja jawna, nie przeoczenie):
`_KWOTOWE` nie jest pelna lista kolumn pienieznych. `forma_opodatkowania.
stawka_ryczaltu` i `zobowiazania.oprocentowanie` ida przez `Decimal` recznie,
poza `_wczytaj` — pierwszej pilnuje `test_forma_opodatkowania.py`, drugiej
`test_null_nie_udaje_liczby.py`.
"""
from datetime import date
from decimal import Decimal
import re
import sqlite3

import numpy as np
import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn
#: JEDEN NOSNIK liczby kolumn kwotowych. Stala mieszka w strazniku schematu
#: (W1, po W4 w `test_schemat_wobec_bazy`) i jest tu WOLANA, nie powtorzona —
#: dwie kopie rozjechalyby sie przy pierwszej zmianie `_KWOTOWE`, a ten plik
#: nadal meldowalby sukces.
from testy.test_schemat_wobec_bazy import ILE_KOLUMN_KWOTOWYCH

#: Ile tabel niesie kwoty. Pomiar `_KWOTOWE` z 2026-08-29: dziewiec.
ILE_TABEL_KWOTOWYCH = 9


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz()
    yield polaczenie
    polaczenie.close()


def _zasil_wszystkie_tabele_kwotowe(polaczenie) -> None:
    """Po jednym wierszu w KAZDEJ z dziewieciu tabel z `_KWOTOWE`.

    Bez tego straznik czytalby puste ramki i meldowal sukces, nie ogladajac
    ani jednej kwoty — ta klasa atrapy zostala w tym projekcie zmierzona
    (W1, mutacja M5: cztery testy zielone, jeden porownywal pustke z pustka).
    """
    magazyn.zapisz_fakture(
        polaczenie, data=date(2026, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    magazyn.zapisz_wpis(polaczenie, data=date(2026, 9, 5),
                        typ=budzet.TYP_WYDATKI, kategoria="Zakupy",
                        kwota=Decimal("249.99"))
    magazyn.zapisz_koszt(polaczenie, data=date(2026, 9, 12), opis="laptop",
                         kwota_netto=Decimal("4000.00"),
                         kwota_vat=Decimal("920.00"))
    magazyn.zapisz_plan(polaczenie, rok=2026, miesiac=9,
                        typ=budzet.TYP_WYDATKI, kategoria="Zakupy",
                        kwota_planowana=Decimal("1500.00"))
    magazyn.zapisz_cel(polaczenie, nazwa="Poduszka",
                       kategoria="Poduszka finansowa",
                       kwota_docelowa=Decimal("30000.00"),
                       termin=date(2027, 12, 31))
    magazyn.zapisz_zobowiazanie(polaczenie, nazwa="Kredyt Revolut",
                                kapital=Decimal("51234.00"),
                                rata_minimalna=Decimal("1305.05"),
                                oprocentowanie=Decimal("9"))
    magazyn.zapisz_aktywo(polaczenie, nazwa_aktywa="Samochod",
                          kategoria="pojazd", wartosc=Decimal("38000.00"))
    magazyn.zapisz_godziny(polaczenie, data=date(2026, 9, 3),
                           rodzaj_czynnosci="programowanie",
                           pkwiu="74.90.19.0",
                           liczba_godzin=Decimal("7.50"))
    magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 9, 1),
                              kwota=Decimal("9995.00"))


#: Jak dostac sie do kazdej tabeli kwotowej PUBLICZNA droga. Klucz jest nazwa
#: tabeli w `_KWOTOWE` — dzieki temu dopisanie tabeli do `_KWOTOWE` bez
#: dopisania jej tutaj czerwieni `test_odczyty_POKRYWAJA_cale_KWOTOWE`.
ODCZYTY = {
    "przychody_jdg": magazyn.wczytaj_faktury,
    "wpisy_budzetu": magazyn.wczytaj_wpisy,
    "koszty_jdg": magazyn.wczytaj_koszty,
    "plan_budzetu": magazyn.wczytaj_plan,
    "cele_oszczednosciowe": magazyn.wczytaj_cele,
    "zobowiazania": magazyn.wczytaj_zobowiazania,
    "majatek": magazyn.wczytaj_majatek,
    "godziny": magazyn.wczytaj_godziny,
    "stan_konta": magazyn.wczytaj_kotwice,
}


def wymagaj_kwot_bez_zmiennoprzecinkowych(ramka, tabela: str) -> int:
    """Podnosi `AssertionError`, gdy ktorakolwiek kwota jest zmiennoprzecinkowa.

    Zwraca liczbe OBEJRZANYCH WARTOSCI — wolajacy ma czym sprawdzic, czy
    cokolwiek do niego dotarlo. Sprawdzenie, do ktorego nic nie dociera,
    melduje sukces.
    """
    kolumny = magazyn._KWOTOWE.get(tabela, [])
    assert kolumny, f"tabela {tabela!r} nie ma kolumn kwotowych w `_KWOTOWE`"
    obejrzane = 0
    for kolumna in kolumny:
        assert kolumna in ramka.columns, (
            f"{tabela}.{kolumna}: kolumna kwotowa zniknela z odczytu")
        seria = ramka[kolumna]
        assert not pd.api.types.is_float_dtype(seria), (
            f"{tabela}.{kolumna}: cala kolumna wrocila jako typ "
            f"zmiennoprzecinkowy ({seria.dtype}). To jest droga, ktora gubi "
            f"grosze — patrz naglowek `magazyn.py`.")
        for wartosc in seria:
            assert not isinstance(wartosc, (float, np.floating)), (
                f"{tabela}.{kolumna}: wartosc {wartosc!r} jest typu "
                f"{type(wartosc).__name__}, a ma byc dziesietna")
            obejrzane += 1
    return obejrzane


# --- 1. kontrakt wyjscia: co dostaje reszta silnika -----------------------

def test_KAZDA_z_szesnastu_kolumn_kwotowych_wraca_jako_Decimal(p):
    """Typ, nie wartosc. Wszystkie 16 kolumn w 9 tabelach, po publicznej drodze."""
    _zasil_wszystkie_tabele_kwotowe(p)
    sprawdzone_pary, obejrzane_wartosci, tabele = 0, 0, set()
    for tabela, odczyt in ODCZYTY.items():
        ramka = odczyt(p)
        assert not ramka.empty, (
            f"{tabela}: odczyt pusty — straznik nie obejrzalby zadnej kwoty")
        for kolumna in magazyn._KWOTOWE[tabela]:
            sprawdzone_pary += 1
            for wartosc in ramka[kolumna]:
                assert type(wartosc) is Decimal, (
                    f"{tabela}.{kolumna}: {wartosc!r} jest typu "
                    f"{type(wartosc).__name__}, a ma byc Decimal")
                obejrzane_wartosci += 1
        tabele.add(tabela)
    # KONTROLA LICZNOSCI — trzy niezalezne liczby, nie „cos sprawdzilem".
    assert sprawdzone_pary == ILE_KOLUMN_KWOTOWYCH, (
        f"straznik obejrzal {sprawdzone_pary} kolumn kwotowych, "
        f"a `_KWOTOWE` niesie {ILE_KOLUMN_KWOTOWYCH}")
    assert len(tabele) == ILE_TABEL_KWOTOWYCH
    assert obejrzane_wartosci >= ILE_KOLUMN_KWOTOWYCH, (
        f"obejrzano {obejrzane_wartosci} wartosci — mniej niz jedna na kolumne")


def test_odczyty_POKRYWAJA_cale_KWOTOWE(p):
    """Nosnikiem listy tabel kwotowych jest `_KWOTOWE`; ten plik ja WOLA.

    Dopisanie tabeli do `_KWOTOWE` bez dopisania odczytu tutaj zostawiloby
    nowa tabele bez straznika przy zielonej suicie.
    """
    assert set(ODCZYTY) == set(magazyn._KWOTOWE), (
        f"rozjazd: brak odczytu dla {set(magazyn._KWOTOWE) - set(ODCZYTY)}, "
        f"odczyt bez tabeli dla {set(ODCZYTY) - set(magazyn._KWOTOWE)}")
    assert len(ODCZYTY) == ILE_TABEL_KWOTOWYCH


# --- 2. surowy odczyt: co oddaje sterownik, ZANIM zadziala normalizacja ---

def test_SUROWY_odczyt_z_bazy_nie_oddaje_liczby_zmiennoprzecinkowej(p, monkeypatch):
    """Tu zaczerwieni sie migracja — i to jest cel istnienia tego testu.

    `_wczytaj` naprawia typ PO odczycie, wiec kontrakt wyjscia (test wyzej)
    przezyje nawet wtedy, gdy droga odczytu odda `float64`: mapa opakuje
    liczbe z powrotem w `Decimal` i strata bedzie niewidoczna. Ten test patrzy
    na ramke TAK, JAK WYSZLA ZE STEROWNIKA — podglada w locie, nie powtarzajac
    ani jednego zapytania SQL z magazynu.

    PODGLAD PRZENIESIONY, NIE WYCISZONY (W4, 2026-08-29). Do podmiany
    sterownika szpieg siedzial na `pandas.read_sql`. Po podmianie magazyn tej
    funkcji NIE WOLA — biblioteka ramek obsluguje surowe polaczenie wylacznie
    dla SQLite, a jej `coerce_float` zamienialby `Decimal` na liczbe
    zmiennoprzecinkowa. Straznik wykryl wtedy WLASNE OSLEPIENIE i padl
    z komunikatem „szpieg nie zobaczyl ani jednego odczytu" (mutacja M10) —
    to zachowanie bylo zamierzone. Szpieg stoi teraz na `magazyn._ramka`,
    czyli na nowej i jedynej drodze odczytu do ramki.
    """
    zebrane: dict[str, list] = {}
    prawdziwy = magazyn._ramka

    def szpieg(polaczenie, sql, parametry=()):
        ramka = prawdziwy(polaczenie, sql, parametry)
        dopasowanie = re.search(r"FROM\s+(\w+)", sql)
        if dopasowanie:
            zebrane.setdefault(dopasowanie.group(1), []).append(ramka.copy())
        return ramka

    monkeypatch.setattr(magazyn, "_ramka", szpieg)
    _zasil_wszystkie_tabele_kwotowe(p)
    for odczyt in ODCZYTY.values():
        odczyt(p)

    obejrzane, tabele = 0, 0
    for tabela in magazyn._KWOTOWE:
        ramki = zebrane.get(tabela, [])
        assert ramki, f"{tabela}: szpieg nie zobaczyl ani jednego odczytu"
        surowa = max(ramki, key=len)
        assert not surowa.empty, f"{tabela}: surowa ramka pusta"
        obejrzane += wymagaj_kwot_bez_zmiennoprzecinkowych(surowa, tabela)
        tabele += 1
    assert tabele == ILE_TABEL_KWOTOWYCH
    assert obejrzane >= ILE_KOLUMN_KWOTOWYCH, (
        f"szpieg obejrzal {obejrzane} wartosci — za malo, zeby cokolwiek orzec")


# --- 3. stan PO MIGRACJI, wytworzony dzisiaj ------------------------------

def _polaczenie_oddajace_Decimal(tmp_path):
    """Sterownik oddajacy `Decimal` — ten sam ksztalt wejscia co psycopg
    na kolumnie `NUMERIC`. Zbudowany na SQLite, bo mechanizm, ktory badamy,
    siedzi w bibliotece ramek, nie w sterowniku. Po W4 to jest JEDYNE miejsce
    w tej suicie, ktore jeszcze dotyka SQLite — i dotyka go jako PRZYRZADU
    POMIAROWEGO, nie jako bazy aplikacji.

    `register_converter` jest globalny dla modulu `sqlite3`, ale dziala
    WYLACZNIE na polaczeniach otwartych z `detect_types`. `magazyn.
    _otworz_surowo` ich nie uzywa (`sqlite3.connect(str(sciezka),
    check_same_thread=False)`), wiec ta rejestracja nie moze zmienic
    zachowania zadnego innego testu ani produkcji.
    """
    sqlite3.register_converter("DECIMAL", lambda b: Decimal(b.decode()))
    polaczenie = sqlite3.connect(tmp_path / "po_migracji.db",
                                 detect_types=sqlite3.PARSE_DECLTYPES)
    polaczenie.execute("CREATE TABLE wpisy_budzetu (kwota DECIMAL)")
    polaczenie.execute("INSERT INTO wpisy_budzetu VALUES ('249.99')")
    polaczenie.execute("INSERT INTO wpisy_budzetu VALUES ('11200.00')")
    polaczenie.commit()
    return polaczenie


def test_sterownik_oddajacy_Decimal_ZAPALA_straznika(tmp_path):
    """KONTROLA DWUSTRONNA i zarazem odpowiedz na pytanie „czy to sie
    zaczerwieni po podmianie sterownika".

    Gdy sterownik oddaje `Decimal`, `pd.read_sql` z domyslnym
    `coerce_float=True` oddaje `float64` — i straznik z tego pliku PADA.
    Ta sama ramka czytana z `coerce_float=False` straznika nie czerwieni.
    """
    polaczenie = _polaczenie_oddajace_Decimal(tmp_path)
    try:
        surowy = polaczenie.execute("SELECT kwota FROM wpisy_budzetu").fetchall()
        assert [type(w[0]).__name__ for w in surowy] == ["Decimal", "Decimal"], (
            "zalozenie testu: sterownik ma oddawac Decimal, jak psycopg")

        po_migracji = pd.read_sql("SELECT * FROM wpisy_budzetu", polaczenie)
        assert pd.api.types.is_float_dtype(po_migracji["kwota"]), (
            "zalozenie testu: pandas z domyslnym coerce_float ma zamienic "
            f"Decimal na liczbe zmiennoprzecinkowa, dostano {po_migracji.dtypes}")
        with pytest.raises(AssertionError, match="zmiennoprzecinkow"):
            wymagaj_kwot_bez_zmiennoprzecinkowych(po_migracji, "wpisy_budzetu")

        bez_koercji = pd.read_sql("SELECT * FROM wpisy_budzetu", polaczenie,
                                  coerce_float=False)
        assert wymagaj_kwot_bez_zmiennoprzecinkowych(
            bez_koercji, "wpisy_budzetu") == 2, (
            "druga strona kontroli: poprawna ramka NIE ma czerwienic")
    finally:
        polaczenie.close()


# --- 4. dlaczego wartosc nie wystarczy ------------------------------------

def test_asercja_przez_Decimal_str_JEST_slepa():
    """Powod, dla ktorego caly ten plik sprawdza typ, a nie kwote.

    `Decimal(str(x))` — ksztalt uzyty w kazdej dotychczasowej asercji kwotowej
    tej suity — daje ten sam wynik dla napisu, dla `Decimal` i dla `float`.
    Podmiana typu jest dla niego niewidoczna.
    """
    kwota = "11200.00"
    przez_napis = Decimal(str(kwota))
    przez_decimal = Decimal(str(Decimal(kwota)))
    przez_float = Decimal(str(float(kwota)))
    assert przez_napis == przez_decimal == przez_float, (
        "zalozenie: trzy drogi daja rowna wartosc")
    assert type(float(kwota)) is not Decimal, (
        "a mimo rownosci wartosci typ jest inny — i tego rownosc nie widzi")


def test_droga_przez_liczbe_zmiennoprzecinkowa_GUBI_grosze():
    """Strata nie jest teoretyczna — ma zmierzona wielkosc.

    Sedno: `float` ma skonczona liczbe cyfr znaczacych, wiec istnieje kwota,
    ktora po tej drodze WRACA INNA. Aplikacja podatkowa nie ma prawa na to
    liczyc, ze akurat ta kwota sie nie trafi.
    """
    kwota = Decimal("1234567890123456.78")
    po_drodze = Decimal(str(float(kwota)))
    assert po_drodze != kwota, "zalozenie testu: ta kwota ma sie zepsuc"
    assert kwota - po_drodze == Decimal("-0.02"), (
        f"strata na tej kwocie: {kwota - po_drodze}")

# -*- coding: utf-8 -*-
"""Straznik W3-2: zdanie o powtorzonym numerze faktury przezywa podmiane sterownika.

CO PILNUJE. `magazyn._zapisz` tlumaczy bledy bazy na zdania dla czlowieka.
Jedno z nich — „Faktura o tym numerze juz jest w bazie (FV/…)" — powstaje
przez DOPASOWANIE PO TRESCI KOMUNIKATU STEROWNIKA:

    except sqlite3.IntegrityError as e:          # magazyn.py:1008
        if "numer_faktury" in str(e):            # magazyn.py:1009

DWIE RZECZY PEKNA PO MIGRACJI, I TYLKO JEDNA JEST OCZYWISTA.

1. **Klauzula `except` przestanie lapac cokolwiek.** psycopg podnosi
   `psycopg.errors.UniqueViolation`, ktora nie dziedziczy z `sqlite3.Error`.
   Nie zadziala ani galaz z numerem faktury, ani zapasowe „Zapis odrzucony
   przez baze" — wyjatek sterownika wyleci z magazynu NIETLUMACZONY, przez
   caly silnik, az na ekran. To pilnuje `test_tlumaczenie_wyjatkow_OBEJMUJE_*`.

2. **Dopasowanie po tresci moze przezyc PRZYPADKIEM — i to jest gorsze.**
   Pomiar 2026-08-29, sterownik SQLite:
       'UNIQUE constraint failed: przychody_jdg.numer_faktury'
   PostgreSQL na `numer_faktury TEXT NOT NULL UNIQUE` (`schemat.sql:86`, wiez
   BEZ NAZWY WLASNEJ) nada wiezowi nazwe automatyczna
   `przychody_jdg_numer_faktury_key` i powie:
       duplicate key value violates unique constraint "przychody_jdg_numer_faktury_key"
   Napis „numer_faktury" **jest w obu**. Warunek trafi wiec dalej — dopoki
   ktos nie nazwie wiezu inaczej. Zdanie dla czlowieka wisi na nazwie wiezu,
   ktorej nikt nie wybral swiadomie. **To jest znalezisko, nie naprawa** —
   naprawa nalezy do W4 (`docs/plan-chmura-2026-08-29.md`).

CZEGO TEN STRAZNIK NIE ROBI: nie naprawia zadnej z dwoch rzeczy. Opisuje
kontrakt widziany przez uzytkownika (testy 1-2) i stan faktyczny sprzegniecia
ze sterownikiem (testy 3-5), zeby migracja nie mogla ich zabrac po cichu.
"""
from datetime import date
from decimal import Decimal
import pathlib
import re

import pytest

from silnik.rdzen import magazyn
from testy import pomocnicze

KORZEN = pathlib.Path(__file__).resolve().parent.parent

#: Pomiar 2026-08-29 na `silnik/rdzen/magazyn.py` (2485 linii), po zdjeciu
#: komentarzy i docstringow. Liczby sa TRIPWIREM MIGRACJI: po podmianie
#: sterownika maja zejsc do zera, a test ma zaczerwienic sie raz — swiadomie,
#: nie po cichu.
ILE_DOPASOWAN_PO_TRESCI = 1
ILE_KLAUZUL_EXCEPT_SQLITE = 10
ILE_KLAUZUL_INTEGRITY = 1

#: Zdanie, ktore uzytkownik ma zobaczyc. Nosnik jest w `magazyn._zapisz`;
#: tutaj stoi jego FRAGMENT ROZPOZNAWCZY, nie kopia calosci.
ZDANIE_O_DUPLIKACIE = "Faktura o tym numerze już jest"


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz(tmp_path / "test.db")
    yield polaczenie
    polaczenie.close()


def _faktura(polaczenie, **nadpisania):
    dane = dict(
        data=date(2026, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    dane.update(nadpisania)
    return magazyn.zapisz_fakture(polaczenie, **dane)


# --- 1. kontrakt widziany przez czlowieka ---------------------------------

def test_duplikat_numeru_MOWI_o_numerze_a_nie_o_bazie(p):
    """Zdanie ma nazwac powod i podac numer. Kontrola licznosci: druga
    faktura NIE wchodzi do bazy — inaczej test przechodzilby na wyjatku
    rzuconym z zupelnie innego powodu."""
    _faktura(p)
    with pytest.raises(magazyn.BladMagazynu) as zlapany:
        _faktura(p)
    komunikat = str(zlapany.value)
    assert ZDANIE_O_DUPLIKACIE in komunikat, (
        f"uzytkownik dostal: {komunikat!r}")
    assert "FV/1/2026" in komunikat, (
        "zdanie ma podac NUMER, ktory sie powtorzyl — bez niego nie wiadomo, "
        f"ktory: {komunikat!r}")
    assert "Zapis odrzucony przez bazę" not in komunikat, (
        "to jest komunikat zapasowy; jego pojawienie sie tutaj znaczy, ze "
        "rozpoznanie duplikatu przestalo trafiac")
    assert len(magazyn.wczytaj_faktury(p)) == 1, (
        "kontrola licznosci: w bazie ma zostac jedna faktura")


def test_INNE_naruszenie_wiezu_daje_komunikat_OGOLNY(p):
    """Druga strona kontroli. Gdyby galaz duplikatu lapala WSZYSTKO, test
    wyzej bylby zielony takze w kodzie, ktory rozpoznania nie ma."""
    with pytest.raises(magazyn.BladMagazynu) as zlapany:
        magazyn._zapisz(p, "INSERT INTO przychody_jdg (numer_faktury)"
                           " VALUES (?)", ("FV/BEZ-RESZTY",))
    komunikat = str(zlapany.value)
    assert ZDANIE_O_DUPLIKACIE not in komunikat, (
        f"naruszenie NOT NULL dostalo zdanie o duplikacie: {komunikat!r}")
    assert "Zapis odrzucony przez bazę" in komunikat, komunikat
    assert len(magazyn.wczytaj_faktury(p)) == 0, "kontrola licznosci"


# --- 2. sprzegniecie ze sterownikiem, zmierzone ---------------------------

class BladObcegoSterownika(Exception):
    """Ksztalt wyjatku, ktory poda psycopg: NIE dziedziczy z `sqlite3.Error`."""


class AtrapaPolaczenia:
    """Polaczenie, ktore zachowuje sie jak baza PostgreSQL przy duplikacie."""

    #: Dokladny ksztalt komunikatu PostgreSQL dla wiezu bez nazwy wlasnej.
    KOMUNIKAT = ('duplicate key value violates unique constraint '
                 '"przychody_jdg_numer_faktury_key"')

    def execute(self, sql, wartosci=()):
        raise BladObcegoSterownika(self.KOMUNIKAT)


def test_tlumaczenie_wyjatkow_OBEJMUJE_WYLACZNIE_sterownik_sqlite3():
    """TRIPWIRE MIGRACJI. Dzis `_zapisz` tlumaczy wylacznie wyjatki SQLite;
    wyjatek innego sterownika przechodzi przez magazyn NIETLUMACZONY.

    Test opisuje stan faktyczny, nie zyczenie. Gdy W4 rozszerzy tlumaczenie
    na psycopg, ten test zaczerwieni sie — i to jest jego cala wartosc:
    wymusza SWIADOMA zmiane zamiast cichej utraty zdania dla czlowieka.
    """
    atrapa = AtrapaPolaczenia()
    with pytest.raises(BladObcegoSterownika) as zlapany:
        magazyn._zapisz(atrapa, "INSERT INTO przychody_jdg …", (0, "FV/1/2026"))
    assert not isinstance(zlapany.value, magazyn.BladMagazynu), (
        "gdyby to byl BladMagazynu, tlumaczenie juz obejmowaloby obcy "
        "sterownik — zaktualizuj ten straznik i stale ILE_* nizej")
    assert "numer_faktury" in str(zlapany.value), (
        "zalozenie testu: komunikat PostgreSQL NIESIE nazwe kolumny w nazwie "
        "wiezu — dlatego dopasowanie po tresci moze przezyc PRZYPADKIEM")


def test_komunikat_SQLite_niesie_nazwe_kolumny(p):
    """Dlaczego dzisiejsze dopasowanie po tresci w ogole dziala.

    Pomiar, nie zalozenie: sterownik mowi
    'UNIQUE constraint failed: przychody_jdg.numer_faktury'.
    """
    import sqlite3

    _faktura(p)
    with pytest.raises(sqlite3.IntegrityError) as zlapany:
        p.execute(
            "INSERT INTO przychody_jdg (data, numer_faktury, kwota_netto,"
            " stawka_vat, kwota_vat, pkwiu, stawka_ryczaltu, zaplacony_zus,"
            " zysk_netto, stawki_wersja)"
            " VALUES ('2026-09-30','FV/1/2026','1','1','1','x','1','1','1','v')")
    surowy = str(zlapany.value)
    assert "numer_faktury" in surowy, surowy
    assert "UNIQUE" in surowy, surowy


def test_ILE_miejsc_rozstrzyga_po_TRESCI_komunikatu_sterownika():
    """Kontrola licznosci sprzegniecia — pomiar, nie liczba z planu.

    Plan sesji (`docs/plan-chmura-2026-08-29.md`, W3 poz. 2) nazywa JEDNO
    miejsce dopasowujace sie po tresci komunikatu. Pomiar to potwierdza,
    ale pokazuje przy tym DZIESIEC klauzul `except sqlite3.…` — kazda z nich
    przestanie lapac cokolwiek po podmianie sterownika.
    """
    zrodlo = (KORZEN / "silnik" / "rdzen" / "magazyn.py").read_text(encoding="utf-8")
    assert len(zrodlo) > 50_000, "kontrola: plik ma byc wczytany w calosci"
    kod = pomocnicze.kod_pythona_bez_prozy(zrodlo)

    po_tresci = re.findall(r"in\s+str\(\s*e\s*\)", kod)
    except_sqlite = re.findall(r"except\s+sqlite3\.", kod)
    integrity = re.findall(r"except\s+sqlite3\.IntegrityError", kod)

    assert len(po_tresci) == ILE_DOPASOWAN_PO_TRESCI, (
        f"dopasowan po tresci komunikatu sterownika: {len(po_tresci)}, "
        f"zmierzono {ILE_DOPASOWAN_PO_TRESCI}")
    assert len(except_sqlite) == ILE_KLAUZUL_EXCEPT_SQLITE, (
        f"klauzul `except sqlite3.…`: {len(except_sqlite)}, "
        f"zmierzono {ILE_KLAUZUL_EXCEPT_SQLITE} — kazda z nich przestaje "
        f"lapac po podmianie sterownika")
    assert len(integrity) == ILE_KLAUZUL_INTEGRITY


def test_ZADEN_INNY_modul_nie_rozstrzyga_po_tresci_komunikatu():
    """Sprzegniecie ma byc w jednym pliku. Kontrola licznosci: ile plikow
    przeszukano — przeszukanie, do ktorego nie dotarl zaden plik, meldowaloby
    „zero miejsc" takze przy skasowanym katalogu."""
    pliki = sorted(p for katalog in ("silnik", "api", "wiedza")
                   for p in (KORZEN / katalog).rglob("*.py")
                   if "__pycache__" not in p.parts)
    assert len(pliki) >= 20, f"przeszukano {len(pliki)} plikow — za malo"
    trafienia = []
    for plik in pliki:
        kod = pomocnicze.kod_pythona_bez_prozy(plik.read_text(encoding="utf-8"))
        if re.search(r"in\s+str\(\s*e\s*\)", kod):
            trafienia.append(plik.relative_to(KORZEN).as_posix())
    assert trafienia == ["silnik/rdzen/magazyn.py"], (
        f"dopasowanie po tresci komunikatu sterownika poza magazynem: {trafienia}")

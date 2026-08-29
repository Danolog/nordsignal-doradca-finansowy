# -*- coding: utf-8 -*-
"""Straznik: zdanie o powtorzonym numerze faktury PRZEZYLO podmiane sterownika.

CO PILNUJE. `magazyn._zapisz` tlumaczy bledy bazy na zdania dla czlowieka.
Jedno z nich — „Faktura o tym numerze juz jest w bazie (FV/…)" — powstaje
teraz przez ROZPOZNANIE WIEZU PO NAZWIE:

    except psycopg.errors.UniqueViolation as e:
        if e.diag.constraint_name == WIEZ_NUMER_FAKTURY:

DO W4 (2026-08-29) BYLO INACZEJ i to jest cala tresc tego pliku:

    except sqlite3.IntegrityError as e:
        if "numer_faktury" in str(e):

DWIE RZECZY PEKLY PRZY MIGRACJI, I TYLKO JEDNA BYLA OCZYWISTA.

1. **Klauzula `except` przestala lapac cokolwiek.** psycopg podnosi
   `psycopg.errors.UniqueViolation`, ktora nie dziedziczy z `sqlite3.Error`.
   Nie zadzialalaby ani galaz z numerem faktury, ani zapasowe „Zapis odrzucony
   przez baze" — wyjatek sterownika wylecialby z magazynu NIETLUMACZONY, przez
   caly silnik, az na ekran. Wszystkie dziesiec klauzul `except sqlite3.…`
   zostalo przepisanych; pilnuje tego `test_ILE_miejsc_…` nizej, ktory zada
   ZERA takich klauzul i DZIESIECIU klauzul psycopg.

2. **Dopasowanie po tresci moglo przezyc PRZYPADKIEM — i to bylo gorsze.**
   Pomiar 2026-08-29 na dzialajacej bazie PostgreSQL: wiez bez nazwy wlasnej
   dostaje nazwe automatyczna `przychody_jdg_numer_faktury_key`, a serwer mowi
       duplicate key value violates unique constraint "przychody_jdg_numer_faktury_key"
   Napis „numer_faktury" **jest w obu** komunikatach — sqlite'owym
   i postgresowym. Warunek trafialby wiec dalej, dopoki ktos nie nazwalby
   wiezu inaczej. Zdanie dla czlowieka wisialoby na nazwie, KTOREJ NIKT NIE
   WYBRAL. Naprawa: wiez ma nazwe wlasna (`numer_faktury_niepowtarzalny`,
   `silnik/baza/schemat.sql`), a kod czyta `e.diag.constraint_name` — czyli
   odpowiedz SERWERA na pytanie „ktory wiez", a nie zdanie, ktore ktos moze
   przeredagowac przy najblizszej zmianie wersji.

CO ZOSTAJE NIEPILNOWANE, wprost: tresc komunikatu ZAPASOWEGO („Zapis odrzucony
przez baze. Szczegol: …") wciaga tekst serwera, a ten bywa przetlumaczony na
jezyk instalacji. Rozpoznanie duplikatu od tresci nie zalezy; komunikat
zapasowy — owszem.
"""
from datetime import date
from decimal import Decimal
import pathlib
import re

import psycopg
import pytest

from silnik.rdzen import magazyn
from testy import pomocnicze

KORZEN = pathlib.Path(__file__).resolve().parent.parent

#: TRIPWIRE MIGRACJI, KTORY ZADZIALAL. Przed W4 liczby brzmialy 1 / 10 / 1
#: i naglowek zapowiadal: „po podmianie sterownika maja zejsc do zera, a test
#: ma zaczerwienic sie raz — swiadomie, nie po cichu". Zaczerwienil sie
#: 2026-08-29 i zostal zaktualizowany razem z kodem.
#:
#: ZERO JEST TU ASERCJA, NIE BRAKIEM ASERCJI: dopisanie gdziekolwiek w module
#: `except sqlite3.…` albo `if … in str(e)` czerwieni ten plik natychmiast.
ILE_DOPASOWAN_PO_TRESCI = 0
ILE_KLAUZUL_EXCEPT_SQLITE = 0
ILE_KLAUZUL_INTEGRITY = 0

#: Ile klauzul lapiacych bledy sterownika ma stac w module. Pomiar
#: 2026-08-29 po W4: SIEDEMNASCIE (`except psycopg.…`) — wiecej niz dziesiec
#: sprzed migracji, bo doszly miejsca, ktore u poprzednika nie mialy czego
#: lapac: kopia przed migracja, odtworzenie z kopii, dwie funkcje atomowe
#: i odczyt do ramki. Bez tej liczby asercje
#: „zero" wyzej sa prawdziwe takze dla modulu, z ktorego ktos usunal CALE
#: tlumaczenie bledow bazy — czyli przy zielonym tescie i wyjatku sterownika
#: lecacym prosto na ekran.
ILE_KLAUZUL_EXCEPT_PSYCOPG = 17

#: Zdanie, ktore uzytkownik ma zobaczyc. Nosnik jest w `magazyn._zapisz`;
#: tutaj stoi jego FRAGMENT ROZPOZNAWCZY, nie kopia calosci.
ZDANIE_O_DUPLIKACIE = "Faktura o tym numerze już jest"


@pytest.fixture
def p(tmp_path):
    polaczenie = magazyn.zmigruj_i_polacz()
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
                           " VALUES (%s)", ("FV/BEZ-RESZTY",))
    komunikat = str(zlapany.value)
    assert ZDANIE_O_DUPLIKACIE not in komunikat, (
        f"naruszenie NOT NULL dostalo zdanie o duplikacie: {komunikat!r}")
    assert "Zapis odrzucony przez bazę" in komunikat, komunikat
    assert len(magazyn.wczytaj_faktury(p)) == 0, "kontrola licznosci"


# --- 2. sprzegniecie ze sterownikiem, zmierzone ---------------------------

class AtrapaPolaczenia:
    """Polaczenie, ktore zachowuje sie jak baza PostgreSQL przy duplikacie.

    Atrapa, a nie prawdziwa baza, bo badamy ROZPOZNANIE: chcemy podac nazwe
    wiezu i tresc komunikatu OSOBNO, zeby zobaczyc, na czym wisi zdanie dla
    czlowieka. Prawdziwa baza zawsze poda oba naraz i zgodnie — i wlasnie
    dlatego sama nie odpowie na pytanie „na czym to wisi".
    """

    def __init__(self, *, nazwa_wiezu: str, komunikat: str):
        self.NAZWA_WIEZU = nazwa_wiezu
        self.KOMUNIKAT = komunikat

    def execute(self, sql, wartosci=()):
        # `diag` prawdziwego wyjatku powstaje z odpowiedzi serwera i jest
        # WLASNOSCIA TYLKO DO ODCZYTU — nie da sie go podstawic na gotowym
        # obiekcie. Robimy wiec podklase, ktora oddaje wlasny obiekt o tym
        # samym ksztalcie; dziedziczenie po `UniqueViolation` zostaje, bo to
        # ono decyduje, ktora klauzula `except` zlapie ten wyjatek.
        nazwa = self.NAZWA_WIEZU

        class UdawanyDuplikat(psycopg.errors.UniqueViolation):
            @property
            def diag(self):
                return type("Diag", (), {"constraint_name": nazwa})()

        raise UdawanyDuplikat(self.KOMUNIKAT)

    def rollback(self):
        pass


def test_rozpoznanie_NIE_ZALEZY_od_tresci_komunikatu():
    """ODWROCONY TRIPWIRE. Przed W4 ten test stwierdzal, ze tlumaczenie
    obejmuje WYLACZNIE sterownik SQLite; teraz stwierdza, ze rozpoznanie
    duplikatu nie zalezy od ani jednego slowa komunikatu.

    Atrapa podnosi `UniqueViolation` z komunikatem, w ktorym slowa
    „numer_faktury" NIE MA WCALE — a mimo to zdanie dla czlowieka pada,
    bo nazwa wiezu sie zgadza. Gdyby kod nadal czytal tresc, ten test
    zaczerwienilby sie natychmiast.
    """
    atrapa = AtrapaPolaczenia(nazwa_wiezu=magazyn.WIEZ_NUMER_FAKTURY,
                              komunikat="duplicate key value violates something")
    assert "numer_faktury" not in atrapa.KOMUNIKAT, (
        "zalozenie testu: komunikat ma NIE niesc nazwy kolumny")
    with pytest.raises(magazyn.BladMagazynu) as zlapany:
        magazyn._zapisz(atrapa, "INSERT INTO przychody_jdg …", (0, "FV/1/2026"))
    assert ZDANIE_O_DUPLIKACIE in str(zlapany.value), str(zlapany.value)


def test_rozpoznanie_NIE_TRAFIA_w_wiez_o_nazwie_AUTOMATYCZNEJ():
    """DRUGA STRONA znaleziska W3 — i powod, dla ktorego wiez dostal nazwe.

    Nazwa automatyczna `przychody_jdg_numer_faktury_key` NIESIE napis
    „numer_faktury". Dawne dopasowanie po tresci trafialoby w nia PRZYPADKIEM.
    Rozpoznanie po nazwie ma trafiac wylacznie w nazwe WYBRANA — dlatego
    naruszenie wiezu o nazwie automatycznej dostaje komunikat OGOLNY.
    """
    atrapa = AtrapaPolaczenia(
        nazwa_wiezu="przychody_jdg_numer_faktury_key",
        komunikat='duplicate key value violates unique constraint '
                  '"przychody_jdg_numer_faktury_key"')
    with pytest.raises(magazyn.BladMagazynu) as zlapany:
        magazyn._zapisz(atrapa, "INSERT INTO przychody_jdg …", (0, "FV/1/2026"))
    assert ZDANIE_O_DUPLIKACIE not in str(zlapany.value), (
        "zdanie o duplikacie wisi na nazwie, ktorej nikt nie wybral: "
        + str(zlapany.value))
    assert "Zapis odrzucony przez bazę" in str(zlapany.value)


def test_PRAWDZIWA_baza_podaje_te_sama_nazwe_wiezu(p):
    """Pomiar na dzialajacej bazie, nie na atrapie.

    Atrapy wyzej sprawdzaja ROZPOZNANIE; ten test sprawdza, ze serwer
    naprawde podaje nazwe, ktorej rozpoznanie szuka. Bez niego cala reszta
    pliku moglaby byc zielona przy wiezie nazwanym w bazie zupelnie inaczej.
    """
    _faktura(p)
    with pytest.raises(psycopg.errors.UniqueViolation) as zlapany:
        p.execute(
            "INSERT INTO przychody_jdg (data, numer_faktury, kwota_netto,"
            " stawka_vat, kwota_vat, pkwiu, zaplacony_zus,"
            " zysk_netto, stawki_wersja)"
            " VALUES ('2026-09-30','FV/1/2026',1,1,1,'x',1,1,'v')")
    assert zlapany.value.diag.constraint_name == magazyn.WIEZ_NUMER_FAKTURY, (
        f"serwer podal wiez {zlapany.value.diag.constraint_name!r}, a kod "
        f"rozpoznaje {magazyn.WIEZ_NUMER_FAKTURY!r}")


def test_ILE_miejsc_rozstrzyga_po_TRESCI_komunikatu_sterownika():
    """Kontrola licznosci sprzegniecia — pomiar, nie liczba z planu.

    Przed W4: jedno dopasowanie po tresci, dziesiec klauzul `except sqlite3.…`.
    Po W4: zero i zero, plus dziesiec klauzul `except psycopg.…`. Wszystkie
    cztery liczby stoja w asercjach, nie w nazwie testu.
    """
    zrodlo = (KORZEN / "silnik" / "rdzen" / "magazyn.py").read_text(encoding="utf-8")
    assert len(zrodlo) > 50_000, "kontrola: plik ma byc wczytany w calosci"
    kod = pomocnicze.kod_pythona_bez_prozy(zrodlo)

    po_tresci = re.findall(r"in\s+str\(\s*e\s*\)", kod)
    except_sqlite = re.findall(r"except\s+sqlite3\.", kod)
    integrity = re.findall(r"except\s+sqlite3\.IntegrityError", kod)
    except_psycopg = re.findall(r"except\s+psycopg\.", kod)

    # KONTROLA LICZNOSCI: bez niej trzy asercje „zero" nizej sa prawdziwe
    # takze dla modulu, z ktorego ktos usunal CALE tlumaczenie bledow bazy.
    assert len(except_psycopg) == ILE_KLAUZUL_EXCEPT_PSYCOPG, (
        f"klauzul `except psycopg.…`: {len(except_psycopg)}, pomiar "
        f"2026-08-29 po W4 dal {ILE_KLAUZUL_EXCEPT_PSYCOPG} — mniej znaczy, "
        f"ze blad sterownika leci przez magazyn nietlumaczony")

    assert len(po_tresci) == ILE_DOPASOWAN_PO_TRESCI, (
        f"dopasowan po tresci komunikatu sterownika: {len(po_tresci)}, "
        f"zmierzono {ILE_DOPASOWAN_PO_TRESCI}")
    assert len(except_sqlite) == ILE_KLAUZUL_EXCEPT_SQLITE, (
        f"klauzul `except sqlite3.…`: {len(except_sqlite)}, "
        f"ma byc {ILE_KLAUZUL_EXCEPT_SQLITE} — taka klauzula nie lapie juz "
        f"niczego i cicho przepuszcza blad sterownika az na ekran")
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
    # ZERO, nie „tylko magazyn" (W4). Rozpoznanie idzie po nazwie wiezu,
    # wiec dopasowanie po tresci komunikatu sterownika nie ma juz prawa stac
    # NIGDZIE — takze w magazynie. Liczba przeszukanych plikow wyzej jest
    # kontrola licznosci: przeszukanie, do ktorego nie dotarl zaden plik,
    # meldowaloby „zero miejsc" takze przy skasowanym katalogu.
    assert trafienia == [], (
        f"dopasowanie po tresci komunikatu sterownika: {trafienia}")

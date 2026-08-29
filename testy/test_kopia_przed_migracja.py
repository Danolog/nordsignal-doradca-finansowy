"""Strazniki kopii przed migracja i wycofania nieudanej migracji (Z53).

Specyfikacja §7.6: „kopia bazy robi sie sama przed kazda zmiana schematu
i przed kazdym zaciagiem — dzis tego w kodzie NIE MA; osiem kopii w katalogu
zrobil czlowiek, pamietajac za kazdym razem".

Z53 jest pierwsza migracja cwiczona przez Z60 (schemat 8), wiec musi dzialac
zanim ktokolwiek podniesie `WERSJA_SCHEMATU`.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from silnik.rdzen import budzet, magazyn


def _baza_w_wersji(sciezka: Path, wersja: int) -> None:
    """Realna baza z danymi, ostemplowana podana wersja schematu."""
    magazyn.zmigruj_i_polacz(sciezka).close()
    p = sqlite3.connect(str(sciezka))
    p.execute("INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, szczegoly) "
              "VALUES ('2026-08-01', ?, 'Zakupy', '10.00', '')",
              (budzet.TYP_WYDATKI,))
    p.execute(f"PRAGMA user_version = {wersja}")
    p.commit()
    p.close()


def _kopie(katalog: Path) -> list[Path]:
    return sorted(katalog.glob("*-kopia-przed-migracja-*"))


# --- kopia powstaje dokladnie wtedy, kiedy trzeba -------------------------

def test_migracja_ZOSTAWIA_kopie_w_wersji_sprzed(tmp_path, monkeypatch):
    """Kryterium odbioru planu: „migracja z wersji 7 na 8 zostawia kopie
    w wersji 7". Podniesienie wersji symulowane, bo `WERSJA_SCHEMATU`
    podnosi dopiero Z57 — mechanizm ma dzialac wczesniej."""
    baza = tmp_path / "cfo.db"
    _baza_w_wersji(baza, 7)
    monkeypatch.setattr(magazyn, "WERSJA_SCHEMATU", 8)

    magazyn.zmigruj_i_polacz(baza).close()

    kopie = _kopie(tmp_path)
    assert len(kopie) == 1, f"kopii jest {len(kopie)}, nie jedna"
    stara = sqlite3.connect(str(kopie[0]))
    assert stara.execute("PRAGMA user_version").fetchone()[0] == 7
    assert stara.execute("SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 1
    stara.close()


def test_kopia_NIE_powstaje_gdy_nie_ma_migracji(tmp_path):
    """Kontrola dwustronna. Kopia przy kazdym otwarciu zasypalaby katalog
    i przestalaby cokolwiek znaczyc — a limit miejsca jest realny."""
    baza = tmp_path / "cfo.db"
    _baza_w_wersji(baza, magazyn.WERSJA_SCHEMATU)
    magazyn.zmigruj_i_polacz(baza).close()
    assert _kopie(tmp_path) == []


def test_kopia_NIE_powstaje_dla_nowej_bazy(tmp_path):
    """Brak pliku to normalny stan poczatkowy, nie awaria — nie ma czego kopiowac."""
    magazyn.zmigruj_i_polacz(tmp_path / "swieza.db").close()
    assert _kopie(tmp_path) == []


def test_nazwa_kopii_niesie_ZNACZNIK_CZASU_co_do_minuty(tmp_path, monkeypatch):
    """Bez znacznika druga migracja tego samego dnia nadpisalaby pierwsza."""
    baza = tmp_path / "cfo.db"
    _baza_w_wersji(baza, 6)
    monkeypatch.setattr(magazyn, "_teraz",
                        lambda: datetime(2026, 8, 27, 14, 5))
    magazyn.zmigruj_i_polacz(baza).close()
    assert [p.name for p in _kopie(tmp_path)] \
        == ["cfo.db-kopia-przed-migracja-2026-08-27-1405"]


def test_kopia_bierze_nazwe_od_OTWIERANEJ_bazy_a_nie_od_stalej(tmp_path, monkeypatch):
    """Od Z52 baza bywa kopia robocza. Nazwa `cfo_database.db-...` na sztywno
    nazwalaby plik, ktorego w tym katalogu nie ma."""
    baza = tmp_path / "cfo_database.db-robocza"
    _baza_w_wersji(baza, 6)
    magazyn.zmigruj_i_polacz(baza).close()
    assert _kopie(tmp_path)[0].name.startswith("cfo_database.db-robocza-kopia-")


# --- brak miejsca: migracja NIE startuje ---------------------------------

def test_brak_miejsca_ZATRZYMUJE_migracje_zanim_ruszy(tmp_path, monkeypatch):
    """Kryterium odbioru planu. Sedno jest w drugiej polowie: nie „rzuca
    bledem", tylko „baza zostaje NIETKNIETA". Migracja bez kopii, ktora
    wystartowala i padla, jest gorsza niz migracja, ktora nie ruszyla."""
    baza = tmp_path / "cfo.db"
    _baza_w_wersji(baza, 6)
    monkeypatch.setattr(magazyn, "_wolne_miejsce", lambda katalog: 1)

    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zmigruj_i_polacz(baza)

    assert "miejsca" in str(blad.value).lower()
    assert _kopie(tmp_path) == [], "kopia niepelna jest gorsza niz jej brak"
    p = sqlite3.connect(str(baza))
    assert p.execute("PRAGMA user_version").fetchone()[0] == 6, \
        "migracja ruszyla mimo braku miejsca"
    p.close()


def test_miejsca_STARCZA_gdy_jest_go_duzo(tmp_path):
    """Kontrola dwustronna: bramka, ktora blokuje zawsze, nie jest bramka."""
    baza = tmp_path / "cfo.db"
    _baza_w_wersji(baza, 6)
    magazyn.zmigruj_i_polacz(baza).close()
    assert len(_kopie(tmp_path)) == 1


def test_pomiar_wolnego_miejsca_WIDZI_cokolwiek(tmp_path):
    """Kontrola licznosci: pomiar, ktory zawsze zwraca zero, przepuscilby
    wszystko przy odwroconym warunku i nikt by nie zauwazyl."""
    assert magazyn._wolne_miejsce(tmp_path) > 0


# --- nieudana migracja naprawde sie wycofuje -----------------------------

def test_nieudana_kontrola_licznosci_WYCOFUJE_wiersze(tmp_path, monkeypatch):
    """Komunikat obiecuje „Zmiany wycofane" — do Z53 wycofanie bylo PRZYPADKOWE.

    Sterownik sqlite3 wycofuje otwarta transakcje przy zamknieciu polaczenia,
    wiec wady nie bylo widac. Wystarczy jednak, zeby ktokolwiek zawolal pozniej
    `commit()` na tym samym polaczeniu — i niedokonczona migracja zostaje
    ZATWIERDZONA pod komunikatem obiecujacym, ze jej nie ma.

    Dlatego ten test nie pyta o `in_transaction`, tylko robi to, co zrobilby
    kod obok: wola `commit()` i sprawdza, czy wiersze znikly.
    """
    baza = tmp_path / "cfo.db"
    polaczenie = magazyn.zmigruj_i_polacz(baza)
    polaczenie.execute("CREATE TABLE wydatki_osobiste "
                       "(data TEXT, kategoria TEXT, kwota TEXT)")
    polaczenie.execute("INSERT INTO wydatki_osobiste VALUES "
                       "('2026-08-01', 'Zakupy', '99.00')")
    polaczenie.commit()

    # kontrola licznosci ma sie NIE zgodzic
    monkeypatch.setattr(magazyn, "_liczba_wydatkow_w_budzecie",
                        lambda p: 0)

    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert "wycofane" in str(blad.value).lower()

    assert polaczenie.in_transaction is False, \
        "transakcja zostala otwarta — komunikat obiecal wiecej, niz zrobil"
    polaczenie.commit()          # to zrobiloby kazde nastepne zapisanie
    assert polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 0, \
        "wiersze przezyly wycofanie i zostaly zatwierdzone"
    polaczenie.close()


def test_udana_migracja_NIE_wycofuje_niczego(tmp_path):
    """Kontrola dwustronna: wycofanie ma dotykac wylacznie sciezki bledu."""
    baza = tmp_path / "cfo.db"
    polaczenie = magazyn.zmigruj_i_polacz(baza)
    polaczenie.execute("CREATE TABLE wydatki_osobiste "
                       "(data TEXT, kategoria TEXT, kwota TEXT)")
    polaczenie.execute("INSERT INTO wydatki_osobiste VALUES "
                       "('2026-08-01', 'Zakupy', '99.00')")
    polaczenie.commit()

    raport = magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert raport.przeniesione == 1
    polaczenie.close()

    ponownie = sqlite3.connect(str(baza))
    assert ponownie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 1
    ponownie.close()

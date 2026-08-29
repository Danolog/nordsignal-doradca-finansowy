# -*- coding: utf-8 -*-
"""Strazniki kopii przed migracja i wycofania nieudanej migracji.

Specyfikacja §7.6: „kopia bazy robi sie sama przed kazda zmiana schematu
i przed kazdym zaciagiem — osiem kopii w katalogu zrobil czlowiek, pamietajac
za kazdym razem".

CO SIE ZMIENILO W W4 (2026-08-29) — pozycja obowiazkowa §3.11.
Do podmiany sterownika kopia byla PLIKIEM obok pliku bazy (`shutil.copy2`).
Baza nie jest juz plikiem, wiec ta droga PRZESTALA ISTNIEC — razem z nia
przestal istniec pomiar wolnego miejsca na dysku (`_wolne_miejsce`), bo dysk
nalezy teraz do serwera i nie mamy do niego dostepu przez SQL.

ZASTEPNIK, ZBUDOWANY W TYM SAMYM ZADANIU: kopia jest PRZESTRZENIA NAZW
(`kopia_przed_migracja_<przestrzen>_<stempel>`) z tabelami zalozonymi przez
`CREATE TABLE ... AS TABLE`. Warunek uruchomienia sie nie zmienil (baza ma
dane I wersja jest nizsza niz kod), obietnica tez: **migracja, ktora nie ma
kopii, NIE RUSZA**.

CZEGO ZASTEPNIK NIE DAJE, WPROST:
  * kopia lezy w TEJ SAMEJ bazie — chroni przed zla migracja, nie przed utrata
    bazy. Przed tym chroni galaz Neona (`prod-backup-*`), robiona osobno;
  * bramki „czy starczy miejsca" NIE MA i nie ma jej nastepcy w kodzie.
    Zastepuje ja co innego: kopia jest robiona PRZED pierwszym zapisem
    migracji, wiec jej niepowodzenie z JAKIEGOKOLWIEK powodu (w tym braku
    miejsca u dostawcy) zatrzymuje migracje przed czymkolwiek nieodwracalnym.
    Bramka pytala „czy dam rade"; teraz po prostu probujemy i patrzymy.
"""

from datetime import datetime

import pytest

from silnik.rdzen import budzet, magazyn
from testy import pomocnicze


def _baza_w_wersji(wersja: int) -> None:
    """Realna baza z danymi, ostemplowana podana wersja schematu."""
    magazyn.zmigruj_i_polacz().close()
    p = pomocnicze.polaczenie_surowe()
    p.execute("INSERT INTO wpisy_budzetu (data, typ, kategoria, kwota, szczegoly) "
              "VALUES ('2026-08-01', %s, 'Zakupy', 10.00, '')",
              (budzet.TYP_WYDATKI,))
    p.execute("UPDATE wersja_schematu SET wersja = %s", (wersja,))
    p.commit()
    p.close()


def _kopie() -> list[str]:
    p = pomocnicze.polaczenie_surowe()
    try:
        return magazyn.kopie(p)
    finally:
        p.close()


# --- kopia powstaje dokladnie wtedy, kiedy trzeba -------------------------

def test_migracja_ZOSTAWIA_kopie_w_wersji_sprzed(monkeypatch):
    """Kryterium odbioru: „migracja z wersji 7 na 8 zostawia kopie w wersji 7".

    Podniesienie wersji symulowane, bo `WERSJA_SCHEMATU` podnosi dopiero
    kolejna zmiana schematu — mechanizm ma dzialac wczesniej.
    """
    _baza_w_wersji(7)
    monkeypatch.setattr(magazyn, "WERSJA_SCHEMATU", 8)

    magazyn.zmigruj_i_polacz().close()

    kopie = _kopie()
    assert len(kopie) == 1, f"kopii jest {len(kopie)}, nie jedna"
    p = pomocnicze.polaczenie_surowe()
    try:
        assert p.execute(
            f"SELECT wersja FROM {kopie[0]}.wersja_schematu").fetchone()[0] == 7
        assert p.execute(
            f"SELECT COUNT(*) FROM {kopie[0]}.wpisy_budzetu").fetchone()[0] == 1
    finally:
        p.close()


def test_kopia_NIE_powstaje_gdy_nie_ma_migracji():
    """Kontrola dwustronna. Kopia przy kazdym otwarciu zasypalaby baze
    i przestalaby cokolwiek znaczyc."""
    _baza_w_wersji(magazyn.WERSJA_SCHEMATU)
    magazyn.zmigruj_i_polacz().close()
    assert _kopie() == []


def test_kopia_NIE_powstaje_dla_nowej_bazy():
    """Pusta przestrzen to normalny stan poczatkowy, nie awaria — nie ma
    czego kopiowac."""
    magazyn.zmigruj_i_polacz().close()
    assert _kopie() == []


def test_kopia_NIE_powstaje_gdy_tabele_sa_PUSTE(monkeypatch):
    """Wymiar, ktorego poprzednik pilnowal wielkoscia pliku (`st_size == 0`).

    Baza ze schematem, ale bez ani jednego wiersza, nie ma czego stracic —
    a kopia czternastu pustych tabel wyglada dokladnie tak samo jak kopia
    danych i zasmieca liste, na ktorej ktos pozniej szuka ratunku.
    """
    magazyn.zmigruj_i_polacz().close()
    p = pomocnicze.polaczenie_surowe()
    p.execute("DELETE FROM kategorie")
    p.execute("DELETE FROM rejestr_stawek")
    p.execute("DELETE FROM forma_opodatkowania")
    p.execute("UPDATE wersja_schematu SET wersja = 6")
    p.commit()
    p.close()

    magazyn.zmigruj_i_polacz().close()
    assert _kopie() == []


def test_nazwa_kopii_niesie_ZNACZNIK_CZASU_co_do_minuty(monkeypatch):
    """Bez znacznika druga migracja tego samego dnia nadpisalaby pierwsza."""
    _baza_w_wersji(6)
    monkeypatch.setattr(magazyn, "_teraz",
                        lambda: datetime(2026, 8, 27, 14, 5))
    magazyn.zmigruj_i_polacz().close()
    assert [n.endswith("_2026_08_27_1405") for n in _kopie()] == [True]


def test_nazwa_kopii_niesie_nazwe_KOPIOWANEJ_przestrzeni(monkeypatch):
    """Kopie leza OBOK przestrzeni, nie w niej. Bez nazwy zrodla dwie kopie
    zrobione w tej samej minucie walczylyby o te sama nazwe — zmierzone
    2026-08-29 na suicie testow, gdzie kazdy test ma wlasna przestrzen."""
    _baza_w_wersji(6)
    magazyn.zmigruj_i_polacz().close()
    p = pomocnicze.polaczenie_surowe()
    try:
        moja = p.execute("SELECT current_schema()").fetchone()[0]
    finally:
        p.close()
    kopie = _kopie()
    assert len(kopie) == 1
    assert kopie[0].startswith(magazyn.PRZEDROSTEK_KOPII + moja + "_"), kopie


def test_kopia_PRZENOSI_WSZYSTKIE_wiersze_a_nie_same_tabele():
    """KONTROLA LICZNOSCI kopii. Kopia, do ktorej nic nie doszlo, melduje
    sukces dokladnie tak samo jak kopia pelna — a odkrywa sie to dopiero
    wtedy, gdy ktos z niej odtwarza."""
    _baza_w_wersji(6)
    p = pomocnicze.polaczenie_surowe()
    przed = {t: p.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in sorted(magazyn._tabele(p))}
    p.close()
    assert sum(przed.values()) > 40, (
        f"kontrola: baza ma niesc dane przed kopia, niesie {sum(przed.values())}")

    magazyn.zmigruj_i_polacz().close()
    kopia = _kopie()[0]
    p = pomocnicze.polaczenie_surowe()
    try:
        po = {t: p.execute(f"SELECT COUNT(*) FROM {kopia}.{t}").fetchone()[0]
              for t in przed}
    finally:
        p.close()
    assert po == przed, f"kopia zgubila wiersze: {po} wobec {przed}"


def test_kopia_DA_SIE_odtworzyc():
    """DRUGA POLOWA KOPII — i pozycja, ktorej poprzednik NIE MIAL.

    Kopia pliku dawala odtworzenie za darmo: wystarczylo podmienic plik.
    Kopia w przestrzeni nazw nie daje niczego za darmo, wiec droga powrotna
    musi byc KODEM, ktory da sie wykonac. „Umiem odtworzyc" bez wykonywalnej
    drogi jest deklaracja, nie dowodem.
    """
    _baza_w_wersji(6)
    magazyn.zmigruj_i_polacz().close()
    kopia = _kopie()[0]

    p = magazyn.polacz()
    try:
        ile_przed = p.execute("SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0]
        assert ile_przed == 1, "kontrola: kopia ma niesc jeden wpis"
        p.execute("DELETE FROM wpisy_budzetu")
        p.commit()
        assert p.execute("SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 0

        licznosc = magazyn.odtworz_z_kopii(p, kopia)

        assert p.execute("SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 1, \
            "odtworzenie nie przywrocilo wiersza"
        assert licznosc["wpisy_budzetu"] == 1
        assert licznosc["kategorie"] > 0, (
            "odtworzenie ma objac WSZYSTKIE tabele kopii, nie jedna")
    finally:
        p.close()


def test_odtworzenie_z_NIEISTNIEJACEJ_kopii_jest_bledem():
    """Kontrola dwustronna: droga powrotna ma odmawiac, a nie meldowac sukces
    nad pustym miejscem."""
    magazyn.zmigruj_i_polacz().close()
    p = magazyn.polacz()
    try:
        with pytest.raises(magazyn.BladMagazynu) as blad:
            magazyn.odtworz_z_kopii(p, "kopia_ktorej_nie_ma")
        assert "kopia_ktorej_nie_ma" in str(blad.value)
    finally:
        p.close()


def test_kopia_ISTNIEJACA_zatrzymuje_migracje_zanim_ruszy(monkeypatch):
    """NASTEPCA BRAMKI „za malo miejsca" — ta sama obietnica, inny powod.

    Sedno jest w drugiej polowie zdania: nie „rzuca bledem", tylko **baza
    zostaje NIETKNIETA**. Migracja bez kopii, ktora wystartowala i padla, jest
    gorsza niz migracja, ktora nie ruszyla.
    """
    _baza_w_wersji(6)
    monkeypatch.setattr(magazyn, "_teraz",
                        lambda: datetime(2026, 8, 27, 14, 5))
    p = pomocnicze.polaczenie_surowe()
    moja = p.execute("SELECT current_schema()").fetchone()[0]
    p.execute(f"CREATE SCHEMA {magazyn.PRZEDROSTEK_KOPII}{moja}_2026_08_27_1405")
    p.commit()
    p.close()

    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.zmigruj_i_polacz()
    assert "juz istnieje" in str(blad.value)
    assert "nietknieta" in str(blad.value)

    p = pomocnicze.polaczenie_surowe()
    try:
        assert p.execute(
            "SELECT wersja FROM wersja_schematu WHERE jedyny").fetchone()[0] == 6, \
            "migracja ruszyla mimo nieudanej kopii"
    finally:
        p.close()


# --- nieudana migracja naprawde sie wycofuje -----------------------------

def test_nieudana_kontrola_licznosci_WYCOFUJE_wiersze(monkeypatch):
    """Komunikat obiecuje „Zmiany wycofane" — do Z53 wycofanie bylo PRZYPADKOWE.

    Sterownik SQLite wycofywal otwarta transakcje przy zamknieciu polaczenia,
    wiec wady nie bylo widac. W PostgreSQL polaczenie bywa oddawane do puli,
    wiec porzucona transakcja przenosi sie na nastepne zadanie.

    Dlatego ten test robi to, co zrobilby kod obok: wola `commit()` i sprawdza,
    czy wiersze znikly.
    """
    polaczenie = magazyn.zmigruj_i_polacz()
    polaczenie.execute("CREATE TABLE wydatki_osobiste "
                       "(data DATE, kategoria TEXT, kwota NUMERIC(14,2))")
    polaczenie.execute("INSERT INTO wydatki_osobiste VALUES "
                       "('2026-08-01', 'Zakupy', 99.00)")
    polaczenie.commit()

    # kontrola licznosci ma sie NIE zgodzic
    monkeypatch.setattr(magazyn, "_liczba_wydatkow_w_budzecie", lambda p: 0)

    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert "wycofane" in str(blad.value).lower()

    polaczenie.commit()          # to zrobiloby kazde nastepne zapisanie
    assert polaczenie.execute(
        "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 0, \
        "wiersze przezyly wycofanie i zostaly zatwierdzone"
    polaczenie.close()


def test_udana_migracja_NIE_wycofuje_niczego():
    """Kontrola dwustronna: wycofanie ma dotykac wylacznie sciezki bledu."""
    polaczenie = magazyn.zmigruj_i_polacz()
    polaczenie.execute("CREATE TABLE wydatki_osobiste "
                       "(data DATE, kategoria TEXT, kwota NUMERIC(14,2))")
    polaczenie.execute("INSERT INTO wydatki_osobiste VALUES "
                       "('2026-08-01', 'Zakupy', 99.00)")
    polaczenie.commit()

    raport = magazyn.wchlon_wydatki_osobiste(polaczenie)
    assert raport.przeniesione == 1
    polaczenie.close()

    ponownie = pomocnicze.polaczenie_surowe()
    try:
        assert ponownie.execute(
            "SELECT COUNT(*) FROM wpisy_budzetu").fetchone()[0] == 1
    finally:
        ponownie.close()

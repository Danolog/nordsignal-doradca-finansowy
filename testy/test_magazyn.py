"""Straznicy magazynu.

Najwazniejszy z nich to straznik PKWiU: bez tej kolumny ewidencja nie pozwala
przypisac przychodu do rodzaju dzialalnosci, a to jest USTAWOWY warunek
stosowania roznych stawek (art. 12 ust. 3 ustawy o ryczalcie).
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from silnik.rdzen import budzet, magazyn

KATALOG = Path(__file__).parent.parent


@pytest.fixture
def p(tmp_path):
    return magazyn.polacz(tmp_path / "test.db")


def _faktura(polaczenie, **nadpisania):
    dane = dict(
        data=date(2026, 9, 30), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25",
    )
    dane.update(nadpisania)
    return magazyn.zapisz_fakture(polaczenie, **dane)


# --- stan poczatkowy ------------------------------------------------------

def test_brak_pliku_bazy_to_stan_poczatkowy_nie_awaria(tmp_path):
    polaczenie = magazyn.polacz(tmp_path / "jeszcze_nie_istnieje.db")
    assert magazyn.wczytaj_faktury(polaczenie).empty
    assert magazyn.wczytaj_godziny(polaczenie).empty


#: Komplet tabel, ktore ma zalozyc `magazyn.polacz`. JEDEN NOSNIK — do
#: 2026-08-25 ten sam zbior stal przepisany takze w `test_magazyn_budzet.py`
#: i przy dolozeniu tabeli `koszty_jdg` trzeba bylo poprawiac oba miejsca.
#: Druga kopia poprawiona z opoznieniem swieci na zielono i nie pilnuje niczego.
TABELE_SCHEMATU = {
    "przychody_jdg", "zobowiazania", "majatek", "godziny", "wpisy_budzetu",
    "plan_budzetu", "kategorie", "cele_oszczednosciowe", "ustawienia",
    "koszty_jdg",
    # Z57: forma opodatkowania per rok. Osobna tabela, a nie klucz
    # w `ustawienia`, bo tamta NIE MA wymiaru roku — a forma zmienia sie
    # rocznie i zmiana na 2027 nie ma prawa ruszyc rozliczenia 2026.
    "forma_opodatkowania",
    # Z60: kotwica prognozy. Tabela z HISTORIA, a nie klucz w `ustawienia`,
    # bo nadpisany klucz nie odpowie na pytanie „jaka byla kotwica, kiedy
    # prognoza to mowila" — a bez tej odpowiedzi prognoza nigdy nie udowodni,
    # ze jest skalibrowana.
    "stan_konta",
    # Z71: wynik przebiegu straznika w tle. Tabela w BAZIE, a nie plik obok
    # aplikacji, bo plik nie podaza za `AI_CFO_BAZA` — przebieg na kopii
    # roboczej nadpisalby wynik dotyczacy bazy produkcyjnej i pasek mowilby
    # o cudzych danych. Tabela znika razem z baza, ktora opisuje.
    "przebiegi_straznika",
}


def test_zbior_tabel_jest_dokladnie_taki_jak_w_schemacie(p):
    """Kontrola licznosci: sprawdzenie, do ktorego nic nie dociera, melduje sukces.

    Asercja przez ROWNOSC, nie przez zawieranie - dzieki temu ten sam test
    pilnuje takze, ze `wydatki_osobiste` NIE wraca po wchlonieciu (Zadanie 15).

    W nazwie testu nie ma liczby celowo: liczba w nazwie obok listy, ktora ja
    niesie, rozjezdza sie przy pierwszej zmianie i nikt tego nie zauwaza.
    """
    # sqlite_sequence to tabela wewnetrzna SQLite, tworzona przez AUTOINCREMENT -
    # nie nasza, wiec ja pomijamy.
    tabele = {w[0] for w in p.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'").fetchall()}
    assert tabele == TABELE_SCHEMATU


# --- straznik PKWiU -------------------------------------------------------

def test_faktura_bez_pkwiu_nie_przechodzi_zapisu(p):
    """Art. 12 ust. 3: bez PKWiU to nie jest ewidencja w rozumieniu przepisu."""
    with pytest.raises(magazyn.BladMagazynu, match="PKWiU"):
        _faktura(p, pkwiu="")
    with pytest.raises(magazyn.BladMagazynu, match="PKWiU"):
        _faktura(p, pkwiu="   ")


def test_faktura_z_pkwiu_przechodzi(p):
    """Kontrola dwustronna: straznik ma czerwienic na bledzie, a nie na wszystkim."""
    assert _faktura(p) > 0
    assert len(magazyn.wczytaj_faktury(p)) == 1


def test_godzina_bez_pkwiu_nie_przechodzi_zapisu(p):
    with pytest.raises(magazyn.BladMagazynu, match="PKWiU"):
        magazyn.zapisz_godziny(p, data=date(2026, 9, 1), rodzaj_czynnosci="sprzedaz",
                               pkwiu="", liczba_godzin=Decimal("8"), opis="")


# --- rozroznianie faktur --------------------------------------------------

def test_dwie_faktury_tego_samego_dnia_rozrozniane_numerem(p):
    _faktura(p, numer_faktury="FV/1/2026")
    _faktura(p, numer_faktury="FV/2/2026")
    df = magazyn.wczytaj_faktury(p)
    assert len(df) == 2
    assert set(df["numer_faktury"]) == {"FV/1/2026", "FV/2/2026"}


def test_duplikat_numeru_faktury_odrzucony(p):
    _faktura(p, numer_faktury="FV/1/2026")
    with pytest.raises(magazyn.BladMagazynu, match="numer"):
        _faktura(p, numer_faktury="FV/1/2026")


# --- Decimal przezywa podroz do bazy i z powrotem -------------------------

def test_kwoty_wracaja_jako_decimal_bez_straty_grosza(p):
    _faktura(p, kwota_netto=Decimal("11200.33"))
    wartosc = magazyn.wczytaj_faktury(p).iloc[0]["kwota_netto"]
    assert isinstance(wartosc, Decimal)
    assert wartosc == Decimal("11200.33")


# --- skladki raz w miesiacu ----------------------------------------------

def test_czy_skladki_naliczone_w_miesiacu(p):
    assert magazyn.czy_skladki_naliczone_w_miesiacu(p, 2026, 9) is False
    _faktura(p, data=date(2026, 9, 30), zaplacony_zus=Decimal("2425.11"))
    assert magazyn.czy_skladki_naliczone_w_miesiacu(p, 2026, 9) is True
    assert magazyn.czy_skladki_naliczone_w_miesiacu(p, 2026, 10) is False


def test_faktura_z_zerowym_zus_nie_oznacza_miesiaca_jako_naliczonego(p):
    """Druga faktura w miesiacu ma zaplacony_zus = 0 - nie moze ustawiac flagi."""
    _faktura(p, numer_faktury="FV/2/2026", zaplacony_zus=Decimal("0.00"))
    assert magazyn.czy_skladki_naliczone_w_miesiacu(p, 2026, 9) is False


# --- przychod narastajaco -------------------------------------------------

def test_przychod_narastajaco_sumuje_rok_do_daty(p):
    _faktura(p, numer_faktury="FV/1", data=date(2026, 9, 30))
    _faktura(p, numer_faktury="FV/2", data=date(2026, 10, 31))
    _faktura(p, numer_faktury="FV/3", data=date(2027, 1, 31))
    assert magazyn.przychod_narastajaco(p, 2026) == Decimal("22400.00")
    assert magazyn.przychod_narastajaco(p, 2027) == Decimal("11200.00")


# --- pozostale tabele -----------------------------------------------------

def test_wydatki_zobowiazania_majatek(p):
    # Kategoria pochodzi ze slownika zasianego przy tworzeniu bazy (Zadanie 15).
    # Wczesniej bylo tu "mieszkanie" - nazwa spoza slownika, ktora po
    # wprowadzeniu walidacji kategorii przestala byc dopuszczalna.
    magazyn.zapisz_wpis(p, data=date(2026, 9, 5), typ=budzet.TYP_WYDATKI,
                        kategoria="Kredyty", kwota=Decimal("2400.00"))
    magazyn.zapisz_zobowiazanie(p, nazwa="kredyt hipoteczny",
                                kapital=Decimal("320000.00"),
                                rata_minimalna=Decimal("2180.00"))
    magazyn.zapisz_aktywo(p, nazwa_aktywa="konto oszczednosciowe",
                          kategoria="poduszka", wartosc=Decimal("18000.00"))
    assert len(magazyn.wczytaj_wpisy(p, typ=budzet.TYP_WYDATKI)) == 1
    assert len(magazyn.wczytaj_zobowiazania(p)) == 1
    assert magazyn.wczytaj_majatek(p).iloc[0]["wartosc"] == Decimal("18000.00")


# --- higiena --------------------------------------------------------------

def test_baza_jest_w_gitignore():
    """Ograniczenie globalne 6. Repo jest prywatne (zmierzone), ale to nie powod,
    zeby realne finanse trafialy do historii gita."""
    assert "cfo_database.db" in (KATALOG / ".gitignore").read_text(encoding="utf-8")


def test_blad_daje_komunikat_po_polsku_nie_slad_wyjatku(p):
    with pytest.raises(magazyn.BladMagazynu) as e:
        _faktura(p, pkwiu="")
    tresc = str(e.value)
    assert "PKWiU" in tresc
    assert "Traceback" not in tresc
    assert any(slowo in tresc.lower() for slowo in ("wymagane", "puste", "brak"))

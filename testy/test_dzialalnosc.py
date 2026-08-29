"""Strazniki daty rozpoczecia dzialalnosci jako ustawienia (Z54).

Powod istnienia: do Z55 rezerwa ZUS naliczala sie PER FAKTURA — miesiac bez
zlecenia nie naliczal skladki. Przy trzech miesiacach i dwoch fakturach dawalo
to 4 850,22 zl zamiast 7 275,33 zl. Zeby liczyc per miesiac, aplikacja musi
najpierw WIEDZIEC, od kiedy dzialalnosc trwa — a tej informacji nie mialaby
skad wziac.

Brak wpisu daje stan „nie wiem", nigdy zero. Zero znaczyloby „zero miesiecy
dzialalnosci", czyli rezerwe ZUS rowna zeru — najlepszy mozliwy stan pokazany
przy braku wiedzy. To ta sama regula co D11 („brak planu to napis, nie zero").
"""

from datetime import date

import pytest

from silnik.rdzen import magazyn, podatki, prezentacja


@pytest.fixture
def p(tmp_path):
    return magazyn.zmigruj_i_polacz()


# --- ustawienie: zapis i odczyt ------------------------------------------

def test_brak_wpisu_to_NIE_WIEM_a_nie_zero(p):
    assert magazyn.odczytaj_dzialalnosc_od(p) is None


def test_zapisana_data_WRACA_jako_data(p):
    magazyn.zapisz_dzialalnosc_od(p, date(2026, 9, 1))
    assert magazyn.odczytaj_dzialalnosc_od(p) == date(2026, 9, 1)


def test_data_PRZEZYWA_ponowne_otwarcie_bazy(tmp_path):
    """Ustawienie ma mieszkac w bazie, nie w pamieci procesu."""
    sciezka = tmp_path / "trwalosc.db"
    pierwsze = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_dzialalnosc_od(pierwsze, date(2026, 9, 1))
    pierwsze.close()
    drugie = magazyn.zmigruj_i_polacz()
    assert magazyn.odczytaj_dzialalnosc_od(drugie) == date(2026, 9, 1)
    drugie.close()


def test_wpis_USZKODZONY_jest_bledem_a_nie_cichym_brakiem(p):
    """Cisza przy uszkodzonym wpisie zamienilaby „mam zla date" w „nie wiem",
    a rezerwa milczalaby zamiast krzyczec."""
    magazyn.ustaw_ustawienie(p, magazyn.KLUCZ_DZIALALNOSC_OD, "wrzesien")
    with pytest.raises(magazyn.BladMagazynu) as blad:
        magazyn.odczytaj_dzialalnosc_od(p)
    assert "wrzesien" in str(blad.value)


# --- liczba miesiecy dzialalnosci ----------------------------------------

def test_wrzesien_do_grudnia_to_CZTERY_miesiace():
    """Kryterium odbioru planu Z54."""
    assert podatki.miesiace_dzialalnosci(date(2026, 9, 1), date(2026, 12, 4)) == 4


def test_jeden_miesiac_to_JEDEN_a_nie_zero():
    """Kryterium odbioru planu Z54. Roznica dat to 29 dni — liczymy MIESIACE
    kalendarzowe, bo skladka nalezy sie za miesiac, nie za jego dlugosc."""
    assert podatki.miesiace_dzialalnosci(date(2026, 9, 1), date(2026, 9, 30)) == 1


def test_miesiac_PRZED_startem_nie_wchodzi_do_liczby():
    """Kontrola dwustronna wymagana przez plan: liczba ma rosnac wylacznie
    od daty startu."""
    assert podatki.miesiace_dzialalnosci(date(2026, 9, 1), date(2026, 11, 30)) == 3
    assert podatki.miesiace_dzialalnosci(date(2026, 8, 1), date(2026, 11, 30)) == 4


def test_przelom_roku_liczy_sie_poprawnie():
    assert podatki.miesiace_dzialalnosci(date(2026, 11, 1), date(2027, 2, 28)) == 4


def test_start_w_srodku_miesiaca_liczy_CALY_ten_miesiac():
    """Zalozenie nazwane: skladka nalezy sie za miesiac rozpoczety, nie za
    jego czesc. Wariant ostrozniejszy — zaniza rezerwe tylko wtedy, gdy
    ustawa mowi inaczej, a nie odwrotnie."""
    assert podatki.miesiace_dzialalnosci(date(2026, 9, 15), date(2026, 9, 20)) == 1


def test_ODWROCONE_daty_sa_bledem_z_trescia():
    """Kryterium odbioru planu Z54. Cicha ujemna liczba miesiecy dalaby
    rezerwe ujemna, czyli wyglad nadplaty."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        podatki.miesiace_dzialalnosci(date(2026, 12, 1), date(2026, 9, 1))
    assert "2026-12-01" in str(blad.value)
    assert "2026-09-01" in str(blad.value)


def test_ten_sam_dzien_to_JEDEN_miesiac():
    """Kontrola dwustronna do testu wyzej: granica ma odcinac odwrocenie,
    nie rownosc."""
    assert podatki.miesiace_dzialalnosci(date(2026, 9, 1), date(2026, 9, 1)) == 1


# --- co widzi uzytkownik --------------------------------------------------

def test_podpis_dzialalnosci_przy_BRAKU_mowi_czego_brak():
    podpis = prezentacja.podpis_dzialalnosci(None)
    assert "nie" in podpis.lower()
    assert "0" not in podpis, "zero wyglada jak zerowa rezerwa ZUS"


def test_podpis_dzialalnosci_z_data_NAZYWA_miesiac_po_polsku():
    podpis = prezentacja.podpis_dzialalnosci(date(2026, 9, 1))
    assert "wrześni" in podpis.lower()
    assert "2026" in podpis

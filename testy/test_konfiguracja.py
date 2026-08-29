"""Strazniki wczytywania konfiguracji lokalnej z pliku `.env`.

Geneza, 2026-08-25: klucz do Gemini API dzialal w powloce, ale aplikacja
uruchomiona ikona z Findera go NIE WIDZIALA. Aplikacja graficzna na macOS
dostaje srodowisko od launchd, nie z `~/.zshrc` - a w sesji graficznej
zmienna byla obecna, lecz PUSTA (dlugosc 0). Doradca meldowal "brak klucza"
i mial racje.

Wniosek konstrukcyjny: aplikacja ma czytac wlasna konfiguracje z pliku obok
siebie, a nie liczyc na srodowisko procesu, ktory ja uruchomil. Plik `.env`
lezy w katalogu projektu, jest w `.gitignore` i przezywa restart systemu -
w przeciwienstwie do `launchctl setenv`.
"""

import os
from pathlib import Path

import pytest

from silnik.rdzen import konfiguracja


@pytest.fixture
def czyste_srodowisko():
    """Przywraca srodowisko po tescie - inaczej testy zatruwaja sie nawzajem."""
    kopia = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(kopia)


def test_wczytuje_zmienne_z_pliku(tmp_path, czyste_srodowisko):
    plik = tmp_path / ".env"
    plik.write_text("AI_CFO_TEST_A=alfa\nAI_CFO_TEST_B=beta\n")
    os.environ.pop("AI_CFO_TEST_A", None)
    os.environ.pop("AI_CFO_TEST_B", None)

    wczytane = konfiguracja.wczytaj_lokalna(plik)

    assert os.environ["AI_CFO_TEST_A"] == "alfa"
    assert os.environ["AI_CFO_TEST_B"] == "beta"
    # Kontrola licznosci: funkcja zwraca, ILE zmiennych wniosla. Zero przy
    # istniejacym pliku znaczy, ze plik jest w formacie, ktorego nie rozumie -
    # a to wyglada identycznie jak brak pliku.
    assert wczytane == 2


def test_srodowisko_procesu_WYGRYWA_z_plikiem(tmp_path, czyste_srodowisko):
    """Zmienna podana przy uruchomieniu ma byc silniejsza niz plik.

    Inaczej nie da sie jednorazowo uruchomic aplikacji z innym kluczem, nie
    ruszajac pliku - a to jest najzwyklejszy sposob sprawdzenia drugiego klucza.
    """
    plik = tmp_path / ".env"
    plik.write_text("AI_CFO_TEST_A=z_pliku\n")
    os.environ["AI_CFO_TEST_A"] = "ze_srodowiska"

    konfiguracja.wczytaj_lokalna(plik)

    assert os.environ["AI_CFO_TEST_A"] == "ze_srodowiska"


def test_pusta_zmienna_srodowiskowa_NIE_blokuje_pliku(tmp_path, czyste_srodowisko):
    """To jest dokladnie przypadek, ktory zepsul doradce.

    `launchctl setenv` zostawil GEMINI_API_KEY o dlugosci ZERO. Zmienna
    istniala, wiec zwykle "nie nadpisuj, jesli juz jest" zostawiloby pustke
    i plik nigdy by nie zadzialal. Pusta wartosc to brak wartosci.
    """
    plik = tmp_path / ".env"
    plik.write_text("AI_CFO_TEST_A=z_pliku\n")
    os.environ["AI_CFO_TEST_A"] = ""

    konfiguracja.wczytaj_lokalna(plik)

    assert os.environ["AI_CFO_TEST_A"] == "z_pliku"


def test_brak_pliku_to_normalny_stan_nie_awaria(tmp_path, czyste_srodowisko):
    assert konfiguracja.wczytaj_lokalna(tmp_path / "czegos-takiego-nie-ma") == 0


def test_komentarze_i_puste_linie_pomijane(tmp_path, czyste_srodowisko):
    plik = tmp_path / ".env"
    plik.write_text("# komentarz\n\nAI_CFO_TEST_A=alfa\n   \n# jeszcze jeden\n")
    os.environ.pop("AI_CFO_TEST_A", None)
    assert konfiguracja.wczytaj_lokalna(plik) == 1
    assert os.environ["AI_CFO_TEST_A"] == "alfa"


def test_cudzyslowy_wokol_wartosci_zdejmowane(tmp_path, czyste_srodowisko):
    """Klucze API wkleja sie czesto w cudzyslowach. Wartosc z cudzyslowem
    w srodku jest innym kluczem niz ten, ktory uzytkownik skopiowal."""
    plik = tmp_path / ".env"
    plik.write_text('AI_CFO_TEST_A="alfa"\nAI_CFO_TEST_B=\'beta\'\n')
    for nazwa in ("AI_CFO_TEST_A", "AI_CFO_TEST_B"):
        os.environ.pop(nazwa, None)
    konfiguracja.wczytaj_lokalna(plik)
    assert os.environ["AI_CFO_TEST_A"] == "alfa"
    assert os.environ["AI_CFO_TEST_B"] == "beta"


def test_linia_bez_znaku_rownosci_pomijana_bez_wywracania(tmp_path,
                                                         czyste_srodowisko):
    plik = tmp_path / ".env"
    plik.write_text("to nie jest przypisanie\nAI_CFO_TEST_A=alfa\n")
    os.environ.pop("AI_CFO_TEST_A", None)
    assert konfiguracja.wczytaj_lokalna(plik) == 1


def test_domyslna_sciezka_wskazuje_katalog_projektu():
    """Pakiet .app uruchomiony z Findera startuje w katalogu /, ale skrypt
    startowy robi `cd` do projektu. Sciezka i tak jest liczona od polozenia
    modulu, nie od katalogu roboczego - zeby nie zalezec od tego `cd`.
    """
    assert konfiguracja.SCIEZKA_DOMYSLNA.name == ".env"
    assert konfiguracja.SCIEZKA_DOMYSLNA.parent == Path(__file__).parent.parent


def test_wartosc_klucza_nigdy_nie_trafia_do_komunikatu(tmp_path,
                                                       czyste_srodowisko):
    """Raport z wczytania podaje LICZBE i NAZWY, nigdy wartosci.

    Komunikat startowy trafia do logu, a log bywa wklejany w zgloszeniach.
    """
    plik = tmp_path / ".env"
    plik.write_text("AI_CFO_TEST_SEKRET=wartosc-ktorej-nie-wolno-pokazac\n")
    os.environ.pop("AI_CFO_TEST_SEKRET", None)
    konfiguracja.wczytaj_lokalna(plik)
    opis = konfiguracja.opis_wczytania(plik)
    assert "AI_CFO_TEST_SEKRET" in opis
    assert "wartosc-ktorej-nie-wolno-pokazac" not in opis

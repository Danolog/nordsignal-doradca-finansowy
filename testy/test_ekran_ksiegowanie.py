# -*- coding: utf-8 -*-
"""Strażnik ZAKRESU ekranu Księgowanie.

Wyglądu pilnuje porównanie zrzutów (`interfejs/narzedzia/porownaj-z-makieta.mjs`),
a nie ten plik. Tutaj sprawdzamy rzeczy, których obraz nie widzi: czy każda
fraza z ramki w ogóle jest w źródle, czy kwota nie została wpisana w komponent
i czy z ekranu nie da się zapisać kosztu firmowego.
"""
import pathlib
import re

from pomocnicze import bez_komentarzy as _bez_komentarzy

KATALOG = pathlib.Path(__file__).resolve().parent.parent

FRAZY_Z_RAMKI = (
    "Bez znaku — minus jest w typie wpisu",
    "Zapisz wpis", "Co ruszy ten wpis", "Ostatnie wpisy",
    "Czego tu nie ma", "Wolne środki", "bez zmian", "Szczegóły",
)

# Siedem stanów błędu z §41.5 specyfikacji. Komunikat „błąd" dla siedmiu
# przyczyn jest tym samym co brak komunikatu, więc każdy ma własne brzmienie.
SIEDEM_BRZMIEN = (
    "Nieczytelna data.",                 # (a)
    "Podaj kwotę.",                      # (b)
    "Nieczytelna kwota.",                # (c)
    "Minus jest już w typie wpisu.",     # (d) — pytanie, nie błąd
    "Wybierz kategorię.",                # (e)
    "jest nieaktywna",                   # (f)
    "Nieznany typ wpisu.",               # (g) — niemożliwy z konstrukcji
)

EKRAN = KATALOG / "interfejs" / "app" / "ksiegowanie" / "page.tsx"
NAPISY = KATALOG / "interfejs" / "lib" / "napisy.ts"
DANE = KATALOG / "interfejs" / "lib" / "dane" / "ksiegowanie.ts"


def _tekst_ekranu() -> str:
    zrodla = [EKRAN, NAPISY, DANE]
    obecne = [p for p in zrodla if p.exists()]
    # Kontrola liczności: sprawdzenie, do którego nic nie dociera, melduje
    # sukces. Bez tej asercji przemianowanie pliku dałoby zielone testy.
    assert len(obecne) == len(zrodla), f"brak plików ekranu: {set(zrodla) - set(obecne)}"
    return "\n".join(_bez_komentarzy(p.read_text(encoding="utf-8")) for p in obecne)


def test_kazda_fraza_z_ramki_JEST_na_ekranie():
    brakujace = [f for f in FRAZY_Z_RAMKI if f not in _tekst_ekranu()]
    assert brakujace == [], f"frazy z ramki, których nie ma na ekranie: {brakujace}"


def test_siedem_brzmien_bledu_MA_JEDEN_nosnik():
    """Wszystkie siedem stoi w `lib/napisy.ts` i ANI JEDNO w komponencie."""
    napisy = NAPISY.read_text(encoding="utf-8")
    ekran = EKRAN.read_text(encoding="utf-8")
    brak = [b for b in SIEDEM_BRZMIEN if b not in napisy]
    assert brak == [], f"brzmienia poza nośnikiem `napisy.ts`: {brak}"
    wpisane_w_ekran = [b for b in SIEDEM_BRZMIEN if b in ekran]
    assert wpisane_w_ekran == [], f"brzmienia wpisane w komponent: {wpisane_w_ekran}"


def test_podpis_bez_znaku_i_pytanie_o_minus_MOWIA_TO_SAMO():
    """Świadomy drugi nośnik (Z-19a): podpis stojący zawsze i pytanie po
    wpisaniu minusa niosą tę samą regułę dwoma zdaniami. Próg konsolidacji:
    przy pierwszej zmianie któregokolwiek z tych zdań — wtedy oba wychodzą
    z `silnik/prezentacja.py`. Do tego czasu pilnuje ich ten strażnik."""
    napisy = NAPISY.read_text(encoding="utf-8")
    for zdanie in ("Bez znaku — minus jest w typie wpisu.", "Minus jest już w typie wpisu."):
        assert zdanie in napisy, f"brak zdania: {zdanie}"
        assert "w typie wpisu" in zdanie


def test_ekran_NIE_MA_wpisanej_recznie_kwoty():
    """Kwota w komponencie to drugi nośnik danych."""
    kod = EKRAN.read_text(encoding="utf-8")
    assert re.findall(r"\d+[,.]\d{2}\s*zł", kod) == []


def test_ekran_NIE_ZAMIENIA_kwoty_na_liczbe():
    """§3.1: liczba zmiennoprzecinkowa w ścieżce kwoty gubi grosze. Poprzednia
    aplikacja robiła to w warstwie sieciowej i zwracała 200."""
    for plik in (EKRAN, KATALOG / "interfejs" / "lib" / "kwota.ts"):
        kod = plik.read_text(encoding="utf-8")
        bez_komentarzy = _bez_komentarzy(kod)
        assert "parseFloat" not in bez_komentarzy, f"parseFloat w {plik.name}"
        assert "parseInt" not in bez_komentarzy, f"parseInt w {plik.name}"


def test_kategoria_Firmowe_NIE_JEST_na_tym_ekranie():
    """D-24: koszty firmowe mają jedno miejsce — ekran Firma."""
    dane = DANE.read_text(encoding="utf-8")
    assert "Firmowe" not in dane


def test_pasmo_ma_PIETNASCIE_kategorii_w_kolejnosci_z_ramki():
    """Kontrola liczności: pomiar, do którego dociera pusta lista, melduje
    sukces. Trzy pierwsze to pozycje planu na październik, dalej alfabetycznie."""
    dane = DANE.read_text(encoding="utf-8")
    nazwy = re.findall(r'kategoria\("([^"]+)"\)', dane)
    assert len(nazwy) == 15, f"kategorii jest {len(nazwy)}, ma być 15: {nazwy}"
    assert nazwy[:3] == ["Czesne", "Energia Elektryczna", "Kredyty"], nazwy[:3]
    assert nazwy[3:] == sorted(nazwy[3:]), f"ogon nie jest alfabetyczny: {nazwy[3:]}"


def test_kursor_STOI_w_polu_kwoty_po_wejsciu():
    """To `autoFocus` zdejmuje jedno z trzech kliknięć do zapisu (§41.1).
    Bez niego bramka „trzy kliknięcia" przestaje być spełniona."""
    kod = _bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "autoFocus" in kod


def test_ekran_NIE_MOWI_o_formie_opodatkowania():
    """Darek jest na skali podatkowej. Ryczałt jest wadą, nie opcją domyślną —
    a ten ekran nie ma prawa wyprowadzać czegokolwiek z formy opodatkowania."""
    tekst = _tekst_ekranu()
    for slowo in ("ryczałt", "Ryczałt", "ryczalt", "skala podatkowa", "liniowy"):
        assert slowo not in tekst, f"forma opodatkowania na ekranie wpisu: {slowo}"

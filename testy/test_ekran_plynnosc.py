# -*- coding: utf-8 -*-
"""Strażnik ZAKRESU ekranu Płynność — pierwszego, który Darek otwiera.

Wyglądu pilnuje porównanie zrzutów, a geometrii wykresu `testy/wykres.test.ts`
(porównanie znak po znaku z atrybutem `d` z ramki). Tutaj stoi to, czego obraz
nie widzi: czy każda fraza z ramki jest w źródle, czy nie dołożono rzeczy
jawnie wykluczonych i czy liczby nie wjechały do komponentu.
"""
import pathlib
import re

from pomocnicze import bez_komentarzy

KATALOG = pathlib.Path(__file__).resolve().parent.parent

EKRAN = KATALOG / "interfejs" / "app" / "page.tsx"
NAPISY = KATALOG / "interfejs" / "lib" / "napisy.ts"
DANE = KATALOG / "interfejs" / "lib" / "dane" / "plynnosc.ts"
WYKRES = KATALOG / "interfejs" / "lib" / "wykres.ts"
STYL = KATALOG / "interfejs" / "app" / "style.module.css"

FRAZY_Z_RAMKI = (
    "Najniżej",              # etykieta wielkiej liczby
    "Co mnie czeka",         # jedyne wezwanie na ekranie
    "Stan na dziś",          # kotwica wewnątrz prognozy
    "Ostatnie sprawdzenie",  # stopka strażnika
    "Księga płynności",
    "Saldo po tym dniu",
    "pod kreską",
    "Masz ",
)


def _zrodla() -> list[pathlib.Path]:
    return [EKRAN, NAPISY, DANE, WYKRES, STYL]


def _tekst_ekranu() -> str:
    obecne = [p for p in _zrodla() if p.exists()]
    # Kontrola liczności: sprawdzenie, do którego nic nie dociera, melduje
    # sukces. Bez tej asercji przemianowanie pliku dałoby zielone testy.
    assert len(obecne) == len(_zrodla()), f"brak plików ekranu: {set(_zrodla()) - set(obecne)}"
    return "\n".join(bez_komentarzy(p.read_text(encoding="utf-8")) for p in obecne)


def test_kazda_fraza_z_ramki_JEST_na_ekranie():
    brakujace = [f for f in FRAZY_Z_RAMKI if f not in _tekst_ekranu()]
    assert brakujace == [], f"frazy z ramki, których nie ma na ekranie: {brakujace}"


def test_etykieta_NAJNIZEJ_stoi_przy_wielkiej_liczbie():
    """Bez niej wielka liczba stoi w wierszu VAT-u i czyta się jako kwota
    VAT-u. To jest zmiana ZNACZENIA ekranu, nie jego wyglądu, więc obraz jej
    nie złapie — bramka odwzorowania widziałaby tylko „mniej pikseli"."""
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    # Trafiamy w TEN KLUCZ, nie w plik. Zmierzone (przebieg Z2, mutacja P1):
    # sprawdzenie „słowo »Najniżej« jest gdzieś w nośniku" przechodziło mimo
    # podmiany właśnie tego brzmienia, bo słowo stało jeszcze przy drugim,
    # nieużywanym kluczu. Drugi klucz skasowany, sprawdzenie zawężone.
    klucz = re.search(r"najnizej:\s*\([^)]*\)\s*=>\s*`([^`]*)`", napisy)
    assert klucz, "nie znalazłem brzmienia etykiety wielkiej liczby w nośniku"
    assert "Najniżej" in klucz.group(1), (
        f"etykieta wielkiej liczby brzmi teraz: {klucz.group(1)!r}. "
        "Bez slowa Najnizej liczba stoi w wierszu VAT-u i czyta sie jako kwota VAT-u."
    )
    assert "NAPISY_PLYNNOSCI.najnizej(" in ekran, "ekran nie woła etykiety wielkiej liczby"


def test_ekran_NIE_MA_wpisanej_recznie_kwoty():
    """Kwota w komponencie to drugi nośnik danych."""
    kod = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert re.findall(r"\d+[,.]\d{2}\s*zł", kod) == []


def test_kwota_STAJE_SIE_liczba_tylko_w_module_wykresu():
    """§3.1: liczba zmiennoprzecinkowa w ścieżce kwoty gubi grosze. Rysunek
    wymaga współrzędnych, więc gdzieś kwota musi przestać być napisem — ale
    dokładnie w JEDNYM miejscu, i tym miejscem jest `lib/wykres.ts`,
    z którego wychodzą wyłącznie piksele."""
    for plik in (EKRAN, DANE, KATALOG / "interfejs" / "lib" / "kwota.ts"):
        kod = bez_komentarzy(plik.read_text(encoding="utf-8"))
        for zakazane in ("parseFloat", "parseInt", "Number(p.saldo", "Number(kwota"):
            assert zakazane not in kod, f"{zakazane} w {plik.name}"


def test_ekran_NIE_KLAMIE_o_ratach_spoza_planu():
    """Zdanie „Prognoza ich NIE dolicza" mówi nieprawdę: prognoza te raty
    odejmuje, tylko drugą drogą, jako pozycje planu. Kontrola Leo, §4.2."""
    assert "NIE dolicza" not in _tekst_ekranu()


def test_ekran_NIE_MA_kafelkow_z_innego_pytania():
    """Przychody / wydatki / oszczędności odpowiadają na inne pytanie i mają
    inny ekran. Jeden ekran na jedno pytanie."""
    tekst = _tekst_ekranu()
    for slowo in ("Przychody", "Oszczędności", "Poduszka", "Cele oszczędnościowe"):
        assert slowo not in tekst, f"kafelek z innego pytania: {slowo}"


def test_werdykt_NIE_DOSTAJE_ikony():
    """Werdykt niosą już słowo, barwa i pozycja. Ikona byłaby trzecim
    nośnikiem tej samej rzeczy, czyli szumem."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    blok = ekran[ekran.index("s.werdykt") : ekran.index("s.wierszWezwania")]
    assert "svg" not in blok.lower(), "ikona w bloku werdyktu"


def test_prognoza_JEST_kreska_przerywana():
    """Linia ciągła twierdziłaby wiedzę; to jest przewidywanie. Różnicę
    niesie kształt kreski, nie barwa (bramka: barwa nie jest jedynym
    nośnikiem znaczenia)."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert ekran.count("strokeDasharray") >= 2, "prognoza albo odcinek pod kreską są ciągłe"


def test_saldo_bite_RAZ_NA_DZIEN():
    """Silnik podaje saldo per pozycja, więc dwie pozycje z jednego dnia
    dostają tę samą wartość — powtórzona wygląda jak błąd rachunku."""
    dane = DANE.read_text(encoding="utf-8")
    ksiega = dane[dane.index("const KSIEGA"): dane.index("function serie")]
    # Wzorzec przechodzi przez znaki nowego wiersza, bo pierwszy wpis księgi
    # jest rozbity na kilka linii. Zmierzone (przebieg Z2, mutacja P3):
    # wzorzec liniowy widział PIĘĆ wierszy z sześciu i nie zauważył, że saldo
    # przeniosło się na niewłaściwą pozycję dnia.
    wiersze = re.findall(
        r'dzien: "(\d{4}-\d{2}-\d{2})".*?saldoPoDniu: ("[^"]*"|null)', ksiega, flags=re.S
    )
    # Kontrola liczności: sprawdzenie, do którego dociera pusty zbiór, melduje
    # sukces. Wierszy ma być tyle, ile jest pól `dzien:`.
    assert len(wiersze) == ksiega.count("dzien:") == 6, (
        f"pomiar zobaczył {len(wiersze)} wierszy z {ksiega.count('dzien:')}"
    )
    kolejnosc = [d for d, _ in wiersze]
    for i, (dzien, saldo) in enumerate(wiersze):
        ostatni_w_dniu = i + 1 >= len(kolejnosc) or kolejnosc[i + 1] != dzien
        if not ostatni_w_dniu:
            assert saldo == "null", (
                f"saldo stoi przy pierwszej pozycji dnia {dzien}, a ma stać na końcu dnia — "
                "powtórzone albo przedwczesne saldo wygląda jak błąd rachunku"
            )
    ile_na_dzien: dict[str, int] = {}
    for dzien, saldo in wiersze:
        ile_na_dzien[dzien] = ile_na_dzien.get(dzien, 0) + (0 if saldo == "null" else 1)
    for dzien, ile in ile_na_dzien.items():
        assert ile <= 1, f"saldo bite {ile} razy w dniu {dzien}"


def test_kotwica_NIESIE_WIEK_odczytu():
    """Kotwica stoi wewnątrz prognozy, drobnym drukiem, z wiekiem odczytu.
    Osobna karta obok była wadą nazwaną na Z67."""
    dane = DANE.read_text(encoding="utf-8")
    assert "dopisek:" in dane
    assert "z odczytu" in dane and "września" in dane


def test_podwojna_linia_jest_ATRAMENTEM_nie_liniatura():
    """Podwójna kreska zamknięcia NIESIE znaczenie; liniatura wierszy jest
    dowiedzioną dekoracją (1,29:1). Gdyby wyglądały tak samo, oko wrzuciłoby
    niosącą do klasy ozdobnych."""
    css = bez_komentarzy(STYL.read_text(encoding="utf-8"))
    kreska = re.search(r"\.kreska\s*\{[^}]*\}", css)
    assert kreska, "brak klasy podwójnej linii"
    assert "--atrament-cichy" in kreska.group(0), "podwójna linia rysowana liniaturą"


def test_styl_NIE_MA_wpisanej_recznie_barwy():
    """Każda barwa idzie ze zmiennej. Wartość szesnastkowa to drugi nośnik
    palety — rozjazd o jeden ton łamie bramkę odwzorowania, a oba pliki
    nadal wyglądają na zadbane."""
    for plik in (STYL, KATALOG / "interfejs" / "app" / "ksiegowanie" / "style.module.css"):
        wpisane = re.findall(r"#[0-9A-Fa-f]{3,8}\b", plik.read_text(encoding="utf-8"))
        assert wpisane == [], f"barwy wpisane ręcznie w {plik.name}: {wpisane}"


def test_ekran_NIE_MOWI_o_formie_opodatkowania():
    """Darek jest na skali podatkowej. Ryczałt jest wadą, nie opcją domyślną."""
    tekst = _tekst_ekranu()
    for slowo in ("ryczałt", "Ryczałt", "ryczalt", "liniowy"):
        assert slowo not in tekst, f"forma opodatkowania na ekranie płynności: {slowo}"

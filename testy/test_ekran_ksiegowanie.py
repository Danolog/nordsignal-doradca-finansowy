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

# PO PODPIECIU (Z7) UKLAD MIESZKA W `formularz.tsx`, a `page.tsx` jest samym
# wejsciem: pobiera dane z trasy i oddaje je formularzowi. Straznik czyta OBA,
# bo inaczej mierzylby polowe ekranu i meldowal sukces.
EKRAN = KATALOG / "interfejs" / "app" / "ksiegowanie" / "formularz.tsx"
WEJSCIE = KATALOG / "interfejs" / "app" / "ksiegowanie" / "page.tsx"
NAPISY = KATALOG / "interfejs" / "lib" / "napisy.ts"
DANE = KATALOG / "interfejs" / "lib" / "dane" / "ksiegowanie.ts"
# Po podpieciu czesc frazy z ramki („Wolne środki", „bez zmian") przyszla
# z warstwy danych DO SILNIKA — bo to on sklada karte „Co ruszy ten wpis".
# Straznik idzie za frazą do jej nowego nosnika, zamiast obnizyc wymaganie.
SILNIK = KATALOG / "silnik" / "ekran_ksiegowanie.py"


def _pliki(zrodla: list) -> str:
    obecne = [p for p in zrodla if p.exists()]
    # Kontrola liczności: sprawdzenie, do którego nic nie dociera, melduje
    # sukces. Bez tej asercji przemianowanie pliku dałoby zielone testy.
    assert len(obecne) == len(zrodla), f"brak plików ekranu: {set(zrodla) - set(obecne)}"
    return "\n".join(_bez_komentarzy(p.read_text(encoding="utf-8")) for p in obecne)


def _tekst_ekranu() -> str:
    """Zrodla, w ktorych czegos NIE WOLNO znalezc — sam interfejs."""
    return _pliki([EKRAN, WEJSCIE, NAPISY, DANE])


def _tekst_z_silnikiem() -> str:
    """Zrodla, w ktorych fraza z ramki MOZE mieszkac — razem z silnikiem."""
    return _pliki([EKRAN, WEJSCIE, NAPISY, DANE, SILNIK])


def test_kazda_fraza_z_ramki_JEST_na_ekranie():
    brakujace = [f for f in FRAZY_Z_RAMKI if f not in _tekst_z_silnikiem()]
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


#: Kafelki pasma WYCIETE Z RAMKI, nie przepisane z pamięci. Ramka jest
#: wiążącą specyfikacją zakresu (CLAUDE.md §3.6), więc to ona mówi, ile
#: kategorii stoi w paśmie i w jakiej kolejności.
RAMKA = KATALOG / "makiety" / "Ksiegowanie.dc.html"


def _kafelki_z_ramki() -> list:
    tekst = RAMKA.read_text(encoding="utf-8")
    poczatek = tekst.index("Czesne")
    # Domknięcie znacznika po ostatnim kafelku MUSI wejść do wycinka —
    # wzorzec szuka tekstu MIĘDZY znacznikami, więc urwany na literze
    # „Zdrowie" gubi ostatnią pozycję i pomiar melduje 14 zamiast 15.
    koniec = tekst.index("Zdrowie") + len("Zdrowie") + 40
    fragment = tekst[poczatek - 400:koniec]
    nazwy = [w.strip() for w in re.findall(r">([^<>]{2,40})<", fragment)]
    return [n for n in nazwy if n]


#: JEDYNY ZNANY ROZJAZD ramki z regułą silnika, nazwany zamiast przemilczany.
#: Ramka stawia „PUWIS" zaraz po „Monika i Ada" — czyli tak, jakby sortowała
#: po surowych znakach, gdzie wielkie „U" (85) stoi przed małym „o" (111).
#: Silnik porównuje po polsku: bez ogonków i bez wielkości liter, więc
#: „podatki" < „praca" < „puwis" i PUWIS ląduje o dwa miejsca dalej.
#: Reguła silnika (`ekran_ksiegowanie._alfabetycznie`) jest tu POPRAWNA,
#: rysunek jest pomyłką ręki. ZGŁOSZONE — nie poprawiam ani ramki, ani silnika.
#: PRÓG: gdy Mila poprawi ramkę, obie liczby niżej się zrównają, a strażnik
#: zaczerwieni się sam i każe zdjąć ten wyjątek.
ROZJAZD_KAFELEK = "PUWIS"
ROZJAZD_MIEJSCE_W_RAMCE = 7
ROZJAZD_MIEJSCE_W_SILNIKU = 9


def test_pasmo_ma_PIETNASCIE_kategorii_w_kolejnosci_Z_REGULY_SILNIKA():
    """Po podpięciu (Z7) kolejność kafelków NIE STOI w źródle interfejsu —
    liczy ją `ekran_ksiegowanie.kolejnosc_kategorii` i przysyła gotową.
    Strażnik mierzy więc regułę wobec ramki, a nie stałą wobec stałej.

    Kontrola liczności stoi PRZED porównaniem: pomiar, do którego dociera
    pusta lista, melduje sukces."""
    import pandas as pd

    from silnik import ekran_ksiegowanie

    z_ramki = _kafelki_z_ramki()
    assert len(z_ramki) == 15, f"z ramki wyszło {len(z_ramki)} kafelków: {z_ramki}"

    # Wejście silnika w stanie z ramki: ani jednego wpisu, trzy pozycje planu
    # na październik 2026. Plan podajemy ramką danych, bo tego żąda reguła.
    plan = pd.DataFrame([
        {"rok": 2026, "miesiac": 10, "typ": "Wydatki", "kategoria": k,
         "opis": "", "kwota": "100.00", "powtarzalna": 0}
        for k in ("Czesne", "Energia Elektryczna", "Kredyty")
    ])
    wyliczona = list(ekran_ksiegowanie.kolejnosc_kategorii(
        z_ramki, wpisy=pd.DataFrame(), plan=plan, typ="Wydatki",
        rok=2026, miesiac=10))

    assert len(wyliczona) == 15, f"silnik oddał {len(wyliczona)} kafelków"
    assert set(wyliczona) == set(z_ramki), "silnik zgubił albo dołożył kategorię"
    assert wyliczona[:3] == ["Czesne", "Energia Elektryczna", "Kredyty"], wyliczona[:3]

    # Rozjazd to PRZESUNIĘCIE DOKŁADNIE JEDNEGO kafelka i tyle wolno mu być.
    # Sprawdzamy go wprost — obie pozycje z nazwy — a potem porównujemy resztę
    # ciągu bez niego. Pominięcie porównania „bo się różni" byłoby strażnikiem,
    # który przestaje strzec dokładnie tam, gdzie zaczyna być potrzebny.
    assert z_ramki.index(ROZJAZD_KAFELEK) == ROZJAZD_MIEJSCE_W_RAMCE, (
        f"ramka stawia {ROZJAZD_KAFELEK} na miejscu "
        f"{z_ramki.index(ROZJAZD_KAFELEK)}, a nie {ROZJAZD_MIEJSCE_W_RAMCE}")
    assert wyliczona.index(ROZJAZD_KAFELEK) == ROZJAZD_MIEJSCE_W_SILNIKU, (
        f"silnik stawia {ROZJAZD_KAFELEK} na miejscu "
        f"{wyliczona.index(ROZJAZD_KAFELEK)}, a nie {ROZJAZD_MIEJSCE_W_SILNIKU}")

    bez_rozjazdu = lambda lista: [n for n in lista if n != ROZJAZD_KAFELEK]
    assert bez_rozjazdu(wyliczona) == bez_rozjazdu(z_ramki), (
        f"kolejność silnika różni się od ramki poza znanym rozjazdem:\n"
        f"  silnik: {wyliczona}\n  ramka:  {z_ramki}")


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


# --- W8: ksztalt wpisanej kwoty ma JEDEN nosnik ---

def test_ksztalt_kwoty_MA_JEDEN_nosnik():
    """CLAUDE.md §3.2. Do W8 regula „co jest czytelna kwota" stala wylacznie
    w tym formularzu. W8 dolozylo drugie miejsce, w ktorym czlowiek wpisuje
    kwote — kontrolke stanu konta na ekranie Plynnosci — i kopia reguly
    rozjechalaby sie przy pierwszej zmianie: jeden ekran przyjmowalby „1 240,5",
    drugi nie, przy zielonej suicie po obu stronach.

    Nosnikiem jest `lib/kwota.ts`. Oba ekrany go WOLAJA. Co zostaje osobne:
    rozstrzygniecie, CO ZROBIC z kwota ujemna — tu jest pytaniem, tam zwyklym
    odczytem. To roznica dziedzinowa, nie druga kopia odczytu.

    Kontrola liczności: sprawdzamy oba wolania, nie jedno. Straznik mierzacy
    tylko formularz przeszedlby przy kontrolce z wlasna kopia reguly."""
    kwota_ts = KATALOG / "interfejs" / "lib" / "kwota.ts"
    kotwica = KATALOG / "interfejs" / "app" / "plynnosc" / "kotwica.tsx"

    nosnik = _bez_komentarzy(kwota_ts.read_text(encoding="utf-8"))
    assert "export function odczytajKwote" in nosnik, (
        "nosnik ksztaltu kwoty zniknal z lib/kwota.ts")
    assert "export function dataJestCzytelna" in nosnik, (
        "nosnik ksztaltu daty zniknal z lib/kwota.ts")

    wolajacy = []
    for plik in (EKRAN, kotwica):
        assert plik.exists(), f"nie ma pliku {plik}"
        kod = _bez_komentarzy(plik.read_text(encoding="utf-8"))
        assert "function odczytajKwote" not in kod, (
            f"druga kopia reguly ksztaltu kwoty w {plik.name}")
        if "odczytajKwote(" in kod:
            wolajacy.append(plik.name)
    assert len(wolajacy) == 2, (
        f"nosnik wolany z {len(wolajacy)} miejsc zamiast dwoch: {wolajacy}")

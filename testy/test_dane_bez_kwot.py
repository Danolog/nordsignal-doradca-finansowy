# -*- coding: utf-8 -*-
"""STRAŻNIK KROKU 7.2: w `interfejs/lib/dane/` nie ma ani jednej wpisanej kwoty.

CO TEN STRAŻNIK NAPRAWDĘ PILNUJE. Do Z6 warstwa danych interfejsu niosła
liczby przepisane z ramek: pięć sald z rubryki, trzy punkty odtworzone
z rysunku z błędem ±11 zł, kwotę stanu pokazowego i cztery wiersze karty
„Co ruszy ten wpis". Każda z nich była DRUGIM NOŚNIKIEM liczby, której
pierwszym nośnikiem jest silnik. Po podpięciu (Z7) warstwa danych ma
wyłącznie WOŁAĆ trasy — a to, czy naprawdę wyłącznie, widać po tym, czy
została w niej choć jedna kwota.

DLACZEGO SKAN OBEJMUJE TAKŻE KOMENTARZE. Kwota w komentarzu nie trafia na
ekran, ale jest zapisem stanu sprzed podpięcia i starzeje się w ciszy —
a przy następnej wątpliwości ktoś ją przeczyta jako wartość odniesienia.
Krok 7.2 mówi wprost „grep nie znajduje", a grep komentarzy nie omija.

KONTROLA LICZNOŚCI JEST TU OBOWIĄZKOWA. Sprawdzenie, do którego nic nie
dociera, melduje sukces: gdyby katalog został przemianowany albo wzorzec
przestał cokolwiek widzieć, pusty zbiór trafień przeszedłby na zielono.
Dlatego każdy przebieg podaje, ile plików i ile znaków obejrzał, i obie
liczby są sprawdzane PRZED porównaniem.

MUTACJA (CLAUDE.md §3.8): `testy/MUTACJE.md`, wpis M-Z7-1.
"""
import pathlib
import re

from pomocnicze import bez_komentarzy

KATALOG = pathlib.Path(__file__).resolve().parent.parent
DANE = KATALOG / "interfejs" / "lib" / "dane"

#: Kwota zapisana po ludzku albo po maszynowemu:
#:   274.06 · 1305,05 · 9 601,03 · 9 920,79 zł · 11 zł
#: Separator tysięcy zwykłą spacją I nierozdzielającą (U+00A0) — ta druga
#: jest tym, co składa `silnik/rdzen/prezentacja.py`, więc wzorzec bez niej
#: przepuszczałby dokładnie te kwoty, które przyszły z silnika.
WZORCE = (
    re.compile(r"\d[\d  ]*[.,]\d{2}\b"),   # liczba z groszami
    re.compile(r"\b\d[\d  ]*\s*zł"),        # liczba z walutą
)

#: Progi pomiaru. Plików w `lib/dane/` są dziś trzy; próg 2 zostawia miejsce
#: na usunięcie jednego bez fałszywego alarmu i łapie awarię „skan nie widzi
#: niczego". Próg znaków łapie przypadek pliku pustego albo obciętego.
PROG_PLIKOW = 2
PROG_ZNAKOW = 1000


def _pliki() -> list[pathlib.Path]:
    return sorted(DANE.glob("*.ts"))


def test_skan_NAPRAWDE_cokolwiek_zobaczyl():
    """Bez tego testu asercja niżej jest bezwartościowa."""
    assert DANE.is_dir(), f"nie ma katalogu warstwy danych: {DANE}"
    pliki = _pliki()
    assert len(pliki) >= PROG_PLIKOW, (
        f"skan widzi {len(pliki)} plików w {DANE}, próg to {PROG_PLIKOW} — "
        f"to nie jest zgodność, to ślepy pomiar")
    znakow = sum(len(p.read_text(encoding="utf-8")) for p in pliki)
    assert znakow >= PROG_ZNAKOW, (
        f"skan przeczytał {znakow} znaków, próg to {PROG_ZNAKOW}")


def test_wzorzec_kwoty_NAPRAWDE_lapie_kwoty():
    """Kontrola dwustronna: wzorzec, który niczego nie łapie, przechodzi
    tak samo jak wzorzec poprawny. Sprawdzamy go na wartościach znanych —
    tych samych, które do Z6 stały w tej warstwie."""
    lapane = ("274.06", "1305,05", "9 601,03", "9 920,79 zł", "11 zł", "0,00")
    for probka in lapane:
        assert any(w.search(probka) for w in WZORCE), f"wzorzec nie widzi kwoty: {probka!r}"
    # I druga strona: rzeczy, które kwotą NIE są, mają przechodzić.
    # Bez tego strażnik z wzorcem `.` byłby „zielony" w tym teście wyżej
    # i czerwieniłby się na każdej dacie, numerze wersji i limicie czasu.
    nielapane = ("2026-10-06", "45", "0.12em", "1440", "v1.2", "300")
    for probka in nielapane:
        assert not any(w.search(probka) for w in WZORCE), (
            f"wzorzec bierze za kwotę coś, co nią nie jest: {probka!r}")


def test_warstwa_danych_NIE_MA_ANI_JEDNEJ_wpisanej_kwoty():
    """Krok 7.2 zadania Z7, dosłownie."""
    trafienia = []
    for plik in _pliki():
        tekst = plik.read_text(encoding="utf-8")
        for numer, wiersz in enumerate(tekst.splitlines(), start=1):
            for wzorzec in WZORCE:
                for m in wzorzec.finditer(wiersz):
                    trafienia.append(f"{plik.name}:{numer}: {m.group(0)!r} — {wiersz.strip()}")
    assert trafienia == [], (
        "kwoty wpisane w warstwę danych interfejsu — każda z nich jest drugim "
        "nośnikiem liczby, której pierwszym nośnikiem jest silnik:\n  "
        + "\n  ".join(trafienia))


def test_warstwa_danych_WOLA_TRASY_zamiast_niesc_stale():
    """Druga połowa tej samej reguły. Brak kwot dałoby się osiągnąć także
    kasując zawartość — a wtedy ekran nie miałby skąd wziąć liczb i strażnik
    wyżej dalej byłby zielony. Ten test pyta o to, czego ma NIE brakować."""
    # KOMENTARZE ZDJETE — inaczej ten straznik jest atrapa. Zmierzone
    # 2026-08-29 (mutacja M-Z7-1c): podmiana `cache: "no-store"` na
    # `cache: "force-cache"` w kodzie dala 4 passed, bo ten sam napis stoi
    # w komentarzu naglowka, ktory TLUMACZY, po co bufor jest wylaczony.
    # Wykryla to mutacja, nie czytanie kodu.
    tresc = {p.name: bez_komentarzy(p.read_text(encoding="utf-8")) for p in _pliki()}
    assert "warstwa-sieciowa.ts" in tresc, "brak jedynego nośnika adresu silnika"
    for plik, sciezki in (
        ("ksiegowanie.ts", ("/api/ksiegowanie", "/api/wpisy", "/api/wpisy/podglad")),
        ("plynnosc.ts", ("/api/plynnosc", "/api/kotwica")),
    ):
        assert plik in tresc, f"brak {plik} w warstwie danych"
        brak = [s for s in sciezki if s not in tresc[plik]]
        assert brak == [], f"{plik} nie woła tras: {brak}"
    # Bufor `fetch` w komponencie serwerowym Next.js oddałby drugą odpowiedź
    # z pamięci — i bramka Z7 („prognoza po wpisie inna niż przed") mierzyłaby
    # wtedy pamięć, nie silnik. To jest awaria, która melduje sukces.
    assert 'cache: "no-store"' in tresc["warstwa-sieciowa.ts"], (
        "warstwa sieciowa pozwala buforować odpowiedzi — po wpisie ekran "
        "pokaże stan sprzed wpisu i będzie wyglądał poprawnie")

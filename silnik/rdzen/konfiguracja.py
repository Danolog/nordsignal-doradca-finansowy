"""Konfiguracja lokalna — klucze i ustawienia z pliku `.env` obok aplikacji.

**Dlaczego to w ogóle istnieje.** Aplikacja graficzna na macOS dostaje
środowisko od `launchd`, a nie z `~/.zshrc`. Uruchomiona ikoną z Findera nie
widzi zmiennych ustawionych w powłoce — i doradca meldował „brak klucza API",
mając rację. Plik obok aplikacji przeżywa restart systemu i nie zależy od tego,
kto ją uruchomił.

**Dlaczego własny parser, a nie `python-dotenv`.** Jego `load_dotenv` pomija
zmienną, gdy klucz **istnieje** w środowisku, niezależnie od zawartości.
Nasza awaria to dokładnie zmienna **istniejąca i pusta**: `launchctl setenv`
zostawił `GEMINI_API_KEY` o długości zero. Biblioteka zostawiłaby tę pustkę
i plik nigdy by nie zadziałał. Reguła, której potrzebujemy, brzmi inaczej:
**pusta wartość to brak wartości** — i jest tu zapisana wprost.

Wartości sekretów **nigdy nie trafiają do komunikatów**. `opis_wczytania`
podaje nazwy i liczbę; log bywa wklejany w zgłoszeniach.
"""

import os
from pathlib import Path

#: Plik leży obok aplikacji. Ścieżka liczona od położenia modułu, nie od
#: katalogu roboczego — żeby nie zależeć od tego, czy ktoś zrobił `cd`.
#: KORZEN projektu. Po przeniesieniu do `silnik/rdzen/` modul lezy DWA
#: poziomy nizej niz w poprzedniku, wiec `parent.parent` wskazywaloby
#: `silnik/`, a nie katalog projektu. Straznik:
#: `testy/test_konfiguracja.py::test_domyslna_sciezka_wskazuje_katalog_projektu`.
KORZEN_PROJEKTU = Path(__file__).resolve().parents[2]
SCIEZKA_DOMYSLNA = KORZEN_PROJEKTU / ".env"


def _rozbierz(linia: str) -> tuple[str, str] | None:
    linia = linia.strip()
    if not linia or linia.startswith("#") or "=" not in linia:
        return None
    nazwa, _, wartosc = linia.partition("=")
    nazwa = nazwa.strip()
    if not nazwa:
        return None
    wartosc = wartosc.strip()
    if len(wartosc) >= 2 and wartosc[0] == wartosc[-1] and wartosc[0] in "\"'":
        wartosc = wartosc[1:-1]
    return nazwa, wartosc


def nazwy_w_pliku(sciezka: Path = SCIEZKA_DOMYSLNA) -> list[str]:
    """Nazwy zmiennych zapisanych w pliku — bez wartości."""
    try:
        tresc = Path(sciezka).read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return []
    return [para[0] for linia in tresc.splitlines()
            if (para := _rozbierz(linia)) is not None]


def wczytaj_lokalna(sciezka: Path = SCIEZKA_DOMYSLNA) -> int:
    """Wnosi zmienne z pliku do środowiska procesu. Zwraca ile ich wniosła.

    **Środowisko procesu wygrywa z plikiem** — ale wyłącznie wtedy, gdy niesie
    niepustą wartość. Dzięki temu da się jednorazowo uruchomić aplikację
    z innym kluczem, nie ruszając pliku, a jednocześnie pusta zmienna
    zostawiona przez `launchctl` nie blokuje wartości z pliku.

    Brak pliku to normalny stan początkowy, nie awaria: aplikacja bez doradcy
    działa w całej reszcie.
    """
    try:
        tresc = Path(sciezka).read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return 0

    wniesione = 0
    for linia in tresc.splitlines():
        para = _rozbierz(linia)
        if para is None:
            continue
        nazwa, wartosc = para
        if os.environ.get(nazwa):  # niepusta wartość w środowisku wygrywa
            continue
        os.environ[nazwa] = wartosc
        wniesione += 1
    return wniesione


def opis_wczytania(sciezka: Path = SCIEZKA_DOMYSLNA) -> str:
    """Zdanie do logu startowego — nazwy i liczba, NIGDY wartości."""
    nazwy = nazwy_w_pliku(sciezka)
    if not nazwy:
        return f"Konfiguracja lokalna: brak pliku {sciezka} albo pusty."
    return (f"Konfiguracja lokalna z {sciezka}: {len(nazwy)} zmiennych ("
            + ", ".join(sorted(nazwy)) + ").")

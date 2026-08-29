"""Jedyny nośnik liczb podatkowych.

Żadna kwota pochodząca z ustawy, rozporządzenia ani komunikatu ZUS nie
występuje poza tym plikiem. Reszta rdzenia woła stąd funkcje, nie przepisuje
wartości (CLAUDE.md §8 v1.17 — „jeden nośnik reguły").

Każda grupa wartości niesie swoje źródło: adres, datę odczytu i datę ostatniej
aktualizacji strony. Wartość bez źródła jest w tym pliku błędem.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from silnik import pieniadz

ROK = 2026


# --- zaokrąglanie: WOŁANE, nie definiowane tutaj ---------------------------
# Jedynym nośnikiem arytmetyki pieniężnej jest `silnik/pieniadz.py` (Z4 krok
# 4.4). Do przenosin ta sama reguła zaokrąglania stała w dwóch miejscach —
# tutaj i tam — czyli była dokładnie tym, przed czym broni `CLAUDE.md` §3.2.
# Te dwie nazwy zostają jako wejście dla siedemnastu modułów, które je wołają;
# **nie liczą już nic same**, tylko przekazują dalej.
#
# Zysk nie jest kosmetyczny: `pieniadz.zabron_float` ODMAWIA przyjęcia liczby
# zmiennoprzecinkowej, a poprzednia wersja tutaj cicho ją konwertowała przez
# `Decimal(x)` — `Decimal(0.1)` daje 0,1000000000000000055511151231257827…,
# co przez większość rachunku wygląda poprawnie i psuje się na sumie kilkuset
# wpisów. Strażnik: `testy/test_pieniadz_jeden_nosnik.py`.

def do_groszy(x: Decimal) -> Decimal:
    """Składki, VAT, kwoty netto — dwa miejsca po przecinku. Woła `pieniadz`."""
    return pieniadz.do_groszy(x)


def do_zlotych(x: Decimal) -> Decimal:
    """Podatek zaokrągla się do pełnych złotych (art. 63 Ordynacji podatkowej).

    Woła `pieniadz`; nie powtarza reguły."""
    return pieniadz.do_zlotych(x)


# --- struktury ------------------------------------------------------------

@dataclass(frozen=True)
class Zrodlo:
    """Metryka pochodzenia grupy wartości.

    `niezweryfikowane` wymienia pozycje, których nie udało się potwierdzić —
    etykieta jest dopuszczalna, udawanie sprawdzonego nie jest.
    """
    url: str
    data_odczytu: date
    data_aktualizacji_strony: date | None
    opis: str
    niezweryfikowane: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProgZdrowotnej:
    """Próg składki zdrowotnej dla ryczałtu.

    `limit_dolny` i `limit_gorny` odnoszą się do przychodu narastająco od
    początku roku kalendarzowego. `mnoznik` mnoży przeciętne wynagrodzenie.
    """
    limit_dolny: Decimal
    limit_gorny: Decimal | None
    mnoznik: Decimal


# --- składka zdrowotna, ryczałt -------------------------------------------

PRZECIETNE_WYNAGRODZENIE_IV_KW = Decimal("9228.64")
STAWKA_ZDROWOTNEJ = Decimal("0.09")

PROGI_ZDROWOTNEJ: tuple[ProgZdrowotnej, ...] = (
    ProgZdrowotnej(Decimal("0"), Decimal("60000"), Decimal("0.60")),
    ProgZdrowotnej(Decimal("60000"), Decimal("300000"), Decimal("1.00")),
    ProgZdrowotnej(Decimal("300000"), None, Decimal("1.80")),
)


def prog_dla_przychodu(przychod_narastajaco: Decimal) -> int:
    """Numer progu składki zdrowotnej (1, 2 albo 3) dla przychodu narastająco.

    **JEDEN NOŚNIK tej reguły w całym silniku** (Z4 krok 4.5). Do przenosin
    stała ona w dwóch miejscach: tutaj (przez `podatki.prog_dla_przychodu`)
    i jako przepisana tabela `if/elif` w `formy.py`. Kopie **rozjechały się**:
    przy przychodzie dokładnie 300 000 zł nośnik dawał mnożnik 1,80, a kopia
    1,00 — różnica 664,46 zł miesięcznie, 7 973,52 zł rocznie, na korzyść
    ryczałtu w porównaniu form. Nikt tego nie pilnował. Teraz pilnuje
    `testy/test_stawki_jeden_nosnik.py`.

    Granica liczona **po osiągnięciu**, nie po przekroczeniu: przychód równy
    60 000 zł wchodzi już na próg drugi. To odczyt ostrożniejszy — źródło jest
    w tej sprawie niejednoznaczne, a pomyłka w tę stronę kosztuje zawyżoną
    rezerwę zamiast niedopłaty.
    """
    przychod = Decimal(przychod_narastajaco)
    for numer, prog in enumerate(PROGI_ZDROWOTNEJ, start=1):
        if prog.limit_gorny is None or przychod < prog.limit_gorny:
            return numer
    return len(PROGI_ZDROWOTNEJ)


def mnoznik_dla_przychodu(przychod_narastajaco: Decimal) -> Decimal:
    """Mnożnik przeciętnego wynagrodzenia dla przychodu narastająco.

    Cukier nad `prog_dla_przychodu` — istnieje po to, żeby wołający nie
    indeksował krotki ręcznie (`PROGI_ZDROWOTNEJ[n-1].mnoznik`), bo takie
    indeksowanie było drugą drogą, którą reguła się powielała.
    """
    return PROGI_ZDROWOTNEJ[prog_dla_przychodu(przychod_narastajaco) - 1].mnoznik


def podstawa_zdrowotnej(mnoznik: Decimal) -> Decimal:
    """Podstawa wymiaru: mnożnik przeciętnego wynagrodzenia, zaokrąglony do groszy.

    Zaokrąglenie następuje TU, przed naliczeniem 9% — tak liczy ZUS.
    9228.64 × 0.60 = 5537.184 → 5537.18, dopiero potem × 0.09.
    """
    return do_groszy(PRZECIETNE_WYNAGRODZENIE_IV_KW * Decimal(mnoznik))


def skladki_zdrowotne_progow() -> tuple[Decimal, ...]:
    """Miesieczna skladka zdrowotna dla KAZDEGO progu, po kolei.

    Istnieje po to, zeby wolajacy nie wpisywal mnoznikow recznie. Do Z4 dwa
    moduly (`narzedzia.py`, `weryfikacja.py`) wywolywaly `skladka_zdrowotna`
    z literalami `0.60` / `1.00` / `1.80` — czyli trzymaly trzecia i czwarta
    kopie tej samej tabeli. Straznik:
    `testy/test_stawki_jeden_nosnik.py::test_mnozniki_progow_maja_JEDEN_nosnik`.
    """
    return tuple(skladka_zdrowotna(p.mnoznik) for p in PROGI_ZDROWOTNEJ)


def skladka_zdrowotna(mnoznik: Decimal) -> Decimal:
    return do_groszy(podstawa_zdrowotnej(mnoznik) * STAWKA_ZDROWOTNEJ)


# --- składki społeczne, duży ZUS ------------------------------------------

PODSTAWA_SPOLECZNYCH = Decimal("5652.00")

STAWKI_SPOLECZNYCH: dict[str, Decimal] = {
    "emerytalna": Decimal("0.1952"),
    "rentowa": Decimal("0.0800"),
    "chorobowa": Decimal("0.0245"),   # dobrowolna
    "wypadkowa": Decimal("0.0167"),   # do 9 ubezpieczonych
    "fp_fs": Decimal("0.0245"),       # Fundusz Pracy + Fundusz Solidarnościowy
}


def skladki_spoleczne(z_chorobowa: bool = True) -> dict[str, Decimal]:
    """Każdy składnik zaokrąglany OSOBNO — tak nalicza ZUS.

    Suma niezaokrąglonych dałaby 1926.77 zamiast 1926.76 (grosz różnicy).
    """
    return {
        nazwa: do_groszy(PODSTAWA_SPOLECZNYCH * stawka)
        for nazwa, stawka in STAWKI_SPOLECZNYCH.items()
        if z_chorobowa or nazwa != "chorobowa"
    }


def suma_spolecznych(z_chorobowa: bool = True) -> Decimal:
    """Suma składników, nigdy wartość przepisana ze strony (ograniczenie globalne 3)."""
    return sum(skladki_spoleczne(z_chorobowa).values(), Decimal("0"))


# --- ryczałt --------------------------------------------------------------

STAWKI_RYCZALTU: tuple[Decimal, ...] = (
    Decimal("0.17"), Decimal("0.15"), Decimal("0.14"), Decimal("0.125"),
    Decimal("0.12"), Decimal("0.10"), Decimal("0.085"), Decimal("0.055"),
    Decimal("0.03"), Decimal("0.02"),
)
STAWKA_RYCZALTU_DOMYSLNA = Decimal("0.085")   # PKWiU 74.90.19.0, decyzja Darka 2026-08-25
STAWKA_RYCZALTU_ALTERNATYWNA = Decimal("0.15")  # sporna kwalifikacja PKWiU

#: Para stawek, ktora `formy.porownaj_formy` zestawia ze skala i liniowym.
#: **Jeden nosnik** — do Z4 te same dwie liczby byly wpisane wprost
#: w `formy.py` (linie 160 i 162), czyli drugi raz. Klucze w rejestrze
#: stawek: `ryczalt.stawka_uslugi_it` i `ryczalt.stawka_15`.
STAWKI_RYCZALTU_DO_POROWNANIA: tuple[tuple[Decimal, str], ...] = (
    (STAWKA_RYCZALTU_DOMYSLNA, "ryczalt 8,5%"),
    (STAWKA_RYCZALTU_ALTERNATYWNA, "ryczalt 15%"),
)

STAWKI_VAT: tuple[Decimal, ...] = (
    Decimal("0.23"), Decimal("0.08"), Decimal("0.05"), Decimal("0.00"),
)
STAWKA_VAT_DOMYSLNA = Decimal("0.23")


# --- skala podatkowa i podatek liniowy (do porównania form, punkt 6c) -----

ZDROWOTNA_MIN_MIESIECZNA = Decimal("432.54")     # skala i liniowy
STAWKA_ZDROWOTNEJ_SKALA = Decimal("0.09")
STAWKA_ZDROWOTNEJ_LINIOWY = Decimal("0.049")
PROG_SKALI = Decimal("120000")
STAWKA_SKALI_PIERWSZA = Decimal("0.12")
STAWKA_SKALI_DRUGA = Decimal("0.32")
KWOTA_ZMNIEJSZAJACA_PODATEK = Decimal("3600")    # 30 000 zł × 12%
STAWKA_LINIOWEGO = Decimal("0.19")

#: Limit odliczenia składki zdrowotnej. NIEZWERYFIKOWANY — podatki.gov.pl
#: przypisuje 14 100 zł do 2026, biznes.gov.pl tę samą kwotę do 2025.
#: Pozycja 12.1 specyfikacji. Dotyczy wyłącznie podatku liniowego.
LIMIT_ODLICZENIA_ZDROWOTNEJ_NIEZWERYFIKOWANY = Decimal("14100")


# --- źródła ---------------------------------------------------------------

_ODCZYT = date(2026, 8, 25)

ZRODLA: dict[str, Zrodlo] = {
    "zdrowotna": Zrodlo(
        url="https://www.biznes.gov.pl/pl/portal/001052",
        data_odczytu=_ODCZYT,
        data_aktualizacji_strony=date(2026, 1, 28),
        opis="Składka zdrowotna ryczałtowców 2026 — trzy progi przychodu.",
    ),
    "spoleczne": Zrodlo(
        url="https://www.biznes.gov.pl/pl/portal/00274",
        data_odczytu=_ODCZYT,
        data_aktualizacji_strony=date(2026, 2, 11),
        opis="Składki społeczne przedsiębiorcy 2026 — duży ZUS, podstawa 5 652 zł.",
    ),
    "vat": Zrodlo(
        url="https://www.biznes.gov.pl/pl/portal/00232",
        data_odczytu=_ODCZYT,
        data_aktualizacji_strony=None,
        opis="Rozliczenie VAT — termin zapłaty przy rozliczeniu miesięcznym.",
    ),
    "ryczalt": Zrodlo(
        url="https://www.biznes.gov.pl/pl/portal/00263",
        data_odczytu=_ODCZYT,
        data_aktualizacji_strony=date(2026, 1, 7),
        opis="Stawki ryczałtu. Stawkę wyznacza PKWiU, nie PKD.",
    ),
    "skala": Zrodlo(
        url="https://www.biznes.gov.pl/pl/portal/00264",
        data_odczytu=date(2026, 8, 26),
        data_aktualizacji_strony=None,
        opis="Skala podatkowa 2026 — stawki 12/32%, prog 120 tys., kwota "
             "zmniejszajaca 3 600 zl, zaliczki narastajaco.",
        niezweryfikowane=[
            "Stawki 12%, 32% i 9% trafiaja do pomiaru jako gole liczby "
            "(12, 32, 9). Same w sobie sa slabym dowodem, bo kazda strona "
            "z liczbami je zawiera. CZESCIOWO DOMKNIETE w Z59: ta strona ma "
            "od tego zadania takze fraze terminowa, sprawdzana przez "
            "oczekiwane_frazy. Fraza niosaca same stawki nadal nie istnieje, "
            "bo mechanizm frazowy jest zwiazany z terminy.TERMINY.",
        ],
    ),
    "skala_liniowy": Zrodlo(
        url="https://www.podatki.gov.pl/ulgi-i-odliczenia/odliczenie-skladek-na-ubezpieczenie-zdrowotne-pit",
        data_odczytu=_ODCZYT,
        data_aktualizacji_strony=None,
        opis="Odliczenie składki zdrowotnej, skala i liniowy — do porównania form.",
        niezweryfikowane=[
            "LIMIT_ODLICZENIA_ZDROWOTNEJ_NIEZWERYFIKOWANY: podatki.gov.pl "
            "przypisuje 14 100 zł do 2026, biznes.gov.pl do 2025 (pozycja 12.1)",
        ],
    ),
}

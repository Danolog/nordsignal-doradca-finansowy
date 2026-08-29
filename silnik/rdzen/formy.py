"""Porównanie form opodatkowania — ryczałt, skala podatkowa, podatek liniowy.

Specyfikacja §6c. Ten moduł istnieje po to, żeby odpowiedzieć na pytanie
ważniejsze niż „8,5% czy 15%": **czy ryczałt jest w ogóle właściwą formą**.
Różnica między formami bywa porównywalna z różnicą między stawkami, a wybór
formy jest bezsporny — kwalifikacja PKWiU sporna.

Formuły skali i liniowego są **uproszczone**: bez kosztów uzyskania, bez ulg,
bez wspólnego rozliczenia. Każde uproszczenie jest wymienione w `zastrzezenia`
i wędruje razem z wynikiem — nigdy nie zostaje w tym pliku.
"""

from dataclasses import dataclass
from decimal import Decimal

from silnik.rdzen import stawki


@dataclass(frozen=True)
class WynikFormy:
    nazwa: str
    pit: Decimal
    zdrowotna: Decimal
    spoleczne: Decimal
    razem: Decimal
    do_dyspozycji: Decimal
    zastrzezenia: list[str]


_ZUS = "Duży ZUS z chorobową. Mały ZUS Plus i ulga na start nieuwzględnione."
_KSIEGOWY = ("Szacunek własny, nie opinia podatkowa. Przed decyzją zestaw "
             "z księgowym.")


def _wspolne(koszty: Decimal) -> list[str]:
    """Zastrzeżenia idą za rzeczywistością, nie za szablonem.

    Powtarzanie „zero kosztów uzyskania przychodu", gdy koszty SĄ policzone,
    jest fałszem — i to fałszem, który podważa zaufanie do wszystkich
    pozostałych zastrzeżeń przy tej samej liczbie.
    """
    if koszty > 0:
        return [
            _ZUS,
            f"Koszty uzyskania przychodu: {koszty} zł (kwoty NETTO z ewidencji "
            "kosztów JDG — dla podatnika VAT kosztem jest netto, bo VAT "
            "naliczony wraca osobno przez rozliczenie VAT).",
            _KSIEGOWY,
        ]
    return [
        _ZUS,
        "Zero kosztów uzyskania przychodu. Skala i liniowy pozwalają je "
        "odliczyć, ryczałt nie — więc realne wyniki skali i liniowego będą "
        "LEPSZE niż tutaj.",
        _KSIEGOWY,
    ]


def _wynik(nazwa, pit, zdrowotna, spoleczne, przychod, zastrzezenia,
           koszty=Decimal("0")):
    """Składa wynik jednej formy.

    `do_dyspozycji` odejmuje koszty WE WSZYSTKICH formach — także w ryczałcie,
    który ich nie odlicza podatkowo. Podatkowo to dwie różne sprawy, ale
    pieniądz wypłynął z konta niezależnie od formy; liczba „do dyspozycji"
    bez kosztów obiecuje środki, których nie ma.
    """
    pit = stawki.do_zlotych(max(Decimal("0"), pit))
    zdrowotna = stawki.do_zlotych(zdrowotna)
    spoleczne = stawki.do_zlotych(spoleczne)
    razem = pit + zdrowotna + spoleczne
    return WynikFormy(
        nazwa=nazwa, pit=pit, zdrowotna=zdrowotna, spoleczne=spoleczne,
        razem=razem,
        do_dyspozycji=Decimal(przychod) - Decimal(koszty) - razem,
        zastrzezenia=_wspolne(Decimal(koszty)) + zastrzezenia,
    )


def _ryczalt(przychod: Decimal, stawka: Decimal, spoleczne: Decimal,
             miesiecy: int, nazwa: str, koszty: Decimal) -> WynikFormy:
    """PODSTAWĄ RYCZAŁTU JEST PRZYCHÓD, NIE DOCHÓD.

    `koszty` wchodzą tu WYŁĄCZNIE do kwoty „do dyspozycji" — nie dotykają ani
    podstawy opodatkowania, ani składki zdrowotnej. Odliczenie ich byłoby
    błędem merytorycznym, nie ulepszeniem; pilnuje tego
    `test_koszty_NIE_ruszaja_ryczaltu`.
    """
    # Próg zdrowotnej: WOŁANY z jedynego nośnika, nie przepisany.
    # Do Z4 stała tu kopia tabeli progów (`if/elif` na 60 000 i 300 000)
    # z komentarzem „ta sama tabela co w rdzen.podatki". Nie była ta sama:
    # przy przychodzie **dokładnie 300 000 zł** kopia dawała mnożnik 1,00,
    # a nośnik 1,80 — bo kopia porównywała nieostro (`<=`), a nośnik ostro.
    # Różnica: 664,46 zł miesięcznie, 7 973,52 zł rocznie, i to na korzyść
    # ryczałtu, czyli w stronę, w którą to porównanie ma NIE być stronnicze.
    # Strażnik: `testy/test_stawki_jeden_nosnik.py`.
    zdrowotna = stawki.skladka_zdrowotna(
        stawki.mnoznik_dla_przychodu(przychod)) * miesiecy
    podstawa = przychod - spoleczne - (zdrowotna / 2)
    zastrzezenia = ["Odliczenie 50% zapłaconej składki zdrowotnej od przychodu."]
    if koszty > 0:
        zastrzezenia.append(
            "Ryczałt NIE odlicza kosztów uzyskania przychodu — podstawą jest "
            "przychód. Koszty widać wyłącznie w kwocie „do dyspozycji”.")
    return _wynik(nazwa, podstawa * stawka, zdrowotna, spoleczne, przychod,
                  zastrzezenia, koszty)


def _skala(przychod: Decimal, spoleczne: Decimal, miesiecy: int,
           koszty: Decimal) -> WynikFormy:
    dochod = max(Decimal("0"), przychod - koszty - spoleczne)
    # Składka zdrowotna na skali NIE jest odliczalna i rośnie liniowo z dochodem.
    zdrowotna = max(stawki.STAWKA_ZDROWOTNEJ_SKALA * dochod,
                    stawki.ZDROWOTNA_MIN_MIESIECZNA * miesiecy)
    if dochod <= stawki.PROG_SKALI:
        pit = stawki.STAWKA_SKALI_PIERWSZA * dochod - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK
    else:
        pit = (stawki.STAWKA_SKALI_PIERWSZA * stawki.PROG_SKALI
               - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK
               + stawki.STAWKA_SKALI_DRUGA * (dochod - stawki.PROG_SKALI))
    return _wynik("skala", pit, zdrowotna, spoleczne, przychod, [
        "Kwota zmniejszająca podatek 3 600 zł (kwota wolna 30 000 zł) — to ona "
        "sprawia, że skala bywa tańsza od spornego ryczałtu 8,5%.",
        "Składka zdrowotna 9% dochodu, NIEODLICZALNA — rośnie liniowo, "
        "więc przewaga skali znika przy wyższym przychodzie.",
        "Formuła uproszczona: bez ulg i wspólnego rozliczenia.",
    ], koszty)


def _liniowy(przychod: Decimal, spoleczne: Decimal, miesiecy: int,
             koszty: Decimal) -> WynikFormy:
    dochod = max(Decimal("0"), przychod - koszty - spoleczne)
    zdrowotna = max(stawki.STAWKA_ZDROWOTNEJ_LINIOWY * dochod,
                    stawki.ZDROWOTNA_MIN_MIESIECZNA * miesiecy)
    limit = stawki.LIMIT_ODLICZENIA_ZDROWOTNEJ_NIEZWERYFIKOWANY
    pit = stawki.STAWKA_LINIOWEGO * (dochod - min(zdrowotna, limit))
    return _wynik("liniowy", pit, zdrowotna, spoleczne, przychod, [
        f"Limit odliczenia składki zdrowotnej {limit} zł jest NIEZWERYFIKOWANY "
        "— podatki.gov.pl przypisuje tę kwotę do 2026, biznes.gov.pl do 2025 "
        "(pozycja 12.1 specyfikacji).",
        "Brak kwoty wolnej — liniowy przegrywa przy niskim dochodzie z definicji.",
    ], koszty)


def porownaj_formy(przychod_roczny: Decimal, miesiecy: int = 12,
                   koszty: Decimal = Decimal("0")) -> list[WynikFormy]:
    """Zwraca cztery formy, posortowane od najtańszej.

    `miesiecy` pozwala policzyć rok niepełny — np. wrzesień–grudzień 2026,
    gdy umowa startuje 1 września.

    `koszty` to suma kosztów uzyskania przychodu w kwotach **netto** za ten
    sam okres. Skala i liniowy je odliczają, ryczałt nie — więc im więcej
    kosztów, tym mocniej porównanie przechyla się PRZECIW ryczałtowi.
    Do 2026-08-25 ta funkcja liczyła zawsze z zerem i tylko to zastrzegała,
    przez co pokazywała ryczałt korzystniej, niż jest.
    """
    przychod = Decimal(przychod_roczny)
    koszty = Decimal(koszty)
    spoleczne = stawki.suma_spolecznych(z_chorobowa=True) * miesiecy
    # Stawki ryczałtu WOŁANE z `stawki.py`, nie wpisane tutaj (Z4 krok 4.5).
    # Reguła `CLAUDE.md` §3.3: żadna liczba z ustawy nie mieszka w kodzie
    # liczącym. Klucze rejestru: `ryczalt.stawka_uslugi_it`, `ryczalt.stawka_15`.
    wyniki = [_ryczalt(przychod, stawka, spoleczne, miesiecy, nazwa, koszty)
              for stawka, nazwa in stawki.STAWKI_RYCZALTU_DO_POROWNANIA]
    wyniki += [
        _skala(przychod, spoleczne, miesiecy, koszty),
        _liniowy(przychod, spoleczne, miesiecy, koszty),
    ]
    return sorted(wyniki, key=lambda w: w.razem)

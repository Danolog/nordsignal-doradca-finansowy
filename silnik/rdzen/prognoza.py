"""Prognoza roczna — kiedy przychód przetnie próg składki zdrowotnej.

Ten moduł jest powodem, dla którego aplikacja nie jest rejestratorem.
Rejestrator mówi, co już się stało. Prognoza mówi, że w czerwcu rata ZUS
rośnie o 332,23 zł — i mówi to w sierpniu, gdy da się jeszcze coś z tym zrobić.

**Wachlarz, nie jedna data.** Umowa z NMI ERP nie gwarantuje wolumenu w żadną
stronę (§6 ust. 2: „nie stanowi gwarancji minimalnego ani maksymalnego poziomu
zleceń"), więc prognoza podająca jedną datę byłaby fałszywym spokojem.
"""

from dataclasses import dataclass
from decimal import Decimal

from silnik.rdzen import stawki
from silnik.rdzen.prezentacja import liczba as _zloty


@dataclass(frozen=True)
class Przeciecie:
    """Moment przecięcia progu składki zdrowotnej.

    `miesiac` równy None znaczy: przy tym wolumenie próg nie zostanie
    przecięty w badanym okresie.
    """
    prog: int                       # numer progu, na który wchodzimy (2 albo 3)
    miesiac: int | None
    przychod_narastajaco: Decimal   # w miesiącu przecięcia, albo na koniec okresu
    wzrost_skladki: Decimal         # o ile miesięcznie rośnie zdrowotna


def _granica(numer_progu: int) -> Decimal:
    """Dolna granica przychodu dla progu o podanym numerze."""
    return stawki.PROGI_ZDROWOTNEJ[numer_progu - 1].limit_dolny


def _wzrost_skladki(numer_progu: int) -> Decimal:
    """Różnica składki między tym progiem a poprzednim — liczona z rejestru."""
    obecny = stawki.skladka_zdrowotna(stawki.PROGI_ZDROWOTNEJ[numer_progu - 1].mnoznik)
    poprzedni = stawki.skladka_zdrowotna(stawki.PROGI_ZDROWOTNEJ[numer_progu - 2].mnoznik)
    return obecny - poprzedni


def prognozuj(godziny_mc: Decimal, stawka_godzinowa: Decimal, miesiecy: int,
              przychod_poczatkowy: Decimal = Decimal("0")) -> list[Przeciecie]:
    """Zwraca przecięcia progu 2 (60 tys.) i progu 3 (300 tys.) w badanym okresie.

    Liczy z części stałej: godziny × stawka. Prowizji nie zgaduje — jej
    wpływ pokazuje się przez podniesienie `przychod_poczatkowy`.
    """
    miesieczny = Decimal(godziny_mc) * Decimal(stawka_godzinowa)
    wyniki: list[Przeciecie] = []

    for numer_progu in (2, 3):
        granica = _granica(numer_progu)
        narastajaco = Decimal(przychod_poczatkowy)
        znaleziony = None
        for miesiac in range(1, miesiecy + 1):
            narastajaco += miesieczny
            if znaleziony is None and narastajaco >= granica:
                znaleziony = (miesiac, narastajaco)
        if znaleziony:
            wyniki.append(Przeciecie(numer_progu, znaleziony[0], znaleziony[1],
                                     _wzrost_skladki(numer_progu)))
        else:
            wyniki.append(Przeciecie(numer_progu, None, narastajaco,
                                     _wzrost_skladki(numer_progu)))
    return wyniki


def wachlarz(warianty_godzin: list[Decimal], stawka_godzinowa: Decimal,
             miesiecy: int, przychod_poczatkowy: Decimal = Decimal("0")
             ) -> dict[Decimal, list[Przeciecie]]:
    """Prognoza dla kilku wariantów wolumenu naraz.

    Domyślne 160 h jest wartością planistyczną, nie zobowiązaniem — dlatego
    interfejs pokazuje wachlarz, a nie jedną datę.
    """
    return {
        godziny: prognozuj(godziny, stawka_godzinowa, miesiecy, przychod_poczatkowy)
        for godziny in warianty_godzin
    }


def ostrzezenie_progowe(przychod_narastajaco: Decimal,
                        srednia_faktura: Decimal) -> str | None:
    """Ostrzeżenie, gdy kolejna faktura przeniesie Cię na wyższy próg.

    To jest informacja, której tabela z historią nie daje, a która realnie
    zmienia decyzję o terminie wystawienia faktury.
    """
    przychod = Decimal(przychod_narastajaco)
    faktura = Decimal(srednia_faktura)
    for numer_progu in (2, 3):
        granica = _granica(numer_progu)
        if przychod >= granica:
            continue
        if przychod + faktura >= granica:
            brakuje = granica - przychod
            return (
                f"Jesteś {_zloty(brakuje)} zł od progu {_zloty(granica)} zł. "
                f"Kolejna faktura podnosi składkę zdrowotną o "
                f"{_zloty(_wzrost_skladki(numer_progu))} zł miesięcznie — "
                f"i dotyczy to już miesiąca, w którym ją wystawisz."
            )
        return None
    return None

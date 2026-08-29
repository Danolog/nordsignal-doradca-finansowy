"""Bilans majątkowy — czysta arytmetyka, zero SQL, zero interfejsu.

Jedyny nośnik reguły „ile jest warte wszystko, co mam, po odjęciu tego, co
jestem winien". `pulpit` tę regułę **woła**, nigdy nie powtarza.

DLACZEGO OSOBNY MODUŁ, A NIE DOKLEJKA DO `budzet.py`: budżet opisuje
**przepływ w miesiącu** (ile wpłynęło, ile wypłynęło), a bilans opisuje
**stan na dziś** (ile leży, ile wisi). To dwie różne wielkości i mylenie ich
kończy się podstawieniem jednej pod drugą — „mam 5 000 na koncie" zamiast
„mam 38 000 długu netto". Kierunek zależności jednostronny, jak w `budzet`:
`pulpit` importuje `majatek`, nigdy odwrotnie.

CZEGO TU ŚWIADOMIE NIE MA: rezerwy na VAT i ZUS. Zobowiązanie podatkowe jest
prawdziwe, ale odpowiadająca mu gotówka **nie jest zapisana po stronie
majątku** — odjęcie samej rezerwy zaniżyłoby wynik o kwotę, która realnie
leży na koncie. Warunek zmiany tej decyzji: wpisanie rachunku firmowego
do tabeli `majatek`.
"""

from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from silnik.rdzen import stawki


#: Kategoria aktywa, która JEST poduszką finansową. Jedyny nośnik tej nazwy
#: po stronie reguły — `pulpit` i `rdzen.narzedzia` ją wołają, nie powtarzają.
KATEGORIA_PODUSZKI = "poduszka"


@dataclass(frozen=True)
class Bilans:
    """Trzy liczby z JEDNEGO pomiaru.

    Składniki jadą razem z wynikiem, bo podpis pod kwotą wymienia je
    z osobna. Gdyby interfejs sumował je po swojemu, ta sama reguła miałaby
    dwa nośniki i mogłaby pokazać kwotę sprzeczną z własnym podpisem.
    """

    aktywa: Decimal
    zobowiazania: Decimal
    netto: Decimal


def _suma(ramka: pd.DataFrame, kolumna: str) -> Decimal:
    """Suma kolumny kwotowej. Pusta tabela to normalny stan, nie awaria."""
    if ramka.empty or kolumna not in ramka.columns:
        return Decimal("0.00")
    return stawki.do_groszy(
        sum((Decimal(str(x)) for x in ramka[kolumna]), Decimal("0.00")))


def poduszka_finansowa(majatek: pd.DataFrame) -> Decimal:
    """Ile mam odłożone NA CZAS BEZ PRACY. Jedyny nośnik tej reguły.

    DECYZJA DARKA 2026-08-28 (D-36), dosłownie: „Poduszka to nie jest to samo,
    co konto oszczędnościowe. Poduszka to jest budowanie zabezpieczenia na
    czas, kiedy nie ma pracy. Konto oszczędnościowe jest oddzielne na różne
    inne cele. Rachunek bieżący jest pieniędzmi na bieżące życie."

    Stąd reguła: poduszką jest WYŁĄCZNIE aktywo z kategorią `poduszka`.
    Ani rachunek rozliczeniowy, ani drugi rachunek, ani lokata nie stają się
    poduszką dlatego, że leżą na nich pieniądze. Kategoria jest deklaracją
    przeznaczenia, a przeznaczenie deklaruje człowiek, nie kod.

    DLACZEGO TO JEST W `rdzen`, A NIE NA EKRANIE. Do 2026-08-28 ta sama
    reguła miała DWA nośniki: `pulpit/dashboard.py` (kafelek „Poduszka
    finansowa") i `rdzen/narzedzia.py` (narzędzie `stan_finansow` doradcy).
    Dwie kopie tej samej reguły to dwie liczby, które rozjadą się przy
    pierwszej zmianie — a wtedy kafelek mówi jedno, doradca drugie i nie ma
    czym rozstrzygnąć, która liczba jest prawdziwa. Ten projekt zmierzył to
    już raz na „wolnych środkach" (ekran −6 098,11 zł, doradca +8 007,89 zł,
    te same dane, ta sama chwila).
    """
    if majatek.empty or "kategoria" not in majatek.columns:
        return Decimal("0.00")
    wybrane = majatek[majatek["kategoria"] == KATEGORIA_PODUSZKI]
    return _suma(wybrane, "wartosc")


def bilans(majatek: pd.DataFrame, zobowiazania: pd.DataFrame) -> Bilans:
    """Wartość netto: suma `wartosc` aktywów minus suma `kapital` długów.

    Po stronie długu liczy się **kapitał pozostały do spłaty**, nie rata i nie
    suma rat do końca kredytu: rata zawiera odsetki za czas, który jeszcze nie
    minął, a tych dziś nie jesteś winien.
    """
    aktywa = _suma(majatek, "wartosc")
    dlugi = _suma(zobowiazania, "kapital")
    return Bilans(aktywa=aktywa, zobowiazania=dlugi, netto=aktywa - dlugi)

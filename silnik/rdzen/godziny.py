"""Agregacja godzin — logika rozliczeniowa, nie prezentacyjna.

Leży w rdzeniu, nie w pulpicie, bo `rozklad_godzin` jest jednym z ośmiu
narzędzi doradcy (§9a specyfikacji). Jedna implementacja, dwóch konsumentów.

**Po co ta tabela w ogóle istnieje.** Art. 12 ust. 3 ustawy o ryczałcie: przy
przychodach opodatkowanych różnymi stawkami rozdzielne rozliczenie przysługuje
WYŁĄCZNIE wtedy, gdy ewidencja pozwala te przychody rozdzielić. Rozdzielony
musi być dowód, nie tylko opis na fakturze.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from silnik.rdzen import magazyn, stawki

#: Rodzaje czynności odwzorowujące §3 ust. 2 umowy B2B z NMI ERP.
#: Sugerowane PKWiU jest podpowiedzią, nie rozstrzygnięciem — kwalifikacja
#: należy do księgowego (pozycja 12.3 specyfikacji).
RODZAJE_CZYNNOSCI: dict[str, str] = {
    "pozyskiwanie klientów (§3.2.a, d)": "46.19.10.0",
    "negocjacje i oferty (§3.2.e)": "46.19.10.0",
    "proces sprzedaży do umowy (§3.2.f)": "46.19.10.0",
    "analiza rynku i konkurencji (§3.2.j)": "73.20.19.0",
    "raporty i rekomendacje (§3.2.l)": "74.90.19.0",
    "współpraca przy rozwiązaniach (§3.2.g)": "74.90.19.0",
    "prowadzenie CRM (§3.2.k)": "82.11.10.0",
    "strategia i marketing (§3.2.h)": "70.22.13.0",
    "wydarzenia branżowe (§3.2.i)": "73.11.19.0",
    "inne (§3.2.m)": "74.90.19.0",
}


@dataclass(frozen=True)
class PozycjaFaktury:
    """Jedna pozycja faktury: godziny jednego PKWiU, przeliczone na kwotę."""
    pkwiu: str
    godziny: Decimal
    stawka_godzinowa: Decimal
    netto: Decimal


def agreguj(polaczenie, od: date, do: date,
            stawka_godzinowa: Decimal = Decimal("70")) -> list[PozycjaFaktury]:
    """Zwija godziny z okresu do pozycji faktury — OSOBNO dla każdego PKWiU.

    Zsumowanie wszystkiego do jednej pozycji odbiera prawo do stosowania
    różnych stawek. Dlatego rozdzielenie jest tu regułą, nie opcją.
    """
    df = magazyn.wczytaj_godziny(polaczenie, od, do)
    if df.empty:
        return []
    sumy: dict[str, Decimal] = {}
    for _, wiersz in df.iterrows():
        sumy[wiersz["pkwiu"]] = sumy.get(wiersz["pkwiu"], Decimal("0")) \
            + wiersz["liczba_godzin"]
    return [
        PozycjaFaktury(pkwiu=pkwiu, godziny=godziny,
                       stawka_godzinowa=stawka_godzinowa,
                       netto=stawki.do_groszy(godziny * stawka_godzinowa))
        for pkwiu, godziny in sorted(sumy.items())
    ]


def rozklad(polaczenie, od: date, do: date) -> dict[str, Decimal]:
    """Godziny w podziale na rodzaj czynności — odpowiedź na pytanie,
    jaka część pracy to naprawdę sprzedaż, a jaka analityka."""
    df = magazyn.wczytaj_godziny(polaczenie, od, do)
    if df.empty:
        return {}
    wynik: dict[str, Decimal] = {}
    for _, wiersz in df.iterrows():
        rodzaj = wiersz["rodzaj_czynnosci"]
        wynik[rodzaj] = wynik.get(rodzaj, Decimal("0")) + wiersz["liczba_godzin"]
    return dict(sorted(wynik.items()))

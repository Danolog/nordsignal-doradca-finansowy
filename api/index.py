# -*- coding: utf-8 -*-
"""PUNKT WEJSCIA WARSTWY SIECIOWEJ — cienka warstwa nad silnikiem, ZERO rachunku.

DLACZEGO KLASA ODPOWIEDZI SIEDZI NA `APIRouter`, A NIE PRZY DOLACZANIU.
Zmierzone w FastAPI 0.141 (poprzednia aplikacja, 2026-08-27): przekazanie
`default_response_class` do `include_router` NIE DOCIERA do trasy — dolaczony
router jest zawijany, a klasa odpowiedzi rozstrzyga sie na routerze. Jedyne
dzialajace miejsce to konstruktor `APIRouter`.

To jest RYZYKO NR 1 calej warstwy: bez tego kwoty wychodza jako liczby
zmiennoprzecinkowe, gubia grosze i zwracaja 200 — awaria, ktora melduje sukces.

ZDANIE SILNIKA DOCIERA W CALOSCI (Z6). Odmowa liczenia jest w tym projekcie
czescia produktu, nie awaria: silnik odmawia, gdy nie zna formy opodatkowania,
gdy stawka ryczaltu nie zostala podana albo gdy kategoria nie istnieje —
i za kazdym razem MOWI, czego brakuje. Do Z6 takie zdania konczyly w konsoli,
a uzytkownik widzial „Internal Server Error", czyli komunikat, z ktorym nie da
sie nic zrobic. Trzy uchwyty nizej zamieniaja je na kod 400 z tym samym
zdaniem, slowo w slowo.

CO PRZEZ TO PRZESTAJE DZIALAC (pozycja obowiazkowa, CLAUDE.md §3.11):
`ValueError` i `ArithmeticError` podniesione przez NASZ WLASNY blad — nie przez
odmowe silnika — takze dostana kod 400 zamiast 500. Wada w kodzie bedzie
wygladac jak zle zadanie uzytkownika. Zawezenie do wlasnych typow wyjatkow
silnika nie jest dzis mozliwe, bo `magazyn`, `podatki` i `budzet` zglaszaja
odmowy takze golym `ValueError`. Nastepca: wspolny typ odmowy w silniku —
otwarte, zglaszam do Ethana. `TypeError` swiadomie NIE jest tu wymieniony:
to najczestszy ksztalt wlasnej wady i ma zostac gloshy jako 500.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from api import trasy_ksiegowanie, trasy_plynnosc
from api.kwoty import OdpowiedzJSON
from silnik.rdzen import magazyn

# KLASA ODPOWIEDZI MA JEDEN NOSNIK — `api/kwoty.py` (Z5 krok 5.3).
#
# Do Z5 stala tu wlasna klasa `OdpowiedzZKwotami`, czyli DRUGI nosnik tej samej
# reguly, i rozniła sie od pierwszego w dwoch miejscach naraz:
#   * zamieniala `Decimal` na napis PO CICHU (`format(x, "f")`) — zamiast
#     zadac, zeby zaokraglenie do groszy zapadlo raz, w `kwoty.kwota()`;
#   * NIE SPRAWDZALA WCALE liczb zmiennoprzecinkowych. `json.dumps` serializuje
#     `float` sam, bez pytania `default`, wiec haczyk na nieznanym typie go nie
#     widzial. Odpowiedz z `float` w srodku wychodzila stad z kodem 200.
# Obie roznice byly ciche. Straznik: `testy/test_kontrakt_dwa_nosniki.py`,
# sekcja „serializacja".

trasy = APIRouter(default_response_class=OdpowiedzJSON)
aplikacja = FastAPI(title="Doradca Finansowy", default_response_class=OdpowiedzJSON)

#: Trasy ZBUDOWANE, nie zapisane w spisie. Liczba wyprowadzona z routerow,
#: a nie wpisana recznie — recznie wpisana rozjechalaby sie przy pierwszej
#: dolozonej trasie i to wlasnie ona byla nieprawdziwa w `api/trasy.py`
#: do Z6 („10 tras" wobec 24 zmierzonych u poprzednika).
ZBUDOWANE = tuple(
    trasa.path
    for router in (trasy_ksiegowanie.trasy, trasy_plynnosc.trasy)
    for trasa in router.routes) + ("/api/zdrowie",)


@trasy.get("/api/zdrowie")
def zdrowie() -> dict:
    """Ile tras jest w spisie i ile z nich naprawde stoi."""
    from api import trasy as spis

    return {
        "stan": "dwa ekrany",
        "tras_w_spisie": len(spis.WSZYSTKIE),
        "zbudowanych": len(ZBUDOWANE),
    }


def _odmowa(_zadanie: Request, blad: Exception) -> JSONResponse:
    """Odmowa silnika oddana W CALOSCI, bez przeredagowania.

    Zdanie silnika mowi, CZEGO BRAKUJE — „Podaj stawke ryczaltu", „Nie ma
    wpisu o numerze 7". Skrocone do „Bad request" przestaje byc instrukcja
    i staje sie samym faktem porazki.
    """
    return JSONResponse(status_code=400, content={"detail": str(blad)})


for _typ_bledu in (magazyn.BladMagazynu, ValueError, ArithmeticError):
    aplikacja.add_exception_handler(_typ_bledu, _odmowa)

aplikacja.include_router(trasy)
aplikacja.include_router(trasy_ksiegowanie.trasy)
aplikacja.include_router(trasy_plynnosc.trasy)

# -*- coding: utf-8 -*-
"""PUNKT WEJSCIA WARSTWY SIECIOWEJ — cienka warstwa nad silnikiem, ZERO rachunku.

DLACZEGO KLASA ODPOWIEDZI SIEDZI NA `APIRouter`, A NIE PRZY DOLACZANIU.
Zmierzone w FastAPI 0.141 (poprzednia aplikacja, 2026-08-27): przekazanie
`default_response_class` do `include_router` NIE DOCIERA do trasy — dolaczony
router jest zawijany, a klasa odpowiedzi rozstrzyga sie na routerze. Jedyne
dzialajace miejsce to konstruktor `APIRouter`.

To jest RYZYKO NR 1 calej warstwy: bez tego kwoty wychodza jako liczby
zmiennoprzecinkowe, gubia grosze i zwracaja 200 — awaria, ktora melduje sukces.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from api.kwoty import OdpowiedzJSON

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


@trasy.get("/api/zdrowie")
def zdrowie() -> dict:
    """Jedyna trasa gotowa. Reszta wg spisu w `api/trasy.py`."""
    from api import trasy as spis

    return {
        "stan": "szkielet",
        "tras_w_spisie": len(spis.WSZYSTKIE),
        "zbudowanych": 1,
    }


aplikacja.include_router(trasy)

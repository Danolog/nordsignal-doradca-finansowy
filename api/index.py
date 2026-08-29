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

import json
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse


class OdpowiedzZKwotami(JSONResponse):
    """Kwoty wychodza jako NAPIS, nigdy jako liczba zmiennoprzecinkowa.

    `json.dumps` domyslnie odmawia serializacji `Decimal`, a najczestsza
    "naprawa" — `default=float` — jest dokladnie ta awaria, przed ktora ten
    plik broni. Napis zachowuje grosze i zmusza odbiorce do jawnej zamiany.
    """

    def render(self, content: Any) -> bytes:
        def zamien(x):
            if isinstance(x, Decimal):
                return format(x, "f")
            raise TypeError(f"nieserializowalne: {type(x).__name__}")

        return json.dumps(
            content, default=zamien, ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")


trasy = APIRouter(default_response_class=OdpowiedzZKwotami)
aplikacja = FastAPI(title="Doradca Finansowy", default_response_class=OdpowiedzZKwotami)


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

# -*- coding: utf-8 -*-
"""DWIE TRASY EKRANU PLYNNOSC. Kazda to jedno `return`.

ZERO RACHUNKU W TRASIE — jak w `trasy_ksiegowanie.py`: ani jednego `if`,
petli i dzialania arytmetycznego. Werdykt, okno wykresu i saldo minimalne
liczy `silnik/ekran_plynnosc.py`, a salda dzienne — `rdzen/prognoza_plynnosci`.

DLACZEGO ZAPIS KOTWICY ODDAJE CALY EKRAN. Nowy odczyt stanu konta przesuwa
punkt startu prognozy, wiec zmienia NARAZ werdykt, dzien pod kreska, saldo
minimalne i cala serie. Odpowiedz „zapisano" kazalaby przegladarce albo
zlozyc te liczby po swojemu (drugi nosnik), albo odpytac drugi raz (dwa
przebiegi prognozy dla jednej chwili).
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Body, Depends, Query

from api import kwoty, wspolne
from silnik import ekran_plynnosc

trasy = APIRouter(default_response_class=kwoty.OdpowiedzJSON)


@trasy.get("/api/plynnosc")
def plynnosc(polaczenie=Depends(wspolne.polaczenie),
             dzis: "str | None" = Query(default=None)) -> dict:
    """`DanePlynnosci`: ksiega, wykres, saldo minimalne, zdanie werdyktu."""
    return asdict(ekran_plynnosc.zbierz(
        polaczenie, dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))


@trasy.put("/api/kotwica")
def kotwica(tresc: dict = Body(...),
            polaczenie=Depends(wspolne.polaczenie),
            dzis: "str | None" = Query(default=None)) -> dict:
    """Odczyt salda — ZRODLO kotwicy prognozy. Kwota moze byc UJEMNA.

    Konto na debecie to realny stan konta, nie blad wpisu — to jedyne miejsce
    w tej bazie, w ktorym minus jest czescia liczby, a nie pomylka jezyka.
    Regule niesie `magazyn.zapisz_stan_konta`, jedyny pisarz tego obszaru.
    """
    return asdict(ekran_plynnosc.zapisz_kotwice(
        polaczenie, data=tresc.get("data"), kwota=tresc.get("kwota"),
        dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))

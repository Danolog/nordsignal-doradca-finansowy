# -*- coding: utf-8 -*-
"""CZTERY TRASY EKRANU KSIEGOWANIE. Kazda to jedno `return`.

ZERO RACHUNKU W TRASIE — zasada twarda Z6, tutaj widoczna golym okiem:
w tym pliku nie ma ani jednego `if`, ani jednej petli i ani jednego dzialania
arytmetycznego. Wszystko, co jest decyzja o kwocie — w tym rozstrzygniecie
„kwota ujemna: pytanie czy zapis" — siedzi w `silnik/ekran_ksiegowanie.py`,
bo trasa jest jedna z wielu, a regula ma byc jedna.

KAZDA KWOTA JAWNIE WOLA `kwoty.kwota()`. Nie jest to ozdoba ani zwyczaj:
`json.dumps` serializuje liczbe zmiennoprzecinkowa SAM, bez pytania `default`,
wiec odpowiedz z `float` w srodku wychodzila u poprzednika z kodem 200 —
awaria, ktora meldowala sukces. Funkcja zamieniajaca wchodzi do silnika
argumentem (`napis_kwoty=kwoty.kwota`), bo silnik nie ma prawa importowac
`fastapi` (`testy/test_granice.py`). Zaokraglenie do groszy zapada RAZ, tam.

JEDEN PISZACY NA JEDEN OBSZAR: do tabeli wpisow pisze wylacznie
`magazyn.zapisz_wpis` / `magazyn.usun_wpis`, wolane z jednego miejsca
w silniku. Zlamanie tej zasady dalo u poprzednika zmierzone 400 prob zapisu
-> 274 wiersze: wpisy ginely bez zadnego sygnalu.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Body, Depends, Query

from api import kwoty, wspolne
from silnik import ekran_ksiegowanie

trasy = APIRouter(default_response_class=kwoty.OdpowiedzJSON)


@trasy.get("/api/ksiegowanie")
def ksiegowanie(polaczenie=Depends(wspolne.polaczenie),
                dzis: "str | None" = Query(default=None),
                typ: str = Query(default=ekran_ksiegowanie.TYP_DOMYSLNY),
                ) -> dict:
    """`DaneKsiegowania`: kategorie w kolejnosci silnika, ostatnie wpisy,
    licznik miesiaca i karta „Co ruszy ten wpis" dla pustego pola kwoty."""
    return asdict(ekran_ksiegowanie.zbierz(
        polaczenie, dzis=wspolne.dzien(dzis), typ=typ,
        napis_kwoty=kwoty.kwota))


@trasy.post("/api/wpisy")
def dodaj_wpis(tresc: dict = Body(...),
               polaczenie=Depends(wspolne.polaczenie),
               dzis: "str | None" = Query(default=None)) -> dict:
    """Zapis wpisu ALBO pytanie o minus — rozstrzyga silnik, nie ta funkcja.

    Kwota ujemna NIE JEST BLEDEM ZADANIA i nie dostaje kodu 4xx: uzytkownik
    nie popelnil literowki, tylko powiedzial prawde w zlym jezyku (minus jest
    juz w typie wpisu). Odpowiedz niesie `stan` i kwote, ktora zapiszemy po
    potwierdzeniu; BRZMIENIE pytania mieszka po stronie interfejsu
    (`interfejs/lib/napisy.ts`) i nie ma tu swojego drugiego nosnika.
    """
    return asdict(ekran_ksiegowanie.zapisz(
        polaczenie, data=tresc.get("data"), typ=tresc.get("typ"),
        kategoria=tresc.get("kategoria"), kwota=tresc.get("kwota"),
        szczegoly=tresc.get("szczegoly"),
        potwierdzone=bool(tresc.get("potwierdzone")),
        dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))


@trasy.delete("/api/wpisy/{id}")
def wycofaj_wpis(id: int, polaczenie=Depends(wspolne.polaczenie),
                 dzis: "str | None" = Query(default=None)) -> dict:
    """Wycofanie wpisu. Nazwa parametru jest `id`, bo taka jest sciezka
    w jedynym spisie tras (`api/trasy.py`) — zmiana nazwy zmienilaby sciezke."""
    return asdict(ekran_ksiegowanie.wycofaj(
        polaczenie, wpis_id=id, dzis=wspolne.dzien(dzis),
        napis_kwoty=kwoty.kwota))


@trasy.post("/api/wpisy/podglad")
def podglad_wpisu(tresc: dict = Body(...),
                  polaczenie=Depends(wspolne.polaczenie),
                  dzis: "str | None" = Query(default=None)) -> dict:
    """`PodgladSkutku` — CZTERY wiersze, czwarty mowi, co sie NIE ruszylo.

    Czwarty wiersz jest jedynym miejscem, w ktorym uzytkownik dowiaduje sie,
    czego wpis NIE dotknal. Bez niego szukalby ruchu, ktorego nie ma, i uznal
    jego brak za wade obliczen.
    """
    return asdict(ekran_ksiegowanie.podglad_z_bazy(
        polaczenie, typ=tresc.get("typ"), kategoria=tresc.get("kategoria"),
        kwota=tresc.get("kwota"), dzien=wspolne.dzien(tresc.get("data")),
        dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))

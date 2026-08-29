# -*- coding: utf-8 -*-
"""SZESC TRAS EKRANU BUDZET. Kazda to jedno `return`.

ZERO RACHUNKU W TRASIE — zasada twarda Z6, tutaj widoczna golym okiem:
w tym pliku nie ma ani jednego `if`, ani jednej petli i ani jednego dzialania
arytmetycznego. Rozstrzygniecia — ktore reguly obowiazuja w miesiacu, czy
pozycje zamknac czy skasowac, co znaczy pusta stawka miesiaca — siedza
w `silnik/ekran_budzet.py`, bo trasa jest jedna z wielu, a regula ma byc
jedna. Straznik: `testy/test_trasy_bez_rachunku.py`.

TRZY Z TYCH TRAS SA WARUNKIEM WYLACZENIA STAREJ ZAKLADKI (P-1):
`POST /api/plan`, `PUT /api/plan/{id}` i `POST /api/plan/{id}/zakoncz`.
Razem z dwoma trasami wpisow (Ksiegowanie) daja komplet pieciu z
`api.trasy.WARUNEK_WYLACZENIA`. Do W9b brakowalo dokladnie tej trojki.

KOSZA NIE MA I NIE BEDZIE. W tym pliku nie ma trasy `DELETE .../plan...` —
kosz przy pozycji planu KONCZY REGULE od wskazanego miesiaca w przod
(`POST /api/plan/{id}/zakoncz`), a historii nie rusza. `magazyn.usun_plan`
istnieje w silniku i jest swiadomie odciety od warstwy sieciowej (Z-9);
pilnuje tego `testy/test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje`.

KAZDA KWOTA WCHODZI I WYCHODZI NAPISEM. Silnik dostaje `napis_kwoty=kwoty.kwota`
argumentem, bo nie ma prawa importowac `fastapi` (`testy/test_granice.py`);
zaokraglenie do groszy zapada RAZ, tam. Kwota przyslana przez przegladarke
jest napisem az do `Decimal` w `ekran_budzet._kwota_do_zapisu` — zadnego
kroku przez liczbe zmiennoprzecinkowa, bo taki krok gubil u poprzednika
grosze i zwracal 200.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Body, Depends, Query

from api import kwoty, wspolne
from silnik import ekran_budzet

trasy = APIRouter(default_response_class=kwoty.OdpowiedzJSON)


@trasy.get("/api/budzet")
def budzet(polaczenie=Depends(wspolne.polaczenie),
           dzis: "str | None" = Query(default=None),
           miesiac: "str | None" = Query(default=None)) -> dict:
    """`DaneBudzetu`: kafelki, bilans planu, plan kontra wykonanie, cele,
    pozycje planu i historia miesiaca.

    `miesiac` w postaci „2026-10". Pusty znaczy „miesiac dnia dzisiejszego" —
    rozstrzyga to silnik, nie ta funkcja, bo ta sama odpowiedz jest potrzebna
    pieciu pozostalym trasom tego ekranu.
    """
    return asdict(ekran_budzet.zbierz(
        polaczenie, dzis=wspolne.dzien(dzis), miesiac=miesiac,
        napis_kwoty=kwoty.kwota))


@trasy.post("/api/plan")
def dodaj_pozycje_planu(tresc: dict = Body(...),
                        polaczenie=Depends(wspolne.polaczenie),
                        dzis: "str | None" = Query(default=None)) -> dict:
    """„Dodaj pozycje planu" — regula obowiazujaca OD wskazanego miesiaca.

    Pozycja zalozona tutaj jest REGULA, nie wpisem na jeden miesiac: obowiazuje
    do odwolania i wlasnie dlatego jej kosz nazywa sie „Zakoncz". Odpowiedz
    niesie caly odswiezony ekran, bo jedna nowa pozycja rusza naraz kafelki,
    bilans, tabele i licznik naglowka.
    """
    return asdict(ekran_budzet.ustaw_pozycje(
        polaczenie, miesiac=tresc.get("miesiac"), typ=tresc.get("typ"),
        kategoria=tresc.get("kategoria"), kwota=tresc.get("kwota"),
        opis=tresc.get("opis"), dzien=tresc.get("dzien"),
        co_ile_miesiecy=tresc.get("coIleMiesiecy"),
        dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))


@trasy.put("/api/plan/{id}")
def zmien_pozycje_planu(id: int, tresc: dict = Body(...),
                        polaczenie=Depends(wspolne.polaczenie),
                        dzis: "str | None" = Query(default=None)) -> dict:
    """Zmiana pozycji planu OD wskazanego miesiaca w przod — historia zostaje.

    Tozsamosc pozycji (typ, kategoria, opis) bierze sie z wiersza wskazanego
    numerem i ta trasa jej NIE zmienia; zmieniaja sie kwota, dzien i cykl.
    Uzasadnienie przy `ekran_budzet.zmien_pozycje`.

    Nazwa parametru jest `id`, bo taka jest sciezka w jedynym spisie tras
    (`api/trasy.py`) — zmiana nazwy zmienilaby sciezke.
    """
    return asdict(ekran_budzet.zmien_pozycje(
        polaczenie, plan_id=id, miesiac=tresc.get("miesiac"),
        kwota=tresc.get("kwota"), dzien=tresc.get("dzien"),
        co_ile_miesiecy=tresc.get("coIleMiesiecy"),
        dzis=wspolne.dzien(dzis), napis_kwoty=kwoty.kwota))


@trasy.post("/api/plan/{id}/zakoncz")
def zakoncz_pozycje_planu(id: int, tresc: dict = Body(...),
                          polaczenie=Depends(wspolne.polaczenie),
                          dzis: "str | None" = Query(default=None)) -> dict:
    """„Zakoncz te pozycje od <miesiac>" — KONIEC REGULY, NIGDY KASOWANIE.

    Wczesniejsze miesiace zostaja bez zmian: nadal pokazuja, ze pozycja byla
    zaplanowana i ile z niej wykonano. Zmienia sie wylacznie przyszlosc.
    Metoda jest `POST`, nie `DELETE`, i to nie jest kwestia gustu — `DELETE`
    obiecywalby usuniecie, a tu nic sie nie usuwa.

    `zakres` (opcjonalny): „ten_i_nastepne" domyslnie albo „tylko_ten" dla
    pominiecia jednego wystapienia pozycji powtarzalnej. Wartosc domyslna
    ustawia silnik — trasa nie ma prawa do rozgalezienia.
    """
    return asdict(ekran_budzet.zakoncz_pozycje(
        polaczenie, plan_id=id, miesiac=tresc.get("miesiac"),
        zakres=tresc.get("zakres"), dzis=wspolne.dzien(dzis),
        napis_kwoty=kwoty.kwota))


@trasy.post("/api/plan/kopiuj")
def kopiuj_plan(tresc: dict = Body(...),
                polaczenie=Depends(wspolne.polaczenie),
                dzis: "str | None" = Query(default=None)) -> dict:
    """„Skopiuj z wrzesnia" — plan poprzedniego miesiaca na wskazany.

    `zMiesiaca` jest opcjonalne: bez niego zrodlo wyprowadza sie z celu tym
    samym nosnikiem, ktorym ekran sklada napis przycisku. Pozycje juz
    istniejace w miesiacu docelowym NIE sa nadpisywane — reczna poprawka jest
    cenniejsza niz kopia.
    """
    return asdict(ekran_budzet.kopiuj(
        polaczenie, miesiac=tresc.get("miesiac"),
        z_miesiaca=tresc.get("zMiesiaca"), dzis=wspolne.dzien(dzis),
        napis_kwoty=kwoty.kwota))


@trasy.post("/api/cele")
def dodaj_cel(tresc: dict = Body(...),
              polaczenie=Depends(wspolne.polaczenie),
              dzis: "str | None" = Query(default=None)) -> dict:
    """„Dodaj cel" — cel oszczednosciowy z terminem.

    Kategoria musi byc typu „Oszczednosci" i rozstrzyga to `magazyn.zapisz_cel`:
    cel wskazujacy kategorie wydatku liczylby postep z pieniedzy WYDANYCH.
    """
    return asdict(ekran_budzet.dodaj_cel(
        polaczenie, nazwa=tresc.get("nazwa"), kategoria=tresc.get("kategoria"),
        kwota_docelowa=tresc.get("kwotaDocelowa"), termin=tresc.get("termin"),
        miesiac=tresc.get("miesiac"), dzis=wspolne.dzien(dzis),
        napis_kwoty=kwoty.kwota))

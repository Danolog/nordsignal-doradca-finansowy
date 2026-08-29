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

import os
import time
from contextlib import asynccontextmanager

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

#: LICZNIKI ZYCIA PROCESU — jedyny sposob, zeby odpowiedziec na pytanie,
#: ktore W6 zastalo NIEROZSTRZYGNIETE: czy na platformie uchwyt cyklu zycia
#: biegnie RAZ NA ZIMNY START, czy RAZ NA WYWOLANIE. Roznica nie jest
#: akademicka — migracja schematu siedzi w tym uchwycie (W2), wiec „raz na
#: wywolanie" znaczyloby pelny DDL na sciezce zadania, czyli dokladnie to,
#: co W2 usuwalo (pomiar sprzed W2: 98 polecen SQL, 59 piszacych, na kazde
#: zadanie HTTP).
#:
#: Odczytuje je `/api/zdrowie`. Trzy liczby razem daja odpowiedz, ktorej
#: zadna z nich nie daje osobno: ten sam `pid` przy `zadan > 1` znaczy ten
#: sam proces, a `uruchomien_cyklu_zycia` mowi, ile razy migracja w tym
#: procesie ruszyla. `uruchomien == zadan` to sygnal alarmowy.
_CHWILA_IMPORTU = time.time()
_URUCHOMIEN_CYKLU_ZYCIA = 0
_ZADAN_ZDROWIA = 0


@asynccontextmanager
async def cykl_zycia(_aplikacja: FastAPI):
    """MIGRACJA RAZ, PRZY STARCIE PROCESU — nie raz na zadanie (W2).

    Do 2026-08-29 `magazyn.polacz()` stawialo schemat samo, przy kazdym
    otwarciu bazy. Poniewaz polaczenie jest zaleznoscia NA ZADANIE
    (`api/wspolne.polaczenie`), znaczylo to pelny DDL przy kazdym zadaniu HTTP:
    zmierzone sonda `set_trace_callback` — **98 polecen SQL, 59 piszacych**.
    U poprzednika (plik na dysku) niewidoczne; przy PostgreSQL nie do
    utrzymania — od W4 baza jest serwerem, a nie plikiem obok kodu.

    Po rozdzieleniu migracja jest tutaj i tylko tutaj. `polacz()` bazy
    niezmigrowanej NIE naprawia po cichu — odmawia otwarcia i mowi, co
    uruchomic. Gdyby ten uchwyt zniknal, aplikacja nie „dzialalaby na pustej
    bazie": kazde zadanie konczylo by sie kodem 400 z instrukcja.

    CO PRZEZ TO PRZESTAJE DZIALAC: proces, ktory otwiera baze z pominieciem
    tego uchwytu (wlasny skrypt, wiersz polecen), musi zawolac migracje sam —
    `./.venv/bin/python -m silnik.rdzen.magazyn`.
    """
    global _URUCHOMIEN_CYKLU_ZYCIA
    _URUCHOMIEN_CYKLU_ZYCIA += 1
    magazyn.zmigruj()
    yield


trasy = APIRouter(default_response_class=OdpowiedzJSON)
aplikacja = FastAPI(title="Doradca Finansowy",
                    default_response_class=OdpowiedzJSON,
                    lifespan=cykl_zycia)

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

    global _ZADAN_ZDROWIA
    _ZADAN_ZDROWIA += 1
    return {
        "stan": "dwa ekrany",
        "tras_w_spisie": len(spis.WSZYSTKIE),
        "zbudowanych": len(ZBUDOWANE),
        # Pomiar zycia procesu — patrz komentarz przy licznikach wyzej.
        "pid": os.getpid(),
        "uruchomien_cyklu_zycia": _URUCHOMIEN_CYKLU_ZYCIA,
        "zadan_zdrowia_w_tym_procesie": _ZADAN_ZDROWIA,
        # MILISEKUNDY JAKO LICZBA CALKOWITA, NIE SEKUNDY JAKO UŁAMEK.
        # Pierwsze podejscie oddawalo `round(..., 3)` i wdrozenie odpowiedzialo
        # kodem 500: `api/kwoty.py` ODMAWIA wypuszczenia liczby
        # zmiennoprzecinkowej z odpowiedzi HTTP — takze takiej, ktora nie jest
        # kwota. To zachowanie jest poprawne i zostaje; to pole sie do niego
        # dostosowuje. Zmierzone na wdrozeniu 2026-08-29.
        "milisekund_od_importu_modulu": int((time.time() - _CHWILA_IMPORTU) * 1000),
        # Region podaje PLATFORMA, my go nie zgadujemy. Pusty napis znaczy
        # „nie na platformie" (praca lokalna), nie „nieznany region".
        "region": os.environ.get("VERCEL_REGION", ""),
        "srodowisko_platformy": os.environ.get("VERCEL_ENV", ""),
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

#: NAZWA WYMAGANA PRZEZ PLATFORME, NIE WYBOR STYLU (W6, 2026-08-29).
#: Budowniczy Pythona Vercela szuka w `api/index.py` obiektu ASGI o nazwie
#: `app` i bez niego ODMAWIA BUDOWY — zmierzone na probniku:
#:   `Error: Found api/index.py but it does not define a top-level "app"
#:    FastAPI instance.`
#: Regula §4 konstytucji projektu („nazwy po polsku") ustepuje tu wymaganiu
#: platformy. To jest DRUGA NAZWA TEGO SAMEGO OBIEKTU, nie drugi obiekt —
#: przypisanie, nie `FastAPI()` drugi raz. Straznik:
#: `testy/test_wejscie_platformy.py::test_app_JEST_TYM_SAMYM_obiektem_co_aplikacja`.
app = aplikacja

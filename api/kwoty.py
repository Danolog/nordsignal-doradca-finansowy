# -*- coding: utf-8 -*-
"""JEDEN NOSNIK ZAMIANY `Decimal` NA JSON. Przeniesiony z poprzednika (Z5).

RYZYKO NR 1 CALEJ WARSTWY SIECIOWEJ, zmierzone u poprzednika 2026-08-27:

    klasa odpowiedzi robiaca `float(obj)` dla `Decimal`
        Decimal("99999999999999.99")  ->  b'{"k":99999999999999.98}'   grosz znikl, HTTP 200
        Decimal("8623.10")           ->  b'{"k":8623.1}'               koncowe zero znikло

Nie bylo ani bledu, ani ostrzezenia — bylo 200 i cicho zla liczba. Po drugiej
stronie granicy jest gorzej, bo tam liczby sie SUMUJE: pomiar na pieciu realnych
kwotach dal `Decimal` 4365.84, a `float` 4365.840000000001.

DLATEGO KONWERSJA JEST GORSZA NIZ BLAD. Blad widac natychmiast i w miejscu,
w ktorym powstal; cicho zla liczba wychodzi na ekran i wraca za trzy miesiace
jako „dlaczego to sie nie zgadza". `OdpowiedzJSON` odmawia obu: liczby
zmiennoprzecinkowej i golego `Decimal`.

CO SIE ZMIENILO WOBEC POPRZEDNIKA — i dlaczego.
Poprzednik pakowal kazda kwote w DWA pola: `{"wartosc": "274.06", "tekst":
"274,06 zl"}`. Napis produkowal silnik, bo przegladarka nie miala formatowac
pieniedzy. **W tym projekcie ta decyzja jest odwrocona i zapadla przede mna:**
`interfejs/lib/kontrakt.ts` niesie `Kwota = string` — samo `"274.06"` — a napis
sklada `interfejs/lib/kwota.ts`. Kontrakt jest wzorcem, wiec `kwota()` zwraca
sam napis. Skutek uboczny nazwany wprost w naglowku `testy/
test_kontrakt_dwa_nosniki.py`: formatowanie ma od tej decyzji DWA nosniki
i one juz sie roznia separatorem. Straznik przypina ten stan, zeby roznica
byla glosna.

CO PRZEZ TE ZMIANE PRZESTAJE DZIALAC (pozycja obowiazkowa, `CLAUDE.md` §3.11):
trasa, ktora zwroci goly `Decimal`, dostaje teraz WYJATEK zamiast napisu.
Poprzednia klasa odpowiedzi tego projektu (`api.index.OdpowiedzZKwotami`)
zamieniala go po cichu przez `format(x, "f")`. Zamiana byla poprawna
arytmetycznie, ale odbierala odpowiedz na pytanie „gdzie zapadlo zaokraglenie
do groszy" — a ono ma zapasc RAZ, tutaj. Cena: kazda trasa musi jawnie wolac
`kwoty.kwota(...)`. To jest cena zamierzona.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse

from silnik import pieniadz


def kwota(x: "Decimal | int | str | None") -> "str | None":
    """Kwota gotowa do przejscia przez granice: napis albo `None`.

    Ksztalt `Kwota` z `interfejs/lib/kontrakt.ts`: `"274.06"` — kropka
    dziesietna, bez separatorow tysiecy, bez waluty.

    `None` przechodzi NIETKNIETE. Stan „nie wiem" ma po drugiej stronie
    granicy zostac stanem „nie wiem", a nie zerem (regula D11) — kontrakt
    przewiduje `Kwota | null` wszedzie tam, gdzie brak wiedzy jest mozliwy.

    Zaokraglenie do groszy nastepuje TUTAJ i RAZ. `pieniadz.do_groszy`
    odmawia przyjecia liczby zmiennoprzecinkowej, wiec `kwota(0.1)` jest
    bledem glosnym, a nie cichym przyblizeniem.
    """
    if x is None:
        return None
    return str(pieniadz.do_groszy(x))


def policz_liscie(drzewo: Any, sciezka: str = "$") -> tuple[list[str], int]:
    """Obchod CALEGO drzewa odpowiedzi: sciezki do liczb zmiennoprzecinkowych
    ORAZ liczba odwiedzonych lisci.

    Druga wartosc nie jest ozdoba — to KONTROLA LICZNOSCI. Obchod, ktory
    nigdzie nie dotarl, zwraca te sama pusta liste co obchod drzewa bez ani
    jednej liczby zmiennoprzecinkowej, i przechodzi kazda asercje „czegos tam
    nie ma". Zmierzone uzasadnienie z jednego dnia u poprzednika (2026-08-26):
    trzem audytorom przeszukanie zwrocilo same zera, w tym dla wzorca, ktory
    wczesniej dawal trzy trafienia.

    OBCHOD IDZIE W GLAB, nie po pierwszym poziomie. Kwota ukryta w trzecim
    zagniezdzeniu (`$.ksiega[7].saldoPoDniu`) jest dokladnie tak samo zla jak
    kwota na wierzchu, a to wlasnie tam siedza wszystkie kwoty tego projektu:
    `DanePlynnosci.ksiega` i `.wykres` to listy obiektow.

    `Decimal` NIE jest tu zglaszany — jego odmowe zalatwia `json.dumps`,
    ktory nie umie go zserializowac i wola `default`.
    """
    znalezione: list[str] = []
    lisci = 0
    if isinstance(drzewo, dict):
        for klucz, wartosc in drzewo.items():
            pod, ile = policz_liscie(wartosc, f"{sciezka}.{klucz}")
            znalezione += pod
            lisci += ile
    elif isinstance(drzewo, (list, tuple)):
        for indeks, wartosc in enumerate(drzewo):
            pod, ile = policz_liscie(wartosc, f"{sciezka}[{indeks}]")
            znalezione += pod
            lisci += ile
    else:
        lisci = 1
        # `bool` jest podklasa `int`, ale nie liczba zmiennoprzecinkowa —
        # warunek jest waski celowo.
        if isinstance(drzewo, float):
            znalezione.append(sciezka)
    return znalezione, lisci


def sciezki_zmiennoprzecinkowe(drzewo: Any, sciezka: str = "$") -> list[str]:
    """Same sciezki, bez licznika — dla wolajacego, ktory liczbe lisci
    sprawdza osobno."""
    return policz_liscie(drzewo, sciezka)[0]


def _odrzuc(obj: Any):
    """Haczyk `json.dumps` na typie, ktorego nie umie zserializowac.

    NIE KONWERTUJE. `Decimal` trafia tu zawsze, bo `json` go nie zna —
    i wlasnie dlatego to jest dobre miejsce na odmowe.
    """
    if isinstance(obj, Decimal):
        raise TypeError(
            f"Decimal {obj} probuje przejsc przez granice HTTP jako liczba. "
            f"Kwoty przechodza WYLACZNIE napisem — opakuj ja w "
            f"api.kwoty.kwota(). Zaokraglenie do groszy ma zapasc raz, tam.")
    raise TypeError(
        f"Nie umiem zserializowac {type(obj).__name__} ({obj!r}) do JSON.")


class OdpowiedzJSON(JSONResponse):
    """Odpowiedz, ktora ODMAWIA wypuszczenia liczby zmiennoprzecinkowej.

    Stoi na `json` ze standardowej biblioteki, nie na szybszym serializatorze —
    bo szybkie serializatory zamieniaja `Decimal` na `float` z uprzejmosci,
    a uprzejmosc jest tu przeciwnikiem.

    Kazda trasa musi rozstrzygac sie na TE klase. Klasa odpowiedzi ustawia sie
    w konstruktorze `APIRouter`, nie przy `include_router` — zmierzone
    w FastAPI 0.141: przekazana przy dolaczaniu NIE DOCIERA do trasy.
    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        # Obchod PRZED serializacja: `json.dumps` serializuje `float` SAM,
        # bez pytania `default`, wiec haczyk na nieznanym typie by go nie
        # zobaczyl. Sciezka w komunikacie, bo „gdzies w odpowiedzi jest
        # liczba zmiennoprzecinkowa" to zgloszenie, ktorego nie da sie zamknac.
        zmiennoprzecinkowe, lisci = policz_liscie(content)
        if zmiennoprzecinkowe:
            raise TypeError(
                "Liczba zmiennoprzecinkowa w odpowiedzi HTTP: "
                + ", ".join(zmiennoprzecinkowe)
                + f" (przejrzano {lisci} lisci). Kwoty przechodza WYLACZNIE "
                  "napisem (api.kwoty.kwota); liczby calkowite sa dozwolone, "
                  "bo nie maja groszy do zgubienia.")
        return json.dumps(content, ensure_ascii=False, allow_nan=False,
                          default=_odrzuc,
                          separators=(",", ":")).encode("utf-8")

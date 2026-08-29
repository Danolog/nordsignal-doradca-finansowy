# -*- coding: utf-8 -*-
"""Straznicy WEJSCIA NA PLATFORME (W6, 2026-08-29).

CO PILNUJE TEN PLIK. Wdrozenie ma trzy miejsca, w ktorych bledna zmiana NIE
DAJE ZADNEGO SYGNALU — ani czerwonego testu, ani bledu budowy, tylko cicha
zmiane zachowania na produkcji:

1. **Nazwa obiektu ASGI.** Budowniczy Pythona Vercela szuka w `api/index.py`
   obiektu `app`. Zmierzone na probniku: bez niego budowa PADA komunikatem
   `Found api/index.py but it does not define a top-level "app" FastAPI
   instance.` Sama obecnosc nazwy nie wystarcza — `app = FastAPI()` obok
   `aplikacja = FastAPI()` tez by sie zbudowalo i wystawilo aplikacje BEZ
   ANI JEDNEJ TRASY, z kodem 404 na wszystkim. Straznik pyta wiec o
   TOZSAMOSC obiektu, nie o istnienie nazwy.

2. **Region funkcji.** Dane finansowe maja byc przetwarzane w UE (PRD §13 R7).
   Do W6 funkcje stawaly w `iad1` (Waszyngton), a baza stoi we Frankfurcie.
   Zmiana regionu z powrotem na amerykanski jest jedna linia w `vercel.json`
   i nie zepsulaby ani jednego testu.

3. **Adres silnika ma JEDEN nosnik** — zmienna `ADRES_SILNIKA`. Adres wpisany
   na sztywno w `next.config.mjs` bylby drugim zrodlem odpowiedzi „gdzie stoi
   silnik"; rozjazd miedzy nim a zmienna czytana przez
   `lib/dane/warstwa-sieciowa.ts` wyslalby CZESC zadan gdzie indziej niz
   reszte — bez zadnego sygnalu, bo obie sciezki odpowiadalyby kodem 200.

KONTROLA LICZNOSCI. Kazdy straznik nizej mowi najpierw, ILE rzeczy zobaczyl.
Sprawdzenie w pliku, ktorego nie ma, przechodzi na zielono nie sprawdziwszy
niczego — ta klasa awarii zdarzyla sie w tej sesji pieciokrotnie.
"""

from __future__ import annotations

import json
import pathlib

import pytest

KORZEN = pathlib.Path(__file__).resolve().parent.parent


# --- 1. nazwa wymagana przez platforme ------------------------------------

def test_app_JEST_TYM_SAMYM_obiektem_co_aplikacja():
    """`app` to DRUGA NAZWA, nie drugi obiekt.

    Mutacja czerwieniaca: zamien `app = aplikacja` na `app = FastAPI()`.
    """
    from api import index

    assert hasattr(index, "app"), (
        "W `api/index.py` nie ma obiektu `app`. Budowniczy Pythona Vercela "
        "odmowi budowy funkcji — zmierzone na probniku 2026-08-29.")
    assert index.app is index.aplikacja, (
        "`app` i `aplikacja` to DWA ROZNE obiekty. Platforma wystawi ten "
        "spod nazwy `app` — czyli aplikacje bez tras.")
    # Kontrola licznosci: obiekt musi ODPOWIADAC na trasy, ktore zbudowalismy.
    # Sciezek nie da sie odczytac z `app.routes` — FastAPI 0.141 opakowuje
    # dolaczone routery w `_IncludedRouter`, ktory nie ma pola `path`.
    # Pytamy wiec o to, co widzi klient: spis tras aplikacji (`openapi`).
    spis = index.app.openapi()["paths"]
    assert len(spis) >= len(index.ZBUDOWANE), (
        f"Obiekt `app` wystawia {len(spis)} sciezek, a zbudowanych tras jest "
        f"{len(index.ZBUDOWANE)}. Pomiar patrzy na pusta aplikacje.")
    for zbudowana in index.ZBUDOWANE:
        assert zbudowana in spis, f"Trasa {zbudowana} nie stoi na `app`."


# --- 2. konfiguracja platformy --------------------------------------------

@pytest.fixture(scope="module")
def konfiguracja_silnika() -> dict:
    plik = KORZEN / "vercel.json"
    assert plik.exists(), (
        "Nie ma `vercel.json` w korzeniu. Bez niego funkcja Pythona nie ma "
        "ani jawnego limitu czasu, ani wskazanego regionu.")
    return json.loads(plik.read_text(encoding="utf-8"))


def test_funkcja_silnika_MA_JAWNY_limit_czasu(konfiguracja_silnika):
    """Kazda funkcja ma jawny `maxDuration` — bez niego obowiazuje domyslny
    limit platformy, ktory zmienia sie bez naszego udzialu.

    Mutacja czerwieniaca: usun `maxDuration` z `vercel.json`.
    """
    funkcje = konfiguracja_silnika.get("functions") or {}
    assert funkcje, "Sekcja `functions` w `vercel.json` jest pusta."
    assert len(funkcje) >= 1, "Pomiar nie zobaczyl ani jednej funkcji."
    for nazwa, ustawienia in funkcje.items():
        assert "maxDuration" in ustawienia, (
            f"Funkcja {nazwa} nie ma jawnego `maxDuration`.")
        assert 1 <= ustawienia["maxDuration"] <= 300, (
            f"Funkcja {nazwa}: `maxDuration` poza zakresem planu.")


def test_funkcja_silnika_STOI_W_UNII(konfiguracja_silnika):
    """Dane finansowe przetwarzane w UE — PRD §13 R7.

    Mutacja czerwieniaca: zmien `regions` na `["iad1"]`.
    """
    regiony = konfiguracja_silnika.get("regions")
    assert regiony, "`vercel.json` nie wskazuje regionu — funkcja stanie tam, gdzie zechce platforma."
    DOZWOLONE = {"fra1", "arn1", "cdg1", "dub1"}  # Frankfurt, Sztokholm, Paryz, Dublin
    assert len(regiony) >= 1, "Pomiar nie zobaczyl ani jednego regionu."
    for r in regiony:
        assert r in DOZWOLONE, (
            f"Region {r} lezy poza UE. Baza stoi w `eu-central-1`, a dane sa "
            f"finansami osoby fizycznej.")


# --- 3. jeden nosnik adresu silnika ---------------------------------------

def test_konfiguracja_next_NIE_NIESIE_adresu_silnika_na_sztywno():
    """Adres silnika przychodzi ze zmiennej, nie z tresci pliku.

    Mutacja czerwieniaca: wpisz w `next.config.mjs`
    `const ADRES_SILNIKA = "https://nordsignal-doradca-silnik.vercel.app"`.
    """
    plik = KORZEN / "interfejs" / "next.config.mjs"
    assert plik.exists(), "Nie ma `interfejs/next.config.mjs`."
    tresc = plik.read_text(encoding="utf-8")
    assert len(tresc) > 200, "Pomiar czyta plik krotszy niz naglowek — cos jest nie tak."

    kod = "\n".join(w for w in tresc.splitlines()
                    if not w.lstrip().startswith("//"))
    assert len(kod.splitlines()) >= 10, (
        f"Po zdjeciu komentarzy zostalo {len(kod.splitlines())} linii — "
        f"pomiar patrzy na pusty plik.")

    assert "process.env.ADRES_SILNIKA" in kod, (
        "`next.config.mjs` nie czyta zmiennej ADRES_SILNIKA — przepisanie "
        "prowadzi wtedy do adresu, ktorego nikt nie wskazal.")

    # ZADNEGO literalu adresu wdrozenia w kodzie — takze w komunikacie bledu.
    #
    # PIERWSZA WERSJA TEGO STRAZNIKA BYLA ATRAPA i wykryla to mutacja, nie
    # czytanie (2026-08-29). Sprawdzala wylacznie linie zawierajace
    # `CEL_PRZEPISANIA`, `destination` albo `ADRES_SILNIKA =` — a mutacja
    # wpisujaca adres do OSOBNEJ stalej (`const _CEL = "https://...vercel.app"`)
    # i uzywajaca jej w przepisaniu przeszla na ZIELONO. Wzorzec listy linii
    # zaklada, ze znamy nazwe, ktorej ktos uzyje; nie znamy.
    #
    # Cena szczelnosci: adresu nie wolno podac takze jako przykladu w tresci
    # komunikatu. Komunikat mowi wiec „pelny adres wdrozenia (ze schematem
    # https)", bez konkretu — swiadoma wymiana konkretu na pewnosc.
    linie_z_adresem = [w for w in kod.splitlines() if ".vercel.app" in w]
    assert not linie_z_adresem, (
        f"Adres wdrozenia wpisany na sztywno w kodzie `next.config.mjs`: "
        f"{[w.strip() for w in linie_z_adresem]}. To DRUGI NOSNIK odpowiedzi "
        f"o tym, gdzie stoi silnik — pierwszym jest zmienna ADRES_SILNIKA.")

    # Adres petli zwrotnej wolno miec WYLACZNIE w galezi pracy lokalnej.
    linie_z_petla = [w for w in kod.splitlines() if "127.0.0.1" in w]
    assert len(linie_z_petla) == 1, (
        f"Adres petli zwrotnej wystepuje w {len(linie_z_petla)} liniach kodu; "
        f"oczekiwana dokladnie jedna (galaz pracy lokalnej).")

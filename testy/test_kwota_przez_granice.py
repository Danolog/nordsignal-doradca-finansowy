# -*- coding: utf-8 -*-
"""STRAZNIK WARTOSCI KWOTY NA GRANICY HTTP (W5, 2026-08-29).

ZNALEZISKO MUTACYJNE, NIE POMYSL. Granica HTTP miala do dzis straznika TYPU
(`test_trasy_dwa_ekrany.py::test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_
zmiennoprzecinkowej`) i nie miala straznika WARTOSCI. Roznica jest cala
tresc tego pliku:

  * mutacja M-B2-1 (`kwoty.kwota()` zwraca `float`) — typ sie zmienia,
    straznik typu pada natychmiast i podaje sciezki: **1 failed**;
  * mutacja M-B2-2 (`kwoty.kwota()` zwraca `str(float(...))`) — typ zostaje
    NAPISEM, wiec przez granice przechodzi kod **200** i cicho zla liczba:
    `"8623.10"` staje sie `"8623.1"`, `"-500.00"` staje sie `"-500.0"`.
    Pomiar 2026-08-29: **1 failed, 1007 passed**. Jedyna czerwien padla
    w `test_kotwica_PRZYJMUJE_kwote_ujemna`, czyli w tescie o kwocie ujemnej,
    ktory zlapal to PRZYPADKIEM — jednym napisem wpisanym na sztywno.

DLACZEGO TO JEST TA SAMA AWARIA, KTORA OPISUJE NAGLOWEK `api/kwoty.py`.
Tamten naglowek nazywa ja wprost: „`Decimal("8623.10")` -> `8623.1`, koncowe
zero znikло, HTTP 200". Straznik jednostkowy `test_kontrakt_dwa_nosniki.py::
test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ` tego nie lapie, bo zaden
z jego trzech przykladow nie ma KONCOWEGO ZERA — a to wlasnie ono znika.
Przyklad z zerem stoi wiec nizej.

CO TEN PLIK PILNUJE, JEDNYM ZDANIEM: kazdy napis, ktory przechodzi granice
jako kwota, ma DOKLADNIE dwa miejsca po kropce — bo tyle ma grosz.

CZEGO NIE PILNUJE, zeby cisza nie uchodzila za zgode:
  * czy kwota jest POPRAWNA — to jest praca straznikow silnika i tras;
  * napisow, ktore kwotami nie sa (daty, identyfikatory) — rozpoznanie idzie
    po ksztalcie „cyfry, kropka, cyfry", wiec `2026-10-06` w nie nie wpada.
"""
from __future__ import annotations

import re
from decimal import Decimal

import pytest

from api import kwoty
from testy import test_trasy_dwa_ekrany as trasy

#: Fikstura klienta ma JEDEN nosnik — ten obok. Powtorzenie jej tutaj byloby
#: druga baza, drugimi nastawami Darka i cicha okazja do rozjazdu.
klient = trasy.klient

#: Ksztalt „napis wygladajacy na liczbe dziesietna". Szeroki celowo: ma
#: zlapac takze `8623.1`, czyli WADE, a nie tylko poprawna postac.
WYGLADA_NA_KWOTE = re.compile(r"^-?\d+\.\d*$")

#: Ksztalt `Kwota` z `interfejs/lib/kontrakt.ts`: kropka i DWA miejsca.
KWOTA_POPRAWNA = re.compile(r"^-?\d+\.\d\d$")

#: Ile kwot-napisow niesie szesc odpowiedzi razem — pomiar 2026-08-29: 139.
#: Prog nizej zostawia miejsce na zmiane ksztaltu ekranu i nadal czerwieni
#: sie, gdy obchod przestanie gdziekolwiek docierac.
NAJMNIEJ_KWOT = 120


def _kwoty_napisami(drzewo, sciezka="$", zebrane=None):
    """Wszystkie liscie-napisy o ksztalcie liczby dziesietnej, ze sciezkami.

    Sciezka jest czescia wyniku, nie ozdoba: „gdzies w odpowiedzi jest zla
    kwota" to zgloszenie, ktorego nie da sie zamknac.
    """
    zebrane = [] if zebrane is None else zebrane
    if isinstance(drzewo, dict):
        for klucz, wartosc in drzewo.items():
            _kwoty_napisami(wartosc, f"{sciezka}.{klucz}", zebrane)
    elif isinstance(drzewo, (list, tuple)):
        for indeks, wartosc in enumerate(drzewo):
            _kwoty_napisami(wartosc, f"{sciezka}[{indeks}]", zebrane)
    elif isinstance(drzewo, str) and WYGLADA_NA_KWOTE.match(drzewo):
        zebrane.append((sciezka, drzewo))
    return zebrane


def test_KAZDA_kwota_przechodzi_granice_z_DWOMA_miejscami_po_kropce(klient):
    """Straznik WARTOSCI — ten, ktorego brakowalo.

    Pada na mutacji M-B2-2, ktora straznik typu przepuszcza z kodem 200.
    """
    wszystkie = []
    for nazwa, odpowiedz in trasy._odpowiedzi(klient).items():
        assert odpowiedz.status_code == 200, nazwa
        znalezione = _kwoty_napisami(odpowiedz.json())
        zle = [(s, w) for s, w in znalezione if not KWOTA_POPRAWNA.match(w)]
        assert zle == [], (
            f"{nazwa}: kwoty bez dwoch miejsc po kropce {zle}. Grosz ma dwa "
            f"miejsca; napis `8623.1` to ta sama utrata, co liczba "
            f"zmiennoprzecinkowa — tyle ze przechodzi z kodem 200.")
        wszystkie += znalezione
    assert len(wszystkie) >= NAJMNIEJ_KWOT, (
        f"obchod znalazl {len(wszystkie)} kwot-napisow, prog {NAJMNIEJ_KWOT}. "
        f"Sprawdzenie, do ktorego nic nie dociera, melduje sukces.")


def test_obchod_NAPRAWDE_lapie_kwote_bez_grosza(klient):
    """Kontrola dwustronna. Bez niej `_kwoty_napisami` moglby zwracac pusta
    liste zawsze, a szesc asercji „nie ma zlych kwot" bylo by zielone przy
    calkowicie zepsutym przyrzadzie."""
    dane = klient.get(f"/api/plynnosc?dzis={trasy.DZIS}").json()
    dane["ksiega"][0]["saldoPoDniu"] = "8623.1"
    dane["stanKonta"] = "-500.0"
    znalezione = _kwoty_napisami(dane)
    zle = sorted(s for s, w in znalezione if not KWOTA_POPRAWNA.match(w))
    assert zle == ["$.ksiega[0].saldoPoDniu", "$.stanKonta"], zle


def test_kwota_ZACHOWUJE_koncowe_zero_bo_to_ONO_znika(klient):
    """Przyklad, ktorego brakowalo straznikowi jednostkowemu.

    `test_kontrakt_dwa_nosniki.py::test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ`
    ma trzy przyklady i ZADEN nie ma koncowego zera — a naglowek `api/kwoty.py`
    opisuje wlasnie ta utrate jako zmierzona awarie poprzednika.
    """
    assert kwoty.kwota(Decimal("8623.10")) == "8623.10"
    assert kwoty.kwota(Decimal("-500.00")) == "-500.00"
    assert kwoty.kwota(Decimal("2610")) == "2610.00", (
        "kwota calkowita tez ma grosze — po drugiej stronie granicy jest "
        "`Kwota = string` o stalym ksztalcie, nie liczba")


@pytest.mark.parametrize("wartosc", ["8623.1", "-500.0", "0.", "12345.678"])
def test_ksztalt_poprawnej_kwoty_ODRZUCA_to_co_ma_odrzucac(wartosc):
    """Kontrola samego wzorca. Wzorzec dopuszczajacy wszystko dalby
    straznika, ktory nigdy sie nie czerwieni."""
    assert WYGLADA_NA_KWOTE.match(wartosc), (
        f"{wartosc!r} nie zostalo nawet rozpoznane jako kwota — straznik "
        f"wyzej by jej nie obejrzal")
    assert not KWOTA_POPRAWNA.match(wartosc)

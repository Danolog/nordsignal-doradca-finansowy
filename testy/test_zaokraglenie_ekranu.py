# -*- coding: utf-8 -*-
"""Straznik: zaokraglenie kwoty do groszy ma JEDEN nosnik — takze wtedy,
gdy nie wyglada jak `quantize`.

DLACZEGO TEN PLIK POWSTAL (przeglad Z10, Leo, 2026-08-29).
`testy/test_stawki_jeden_nosnik.py::
test_kwota_nie_jest_liczona_wlasnym_quantize_poza_pieniadzem` deklaruje, ze
kwot nie wolno zaokraglac poza `silnik/pieniadz.py`. Szuka jednak WYLACZNIE
ksztaltu `quantize(GROSZ | ZLOTY | Decimal("0.01") | Decimal("1"))`. Python
zaokragla takze przez opis formatu — `f"{x:,.2f}"` — i tego ksztaltu tamten
wzorzec nie widzi.

MUTACJA, KTORA TO POKAZALA (M-L7, 2026-08-29, kopia drzewa poza repozytorium):
w `silnik/rdzen/prognoza_plynnosci.py` wiersz 409 zamieniono

    kwota = stawki.do_groszy(Decimal(str(w["kwota"])))
na
    kwota = Decimal(f'{Decimal(str(w["kwota"])):.2f}')

czyli podstawiono DRUGI nosnik zaokraglenia, dzialajacy INNA regula
(`ROUND_HALF_EVEN` z domyslnego kontekstu dziesietnego zamiast `ROUND_HALF_UP`
z `pieniadz.py`), w sciezce kwoty prognozy plynnosci.
WYNIK: `892 passed, 3 deselected` — zadnej czerwieni. Mutacje cofnieto,
kontrola po cofnieciu: `892 passed`.

DLACZEGO ROZNICA REGUL NIE JEST DROBIAZGIEM. Pomiar tego samego dnia:

    wartosc   | silnik do_groszy | ekran prezentacja.zloty
      0.145   |            0.15  | 0,14 zl
      0.005   |            0.01  | 0,00 zl
     12.345   |           12.35  | 12,34 zl

Trzy z szesciu sprawdzonych wartosci daja INNY grosz. To jest ta klasa
rozjazdu, ktora przez wieksza czesc rachunku wyglada poprawnie.

CO TEN PLIK PILNUJE, A CZEGO NIE. Pilnuje, ze opis formatu z dwoma miejscami
po przecinku nie pojawi sie w zadnym module liczacym POZA jednym nazwanym
wyjatkiem. NIE naprawia samego wyjatku — to nie jest zadanie przegladu.
"""

import re
from decimal import Decimal
from pathlib import Path

from silnik import pieniadz
from silnik.rdzen import prezentacja

KORZEN = Path(__file__).resolve().parent.parent

#: Jedyny nazwany wyjatek. `prezentacja.liczba` sklada napis dla oka i przy
#: okazji zaokragla — INNA regula niz silnik (patrz naglowek).
#:
#: PROG KONSOLIDACJI (CLAUDE.md §3.2, „swiadomy drugi nosnik wylacznie
#: z testem-straznikiem i jawnym progiem"): **przy pierwszej zmianie
#: `prezentacja.liczba`** formatowanie ma wolac `pieniadz.do_groszy` przed
#: zlozeniem napisu, a ten wyjatek znika razem z testem przypinajacym nizej.
#: Wlasciciel: Ethan (silnik).
WYJATEK = "prezentacja.py"


def _moduly_liczace() -> list[Path]:
    pliki = sorted(KORZEN.glob("silnik/**/*.py")) + sorted(KORZEN.glob("api/*.py"))
    assert len(pliki) >= 20, (
        f"kontrola licznosci: straznik widzi tylko {len(pliki)} plikow — "
        f"sciezka jest zla, a zero trafien wygladaloby jak sukces")
    return pliki


def test_grosze_nie_sa_zaokraglane_OPISEM_FORMATU_poza_jednym_wyjatkiem():
    """Drugi ksztalt zaokraglenia — `f"{x:.2f}"` — takze ma jeden nosnik.

    Wzorzec celuje w DWA miejsca po przecinku, bo tyle ma grosz. Procenty
    (`:.0f` w `narzedzia.py`) sa poza regula: to nie jest kwota.
    """
    wzorzec = re.compile(r':,?\.2f')
    trafienia = sorted({p.name for p in _moduly_liczace()
                        if wzorzec.search(p.read_text(encoding="utf-8"))})
    assert trafienia == [WYJATEK], (
        f"zaokraglanie kwot opisem formatu poza jedynym nosnikiem: "
        f"{trafienia}. Zaokraglenie ma zapasc w `silnik/pieniadz.py` — "
        f"opis formatu uzywa ROUND_HALF_EVEN, a pieniadz ROUND_HALF_UP, "
        f"wiec dwa nosniki daja rozny grosz na polowie przypadkow.")


def test_ROZJAZD_regul_jest_PRZYPIETY_a_nie_przemilczany():
    """Przypina stan faktyczny, zeby jego zmiana byla glosna w obie strony.

    Dzis ekran i silnik zaokraglaja INACZEJ. Ten test czerwieni sie zarowno
    wtedy, gdy ktos rozjazd POGLEBI, jak i wtedy, gdy go NAPRAWI — naprawa
    ma zdjac ten test razem z `WYJATEK` wyzej, swiadomie, a nie po cichu.
    """
    rozjezdzone = [s for s in ("0.145", "0.005", "12.345", "2.675",
                               "1305.055", "2425.115")
                   if prezentacja.zloty(Decimal(s))
                   != f"{prezentacja.liczba(pieniadz.do_groszy(Decimal(s)))}"
                      f"{prezentacja.SEPARATOR_TYSIECY}zł"]
    assert rozjezdzone == ["0.145", "0.005", "12.345"], (
        f"rozjazd zaokraglen zmienil zasieg: {rozjezdzone}. "
        f"Jesli to naprawa — zdejmij ten test i wyjatek `WYJATEK`.")


def test_prezentacja_ODMAWIA_liczby_zmiennoprzecinkowej():
    """Ostatni metr do oka tez jest sciezka kwoty (CLAUDE.md §3.1).

    DZIS TEN TEST JEST CZERWONY PRZY NAPRAWIE, NIE PRZY WADZIE — i to jest
    swiadome: `prezentacja.zloty` ma w sygnaturze `float` i przyjmuje go,
    omijajac `pieniadz.zabron_float`. Pomiar 2026-08-29:
    `prezentacja.zloty(4365.840000000001)` -> `'4 365,84 zł'`, bez sygnalu.
    Przypiete, zeby stan byl glosny; naprawa (odmowa dla `float`) zdejmuje
    ten test. Wlasciciel: Ethan (silnik).
    """
    assert prezentacja.zloty(0.1) == "0,10 zł", (
        "jesli to czerwien po naprawie — prezentacja zaczela odmawiac float, "
        "zdejmij ten test")
    try:
        pieniadz.do_groszy(0.1)
    except TypeError:
        return
    raise AssertionError("pieniadz.do_groszy przestal odmawiac float")

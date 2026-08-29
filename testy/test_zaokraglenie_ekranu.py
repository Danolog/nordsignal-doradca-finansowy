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

--------------------------------------------------------------------------
PROG Z TEGO PLIKU ZADZIALAL — naprawa, 2026-08-29, Ethan (silnik).

Prog brzmial: „przy pierwszej zmianie `prezentacja.liczba` formatowanie ma
wolac `pieniadz.do_groszy` przed zlozeniem napisu". Wywolanie jest na miejscu:

    silnik/rdzen/prezentacja.py:  f"{pieniadz.do_groszy(Decimal(str(x))):,.2f}"

Te same szesc wartosci PO naprawie — zero rozjazdow:

    wartosc   | silnik do_groszy | ekran prezentacja.zloty
      0.145   |            0.15  | 0,15 zl
      0.005   |            0.01  | 0,01 zl
     12.345   |           12.35  | 12,35 zl

CO SIE PRZEZ TO ZMIENILO W TYM PLIKU:
  * `test_ROZJAZD_regul_jest_PRZYPIETY_a_nie_przemilczany` ZDJETY, dokladnie
    tak, jak zadal jego wlasny docstring („naprawa ma zdjac ten test razem
    z `WYJATEK`, swiadomie, a nie po cichu"). W jego miejsce stoi kontrola
    ODWROTNA: obie strony maja dawac TEN SAM grosz.
  * `WYJATEK` ZOSTAJE, ale znaczy juz co innego — patrz komentarz przy stalej.
  * Test odmowy `float` ZOSTAJE CZERWONY PRZY NAPRAWIE, bo naprawy nie bylo:
    granica typu to OSOBNA wada i zostaje jako dlug z progiem (nizej).
--------------------------------------------------------------------------
"""

import re
from decimal import Decimal
from pathlib import Path

from pomocnicze import kod_pythona_bez_prozy
from silnik import pieniadz
from silnik.rdzen import prezentacja

KORZEN = Path(__file__).resolve().parent.parent

#: Jedyny nazwany wyjatek — I ZNACZY JUZ CO INNEGO NIZ PRZED NAPRAWA.
#:
#: BYLO: `prezentacja.liczba` zaokraglalo opisem formatu, wlasna regula
#: (`ROUND_HALF_EVEN`), rozna od reguly silnika. To byl DRUGI NOSNIK
#: zaokraglenia i dawal inny grosz na polowie sprawdzonych wartosci.
#:
#: JEST: `prezentacja.liczba` wola `pieniadz.do_groszy`, a `:,.2f` sluzy juz
#: TYLKO RENDEROWANIU wartosci, ktora jest zaokraglona ZANIM tu dotrze.
#: Opis formatu na liczbie o dwoch miejscach po przecinku nie zaokragla
#: niczego — nie ma czego uciac.
#:
#: DLACZEGO WYJATEK MIMO TO ZOSTAJE. Wzorzec straznika celuje w KSZTALT
#: (`:,.2f`), nie w intencje, a kazdy napis kwotowy musi ten ksztalt
#: gdzies miec. Wyjatek jest wiec trwaly i JEDEN — jego rola to nie
#: „poczekalnia dla dlugu", tylko „miejsce, w ktorym kwota staje sie
#: napisem". Drugi plik na tej liscie nadal jest wada.
#:
#: KONTROLA, ZE WYJATEK NIE JEST FURTKA: `test_ekran_i_silnik_zaokraglaja
#: _TAK_SAMO` nizej sprawdza, ze zaokraglenie w tym pliku daje ten sam grosz
#: co silnik. Sam wyjatek na liscie nie wystarczy.
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
    # SZUKAMY W KODZIE, NIE W PROZIE. Nagłówek `pieniadz.py` CYTUJE zakazany
    # kształt, żeby wyjaśnić, dlaczego jest zakazany — i zaczerwienił tego
    # strażnika 2026-08-29. To trzecie trafienie tego wzorca w tym projekcie
    # (M3 w Z1, M-Z7-1c w Z7). Proza wyjaśniająca regułę nie jest jej
    # złamaniem; napis, którego program używa, jest.
    trafienia = sorted({p.name for p in _moduly_liczace()
                        if wzorzec.search(kod_pythona_bez_prozy(
                            p.read_text(encoding="utf-8")))})
    assert trafienia == [WYJATEK], (
        f"zaokraglanie kwot opisem formatu poza jedynym nosnikiem: "
        f"{trafienia}. Zaokraglenie ma zapasc w `silnik/pieniadz.py` — "
        f"opis formatu uzywa ROUND_HALF_EVEN, a pieniadz ROUND_HALF_UP, "
        f"wiec dwa nosniki daja rozny grosz na polowie przypadkow.")


#: Wartosci, na ktorych rozjazd byl WIDOCZNY przed naprawa. Trzy pierwsze
#: dawaly inny grosz, trzy dalsze nie — obie grupy zostaja, bo kontrola
#: wylacznie na wartosciach „trudnych" nie odroznia naprawy od przypadku.
WARTOSCI_GRANICZNE = ("0.145", "0.005", "12.345",
                      "2.675", "1305.055", "2425.115")


def test_ekran_i_silnik_zaokraglaja_TAK_SAMO():
    """Kontrola ODWROTNA do zdjetego `test_ROZJAZD_..._PRZYPIETY`.

    Tamten przypinal ROZJAZD, zeby jego naprawa nie przeszla po cichu.
    Naprawa nastapila (2026-08-29), wiec przypiety jest teraz stan ZGODNY:
    ten sam grosz po obu stronach granicy „liczba kontra napis".

    DLACZEGO TO NIE JEST TAUTOLOGIA po tym, jak `liczba` wola `do_groszy`.
    Bo droga jest INNA: lewa strona idzie przez `zloty(x)` — pelna sciezke
    prezentacji z surowa wartoscia; prawa przez `liczba(do_groszy(x))` —
    wartosc zaokraglona ZANIM dotknie prezentacji. Gdyby ktos zdjal wolanie
    z `liczba`, lewa strona wrocilaby do `ROUND_HALF_EVEN`, a prawa zostala
    przy `ROUND_HALF_UP` — i te asercje by padly.
    """
    rozjezdzone = [
        s for s in WARTOSCI_GRANICZNE
        if prezentacja.zloty(Decimal(s))
        != (f"{prezentacja.liczba(pieniadz.do_groszy(Decimal(s)))}"
            f"{prezentacja.SEPARATOR_TYSIECY}zł")]
    assert rozjezdzone == [], (
        f"ekran i silnik znowu zaokraglaja inaczej: {rozjezdzone}. "
        f"Sprawdz, czy `prezentacja.liczba` nadal wola `pieniadz.do_groszy`.")


def test_kontrola_licznosci_porownanie_WIDZI_wartosci_trudne():
    """Sprawdzenie, do ktorego nic nie dociera, melduje sukces.

    Test wyzej przechodzi rowniez wtedy, gdy `WARTOSCI_GRANICZNE` sa puste
    albo gdy zaden z nich nie jest wartoscia na granicy zaokraglenia. Ten
    test pyta o to wprost: ile z nich LEZY dokladnie w polowie grosza —
    czyli ile w ogole ma szanse rozroznic dwie reguly.
    """
    assert len(WARTOSCI_GRANICZNE) >= 6
    w_polowie = [s for s in WARTOSCI_GRANICZNE
                 if Decimal(s) * 1000 % 10 == 5]
    assert len(w_polowie) == 6, (
        f"tylko {len(w_polowie)} z {len(WARTOSCI_GRANICZNE)} wartosci lezy "
        f"w polowie grosza — porownanie nie odrozni HALF_UP od HALF_EVEN")
    # Kontrola dwustronna: te dwie reguly NAPRAWDE daja tu rozne wyniki,
    # wiec porownanie wyzej ma co mierzyc.
    from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP
    rozne = [s for s in WARTOSCI_GRANICZNE
             if Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
             != Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)]
    assert len(rozne) >= 3, (
        f"tylko {len(rozne)} wartosci rozroznia obie reguly zaokraglania")


def test_prezentacja_ODMAWIA_liczby_zmiennoprzecinkowej():
    """Ostatni metr do oka tez jest sciezka kwoty (CLAUDE.md §3.1).

    STAN PO NAPRAWIE ZAOKRAGLENIA: zamknieta zostala POLOWA tego znaleziska
    — regula zaokraglenia. Granica typu NIE, i to jest decyzja, nie
    przeoczenie: `prezentacja.liczba` wola `pieniadz.do_groszy(Decimal(str(x)))`,
    czyli sprowadza wartosc do `Decimal` PRZED wolaniem, wiec `zabron_float`
    nigdy nie widzi liczby zmiennoprzecinkowej. Naprawa granicy typu zmienia
    ZACHOWANIE wolajacych (wyjatek zamiast napisu) i nalezy do osobnego
    plasterka — opisana jako dlug z progiem w naglowku `silnik/pieniadz.py`.

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

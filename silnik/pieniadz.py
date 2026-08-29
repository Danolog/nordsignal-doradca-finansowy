# -*- coding: utf-8 -*-
"""JEDEN NOSNIK ARYTMETYKI PIENIEZNEJ — z dwoma nazwanymi granicami.

Zaokraglenie jest REGULA PRAWNA, a nie szczegolem technicznym, i rozne kwoty
zaokragla sie roznie. Dlatego regula ma jeden nosnik: ten plik.

SPROSTOWANIE, 2026-08-29 (przeglad Z10, Leo). Do tego dnia naglowek zaczynal
sie zdaniem: *„Kazde zaokraglenie w tej aplikacji przechodzi przez ten plik."*
**To bylo nieprawda i zdanie zostalo usuniete.** Zaokraglenie mialo wtedy DWA
nosniki o ROZNEJ REGULE:

    silnik/pieniadz.py     -> ROUND_HALF_UP     (jawnie, tutaj)
    prezentacja.liczba     -> ROUND_HALF_EVEN   (ukryte w `f"{x:,.2f}"`)

Zmierzone tego samego dnia — trzy z szesciu wartosci dawaly INNY GROSZ:

    0.145  -> silnik 0,15   ekran 0,14 zl
    0.005  -> silnik 0,01   ekran 0,00 zl
   12.345  -> silnik 12,35  ekran 12,34 zl

W aplikacji podatkowej znaczylo to, ze **ekran i przelew mogly sie roznic
groszem**, a roznica byla niewidoczna, bo obie liczby wygladaly poprawnie.
NAPRAWIONE tego samego dnia: `prezentacja.liczba` wola `do_groszy` przed
zlozeniem napisu. Straznik: `testy/test_zaokraglenie_ekranu.py`.

CZEGO TEN PLIK NADAL NIE PILNUJE — dwa dlugi z progiem, nie obietnice.

DLUG 1: GRANICA TYPU NIE SIEGA OSTATNIEGO METRA DO OKA.
`prezentacja.zloty` i `prezentacja.liczba` maja `float` w sygnaturze
i przyjmuja go: `zloty(4365.840000000001)` -> `'4 365,84 zl'`, BEZ SYGNALU.
`zabron_float` nigdy tego nie widzi, bo prezentacja sprowadza wartosc przez
`Decimal(str(x))` zanim zawola `do_groszy`.
  * WIELKOSC SKUTKU: liczba zmiennoprzecinkowa dojezdza do oka wygladajac
    poprawnie. Sam napis jest dzis dobry — `str(float)` odtwarza wartosc
    z dokladnoscia, ktora po zaokragleniu do groszy daje ten sam wynik.
    Ryzyko nie lezy w napisie, tylko w tym, ze DROGA jest otwarta: kwota
    policzona `float`-em przechodzi cala aplikacje bez ani jednego sygnalu.
  * PROG: przy pierwszym `float` w sygnaturze funkcji SILNIKA (nie
    prezentacji) albo przy pierwszym zgloszeniu rozjazdu grosza na ekranie —
    `prezentacja` przestaje przyjmowac `float`, a `Decimal(str(x))` znika
    razem z tym. Zmiana lamie wolajacych, wiec jest osobnym plasterkiem.
  * Straznik przypinajacy stan: `test_prezentacja_ODMAWIA_liczby_
    zmiennoprzecinkowej` — czerwieni sie PRZY NAPRAWIE, nie przy wadzie.

DLUG 2: ZAPLATY PODATKOWE NIE MAJA OKRESU (znalezisko Leo, Z10).
`podatki.zaplaty_podatkowe` sumuje wpisy kategorii „Podatki i ZUS" ze
WSZYSTKICH LAT przeciw zobowiazaniu JEDNEGO roku. Kolumna, ktora to zamyka —
`wpisy_budzetu.zrodlo` z PRD rozdz. 6.3 — NIE ISTNIEJE w schemacie; tak samo
`kategorie.niezbedna` i `przychody_jdg.data_obowiazku_vat`.
  * WIELKOSC SKUTKU DZIS: **0,00 zl** — baza wzorcowa nie ma ani jednego
    wpisu w kategorii „Podatki i ZUS", wiec suma jest pusta.
  * WIELKOSC SKUTKU PO PIERWSZYM WPISIE: pelna kwota tego wpisu, odjeta od
    rezerwy niezaleznie od roku, ktorego dotyczyla. Kierunek bledu jest
    NIEKORZYSTNY: rezerwa wychodzi ZANIZONA, czyli obraz poprawia sie
    wzgledem prawdy — a to jest ten kierunek, ktorego nie widac.
  * PROG: **pierwszy wpis w kategorii „Podatki i ZUS"** albo migracja
    schematu dokladajaca `wpisy_budzetu.zrodlo` — co nastapi pierwsze.
    Wtedy filtr okresu wchodzi razem z kolumna, nie osobno.

DLUG 3: REJESTR STAWEK NIE MA KONSUMENTA (znalezisko Leo, Z10).
Opisany w `docs/PRD.md` rozdz. 5 i 7 — tu tylko odeslanie, zeby nie powstal
drugi nosnik tego samego znaleziska.

DLACZEGO KONTEKST DZIESIETNY NIE JEST USTAWIANY GLOBALNIE. Zaokraglenie ma
byc widoczne w miejscu, w ktorym zapada. Ustawienie go raz w konfiguracji
modulu sprawia, ze pol roku pozniej nikt nie wie, gdzie liczba stracila
grosze.

DLACZEGO NIE `float`. Liczba zmiennoprzecinkowa nie potrafi zapisac 1305.05.
Poprzednia aplikacja miala zmierzona awarie dokladnie tego typu: warstwa
sieciowa zamieniala `Decimal` na `float`, gubila grosze i ZWRACALA 200 —
czyli meldowala sukces. `zabron_float` istnieje po to, zeby ta awaria byla
halasliwa.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

GROSZ = Decimal("0.01")
ZLOTY = Decimal("1")


def do_groszy(x: Decimal | int | str) -> Decimal:
    """Skladki, VAT, kwoty netto, salda — dwa miejsca po przecinku."""
    return zabron_float(x).quantize(GROSZ, rounding=ROUND_HALF_UP)


def do_zlotych(x: Decimal | int | str) -> Decimal:
    """Podatek zaokragla sie do PELNYCH ZLOTYCH — art. 63 Ordynacji podatkowej.

    To jedyna kwota w aplikacji, ktora tak sie zaokragla. Uzycie tego dla
    czegokolwiek innego niz podatek jest bledem.
    """
    return zabron_float(x).quantize(ZLOTY, rounding=ROUND_HALF_UP)


def zabron_float(x) -> Decimal:
    """Zamiana na `Decimal` z ODMOWA dla liczby zmiennoprzecinkowej.

    Nie konwertuje `float` po cichu, bo `Decimal(0.1)` daje
    0.1000000000000000055511151231257827021181583404541015625 — wartosc,
    ktora przez wieksza czesc rachunku wyglada poprawnie i psuje sie dopiero
    na sumie kilkuset wpisow.
    """
    if isinstance(x, float):
        raise TypeError(
            f"liczba zmiennoprzecinkowa w sciezce kwoty: {x!r}. "
            "Kwoty ida jako Decimal albo napis — nigdy jako float."
        )
    return x if isinstance(x, Decimal) else Decimal(str(x))


def suma(kwoty) -> Decimal:
    """Suma bez zaokraglania po drodze.

    Zaokraglenie zapada u WYWOLUJACEGO, bo tylko on wie, czy sumuje skladniki
    zaokraglane osobno (skladki ZUS), czy wartosci, ktore wolno zaokraglic
    dopiero na koncu.
    """
    return sum((zabron_float(k) for k in kwoty), Decimal("0"))


def kazdy_osobno(kwoty) -> Decimal:
    """Suma skladnikow zaokraglanych OSOBNO — tak nalicza ZUS.

    Zmierzone na stawkach 2026 przy podstawie 5 652,00 zl:
        osobno            -> 1 926,76 zl
        razem, na koncu   -> 1 926,77 zl
    Grosz roznicy, ale w przelewie do urzedu. Straznik:
    `testy/test_rejestr_stawek.py::test_skladki_zaokraglane_OSOBNO_daja_1926_76`.
    """
    return sum((do_groszy(k) for k in kwoty), Decimal("0"))

# -*- coding: utf-8 -*-
"""JEDEN NOSNIK ARYTMETYKI PIENIEZNEJ.

Kazde zaokraglenie w tej aplikacji przechodzi przez ten plik. Nie dlatego, ze
tak jest schludniej — dlatego, ze zaokraglenie jest REGULA PRAWNA, a nie
szczegolem technicznym, i rozne kwoty zaokragla sie roznie.

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

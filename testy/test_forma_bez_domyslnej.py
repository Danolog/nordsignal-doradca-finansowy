"""Straznik: forma opodatkowania NIE MA wartosci domyslnej (E5, 2026-08-28).

DLACZEGO TEN PLIK ISTNIEJE. Do 2026-08-28 ryczalt byl wartoscia domyslna
w trzech miejscach `rdzen/podatki.py`:

    skladki_zus_za_miesiace(..., forma: str = "RYCZALT")
    RezerwaPodatkowa.forma = "RYCZALT" / .nazwa_podatku = "Ryczalt"
    rezerwa_na_podatki(..., forma: str = "RYCZALT")

Wolajacy, ktory formy nie podal, dostawal liczbe ryczaltowa — cicho
i wiarygodnie. Darek jest na skali od 2026 (`docs/plan-forma-opodatkowania.md`
v0.5) i musial to powiedziec TRZY RAZY jednego dnia (09:44, 15:03, 17:34),
bo napis „ryczalt" wracal. To byl defekt w kodzie, nie w pamieci.

DLACZEGO NIE ZAMIENILISMY DOMYSLNEJ NA `"SKALA"`. To ten sam blad z inna
wartoscia: nadal zgadywanie za wolajacego, tylko w druga strone. Forma jest
USTAWIENIEM uzytkownika i moze sie zmienic — jedyna poprawna domyslna to
BRAK domyslnej, zeby pominiecie bylo bledem w chwili wywolania.

CZEGO TE TESTY NIE PILNUJA — jawnie (CLAUDE.md sekcja 8, v1.17). Nie pilnuja
czterech miejsc, w ktorych ryczalt jest ZASZYTY NA SZTYWNO, a nie domyslny:
`pulpit/jdg.py:153` (formularz faktury zawsze liczy `policz_ryczalt`),
`rdzen/narzedzia.py:159` (narzedzie doradcy — j.w.), `rdzen/doradca.py:51`
(instrukcja systemowa twierdzi, ze uzytkownik jest na ryczalcie) oraz kolumna
„Ryczalt" w tabeli faktur (`pulpit/jdg.py:59`). To osobny plasterek z wlasnym
strazikiem — tutaj sa wymienione, zeby nikt nie uznal tego pliku za dowod,
ze ryczalt zniknal z aplikacji.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import podatki

FAKTURA = pd.DataFrame([{
    "data": "2026-10-05",
    "kwota_netto": Decimal("11200.00"),
    "kwota_vat": Decimal("2576.00"),
    "zaplacony_zus": Decimal("2425.11"),
    "zysk_netto": Decimal("8007.89"),
}])
PUSTO = pd.DataFrame()
OD = date(2026, 9, 1)
DO = date(2026, 11, 30)


def _rezerwa(forma: str, stawka=None):
    return podatki.rezerwa_na_podatki(
        FAKTURA, PUSTO, PUSTO, dzialalnosc_od=OD, dzis=DO,
        forma=forma, stawka_ryczaltu=stawka)


# --- SEDNO: pominiecie formy jest bledem WYWOLANIA, nie zla liczba -------

def test_rezerwa_na_podatki_ODMAWIA_gdy_nikt_nie_podal_formy():
    """Mutacja czerwieniaca: przywroc `forma: str = "RYCZALT"` w sygnaturze
    `rezerwa_na_podatki` — wywolanie stanie sie legalne i policzy ryczaltem."""
    with pytest.raises(TypeError) as blad:
        podatki.rezerwa_na_podatki(
            FAKTURA, PUSTO, PUSTO, dzialalnosc_od=OD, dzis=DO)
    assert "forma" in str(blad.value), (
        f"blad ma nazywac BRAKUJACY ARGUMENT, a mowi: {blad.value}")


def test_skladki_zus_ODMAWIAJA_gdy_nikt_nie_podal_formy():
    """Mutacja czerwieniaca: przywroc `forma: str = "RYCZALT"` w sygnaturze
    `skladki_zus_za_miesiace`. Zdrowotna liczy sie inaczej w kazdej formie —
    ta domyslna zanizala/zawyzala skladke bez slowa ostrzezenia."""
    with pytest.raises(TypeError) as blad:
        podatki.skladki_zus_za_miesiace(FAKTURA, od=OD, do=DO)
    assert "forma" in str(blad.value), (
        f"blad ma nazywac BRAKUJACY ARGUMENT, a mowi: {blad.value}")


def test_RezerwaPodatkowa_ODMAWIA_zbudowania_bez_formy():
    """Mutacja czerwieniaca: przywroc `forma: str = "RYCZALT"` i
    `nazwa_podatku: str = "Ryczalt"` jako wartosci domyslne pol dataclassu.

    To pole jedzie WPROST na ekran (`prezentacja.podpis_rezerwy`) i przez
    granice HTTP (`api/router.py`), wiec domyslna „Ryczalt" byla napisem
    widzianym przez czlowieka, nie tylko wartoscia w pamieci."""
    wspolne = dict(
        vat_nalezny=Decimal("0"), vat_naliczony=Decimal("0"),
        vat_do_zaplaty=Decimal("0"), zus=Decimal("0"),
        podatek_dochodowy=Decimal("0"), naliczone_razem=Decimal("0"),
        zaplacone=Decimal("0"), saldo=Decimal("0"))
    with pytest.raises(TypeError) as blad:
        podatki.RezerwaPodatkowa(**wspolne)
    tresc = str(blad.value)
    assert "forma" in tresc or "nazwa_podatku" in tresc, (
        f"blad ma nazywac BRAKUJACE POLE, a mowi: {tresc}")

    # Kontrola dwustronna do tego samego testu: z podana forma budowa DZIALA.
    # Bez niej ten straznik przechodzilby takze wtedy, gdyby dataclass byl
    # zepsuty na amen i odmawial KAZDEJ budowy.
    zbudowana = podatki.RezerwaPodatkowa(
        **wspolne, forma="SKALA", nazwa_podatku="PIT")
    assert zbudowana.forma == "SKALA"


# --- KONTROLA DWUSTRONNA: skala nie niesie ryczaltu i odwrotnie ----------

def test_SKALA_nie_przemyca_ani_jednej_wartosci_ryczaltowej():
    """Przy skali na ekran nie ma prawa trafic slowo „Ryczalt" ani liczba
    policzona ryczaltem. Liczby porownawcze zmierzone 2026-08-28 na tych
    samych danych wejsciowych."""
    skala = _rezerwa("SKALA")
    ryczalt = _rezerwa("RYCZALT", Decimal("0.085"))

    # kontrola licznosci: pomiar ma cokolwiek widziec
    assert len(FAKTURA) == 1, "pomiar bez faktury nie porownuje niczego"
    assert skala.miesiace_zus == 3 and ryczalt.miesiace_zus == 3, (
        "obie strony maja objac te same trzy miesiace, inaczej roznica "
        "wynika z okresu, a nie z formy")

    assert skala.forma == "SKALA"
    assert skala.nazwa_podatku == "PIT"
    assert "ycza" not in skala.nazwa_podatku, (
        f"nazwa podatku przy skali brzmi {skala.nazwa_podatku!r}")

    # Te same dane, dwie formy, TRZY rozne liczby. Gdyby ktora sie zgadzala,
    # znaczyloby, ze forma nie doszla do silnika.
    assert skala.zus == Decimal("7479.95") != ryczalt.zus
    assert ryczalt.zus == Decimal("7275.33")
    assert skala.podatek_dochodowy == Decimal("0.00")
    assert ryczalt.podatek_dochodowy == Decimal("767.00")
    assert skala.saldo == Decimal("10055.95")
    assert ryczalt.saldo == Decimal("10618.33")


def test_RYCZALT_nadal_dziala_i_nie_zostal_wyciety():
    """Druga strona kontroli. Forma jest ustawieniem, nie stala — Darek moze
    ja zmienic i wtedy liczby ryczaltowe maja WROCIC, a nie zniknac.

    Bez tego testu „naprawa" polegajaca na wycieciu ryczaltu z silnika
    przeszlaby jako sukces."""
    ryczalt = _rezerwa("RYCZALT", Decimal("0.085"))
    assert ryczalt.forma == "RYCZALT"
    assert ryczalt.nazwa_podatku == "Ryczałt"
    assert ryczalt.podatek_dochodowy > 0, (
        "ryczalt bez podatku dochodowego znaczy, ze silnik ryczaltu przestal "
        "liczyc — to nie jest naprawa, to usuniecie funkcji")


def test_RYCZALT_bez_stawki_ODMAWIA_zamiast_zgadnac():
    """Trzeci stan: forma podana, stawka nie. Zgadniecie stawki byloby tym
    samym bledem co domyslna forma, tylko o poziom nizej."""
    with pytest.raises(podatki.BladMagazynu):
        _rezerwa("RYCZALT")


def test_forma_NIEROZSTRZYGNIETA_ODMAWIA_zamiast_wziac_ryczalt():
    """Brak decyzji uzytkownika to trzeci stan (D8), nie ryczalt. Ten test
    czerwieni sie takze wtedy, gdyby ktos „naprawil" odmowe, wstawiajac
    ciche przejscie na dowolna forme."""
    with pytest.raises(podatki.BladMagazynu) as blad:
        _rezerwa("NIEROZSTRZYGNIETA")
    assert "forma" in str(blad.value).lower()

"""Strazniki: koszt pomniejsza podatek dochodowy PRZY SKALI, a przy ryczalcie NIE.

ZNALEZISKO (Ethan, 2026-08-28, przy porzadkowaniu dokumentow). `policz_skala`
odejmowala koszty od dochodu miesiaca (`rdzen/podatki.py`, `dochod_miesiaca =
netto - koszty - spoleczne`), ale `rezerwa_na_podatki` NIE przekazywala kosztow
do `_podatek_dochodowy` w ogole — szly wylacznie do `vat_naliczony`. Skutek:
rezerwa przy skali zawyzona o podatek od kosztow. To pieniadze Darka odlozone
na podatek, ktorego nie bedzie.

REGULA (Darek, 2026-08-28 godz. 19:50): „Koszty sa rozliczane co miesiac,
miesiac po miesiacu". Koszt danego miesiaca pomniejsza dochod TEGO miesiaca.

ROZROZNIENIE, ktore latwo pomylic: narastajaco przy skali liczy sie PROG
PODATKOWY (moment przekroczenia 120 000 zl od poczatku roku), a NIE koszty.
Koszt wchodzi per miesiac; dochod narastajacy budowany jest z miesiecy JUZ
pomniejszonych o koszty. Straznikiem tego rozroznienia jest
`test_prog_liczy_sie_z_miesiecy_JUZ_pomniejszonych_o_koszty`.

DLACZEGO TE TESTY NIE STOJA NA BAZIE-WZORCU: `koszty_jdg` ma tam 0 wierszy,
wiec naprawa dalaby na niej roznice ZERO, a test przeszedlby nie dotknawszy
naprawianej sciezki. Ta sama klasa falszywej zieleni, co pusty skan meldujacy
sukces. Dane sa tu budowane jawnie, z realnym kosztem.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import magazyn, podatki

NETTO = Decimal("11200.00")
KOSZT = Decimal("4000.00")

#: Podatek od kosztu 4 000 zl w pierwszym progu skali: 12% = 480 zl.
#: Liczba WPISANA WPROST, nie wyliczona w tescie — test liczacy oczekiwanie
#: ta sama arytmetyka co kod przechodzi takze wtedy, gdy oba sa zle.
SPADEK_PODATKU = Decimal("480.00")


def _faktury(*miesiace) -> pd.DataFrame:
    return pd.DataFrame([
        {"data": f"{rok}-{m:02d}-10", "kwota_netto": NETTO,
         "kwota_vat": Decimal("2576.00"), "zaplacony_zus": Decimal("2425.11"),
         "zysk_netto": Decimal("8007.89")}
        for rok, m in miesiace])


def _koszty(*pozycje) -> pd.DataFrame:
    if not pozycje:
        return pd.DataFrame()
    return pd.DataFrame([
        {"data": data, "opis": "laptop", "kwota_netto": kwota,
         "kwota_vat": Decimal("0.00")}
        for data, kwota in pozycje])


#: Rok z realnym podatkiem. Jedna faktura daje podatek 0,00 zl (kwota
#: zmniejszajaca zjada caly podatek), wiec naprawa bylaby na niej NIEWIDOCZNA.
ROK_Z_PODATKIEM = _faktury(*((2026, m) for m in range(7, 13)))


def _rezerwa(forma, faktury, koszty, **reszta):
    return podatki.rezerwa_na_podatki(
        faktury, koszty, pd.DataFrame(),
        dzialalnosc_od=date(2026, 7, 1), dzis=date(2026, 12, 31),
        forma=forma, **reszta)


def test_dane_testowe_daja_NIEZEROWY_podatek():
    """KONTROLA LICZNOSCI. Bez niej „0 == 0" przechodzi jako dowod naprawy."""
    bez = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM, _koszty())
    assert bez.podatek_dochodowy >= Decimal("1000.00"), (
        f"dane testowe daja podatek {bez.podatek_dochodowy} — za malo, zeby "
        f"spadek o {SPADEK_PODATKU} byl widoczny")


def test_koszt_OBNIZA_podatek_dochodowy_przy_SKALI():
    """Sedno naprawy, z liczba: 4 000 zl kosztu to 480 zl mniej rezerwy."""
    bez = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM, _koszty())
    z_kosztem = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM,
                         _koszty(("2026-09-12", KOSZT)))
    assert bez.podatek_dochodowy - z_kosztem.podatek_dochodowy == SPADEK_PODATKU
    assert bez.naliczone_razem - z_kosztem.naliczone_razem == SPADEK_PODATKU, \
        "spadek podatku ma zejsc do sumy naliczonych, nie zatrzymac sie w polu"


def test_koszt_NIE_RUSZA_podatku_przy_RYCZALCIE():
    """KONTROLA DWUSTRONNA. Przy ryczalcie podstawa jest PRZYCHOD — koszt jej
    nie dotyka. Przekazanie kosztow bezwarunkowo zanizyloby ryczalt, czyli
    ZANIZYLO rezerwe: niedoplata do urzedu jest grozniejsza niz nadplata."""
    wspolne = dict(stawka_ryczaltu=Decimal("0.085"))
    bez = _rezerwa(magazyn.FORMA_RYCZALT, ROK_Z_PODATKIEM, _koszty(), **wspolne)
    z_kosztem = _rezerwa(magazyn.FORMA_RYCZALT, ROK_Z_PODATKIEM,
                         _koszty(("2026-09-12", KOSZT)), **wspolne)
    assert bez.podatek_dochodowy == z_kosztem.podatek_dochodowy
    assert bez.podatek_dochodowy > 0, "kontrola licznosci: ryczalt ma byc niezerowy"


def test_ZERO_kosztow_nie_zmienia_niczego():
    """Kontrola dwustronna druga strona: brak kosztow ma dawac dokladnie to,
    co przed naprawa. Zero roznicy NIE JEST bledem."""
    pusto = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM, _koszty())
    ramka_pusta = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM, pd.DataFrame())
    assert pusto.podatek_dochodowy == ramka_pusta.podatek_dochodowy
    assert pusto.podatek_dochodowy == Decimal("3077.00"), \
        "wartosc sprzed naprawy zmierzona 2026-08-28 — zmiana tu to regresja"


# --- przelom roku: dwa niezalezne ryzyka ---------------------------------

def test_koszt_z_INNEGO_ROKU_nie_wchodzi():
    """Koszt z grudnia 2025 nie ma prawa pomniejszyc dochodu 2026."""
    bez = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM, _koszty())
    obcy = _rezerwa(magazyn.FORMA_SKALA, ROK_Z_PODATKIEM,
                    _koszty(("2025-12-30", KOSZT)))
    assert bez.podatek_dochodowy == obcy.podatek_dochodowy


def test_koszt_GRUDNIOWY_nie_pomniejsza_dochodu_STYCZNIA():
    """Dwa lata naraz. Koszt z grudnia 2026 obniza podatek 2026 i NIE dotyka
    2027 — inaczej przekroczenie progu w listopadzie znikaloby przez koszt
    grudniowy nastepnego roku."""
    dwa_lata = _faktury(*[(2026, m) for m in range(7, 13)],
                        *[(2027, m) for m in range(1, 7)])
    bez = podatki.rezerwa_na_podatki(
        dwa_lata, _koszty(), pd.DataFrame(),
        dzialalnosc_od=date(2026, 7, 1), dzis=date(2027, 12, 31),
        forma=magazyn.FORMA_SKALA)
    z_grudniem = podatki.rezerwa_na_podatki(
        dwa_lata, _koszty(("2026-12-20", KOSZT)), pd.DataFrame(),
        dzialalnosc_od=date(2026, 7, 1), dzis=date(2027, 12, 31),
        forma=magazyn.FORMA_SKALA)
    assert bez.podatek_dochodowy - z_grudniem.podatek_dochodowy == SPADEK_PODATKU
    # rok 2027 policzony osobno musi byc nietkniety
    stan_2027_bez = podatki.stan_roku_skali(dwa_lata, 2027)
    assert stan_2027_bez.dochod_narastajaco > 0, "kontrola licznosci: 2027 ma faktury"


def test_prog_liczy_sie_z_miesiecy_JUZ_pomniejszonych_o_koszty():
    """ROZROZNIENIE, o ktore prosil Oliver. Narastajaco idzie PROG, nie koszt.

    Dochod narastajacy po roku ma byc dokladnie o sume kosztow mniejszy —
    czyli koszty weszly do narastania RAZ, przez miesiace, a nie osobnym
    torem obok niego.
    """
    bez = podatki.stan_roku_skali(ROK_Z_PODATKIEM, 2026)
    z_kosztem = podatki.stan_roku_skali(
        ROK_Z_PODATKIEM, 2026, koszty=_koszty(("2026-09-12", KOSZT)))
    assert bez.dochod_narastajaco - z_kosztem.dochod_narastajaco == KOSZT


def test_koszt_NIE_liczony_DWA_RAZY_gdy_w_miesiacu_sa_dwie_faktury():
    """Miesiac z dwiema fakturami odejmuje koszt raz, nie przy kazdej."""
    dwie = pd.concat([ROK_Z_PODATKIEM, _faktury((2026, 9))], ignore_index=True)
    bez = podatki.stan_roku_skali(dwie, 2026)
    z_kosztem = podatki.stan_roku_skali(
        dwie, 2026, koszty=_koszty(("2026-09-12", KOSZT)))
    assert bez.dochod_narastajaco - z_kosztem.dochod_narastajaco == KOSZT


def test_koszt_w_miesiacu_BEZ_faktury_NIE_GINIE():
    """Petla idzie po fakturach, a koszt moze trafic w miesiac bez zadnej.
    Zgubienie go zawyzaloby rezerwe — dokladnie wada, ktora naprawiamy.

    SPROSTOWANIE 2026-08-28: pierwsza wersja datowala koszt na 2026-11-05,
    czyli w miesiac, ktory fakture MA (`ROK_Z_PODATKIEM` to lipiec–grudzien).
    Test byl strażnikiem-atrapa i przezyl mutacje „usun petle miesiecy bez
    faktury" (9 passed). Wykryla to mutacja, nie czytanie kodu. Marzec 2026
    faktury nie ma — i o to w tym tescie chodzi.
    """
    assert not any(str(d).startswith("2026-03")
                   for d in ROK_Z_PODATKIEM["data"]), \
        "kontrola: marzec ma NIE miec faktury, inaczej test nie bada niczego"
    z_kosztem = podatki.stan_roku_skali(
        ROK_Z_PODATKIEM, 2026, koszty=_koszty(("2026-03-05", KOSZT)))
    bez = podatki.stan_roku_skali(ROK_Z_PODATKIEM, 2026)
    assert bez.dochod_narastajaco - z_kosztem.dochod_narastajaco == KOSZT

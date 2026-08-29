"""Strazniki: ZUS rozbity NA OKRESY, nie jedna kwota na jeden termin (wada 2).

WADA. `do_zaplaty` budowalo slownik kwot z SUM rezerwy (`{"ZUS": rezerwa.zus}`)
i przypinalo kazda sume do JEDNEGO najblizszego terminu. Odczyt 6 pazdziernika
dawal `ZUS 5 120,65 zl, termin 2026-10-20` — a to sa DWIE skladki (wrzesien
i pazdziernik), z ktorych na 20 pazdziernika wymagalna jest JEDNA.

DRUGI SKUTEK — NIEZWERYFIKOWANY END-TO-END, wniosek z czytania kodu, nie
pomiar. `prognoza_plynnosci` kluczuje daniny po `(termin, nazwa)` i usuwa
ZALOZONA danina prognozy tam, gdzie stoi REALNA zaleglosc
(`prognoza_plynnosci.py`, KROK 7: `daniny.pop(klucz, None)`). Przy jednej
zbiorczej pozycji znikala danina z 20 X, a zalozona skladka z 20 XI
ZOSTAWALA — czyli pazdziernikowy ZUS wchodzilby na os DWA RAZY: raz w
zbiorczej kwocie na 20 X, raz jako zalozenie na 20 XI. Po rozbiciu obie
pozycje maja wlasny klucz, wiec obie zalozone daniny znikaja.
NIE POTWIERDZILEM tego przebiegiem prognozy na danych — wymaga bazy z
kotwica, a `stan_konta` ma 0 wierszy. Do sprawdzenia przy przeliczaniu
czterech ramek plynnosci; jesli sie potwierdzi, ramki sprzed tej zmiany
zanizaly saldo listopada o pelna skladke.

DECYZJA PRODUKTOWA (Oliver, Poziom 2, 2026-08-28): pozycja jeszcze
niewymagalna ZOSTAJE na liscie, z widoczna data wymagalnosci. Kafelek nazywa
sie „Do zaplacenia" i ma mowic ILE i KIEDY, a nie tylko co wymagalne dzis.

POMIAR (dzialalnosc od 2026-09-01, jedna faktura 11 200 zl z 2026-10-05,
forma SKALA, odczyt 2026-10-06):
    wrzesien   1 926,76 spoleczne + 432,54 zdrowotna minimalna = 2 359,30
    pazdziernik 1 926,76 spoleczne + 834,59 zdrowotna od dochodu = 2 761,35
    razem 5 120,65 — ta sama suma co przed rozbiciem
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn, podatki

WRZESIEN = date(2026, 9, 1)
ZUS_WRZESIEN = Decimal("2359.30")
ZUS_PAZDZIERNIK = Decimal("2761.35")
ZUS_RAZEM = Decimal("5120.65")


def _faktury():
    return pd.DataFrame([{
        "data": "2026-10-05", "kwota_netto": Decimal("11200.00"),
        "kwota_vat": Decimal("2576.00"), "zaplacony_zus": Decimal("2425.11"),
        "zysk_netto": Decimal("8007.89")}])


def _rezerwa(dzis, wpisy=None):
    return podatki.rezerwa_na_podatki(
        _faktury(), pd.DataFrame(),
        pd.DataFrame() if wpisy is None else wpisy,
        dzialalnosc_od=WRZESIEN, dzis=dzis, forma=magazyn.FORMA_SKALA)


def _zus(pozycje):
    return [p for p in pozycje if p.nazwa == "ZUS"]


def test_kontrola_licznosci_rezerwa_niesie_dwa_miesiace():
    """Bez tego test nizej moglby badac przypadek jednomiesieczny i przejsc."""
    r = _rezerwa(date(2026, 10, 6))
    assert r.miesiace_zus == 2, f"oczekiwalem dwoch miesiecy, jest {r.miesiace_zus}"
    assert r.zus == ZUS_RAZEM


def test_ZUS_rozbity_na_DWIE_pozycje_z_wlasnymi_terminami():
    """Sedno wady 2."""
    dzis = date(2026, 10, 6)
    pozycje = _zus(podatki.do_zaplaty(_rezerwa(dzis), dzis, pd.DataFrame()))
    assert len(pozycje) == 2, \
        f"ZUS ma byc rozbity na dwa okresy, jest {len(pozycje)}: " \
        f"{[(str(p.za_okres), str(p.kwota), str(p.termin)) for p in pozycje]}"
    wrzesien, pazdziernik = sorted(pozycje, key=lambda p: p.za_okres)
    assert (wrzesien.za_okres, wrzesien.kwota, wrzesien.termin) == \
           (date(2026, 9, 1), ZUS_WRZESIEN, date(2026, 10, 20))
    assert (pazdziernik.za_okres, pazdziernik.kwota, pazdziernik.termin) == \
           (date(2026, 10, 1), ZUS_PAZDZIERNIK, date(2026, 11, 20))


def test_rozbicie_NIE_GUBI_i_NIE_TWORZY_pieniedzy():
    """Suma pozycji ZUS ma sie rownac kwocie ZUS w rezerwie, co do grosza."""
    dzis = date(2026, 10, 6)
    rezerwa = _rezerwa(dzis)
    pozycje = _zus(podatki.do_zaplaty(rezerwa, dzis, pd.DataFrame()))
    assert sum((p.kwota for p in pozycje), Decimal("0.00")) == rezerwa.zus


def test_JEDEN_miesiac_daje_JEDNA_pozycje():
    """KONTROLA DWUSTRONNA. Rozbicie, ktore zawsze mnozy pozycje, jest tak samo
    zle jak zbiorcza kwota — przy jednym miesiacu ma byc dokladnie jedna."""
    dzis = date(2026, 9, 15)
    pozycje = _zus(podatki.do_zaplaty(_rezerwa(dzis), dzis, pd.DataFrame()))
    assert len(pozycje) == 1
    assert pozycje[0].za_okres == WRZESIEN
    assert pozycje[0].termin == date(2026, 10, 20)


def test_zaplata_zdejmuje_od_NAJWCZESNIEJSZEGO_okresu():
    """Ta sama regula, co przy daninach: placi sie najpierw to, co najpilniejsze.
    Zaplata za wrzesien nie moze zdjac kwoty z pazdziernika i odwrotnie."""
    dzis = date(2026, 10, 6)
    wpisy = pd.DataFrame([{
        "data": "2026-10-15", "typ": budzet.TYP_WYDATKI,
        "kategoria": "Podatki i ZUS", "kwota": ZUS_WRZESIEN,
        "szczegoly": "ZUS za wrzesien"}])
    pozycje = _zus(podatki.do_zaplaty(_rezerwa(dzis, wpisy), dzis, wpisy))
    assert len(pozycje) == 1, "wrzesien zaplacony — ma zostac sam pazdziernik"
    assert pozycje[0].za_okres == date(2026, 10, 1)
    assert pozycje[0].kwota == ZUS_PAZDZIERNIK


def test_VAT_i_PIT_NIE_zostaly_po_cichu_rozbite():
    """Granica zmiany, zapisana jako test. Rozbicie VAT-u na okresy wymaga
    rozstrzygniecia kasowe/memorialowe (wada 3) i NIE jest przedmiotem tej
    zmiany. Gdyby wpadlo tu przypadkiem, kwoty na ekranie zmienilyby sie
    bez decyzji."""
    dzis = date(2026, 10, 6)
    pozycje = podatki.do_zaplaty(_rezerwa(dzis), dzis, pd.DataFrame())
    assert len([p for p in pozycje if p.nazwa == "VAT"]) == 1
    assert len([p for p in pozycje if p.nazwa == "PIT"]) <= 1

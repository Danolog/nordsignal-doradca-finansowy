"""Strazniki: termin daniny nie moze dotyczyc miesiaca PRZED dzialalnoscia.

WADA (Mila 2026-08-28, potwierdzona niezaleznie przez Olivera i przeze mnie).
Darek wznawia dzialalnosc 1 wrzesnia 2026. Pierwsza skladka ZUS jest ZA
WRZESIEN, platna do 20 pazdziernika — powiedzial to wprost o 19:14. Silnik
naliczal wlasciwa KWOTE, ale dawal jej termin 21 wrzesnia, czyli termin
skladki ZA SIERPIEN, w ktorym dzialalnosci nie bylo. Aplikacja kazala
zaplacic urzedowi miesiac za wczesnie.

Pomiar sprzed naprawy (`terminy.najblizsze(date(2026,9,15), forma='SKALA')`):
    PIT  termin 2026-09-21  za okres 2026-08-01
    ZUS  termin 2026-09-21  za okres 2026-08-01
    VAT  termin 2026-09-25  za okres 2026-08-01

Wada siedziala w NOSNIKU (`terminy.najblizsze` liczyl z samego kalendarza),
a nie u konsumenta — dlatego naprawa jest tutaj i domyka wszystkich naraz.
`PozycjaDoZaplaty` juz wczesniej niosla `za_okres`; brakowalo prawdziwej
wartosci, nie pola.
"""

from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import magazyn, terminy

WRZESIEN = date(2026, 9, 1)


def test_pomiar_kontrolny_bez_daty_dzialalnosci_zostaje_JAK_BYL():
    """Kontrola dwustronna, strona pierwsza: brak daty niczego nie zmienia.

    Bez tego testu naprawa moglaby po cichu przesunac terminy wszystkim,
    takze tym, ktorzy dzialalnosc prowadza od lat.
    """
    stare = terminy.najblizsze(date(2026, 9, 15), forma=magazyn.FORMA_SKALA)
    assert len(stare) >= 3, f"kontrola licznosci: tylko {len(stare)} pozycji"
    zus = next(t for t in stare if t.nazwa == "ZUS")
    assert zus.za_okres == date(2026, 8, 1)
    assert zus.data == date(2026, 9, 21)


def test_termin_NIE_dotyczy_miesiaca_PRZED_dzialalnoscia():
    """Sedno naprawy. 15 wrzesnia, dzialalnosc od 1 wrzesnia: nie ma prawa
    pasc zaden termin za sierpien."""
    pozycje = terminy.najblizsze(date(2026, 9, 15), forma=magazyn.FORMA_SKALA,
                                 dzialalnosc_od=WRZESIEN)
    assert len(pozycje) >= 3, f"kontrola licznosci: {len(pozycje)} pozycji"
    zbyt_wczesne = [(t.nazwa, t.za_okres) for t in pozycje
                    if t.za_okres < WRZESIEN and not t.nazwa.startswith("Zdrowotna")]
    assert not zbyt_wczesne, f"terminy sprzed dzialalnosci: {zbyt_wczesne}"


def test_pierwsza_skladka_ZUS_jest_za_wrzesien_platna_w_pazdzierniku():
    """Zdanie Darka z godz. 19:14, zamienione na asercje."""
    pozycje = terminy.najblizsze(date(2026, 9, 15), forma=magazyn.FORMA_SKALA,
                                 dzialalnosc_od=WRZESIEN)
    zus = next(t for t in pozycje if t.nazwa == "ZUS")
    assert zus.za_okres == WRZESIEN, "skladka ma byc ZA WRZESIEN"
    assert zus.data == date(2026, 10, 20), "platna do 20 pazdziernika"


def test_dzialalnosc_OD_STYCZNIA_zachowuje_terminy_sierpniowe():
    """KONTROLA DWUSTRONNA, strona druga. Bramka, ktora odcina zawsze, nie
    jest bramka — przy dzialalnosci od stycznia sierpien MUSI byc."""
    pozycje = terminy.najblizsze(date(2026, 9, 15), forma=magazyn.FORMA_SKALA,
                                 dzialalnosc_od=date(2026, 1, 1))
    zus = next(t for t in pozycje if t.nazwa == "ZUS")
    assert zus.za_okres == date(2026, 8, 1)
    assert zus.data == date(2026, 9, 21)


def test_po_wejsciu_w_rytm_data_dzialalnosci_niczego_nie_przesuwa():
    """6 pazdziernika okres wrzesniowy jest juz naturalny — naprawa ma byc
    wtedy niewidoczna, a nie przesuwac terminow w kolko."""
    bez = terminy.najblizsze(date(2026, 10, 6), forma=magazyn.FORMA_SKALA)
    z_data = terminy.najblizsze(date(2026, 10, 6), forma=magazyn.FORMA_SKALA,
                                dzialalnosc_od=WRZESIEN)
    assert [(t.nazwa, t.data, t.za_okres) for t in bez] == \
           [(t.nazwa, t.data, t.za_okres) for t in z_data]


def test_termin_ROCZNY_nie_znika_przez_date_dzialalnosci():
    """Zdrowotna roczna ma wlasny cykl i nie podlega tej regule. Odciecie jej
    zabraloby jedyna pozycje pilnujaca doplaty rocznej."""
    pozycje = terminy.najblizsze(date(2026, 9, 15), forma=magazyn.FORMA_SKALA,
                                 dzialalnosc_od=WRZESIEN)
    assert any(t.nazwa.startswith("Zdrowotna") for t in pozycje)


def test_dzialalnosc_od_w_PRZYSZLOSCI_nie_daje_terminu_z_przeszlosci():
    """Odczyt przed startem dzialalnosci: pierwszy okres to wrzesien, termin
    w pazdzierniku. Zaden termin nie moze wypasc przed data odczytu-startu."""
    pozycje = terminy.najblizsze(date(2026, 8, 20), forma=magazyn.FORMA_SKALA,
                                 dzialalnosc_od=WRZESIEN)
    miesieczne = [t for t in pozycje if not t.nazwa.startswith("Zdrowotna")]
    assert miesieczne, "kontrola licznosci: brak pozycji miesiecznych"
    for t in miesieczne:
        assert t.za_okres >= WRZESIEN, f"{t.nazwa}: okres {t.za_okres}"


# --- konsument: rezerwa -> do_zaplaty ------------------------------------
# Powyzsze dowodzi, ze NOSNIK liczy dobrze. To jeszcze nie znaczy, ze ekran
# dostaje dobra date — konsument musi ja ZAWOLAC. Ponizsze to sprawdza.

def _rezerwa_wrzesniowa(dzis):
    import pandas as pd
    from silnik.rdzen import podatki
    faktury = pd.DataFrame([{
        "data": "2026-09-10", "kwota_netto": Decimal("11200.00"),
        "kwota_vat": Decimal("2576.00"), "zaplacony_zus": Decimal("2425.11"),
        "zysk_netto": Decimal("8007.89")}])
    return podatki.rezerwa_na_podatki(
        faktury, pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=WRZESIEN, dzis=dzis, forma=magazyn.FORMA_SKALA)


def test_POZYCJE_DO_ZAPLATY_nie_niosa_okresu_sprzed_dzialalnosci():
    """Kontrola przez calego konsumenta: rezerwa niesie date dzialalnosci,
    `do_zaplaty` ja wola, wiec zadna pozycja na ekranie nie moze dotyczyc
    sierpnia. Bez tego testu naprawa mogla zostac w nosniku i nie dojsc
    do zadnego ekranu."""
    from silnik.rdzen import podatki
    import pandas as pd
    dzis = date(2026, 9, 15)
    rezerwa = _rezerwa_wrzesniowa(dzis)
    assert rezerwa.dzialalnosc_od == WRZESIEN, "rezerwa ma niesc te date"
    pozycje = podatki.do_zaplaty(rezerwa, dzis, pd.DataFrame())
    assert pozycje, "kontrola licznosci: brak pozycji, test nic nie bada"
    zbyt_wczesne = [(p.nazwa, p.za_okres) for p in pozycje
                    if p.za_okres < WRZESIEN]
    assert not zbyt_wczesne, f"pozycje sprzed dzialalnosci: {zbyt_wczesne}"
    zus = next((p for p in pozycje if p.nazwa == "ZUS"), None)
    assert zus is not None and zus.termin == date(2026, 10, 20), \
        f"ZUS ma byc platny 20 pazdziernika, jest {zus and zus.termin}"

# -*- coding: utf-8 -*-
"""D-20 i D-61: os prognozy ma DWA zrodla — wpisy i plan.

DLACZEGO TEN PLIK ISTNIEJE. Do Z7b `prognoza_plynnosci.zbuduj` bral wylacznie
plan, a wpisy wchodzily tam jedynie przez `podatki.do_zaplaty`. Zmierzone
w Z7 na zywym przebiegu przez przegladarke:

    saldoMinimalne:  przed 8 335,87 zl · po wpisie 8 335,87 zl · po wycofaniu 8 335,87 zl

Wpis DOCIERAL do silnika (numer 215, licznik miesiaca 0 -> 1, wiersz
w „Ostatnich wpisach"), a prognoza go nie widziala. Cala sciezka „wpisz
wydatek i zobacz, czy dasz rade do konca okresu" byla teatrem.

D-20 (Darek, 2026-08-28 g. 18:04): **dni minione licza sie z rzeczywistych
wpisow, dni przyszle z planu.** Proste odejmowanie wydanego od planu Darek
ODRZUCIL, bo *„dziala tylko w jedna strone i grozi podwojnym liczeniem"*.

D-61 (Sophia, 2026-08-29): **wpis konsumuje pozycje planu tej kategorii w tym
miesiacu az do zera; nadwyzka obciaza os w calosci.**

BRAMKA Z PLANU WYKONAWCZEGO, krok 1.2 — trzy zdania, trzy testy:
  „przy wpisie 500 zl PONAD PLAN w dniu minionym saldo NA DZIS jest o 500,00 zl
   nizsze niz przed wpisem; przy wpisie w dniu przyszlym — bez zmiany;
   kotwica nowsza od wpisu uniewaznia je (zero podwojnego liczenia)."

DWA SLOWA, KTORE ZGUBILA BRAMKA NOCNA — i dlatego mierzyla nie to, co trzeba:
„ponad plan". Wpis MIESZCZACY SIE w planie nie ma prawa zmienic sumy; zmienia
wylacznie DATE WYPLYWU. Bramka nocna zamienila przy okazji „saldo na dzis"
na „saldo minimalne" — a minimum krzywej lezy zwykle poza oknem przesuniecia.
Stad wynik, ktory wygladal jak spor o semantyke, a byl zle dobranym przyrzadem.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn
from silnik.rdzen import prognoza_plynnosci as pp

DZIS = date(2026, 10, 6)
KOTWICA = pp.Kotwica(data=date(2026, 9, 1), kwota=Decimal("10000.00"))
WOLUMEN = pp.Wolumen(ostrozny=Decimal("120"), realny=Decimal("160"),
                     stawka=Decimal("70"))
FORMA = magazyn.FormaRoku(rok=2026, forma=magazyn.FORMA_SKALA,
                          stawka_ryczaltu=None)

#: Pozycja planu z bazy-wzorca: „Energia Elektryczna", 330,00 zl, dzien 20.
#: Ta sama, na ktorej D-61 sie wylozyla — nie wymyslona na potrzeby testu.
KATEGORIA = "Energia Elektryczna"
PLAN_KWOTA = Decimal("330.00")
DZIEN_PLANU = 20
WPIS_Z_ZADANIA = Decimal("274.06")


def _plan(*wiersze) -> pd.DataFrame:
    return pd.DataFrame([
        dict(id=i + 1, rok=r, miesiac=m, typ=t, kategoria=k,
             kwota_planowana=str(kw), powtarzalna=0, do_roku=None,
             do_miesiaca=None, opis="", dzien=d, co_ile_miesiecy=1)
        for i, (r, m, t, k, kw, d) in enumerate(wiersze)])


def _wpisy(*wiersze) -> pd.DataFrame:
    kolumny = ["id", "data", "typ", "kategoria", "kwota", "szczegoly"]
    if not wiersze:
        return pd.DataFrame(columns=kolumny)
    return pd.DataFrame([
        dict(id=i + 1, data=d, typ=t, kategoria=k, kwota=str(kw), szczegoly="")
        for i, (d, t, k, kw) in enumerate(wiersze)])


PLAN_ENERGIA = _plan(
    (2026, 10, budzet.TYP_WYDATKI, KATEGORIA, PLAN_KWOTA, DZIEN_PLANU))


def _licz(*, plan=None, wpisy=None, kotwica=KOTWICA, dzis=DZIS):
    return pp.zbuduj(
        plan=plan if plan is not None else pd.DataFrame(),
        kotwica=kotwica, wolumen=WOLUMEN, forma=FORMA, zaleglosci=[],
        przychod_narastajaco=Decimal("0"), dzis=dzis,
        wpisy=wpisy if wpisy is not None else _wpisy())


def _saldo(wynik, dzien: date) -> Decimal:
    """Saldo ostrozne danego dnia — z KONTROLA, ze dzien w ogole jest na osi.

    Bez niej `next(...)` z wartoscia domyslna zwrocilby zero i porownanie
    „przed kontra po" wychodzilo by zerowe dla obu stron: pomiar, ktory
    nigdzie nie dotarl, meldowalby brak roznicy.
    """
    trafienia = [d.saldo_ostrozne for d in (wynik.dni or ()) if d.data == dzien]
    assert len(trafienia) == 1, (
        f"dzien {dzien} nie lezy na osi (dni: "
        f"{len(wynik.dni or ())}) — pomiar mierzy pustke")
    return trafienia[0]


def _zdarzenia(wynik, nazwa: str):
    return [(d.data, z.kwota_ostrozna, z.rodzaj)
            for d in (wynik.dni or ()) for z in d.zdarzenia if z.nazwa == nazwa]


# --- kontrola licznosci PRZED jakimkolwiek porownaniem -------------------

def test_pomiar_widzi_OS_a_nie_pustke():
    """Kazdy test nizej porownuje dwie prognozy. Gdyby `zbuduj` zwracalo
    `dni=None` (stan „nie wiem"), wszystkie roznice wyszlyby zerowe i cala
    reszta pliku byla by zielona, nie zobaczywszy niczego."""
    wynik = _licz(plan=PLAN_ENERGIA)
    assert wynik.stan != pp.STAN_NIE_WIEM, wynik.zastrzezenia
    assert wynik.dni, "os jest pusta"
    assert len(wynik.dni) > 150, f"os ma {len(wynik.dni)} dni — za krotka"
    assert len(_zdarzenia(wynik, KATEGORIA)) == 1, \
        "pozycja planu nie weszla na os — nie ma czego konsumowac"


# --- BRAMKA planu wykonawczego, krok 1.2 — trzy zdania -------------------

def test_BRAMKA_wpis_500_PONAD_PLAN_w_dniu_minionym_obniza_saldo_NA_DZIS_o_500():
    """Zdanie pierwsze bramki. „Ponad plan" znaczy tu: kategoria, ktorej plan
    nie przewiduje — nie ma czego konsumowac, wiec caly wpis obciaza os."""
    bez = _licz(plan=PLAN_ENERGIA)
    z_wpisem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, "Zakupy", "500.00")))
    roznica = _saldo(z_wpisem, DZIS) - _saldo(bez, DZIS)
    assert roznica == Decimal("-500.00"), (
        f"saldo na dzis: przed {_saldo(bez, DZIS)}, po {_saldo(z_wpisem, DZIS)}, "
        f"roznica {roznica} — bramka zada dokladnie -500,00 zl")


def test_BRAMKA_ten_sam_wpis_w_dniu_PRZYSZLYM_nie_rusza_salda_na_dzis():
    """Zdanie drugie bramki. Kontrola dwustronna do testu wyzej: gdyby
    prognoza dodawala wpisy bez ogladania sie na date, ten test tez pokazalby
    -500,00 zl — i pierwszy przechodzilby z tego samego, zlego powodu."""
    bez = _licz(plan=PLAN_ENERGIA)
    przyszly = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-20", budzet.TYP_WYDATKI, "Zakupy", "500.00")))
    assert _saldo(przyszly, DZIS) - _saldo(bez, DZIS) == Decimal("0.00"), \
        "wpis z przyszlosci ruszyl saldo NA DZIS"
    # ...ale ma ruszyc saldo PO swojej dacie — inaczej wpadl w prozne.
    po = date(2026, 10, 21)
    assert _saldo(przyszly, po) - _saldo(bez, po) == Decimal("-500.00"), \
        "wpis z przyszlosci nie obciazyl osi wcale — zniknal"


def test_BRAMKA_kotwica_NOWSZA_od_wpisu_uniewaznia_go():
    """Zdanie trzecie bramki — zero podwojnego liczenia.

    Stan konta odczytany 1 X JUZ ZAWIERA wydatek z 15 IX. Policzony drugi raz
    odjalby te same pieniadze dwukrotnie. To jest dokladnie ten tryb awarii,
    dla ktorego Darek odrzucil proste odejmowanie."""
    kotwica_pazdziernikowa = pp.Kotwica(data=date(2026, 10, 1),
                                        kwota=Decimal("10000.00"))
    bez = _licz(kotwica=kotwica_pazdziernikowa)
    ze_starym = _licz(kotwica=kotwica_pazdziernikowa, wpisy=_wpisy(
        ("2026-09-15", budzet.TYP_WYDATKI, "Zakupy", "500.00")))
    assert _saldo(ze_starym, DZIS) == _saldo(bez, DZIS), \
        "wpis sprzed kotwicy zostal policzony drugi raz"


# --- trzy przypadki D-61 -------------------------------------------------

def test_PRZYPADEK_1_wpis_MIESCI_SIE_w_planie_suma_bez_zmian_data_przesunieta():
    """274,06 zl na Energie NIE JEST wydatkiem ponad plan — plan przewiduje
    w tej kategorii 330,00 zl. Suma sie nie zmienia; zmienia sie ROZKLAD."""
    bez = _licz(plan=PLAN_ENERGIA)
    z_wpisem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, KATEGORIA, WPIS_Z_ZADANIA)))

    przed = _zdarzenia(bez, KATEGORIA)
    po = _zdarzenia(z_wpisem, KATEGORIA)
    assert [(d.isoformat(), str(k)) for d, k, _ in przed] == \
           [("2026-10-20", "-330.00")]
    assert [(d.isoformat(), str(k)) for d, k, _ in po] == \
           [("2026-10-06", "-274.06"), ("2026-10-20", "-55.94")]

    # SUMA BEZ ZMIAN — to jest sedno przypadku 1.
    assert sum(k for _, k, _ in przed) == sum(k for _, k, _ in po) \
           == Decimal("-330.00")
    # DATA WYPLYWU PRZESUNIETA: salda miedzy 6 a 19 X spadaja...
    for dzien in (DZIS, date(2026, 10, 12), date(2026, 10, 19)):
        assert _saldo(z_wpisem, dzien) - _saldo(bez, dzien) \
               == -WPIS_Z_ZADANIA, dzien
    # ...a po 20 X wracaja do tej samej liczby.
    assert _saldo(z_wpisem, date(2026, 10, 21)) == _saldo(bez, date(2026, 10, 21))


def test_PRZYPADEK_2_wpis_PRZEKRACZA_plan_os_nizej_o_NADWYZKE():
    """500,00 zl przy planie 330,00 zl. Plan zjedzony do zera, a 170,00 zl
    nadwyzki obciaza os BEZ KOMPENSATY (asymetria D-9)."""
    bez = _licz(plan=PLAN_ENERGIA)
    z_wpisem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, KATEGORIA, "500.00")))
    po = _zdarzenia(z_wpisem, KATEGORIA)
    assert [(d.isoformat(), str(k)) for d, k, _ in po] == \
           [("2026-10-06", "-500.00")], \
        "pozycja planu nie zostala zjedzona do zera"
    nadwyzka = Decimal("500.00") - PLAN_KWOTA
    po_planie = date(2026, 10, 21)
    assert _saldo(z_wpisem, po_planie) - _saldo(bez, po_planie) == -nadwyzka, \
        f"os mala byc nizsza dokladnie o nadwyzke {nadwyzka}"


def test_PRZYPADEK_3_kategoria_BEZ_pozycji_planu_os_nizej_o_CALA_kwote():
    """Nie ma czego konsumowac — wpis wchodzi w calosci. To zgadza sie z tym,
    co nocna kontrola zobaczyla na „Podatki i ZUS" (8 335,87 -> 8 609,93)."""
    bez = _licz(plan=PLAN_ENERGIA)
    z_wpisem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, "Zakupy", "500.00")))
    for dzien in (DZIS, date(2026, 10, 21), date(2026, 11, 30)):
        assert _saldo(z_wpisem, dzien) - _saldo(bez, dzien) \
               == Decimal("-500.00"), dzien


def test_PODWOJNE_LICZENIE_nie_wystepuje_604_06_nie_pada():
    """Kontrola na wartosci znanej, wprost z PRD: bez D-61 os policzylaby
    274,06 zl (6 X) PLUS 330,00 zl (20 X) = 604,06 zl za prad w jednym
    miesiacu. Ten test pyta o te liczbe po nazwisku."""
    z_wpisem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, KATEGORIA, WPIS_Z_ZADANIA)))
    pozycje = _zdarzenia(z_wpisem, KATEGORIA)
    assert len(pozycje) == 2, \
        f"kontrola licznosci: {len(pozycje)} pozycji zamiast dwoch"
    suma = -sum(k for _, k, _ in pozycje)
    assert suma != Decimal("604.06"), \
        "PODWOJNE LICZENIE: wpis nie skonsumowal pozycji planu"
    assert suma == PLAN_KWOTA, f"za prad w X wyszlo {suma}, plan mowi {PLAN_KWOTA}"


# --- D-20 sam w sobie ----------------------------------------------------

def test_plan_na_dzien_MINIONY_NIE_obciaza_osi():
    """Sedno D-20. Przeszlosc opisuja wpisy, nie zamiary — pozycja planu
    na dzien miniony odpada niezaleznie od tego, czy wpis padl."""
    plan_wczoraj = _plan(
        (2026, 10, budzet.TYP_WYDATKI, "Czesne", "660.00", 5))   # 5 X < 6 X
    plan_jutro = _plan(
        (2026, 10, budzet.TYP_WYDATKI, "Czesne", "660.00", 7))   # 7 X > 6 X
    pusty = _licz()
    assert _saldo(_licz(plan=plan_wczoraj), DZIS) == _saldo(pusty, DZIS), \
        "pozycja planu na dzien miniony obciazyla os"
    jutro = date(2026, 10, 8)
    assert _saldo(_licz(plan=plan_jutro), jutro) - _saldo(pusty, jutro) \
        == Decimal("-660.00"), \
        "kontrola dwustronna: pozycja planu na dzien PRZYSZLY ma obciazyc os"


def test_wpis_PRZYCHODOWY_nie_konsumuje_planu_WYDATKU():
    """Klucz konsumpcji to (typ, kategoria), nie sama kategoria. Inaczej
    przychod w kategorii „Energia Elektryczna" (zwrot nadplaty) skasowalby
    zaplanowany rachunek — czyli kompensata, ktorej D-9 zabrania."""
    z_przychodem = _licz(plan=PLAN_ENERGIA, wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_PRZYCHODY, KATEGORIA, "300.00")))
    plan_na_osi = [k for _, k, r in _zdarzenia(z_przychodem, KATEGORIA)
                   if r == pp.RODZAJ_PLAN]
    assert plan_na_osi == [-PLAN_KWOTA], \
        f"plan wydatku zostal skonsumowany przychodem: {plan_na_osi}"


@pytest.mark.parametrize("kategoria", [budzet.KATEGORIA_PODATKI,
                                       budzet.KATEGORIA_PRZYCHOD_JDG])
def test_wpisy_danin_i_przychodu_JDG_NIE_wchodza_na_os_dwa_razy(kategoria):
    """Te dwie kategorie maja na osi wlasne zrodla: daniny wchodza przez
    `podatki.do_zaplaty`, przychod JDG przez godziny i stawke. Wpuszczone
    tedy weszlyby DRUGI RAZ — ta sama pulapka, przed ktora broni D-20."""
    bez = _licz()
    z_wpisem = _licz(wpisy=_wpisy(
        ("2026-10-06", budzet.TYP_WYDATKI, kategoria, "500.00")))
    assert _saldo(z_wpisem, DZIS) == _saldo(bez, DZIS), \
        f"wpis w kategorii {kategoria} wszedl na os drugi raz"


def test_BEZ_wpisow_os_biegnie_z_PRZYSZLEGO_planu():
    """Kontrola dwustronna calego pliku: brak wpisow nie ma znaczyc „brak
    prognozy". Plan dalej opisuje przyszlosc."""
    wynik = _licz(plan=PLAN_ENERGIA)
    assert len(_zdarzenia(wynik, KATEGORIA)) == 1
    po = date(2026, 10, 21)
    assert _saldo(wynik, po) - _saldo(_licz(), po) == -PLAN_KWOTA

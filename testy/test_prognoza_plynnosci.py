"""Prognoza plynnosci na osi DZIENNEJ — czysta arytmetyka (Z62, zdolnosc A1).

Osobny modul od `rdzen/prognoza.py`: tamten odpowiada na inne pytanie (kiedy
przychod przetnie prog zdrowotnej), pracuje na osi miesiecznej i nie zna ani
salda, ani wydatkow.

DLACZEGO FUNKCJA CZYSTA, BEZ BAZY. Zmierzone przed tym plasterkiem:
`wolne_srodki(plan, miesiace, Decimal("0"))` — czyli zdjecie rezerwy
podatkowej — przeszlo 532 testy. Straznik postawiony na ARGUMENTACH funkcji
czystej lapie te klase mutacji; straznik postawiony na funkcji czytajacej baze
nie lapie nic, bo argumenty powstaja w srodku.

Os jest dzienna i to nie jest szczegol (specyfikacja §4.2): dwudziestego
wychodzi ZUS i zaliczka, dwudziestego piatego VAT. Jesli faktura wplynie
dwudziestego szostego, przez szesc dni saldo jest ujemne, a na koniec miesiaca
dodatnie. Prognoza miesieczna tego nie pokaze.
"""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from silnik.rdzen import budzet, magazyn, podatki, prognoza_plynnosci, terminy

KOTWICA = prognoza_plynnosci.Kotwica(data=date(2026, 9, 1),
                                     kwota=Decimal("10000.00"))
WOLUMEN = prognoza_plynnosci.Wolumen(ostrozny=Decimal("120"),
                                     realny=Decimal("160"),
                                     stawka=Decimal("70"))
SKALA = magazyn.FormaRoku(rok=2026, forma=magazyn.FORMA_SKALA,
                          stawka_ryczaltu=None)
RYCZALT = magazyn.FormaRoku(rok=2026, forma=magazyn.FORMA_RYCZALT,
                            stawka_ryczaltu=Decimal("0.085"))
NIEROZSTRZYGNIETA = magazyn.FormaRoku(rok=2026,
                                      forma=magazyn.FORMA_NIEROZSTRZYGNIETA,
                                      stawka_ryczaltu=None)


def _plan(*wiersze) -> pd.DataFrame:
    """Ramka planu. Kolumny jak w bazie po Z48; `dzien=None` znaczy
    „dzien platnosci nieznany" — prognoza ma go DOMNIEMAC ostroznie."""
    return pd.DataFrame(
        [{"rok": r, "miesiac": m, "typ": t, "kategoria": k,
          "kwota_planowana": kw, "powtarzalna": 1, "do_roku": None,
          "do_miesiaca": None, "opis": o, "dzien": d, "co_ile_miesiecy": 1}
         for r, m, t, k, kw, d, o in wiersze])


def _zbuduj(**nadpisania):
    argumenty = dict(
        plan=pd.DataFrame(), kotwica=KOTWICA, wolumen=WOLUMEN, forma=SKALA,
        zaleglosci=[], przychod_narastajaco=Decimal("0"),
        dzis=date(2026, 9, 1))
    argumenty.update(nadpisania)
    return prognoza_plynnosci.zbuduj(**argumenty)


def _kwoty_zdarzen(wynik, nazwa: str) -> list[Decimal]:
    return [z.kwota_ostrozna for d in wynik.dni for z in d.zdarzenia
            if z.nazwa == nazwa]


# --- krok 0: „nie wiem" ma trzy nosniki naraz ----------------------------

def test_BRAK_kotwicy_daje_nie_wiem_a_nie_zero():
    """R11: prognoza zbudowana na saldzie ksiegowym startuje z punktu, ktory
    nie istnieje. Zero zamiast „nie wiem" to najlepszy mozliwy stan pokazany
    wtedy, gdy nie wiadomo nic."""
    wynik = _zbuduj(kotwica=None)
    assert wynik.stan == prognoza_plynnosci.STAN_NIE_WIEM
    assert wynik.dni is None, "`dni is None` to JEDYNY dyskryminator „nie liczylem\""
    assert wynik.zastrzezenia, "odmowa bez powodu jest cisza, a cisza jest zakazana"
    powod = [z for z in wynik.zastrzezenia
             if z.kod == prognoza_plynnosci.KOD_BRAK_KOTWICY]
    assert len(powod) == 1
    # Zdanie dla uzytkownika mowi „stan konta", nie „kotwica" — zargon
    # tlumaczy sie na granicy (CLAUDE.md §3), a nie zostawia w komunikacie.
    assert "stan konta" in powod[0].tekst.lower()
    assert "kotwic" not in powod[0].tekst.lower()


def test_BRAK_wolumenu_ostroznego_odmawia_OBU_linii():
    """R17: rysowanie samej realnej daloby zielony obraz z wylaczonym
    mechanizmem ostrzegania — ostrzezenie zapala sie na linii ostroznej."""
    pusty = prognoza_plynnosci.Wolumen(ostrozny=None, realny=Decimal("160"),
                                       stawka=Decimal("70"))
    wynik = _zbuduj(wolumen=pusty)
    assert wynik.stan == prognoza_plynnosci.STAN_NIE_WIEM
    assert wynik.dni is None


def test_z_kotwica_i_wolumenem_prognoza_LICZY():
    """Kontrola dwustronna: odmowa, ktora zdarza sie zawsze, nie jest odmowa."""
    wynik = _zbuduj()
    assert wynik.stan == prognoza_plynnosci.STAN_POLICZONA
    assert wynik.dni is not None and len(wynik.dni) > 150, \
        f"os ma {0 if wynik.dni is None else len(wynik.dni)} dni, nie ~183"


# --- krok 1: os dzienna --------------------------------------------------

def test_os_NIGDY_nie_zaczyna_sie_przed_kotwica():
    """Straznik obowiazkowy z planu. Dzien przed kotwica to dzien, o ktorego
    saldzie nie wiemy nic — dorysowanie go jest zmysleniem."""
    wynik = _zbuduj(kotwica=prognoza_plynnosci.Kotwica(
        data=date(2026, 9, 17), kwota=Decimal("500.00")))
    assert wynik.dni[0].data == date(2026, 9, 17)
    assert min(d.data for d in wynik.dni) == date(2026, 9, 17)


def test_os_konczy_sie_na_koncu_szostego_miesiaca():
    """Horyzont 6 miesiecy: wrzesien..luty. Przelom roku jest w kazdym oknie
    szesciomiesiecznym — cwiczy `_nastepny_miesiac` i reset narastajaco."""
    wynik = _zbuduj()
    assert wynik.dni[-1].data == date(2027, 2, 28)


def test_saldo_pierwszego_dnia_startuje_od_KWOTY_kotwicy():
    wynik = _zbuduj()
    assert wynik.dni[0].saldo_ostrozne == Decimal("10000.00")
    assert wynik.dni[0].saldo_realne == Decimal("10000.00")


def test_ostatni_dzien_PELNY_jest_wczesniej_niz_koniec_osi():
    """Danina ostatniego miesiaca placi sie POZA horyzontem, wiec ogon jest
    z natury zawyzony. Ekran wyszarza za `ostatni_dzien_pelny` — bez tego
    uzytkownik czyta najbardziej optymistyczna liczbe jako prognoze."""
    wynik = _zbuduj()
    assert wynik.ostatni_dzien_pelny == date(2027, 1, 31)
    assert wynik.ostatni_dzien_pelny < wynik.dni[-1].data


# --- krok 2: plan wolany DOKLADNIE horyzont razy -------------------------

def test_plan_na_miesiac_wolany_DOKLADNIE_szesc_razy_nie_183(monkeypatch):
    """Straznik obowiazkowy z planu. Os ma ~183 dni; rozwijanie regul planu
    per DZIEN dalo by ten sam wynik i 183 przebiegi tej samej reguly —
    czyli wydajnosc, ktorej nikt nigdy nie zmierzy, i nosnik wolany tak
    czesto, ze kazda jego zmiana staje sie ryzykiem."""
    licznik = {"ile": 0}
    prawdziwa = budzet.plan_na_miesiac

    def zliczajaca(plan, rok, miesiac):
        licznik["ile"] += 1
        return prawdziwa(plan, rok, miesiac)

    monkeypatch.setattr(budzet, "plan_na_miesiac", zliczajaca)
    _zbuduj(plan=_plan((2026, 9, budzet.TYP_WYDATKI, "Zakupy", "500.00", 10, "")))
    assert licznik["ile"] == 6, \
        f"plan_na_miesiac wolane {licznik['ile']} razy, nie 6"


# --- straznik: brak podwojnego PRZYCHODU ---------------------------------

def test_przychod_JDG_z_planu_NIE_doklada_sie_do_godzin():
    """Straznik obowiazkowy. Przychod JDG istnieje w aplikacji dwiema drogami:
    `godziny x stawka` oraz pozycja planu w `KATEGORIA_PRZYCHOD_JDG`
    (`magazyn.py:1312`). Policzenie obu dalo by przychod podwojony —
    i wygladalo by jak bardzo dobry miesiac."""
    bez = _zbuduj()
    z_pozycja = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_PRZYCHODY, budzet.KATEGORIA_PRZYCHOD_JDG,
         "8400.00", 28, "")))
    assert z_pozycja.dni[-1].saldo_ostrozne == bez.dni[-1].saldo_ostrozne, \
        "pozycja planu w kategorii przychodu JDG dolozyla sie do godzin"


def test_przychod_SPOZA_kategorii_JDG_normalnie_wchodzi():
    """Kontrola dwustronna: filtr, ktory odsiewa kazdy przychod, zamienia
    prognoze w wykres samych wydatkow."""
    bez = _zbuduj()
    z_pozycja = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_PRZYCHODY, "Zwrot wydatków", "1000.00", 15, "")))
    assert z_pozycja.dni[-1].saldo_ostrozne \
        == bez.dni[-1].saldo_ostrozne + Decimal("6000.00")


# --- straznik: brak podwojnego PODATKU -----------------------------------

def test_pozycja_planu_w_kategorii_PODATKI_daje_ZERO_zdarzen():
    """Straznik obowiazkowy. Danina moze wejsc do liczby trzema drogami naraz;
    prognoza liczy ja z silnika, wiec pozycja planu musi wypasc."""
    wynik = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_WYDATKI, budzet.KATEGORIA_PODATKI, "3000.00",
         20, "ZUS")))
    z_planu = [z for d in wynik.dni for z in d.zdarzenia
               if z.rodzaj == prognoza_plynnosci.RODZAJ_PLAN]
    assert z_planu == [], \
        f"pozycja planu w kategorii podatkowej dala {len(z_planu)} zdarzen"
    assert any(z.rodzaj == prognoza_plynnosci.RODZAJ_DANINA
               for d in wynik.dni for z in d.zdarzenia), \
        "kontrola licznosci: daniny z silnika maja byc — inaczej test nic nie widzial"


# --- straznik: brak podwojnej RATY ---------------------------------------

def test_zobowiazania_NIE_daja_zdarzen_tylko_wracaja_lista():
    """Straznik obowiazkowy. Raty kredytow istnieja i w tabeli `zobowiazania`,
    i w planie (`budzet.py:242-243` wymienia „Kredyt Revolut" i „Kredyt Alior"
    jako pozycje planu). Emitowanie ich z obu zrodel podwoilo by rate.

    Prognoza nie dopasowuje po nazwie — to bylo by zgadywanie. Zwraca pelna
    liste, a ekran mowi „sprawdz, czy te dwie sa w planie"."""
    zobowiazania = pd.DataFrame([
        {"id": 1, "nazwa": "Kredyt Revolut", "kapital": Decimal("12000.00"),
         "rata_minimalna": Decimal("450.00")},
        {"id": 2, "nazwa": "Kredyt Alior", "kapital": Decimal("8000.00"),
         "rata_minimalna": Decimal("300.00")}])
    bez = _zbuduj()
    wynik = _zbuduj(zobowiazania=zobowiazania)

    assert len(wynik.zobowiazania_spoza_planu) == 2
    assert wynik.dni[-1].saldo_ostrozne == bez.dni[-1].saldo_ostrozne, \
        "rata z tabeli zobowiazan weszla do salda — podwojenie wobec planu"


# --- straznik: zaleglosc NIE liczona dwa razy ----------------------------

def test_zaleglosc_wchodzi_RAZ_a_nie_takze_jako_danina_prognozy():
    """Straznik obowiazkowy. `podatki.do_zaplaty` rozbija SALDO rezerwy na
    daniny z terminami — a prognoza generuje daniny za miesiace osi. Gdy oba
    trafiaja w ten sam termin i te sama danine, kwota schodzi z konta dwa razy.

    Rozstrzyga zaleglosc: liczy sie z REALNYCH faktur, prognoza z zalozenia."""
    zaleglosc = podatki.PozycjaDoZaplaty(
        nazwa="ZUS", kwota=Decimal("2500.00"),
        termin=date(2026, 10, 20), za_okres=date(2026, 9, 1))
    wynik = _zbuduj(zaleglosci=[zaleglosc])

    zus_20_pazdziernika = [z.kwota_ostrozna for d in wynik.dni
                           if d.data == date(2026, 10, 20)
                           for z in d.zdarzenia if z.nazwa == "ZUS"]
    assert len(zus_20_pazdziernika) == 1, \
        f"ZUS 20 pazdziernika wystapil {len(zus_20_pazdziernika)} razy"
    assert zus_20_pazdziernika[0] == Decimal("-2500.00"), \
        "wygrac ma zaleglosc z realnych faktur, nie danina z zalozenia"


def test_zaleglosc_w_INNYM_terminie_nie_kasuje_daniny_prognozy():
    """Kontrola dwustronna: gdyby zaleglosc gasila kazda danine tej nazwy,
    prognoza przestala by pokazywac przyszle skladki w ogole."""
    zaleglosc = podatki.PozycjaDoZaplaty(
        nazwa="ZUS", kwota=Decimal("2500.00"),
        termin=date(2026, 10, 20), za_okres=date(2026, 9, 1))
    wynik = _zbuduj(zaleglosci=[zaleglosc])
    zus_listopad = [z for d in wynik.dni if d.data == date(2026, 11, 20)
                    for z in d.zdarzenia if z.nazwa == "ZUS"]
    assert len(zus_listopad) == 1, "danina listopadowa zniknela razem z zalegloscia"


# --- daniny: forma rozstrzyga, NIEROZSTRZYGNIETA odmawia -----------------

def test_forma_NIEROZSTRZYGNIETA_nie_liczy_danin_ale_LICZY_linie():
    """Specyfikacja §5.5: brak formy → nie liczy danin, pokazuje linie bez
    podatkow i MOWI TO WPROST. Odmowa calosci byla by przesada, cicha
    linia bez podatkow — klamstwem."""
    wynik = _zbuduj(forma=NIEROZSTRZYGNIETA)
    assert wynik.stan == prognoza_plynnosci.STAN_POLICZONA
    assert wynik.daniny_policzone is False
    assert any(z.rodzaj == prognoza_plynnosci.RODZAJ_DANINA
               for d in wynik.dni for z in d.zdarzenia) is False
    assert any("forma" in z.tekst.lower() for z in wynik.zastrzezenia)

    # SEDNO: „bez podatkow" znaczy linia WYZSZA, nie linia PLASKA. Ten
    # straznik dolozono po tym, jak 28 zielonych testow przepuscilo wersje,
    # w ktorej brak formy kasowal takze przychod — a plaska linia na kotwicy
    # czyta sie jako „nic nie wplynie" i produkuje falszywy alarm.
    przychody = [z for d in wynik.dni for z in d.zdarzenia
                 if z.rodzaj == prognoza_plynnosci.RODZAJ_PRZYCHOD_JDG]
    assert len(przychody) == 6, \
        f"bez formy linia dostala {len(przychody)} wplywow zamiast szesciu"
    z_forma = _zbuduj(forma=SKALA)
    assert wynik.dni[-1].saldo_ostrozne > z_forma.dni[-1].saldo_ostrozne, \
        "linia bez podatkow ma biec WYZEJ niz linia z podatkami"


def test_RYCZALT_i_SKALA_daja_ROZNE_daniny():
    """Kontrola dwustronna do testu wyzej i do calego Z58/Z59: silnik ma
    naprawde rozstrzygac po formie, a nie liczyc zawsze tak samo."""
    ze_skali = _zbuduj(forma=SKALA)
    z_ryczaltu = _zbuduj(forma=RYCZALT)
    assert _kwoty_zdarzen(ze_skali, "PIT"), "skala nie wyprodukowala zaliczki PIT"
    assert _kwoty_zdarzen(z_ryczaltu, "Ryczałt"), "ryczalt nie wyprodukowal podatku"
    assert not _kwoty_zdarzen(ze_skali, "Ryczałt")
    assert not _kwoty_zdarzen(z_ryczaltu, "PIT")


def test_daniny_licza_sie_OSOBNO_dla_kazdej_linii():
    """Specyfikacja §4.2: wyzszy przychod to wyzszy VAT i wyzsza zaliczka.
    To dwa pelne scenariusze, nie dwie linie przychodu na jednym koszcie."""
    wynik = _zbuduj()
    vaty = [(z.kwota_ostrozna, z.kwota_realna) for d in wynik.dni
            for z in d.zdarzenia if z.nazwa == "VAT"]
    assert vaty, "kontrola licznosci: zadnego zdarzenia VAT na osi"
    ostrozny, realny = vaty[0]
    assert realny < ostrozny, \
        f"VAT linii realnej ({realny}) nie jest wiekszy co do wartosci niz ostroznej ({ostrozny})"


def test_daniny_ida_na_termin_z_NOSNIKA_terminow():
    """Terminy pochodza z `terminy.TERMINY`, nie z liczby wpisanej tutaj.
    VAT za wrzesien = 25 pazdziernika (niedziela) → 26 pazdziernika."""
    wynik = _zbuduj()
    dni_vat = [d.data for d in wynik.dni
               for z in d.zdarzenia if z.nazwa == "VAT"]
    assert date(2026, 10, 26) in dni_vat, \
        f"VAT za wrzesien nie trafil na 26 pazdziernika; trafil na {dni_vat[:3]}"


# --- dzien domniemany ----------------------------------------------------

def test_pozycja_BEZ_dnia_platnosci_ma_dzien_DOMNIEMANY_i_liczbe():
    """Wydatek bez dnia laduje na 1., przychod na ostatni — ostroznie wg
    kierunku. To ZALOZENIE, wiec musi byc widoczne z liczba, a nie ukryte."""
    wynik = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_WYDATKI, "Zakupy", "500.00", None, ""),
        (2026, 9, budzet.TYP_PRZYCHODY, "Zwrot wydatków", "300.00", None, "")))
    assert wynik.dzien_domniemany is True
    domniemane = [z for z in wynik.zastrzezenia
                  if z.kod == prognoza_plynnosci.KOD_DZIEN_DOMNIEMANY]
    assert len(domniemane) == 1
    assert domniemane[0].liczba == 12, \
        f"pozycji bez dnia policzono {domniemane[0].liczba}, nie 12 (2 pozycje x 6 miesiecy)"

    wrzesien_1 = [z.nazwa for d in wynik.dni if d.data == date(2026, 9, 1)
                  for z in d.zdarzenia]
    wrzesien_30 = [z.nazwa for d in wynik.dni if d.data == date(2026, 9, 30)
                   for z in d.zdarzenia]
    assert "Zakupy" in wrzesien_1, "wydatek bez dnia nie trafil na 1."
    assert "Zwrot wydatków" in wrzesien_30, "przychod bez dnia nie trafil na ostatni"


def test_pozycja_Z_dniem_platnosci_NIE_jest_domniemana():
    """Kontrola dwustronna: zastrzezenie przy kazdym uruchomieniu przestaje
    sie czytac."""
    wynik = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_WYDATKI, "Zakupy", "500.00", 10, "")))
    assert wynik.dzien_domniemany is False
    assert not [z for z in wynik.zastrzezenia
                if z.kod == prognoza_plynnosci.KOD_DZIEN_DOMNIEMANY]


def test_dzien_31_pozycji_planu_trafia_w_LUTY():
    """Regula upubliczniona w Z61. Pozycja platna 31. bez tego wypada z osi
    dziennej BEZ SLADU — a luty jest w kazdym szesciomiesiecznym oknie."""
    wynik = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_WYDATKI, "Czynsz", "2000.00", 31, "")))
    luty = [z.nazwa for d in wynik.dni if d.data == date(2027, 2, 28)
            for z in d.zdarzenia]
    assert "Czynsz" in luty


# --- pierwszy dzien ujemny i minimum -------------------------------------

def test_pierwszy_dzien_UJEMNY_wskazany_na_linii_OSTROZNEJ():
    """R6: ostrzezenie zapala sie na ostroznej, realna sluzy do patrzenia."""
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 1),
                                           kwota=Decimal("100.00")),
        plan=_plan((2026, 9, budzet.TYP_WYDATKI, "Zakupy", "9000.00", 5, "")))
    assert wynik.pierwszy_dzien_ujemny == date(2026, 9, 5)
    assert wynik.minimum is not None and wynik.minimum < 0
    assert wynik.brakuje == -wynik.minimum


def test_ostrzezenie_zapala_sie_gdy_OSTROZNA_schodzi_a_realna_NIE():
    """R6 dosownie: ostrzezenie zapala sie na OSTROZNEJ, realna sluzy do
    patrzenia. Bez tego przypadku regula nie jest strzezona wcale — przy
    wydatku, ktory topi obie linie naraz, obie daja te sama odpowiedz
    i podmiana jednej na druga przechodzi bez sladu.

    120 h x 70 zl = 8 400 zl; 160 h x 70 zl = 11 200 zl. Kotwica 5 000 zl,
    wydatek 14 000 zl 5 pazdziernika: ostrozna -600 zl, realna +2 200 zl.
    """
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 1),
                                           kwota=Decimal("5000.00")),
        plan=_plan((2026, 10, budzet.TYP_WYDATKI, "Remont", "14000.00", 5, "")),
        forma=NIEROZSTRZYGNIETA)

    assert wynik.pierwszy_dzien_ujemny == date(2026, 10, 5)
    ten_dzien = [d for d in wynik.dni if d.data == date(2026, 10, 5)][0]
    assert ten_dzien.saldo_ostrozne < 0
    assert ten_dzien.saldo_realne > 0, \
        "przypadek nie rozroznia linii — straznik R6 nic by nie pilnowal"


def test_plynnosc_dodatnia_NIE_zglasza_dnia_ujemnego():
    """Kontrola dwustronna: ostrzezenie, ktore zapala sie zawsze, nie jest
    ostrzezeniem. `pierwszy_dzien_ujemny is None` przy `stan=policzona`
    to DOBRA wiadomosc — i dlatego nie moze byc tym samym nosnikiem
    co „nie liczylem" (`dni is None`)."""
    wynik = _zbuduj(kotwica=prognoza_plynnosci.Kotwica(
        data=date(2026, 9, 1), kwota=Decimal("500000.00")))
    assert wynik.pierwszy_dzien_ujemny is None
    assert wynik.brakuje is None
    assert wynik.dni is not None


# --- swiezosc kotwicy wg ZDARZENIA, nie kalendarza (R18) -----------------

def test_kotwica_po_ktorej_MINAL_termin_jest_NIEAKTUALNA():
    """R18. Kotwica z 19. jest nieprawdziwa nastepnego dnia o ZUS i zaliczke.
    Prog dniowy przemilczalby dobe, w ktorej zeszlo 4 500 zl."""
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 19),
                                           kwota=Decimal("10000.00")),
        zaleglosci=[podatki.PozycjaDoZaplaty(
            nazwa="ZUS", kwota=Decimal("2500.00"),
            termin=date(2026, 9, 21), za_okres=date(2026, 8, 1))],
        dzis=date(2026, 9, 22))
    assert wynik.stan == prognoza_plynnosci.STAN_NIEAKTUALNA
    assert wynik.dni is not None, "nieaktualna to nie to samo co nie policzona"


def test_kotwica_bez_zdarzenia_po_drodze_zostaje_AKTUALNA():
    """Kontrola dwustronna R18: kotwica z 26. wrzesnia jest w porzadku przez
    tydzien, bo nic z konta nie schodzi. Prog dniowy prosilby o odswiezenie
    w tygodniach bez zdarzen."""
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 26),
                                           kwota=Decimal("10000.00")),
        dzis=date(2026, 9, 29))
    assert wynik.stan == prognoza_plynnosci.STAN_POLICZONA


def test_PRZEWIDYWANY_wplyw_nie_czyni_kotwicy_nieaktualna():
    """R18 czytane doslownie: kotwica traci waznosc, gdy minal TERMIN DANINY
    albo DZIEN PLATNOSCI pozycji planu — nie gdy minal dzien, na ktory
    prognoza SAMA zalozyla wplyw.

    Roznica jest merytoryczna, nie formalna: danina i pozycja planu to
    zobowiazania, ktore albo zeszly z konta, albo sa przeterminowane.
    Przewidywany wplyw to zalozenie tej samej prognozy — proszenie o odswiezenie
    stanu konta, bo wlasne zalozenie sie „zdarzylo", to pytanie samego siebie
    o potwierdzenie.

    Kotwica 28 wrzesnia, dzis 2 pazdziernika: przychod JDG laduje 30 wrzesnia,
    czyli W OKNIE; daniny za wrzesien dopiero 20 i 26 pazdziernika.

    Dolozone po przebiegu mutacyjnym: mutacja M268 (przewidywany wplyw wchodzi
    do reguly swiezosci) PRZEZYLA komplet 708 testow, bo zaden nie wywolal
    tego stanu.
    """
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 28),
                                           kwota=Decimal("10000.00")),
        dzis=date(2026, 10, 2))

    w_oknie = [d.data for d in wynik.dni
               if date(2026, 9, 28) < d.data <= date(2026, 10, 2)
               for z in d.zdarzenia
               if z.rodzaj == prognoza_plynnosci.RODZAJ_PRZYCHOD_JDG]
    assert w_oknie == [date(2026, 9, 30)], \
        f"kontrola licznosci: w oknie mial byc jeden wplyw, jest {w_oknie}"
    assert wynik.stan == prognoza_plynnosci.STAN_POLICZONA, \
        "przewidywany wplyw uniewaznil kotwice — prognoza pyta samej siebie"


def test_kotwica_starsza_niz_SUFIT_jest_nieaktualna_mimo_ciszy():
    """Twardy sufit 31 dni z R18 — druga polowa reguly, obok zdarzen."""
    wynik = _zbuduj(
        kotwica=prognoza_plynnosci.Kotwica(data=date(2026, 9, 1),
                                           kwota=Decimal("10000.00")),
        plan=pd.DataFrame(), forma=NIEROZSTRZYGNIETA,
        dzis=date(2026, 10, 20))
    assert wynik.stan == prognoza_plynnosci.STAN_NIEAKTUALNA


# --- granica modulu ------------------------------------------------------

def test_modul_NIE_definiuje_wlasnego_formatowania_kwot():
    """Straznik obowiazkowy (ryzyko nr 7 planu): prognoza jako czwarty nosnik
    formatowania. Formatowanie ma jeden nosnik od Z51 — `rdzen/prezentacja.py`.
    Prognoza jest czysta arytmetyka i nie formatuje NICZEGO."""
    import re
    from pathlib import Path

    assert not hasattr(prognoza_plynnosci, "_zloty")
    zrodlo = Path(prognoza_plynnosci.__file__).read_text(encoding="utf-8")
    assert "prezentacja" not in zrodlo, "modul arytmetyczny siega po formatowanie"
    assert "wspolne" not in zrodlo, "modul arytmetyczny siega do pulpitu"
    # Kwota WSTAWIANA do napisu z waluta — a nie samo slowo „zl" w zdaniu.
    # Silnik ma prawo pisac zdania po polsku (specyfikacja §5.1 regula 3);
    # nie ma prawa SKLADAC z nich kwot, bo to czwarty nosnik formatowania.
    sklejone = re.findall(r"\{[^}]*\}\s*zł", zrodlo)
    assert sklejone == [], f"modul sklada kwote z waluta: {sklejone}"


def test_wszystkie_kwoty_wyniku_sa_DECIMAL_nigdy_float():
    """Kontrola licznosci: pomiar, do ktorego nic nie dociera, przechodzi
    kazda asercje „czegos tam nie ma"."""
    wynik = _zbuduj(plan=_plan(
        (2026, 9, budzet.TYP_WYDATKI, "Zakupy", "500.00", 10, "")))
    sprawdzone = 0
    for d in wynik.dni:
        for kwota in (d.saldo_ostrozne, d.saldo_realne):
            assert isinstance(kwota, Decimal), f"{kwota!r} nie jest Decimal"
            sprawdzone += 1
        for z in d.zdarzenia:
            for kwota in (z.kwota_ostrozna, z.kwota_realna):
                assert isinstance(kwota, Decimal), f"{kwota!r} nie jest Decimal"
                sprawdzone += 1
    assert sprawdzone > 360, f"sprawdzono {sprawdzone} kwot, za malo na 183 dni"

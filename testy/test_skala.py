"""Strazniki silnika skali podatkowej (Z58, plan formy Z30).

Po ustaleniu §0 planu formy skala jest sciezka PODSTAWOWA, nie alternatywna:
Darek byl na zasadach ogolnych przed zawieszeniem dzialalnosci, a milczenie
do 20.10.2026 utrwala je takze na lata nastepne.

CZTERY ROZNICE, KTORE LATWO PRZEOCZYC (plan formy §3):
1. Progi zdrowotnej 60/300 tys. NA SKALI NIE ISTNIEJA. Zdrowotna liczy sie
   od DOCHODU, nie od progu przychodu.
2. Zdrowotna na skali NIE JEST ODLICZALNA (od 2022). Na ryczalcie odlicza sie
   50% od przychodu — pomylenie tych regul psuje kazda fakture.
3. Kwota zmniejszajaca 3 600 zl bierze sie w CALOSCI, nie po 300 zl na miesiac.
   To straznik ODWROCONY wobec v0.2 planu, ktora kazala dokladnie odwrotnie.
   Podzial po 300 zl to mechanizm PLATNIKA (pracodawcy), nie samodzielnie
   liczonej zaliczki przedsiebiorcy.
4. Zaliczka narastajaco: podatek od dochodu od poczatku roku minus zaliczki
   juz naliczone. Zaliczka nieprzekraczajaca 1 000 zl nie tworzy obowiazku
   wplaty w tym miesiacu.
"""

from decimal import Decimal

import pytest

from silnik.rdzen import formy, magazyn, podatki, stawki

NETTO = Decimal("11200.00")
VAT = Decimal("0.23")
SPOLECZNE = stawki.suma_spolecznych(z_chorobowa=True)


def _skala(*, netto=NETTO, dochod_narastajaco="0", zaliczki="0",
           naliczone=False, koszty="0"):
    return podatki.policz_skala(
        kwota_netto=netto, stawka_vat=VAT,
        dochod_narastajaco=Decimal(dochod_narastajaco),
        zaliczki_juz_naliczone=Decimal(zaliczki),
        skladki_juz_naliczone_w_miesiacu=naliczone,
        koszty=Decimal(koszty))


# --- nazwy: `policz` staje sie wejsciem wspolnym -------------------------

def test_policz_ryczalt_ISTNIEJE_pod_nowa_nazwa():
    """Stara nazwa `policz` byla ryczaltowa. Po Z58 `policz` rozstrzyga
    po formie, a ryczalt ma wlasna, jawna nazwe."""
    w = podatki.policz_ryczalt(NETTO, Decimal("0.085"), VAT, Decimal("0"), False)
    assert w.pit == Decimal("767.00")


def test_policz_ROZSTRZYGA_po_formie():
    r = podatki.policz(magazyn.FORMA_RYCZALT, kwota_netto=NETTO,
                       stawka_ryczaltu=Decimal("0.085"), stawka_vat=VAT,
                       przychod_narastajaco=Decimal("0"),
                       skladki_juz_naliczone_w_miesiacu=False)
    s = podatki.policz(magazyn.FORMA_SKALA, kwota_netto=NETTO, stawka_vat=VAT,
                       dochod_narastajaco=Decimal("0"),
                       zaliczki_juz_naliczone=Decimal("0"),
                       skladki_juz_naliczone_w_miesiacu=False)
    assert r.pit != s.pit, "dwie formy dajace te sama kwote to znak, ze jedna z nich nie liczy"


def test_policz_przy_NIEROZSTRZYGNIETEJ_ODMAWIA():
    """Nie zgaduje. Precedens: `weryfikacja.sprawdz` przy ROZBIEZNE blokuje
    formularz zamiast liczyc z niepewnych stawek."""
    with pytest.raises(magazyn.BladMagazynu) as blad:
        podatki.policz(magazyn.FORMA_NIEROZSTRZYGNIETA, kwota_netto=NETTO)
    assert "form" in str(blad.value).lower()


# --- zaliczka narastajaco ------------------------------------------------

def test_kwota_zmniejszajaca_brana_w_CALOSCI_a_nie_po_300_zl():
    """STRAZNIK ODWROCONY wobec v0.2 planu formy.

    Brzmienie v0.2, doslownie: „Kwota zmniejszajaca 3 600 zl jest ROCZNA.
    W zaliczkach rozklada sie po 300 zl miesiecznie; wziecie jej w calosci
    w pierwszym miesiacu zanizyloby pierwsza zaliczke i zawyzylo kazda kolejna."
    To jest NIEPRAWDA dla zaliczek JDG — zrodlo `portal/00264`:
    „pomnóż podstawę opodatkowania przez 12% i odejmij 3600 zł".
    """
    w = _skala()
    dochod = NETTO - SPOLECZNE
    bez_zmniejszenia = stawki.STAWKA_SKALI_PIERWSZA * dochod
    assert w.podatek_narastajaco == max(
        Decimal("0"), bez_zmniejszenia - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK)
    assert w.podatek_narastajaco < bez_zmniejszenia - Decimal("300"), \
        "kwota zmniejszajaca wzieta po 1/12 zamiast w calosci"


def test_zaliczka_ODEJMUJE_juz_naliczone():
    """Sedno liczenia narastajaco: podatek od poczatku roku minus to,
    co juz naliczone. Bez tego kazdy miesiac placilby caly podatek roczny."""
    pierwsza = _skala()
    druga = _skala(dochod_narastajaco=str(NETTO - SPOLECZNE),
                   zaliczki=str(pierwsza.podatek_narastajaco))
    assert druga.zaliczka_przed_zaokragleniem == (
        druga.podatek_narastajaco - pierwsza.podatek_narastajaco)


def test_przejscie_PROGU_120_tys_w_srodku_roku():
    """Kryterium odbioru planu Z30. Dochod tuz pod progiem i tuz nad nim —
    czesc powyzej ma isc po 32%, nie cala kwota."""
    tuz_pod = stawki.PROG_SKALI - Decimal("1000")
    w = _skala(netto=Decimal("11000.00"),
               dochod_narastajaco=str(tuz_pod),
               naliczone=True)
    dochod = tuz_pod + Decimal("11000.00")
    oczekiwany = (stawki.STAWKA_SKALI_PIERWSZA * stawki.PROG_SKALI
                  + stawki.STAWKA_SKALI_DRUGA * (dochod - stawki.PROG_SKALI)
                  - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK)
    assert w.podatek_narastajaco == oczekiwany
    assert w.dochod_narastajaco > stawki.PROG_SKALI


def test_ponizej_progu_CALOSC_po_dwanascie_procent():
    """Kontrola dwustronna: stawka druga nie ma prawa dotknac dochodu
    ponizej progu."""
    w = _skala()
    assert w.podatek_narastajaco == max(
        Decimal("0"),
        stawki.STAWKA_SKALI_PIERWSZA * w.dochod_narastajaco
        - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK)


def test_zaliczka_do_1000_zl_NIE_TWORZY_obowiazku_wplaty():
    """Kryterium odbioru planu Z30. `portal/00264`: „mogą nie wpłacać zaliczki
    […] jeżeli podatek […] nie przekracza 1000 zł".

    Kwota jest jednak DALEJ NALICZONA — narzedzie do odkladania pieniedzy ma
    ja zarezerwowac, bo obowiazek wroci w kolejnym miesiacu."""
    w = _skala(netto=Decimal("4000.00"))
    assert w.zaliczka <= Decimal("1000")
    assert w.obowiazek_wplaty is False
    assert w.podatek_narastajaco == w.zaliczka_przed_zaokragleniem


def test_zaliczka_POWYZEJ_1000_zl_tworzy_obowiazek():
    """Kontrola dwustronna: zwolnienie ma dotyczyc wylacznie kwot malych.

    Kwota dobrana pomiarem, nie na oko: przy 30 000 zl netto podatek za
    pierwszy miesiac wynosi ZERO, bo caly miesci sie w kwocie zmniejszajacej
    (12% x 28 073,24 = 3 368,79 < 3 600). To poprawne zachowanie i osobny
    dowod na to, ze kwota zmniejszajaca idzie w calosci."""
    w = _skala(netto=Decimal("60000.00"))
    assert w.zaliczka > Decimal("1000")
    assert w.obowiazek_wplaty is True


def test_zaliczka_zaokraglona_do_PELNYCH_ZLOTYCH():
    """Art. 63 Ordynacji podatkowej — ta sama regula co przy ryczalcie."""
    w = _skala(netto=Decimal("30000.00"))
    assert w.zaliczka == w.zaliczka.quantize(Decimal("1"))
    assert w.zaliczka != w.zaliczka_przed_zaokragleniem or \
        w.zaliczka_przed_zaokragleniem == w.zaliczka_przed_zaokragleniem.quantize(Decimal("1"))


# --- zdrowotna -----------------------------------------------------------

def test_zdrowotna_liczona_od_DOCHODU_a_nie_z_progu_przychodu():
    """Roznica nr 1 i 3 z planu formy. Na ryczalcie skladka jest ryczaltowa
    i zalezy od progu przychodu; na skali rosnie liniowo z dochodem."""
    maly = _skala(netto=Decimal("20000.00"))
    duzy = _skala(netto=Decimal("60000.00"))
    assert duzy.zdrowotna > maly.zdrowotna, \
        "zdrowotna na skali ma rosnac razem z dochodem"
    assert duzy.zdrowotna == stawki.do_groszy(
        stawki.STAWKA_ZDROWOTNEJ_SKALA * duzy.dochod_miesiaca)


def test_MINIMALNA_zdrowotna_przy_dochodzie_bliskim_zeru():
    """Kryterium odbioru planu Z30. Dochod ponizej progu nie zwalnia
    ze skladki — jest minimum miesieczne."""
    w = _skala(netto=Decimal("2000.00"))
    assert w.dochod_miesiaca <= Decimal("0") or w.dochod_miesiaca < Decimal("5000")
    assert w.zdrowotna == stawki.ZDROWOTNA_MIN_MIESIECZNA


def test_zdrowotna_NIE_JEST_ODLICZANA_od_podstawy():
    """Roznica nr 2 z planu formy, potwierdzona `portal/001052`:
    „Przedsiebiorcy opodatkowani wedlug skali podatkowej nie moga odliczyc".

    Na ryczalcie odlicza sie 50% zdrowotnej od przychodu — gdyby ta sama regula
    trafila na skale, podstawa bylaby zanizona przy kazdej fakturze.
    """
    w = _skala()
    assert w.dochod_miesiaca == NETTO - SPOLECZNE, \
        "zdrowotna weszla do podstawy — na skali nie ma prawa"


def test_PROGI_60_i_300_tys_NIE_dotycza_skali():
    """Roznica nr 1: te progi sa ryczaltowe. Ta sama skladka zdrowotna
    po obu stronach progu 60 tys. dowodzi, ze silnik ich nie uzywa."""
    pod = _skala(netto=Decimal("10000.00"), dochod_narastajaco="0")
    nad = _skala(netto=Decimal("10000.00"), dochod_narastajaco="100000")
    assert pod.zdrowotna == nad.zdrowotna, \
        "zdrowotna zmienila sie z przychodem narastajaco — to regula RYCZALTU"


# --- skladki naliczone raz na miesiac -------------------------------------

def test_druga_faktura_w_miesiacu_NIE_nalicza_skladek_drugi_raz():
    druga = _skala(naliczone=True)
    assert druga.spoleczne == Decimal("0.00")
    assert druga.zdrowotna == Decimal("0.00")


# --- kontrola krzyzowa z `formy.py` ---------------------------------------

def test_suma_DWUNASTU_zaliczek_rowna_sie_podatkowi_rocznemu():
    """KONTROLA KRZYZOWA wymagana przez plan Z30.

    Dwa niezalezne silniki liczace te sama rzecz z dwoch stron: `policz_skala`
    miesiac po miesiacu i `formy.porownaj_formy` raz na rok. Rozjazd znaczy,
    ze jeden z nich zle rozumie skale — i to jest jedyny sposob, zeby sie o tym
    dowiedziec bez urzedu skarbowego.

    PRZED zaokragleniem: rownosc co do grosza. PO zaokragleniu: tolerancja
    +/-12 zl, bo dwanascie niezaleznych zaokraglen do pelnych zlotych
    (art. 63 Ordynacji). Zadanie rownosci co do grosza byloby straznikiem,
    ktory pada na POPRAWNYM kodzie.
    """
    miesieczne = Decimal("11200.00")
    dochod = Decimal("0")
    zaliczki_dokladne = Decimal("0")
    suma_przed = Decimal("0")
    suma_po = Decimal("0")
    ile = 0

    for _ in range(12):
        w = podatki.policz_skala(
            kwota_netto=miesieczne, stawka_vat=VAT,
            dochod_narastajaco=dochod,
            zaliczki_juz_naliczone=zaliczki_dokladne,
            skladki_juz_naliczone_w_miesiacu=False)
        suma_przed += w.zaliczka_przed_zaokragleniem
        suma_po += w.zaliczka
        zaliczki_dokladne += w.zaliczka_przed_zaokragleniem
        dochod = w.dochod_narastajaco
        ile += 1

    assert ile == 12, "kontrola licznosci: dwanascie miesiecy, nie mniej"

    roczny = next(f for f in formy.porownaj_formy(miesieczne * 12, miesiecy=12)
                  if f.nazwa == "skala")

    # SPROSTOWANIE ZALOZENIA PLANU. Plan Z30 zada rownosci „sumy dwunastu
    # zaliczek PRZED zaokragleniem" z podatkiem rocznym z `formy.py`. Pomiar
    # pokazuje, ze `formy.py` sam JUZ ZAOKRAGLA do pelnych zlotych
    # (`_wynik` wola `stawki.do_zlotych`), wiec rownosc co do grosza jest
    # nieosiagalna z definicji: 9 753,47 kontra 9 753. Porownanie idzie wiec
    # po JEDNYM zaokragleniu z obu stron — to ta sama tresc, bez fikcji.
    assert stawki.do_zlotych(suma_przed) == roczny.pit, \
        f"miesieczne {suma_przed} (-> {stawki.do_zlotych(suma_przed)}) " \
        f"vs roczne {roczny.pit}"

    # PO zaokragleniu kazdej z dwunastu zaliczek osobno: tolerancja +/-12 zl.
    # Zadanie rownosci co do grosza byloby straznikiem padajacym na POPRAWNYM
    # kodzie (dwanascie niezaleznych zaokraglen, art. 63 Ordynacji).
    assert abs(suma_po - roczny.pit) <= Decimal("12"), \
        f"suma zaokraglonych {suma_po} vs roczne {roczny.pit}"


# --- pokrycie mechanizmem weryfikacji -------------------------------------

def test_stale_skali_SA_sprawdzane_u_zrodla():
    """WARUNEK UKONCZENIA z planu Z30, nie ozdoba.

    Pomiar 2026-08-26: `oczekiwane_wartosci()` sprawdzalo 10 liczb i ANI JEDNEJ
    stalej skali. Aplikacja dostawalaby drugi silnik podatkowy z ZEROWYM
    pokryciem mechanizmu, ktory pierwszy silnik ma — i to silnik, ktory po
    ustaleniu §0 jest sciezka podstawowa.
    """
    from silnik.rdzen import weryfikacja

    url = stawki.ZRODLA["skala"].url
    assert "00264" in url, f"zrodlo skali wskazuje {url}"

    wartosci = weryfikacja.oczekiwane_wartosci()
    assert url in wartosci, "strona skali nie jest w ogole sprawdzana"
    assert len(wartosci[url]) == 6, \
        f"stalych skali jest {len(wartosci[url])}, ma byc szesc"

    for stala in (stawki.PROG_SKALI, stawki.KWOTA_ZMNIEJSZAJACA_PODATEK,
                  stawki.ZDROWOTNA_MIN_MIESIECZNA):
        assert stala in wartosci[url], f"{stala} nie jest sprawdzana u zrodla"

"""Strazniki rezerwy na podatki liczonej jako SALDO.

Decyzja Darka D3 (2026-08-25, godz. 22:05, `docs/plan-integracji-jdg-budzet.md`
par. 9): rezerwa to NALICZONE MINUS ZAPLACONE, nie suma naliczonych. Powod
z jego slow: „podatek VAT naliczany jest za dany miesiac, a nastepnie jest
20 dni na jego zaplacenie" — czyli pytanie brzmi „ile jeszcze nie zaplacilem",
a nie „ile sie naliczylo od poczatku bazy".

Wada, ktora to zamyka: do 2026-08-25 kafel sumowal VAT i ZUS ze WSZYSTKICH
faktur i nigdy nie schodzil w dol. Po wprowadzeniu ujecia kasowego (D1)
zaplacony podatek staje sie wydatkiem, a kafel dalej liczylby go jako
niezaplacony — liczba roslaby w nieskonczonosc.
"""

from datetime import date
from decimal import Decimal

import pandas as pd

from silnik.rdzen import budzet, podatki


#: ZMIANA Z55, jawnie. Do Z55 rezerwa liczyla ZUS z kolumny `zaplacony_zus`,
#: wiec fikstura nie potrzebowala ani daty faktury, ani okresu dzialalnosci.
#: Teraz ZUS liczy sie z MIESIECY, wiec i jedno, i drugie jest obowiazkowe.
#:
#: Liczby asertowane w tym pliku ZOSTAJA TE SAME i to nie przypadek: okres to
#: jeden miesiac, a skladka za jeden miesiac na progu 1 wynosi dokladnie
#: 2 425,11 zl — tyle, ile niosla kolumna `zaplacony_zus` tej faktury. Zmienil
#: sie POWOD tej liczby, nie ona sama. Straznik nowej reguly (trzy miesiace,
#: dwie faktury → 7 275,33 zl) stoi w `testy/test_rezerwa_zus.py`.
DATA_FV = "2026-08-25"
DZIALALNOSC_OD = date(2026, 8, 1)
KONIEC_SIERPNIA = date(2026, 8, 31)


def _rezerwa(faktury, koszty, wpisy):
    """Rezerwa dla JEDNEGO miesiaca dzialalnosci NA RYCZALCIE.

    ZMIANA Z59: forma jest teraz argumentem obowiazkowym — rezerwa przestala
    ZAKLADAC ryczalt. Ten plik zostaje przy ryczalcie swiadomie, bo wszystkie
    jego liczby wyprowadzono z silnika ryczaltowego; straznicy skali stoja
    w `testy/test_rezerwa_forma.py` i `testy/test_skala.py`.
    """
    return podatki.rezerwa_na_podatki(faktury, koszty, wpisy,
                                      dzialalnosc_od=DZIALALNOSC_OD,
                                      dzis=KONIEC_SIERPNIA,
                                      forma="RYCZALT",
                                      stawka_ryczaltu=Decimal("0.085"))


def _faktury(*trojki) -> pd.DataFrame:
    """(netto, vat, zus, zysk) — kolumny jak w tabeli przychody_jdg."""
    return pd.DataFrame([
        {"data": DATA_FV, "kwota_netto": Decimal(n), "kwota_vat": Decimal(v),
         "zaplacony_zus": Decimal(z), "zysk_netto": Decimal(y)}
        for n, v, z, y in trojki
    ])


def _koszty(*pary) -> pd.DataFrame:
    return pd.DataFrame([
        {"kwota_netto": Decimal(n), "kwota_vat": Decimal(v)} for n, v in pary
    ])


def _wpisy(*trojki) -> pd.DataFrame:
    """(typ, kategoria, kwota) — wpisy budzetu."""
    return pd.DataFrame([
        {"data": "2026-08-20", "typ": t, "kategoria": k, "kwota": Decimal(kw),
         "szczegoly": ""}
        for t, k, kw in trojki
    ])


#: Faktura Darka FV 1/2026: netto 11 200, VAT 2 576, ZUS 2 425,11,
#: zysk 8 007,89 — czyli ryczalt 767,00.
FV = ("11200.00", "2576.00", "2425.11", "8007.89")


# --- odzyskanie kwoty ryczaltu --------------------------------------------

def test_ryczalt_odzyskany_z_faktury_zgadza_sie_z_silnikiem():
    """Tabela faktur NIE trzyma kwoty ryczaltu — da sie ja odzyskac
    z tozsamosci `zysk = netto - zus - pit`. To odwrocenie `policz`,
    nie oszacowanie; ten test wiaze jedno z drugim, zeby zmiana silnika
    nie rozjechala sie po cichu z odczytem."""
    w = podatki.policz_ryczalt(Decimal("11200.00"), Decimal("0.085"), Decimal("0.23"),
                       Decimal("0"), False)
    odzyskany = podatki.ryczalt_z_faktury(
        kwota_netto=w.kwota_netto,
        zaplacony_zus=w.zdrowotna + w.spoleczne,
        zysk_netto=w.do_dyspozycji)
    assert odzyskany == w.pit


# --- naliczone ------------------------------------------------------------

def test_naliczone_to_vat_plus_zus_plus_podatek_dochodowy():
    """Do 2026-08-25 kafel pomijal ryczalt i przez to zanizal zobowiazanie."""
    r = _rezerwa(_faktury(FV), pd.DataFrame(), pd.DataFrame())
    assert r.vat_nalezny == Decimal("2576.00")
    assert r.zus == Decimal("2425.11")
    assert r.podatek_dochodowy == Decimal("767.00")
    assert r.naliczone_razem == Decimal("5768.11")


def test_vat_naliczony_pomniejsza_zobowiazanie():
    r = _rezerwa(_faktury(FV), _koszty(("4000.00", "920.00")),
                                   pd.DataFrame())
    assert r.vat_naliczony == Decimal("920.00")
    assert r.vat_do_zaplaty == Decimal("1656.00")
    assert r.naliczone_razem == Decimal("4848.11")


def test_nadwyzka_vat_naliczonego_nie_zjada_zus_ani_ryczaltu():
    """VAT do zwrotu to inna sprawa i inny wniosek do urzedu. Ujemny VAT
    przelewany na ZUS zanizylby rezerwe na skladki, ktore i tak trzeba
    zaplacic w calosci."""
    r = _rezerwa(_faktury(FV), _koszty(("40000.00", "9200.00")),
                                   pd.DataFrame())
    assert r.vat_do_zaplaty == Decimal("0.00")
    assert r.naliczone_razem == Decimal("3192.11")   # sam ZUS + ryczalt


# --- saldo ----------------------------------------------------------------

def test_zaplata_pomniejsza_saldo():
    zaplaty = _wpisy((budzet.TYP_WYDATKI, budzet.KATEGORIA_PODATKI, "2576.00"))
    r = _rezerwa(_faktury(FV), pd.DataFrame(), zaplaty)
    assert r.zaplacone == Decimal("2576.00")
    assert r.saldo == Decimal("3192.11")


def test_nadplata_daje_saldo_ujemne_a_nie_zero():
    """Nadplata jest prawdziwa informacja. Uciecie do zera zamienia
    „masz u urzedu 800 zl" na „jestes na zero" — i te 800 zl znika."""
    zaplaty = _wpisy((budzet.TYP_WYDATKI, budzet.KATEGORIA_PODATKI, "6568.11"))
    r = _rezerwa(_faktury(FV), pd.DataFrame(), zaplaty)
    assert r.saldo == Decimal("-800.00")


def test_zaplata_liczy_sie_TYLKO_z_kategorii_podatkowej():
    """Zakupy i czynsz nie sa zaplata podatku. Bez filtra kazdy wydatek
    zbijalby rezerwe i kafel pokazywalby zero przez cale zycie."""
    zaplaty = _wpisy(
        (budzet.TYP_WYDATKI, budzet.KATEGORIA_PODATKI, "1000.00"),
        (budzet.TYP_WYDATKI, "Zakupy", "9999.00"),
        (budzet.TYP_PRZYCHODY, budzet.KATEGORIA_PODATKI, "5000.00"),
    )
    r = _rezerwa(_faktury(FV), pd.DataFrame(), zaplaty)
    assert r.zaplacone == Decimal("1000.00")


def test_pusta_baza_BEZ_dzialalnosci_daje_same_zera():
    """ZMIANA Z55, jawnie. Stare brzmienie testu, doslownie:
    `test_pusta_baza_daje_same_zera` — `_rezerwa(pusta, pusta, pusta)` dawalo
    same zera, bo ZUS liczyl sie z faktur, a faktur nie bylo.

    Po Z55 „pusta baza" przestala byc jednym stanem. Bez daty rozpoczecia
    dzialalnosci wszystko jest zerem — bo nie wiadomo nic. Z data zerem NIE
    JEST, i to jest sedno naprawy: skladke placi sie za miesiac dzialalnosci,
    nie za miesiac przychodu. Kontrola dwustronna nizej."""
    r = podatki.rezerwa_na_podatki(
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
        dzialalnosc_od=None, dzis=KONIEC_SIERPNIA,
        forma="RYCZALT", stawka_ryczaltu=Decimal("0.085"))
    assert (r.naliczone_razem, r.zaplacone, r.saldo) == \
        (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    assert r.miesiace_zus is None


def test_pusta_baza_Z_dzialalnoscia_NIE_daje_zera():
    """Kontrola dwustronna: miesiac bez faktury ma skladke."""
    r = _rezerwa(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert r.miesiace_zus == 1
    assert r.zus > Decimal("0.00")
    assert r.saldo == r.zus


# --- kategoria jest jednym nosnikiem --------------------------------------

def test_kategoria_podatkowa_jest_na_liscie_startowej():
    """Bez niej nie da sie wpisac zaplaty, a saldo nigdy nie spada."""
    assert budzet.KATEGORIA_PODATKI in budzet.KATEGORIE_STARTOWE["Wydatki"]


# --- jeden nosnik: kafel i doradca musza podawac TE SAMA kwote -------------

def test_doradca_i_pulpit_podaja_te_sama_rezerwe(tmp_path):
    """Do 2026-08-25 formula rezerwy stala przepisana w DWOCH miejscach:
    `pulpit/dashboard.py:141` i `rdzen/narzedzia.py:75`. Poprawienie jednej
    kopii sprawiloby, ze doradca odpowiada inna kwota, niz pokazuje ekran,
    a uzytkownik nie ma jak zgadnac, ktora jest prawdziwa.

    Dane dobrane tak, zeby STARA formula (VAT + ZUS, bez ryczaltu i bez
    odjecia zaplat) dawala inny wynik niz nowa — inaczej test przeszedlby
    takze po cofnieciu naprawy.
    """
    from datetime import date

    from silnik.rdzen import magazyn, narzedzia

    p = magazyn.polacz(tmp_path / "rezerwa.db")
    magazyn.zapisz_fakture(
        p, data=date(2026, 8, 25), numer_faktury="FV/1/2026",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    magazyn.zapisz_wpis(p, data=date(2026, 8, 20), typ=budzet.TYP_WYDATKI,
                        kategoria=budzet.KATEGORIA_PODATKI,
                        kwota=Decimal("1000.00"), szczegoly="VAT za lipiec")

    magazyn.zapisz_dzialalnosc_od(p, DZIALALNOSC_OD)

    z_narzedzia = narzedzia.zbuduj(p)["stan_finansow"]()["zarezerwowane_na_podatki"]
    # Ten sam zbieracz, ktorego uzywa narzedzie doradcy — i to jest tresc
    # tego straznika. Po Z55 rezerwa zalezy takze od daty dzialalnosci
    # i od DZISIEJSZEJ daty; dwie drogi do tej liczby musza brac oba
    # argumenty z tego samego miejsca, inaczej ekran i doradca rozjada sie
    # nie na formule, tylko na wejsciu.
    wprost = podatki.rezerwa_z_bazy(p)

    assert z_narzedzia == f"{wprost.saldo:.2f}"
    stara_formula = Decimal("2576.00") + Decimal("2425.11")
    assert wprost.saldo != stara_formula, \
        "dane testowe nie odrozniaja nowej formuly od starej"

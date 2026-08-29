# -*- coding: utf-8 -*-
"""STRAZNICY WIERSZA „PLYNNOSC" NA KARCIE „Co ruszy ten wpis" (D-62).

DLACZEGO TEN WIERSZ ISTNIEJE. Po D-20 i D-61 wpis, ktory miesci sie w planie,
NIE ZMIENIA sumy prognozy — konsumuje pozycje planu, ktora i tak miala byc
zaplacona. Uzytkownik wpisuje 274,06 zl, patrzy na Plynnosc, widzi te sama
liczbe i **nie ma jak odroznic poprawnego dzialania od awarii zapisu**.
Karta milczala akurat w tym stanie, w ktorym milczenie klamie najbardziej.

CZEGO PILNUJA TE TESTY — i to jest wazniejsze niz brzmienia. Pilnuja, ze
**wielkosc w zdaniu rowna sie ruchowi, ktory uzytkownik zobaczy na Plynnosci**.
Zdanie „nizej o 170,00 zl" jest prawdziwe wtedy i tylko wtedy, gdy prognoza
schodzi o 170,00 zl — a nie o 500,00 zl (kwota wpisu) ani o 330,00 zl (pozycja
planu). Obie te liczby leza w zasiegu reki i obie wygladaja wiarygodnie.
Dlatego kazdy przypadek jest sprawdzany DWA RAZY: raz na tresci zdania,
raz na roznicy dwoch odczytow `/api/plynnosc` wokol prawdziwego zapisu.

To jest §3.5 konstytucji projektu: etykieta opisuje liczbe, ktora pokazuje,
a stan wyjatkowy podaje WIELKOSC, nie samo slowo.
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.index import aplikacja
from silnik.rdzen import magazyn

DZIS = "2026-10-06"

#: Spacja NIEROZDZIELAJACA (U+00A0) przed „zl" i w separatorze tysiecy —
#: `prezentacja.SEPARATOR_TYSIECY`. Stoi w oczekiwanych brzmieniach jawnie,
#: bo kwota rozerwana miedzy wierszami przestaje byc kwota. DLUG NAZWANY:
#: ramki i `interfejs/lib/kwota.ts` niosa zwykla spacje (U+0020), wiec strona
#: Pythona odstaje; przypina to `test_kontrakt_dwa_nosniki.py::
#: test_dwa_nosniki_formatowania_kwoty_sa_PRZYPIETE`. Ten plik tego sporu
#: NIE rozstrzyga — czyta stan faktyczny.

#: Pozycja planu z pomiaru odbiorczego Jacka: „Energia Elektryczna",
#: 330,00 zl na 20 X. Wszystkie trzy przypadki D-62 licza sie wobec niej.
PLAN_KWOTA = Decimal("330.00")
PLAN_DZIEN = 20


@pytest.fixture
def klient(tmp_path, monkeypatch):
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(polaczenie, rok=2026, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_dzialalnosc_od(polaczenie, date(2026, 9, 1))
    magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 10, 5),
                              kwota=Decimal("9920.79"))
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki",
        kategoria="Energia Elektryczna", kwota_planowana=PLAN_KWOTA,
        dzien=PLAN_DZIEN)
    polaczenie.close()
    return TestClient(aplikacja)


def _wpis(kwota: str, kategoria: str = "Energia Elektryczna") -> dict:
    return {"data": DZIS, "typ": "Wydatki", "kategoria": kategoria,
            "kwota": kwota}


def _wiersz_plynnosci(klient, kwota: str, kategoria="Energia Elektryczna") -> dict:
    odpowiedz = klient.post(f"/api/wpisy/podglad?dzis={DZIS}",
                            json=_wpis(kwota, kategoria))
    assert odpowiedz.status_code == 200, odpowiedz.text[:200]
    wiersze = odpowiedz.json()["wiersze"]
    assert len(wiersze) == 5, f"karta ma {len(wiersze)} wierszy zamiast pieciu"
    wiersz = wiersze[-1]
    assert wiersz["etykieta"] == "Płynność", (
        f"ostatni wiersz to {wiersz['etykieta']!r}, nie Płynność")
    return wiersz


# --- TRZY PRZYPADKI, kazdy z pelnym brzmieniem ---------------------------

def test_wpis_MIESCI_SIE_w_planie_mowi_o_dacie_i_o_RESZCIE_pozycji(klient):
    """Wielkosc jest tu potrojna i kazda czesc jest inna liczba: ile wchodzi
    (274,06), ile wynosi pozycja planu (330,00) i ile z niej ZOSTAJE (55,94).

    Trzecia liczba jest sednem. Wpis 274,06 zl NIE przesuwa calej pozycji
    na dzis — D-61 mowi „konsumuje AZ DO ZERA", wiec 55,94 zl zostaje na
    20 X i uzytkownik ten wyplyw na Plynnosci ZOBACZY. Zdanie, ktore
    mowiloby „pozycja przesuwa sie na 6 X", byloby falszem widocznym
    na sasiednim ekranie.
    """
    assert _wiersz_plynnosci(klient, "274.06")["wyjasnienie"] == (
        "bez zmian co do sumy — 274,06 zł wchodzi na 6 października "
        "w miejsce pozycji planu 330,00 zł z 20 października; "
        "zostaje z niej 55,94 zł na 20 października")


def test_wpis_zjadajacy_CALA_pozycje_mowi_ze_schodzi_ona_z_osi(klient):
    """Druga strona przypadku wyzej. Bez tego testu zdanie o reszcie moglo by
    zawsze mowic „zostaje 0,00 zl na 20 X" — czyli obiecywac wyplyw, ktorego
    juz nie ma."""
    assert _wiersz_plynnosci(klient, "330.00")["wyjasnienie"] == (
        "bez zmian co do sumy — 330,00 zł wchodzi na 6 października "
        "w miejsce pozycji planu 330,00 zł z 20 października; "
        "pozycja schodzi z osi w całości")


def test_wpis_PRZEKRACZAJACY_plan_podaje_NADWYZKE_a_nie_kwote_wpisu(klient):
    """Zmierzone przez Jacka w przegladarce: wpis 500,00 zl przy planie
    330,00 zl obniza `saldoMinimalne` o 170,00 zl, a nie o 500,00 zl.
    Zdanie ma podac te liczbe, ktora zobaczy uzytkownik."""
    assert _wiersz_plynnosci(klient, "500.00")["wyjasnienie"] == (
        "niżej o 170,00 zł — o tyle wydatek przekracza pozycję planu "
        "330,00 zł z 20 października")
    assert _wiersz_plynnosci(klient, "374.06")["wyjasnienie"] == (
        "niżej o 44,06 zł — o tyle wydatek przekracza pozycję planu "
        "330,00 zł z 20 października")


def test_kategoria_BEZ_pozycji_planu_obciaza_os_w_calosci(klient):
    assert _wiersz_plynnosci(klient, "274.06", "Zakupy")["wyjasnienie"] == (
        "niżej o 274,06 zł — kategoria nie ma pozycji planu na ten miesiąc")


# --- dwa stany dolozone: kategoria spoza osi i pusta kwota ---------------

def test_kategoria_SPOZA_OSI_nie_udaje_braku_planu(klient):
    """„Podatki i ZUS" nie wchodzi na os, bo daniny silnik liczy z faktur
    (`prognoza_plynnosci._wpisy_wg_miesiaca`). To NIE JEST to samo, co brak
    pozycji planu — zlanie obu stanow w jedno zdanie mowiloby uzytkownikowi,
    ze ma dolozyc plan, ktory i tak niczego by nie zmienil."""
    zdanie = _wiersz_plynnosci(klient, "274.06", "Podatki i ZUS")["wyjasnienie"]
    assert zdanie == ("bez zmian — daniny i przychód z faktur liczy silnik "
                      "z własnych źródeł, nie z wpisów")
    assert "nie ma pozycji planu" not in zdanie


def test_pusta_kwota_NIE_oglasza_spadku_o_zero(klient):
    """Karta na wejsciu, zanim uzytkownik cokolwiek wpisal. „Nizej o 0,00 zl"
    byloby falszywym alarmem w stanie, ktory nie jest zadnym alarmem."""
    assert _wiersz_plynnosci(klient, "0.00")["wyjasnienie"] == (
        "bez zmian — dopóki nie wpiszesz kwoty, nie ma czego przeliczyć")


# --- SEDNO: wielkosc w zdaniu rowna sie ruchowi na Plynnosci -------------

def _wielkosc_ze_zdania(zdanie: str) -> "Decimal | None":
    """Liczba, ktora uzytkownik PRZECZYTA po slowie „nizej/wyzej o".

    Czytana ze ZDANIA, nie z pola odpowiedzi — bo to zdanie jest tym, co
    trafia na ekran. Straznik czytajacy pole obok mierzylby posrednika.
    """
    trafienie = re.search(
        "(niżej|wyżej) o ([0-9\\s ]+,[0-9]{2})\\s*zł", zdanie)
    if trafienie is None:
        return None
    return Decimal(trafienie.group(2).replace(" ", "")
                   .replace(" ", "").replace(",", "."))


@pytest.mark.parametrize("kwota,kategoria", [
    ("274.06", "Energia Elektryczna"),   # miesci sie w planie
    ("330.00", "Energia Elektryczna"),   # zjada pozycje w calosci
    ("374.06", "Energia Elektryczna"),   # przekracza o 44,06
    ("500.00", "Energia Elektryczna"),   # przekracza o 170,00
    ("274.06", "Zakupy"),                # bez pozycji planu
])
def test_WIELKOSC_w_zdaniu_ROWNA_SIE_ruchowi_ktory_zobaczy_uzytkownik(
        klient, kwota, kategoria):
    """Bramka odbioru D-62 punkt 2, sprawdzona zachowaniem, nie deklaracja.

    Zdanie zapowiada ruch; potem wpis idzie do bazy naprawde i porownujemy
    zapowiedz z roznica dwoch odczytow `/api/plynnosc`. Wielkosc wzieta
    z innego rachunku niz ten, ktory ja opisuje, jest wada — i wlasnie ten
    test ja lapie. Dwie liczby-pulapki leza w zasiegu reki i obie wygladaja
    wiarygodnie: kwota wpisu (500,00) i kwota pozycji planu (330,00).

    Mierzymy KONIEC osi, nie `saldoMinimalne`: zdanie mowi „co do sumy",
    a suma miesiaca widac na ostatnim punkcie wykresu. `saldoMinimalne`
    zmienia sie takze od przesuniecia DATY wyplywu, czyli od czegos, czego
    to zdanie swiadomie nie obiecuje.
    """
    zapowiedz = _wielkosc_ze_zdania(
        _wiersz_plynnosci(klient, kwota, kategoria)["wyjasnienie"])

    przed = klient.get(f"/api/plynnosc?dzis={DZIS}").json()
    zapisany = klient.post(f"/api/wpisy?dzis={DZIS}",
                           json=_wpis(kwota, kategoria))
    assert zapisany.status_code == 200, zapisany.text[:200]
    po = klient.get(f"/api/plynnosc?dzis={DZIS}").json()

    # kontrola licznosci: oba odczyty maja co pokazywac
    assert len(przed["wykres"]) > 30 and len(po["wykres"]) == len(przed["wykres"]), (
        f"pomiar bez wykresu niczego nie porownuje: "
        f"{len(przed['wykres'])} wobec {len(po['wykres'])} punktow")

    ruch = (Decimal(po["wykres"][-1]["saldo"])
            - Decimal(przed["wykres"][-1]["saldo"]))
    oczekiwana = Decimal("0.00") if zapowiedz is None else -zapowiedz
    assert ruch == oczekiwana, (
        f"karta zapowiedziala {oczekiwana}, a prognoza ruszyla sie o {ruch} "
        f"(wpis {kwota} w kategorii {kategoria})")


def test_czytacz_wielkosci_NAPRAWDE_wyjmuje_liczbe_ze_zdania():
    """Kontrola dwustronna. Bez niej `_wielkosc_ze_zdania` mogloby zwracac
    `None` zawsze — a wtedy kazdy przypadek testu wyzej porownywalby zero
    z zerem i przechodzil takze wtedy, gdy zdanie klamie."""
    assert _wielkosc_ze_zdania(
        "niżej o 170,00 zł — o tyle wydatek przekracza") == Decimal("170.00")
    assert _wielkosc_ze_zdania(
        "wyżej o 1 234,56 zł — cokolwiek") == Decimal("1234.56")
    assert _wielkosc_ze_zdania("bez zmian co do sumy — 274,06 zł wchodzi") is None

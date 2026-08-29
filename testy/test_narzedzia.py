"""Straznicy narzedzi doradcy.

Najwazniejszy test w calym projekcie: zadne narzedzie nie zwraca nazwy klienta
ani numeru faktury. To nie jest ostroznosc - to par. 7 ust. 4 lit. a umowy B2B
z NMI ERP (tajemnica o klientach, 3 lata po zakonczeniu umowy).

Zabezpieczenie ma byc STRUKTURALNE: nazwa nie moze wyjechac, bo nie istnieje
na sciezce wyjscia. Nie regulaminowe, czyli "model zostal poproszony, zeby nie".
"""
from datetime import date
from decimal import Decimal

import pytest

from silnik.rdzen import budzet, magazyn, narzedzia, podatki

POLA_ZAKAZANE = {"kontrahent", "klient", "nazwa_klienta", "numer_faktury",
                 "numer", "opis", "tresc", "nazwa_transakcji", "nazwa_aktywa",
                 "nazwa",
                 # Dopisane w Zadaniu 21: kolumna `szczegoly` wpisu budzetu to
                 # pole tekstowe, w ktore uzytkownik wpisuje, czego wydatek
                 # dotyczyl - a wiec potencjalnie nazwe kontrahenta.
                 "szczegoly"}

NAZWA_KLIENTA = "NMI ERP sp. z o.o."


@pytest.fixture(autouse=True)
def zrodla_bez_sieci(monkeypatch):
    """ZNALEZISKO Z77 (P3): dwa testy tego pliku chodzily do sieci.

    `narzedzia.stan_stawek` wola `weryfikacja.sprawdz()`, ktore odpytuje
    PIEC stron rzadowych z limitem 20 s kazda. Do Z77 nie bylo tu zadnego
    szwu, wiec zachowanie zalezalo od tego, czy podreczny zapis w katalogu
    domowym czlowieka byl swiezszy niz 24 godziny: przy swiezym — odczyt
    z pliku, przy przeterminowanym — piec zadan HTTP z suity jednostkowej.
    Ten sam tryb awarii, ktory Z76 nazwal przy trasie: straznik byl ZEGAREM.

    Wykryla to fikstura `bez_sieci` z `conftest.py`, dolozona w tym samym
    zadaniu. Pusta strona daje raport ROZBIEZNE — struktura wyniku, ktorej
    oba testy pilnuja, jest ta sama co przy ZGODNE, a wynik przestal zalezec
    od pory doby i od stanu sieci.
    """
    from silnik.rdzen import weryfikacja

    monkeypatch.setattr(weryfikacja, "_pobierz", lambda url: "")


@pytest.fixture
def polaczenie(tmp_path):
    p = magazyn.zmigruj_i_polacz(tmp_path / "n.db")
    magazyn.zapisz_fakture(
        p, data=date(2026, 9, 30), numer_faktury=f"FV/1/2026 dla {NAZWA_KLIENTA}",
        kwota_netto=Decimal("11200.00"), stawka_vat=Decimal("0.23"),
        kwota_vat=Decimal("2576.00"), pkwiu="74.90.19.0",
        stawka_ryczaltu=Decimal("0.085"), zaplacony_zus=Decimal("2425.11"),
        zysk_netto=Decimal("8007.89"), stawki_wersja="2026-08-25")
    magazyn.zapisz_godziny(p, data=date(2026, 9, 5),
                           rodzaj_czynnosci="pozyskiwanie klientów (§3.2.a, d)",
                           pkwiu="46.19.10.0", liczba_godzin=Decimal("120"),
                           opis=f"spotkania w {NAZWA_KLIENTA}")
    magazyn.zapisz_aktywo(p, nazwa_aktywa="konto w banku X", kategoria="poduszka",
                          wartosc=Decimal("18000.00"))
    magazyn.zapisz_zobowiazanie(p, nazwa="kredyt hipoteczny",
                                kapital=Decimal("320000.00"),
                                rata_minimalna=Decimal("2180.00"))
    magazyn.zapisz_wpis(p, data=date(2026, 9, 5), typ=budzet.TYP_WYDATKI,
                        kategoria="Kredyty", kwota=Decimal("2400.00"),
                        # Pole `szczegoly` jest wolnym tekstem uzytkownika -
                        # wlasnie tam trafi nazwa kontrahenta. Bez niej w
                        # fiksturze narzedzia budzetowe przechodzilyby przez
                        # pustke i straznik nie mialby czego zlapac.
                        szczegoly=f"przelew do {NAZWA_KLIENTA}")
    magazyn.zapisz_wpis(p, data=date(2026, 9, 6), typ=budzet.TYP_OSZCZEDNOSCI,
                        kategoria="Inwestycje", kwota=Decimal("500.00"))
    magazyn.zapisz_plan(p, rok=2026, miesiac=9, typ=budzet.TYP_WYDATKI,
                        kategoria="Kredyty", kwota_planowana=Decimal("2000.00"))
    magazyn.zapisz_cel(p, nazwa="Cel testowy", kategoria="Inwestycje",
                       kwota_docelowa=Decimal("10000.00"),
                       termin=date(2027, 12, 31))
    return p


def _klucze_i_wartosci(obiekt, klucze=None, wartosci=None):
    """Schodzi rekurencyjnie po strukturze i zbiera WSZYSTKIE klucze i napisy."""
    klucze = set() if klucze is None else klucze
    wartosci = [] if wartosci is None else wartosci
    if isinstance(obiekt, dict):
        for k, v in obiekt.items():
            klucze.add(str(k))
            _klucze_i_wartosci(v, klucze, wartosci)
    elif isinstance(obiekt, (list, tuple, set)):
        for v in obiekt:
            _klucze_i_wartosci(v, klucze, wartosci)
    else:
        wartosci.append(str(obiekt))
    return klucze, wartosci


# --- straznik poufnosci ---------------------------------------------------

@pytest.mark.parametrize("nazwa", sorted(narzedzia.NAZWY))
def test_zadne_narzedzie_nie_zwraca_danych_klienta(nazwa, polaczenie):
    """Par. 7 ust. 4 lit. a umowy B2B. Zabezpieczenie strukturalne."""
    funkcja = narzedzia.zbuduj(polaczenie)[nazwa]
    wynik = funkcja(**narzedzia.ARGUMENTY_TESTOWE.get(nazwa, {}))
    klucze, wartosci = _klucze_i_wartosci(wynik)
    assert not (klucze & POLA_ZAKAZANE), \
        f"{nazwa} zwraca zakazane pola: {sorted(klucze & POLA_ZAKAZANE)}"
    for wartosc in wartosci:
        assert "NMI" not in wartosc, f"{nazwa} zwraca nazwe klienta w: {wartosc!r}"
        assert "FV/" not in wartosc, f"{nazwa} zwraca numer faktury w: {wartosc!r}"


def test_baza_NAPRAWDE_zawiera_nazwe_klienta_takze_w_budzecie(polaczenie):
    """Kontrola dwustronna dla narzedzi budzetowych z Zadania 21.

    Bez niej straznik poufnosci przechodzi przez pustke: narzedzia nie
    zwracaja nazwy klienta, bo nazwy nie ma nigdzie w danych.
    """
    wpisy = magazyn.wczytaj_wpisy(polaczenie)
    assert any(NAZWA_KLIENTA in str(s) for s in wpisy["szczegoly"]), \
        "fikstura ma zawierac nazwe klienta w polu szczegoly"
    assert len(magazyn.wczytaj_cele(polaczenie)) == 1
    assert len(magazyn.wczytaj_plan(polaczenie)) == 1


def test_baza_NAPRAWDE_zawiera_nazwe_klienta(polaczenie):
    """Kontrola dwustronna. Bez niej test wyzej przechodzilby przez pustke -
    dane musza byc w bazie, zeby ich brak w wyniku cokolwiek znaczyl."""
    tekst = magazyn.wczytaj_faktury(polaczenie).to_string()
    assert "NMI" in tekst and "FV/" in tekst
    assert "NMI" in magazyn.wczytaj_godziny(polaczenie).to_string()


def test_straznik_poufnosci_widzi_wszystkie_narzedzia():
    """Kontrola licznosci: sprawdzenie, do ktorego nic nie dociera, melduje sukces.

    W nazwie tego testu nie ma juz liczby: przy podbiciu z osmiu na dwanascie
    trzeba bylo zmieniac nazwe razem z asercja, a to jest dokladnie ten wzorzec
    rozjazdu, ktory projekt juz raz zlapal (liczba w prozie obok listy,
    ktora ja niesie).
    """
    assert len(narzedzia.NAZWY) == 12
    assert len(set(narzedzia.NAZWY)) == 12, "nazwy narzedzi maja byc rozne"


def test_kazde_narzedzie_ma_docstring_opisujacy_je_modelowi():
    """SDK Gemini buduje schemat narzedzia z docstringa i adnotacji typow.
    Narzedzie bez docstringa jest dla modelu bezuzyteczne."""
    for nazwa, funkcja in narzedzia.zbuduj(None).items():
        assert funkcja.__doc__ and len(funkcja.__doc__) > 40, \
            f"{nazwa} bez sensownego docstringa"


# --- jeden nosnik: narzedzie liczy tym samym, co formularz ---------------

def test_policz_podatek_zwraca_to_samo_co_silnik(polaczenie):
    """Jeden nosnik (CLAUDE.md par. 8 v1.17): narzedzie doradcy i formularz
    faktury licza TA SAMA funkcja — `podatki.policz_fakture_z_bazy`.

    ZMIANA 2026-08-28: do tej pory narzedzie bralo `stawka_ryczaltu` OD
    MODELU i wolalo `policz_ryczalt` bezwarunkowo, wiec test porownywal je
    z silnikiem ryczaltu — i byl zielony takze wtedy, gdy uzytkownik jest na
    skali. Dzis forma pochodzi z bazy i test porownuje z NIA, nie z ryczaltem.
    """
    dzis = date.today()
    n = narzedzia.zbuduj(polaczenie)["policz_podatek"]
    z_narzedzia = n(kwota_netto="11200")
    forma, z_silnika = podatki.policz_fakture_z_bazy(
        polaczenie, kwota_netto=Decimal("11200"), stawka_vat=Decimal("0.23"),
        dzien=dzis)
    assert z_narzedzia["nazwa_podatku"] == podatki.NAZWA_PODATKU[forma.forma]
    assert z_narzedzia["pit"] == str(z_silnika.pit)
    assert z_narzedzia["do_dyspozycji"] == str(z_silnika.do_dyspozycji)


def test_policz_podatek_liczy_FORMA_Z_BAZY_w_obie_strony(polaczenie):
    """Kontrola dwustronna po formie: ta sama kwota, dwie rozne liczby.

    Gdyby narzedzie zaszywalo forme (jak do 2026-08-28), obie galezie daly by
    ten sam wynik i ten test nie moglby byc zielony.
    """
    rok = date.today().year
    n = narzedzia.zbuduj(polaczenie)["policz_podatek"]

    magazyn.zapisz_forme(polaczenie, rok=rok, forma=magazyn.FORMA_SKALA)
    skala = n(kwota_netto="11200")
    assert skala["nazwa_podatku"] == "PIT"
    assert "podstawa_ryczaltu" not in skala

    magazyn.zapisz_forme(polaczenie, rok=rok, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    ryczalt = n(kwota_netto="11200")
    assert ryczalt["nazwa_podatku"] == "Ryczałt"
    assert "podstawa_ryczaltu" in ryczalt
    assert skala["pit"] != ryczalt["pit"], (
        f"obie formy daly te sama kwote {skala['pit']} — forma nie dziala")


def test_policz_podatek_uwzglednia_czy_skladki_juz_naliczono(polaczenie):
    """Kontrola dwustronna: narzedzie nie ignoruje stanu bazy.

    Faktura w bazie ma date wrzesniowa, wiec w innym miesiacu skladki NIE sa
    naliczone i podstawa jest o nie pomniejszona. Gdyby narzedzie bralo stala,
    ten test i poprzedni nie moglyby byc jednoczesnie zielone.

    Mierzone przy RYCZALCIE, bo tylko on niesie „podstawe ryczaltu" — forma
    ustawiana jawnie, nie zakladana z zaczepu bazy.
    """
    rok = date.today().year
    magazyn.zapisz_forme(polaczenie, rok=rok, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    n = narzedzia.zbuduj(polaczenie)["policz_podatek"]
    wynik = n(kwota_netto="11200")
    naliczone = magazyn.czy_skladki_naliczone_w_miesiacu(
        polaczenie, rok, date.today().month)
    if naliczone:
        assert wynik["skladki_spoleczne"] == "0.00"
        assert wynik["podstawa_ryczaltu"] == "11200.00"
    else:
        assert wynik["skladki_spoleczne"] == "1926.76"
        assert wynik["podstawa_ryczaltu"] == "9024.06"


def test_prognoza_zwraca_miesiac_przeciecia(polaczenie):
    n = narzedzia.zbuduj(polaczenie)["prognoza_roczna"]
    wynik = n(godziny_miesiecznie=160)
    assert wynik["prog_60_tys"]["miesiac"] in range(1, 13)


def test_stan_stawek_niesie_zrodlo_i_date(polaczenie):
    wynik = narzedzia.zbuduj(polaczenie)["stan_stawek"]()
    assert wynik["data_odczytu_rejestru"] == "2026-08-25"
    assert wynik["zrodla"]


def test_agregat_faktur_podaje_liczby_ale_nie_pozycje(polaczenie):
    wynik = narzedzia.zbuduj(polaczenie)["agregat_faktur"]()
    assert wynik["liczba_faktur"] == 1
    assert wynik["suma_netto"] == "11200.00"
    assert "faktury" not in wynik and "pozycje" not in wynik


def test_stan_finansow_liczy_wylacznie_wydatki_nie_caly_budzet(polaczenie):
    """Regresja mozliwa dopiero po Zadaniu 15 i dlatego latwa do przeoczenia.

    Do Zadania 15 wydatki mialy WLASNA tabele, wiec zsumowanie jej w calosci
    bylo poprawne. Po wchlonieciu ta sama tabela trzyma przychody, wydatki
    i oszczednosci naraz - suma bez filtru typu wygladalaby jak wydatki i nia
    nie byla, a zaden wyjatek by nie padl.

    Kontrola licznosci wbudowana: test wklada po jednym wpisie KAZDEGO typu,
    wiec brak filtru zmienia wynik o kwoty, ktore sa tu jawnie wypisane.
    """
    dzis = date.today()
    for typ, kategoria, kwota in (
        (budzet.TYP_PRZYCHODY, "Wynagrodzenie", "8000.00"),
        (budzet.TYP_WYDATKI, "Zakupy", "150.00"),
        (budzet.TYP_OSZCZEDNOSCI, "Inwestycje", "500.00"),
    ):
        magazyn.zapisz_wpis(polaczenie, data=dzis, typ=typ,
                            kategoria=kategoria, kwota=Decimal(kwota))

    wszystkie = magazyn.wczytaj_wpisy(polaczenie)
    biezace = wszystkie[wszystkie["data"].str.startswith(
        f"{dzis.year:04d}-{dzis.month:02d}")]
    assert len(biezace) == 3, "kontrola licznosci: pomiar ma widziec trzy typy"

    wynik = narzedzia.zbuduj(polaczenie)["stan_finansow"]()
    assert wynik["wydatki_biezacego_miesiaca"] == "150.00"


# --- Z42: doradca i ekran licza z tego samego nosnika ---------------------

def test_doradca_podaje_te_sama_kwote_do_alokacji_co_ekran(polaczenie):
    """Straznik przeciw rozejsciu sie nosnikow.

    Regresja z 2026-08-26: ekran przeszedl na `do_alokacji_z_planu` (Z41
    Task 10), a narzedzie doradcy zostalo na `do_alokacji` liczonym z WPISOW.
    Grudzien: ekran −4850,00, doradca −1875,11. Dwie prawdy o jednej liczbie.
    """
    magazyn.zapisz_plan(polaczenie, rok=2026, miesiac=9, typ="Przychody",
                        kategoria="Wynagrodzenie",
                        kwota_planowana=Decimal("8000.00"))
    magazyn.zapisz_plan(polaczenie, rok=2026, miesiac=9, typ="Wydatki",
                        kategoria="Zakupy", kwota_planowana=Decimal("2000.00"))
    magazyn.zapisz_wpis(polaczenie, data=date(2026, 9, 5),
                        typ=budzet.TYP_WYDATKI, kategoria="Zakupy",
                        kwota=Decimal("150.00"))

    plan = magazyn.wczytaj_plan(polaczenie)
    z_ekranu = budzet.do_alokacji_z_planu(plan, [(2026, 9)])
    wynik = narzedzia.zbuduj(polaczenie)["wykonanie_planu"](2026, 9)
    assert wynik["do_alokacji"] == str(z_ekranu.kwota)


def test_doradca_widzi_pozycje_planu_dziedziczona(polaczenie):
    """Narzedzie czyta PELNY plan i rozwija reguly — nie filtruje po miesiacu."""
    magazyn.ustal_regule_planu(polaczenie, rok=2026, miesiac=9, typ="Wydatki",
                               kategoria="Zakupy",
                               kwota_planowana=Decimal("100.00"))
    wynik = narzedzia.zbuduj(polaczenie)["wykonanie_planu"](2026, 11)
    zakupy = [p for p in wynik["pozycje"] if p["kategoria"] == "Zakupy"]
    assert len(zakupy) == 1
    assert zakupy[0]["planowane"] == "100.00"


def test_doradca_mowi_brak_planu_zamiast_zera(polaczenie):
    """Zero na ekranie wyglada jak budzet spiety co do grosza — najlepszy
    mozliwy stan. Brak planu nie ma prawa go udawac (ta sama regula co
    `Alokacja.kwota is None`). Miesiac spoza fikstury — wrzesien 2026 plan ma."""
    assert magazyn.wczytaj_plan(polaczenie, rok=2030, miesiac=5).empty
    wynik = narzedzia.zbuduj(polaczenie)["wykonanie_planu"](2030, 5)
    assert wynik["do_alokacji"] is None
    assert "brak planu" in wynik["do_alokacji_komentarz"].lower()

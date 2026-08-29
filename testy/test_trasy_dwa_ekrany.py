# -*- coding: utf-8 -*-
"""STRAZNICY SZESCIU TRAS ZADANIA Z6 — Ksiegowanie i Plynnosc.

CO TE TESTY SPRAWDZAJA NA ZYWYM ZADANIU HTTP, A NIE NA SILNIKU. Warstwa
sieciowa ma zmierzona klase awarii, ktorej straznik zrodlowy nie lapie:
odpowiedz z liczba zmiennoprzecinkowa w srodku wychodzila u poprzednika
z kodem 200, bo `json.dumps` serializuje `float` SAM, bez pytania `default`.
Zaden test silnika tego nie zobaczy — kwota traci grosze dopiero przy
przekraczaniu granicy. Dlatego kazda z szesciu tras jest tu wolana naprawde,
a jej odpowiedz obchodzona w GLAB.

KONTROLA LICZNOSCI JEST OBOWIAZKOWA, NIE OZDOBNA. Obchod, ktory nigdzie nie
dotarl, zwraca te sama pusta liste co obchod drzewa bez ani jednej liczby
zmiennoprzecinkowej — i przechodzi kazda asercje „czegos tam nie ma".
Dlatego kazde sprawdzenie „zero liczb zmiennoprzecinkowych" stoi obok
liczby odwiedzonych lisci, a ta liczba jest ASERCJA, nie wydrukiem.
"""

from datetime import date
from decimal import Decimal

import dataclasses

import pytest
from fastapi.testclient import TestClient

from api import kwoty
from api.index import aplikacja
from silnik import kontrakt
from silnik.rdzen import magazyn

#: Dzien odniesienia wszystkich przebiegow. USTALONY, nie z zegara: bramka
#: „ta sama liczba z silnika i z HTTP" jest niesprawdzalna, gdy wynik zalezy
#: od godziny przebiegu.
DZIS = "2026-10-06"

#: Ponizej tego progu uznajemy obchod odpowiedzi za ZEPSUTY, a nie za dowod.
#: Najuboższa z szesciu odpowiedzi (`PodgladSkutku`) niesie 17 lisci.
PROG_LISCI = 15

#: ILE LISCI MA KAZDA ODPOWIEDZ — pomiar z 2026-08-29 na fiksturze nizej,
#: przypiety asercja. To nie jest wydruk: obchod, ktory nagle widzi polowe
#: drzewa, zwraca te sama pusta liste sciezek co obchod drzewa czystego.
#: Zmiana ktorejkolwiek z tych liczb jest SYGNALEM DO SPRAWDZENIA, nie
#: pozycja do podbicia: albo ksztalt odpowiedzi sie zmienil (wtedy podnosi
#: sie ja razem z powodem), albo obchod przestal gdzies docierac.
#: Podniesienie D-62 (2026-08-29): PIATY wiersz podgladu („Plynnosc")
#: doklada 4 liscie do `PodgladSkutku` (17 -> 21) i po 4 do kazdej
#: odpowiedzi, ktora `DaneKsiegowania` w sobie niesie (74 -> 78,
#: 84 -> 88, 78 -> 82). Trasy Plynnosci bez zmian — i to jest
#: kontrola: gdyby urosly, wiersz trafilby nie tam, gdzie mial.
#: PODNIESIONE W Z7b: `/api/plynnosc` i `/api/kotwica` 147 -> 152.
#: Powod SPRAWDZONY, nie zalozony — tak, jak zada komentarz wyzej:
#:   * roznica to dokladnie 5 lisci, a `kontrakt.PozycjaKsiegi` ma 5 pol,
#:     wiec przybyla JEDNA POZYCJA KSIEGI, nie nowe pole;
#:   * ksztalt odpowiedzi jest ustalony przez `kontrakt.DanePlynnosci`
#:     (12 pol) i nie moze sie zmienic bez czerwieni
#:     `test_kontrakt_dwa_nosniki`, ktory jest zielony;
#:   * ta jedna pozycja to WPIS uzytkownika, ktory od D-20 wchodzi na os —
#:     czyli dokladnie ta zmiana, po ktora bylo zadanie Z7b.
LISCIE = {
    # Z7b: +1 lisc na kazdej odpowiedzi niosacej `DaneKsiegowania` —
    # nowe pole `ostatnieSprawdzenie` (domkniecie luki kontraktu). Zestaw
    # pol sprawdza osobno `test_ksiegowanie_oddaje_ksztalt_DaneKsiegowania`,
    # ktory czyta go z kontraktu, wiec ta liczba nie jest jedynym dowodem.
    "GET /api/ksiegowanie": 78,
    "POST /api/wpisy": 88,
    "DELETE /api/wpisy/{id}": 82,
    "POST /api/wpisy/podglad": 21,
    "GET /api/plynnosc": 152,
    "PUT /api/kotwica": 152,
}


@pytest.fixture
def klient(tmp_path, monkeypatch):
    """Wlasna baza na przebieg + gotowe nastawy Darka.

    NASTAWY SA CZESCIA FIKSTURY, nie tlem: skala podatkowa (nigdy ryczalt),
    duzy ZUS, dzialalnosc od 1 IX 2026. Baza bez formy opodatkowania nie
    liczy prognozy w ogole — i to jest zachowanie zamierzone
    (`testy/test_forma_bez_domyslnej.py`), a nie stan do testowania szczescia.
    """
    monkeypatch.setenv(magazyn.ZMIENNA_BAZY, str(tmp_path / "trasy.db"))
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(polaczenie, rok=2026, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_dzialalnosc_od(polaczenie, date(2026, 9, 1))
    magazyn.zapisz_stan_konta(polaczenie, data=date(2026, 10, 5),
                              kwota=Decimal("9920.79"))
    for miesiac in (10, 11):
        magazyn.ustal_regule_planu(
            polaczenie, rok=2026, miesiac=miesiac, typ="Wydatki",
            kategoria="Energia Elektryczna",
            kwota_planowana=Decimal("2610.00"), dzien=10)
        magazyn.ustal_regule_planu(
            polaczenie, rok=2026, miesiac=miesiac, typ="Wydatki",
            kategoria="Czesne", kwota_planowana=Decimal("660.00"), dzien=25)
        magazyn.ustal_regule_planu(
            polaczenie, rok=2026, miesiac=miesiac, typ="Wydatki",
            kategoria="Kredyty", kwota_planowana=Decimal("1305.05"), dzien=12)
    polaczenie.close()
    return TestClient(aplikacja)


def _wpis(**nadpisania) -> dict:
    tresc = {"data": DZIS, "typ": "Wydatki", "kategoria": "Energia Elektryczna",
             "kwota": "274.06", "szczegoly": "prąd, rozliczenie za wrzesień"}
    tresc.update(nadpisania)
    return tresc


# --- GET /api/ksiegowanie -------------------------------------------------

def test_ksiegowanie_oddaje_ksztalt_DaneKsiegowania(klient):
    dane = klient.get(f"/api/ksiegowanie?dzis={DZIS}").json()
    # ZESTAW POL WOLANY Z KONTRAKTU, nie przepisany tutaj (Z7b).
    # Przepisana lista byla TRZECIM nosnikiem ksztaltu — obok `kontrakt.ts`
    # i `kontrakt.py` — i rozjechala sie przy pierwszym dopisaniu pola
    # (`ostatnieSprawdzenie`). Zawolana rozjechac sie nie moze.
    oczekiwane = {p.name for p in dataclasses.fields(kontrakt.DaneKsiegowania)}
    assert len(oczekiwane) >= 8, \
        f"kontrola licznosci: kontrakt niesie {len(oczekiwane)} pol"
    assert set(dane) == oczekiwane
    assert dane["dzisiaj"] == DZIS
    assert dane["typDomyslny"] == "Wydatki"
    assert dane["nazwaMiesiaca"] == "październiku"


def test_kategorie_przychodza_w_kolejnosci_USTALONEJ_PRZEZ_SILNIK(klient):
    """Trzy pozycje planu na pazdziernik stoja pierwsze, dalej alfabetycznie.
    Trasa NIE SORTUJE — gdyby sortowala, kolejnosc mialaby dwa nosniki."""
    dane = klient.get(f"/api/ksiegowanie?dzis={DZIS}").json()
    nazwy = [k["nazwa"] for k in dane["kategorie"]]
    assert nazwy[:3] == ["Czesne", "Energia Elektryczna", "Kredyty"]
    assert nazwy[3:] == sorted(nazwy[3:], key=str.casefold)
    assert "z planu na październik" in dane["uzasadnienieKolejnosci"]


def test_kategoria_kosztu_firmowego_NIE_STOI_na_tym_ekranie(klient):
    """D-24: koszt firmowy ma jedno miejsce — ekran Firma. Slownik w bazie
    te kategorie ZAWIERA, wiec brak na ekranie musi byc regula, nie
    przypadkiem — kontrola dwustronna nizej to pokazuje."""
    from silnik.rdzen import budzet

    dane = klient.get(f"/api/ksiegowanie?dzis={DZIS}").json()
    nazwy = [k["nazwa"] for k in dane["kategorie"]]
    assert budzet.KATEGORIA_KOSZTY_JDG not in nazwy
    # kontrola dwustronna: kategoria JEST w bazie, wiec pomiar cos widzial
    polaczenie = magazyn.zmigruj_i_polacz()
    w_bazie = [str(w["nazwa"]) for _, w in
               magazyn.wczytaj_kategorie(polaczenie, "Wydatki").iterrows()]
    polaczenie.close()
    assert budzet.KATEGORIA_KOSZTY_JDG in w_bazie
    assert len(nazwy) == len(w_bazie) - 1


# --- POST /api/wpisy ------------------------------------------------------

def test_zapis_wpisu_trafia_do_bazy_i_oddaje_odswiezony_ekran(klient):
    odpowiedz = klient.post(f"/api/wpisy?dzis={DZIS}", json=_wpis())
    assert odpowiedz.status_code == 200
    tresc = odpowiedz.json()
    assert tresc["stan"] == "zapisany"
    assert tresc["id"] == 1
    assert tresc["kwota"] == "274.06"
    assert tresc["dane"]["liczbaWpisowWMiesiacu"] == 1
    assert tresc["dane"]["ostatnieWpisy"][0]["kwota"] == "274.06"


def test_kwota_UJEMNA_zwraca_PYTANIE_a_nie_blad_i_NIC_nie_zapisuje(klient):
    """Przypadek (d) z §41.5. Uzytkownik nie popelnil literowki — powiedzial
    prawde w zlym jezyku. Zapis po cichu bylby interfejsem, ktory poprawia
    liczby uzytkownika bez jego wiedzy; kod 4xx kazalby mu poprawiac cos,
    co dla niego bylo poprawne."""
    odpowiedz = klient.post(f"/api/wpisy?dzis={DZIS}",
                            json=_wpis(kwota="-274.06"))
    assert odpowiedz.status_code == 200, "to jest pytanie, nie blad zadania"
    tresc = odpowiedz.json()
    assert tresc["stan"] == "pytanie_o_minus"
    assert tresc["id"] is None
    # kwota w pytaniu jest DODATNIA — to ta sama liczba, ktora zapiszemy
    assert tresc["kwota"] == "274.06"
    assert tresc["typ"] == "Wydatki"
    # NIC nie trafilo do bazy
    assert tresc["dane"]["liczbaWpisowWMiesiacu"] == 0
    assert klient.get(f"/api/ksiegowanie?dzis={DZIS}"
                      ).json()["ostatnieWpisy"] == []


def test_potwierdzenie_pytania_o_minus_ZAPISUJE_wartosc_bezwzgledna(klient):
    """Druga strona przypadku (d): „Tak, zapisz". Bez tego testu naprawa
    polegajaca na odrzucaniu kwot ujemnych na zawsze przeszlaby jako sukces."""
    tresc = klient.post(f"/api/wpisy?dzis={DZIS}",
                        json=_wpis(kwota="-274.06", potwierdzone=True)).json()
    assert tresc["stan"] == "zapisany"
    assert tresc["kwota"] == "274.06"
    assert tresc["dane"]["ostatnieWpisy"][0]["kwota"] == "274.06"


def test_kategoria_spoza_slownika_dostaje_ZDANIE_SILNIKA_nie_500(klient):
    odpowiedz = klient.post(f"/api/wpisy?dzis={DZIS}",
                            json=_wpis(kategoria="Nie ma takiej"))
    assert odpowiedz.status_code == 400
    assert "Nie ma takiej" in odpowiedz.json()["detail"]


# --- DELETE /api/wpisy/{id} ----------------------------------------------

def test_wycofanie_wpisu_zdejmuje_go_i_oddaje_odswiezony_ekran(klient):
    numer = klient.post(f"/api/wpisy?dzis={DZIS}", json=_wpis()).json()["id"]
    tresc = klient.delete(f"/api/wpisy/{numer}?dzis={DZIS}").json()
    assert tresc["stan"] == "wycofany"
    assert tresc["id"] == numer
    assert tresc["dane"]["liczbaWpisowWMiesiacu"] == 0


def test_wycofanie_NIEISTNIEJACEGO_wpisu_jest_bledem_a_nie_cicha_zgoda(klient):
    """Pomylka w numerze, ktora melduje sukces, jest gorsza niz odmowa."""
    odpowiedz = klient.delete(f"/api/wpisy/9999?dzis={DZIS}")
    assert odpowiedz.status_code == 400
    assert "9999" in odpowiedz.json()["detail"]


# --- POST /api/wpisy/podglad ---------------------------------------------

def test_podglad_ma_PIEC_wierszy_a_dwa_ostatnie_mowia_co_sie_NIE_ruszylo(klient):
    """Dwa ostatnie wiersze nie sa wypelniaczem do rownej liczby — to JEDYNE
    miejsce, w ktorym uzytkownik dowiaduje sie, czego wpis NIE dotknal.

    Piaty („Plynnosc", D-62) powstal, bo po D-20/D-61 wpis miesczacy sie
    w planie NIE ZMIENIA sumy prognozy — a karta, ktora o tym milczy, czyni
    poprawne dzialanie nieodroznialnym od awarii zapisu."""
    tresc = klient.post(f"/api/wpisy/podglad?dzis={DZIS}", json=_wpis()).json()
    assert tresc["kwota"] == "274.06"
    assert len(tresc["wiersze"]) == 5
    czwarty, piaty = tresc["wiersze"][3], tresc["wiersze"][4]
    assert czwarty["etykieta"] == "Wolne środki"
    assert czwarty["po"] is None, "brak wartosci po = ta liczba sie NIE zmienia"
    assert czwarty["wyjasnienie"] == "bez zmian — liczą się z planu, nie z wpisów"
    assert piaty["etykieta"] == "Płynność"
    assert piaty["po"] is None
    assert piaty["wyjasnienie"], "wiersz Plynnosc bez zdania to ta sama cisza"
    # trzy pierwsze wiersze MAJA ruch — inaczej karta niczego nie zapowiada.
    # `\u00a0` to spacja NIEROZDZIELAJACA z `prezentacja.SEPARATOR_TYSIECY`:
    # kwota rozerwana miedzy wierszami przestaje byc kwota. DLUG NAZWANY,
    # nie ukryty: ramki i `interfejs/lib/kwota.ts` niosa zwykla spacje
    # (U+0020), wiec strona Pythona odstaje. Przypiety straznikiem
    # `test_kontrakt_dwa_nosniki.py::test_dwa_nosniki_formatowania_kwoty_sa_PRZYPIETE`
    # — ten test nie rozstrzyga tego sporu, tylko przypina stan faktyczny.
    assert [w["po"] for w in tresc["wiersze"][:3]] == [
        "274,06\u00a0zł", "274,06\u00a0zł", "6,0%"]


def test_podglad_liczy_od_stanu_ktory_JUZ_JEST_w_bazie(klient):
    """Kontrola licznosci karty: po pierwszym wpisie `przed` przestaje byc
    zerem. Bez tej asercji karta pokazujaca zawsze „0,00 -> kwota" wygladalaby
    poprawnie i nie liczyla niczego."""
    klient.post(f"/api/wpisy?dzis={DZIS}", json=_wpis())
    tresc = klient.post("/api/wpisy/podglad", json=_wpis()).json()
    assert [w["przed"] for w in tresc["wiersze"][:3]] == ["274,06", "274,06", "6,0%"]
    assert [w["po"] for w in tresc["wiersze"][:3]] == [
        "548,12\u00a0zł", "548,12\u00a0zł", "12,0%"]


def test_podglad_kwoty_UJEMNEJ_pokazuje_skutek_wartosci_bezwzglednej(klient):
    """Podglad nie PYTA o minus — pyta zapis. Pokazuje jednak skutek tej
    liczby, ktora po potwierdzeniu trafi do bazy; skutek ze znakiem
    obiecywalby ruch w druga strone niz zapis."""
    ujemny = klient.post("/api/wpisy/podglad", json=_wpis(kwota="-274.06")).json()
    dodatni = klient.post("/api/wpisy/podglad", json=_wpis()).json()
    assert ujemny == dodatni


# --- GET /api/plynnosc ----------------------------------------------------

def test_plynnosc_oddaje_ksztalt_DanePlynnosci(klient):
    dane = klient.get(f"/api/plynnosc?dzis={DZIS}").json()
    assert set(dane) == {
        "odczyt", "okresNapis", "ksiega", "wykres", "dzienPodKreska",
        "saldoMinimalne", "dataSaldaMinimalnego", "zdanieWerdyktu",
        "horyzontDni", "liczbaPozycjiCoMnieCzeka", "koniecOknaCoMnieCzeka",
        "ostatnieSprawdzenie"}
    assert dane["odczyt"] == DZIS
    assert dane["okresNapis"] == "październik 2026 · 45 dni naprzód"
    assert len(dane["wykres"]) == 46, "45 dni naprzod to 46 punktow z dzisiejszym"
    assert dane["ostatnieSprawdzenie"] is None, (
        "brak wartosci znaczy: straznik NIGDY nie dzialal. Nie wolno go "
        "zamieniac na zdanie o sprawdzeniu")


def test_ksiega_bije_saldo_RAZ_NA_DZIEN(klient):
    """Silnik podaje saldo per pozycja, wiec dwie pozycje z jednego dnia
    dostaja TE SAMA wartosc — a powtorzona liczba wyglada jak blad.
    Zwezenie robi trasa albo silnik, NIGDY ekran."""
    # DRUGA pozycja planu tego samego dnia co „Energia Elektryczna" — bez niej
    # regula nie ma na czym zadzialac, a straznik meldowalby sukces, nie
    # widzac ani jednego przypadku. Stoi w tescie, nie w fiksturze: fikstura
    # odwzorowuje ramke (trzy pozycje planu), a to jest przypadek szczegolny.
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki", kategoria="Gaz",
        kwota_planowana=Decimal("150.00"), dzien=10)
    polaczenie.close()
    ksiega = klient.get(f"/api/plynnosc?dzis={DZIS}").json()["ksiega"]
    widziane = set()
    for pozycja in ksiega:
        pierwsza = pozycja["dzien"] not in widziane
        widziane.add(pozycja["dzien"])
        assert (pozycja["saldoPoDniu"] is not None) == pierwsza, (
            f"saldo poza pierwsza pozycja dnia: {pozycja}")
    dni = [p["dzien"] for p in ksiega]
    assert len(dni) > len(set(dni)), (
        "pomiar nic nie widzial: w tej ksiedze nie ma ani jednego dnia "
        "z dwiema pozycjami, wiec regula nie miala na czym zadzialac")


def test_zdanie_werdyktu_nazywa_PRZYCZYNE_nie_tylko_fakt(klient):
    """Wzorzec zlej wiadomosci: liczba, zdanie, dzialanie. Samo „schodzisz
    ponizej zera" zostawia lek bez wyjscia."""
    klient.put(f"/api/kotwica?dzis={DZIS}",
               json={"data": DZIS, "kwota": "100.00"})
    dane = klient.get(f"/api/plynnosc?dzis={DZIS}").json()
    assert dane["dzienPodKreska"] is not None
    assert "schodzisz poniżej zera" in dane["zdanieWerdyktu"]
    assert "tego dnia wychodzi" in dane["zdanieWerdyktu"]
    assert dane["dzienPodKreska"] <= max(p["dzien"] for p in dane["wykres"]), (
        "dzien pod kreska poza wykresem = ostrzezenie o czyms, czego nie widac")


def test_ODMOWA_silnika_daje_ZDANIE_SILNIKA_a_nie_pusty_ekran_ani_500(klient):
    """Awaria do stanu uzytecznego, nie do zera (CLAUDE.md §3.7).

    Silnik ma RACJE, odmawiajac liczenia bez formy opodatkowania —
    zgadywanie formy jest zmierzonym mechanizmem awarii
    (`testy/test_forma_bez_domyslnej.py`). Odmowa nie ma jednak prawa wyjsc
    na ekran jako pustka ani jako 500.

    ROK 2027, NIE 2026 — i to nie jest sztuczka. `magazyn._zaczep_formy`
    wpisuje SKALE na rok zaczepu (2026) przy pierwszym otwarciu bazy, wiec
    stan „forma nierozstrzygnieta" zaczyna sie dopiero od nastepnego roku.
    Ta galaz jest wiec nie hipoteza, tylko stanem, w ktory aplikacja wejdzie
    1 stycznia 2027, jesli Darek nie wskaze formy.
    """
    odpowiedz = klient.get("/api/plynnosc?dzis=2027-10-06")
    assert odpowiedz.status_code == 200
    dane = odpowiedz.json()
    assert dane["ksiega"] == [] and dane["wykres"] == []
    assert dane["saldoMinimalne"] is None, "zero nigdy nie zastepuje braku wiedzy"
    assert "forma" in dane["zdanieWerdyktu"].lower(), dane["zdanieWerdyktu"]


# --- PUT /api/kotwica -----------------------------------------------------

def test_kotwica_zmienia_prognoze_a_nie_tylko_zapisuje(klient):
    """Bramka Z7 w miniaturze: po zapisie odczytu liczba MA byc inna."""
    przed = klient.get(f"/api/plynnosc?dzis={DZIS}").json()
    po = klient.put(f"/api/kotwica?dzis={DZIS}",
                    json={"data": DZIS, "kwota": "1000.00"}).json()
    assert po["saldoMinimalne"] != przed["saldoMinimalne"]
    assert po["ksiega"][0]["dopisek"].endswith("6 października")


def test_kotwica_PRZYJMUJE_kwote_ujemna(klient):
    """Konto na debecie to realny stan konta, nie blad wpisu — to jedyne
    miejsce w tej bazie, w ktorym minus jest czescia liczby. Regula „minus
    jest w typie wpisu" tu NIE obowiazuje."""
    odpowiedz = klient.put(f"/api/kotwica?dzis={DZIS}",
                           json={"data": DZIS, "kwota": "-500.00"})
    assert odpowiedz.status_code == 200
    assert odpowiedz.json()["ksiega"][0]["saldoPoDniu"] == "-500.00"


# --- ZERO LICZB ZMIENNOPRZECINKOWYCH, wszystkie szesc tras ----------------

def _odpowiedzi(klient) -> dict:
    """Wszystkie szesc tras wolanych naprawde, w kolejnosci spisu."""
    klient.post(f"/api/wpisy?dzis={DZIS}", json=_wpis(kwota="100.00"))
    return {
        "GET /api/ksiegowanie": klient.get(f"/api/ksiegowanie?dzis={DZIS}"),
        "POST /api/wpisy": klient.post(f"/api/wpisy?dzis={DZIS}", json=_wpis()),
        "DELETE /api/wpisy/{id}": klient.delete(f"/api/wpisy/1?dzis={DZIS}"),
        "POST /api/wpisy/podglad": klient.post("/api/wpisy/podglad", json=_wpis()),
        "GET /api/plynnosc": klient.get(f"/api/plynnosc?dzis={DZIS}"),
        "PUT /api/kotwica": klient.put(
            f"/api/kotwica?dzis={DZIS}", json={"data": DZIS, "kwota": "9920.79"}),
    }


def test_ZADNA_z_szesciu_tras_nie_wypuszcza_liczby_zmiennoprzecinkowej(klient):
    """Obchod idzie W GLAB kazdej odpowiedzi i podaje, ILE lisci widzial.

    Zero trafien przy zerze odwiedzonych lisci nie jest wynikiem — dlatego
    licznik jest asercja. Zmierzone u poprzednika przy mutacji `kwota()`:
    PIEC z szesciu sciezek z `float` lezalo PONIZEJ pierwszego poziomu
    (`$.ksiega[1].saldoPoDniu`, `$.wykres[0].saldo`), wiec obchod po wierzchu
    znalazlby jedna i zameldowal, ze reszta jest w porzadku.
    """
    raport = {}
    for nazwa, odpowiedz in _odpowiedzi(klient).items():
        assert odpowiedz.status_code == 200, nazwa
        znalezione, lisci = kwoty.policz_liscie(odpowiedz.json())
        raport[nazwa] = lisci
        assert znalezione == [], f"{nazwa}: liczby zmiennoprzecinkowe {znalezione}"
        assert lisci >= PROG_LISCI, (
            f"{nazwa}: obchod odwiedzil {lisci} lisci — ponizej progu "
            f"{PROG_LISCI}. Sprawdzenie, do ktorego nic nie dociera, "
            f"melduje sukces.")
    assert len(raport) == 6, f"zmierzono {len(raport)} tras zamiast szesciu"
    assert raport == LISCIE, (
        f"liczba lisci odpowiedzi sie zmienila: {raport} wobec {LISCIE}. "
        f"Sprawdz, czy zmienil sie KSZTALT odpowiedzi, zanim podniesiesz "
        f"te liczby.")


def test_obchod_odpowiedzi_NAPRAWDE_lapie_liczbe_zmiennoprzecinkowa(klient):
    """Kontrola dwustronna do testu wyzej. Bez niej `policz_liscie` mogloby
    zwracac pusta liste zawsze, a szesc asercji „zero trafien" przechodziloby
    przy calkowicie zepsutym mechanizmie."""
    dane = klient.get(f"/api/plynnosc?dzis={DZIS}").json()
    dane["ksiega"][1]["saldoPoDniu"] = 8295.98
    dane["wykres"][0]["saldo"] = 9601.03
    znalezione, lisci = kwoty.policz_liscie(dane)
    assert znalezione == ["$.ksiega[1].saldoPoDniu", "$.wykres[0].saldo"]
    assert lisci >= PROG_LISCI


def test_KAZDY_router_ma_klase_odpowiedzi_ODMAWIAJACA_liczb(  # noqa: N802
        ):
    """RYZYKO NR 1 CALEJ WARSTWY, sprawdzone tam, gdzie naprawde stoi.

    Klasa odpowiedzi rozstrzyga sie w KONSTRUKTORZE `APIRouter`, a nie przy
    `include_router` — zmierzone w FastAPI 0.141 u poprzednika: przekazana
    przy dolaczaniu NIE DOCIERA do trasy. Router bez niej wypuszcza liczbe
    zmiennoprzecinkowa z kodem 200, czyli awarie, ktora melduje sukces.

    Test wyzej („zadna z szesciu tras…") tego NIE pokrywa i trzeba to
    powiedziec wprost: przy zepsutym `kwota()` odpowiedz konczy sie kodem
    500, wiec tamten test czerwieni sie na kodzie, nie na liczbie. Dopiero
    ten straznik pyta o mechanizm, ktory ma tam stac.
    """
    from api import trasy_ksiegowanie, trasy_plynnosc

    routery = {"trasy_ksiegowanie": trasy_ksiegowanie.trasy,
               "trasy_plynnosc": trasy_plynnosc.trasy}
    assert len(routery) == 2
    for nazwa, router in routery.items():
        assert router.default_response_class is kwoty.OdpowiedzJSON, (
            f"{nazwa}: klasa odpowiedzi to {router.default_response_class}, "
            f"a nie OdpowiedzJSON — liczby zmiennoprzecinkowe wyjda z 200")
    # Kontrola dwustronna: klasa naprawde odmawia, a nie tylko sie nazywa.
    with pytest.raises(TypeError) as blad:
        kwoty.OdpowiedzJSON(content={"ksiega": [{"saldoPoDniu": 8295.98}]})
    assert "$.ksiega[0].saldoPoDniu" in str(blad.value)


def test_FORMA_OPODATKOWANIA_dojezdza_az_do_odpowiedzi_HTTP(klient):
    """Ryczalt jest WADA, nie opcja domyslna — sprawdzone na drucie.

    `testy/test_forma_bez_domyslnej.py` pilnuje, ze pominiecie formy jest
    bledem WYWOLANIA w silniku. To jest pytanie o poziom wyzej: czy forma
    zapisana w bazie zmienia LICZBE, ktora wychodzi z trasy. Zmierzony
    mechanizm awarii u poprzednika brzmial dokladnie tak: rachunek liczyl
    ryczaltem komus, kto jest na skali, i robil to wiarygodnie.

    Dwie formy, te same dane, DWIE ROZNE liczby. Gdyby byly rowne, znaczyloby
    to, ze forma nie dojechala do silnika — i wtedy zaden z pozostalych
    testow tego pliku by tego nie zauwazyl.
    """
    skala = klient.get(f"/api/plynnosc?dzis={DZIS}").json()["saldoMinimalne"]

    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(polaczenie, rok=2026, forma=magazyn.FORMA_RYCZALT,
                         stawka_ryczaltu=Decimal("0.085"))
    polaczenie.close()
    ryczalt = klient.get(f"/api/plynnosc?dzis={DZIS}").json()["saldoMinimalne"]

    assert skala is not None and ryczalt is not None, (
        "pomiar nic nie widzial: obie prognozy odmowily liczenia")
    assert skala != ryczalt, (
        f"skala i ryczalt daja te sama liczbe ({skala}) — forma nie "
        f"dojechala do silnika przez granice HTTP")
    # Kontrola kierunku: Darek jest na SKALI i to ona jest stanem bazy
    # po fiksturze. Sam fakt roznicy nie mowi, ktora liczbe widzi uzytkownik.
    assert skala == "2986.44", f"skala oddaje {skala}"


@pytest.mark.parametrize("tresc,co_zle", [
    ({"data": DZIS, "typ": "Wydatki", "kategoria": "Energia Elektryczna",
      "kwota": "abc"}, "kwota nieczytelna"),
    ({"data": DZIS, "typ": "Wydatki", "kategoria": "Energia Elektryczna",
      "kwota": ""}, "kwota pusta"),
    ({"data": "nie-data", "typ": "Wydatki", "kategoria": "Energia Elektryczna",
      "kwota": "10.00"}, "data nieczytelna"),
    ({"data": DZIS, "typ": "Wypłaty", "kategoria": "Energia Elektryczna",
      "kwota": "10.00"}, "typ spoza zbioru"),
])
def test_wejscie_nie_do_odczytania_konczy_sie_400_a_nie_500(klient, tresc, co_zle):
    """Kod 500 znaczy „nasza wada"; 400 znaczy „nie umiem tego przeczytac".
    Zlanie ich w jedno odbiera te informacje i uzytkownikowi, i nam."""
    odpowiedz = klient.post(f"/api/wpisy?dzis={DZIS}", json=tresc)
    assert odpowiedz.status_code == 400, f"{co_zle}: {odpowiedz.text[:200]}"
    assert odpowiedz.json()["detail"], f"{co_zle}: odmowa bez zdania"


def test_kotwica_z_nieczytelna_kwota_konczy_sie_400_a_nie_500(klient):
    odpowiedz = klient.put(f"/api/kotwica?dzis={DZIS}",
                           json={"data": DZIS, "kwota": "dużo"})
    assert odpowiedz.status_code == 400
    assert odpowiedz.json()["detail"]

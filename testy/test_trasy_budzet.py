# -*- coding: utf-8 -*-
"""STRAZNICY SZESCIU TRAS EKRANU BUDZET (W9b).

CO TE TESTY SPRAWDZAJA NA ZYWYM ZADANIU HTTP, A NIE NA SILNIKU. Warstwa
sieciowa ma zmierzona klase awarii, ktorej straznik zrodlowy nie lapie:
odpowiedz z liczba zmiennoprzecinkowa w srodku wychodzila u poprzednika
z kodem 200, bo `json.dumps` serializuje `float` SAM, bez pytania `default`.
Drugi wariant tej samej awarii, znaleziony w tej sesji: kwota wychodzi
NAPISEM, a napis klamie — `"8623.10"` -> `"8623.1"`, kod 200, straznik
pilnujacy TYPU zielony. Dlatego kazda z szesciu tras jest tu wolana naprawde,
jej odpowiedz obchodzona W GLAB, a wartosci porownywane CO DO ZNAKU.

KONTROLA LICZNOSCI JEST OBOWIAZKOWA, NIE OZDOBNA. Obchod, ktory nigdzie nie
dotarl, zwraca te sama pusta liste co obchod drzewa bez ani jednej liczby
zmiennoprzecinkowej — i przechodzi kazda asercje „czegos tam nie ma".
Dlatego kazde sprawdzenie „zero liczb zmiennoprzecinkowych" stoi obok liczby
odwiedzonych lisci, a ta liczba jest ASERCJA, nie wydrukiem.

FIKSTURA ODTWARZA RAMKE, NIE WYGODNY PRZYPADEK. Trzy pozycje planu na
pazdziernik 2026 sumuja sie do 2 614,81 zl, a cel „Poduszka finansowa"
30 000,00 zl z terminem 6 I 2028 daje tempo 2 000,00 zl / mc przez 15 mc —
dokladnie te liczby stoja na `makiety/Budzet.dc.html`. Kategoria „Kredyty"
ma DWIE pozycje planu (1 305,05 + 319,76), bo ramka pokazuje ja jako jeden
wiersz z dwoma dniami platnosci („1 i 12 X") i to jest jedyny przypadek,
w ktorym wiersz tabeli NIE MA jednego numeru pozycji do poprawiania.
"""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api import kwoty
from api.index import aplikacja
from silnik import kontrakt
from silnik.rdzen import magazyn

#: Dzien odniesienia wszystkich przebiegow. USTALONY, nie z zegara: bramka
#: „ta sama liczba z silnika i z HTTP" jest niesprawdzalna, gdy wynik zalezy
#: od godziny przebiegu. Ten sam dzien niesie ramka („6 października 2026").
DZIS = "2026-10-06"
MIESIAC = "2026-10"

#: Ponizej tego progu uznajemy obchod odpowiedzi za ZEPSUTY, a nie za dowod.
PROG_LISCI = 100

#: ILE LISCI MA KAZDA ODPOWIEDZ — pomiar 2026-08-29 na fiksturze nizej,
#: przypiety asercja. To nie jest wydruk: obchod, ktory nagle widzi polowe
#: drzewa, zwraca te sama pusta liste sciezek co obchod drzewa czystego.
#: Zmiana ktorejkolwiek z tych liczb jest SYGNALEM DO SPRAWDZENIA, nie
#: pozycja do podbicia: albo ksztalt odpowiedzi sie zmienil (wtedy podnosi
#: sie ja razem z powodem), albo obchod przestal gdzies docierac.
#:
#: ROZKLAD LICZBY 103 SPRAWDZONY, nie zalozony — inaczej byla by to liczba
#: przepisana z przebiegu, a taka nie wykrywa niczego poza wlasna zmiana:
#:   14 pol wierzchnich (19 pol `DaneBudzetu` minus piec list)
#: + 15 = 3 kafelki x 5 pol  + 30 = 3 wiersze wykonania x 10 pol
#: + 32 = 4 pozycje planu x 8 pol + 12 = 1 cel x 12 pol
#: + 0  = historia (zero wpisow w tym miesiacu)  ->  103
#:
#: Cztery zapisy sa wolane PO SOBIE, na tej samej bazie, wiec ich liczby
#: opisuja stan po poprzednich krokach — nie sa niezalezne od siebie i tak
#: maja byc czytane. Kazdy zapis oddaje ekran w komplecie PLUS trzy pola
#: wlasne (`stan`, `wynik`, `id`).
LISCIE = {
    "GET /api/budzet": 103,
    "POST /api/plan": 124,
    "PUT /api/plan/{id}": 136,
    "POST /api/plan/{id}/zakoncz": 118,
    "POST /api/plan/kopiuj": 124,
    "POST /api/cele": 136,
}


@pytest.fixture
def klient():
    """Wlasna baza na przebieg + nastawy Darka + plan z ramki.

    NASTAWY SA CZESCIA FIKSTURY, nie tlem: SKALA PODATKOWA (nigdy ryczalt),
    dzialalnosc od 1 IX 2026. Baza bez formy opodatkowania nie policzy
    rezerwy w ogole — i to jest zachowanie zamierzone
    (`testy/test_forma_bez_domyslnej.py`), sprawdzane osobno nizej.
    """
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_forme(polaczenie, rok=2026, forma=magazyn.FORMA_SKALA)
    magazyn.zapisz_dzialalnosc_od(polaczenie, date(2026, 9, 1))
    # Kredyty: DWIE pozycje w jednej kategorii — 1 305,05 + 319,76 = 1 624,81.
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki", kategoria="Kredyty",
        opis="Alior", kwota_planowana=Decimal("1305.05"), dzien=1)
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki", kategoria="Kredyty",
        opis="Revolut", kwota_planowana=Decimal("319.76"), dzien=12)
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki", kategoria="Czesne",
        kwota_planowana=Decimal("660.00"), dzien=25)
    magazyn.ustal_regule_planu(
        polaczenie, rok=2026, miesiac=10, typ="Wydatki",
        kategoria="Energia Elektryczna", kwota_planowana=Decimal("330.00"),
        dzien=20)
    magazyn.zapisz_cel(
        polaczenie, nazwa="Poduszka finansowa", kategoria="Poduszka finansowa",
        kwota_docelowa=Decimal("30000.00"), termin=date(2028, 1, 6))
    polaczenie.close()
    return TestClient(aplikacja)


@pytest.fixture
def klient_bez_formy():
    """Baza BEZ formy opodatkowania — stan, w ktorym silnik ODMAWIA liczenia.

    To nie jest przypadek brzegowy do zaliczenia, tylko stan startowy kazdej
    swiezej bazy: dopoki Darek nie wskaze formy w Ustawieniach, rezerwy nie
    da sie policzyc i ekran ma o tym POWIEDZIEC, a nie pokazac zero.
    """
    polaczenie = magazyn.zmigruj_i_polacz()
    magazyn.zapisz_dzialalnosc_od(polaczenie, date(2026, 9, 1))
    # STAN OSIAGALNY, NIE WYMYSLONY. Migracja zaczepia forme na rok zaczepu
    # (`magazyn._zaczep_formy`), wiec swieza baza forme MA. Stan bez formy
    # powstaje wtedy, gdy Darek skasuje ten wpis swiadomie — i wlasnie ten
    # przypadek naglowek `_zaczep_formy` opisuje wprost jako dopuszczalny.
    # Bez tego skasowania ten test sprawdzalby stan, ktorego nie ma.
    polaczenie.execute("DELETE FROM forma_opodatkowania")
    polaczenie.commit()
    polaczenie.close()
    return TestClient(aplikacja)


def _budzet(klient, miesiac: str = MIESIAC) -> dict:
    odpowiedz = klient.get(f"/api/budzet?dzis={DZIS}&miesiac={miesiac}")
    assert odpowiedz.status_code == 200, odpowiedz.text
    return odpowiedz.json()


def _bez_zmiennoprzecinkowych(nazwa: str, tresc) -> int:
    """Obchod W GLAB plus kontrola licznosci — jedno bez drugiego nic nie mowi.

    Zwraca liczbe odwiedzonych lisci, zeby wolajacy mogl porownac CALY zestaw
    szesciu liczb naraz. Porownanie po jednej gasi sie na pierwszej roznicy
    i nie mowi, czy pozostale piec tras jeszcze zyje.
    """
    sciezki, lisci = kwoty.policz_liscie(tresc)
    assert sciezki == [], f"{nazwa}: liczba zmiennoprzecinkowa w {sciezki}"
    assert lisci >= PROG_LISCI, (
        f"{nazwa}: obchod odwiedzil {lisci} lisci, prog {PROG_LISCI} — "
        f"to nie jest dowod, to slepy pomiar")
    return lisci


# --- 0. ksztalt i kontrola licznosci --------------------------------------

def test_budzet_oddaje_ksztalt_DaneBudzetu(klient):
    """ZESTAW POL WOLANY Z KONTRAKTU, nie przepisany tutaj. Przepisana lista
    bylaby TRZECIM nosnikiem ksztaltu — obok `kontrakt.ts` i `kontrakt.py`."""
    dane = _budzet(klient)
    oczekiwane = {p.name for p in dataclasses.fields(kontrakt.DaneBudzetu)}
    assert len(oczekiwane) >= 15, \
        f"kontrola licznosci: kontrakt niesie {len(oczekiwane)} pol"
    assert set(dane) == oczekiwane
    assert dane["dzisiaj"] == DZIS
    assert dane["miesiac"] == MIESIAC
    assert dane["miesiacNapis"] == "październik 2026"
    assert dane["nazwaMiesiaca"] == "październiku"


def test_kazda_z_szesciu_tras_ODPOWIADA_i_nie_niesie_liczby(klient):
    """Wszystkie szesc tras naraz — kontrola licznosci na poziomie SPISU.

    Bez tego testu mozna zbudowac piec tras i nie zauwazyc; kazdy test
    ponizej sprawdza swoja jedna i przechodzi.
    """
    from api import trasy as spis
    from api.index import ZBUDOWANE

    w_spisie = [t for t in spis.WSZYSTKIE if t.ekran == "budzet"]
    assert len(w_spisie) == 6, f"spis niesie {len(w_spisie)} tras Budzetu"
    brakujace = [t.sciezka for t in w_spisie if t.sciezka not in ZBUDOWANE]
    assert brakujace == [], f"w spisie sa, a nie stoja: {brakujace}"

    zmierzone = {"GET /api/budzet": _bez_zmiennoprzecinkowych(
        "GET /api/budzet", _budzet(klient))}

    odpowiedzi = {
        "POST /api/plan": klient.post(
            f"/api/plan?dzis={DZIS}",
            json={"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "Gaz",
                  "kwota": "212.50", "dzien": 15}),
        "PUT /api/plan/{id}": None,
        "POST /api/plan/{id}/zakoncz": None,
        "POST /api/plan/kopiuj": klient.post(
            f"/api/plan/kopiuj?dzis={DZIS}", json={"miesiac": "2026-11"}),
        "POST /api/cele": klient.post(
            f"/api/cele?dzis={DZIS}",
            json={"nazwa": "Wakacje", "kategoria": "Inwestycje",
                  "kwotaDocelowa": "6000.00", "termin": "2027-07-01",
                  "miesiac": MIESIAC}),
    }
    numer = _numer_pozycji(_budzet(klient), "Czesne")
    odpowiedzi["PUT /api/plan/{id}"] = klient.put(
        f"/api/plan/{numer}?dzis={DZIS}",
        json={"miesiac": MIESIAC, "kwota": "700.00", "dzien": 25})
    odpowiedzi["POST /api/plan/{id}/zakoncz"] = klient.post(
        f"/api/plan/{numer}/zakoncz?dzis={DZIS}", json={"miesiac": MIESIAC})

    for nazwa, odpowiedz in odpowiedzi.items():
        assert odpowiedz.status_code == 200, f"{nazwa}: {odpowiedz.text}"
        zmierzone[nazwa] = _bez_zmiennoprzecinkowych(nazwa, odpowiedz.json())

    assert zmierzone == LISCIE, (
        "liczba lisci sie zmienila. Albo ksztalt odpowiedzi jest inny (wtedy "
        "podnies te liczby RAZEM Z POWODEM), albo obchod przestal gdzies "
        f"docierac. Zmierzone: {zmierzone}")


def _numer_pozycji(dane: dict, kategoria: str, opis: str = "") -> int:
    """Numer pozycji planu po kategorii — z kontrola licznosci.

    Wyszukanie, ktore nic nie znalazlo, zwrocilo by `None` i test padlby
    dopiero na zadaniu HTTP, z komunikatem o niczym.
    """
    pasujace = [p for p in dane["pozycjePlanu"]
                if p["kategoria"] == kategoria and p["opis"] == opis]
    assert len(pasujace) == 1, (
        f"pozycji {kategoria!r} (opis {opis!r}) jest {len(pasujace)}, "
        f"a szukam jednej: {[p['kategoria'] for p in dane['pozycjePlanu']]}")
    return pasujace[0]["id"]


# --- 1. kafelki i bilans — liczby z ramki ---------------------------------

def test_kafelki_niosa_liczby_z_RAMKI_i_sumuja_sie(klient):
    """2 614,81 + rezerwa = „Plan miesiaca razem". Kontrola arytmetyczna
    jest tu obowiazkowa: kafelek „razem" ma tytul obiecujacy sume i musi
    pokazywac sume, a nie jedna z jej skladowych (§3.5)."""
    dane = _budzet(klient)
    kafelki = {k["klucz"]: k for k in dane["kafelki"]}
    assert set(kafelki) == {"wydatkiZPlanu", "rezerwa", "razem"}
    assert kafelki["wydatkiZPlanu"]["kwota"] == "2614.81"
    assert kafelki["wydatkiZPlanu"]["tytul"] == "Wydatki osobiste z planu"
    assert (Decimal(kafelki["razem"]["kwota"])
            == Decimal(kafelki["wydatkiZPlanu"]["kwota"])
            + Decimal(kafelki["rezerwa"]["kwota"]))


def test_bilans_planu_jest_UJEMNY_o_cala_kwote_wydatkow(klient):
    """Miesiac bez ani jednej zaplanowanej pozycji przychodu — bilans ujemny
    o cala kwote wydatkow. Rezerwa w te liczbe NIE WCHODZI: stoi w kafelku,
    osobno, bo nie jest wydatkiem tego miesiaca."""
    dane = _budzet(klient)
    assert dane["planPrzychodow"] == "0.00"
    assert dane["planWydatkow"] == "2614.81"
    assert dane["planOszczednosci"] == "0.00"
    assert dane["bilansPlanu"] == "-2614.81"


def test_rezerwa_BEZ_FORMY_nie_jest_zerem_tylko_zdaniem(klient_bez_formy):
    """§3.7 — awaria do stanu uzytecznego, nie do zera.

    Forma opodatkowania nie ma wartosci domyslnej i mi ec nie bedzie. Silnik
    odmawia liczenia rezerwy, a ekran ma powiedziec CZEGO BRAKUJE — zero
    w tym miejscu czytaloby sie jako „nic nie jestes winien urzedowi".
    """
    dane = _budzet(klient_bez_formy)
    kafelki = {k["klucz"]: k for k in dane["kafelki"]}
    assert kafelki["rezerwa"]["kwota"] is None
    assert kafelki["razem"]["kwota"] is None, \
        "suma z nieznanym skladnikiem udaje, ze skladnik zna"
    zdanie = kafelki["rezerwa"]["wyjasnienie"]
    assert zdanie and "form" in zdanie.lower(), zdanie
    assert "Ustawieniach" in zdanie, \
        "zdanie ma mowic, CO ZROBIC, a nie tylko, ze sie nie da"
    # Kontrola dwustronna: reszta ekranu liczy sie NORMALNIE. Odmowa jednego
    # kafelka nie ma prawa wygasic calego ekranu.
    assert dane["bilansPlanu"] == "0.00"
    assert dane["kafelki"][0]["kwota"] == "0.00"


def test_slowo_RYCZALT_nie_pada_na_tym_ekranie(klient):
    """Darek jest na SKALI. W poprzedniej aplikacji ryczalt byl wartoscia
    domyslna w trzech miejscach i podawal kwoty wyliczone forma, ktorej
    Darek nie ma — ten straznik pilnuje, ze nie wrocil tylna droga."""
    tekst = klient.get(f"/api/budzet?dzis={DZIS}&miesiac={MIESIAC}").text
    assert "ycza" not in tekst.lower(), \
        "na ekranie Budzet pojawilo sie slowo z rodziny „ryczalt”"


# --- 2. tabela „Plan kontra wykonanie" ------------------------------------

def test_najwieksze_odchylenie_STOI_U_GORY(klient):
    """Napis z ramki pod tytulem sekcji. Kolejnosc jest OBIETNICA wobec
    czytelnika, nie wlasnoscia kolejnosci wierszy w bazie."""
    dane = _budzet(klient)
    kategorie = [w["kategoria"] for w in dane["pozycjeWykonania"]]
    assert kategorie == ["Kredyty", "Czesne", "Energia Elektryczna"]
    odchylenia = [Decimal(w["odchylenie"]) for w in dane["pozycjeWykonania"]]
    assert odchylenia == [Decimal("-1624.81"), Decimal("-660.00"),
                          Decimal("-330.00")]
    assert odchylenia == sorted(odchylenia, key=lambda x: -abs(x))


def test_wiersz_z_DWOMA_pozycjami_planu_NIE_MA_jednego_numeru(klient):
    """Kategoria „Kredyty" ma dwie pozycje planu (Alior i Revolut), wiec
    „popraw te pozycje" nie ma jednej odpowiedzi. `None` z `liczba == 2` mowi
    to wprost; sam `None` byl by nieodroznialny od „nie ma czego poprawiac"."""
    dane = _budzet(klient)
    wiersze = {w["kategoria"]: w for w in dane["pozycjeWykonania"]}
    assert wiersze["Kredyty"]["idPozycjiPlanu"] is None
    assert wiersze["Kredyty"]["liczbaPozycjiPlanu"] == 2
    assert wiersze["Czesne"]["liczbaPozycjiPlanu"] == 1
    assert wiersze["Czesne"]["idPozycjiPlanu"] is not None


def test_procent_bez_planu_to_MYSLNIK_a_nie_zero(klient):
    """Kategoria tknieta wpisem, ale niezaplanowana. Zero procent klamaloby,
    ze wydatek zmiescil sie w budzecie (`budzet.Wykonanie` §procent)."""
    klient.post(f"/api/wpisy?dzis={DZIS}",
                json={"data": DZIS, "typ": "Wydatki", "kategoria": "Zakupy",
                      "kwota": "120.00", "szczegoly": ""})
    dane = _budzet(klient)
    wiersze = {w["kategoria"]: w for w in dane["pozycjeWykonania"]}
    assert wiersze["Zakupy"]["procent"] == "—"
    assert wiersze["Zakupy"]["procentPaska"] is None
    assert wiersze["Zakupy"]["liczbaPozycjiPlanu"] == 0
    assert wiersze["Zakupy"]["idPozycjiPlanu"] is None


def test_pasek_postepu_NIE_WYCHODZI_poza_sto(klient):
    """Przekroczenie planu niesie `przekroczone`, nie 340 na pasku — pasek
    dluzszy niz jego tor nie istnieje wizualnie. Liczba niescieta zostaje
    w `procent` i to ona idzie na ekran jako napis."""
    for _ in range(3):
        klient.post(f"/api/wpisy?dzis={DZIS}",
                    json={"data": DZIS, "typ": "Wydatki",
                          "kategoria": "Czesne", "kwota": "660.00",
                          "szczegoly": ""})
    wiersze = {w["kategoria"]: w for w in _budzet(klient)["pozycjeWykonania"]}
    assert wiersze["Czesne"]["przekroczone"] is True
    assert wiersze["Czesne"]["procent"] == "300,0%"
    assert wiersze["Czesne"]["procentPaska"] == 100


# --- 3. cztery operacje P-1: dwie ostatnie -------------------------------

def test_P1_USTAWIC_pozycje_planu_przez_POST(klient):
    """P-1 operacja 3, czesc pierwsza: dodanie pozycji planu.

    LICZBY PRZED I PO — a nie sam kod 200. Zapis, ktory zwraca 200 i nie
    zmienia zadnej liczby, jest awaria meldujaca sukces.
    """
    przed = _budzet(klient)
    assert przed["planWydatkow"] == "2614.81"
    assert len(przed["pozycjePlanu"]) == 4

    odpowiedz = klient.post(
        f"/api/plan?dzis={DZIS}",
        json={"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "Gaz",
              "kwota": "212.50", "dzien": 15})
    assert odpowiedz.status_code == 200, odpowiedz.text
    wynik = odpowiedz.json()
    assert wynik["stan"] == "plan_ustawiony"
    assert wynik["wynik"] == "nowa"

    po = wynik["dane"]
    assert po["planWydatkow"] == "2827.31"          # 2614.81 + 212.50
    assert po["bilansPlanu"] == "-2827.31"
    assert len(po["pozycjePlanu"]) == 5
    # Odpowiedz zapisu i osobny odczyt musza sie ZGADZAC. Rozjazd znaczylby,
    # ze ekran po zapisie pokazuje co innego niz ekran po odswiezeniu.
    assert po == _budzet(klient)


def test_P1_ZMIENIC_pozycje_planu_przez_PUT(klient):
    """P-1 operacja 3, czesc druga: zmiana istniejacej pozycji.

    Zmiana obowiazuje OD wskazanego miesiaca w przod i NIE zaklada nowej
    pozycji — liczba pozycji zostaje ta sama, zmienia sie kwota.
    """
    przed = _budzet(klient)
    numer = _numer_pozycji(przed, "Czesne")

    odpowiedz = klient.put(
        f"/api/plan/{numer}?dzis={DZIS}",
        json={"miesiac": MIESIAC, "kwota": "700.00", "dzien": 25})
    assert odpowiedz.status_code == 200, odpowiedz.text
    wynik = odpowiedz.json()
    assert wynik["stan"] == "plan_ustawiony"
    assert wynik["wynik"] == "zaktualizowana", \
        "regula zaczynajaca sie w tym miesiacu ma sie zmienic W MIEJSCU"

    po = wynik["dane"]
    assert len(po["pozycjePlanu"]) == len(przed["pozycjePlanu"])
    assert po["planWydatkow"] == "2654.81"          # 2614.81 - 660 + 700
    czesne = [p for p in po["pozycjePlanu"] if p["kategoria"] == "Czesne"]
    assert [p["kwota"] for p in czesne] == ["700.00"]


def test_P1_ZAKONCZYC_pozycje_planu_HISTORIA_ZOSTAJE(klient):
    """P-1 operacja 4 — i najwazniejszy straznik tego ekranu.

    Pozycja zalozona w pazdzierniku, zakonczona od LISTOPADA: listopad jej
    nie ma, PAZDZIERNIK MA JA BEZ ZMIAN. Gdyby trasa kasowala wiersz,
    pazdziernik pokazywalby plan mniejszy o 660 zl i historia klamalaby
    o miesiacu, ktory Darek juz zamknal.
    """
    przed = _budzet(klient)
    numer = _numer_pozycji(przed, "Czesne")
    # Pozycja musi obowiazywac takze w listopadzie, zeby bylo co konczyc.
    listopad_przed = _budzet(klient, "2026-11")
    assert "Czesne" in [p["kategoria"] for p in listopad_przed["pozycjePlanu"]]

    odpowiedz = klient.post(f"/api/plan/{numer}/zakoncz?dzis={DZIS}",
                            json={"miesiac": "2026-11"})
    assert odpowiedz.status_code == 200, odpowiedz.text
    wynik = odpowiedz.json()
    assert wynik["stan"] == "plan_zakonczony"
    assert wynik["wynik"] == "zamknieta", \
        "regula ciagnaca sie z wczesniej ma zostac ZAMKNIETA, nie skasowana"

    listopad_po = wynik["dane"]
    assert listopad_po["miesiac"] == "2026-11"
    assert "Czesne" not in [p["kategoria"]
                            for p in listopad_po["pozycjePlanu"]]
    assert listopad_po["planWydatkow"] == "1954.81"     # 2614.81 - 660.00

    # HISTORIA NIETKNIETA — to jest cala roznica miedzy „zakoncz" a „usun".
    pazdziernik_po = _budzet(klient, MIESIAC)
    assert pazdziernik_po["planWydatkow"] == przed["planWydatkow"] == "2614.81"
    assert "Czesne" in [p["kategoria"]
                        for p in pazdziernik_po["pozycjePlanu"]]


def test_zakonczenie_pozycji_zalozonej_W_TYM_MIESIACU_kasuje_wiersz(klient):
    """Kontrola dwustronna do testu wyzej. Pozycja, ktora ZACZYNA sie w tym
    samym miesiacu, w ktorym ja konczymy, nie ma zadnej przeszlosci do
    zachowania — i wtedy wiersz znika. Rozstrzyga to `magazyn.zakoncz_plan`,
    nie warstwa sieciowa; straznik przypina, ze warstwa tego nie zmiekcza."""
    numer = _numer_pozycji(_budzet(klient), "Czesne")
    wynik = klient.post(f"/api/plan/{numer}/zakoncz?dzis={DZIS}",
                        json={"miesiac": MIESIAC}).json()
    assert wynik["wynik"] == "skasowana"
    assert "Czesne" not in [p["kategoria"]
                            for p in wynik["dane"]["pozycjePlanu"]]


def test_zakonczenie_NIE_JEST_metoda_DELETE(klient):
    """Kosz konczy regule, wiec droga do niego nie moze obiecywac usuniecia.
    Straznik behawioralny obok zrodlowego z `test_nosniki.py`: tam pilnujemy
    SPISU, tu pilnujemy, ze zbudowana aplikacja naprawde nie odpowiada."""
    numer = _numer_pozycji(_budzet(klient), "Czesne")
    assert klient.delete(f"/api/plan/{numer}").status_code == 405
    assert klient.delete("/api/plan").status_code == 405


# --- 4. kopia planu i cel -------------------------------------------------

def test_kopiuj_plan_NIE_DOKLADA_pozycji_ktore_juz_obowiazuja(klient):
    """Straznik ZMIERZONEJ WADY PIENIEZNEJ, naprawionej w W9b.

    Pozycje pazdziernikowe sa REGULAMI, wiec obowiazuja takze w listopadzie
    bez ani jednego wlasnego wiersza. Kopia „z pazdziernika na listopad" nie
    ma wiec czego przenosic — i ma to powiedziec.

    Przed naprawa `magazyn.kopiuj_plan` czytal WIERSZE miesiaca zrodlowego
    zamiast pozycji obowiazujacych, a „czy juz jest" sprawdzal bez `opis`.
    Zmierzony skutek: plan listopada 2 284,81 zl -> 3 589,86 zl, druga
    pozycja „Kredyty" z pusta nazwa, „Czesne" bez dnia platnosci — i meldunek
    „skopiowane 2, pominiete 1". Ten test czerwieni sie, gdy tamto wroci.
    """
    przed = _budzet(klient, "2026-11")
    assert len(przed["pozycjePlanu"]) == 4
    assert przed["planWydatkow"] == "2614.81"

    wynik = klient.post(f"/api/plan/kopiuj?dzis={DZIS}",
                        json={"miesiac": "2026-11"}).json()
    assert wynik["stan"] == "plan_skopiowany"
    assert wynik["wynik"] == "skopiowane 0, pominiete 4", wynik["wynik"]

    po = wynik["dane"]
    assert len(po["pozycjePlanu"]) == 4
    assert po["planWydatkow"] == "2614.81", \
        "kopia dolozyla do planu pieniadze, ktorych nikt nie zaplanowal"
    assert [p["kategoria"] for p in po["pozycjePlanu"]] == \
        [p["kategoria"] for p in przed["pozycjePlanu"]]
    assert [p["dzien"] for p in po["pozycjePlanu"]] == \
        [p["dzien"] for p in przed["pozycjePlanu"]], \
        "kopia zgubila dni platnosci"


def test_kopiuj_plan_PRZENOSI_pozycje_do_miesiaca_bez_planu(klient):
    """Kontrola dwustronna do testu wyzej: bramka, ktora nic nie przepuszcza,
    nie jest bramka. Pozycja JEDNORAZOWA (nie regula) obowiazuje wylacznie
    w swoim miesiacu, wiec z nastepnego trzeba ja przeniesc — razem z dniem
    platnosci i z nazwa."""
    from silnik.rdzen import magazyn as m

    polaczenie = m.polacz()
    m.zapisz_plan(polaczenie, rok=2026, miesiac=10, typ="Wydatki",
                  kategoria="Zdrowie", opis="Dentysta",
                  kwota_planowana=Decimal("450.00"), dzien=8)
    polaczenie.close()
    assert "Zdrowie" not in [p["kategoria"]
                             for p in _budzet(klient, "2026-11")["pozycjePlanu"]]

    wynik = klient.post(f"/api/plan/kopiuj?dzis={DZIS}",
                        json={"miesiac": "2026-11"}).json()
    assert wynik["wynik"] == "skopiowane 1, pominiete 4", wynik["wynik"]
    przeniesiona = [p for p in wynik["dane"]["pozycjePlanu"]
                    if p["kategoria"] == "Zdrowie"]
    assert len(przeniesiona) == 1
    assert przeniesiona[0]["opis"] == "Dentysta"
    assert przeniesiona[0]["kwota"] == "450.00"
    assert przeniesiona[0]["dzien"] == 8, "kopia zgubila dzien platnosci"


def test_kopiuj_plan_wyprowadza_ZRODLO_z_celu(klient):
    """Bez `zMiesiaca` zrodlem jest miesiac poprzedni — ten sam nosnik, ktory
    sklada napis przycisku. Dwa nosniki rozjechalyby sie 1 stycznia."""
    dane = _budzet(klient)
    assert dane["miesiacKopiujZ"] == "2026-09"
    assert dane["napisKopiujZ"] == "Skopiuj z września"
    # Wrzesien nie ma planu, wiec kopia z niego niczego nie przenosi —
    # i wlasnie to ma powiedziec, zamiast meldowac sukces.
    wynik = klient.post(f"/api/plan/kopiuj?dzis={DZIS}",
                        json={"miesiac": MIESIAC}).json()
    assert wynik["wynik"] == "skopiowane 0, pominiete 0"


def test_dodaj_cel_liczy_postep_Z_WPISOW(klient):
    """Cel z ramki: 30 000,00 zl, tempo 2 000,00 zl / mc przez 15 mc.
    Postep liczy sie z wpisow w kategorii celu, nie z liczby wpisanej
    recznie — pasek napedzany reczna liczba pokazuje to, co uzytkownik
    wpisal, a nie to, co ma."""
    dane = _budzet(klient)
    assert len(dane["cele"]) == 1
    cel = dane["cele"][0]
    assert cel["nazwa"] == "Poduszka finansowa"
    assert cel["kwotaDocelowa"] == "30000.00"
    assert cel["uzbierane"] == "0.00"
    assert cel["tempoNapis"] == "2\u00a0000,00\u00a0zł / mc przez 15 mc"
    assert cel["procentPaska"] == 0
    assert cel["osiagniety"] is False and cel["poTerminie"] is False

    klient.post(f"/api/wpisy?dzis={DZIS}",
                json={"data": DZIS, "typ": "Oszczędności",
                      "kategoria": "Poduszka finansowa", "kwota": "3000.00",
                      "szczegoly": ""})
    cel_po = _budzet(klient)["cele"][0]
    assert cel_po["uzbierane"] == "3000.00"
    assert cel_po["brakuje"] == "27000.00"
    assert cel_po["procentPaska"] == 10


def test_dodaj_cel_przez_trase(klient):
    """Nowy cel wchodzi do licznika naglowka: „N pozycji planu" liczy TAKZE
    cele, dokladnie tak jak naglowek ramki („4 pozycje planu" = trzy wydatki
    + jeden cel)."""
    przed = _budzet(klient)
    assert przed["liczbaPozycjiPlanu"] == len(przed["pozycjePlanu"]) + 1 == 5

    wynik = klient.post(
        f"/api/cele?dzis={DZIS}",
        json={"nazwa": "Wakacje", "kategoria": "Inwestycje",
              "kwotaDocelowa": "6000.00", "termin": "2027-07-01",
              "miesiac": MIESIAC}).json()
    assert wynik["stan"] == "cel_dodany"
    assert wynik["id"] is not None
    assert len(wynik["dane"]["cele"]) == 2
    assert wynik["dane"]["liczbaPozycjiPlanu"] == 6


def test_cel_w_kategorii_WYDATKU_jest_ODMOWA_a_nie_zapisem(klient):
    """Cel wskazujacy kategorie wydatku liczylby postep z pieniedzy WYDANYCH:
    pasek pokazywalby, ze zbierasz na wakacje, im wiecej wydajesz na zakupy.
    Regule niesie `magazyn.zapisz_cel`; warstwa sieciowa jej nie zmiekcza."""
    odpowiedz = klient.post(
        f"/api/cele?dzis={DZIS}",
        json={"nazwa": "Wakacje", "kategoria": "Zakupy",
              "kwotaDocelowa": "6000.00", "termin": "2027-07-01"})
    assert odpowiedz.status_code == 400, odpowiedz.text
    assert "Zakupy" in odpowiedz.json()["detail"]


# --- 5. kwoty przez granice ----------------------------------------------

def test_kwota_z_ZEREM_NA_KONCU_nie_gubi_go_po_drodze(klient):
    """Zmierzona awaria wariantu napisowego: `"8623.10"` -> `"8623.1"`,
    kod 200, straznik pilnujacy TYPU zielony. Porownujemy WARTOSC, co do
    znaku, a nie sam typ."""
    wynik = klient.post(
        f"/api/plan?dzis={DZIS}",
        json={"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "Transport",
              "kwota": "8623.10", "dzien": 3}).json()
    pozycje = {p["kategoria"]: p for p in wynik["dane"]["pozycjePlanu"]}
    assert pozycje["Transport"]["kwota"] == "8623.10"
    surowe = klient.get(f"/api/budzet?dzis={DZIS}&miesiac={MIESIAC}").content
    assert b'"8623.10"' in surowe
    assert b'"kwota":8623.1' not in surowe


def test_odmowa_silnika_wychodzi_ZDANIEM_a_nie_piecsetka(klient):
    """§3.7 — awaria do stanu uzytecznego. Numer pozycji, ktorej nie ma, to
    zwykle pozycja zakonczona w innym oknie przegladarki; odpowiedz ma
    powiedziec, co zrobic, a nie pokazac „Internal Server Error"."""
    odpowiedz = klient.put(f"/api/plan/999999?dzis={DZIS}",
                           json={"miesiac": MIESIAC, "kwota": "100.00"})
    assert odpowiedz.status_code == 400, odpowiedz.text
    zdanie = odpowiedz.json()["detail"]
    assert "999999" in zdanie and "Odśwież" in zdanie, zdanie


# --- 6. straznik zrodlowy: kosz konczy regule ----------------------------

def test_ekran_budzetu_NIE_WOLA_usun_plan():
    """Z-9 od strony KODU, nie spisu tras. `magazyn.usun_plan` istnieje
    i jest swiadomie odciety od interfejsu — droga do niego nie moze
    powstac tylnymi drzwiami, przez modul ekranu."""
    import pathlib

    from pomocnicze import kod_pythona_bez_prozy

    korzen = pathlib.Path(__file__).resolve().parent.parent
    sprawdzone = 0
    for plik in (korzen / "silnik" / "ekran_budzet.py",
                 korzen / "api" / "trasy_budzet.py"):
        kod = kod_pythona_bez_prozy(plik.read_text(encoding="utf-8"))
        sprawdzone += 1
        assert "usun_plan" not in kod, (
            f"{plik.name} wola `magazyn.usun_plan`. Kosz przy pozycji planu "
            f"KONCZY regule od wskazanego miesiaca w przod, nie kasuje "
            f"historii (Z-9).")
        assert "usun_cel" not in kod, f"{plik.name} wola `magazyn.usun_cel`"
    assert sprawdzone == 2, \
        f"straznik przejrzal {sprawdzone} pliki zamiast dwoch"


# --- 7. walidacja wejscia PRZED zapisem ----------------------------------

def test_pozycja_planu_BEZ_KATEGORII_nie_dociera_do_bazy(klient):
    """§ walidacja przed operacja na bazie.

    Do W9b `magazyn.ustal_regule_planu` robilo `str(kategoria).strip()`, wiec
    zadanie bez kategorii zapisywalo pozycje planu o nazwie „None": kwote
    w planie, ktorej zaden wpis nigdy nie wykona, i ktora nie wyglada na blad.
    Sprawdzenie stoi PRZED zapisem i wola jedyny nosnik reguly
    (`magazyn.wymagaj_kategorii`).
    """
    przed = _budzet(klient)
    for zle in ({"miesiac": MIESIAC, "typ": "Wydatki", "kwota": "100.00"},
                {"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "",
                 "kwota": "100.00"},
                {"miesiac": MIESIAC, "typ": "Wydatki",
                 "kategoria": "Kategoria Ktorej Nie Ma", "kwota": "100.00"}):
        odpowiedz = klient.post(f"/api/plan?dzis={DZIS}", json=zle)
        assert odpowiedz.status_code == 400, f"{zle} -> {odpowiedz.text}"
        assert "Ustawienia" in odpowiedz.json()["detail"], \
            "odmowa ma mowic, CO ZROBIC"
    po = _budzet(klient)
    assert po["pozycjePlanu"] == przed["pozycjePlanu"], \
        "odrzucone zadanie zostawilo slad w bazie"
    assert po["planWydatkow"] == przed["planWydatkow"]


def test_pozycja_planu_W_ZLYM_TYPIE_jest_odmowa(klient):
    """Kategoria to para (typ, nazwa), nie sama nazwa: „Inne" jest jednoczesnie
    kategoria przychodu i wydatku. „Czesne" w typie „Przychody" nie istnieje."""
    odpowiedz = klient.post(
        f"/api/plan?dzis={DZIS}",
        json={"miesiac": MIESIAC, "typ": "Przychody", "kategoria": "Czesne",
              "kwota": "100.00"})
    assert odpowiedz.status_code == 400, odpowiedz.text
    assert "Czesne" in odpowiedz.json()["detail"]


def test_ZAPIS_POWTORZONY_daje_jeden_skutek_a_nie_dwa(klient):
    """Idempotencja zapisow, ktore przegladarka moze powtorzyc.

    `POST /api/plan` z tym samym miesiacem, typem, kategoria i opisem NIE
    zaklada drugiej pozycji — nadpisuje istniejaca i mowi o tym slowem
    („zaktualizowana" zamiast „nowa"). Bez tego dwuklik na „Dodaj pozycje
    planu" podwajalby plan, a dwie identyczne pozycje wygladalyby jak dane.
    """
    pierwszy = klient.post(
        f"/api/plan?dzis={DZIS}",
        json={"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "Gaz",
              "kwota": "212.50", "dzien": 15}).json()
    assert pierwszy["wynik"] == "nowa"
    assert pierwszy["dane"]["planWydatkow"] == "2827.31"

    drugi = klient.post(
        f"/api/plan?dzis={DZIS}",
        json={"miesiac": MIESIAC, "typ": "Wydatki", "kategoria": "Gaz",
              "kwota": "212.50", "dzien": 15}).json()
    assert drugi["wynik"] == "zaktualizowana"
    assert drugi["dane"]["planWydatkow"] == "2827.31", \
        "powtorzone zadanie podwoilo plan"
    assert len(drugi["dane"]["pozycjePlanu"]) == 5

    # Kopia planu tez jest idempotentna: drugi przebieg nie ma juz czego
    # przeniesc, bo wszystko obowiazuje w miesiacu docelowym.
    klient.post(f"/api/plan/kopiuj?dzis={DZIS}", json={"miesiac": "2026-11"})
    powtorka = klient.post(f"/api/plan/kopiuj?dzis={DZIS}",
                           json={"miesiac": "2026-11"}).json()
    assert powtorka["wynik"] == "skopiowane 0, pominiete 5", powtorka["wynik"]

"""Strazniki `rdzen/prezentacja.py` — formatowania kwot i reguly koloru karty.

Z51. Cztery funkcje przenios sie tu 1:1 z `pulpit/wspolne.py` razem z testami,
bo `api/` nie moze importowac `pulpit/` (ten ciagnie `nicegui`, wspolne.py:10),
a skopiowanie formatowania do `api/` utworzyloby drugi nosnik — dokladnie ten,
przed ktorym broni docstring `rola_alokacji`.

Testy `rola_alokacji` i `opis_alokacji` sa PRZENIESIONE z
`testy/test_pulpit_budzet.py` (sekcje „karta »Do alokacji«" i Z46), bez zmiany
tresci asercji. Nowe w tym pliku sa wylacznie strazniki jednego nosnika.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from pomocnicze import kod_pythona_bez_prozy

from silnik.rdzen import budzet
from silnik.rdzen import prezentacja

KATALOG = Path(__file__).resolve().parent.parent


# --- formatowanie kwot ----------------------------------------------------
#
# Do Z51 `zloty` nie mial ani jednego wlasnego testu — byl sprawdzany wylacznie
# przez „ta sama funkcja po obu stronach" w testach pulpitu, co nie mowi nic
# o tym, czy formatuje poprawnie. Od Z64 ten napis przechodzi granice HTTP
# jako pole `tekst`, wiec staje sie regula o konsekwencji zewnetrznej.

def test_zloty_daje_polskie_separatory_i_jednostke():
    assert prezentacja.zloty(Decimal("-6098.11")) == "\u22126\u00a0098,11\u00a0zł"


# --- D-58: minus typograficzny, nie dywiz ---------------------------------
#
# ROZSTRZYGNIECIE: ramka wygrywa, silnik sie dostosowuje. Ramki i ekran nios a
# U+2212 MINUS SIGN; `prezentacja.zloty` zwracal U+002D HYPHEN-MINUS. Roznica
# jest niewidoczna w recenzji kodu i widoczna w bramce odwzorowania, bo oba
# znaki maja rozna szerokosc.
#
# DLACZEGO TRZY OSOBNE ASERCJE, A NIE JEDNA NA NAPISIE. Asercja na calym
# napisie (wyzej) czerwieni sie takze wtedy, gdy zmieni sie separator albo
# jednostka — a wtedy nie wiadomo, co pekło. Te ponizej pytaja o JEDEN znak
# po kodzie, wiec komunikat mowi wprost, ze wrocil dywiz.

def test_minus_przy_kwocie_to_U2212_a_NIE_dywiz_ASCII():
    """Straznik D-58. Kontrola po KODZIE ZNAKU, nie po wygladzie napisu —
    dywiz i minus sa w edytorze nie do odroznienia."""
    wynik = prezentacja.zloty(Decimal("-210.67"))
    assert wynik[0] == "\u2212", (
        f"minus przy kwocie ma kod U+{ord(wynik[0]):04X}, ma miec U+2212 "
        f"(MINUS SIGN). U+002D to dywiz ASCII — ramki go nie uzywaja.")
    assert "\u002d" not in wynik, "dywiz ASCII gdziekolwiek w kwocie"


def test_minus_stoi_TYLKO_na_poczatku_a_nie_zamiast_kazdego_dywizu():
    """Kontrola dwustronna. Zamiana globalna przeszlaby test wyzej i zepsula
    daty ISO, ktore przechodza przez sasiednie funkcje tego modulu."""
    # Etykieta okresu bierze napis z dywizem ISO (`2026-09`) i ma go zachowac
    # tam, gdzie dywiz jest separatorem, a nie znakiem liczby.
    assert "\u2212" not in prezentacja.etykieta_okresu("2026-09")
    assert "\u2212" not in prezentacja.zloty(Decimal("1305.05"))
    assert "\u2212" not in prezentacja.zloty(Decimal("0.00"))


def test_stala_MINUS_jest_ZAPISANA_ucieczka_a_nie_wklejona():
    """Ta sama pulapka co przy separatorze: znak wklejony wprost jest
    w kodzie nieodroznialny od dywizu. Pytamy o PRZYPISANIE, nie o to, czy
    plik gdziekolwiek wspomina o ucieczce — pierwsza wersja straznika
    separatora przezyla mutacje wlasnie dlatego (M176)."""
    zrodlo = (KATALOG / "silnik" / "rdzen"
              / "prezentacja.py").read_text(encoding="utf-8")
    assert 'MINUS = "\\u2212"' in zrodlo, \
        "minus ma byc zapisany ucieczka `\\u2212`, nie wklejony"
    assert prezentacja.MINUS == "\u2212"


def test_zloty_zaokragla_do_dwoch_miejsc_i_nie_gubi_grosza():
    assert prezentacja.zloty(Decimal("0.01")) == "0,01\u00a0zł"
    assert prezentacja.zloty(Decimal("1234567.89")) == "1\u00a0234\u00a0567,89\u00a0zł"


def test_brak_kwoty_daje_myslnik_a_NIGDY_zera():
    """Kontrola dwustronna do reguly D11: zero wyglada jak budzet spiety."""
    assert prezentacja.zloty(None) == "—"
    assert prezentacja.zloty(Decimal("0.00")) == "0,00\u00a0zł"


def test_liczba_to_ta_sama_regula_BEZ_jednostki():
    """`rdzen.prognoza` doklejal „zl" sam — nosnik ma byc jeden, nie dwa."""
    assert prezentacja.liczba(Decimal("6098.11")) == "6\u00a0098,11"
    assert prezentacja.zloty(Decimal("6098.11")) \
        == prezentacja.liczba(Decimal("6098.11")) + "\u00a0zł"


def test_procent_obcina_zera_nieznaczace():
    assert prezentacja.procent(Decimal("0.085")) == "8,5%"
    assert prezentacja.procent(Decimal("0.15")) == "15%"


# --- karta „Do alokacji": co uzytkownik zobaczy ---------------------------
#
# PRZENIESIONE z test_pulpit_budzet.py (Z51, bez zmiany asercji).
# To JEDYNE straznikowane miejsce interfejsu obok wyboru miesiaca: nie uklad
# graficzny, tylko decyzja o tresci. `opis_alokacji` jest czysta wlasnie po to,
# zeby dalo sie ja sprawdzic bez uruchamiania NiceGUI.

def test_brak_planu_daje_NAPIS_a_nigdy_kwote_zero():
    """Zero wygladaloby jak budzet spiety co do grosza — najlepszy mozliwy stan."""
    tekst, _ = prezentacja.opis_alokacji(budzet.Alokacja(None, 0, 1))
    assert "Brak planu" in tekst
    assert "0,00" not in tekst


def test_plan_czesciowy_mowi_ile_miesiecy_pokrywa():
    _, podpis = prezentacja.opis_alokacji(
        budzet.Alokacja(Decimal("-2370.00"), 1, 3))
    assert "1 z 3" in podpis


def test_plan_pelny_nie_dokleja_ostrzezenia_o_pokryciu():
    """Kontrola dwustronna: ostrzezenie ma sie pojawiac tylko gdy trzeba."""
    _, podpis = prezentacja.opis_alokacji(
        budzet.Alokacja(Decimal("-2370.00"), 3, 3))
    assert "z 3" not in podpis


def test_podpis_karty_mowi_o_PLANIE_a_nie_o_wykonaniu():
    """Etykieta ma zmienic sie razem ze znaczeniem liczby."""
    _, podpis = prezentacja.opis_alokacji(budzet.Alokacja(Decimal("0.00"), 1, 1))
    assert "plan" in podpis.lower()


def test_opis_wolnych_srodkow_mowi_ze_podatki_juz_odjete():
    """Podpis ma niesc CALY wzor, bo to jest jedyne miejsce, gdzie uzytkownik
    moze sprawdzic, czemu liczba jest taka, a nie inna."""
    _, podpis = prezentacja.opis_alokacji(
        budzet.Alokacja(Decimal("-618.11"), 1, 1))
    assert "podatk" in podpis.lower()
    assert "oszczędnoś" in podpis.lower()


# --- kolor karty „Do alokacji" --------------------------------------------
# PRZENIESIONE z test_pulpit_budzet.py (Z51, bez zmiany asercji).

def test_brak_planu_jest_NEUTRALNY_a_nie_zielony():
    """Wada wykryta 2026-08-26 po zmianie domyslnego miesiaca na biezacy.

    `(alokacja.kwota or 0) >= 0` traktowalo brak planu (`None`) jak zero, wiec
    karta „Brak planu w wybranym okresie" swiecila na zielono — kolorem stanu
    najlepszego z mozliwych.
    """
    assert prezentacja.rola_alokacji(budzet.Alokacja(None, 0, 1)) == "neutralny"


def test_dodatnia_alokacja_jest_zielona_a_ujemna_czerwona():
    """Kontrola dwustronna: neutralnosc nie moze zjesc pozostalych dwoch stanow."""
    assert prezentacja.rola_alokacji(
        budzet.Alokacja(Decimal("100.00"), 1, 1)) == "przychody"
    assert prezentacja.rola_alokacji(
        budzet.Alokacja(Decimal("-100.00"), 1, 1)) == "blad"


def test_zerowa_alokacja_jest_zielona_bo_budzet_spiety_to_dobry_stan():
    assert prezentacja.rola_alokacji(
        budzet.Alokacja(Decimal("0.00"), 1, 1)) == "przychody"


# --- jeden nosnik ---------------------------------------------------------

def test_regula_formatowania_kwoty_ma_JEDEN_nosnik_w_calym_projekcie():
    """Do Z51 ta sama regula stala w `pulpit/wspolne.py` i `rdzen/prognoza.py`,
    kazda z wlasna stala separatora — i jedna z nich miala znak nierozdzielajacy
    WKLEJONY DOSLOWNIE, nie do odroznienia wzrokiem od zwyklej spacji.

    Ryzyko nr 7 planu: prognoza plynnosci (Z62) jako czwarty nosnik.
    """
    # ZAKRES STRAZNIKA po przeniesieniu: caly silnik i cala warstwa sieciowa
    # tego projektu. `pulpit/` znika (stary interfejs), ale `api/` i `wiedza/`
    # dochodza — to sa dokladnie te miejsca, w ktore regula formatowania
    # uciekala u poprzednika. KONTROLA LICZNOSCI ponizej nie jest ozdoba:
    # sprawdzenie, do ktorego nic nie dociera, MELDUJE SUKCES.
    pliki = (sorted(KATALOG.glob("silnik/**/*.py"))
             + sorted(KATALOG.glob("api/*.py"))
             + sorted(KATALOG.glob("wiedza/**/*.py")))
    assert len(pliki) >= 20, f"straznik widzi tylko {len(pliki)} plikow"

    # Kod, nie proza — patrz `kod_pythona_bez_prozy`. Bez tego strażnik
    # czerwieni się na dokumentacji, która cytuje zakazany kształt.
    z_formatem = [p for p in pliki
                  if ":,.2f" in kod_pythona_bez_prozy(
                      p.read_text(encoding="utf-8"))]
    assert [p.name for p in z_formatem] == ["prezentacja.py"], \
        f"format kwoty przepisany zamiast zawolany: {[p.name for p in z_formatem]}"

    ze_stala = [p for p in pliki
                if "SEPARATOR_TYSIECY = " in kod_pythona_bez_prozy(
                    p.read_text(encoding="utf-8"))]
    assert [p.name for p in ze_stala] == ["prezentacja.py"], \
        f"separator ma wiecej niz jeden nosnik: {[p.name for p in ze_stala]}"


def test_separator_jest_ZAPISANY_ucieczka_a_nie_wklejony():
    """Znak nierozdzielajacy wklejony wprost jest w kodzie nieodrozniałny od
    spacji — przezyl tak w `pulpit/wspolne.py:29` do Z51."""
    zrodlo = (KATALOG / "silnik" / "rdzen" / "prezentacja.py").read_text(encoding="utf-8")
    # Sprawdzamy PRZYPISANIE, nie „czy w pliku gdziekolwiek pada slowo o ucieczce".
    # Pierwsza wersja tego straznika pytala `"\\u00a0" in zrodlo` i przezyla
    # mutacje M176 — wystarczyl jej komentarz nad stala (Z51, 2026-08-27).
    assert 'SEPARATOR_TYSIECY = "\\u00a0"' in zrodlo, \
        "separator ma byc zapisany ucieczka `\\u00a0`, nie wklejony"
    assert prezentacja.SEPARATOR_TYSIECY == "\u00a0"


# --- Z52: ktora baze widzi uzytkownik -------------------------------------

def test_podpis_zrodla_MILCZY_o_bazie_PRODUKCYJNEJ():
    """Adres serwera przy kazdym uruchomieniu bylby szumem — i przestalby
    znaczyc „uwaga, to nie Twoja baza".

    ODWROCENIE SENSU W W4 (2026-08-29). U poprzednika „domyslna" znaczylo
    „plik w repozytorium", czyli baze robocza. Po podmianie sterownika znaczy
    „serwer NIE na tej maszynie", czyli baze produkcyjna — i to o niej pasek
    ma milczec, bo to jest stan normalny.
    """
    from silnik.rdzen.magazyn import OpisBazy
    podpis = prezentacja.podpis_zrodla(
        OpisBazy(adres="ep-cos.eu-central-1.aws.neon.tech/doradca",
                 domyslna=True))
    assert "neon.tech" not in podpis
    assert "lokalnie" in podpis


def test_podpis_zrodla_NAZYWA_baze_nietypowa():
    """Tryb awarii, przed ktorym to broni: „patrzylem w niewlasciwa baze
    i wygladalo dobrze" (plan Z52)."""
    from silnik.rdzen.magazyn import OpisBazy
    podpis = prezentacja.podpis_zrodla(
        OpisBazy(adres="localhost:5434/kopia_robocza", domyslna=False))
    assert "localhost:5434/kopia_robocza" in podpis


def test_podpis_zrodla_NIGDY_nie_niesie_hasla():
    """CLAUDE.md §8. Adres bazy niesie haslo do produkcji, a pasek aplikacji
    jest miejscem, w ktore patrzy sie przez caly dzien.

    Straznik jest tutaj, a nie tylko przy `adres_bez_hasla`, bo to `pasek`
    jest miejscem, w ktorym wyciek bylby widoczny — i to on musi czerwienic
    sie, gdyby ktos podal mu adres surowy.
    """
    from silnik.rdzen.magazyn import OpisBazy, adres_bez_hasla
    tajne = "haslo-ktorego-nie-wolno-zobaczyc"
    adres = f"postgresql://kto:{tajne}@localhost:5434/doradca_test"
    podpis = prezentacja.podpis_zrodla(
        OpisBazy(adres=adres_bez_hasla(adres), domyslna=False))
    assert tajne not in podpis
    assert "localhost:5434/doradca_test" in podpis


# --- Z55: podpis kafelka rezerwy -----------------------------------------

def _rezerwa(**pola):
    from silnik.rdzen.podatki import RezerwaPodatkowa
    domyslne = dict(
        vat_nalezny=Decimal("2576.00"), vat_naliczony=Decimal("0.00"),
        vat_do_zaplaty=Decimal("2576.00"), zus=Decimal("7275.33"),
        podatek_dochodowy=Decimal("767.00"),
        naliczone_razem=Decimal("10618.33"),
        zaplacone=Decimal("0.00"), saldo=Decimal("10618.33"),
        miesiace_zus=3, zastrzezenia=(),
        forma="RYCZALT", nazwa_podatku="Ryczałt")
    return RezerwaPodatkowa(**{**domyslne, **pola})


def test_podpis_rezerwy_MOWI_z_ilu_miesiecy_liczy_sie_ZUS():
    """Bez tego liczba ZUS wyglada jak suma z faktur — czyli jak liczba,
    ktora byla tam przed Z55. Podpis ma nazywac REGULE, nie tylko kwote."""
    podpis = prezentacja.podpis_rezerwy(_rezerwa())
    assert "3" in podpis
    assert "miesi" in podpis.lower()


def test_podpis_rezerwy_BEZ_daty_niesie_zastrzezenie_od_silnika():
    """Zdanie przychodzi z rdzenia w calosci (specyfikacja §5.1 pkt 3) —
    ekran go nie przeredagowuje."""
    zastrzezenie = "Składki ZUS nie zostały policzone: nie znam daty."
    podpis = prezentacja.podpis_rezerwy(
        _rezerwa(zus=Decimal("0.00"), miesiace_zus=None,
                 zastrzezenia=(zastrzezenie,)))
    assert zastrzezenie in podpis


def test_podpis_rezerwy_NIE_udaje_ze_zna_miesiace_gdy_ich_nie_zna():
    """Kontrola dwustronna: „0 miesięcy" bylo by zerem udajacym „nie wiem"."""
    podpis = prezentacja.podpis_rezerwy(
        _rezerwa(zus=Decimal("0.00"), miesiace_zus=None,
                 zastrzezenia=("cokolwiek",)))
    assert "0 miesi" not in podpis


# --- Z57: co ekran mowi o formie opodatkowania ---------------------------

def test_podpis_formy_przy_NIEROZSTRZYGNIETEJ_KAZE_wskazac_forme():
    """Plan Z29: „ekran przy NIEROZSTRZYGNIETA pokazuje polecenie wskazania
    formy, nie kwote"."""
    from silnik.rdzen.magazyn import FORMA_NIEROZSTRZYGNIETA, FormaRoku
    podpis = prezentacja.podpis_formy(
        FormaRoku(rok=2027, forma=FORMA_NIEROZSTRZYGNIETA, stawka_ryczaltu=None))
    assert "2027" in podpis
    assert "wskaż" in podpis.lower()
    assert "zgadn" in podpis.lower(), "ma byc powiedziane, ze aplikacja NIE zgaduje"


def test_podpis_formy_NAZYWA_wybrana_forme():
    from silnik.rdzen.magazyn import FORMA_SKALA, FormaRoku
    podpis = prezentacja.podpis_formy(
        FormaRoku(rok=2026, forma=FORMA_SKALA, stawka_ryczaltu=None))
    assert "skal" in podpis.lower()
    assert "2026" in podpis


def test_podpis_formy_przy_RYCZALCIE_podaje_stawke():
    from silnik.rdzen.magazyn import FORMA_RYCZALT, FormaRoku
    podpis = prezentacja.podpis_formy(
        FormaRoku(rok=2027, forma=FORMA_RYCZALT,
                  stawka_ryczaltu=Decimal("0.085")))
    assert "8,5%" in podpis


def test_ostrzezenia_formy_MOWIA_ze_to_nie_zgloszenie_do_urzedu():
    """Plan Z29, ostrzezenie (a). Aplikacja zapisuje wybor dla siebie —
    urzad o nim nie wie i nie dowie sie sam."""
    ostrzezenia = prezentacja.ostrzezenia_formy(2027)
    assert any("urzęd" in o.lower() or "oświadcz" in o.lower()
               for o in ostrzezenia)


def test_ostrzezenia_dla_2026_dokladaja_TERMIN_20_pazdziernika():
    """Plan Z29, ostrzezenie (b): przy roku 2026 dodatkowo termin 20.10.2026
    i zdanie, ze milczenie zostawia skale takze na lata nastepne."""
    ostrzezenia = prezentacja.ostrzezenia_formy(2026)
    tekst = " ".join(ostrzezenia)
    assert "20.10.2026" in tekst
    assert "milcz" in tekst.lower()
    assert len(ostrzezenia) > len(prezentacja.ostrzezenia_formy(2027)), \
        "kontrola dwustronna: rok 2026 ma MIEC wiecej ostrzezen niz inne lata"


# --- Z75: zdania o strazniku w tle i o terminie ----------------------------

def test_podpis_straznika_ODROZNIA_nigdy_od_cicho():
    """§5.4: strażnik, który nie zadziałał, wygląda identycznie jak strażnik,
    który zadziałał i nic nie znalazł. Pasek musi je rozróżniać SŁOWAMI."""
    nigdy = prezentacja.podpis_straznika(None, date(2026, 9, 18))
    cicho = prezentacja.podpis_straznika(
        {"kiedy": "2026-09-18T06:00:00", "pilnych": 0, "powod": None,
         "zrodla": "zgodne", "stan_prognozy": "policzona", "powiadomiono": False},
        date(2026, 9, 18))
    assert "nigdy" in nigdy.lower()
    assert "06:00" in cicho and "dziś" in cicho.lower()
    assert nigdy != cicho


def test_podpis_straznika_niesie_LICZBE_pilnych():
    tekst = prezentacja.podpis_straznika(
        {"kiedy": "2026-09-17T06:00:00", "pilnych": 2,
         "powod": "VAT — termin 2026-09-19.", "zrodla": "zgodne",
         "stan_prognozy": "policzona", "powiadomiono": True},
        date(2026, 9, 18))
    assert "2" in tekst
    assert "wczoraj" in tekst.lower()


def test_ZERO_pilnych_przy_stanie_NIE_WIEM_NIE_uspokaja():
    """Trzeci stan §5.4, wniesiony rozstrzygnięciem Grupy A.

    `CoMnieCzeka.pilnych` ma typ `int | None`: `None` znaczy „nie liczyłem".
    Kolumna `pilnych` w `przebiegi_straznika` jest `INTEGER NOT NULL`
    i przy stanie „nie wiem" zapisuje `0` — rozróżnienie niesie osobna
    kolumna `stan_prognozy`. To rozstrzygnięcie stoi WYŁĄCZNIE na tym
    strażniku: gdyby zdanie przy `pilnych=0` mówiło „nic pilnego nie
    znalazł" niezależnie od `stan_prognozy`, pasek uspokajałby bez pokrycia,
    a kolumna musiałaby stać się `nullable` (schemat 11, druga migracja
    bazy produkcyjnej w jednym plasterku).

    KONTROLA DWUSTRONNA. Sama asercja „mówi »nie policzył«" przeszłaby
    również wtedy, gdyby funkcja mówiła tak ZAWSZE. Druga połowa testu
    sprawdza więc stan przeciwny: przy `stan_prognozy="policzona"` i tym
    samym `pilnych=0` zdanie MA brzmieć „nic pilnego nie znalazł".
    """
    wspolne = {"kiedy": "2026-09-18T06:00:00", "pilnych": 0, "powod": None,
               "zrodla": "zgodne", "powiadomiono": False}
    nie_wiem = prezentacja.podpis_straznika(
        {**wspolne, "stan_prognozy": "nie_wiem"}, date(2026, 9, 18))
    policzona = prezentacja.podpis_straznika(
        {**wspolne, "stan_prognozy": "policzona"}, date(2026, 9, 18))

    assert "nie policzył" in nie_wiem.lower(), nie_wiem
    assert "nic pilnego" not in nie_wiem.lower(), nie_wiem

    assert "nic pilnego" in policzona.lower(), policzona
    assert "nie policzył" not in policzona.lower(), policzona

    assert nie_wiem != policzona


def test_przebieg_Z_PRZYSZLOSCI_czyta_sie_jak_DZIS_a_nie_minus_jeden_dzien():
    """Zegar przestawiony o dobę albo przebieg tuż po północy — nie hipoteza.

    `(dzis - kiedy.date()).days` jest wtedy UJEMNE, a gałąź „ile dni temu"
    złożyłaby zdanie „-1 dni temu": napis, którego nikt nie napisał celowo.
    Rozstrzygnięcie: przebieg świeższy niż dzień, o który pytamy, czyta się
    jak `dziś`. To nie jest ostrzeżenie — strażnik zadziałał, i to niedawno;
    jedyne, co jest nie tak, to zegar, a o zegarze pasek terminów nie mówi.

    KONTROLA DWUSTRONNA: druga połowa pilnuje, żeby poprawka nie zwinęła
    WSZYSTKIEGO do „dziś" — przebieg naprawdę stary ma nadal mówić, ile ma lat.
    """
    przyszly = prezentacja.podpis_straznika(
        {"kiedy": "2026-09-19T06:00:00", "pilnych": 0, "powod": None,
         "zrodla": "zgodne", "stan_prognozy": "policzona", "powiadomiono": False},
        date(2026, 9, 18))
    assert "dziś" in przyszly.lower(), przyszly
    assert "-1" not in przyszly, przyszly
    assert "dni temu" not in przyszly, przyszly

    stary = prezentacja.podpis_straznika(
        {"kiedy": "2026-09-14T06:00:00", "pilnych": 0, "powod": None,
         "zrodla": "zgodne", "stan_prognozy": "policzona", "powiadomiono": False},
        date(2026, 9, 18))
    assert "4 dni temu" in stary, stary
    assert "dziś" not in stary.lower(), stary


def test_ODMIANA_pilnych_pozycji_po_polsku():
    """W1: jedyny nosnik odmiany odmienial zle — „1 pilne pozycje".

    To zdanie idzie na pasek jako sygnal straznika majacego budzic przy
    braku pieniedzy, a cala racja bytu Z75 brzmi „odmiana po polsku ma
    jeden nosnik w Pythonie". Nosnik istnial i odmienial zle.

    Cztery formy, nie dwie. Nastolatki (12-14) biora forme jak 5+, mimo
    ze koncza sie na 2-4 — to jest ta czesc reguly, ktora wypada z kazdej
    naiwnej implementacji, dlatego 12 i 22 sa w tescie razem.
    """
    assert prezentacja.odmien_pozycje(1) == "1 pilną pozycję"
    assert prezentacja.odmien_pozycje(2) == "2 pilne pozycje"
    assert prezentacja.odmien_pozycje(5) == "5 pilnych pozycji"
    assert prezentacja.odmien_pozycje(12) == "12 pilnych pozycji"
    assert prezentacja.odmien_pozycje(22) == "22 pilne pozycje"


def test_podpis_straznika_UZYWA_odmiany_a_nie_wlasnej_kopii():
    """Kontrola, ze zdanie WOLA nosnik odmiany, zamiast go powtarzac.

    Bez tego `odmien_pozycje` moglby byc poprawny i nieuzywany — dokladnie
    ta klasa wady, ktora w Z73p3 dala trzy nosniki jednej listy.
    """
    def zdanie(ile):
        return prezentacja.podpis_straznika(
            {"kiedy": "2026-09-18T06:00:00", "pilnych": ile, "powod": None,
             "zrodla": "zgodne", "stan_prognozy": "policzona",
             "powiadomiono": True},
            date(2026, 9, 18))

    assert "znalazł 1 pilną pozycję" in zdanie(1), zdanie(1)
    assert "znalazł 5 pilnych pozycji" in zdanie(5), zdanie(5)


def test_BRAK_klucza_stan_prognozy_to_awaria_GLOSNA_nie_uspokojenie():
    """W2: `.get("stan_prognozy")` bylo jedyna miekka sciezka w tej funkcji.

    `kiedy` i `pilnych` czytane sa twardo — rozjazd nazwy kolumny daje
    `KeyError`, awarie glosna. Przy `.get` literowka w nazwie dawala `None`,
    warunek nie zachodzil, funkcja wpadala w `else` i mowila „nic pilnego
    nie znalazl". Cichy powrot do stanu, przed ktorym broni straznik
    `test_ZERO_pilnych_przy_stanie_NIE_WIEM_NIE_uspokaja` — a ksztalt
    slownika jest w testach przepisany ze schematu recznie, wiec rozjazdu
    nazw nikt dzis nie lapie.
    """
    bez_klucza = {"kiedy": "2026-09-18T06:00:00", "pilnych": 0, "powod": None,
                  "zrodla": "zgodne", "powiadomiono": False}
    with pytest.raises(KeyError):
        prezentacja.podpis_straznika(bez_klucza, date(2026, 9, 18))

    # KONTROLA LICZNOSCI: ten sam slownik Z kluczem przechodzi i daje zdanie.
    # Bez tego `pytest.raises` przeszlaby rowniez wtedy, gdyby funkcja
    # wybuchala na czymkolwiek innym.
    z_kluczem = {**bez_klucza, "stan_prognozy": "policzona"}
    assert "nic pilnego" in prezentacja.podpis_straznika(
        z_kluczem, date(2026, 9, 18)).lower()


def test_podpis_terminu_mowi_DZIS_jutro_i_za_ile():
    assert prezentacja.podpis_terminu(0).lower() == "dziś"
    assert prezentacja.podpis_terminu(1).lower() == "jutro"
    # Rownosc, nie zawieranie (D7). `"5" in ...` przeszloby dla „za 5 lat",
    # „5" i „ 5 " — dwie asercje wyzej porownuja przez rownosc, ta odstawala.
    assert prezentacja.podpis_terminu(5) == "za 5 dni"

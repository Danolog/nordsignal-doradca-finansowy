# -*- coding: utf-8 -*-
"""SKLADANIE ODPOWIEDZI EKRANU BUDZET + cztery zapisy tego ekranu.

TEN PLIK NIE LICZY ANI JEDNEJ KWOTY OD ZERA — dokladnie jak
`silnik/ekran_plynnosc.py` i `silnik/ekran_ksiegowanie.py`. Sumy planu liczy
`budzet.sumy_planu`, zestawienie `budzet.wykonanie_planu`, postep celu
`budzet.postep_celu`, rezerwe podatkowa `podatki.rezerwa_z_bazy`, dzien
pozycji `prognoza_plynnosci.dzien_pozycji`. Jedyna arytmetyka w tym pliku to
trzy dodawania, ktore ten ekran OBIECUJE pokazac: bilans planu (przychody
minus wydatki minus oszczednosci), odchylenie (wykonane minus plan) i suma
kafelka „Plan miesiaca razem".

FORMA OPODATKOWANIA NIE MA TU WARTOSCI DOMYSLNEJ I MIEC NIE BEDZIE.
Kafelek „Rezerwa na podatki" idzie przez `podatki.rezerwa_z_bazy`, ktory
czyta forme z bazy i ODMAWIA liczenia, gdy jej nie zna. Ten plik odmowy nie
lata: zamienia ja na kafelek bez kwoty i ze zdaniem silnika w calosci
(`CLAUDE.md` §3.7). OD W11 dotyczy to takze braku DATY ROZPOCZECIA
dzialalnosci — bez niej ZUS nie zostaje policzony w ogole, wiec rezerwa
i suma „Plan miesiaca razem" nie maja kwoty; granica opisana przy
`_rezerwa_albo_odmowa`. W poprzedniej aplikacji ryczalt byl wartoscia domyslna
w trzech miejscach i podawal kwoty wyliczone forma, ktorej Darek nie ma —
slowo „RYCZALT" nie pada w tym pliku ani razu i to nie jest przypadek.

KOSZ KONCZY REGULE, NIE KASUJE (Z-9). `zakoncz_pozycje` wola
`magazyn.zakoncz_plan`, ktory pozycje ciagnaca sie z wczesniej ZAMYKA na
miesiacu M−1, a nie usuwa. `magazyn.usun_plan` istnieje i jest swiadomie
odciety od tego pliku — pilnuje tego
`testy/test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje` oraz
`testy/test_trasy_budzet.py::test_ekran_budzetu_NIE_WOLA_usun_plan`.

GRANICA MIEDZY SILNIKIEM A WIDOKIEM: silnik oddaje LICZBY i NAZWY MIESIECY,
widok sklada z nich proze (`interfejs/lib/napisy.ts`). Wyjatkiem jest zdanie,
ktore niesie liczbe albo odmowe silnika — `KafelekBudzetu.wyjasnienie`
i `CelNaEkranie.tempoNapis`. Zapisu rzymskiego dnia („20 X") nie sklada tu
nic: dzien jedzie polem, a rzymskie cyfry sklada `interfejs/lib/kwota.ts`,
jedyny nosnik tej konwencji.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

import pandas as pd

from silnik import kontrakt
from silnik.ekran_ksiegowanie import ostatnie_wpisy
from silnik.rdzen import budzet, magazyn, podatki, prezentacja
from silnik.rdzen import prognoza_plynnosci as pp

#: Funkcja zamieniajaca kwote na napis kontraktu. W produkcji `api.kwoty.kwota`.
#: BEZ WARTOSCI DOMYSLNEJ — uzasadnienie w naglowku `ekran_ksiegowanie.py`.
NapisKwoty = Callable[..., "str | None"]

#: Klucze trzech kafelkow. Widok siega po nie po NAZWIE, nie po indeksie —
#: kolejnosc listy jest wlasnoscia tego pliku i wolno ja tu zmienic.
KLUCZ_WYDATKI_Z_PLANU = "wydatkiZPlanu"
KLUCZ_REZERWA = "rezerwa"
KLUCZ_RAZEM = "razem"

#: Tytuly i dopiski kafelkow — PRZEPISANE Z RAMKI `makiety/Budzet.dc.html`
#: (linie 3 kafelkow), bo ramka jest wiazaca specyfikacja (`CLAUDE.md` §3.6).
#: Stoja tutaj, a nie w widoku, bo `CLAUDE.md` §3.5 wiaze ETYKIETE Z LICZBA:
#: tytul i liczba maja wychodzic z jednego miejsca, inaczej zmiana rachunku
#: zostawia stary tytul nad nowa liczba. To sie w tym projekcie zdarzylo
#: (kafelek „Zaplanowane wydatki" nad reszta planu powiekszona o rezerwe).
TYTUL_WYDATKI_Z_PLANU = "Wydatki osobiste z planu"
TYTUL_REZERWA = "Rezerwa na podatki"
TYTUL_RAZEM = "Plan miesiąca razem"
DOPISEK_WYDATKI_Z_PLANU = "przepływ tego miesiąca"
DOPISEK_REZERWA = "saldo narastające, nie wydatek miesiąca"
DOPISEK_RAZEM = "to jest kwota z ekranu Miesiąc"

#: Stany odpowiedzi zapisu. `stan` rozstrzyga, CO sie stalo — kod HTTP tego
#: nie rozstrzyga, bo „nadpisalem istniejaca regule" i „zalozylem nowa" to
#: dla uzytkownika dwie rozne wiadomosci, a dla HTTP jedno 200.
STAN_PLAN_USTAWIONY = "plan_ustawiony"
STAN_PLAN_ZAKONCZONY = "plan_zakonczony"
STAN_PLAN_SKOPIOWANY = "plan_skopiowany"
STAN_CEL_DODANY = "cel_dodany"


@dataclass(frozen=True, slots=True)
class OdpowiedzBudzetu:
    """Wynik zapisu razem z odswiezonym ekranem.

    `dane` jedzie w KOMPLECIE swiadomie — wzorzec przejety z
    `ekran_ksiegowanie.OdpowiedzZapisu` i z `PUT /api/kotwica`. Jeden zapis
    na tym ekranie rusza naraz: trzy kafelki, bilans planu, tabele „Plan
    kontra wykonanie", liste pozycji planu i licznik naglowka. Przegladarka,
    ktora doliczylaby je sobie sama, bylaby drugim nosnikiem kazdej z tych
    regul, a rozjazd bylo by widac dopiero po odswiezeniu strony.

    `wynik` niesie SLOWO OD MAGAZYNU, nie przeredagowane: „nowa" /
    „zaktualizowana" / „zwersjonowana" przy ustawianiu, „skasowana" /
    „zamknieta" / „pominieta" przy konczeniu. To jest jedyne miejsce, w
    ktorym uzytkownik dowiaduje sie, czy jego zmiana zalozyla nowa regule,
    czy zamknela stara — a te dwie rzeczy inaczej wygladaja w historii.
    """

    stan: str
    wynik: str
    id: "int | None"
    dane: kontrakt.DaneBudzetu


# --- pomocnicze: miesiac ---------------------------------------------------

def rozloz_miesiac(napis: "str | None", dzis: date) -> tuple[int, int]:
    """„2026-10" -> (2026, 10). Pusty napis znaczy „miesiac dnia dzisiejszego".

    JEDEN NOSNIK formatu miesiaca po stronie tego ekranu. Ten sam ksztalt
    przyjmuje `prezentacja.etykieta_okresu`, wiec napis „2026-10" ma w calym
    projekcie jedno znaczenie i jedna droge do rozlozenia na liczby.
    """
    if napis in (None, ""):
        return dzis.year, dzis.month
    rok, miesiac = str(napis).split("-")[:2]
    numer = int(miesiac)
    if not 1 <= numer <= 12:
        raise magazyn.BladMagazynu(
            f"Nie ma miesiąca o numerze {numer} ({napis!r}). Podaj miesiąc "
            f"w postaci „2026-10”.")
    return int(rok), numer


def _napis_miesiaca(rok: int, miesiac: int) -> str:
    return f"{rok:04d}-{miesiac:02d}"


def _miesiac_wczesniej(rok: int, miesiac: int) -> tuple[int, int]:
    """`M − 1` na osi absolutnej — styczen 2027 daje grudzien 2026.

    WOLA `budzet.ostatnie_miesiace`, publiczny nosnik osi absolutnej, zamiast
    odejmowac numer miesiaca u siebie. Odejmowanie samego numeru daje przy
    przejsciu przez Nowy Rok zero i liczby ujemne — miesiace, ktorych nie ma.
    Ta sama liczba rzadzi napisem „Skopiuj z wrzesnia" i tym, co faktycznie
    zostanie skopiowane; dwa nosniki rozjechalyby sie 1 stycznia.
    """
    return budzet.ostatnie_miesiace(rok, miesiac, 2)[0]


# --- kafelki ---------------------------------------------------------------

def _rezerwa_albo_odmowa(polaczenie, *, wpisy: pd.DataFrame, dzis: date
                         ) -> "tuple[Decimal | None, str | None]":
    """Saldo rezerwy podatkowej ALBO zdanie silnika o tym, czego brakuje.

    ODMOWA JEST TU CZESCIA PRODUKTU, NIE AWARIA (`CLAUDE.md` §3.7).
    `podatki.rezerwa_z_bazy` odmawia liczenia, gdy w bazie nie ma formy
    opodatkowania na ten rok albo gdy forma wymaga stawki, ktorej nie podano.
    Ma racje: kwota policzona zgadnieta forma jest wiarygodna i zla, a od tej
    liczby zalezy, ile pieniedzy Darek odlozy dla urzedu.

    ZERO NIE ZASTEPUJE BRAKU WIEDZY (regula D11). `None` idzie do kafelka
    jako brak kwoty; zero czytaloby sie jako „nic nie jestes winien".

    DWA BRAKUJACE WEJSCIA, JEDNA ODPOWIEDZ (naprawa W11, przeglad Leo).
    Do W11 odmawiala tylko gorna galaz — brak FORMY opodatkowania. Brak DATY
    ROZPOCZECIA dzialalnosci przechodzil dolem i kafelek „Rezerwa na podatki"
    pokazywal `0,00 zl` tam, gdzie prawda na nastawach Darka wynosila
    4 718,60 zl (pomiar Leo, 6 X 2026). Dwa rownie brakujace wejscia byly
    traktowane odwrotnie, a docstring tej funkcji nazywal regule, ktora
    funkcja lamala.

    GRANICA ODMOWY JEST OSTRA I PRZECHODZI PRZEZ `miesiace_zus`:

    * `miesiace_zus is None` — ZUS NIE ZOSTAL POLICZONY W OGOLE, bo silnik
      nie zna daty rozpoczecia. To JEDYNY dyskryminator tego stanu (naglowek
      pola w `podatki.RezerwaPodatkowa`) i tu odmawiamy. Samo `zus == 0` nie
      odroznia „nie liczylem" od „policzylem i wyszlo zero".
    * `miesiace_zus == 0` — data rozpoczecia jest ZNANA i lezy w przyszlosci.
      Miesiac przed rozpoczeciem dzialalnosci naprawde nie niesie skladek,
      wiec zero jest tu WIEDZA, nie brakiem wiedzy, i kafelek ma pokazac
      liczbe razem z zastrzezeniem silnika przy niej (§3.5).

    Ta sama granica stoi w `prezentacja.podpis_rezerwy` i pochodzi z tego
    samego pola — zdania odmowy nie skladamy tutaj, tylko oddajemy
    zastrzezenia silnika w calosci (§3.7). Zastrzezenie przy braku daty NIE
    MOZE podac wielkosci zanizenia, bo bez daty nie zna liczby miesiecy —
    i to jest argument ZA odmowa, a nie za zerem z dopiskiem (§3.5).
    """
    try:
        rezerwa = podatki.rezerwa_z_bazy(polaczenie, wpisy=wpisy, dzis=dzis)
    except magazyn.BladMagazynu as blad:
        return None, str(blad)
    if rezerwa.miesiace_zus is None:
        return None, " ".join(rezerwa.zastrzezenia)
    if rezerwa.zastrzezenia:
        return rezerwa.saldo, " ".join(rezerwa.zastrzezenia)
    return rezerwa.saldo, None


def kafelki(*, plan_wydatkow: Decimal, rezerwa: "Decimal | None",
            wyjasnienie_rezerwy: "str | None", napis_kwoty: NapisKwoty
            ) -> tuple[kontrakt.KafelekBudzetu, ...]:
    """Trzy kafelki nad bilansem. JEDEN NOSNIK pary „tytul + liczba".

    „Plan miesiaca razem" to jedyne dodawanie w tej funkcji i jest to
    dokladnie ta suma, ktora kafelek OBIECUJE w tytule. Gdy rezerwy nie da
    sie policzyc, suma tez sie nie da — i wtedy kafelek nie ma kwoty, zamiast
    pokazywac sam plan wydatkow pod tytulem „razem". Tytul opisujacy inna
    liczbe niz pokazana jest w tym projekcie nazwana wada
    (`docs/2026-08-28-regula-etykieta-opisuje-liczbe.md`).
    """
    razem = None if rezerwa is None else plan_wydatkow + rezerwa
    return (
        kontrakt.KafelekBudzetu(
            klucz=KLUCZ_WYDATKI_Z_PLANU, tytul=TYTUL_WYDATKI_Z_PLANU,
            kwota=napis_kwoty(plan_wydatkow),
            dopisek=DOPISEK_WYDATKI_Z_PLANU, wyjasnienie=None),
        kontrakt.KafelekBudzetu(
            klucz=KLUCZ_REZERWA, tytul=TYTUL_REZERWA,
            kwota=napis_kwoty(rezerwa), dopisek=DOPISEK_REZERWA,
            wyjasnienie=wyjasnienie_rezerwy),
        kontrakt.KafelekBudzetu(
            klucz=KLUCZ_RAZEM, tytul=TYTUL_RAZEM, kwota=napis_kwoty(razem),
            dopisek=DOPISEK_RAZEM, wyjasnienie=wyjasnienie_rezerwy),
    )


# --- tabela „Plan kontra wykonanie" ---------------------------------------

def _pasek(procent: "Decimal | None") -> "int | None":
    """Szerokosc paska postepu w punktach procentowych, przycieta do 0–100.

    PRZYCIECIE JEST WLASNOSCIA PASKA, NIE LICZBY. Wartosc niescieta zostaje
    w `procent` i to ona idzie na ekran jako napis; pasek nie umie byc
    dluzszy niz jego tor, wiec 340% narysowane doslownie wyszloby poza karte
    i wygladalo jak wada ukladu. Przekroczenie niesie `przekroczone`.

    `None` przechodzi nietkniete: planu nie ma, wiec paska tez nie ma. Zero
    narysowaloby pusty pasek, czyli „nic nie wydales z planu, ktory jest" —
    zdanie o czyms, czego nie ma.
    """
    if procent is None:
        return None
    return max(0, min(100, int(procent)))


def pozycje_wykonania(wykonanie, pozycje_planu, *, napis_kwoty: NapisKwoty
                      ) -> tuple[kontrakt.PozycjaWykonania, ...]:
    """Wiersze tabeli, NAJWIEKSZE ODCHYLENIE U GORY (napis z ramki).

    ODCHYLENIE TO `-pozostalo`, nie wlasny rachunek. `budzet.Wykonanie` liczy
    `pozostalo = plan - wykonane` i jest jedynym nosnikiem tej roznicy razem
    z jej zaokragleniem; kolumna „Odchylenie" pokazuje ta sama roznice
    z drugiej strony. Wlasne `wykonane - planowane` bylo by drugim nosnikiem
    i rozjechalo sie przy pierwszej zmianie zaokraglenia.

    POWIAZANIE Z POZYCJA PLANU JEST NIEPEWNE Z NATURY i tak jest oddane.
    Wpis budzetu nie mowi, ktora POZYCJE planu realizuje, wiec wiersz tabeli
    jest per (typ, kategoria). Gdy za wierszem stoi dokladnie jedna pozycja
    planu, jej numer idzie w `idPozycjiPlanu` i widok moze postawic link
    „zmien pozycje"; przy zerze albo dwoch numer jest `None`, a `liczba`
    mowi ktory to z tych dwoch przypadkow.
    """
    numery: dict[tuple[str, str], list[int]] = {}
    for pozycja in pozycje_planu:
        numery.setdefault((pozycja.typ, pozycja.kategoria), []).append(
            pozycja.id)

    # Malejaco po WARTOSCI BEZWZGLEDNEJ odchylenia: „najwieksze odchylenie
    # u gory" (napis z ramki) nie rozroznia kierunku — przekroczenie planu
    # o 800 zl i niewydanie 800 zl sa oba duzym odchyleniem i oba maja byc
    # widoczne. Remis rozstrzyga nazwa, zeby kolejnosc nie zalezala od bazy.
    #
    # SORTUJEMY PO LICZBIE Z SILNIKA, NIE PO NAPISIE ODPOWIEDZI. Napis
    # przeszedl juz przez zaokraglenie do groszy i przez konwencje zapisu —
    # sortowanie po nim wiazaloby kolejnosc wierszy z formatem kwoty, czyli
    # z rzecza, ktora wolno zmienic bez ruszania tej reguly.
    uporzadkowane = sorted(wykonanie,
                           key=lambda w: (-abs(w.pozostalo), w.kategoria))
    return tuple(
        kontrakt.PozycjaWykonania(
            typ=w.typ, kategoria=w.kategoria,
            plan=napis_kwoty(w.planowane), wykonane=napis_kwoty(w.wykonane),
            # Kolumna „Odchylenie" to `pozostalo` z drugiej strony:
            # `plan - wykonane` odwrocone. Wlasne `wykonane - planowane`
            # byloby drugim nosnikiem tej roznicy razem z jej zaokragleniem.
            odchylenie=napis_kwoty(-w.pozostalo),
            procent=prezentacja.procent_wykonania(w.procent),
            procentPaska=_pasek(w.procent), przekroczone=w.przekroczone,
            idPozycjiPlanu=_jedyny_numer(numery.get((w.typ, w.kategoria), [])),
            liczbaPozycjiPlanu=len(numery.get((w.typ, w.kategoria), [])))
        for w in uporzadkowane)


def _jedyny_numer(numery: list) -> "int | None":
    """Numer pozycji planu, gdy jest DOKLADNIE jeden. Inaczej `None`.

    Zero i dwa daja ten sam `None` swiadomie — w obu przypadkach „popraw te
    pozycje" nie ma jednej odpowiedzi. Rozroznia je `liczbaPozycjiPlanu`,
    bo widok musi wiedziec, czy nie ma czego poprawiac, czy jest z czego
    wybierac.
    """
    return numery[0] if len(numery) == 1 else None


# --- pozycje planu obowiazujace w miesiacu --------------------------------

def pozycje_planu(plan: pd.DataFrame, *, rok: int, miesiac: int, dzis: date,
                  napis_kwoty: NapisKwoty
                  ) -> tuple[kontrakt.PozycjaPlanu, ...]:
    """Reguly planu obowiazujace w tym miesiacu — to, co edytuje panel.

    KTORE REGULY OBOWIAZUJA — rozstrzyga `budzet.plan_na_miesiac`, jedyny
    nosnik tej odpowiedzi. Wlasny filtr po wierszach miesiaca nie widzialby
    pozycji trwalej zalozonej wczesniej i ekran pokazywalby pusty plan tam,
    gdzie plan jest.

    CZY POZYCJA JESZCZE CZEKA — rozstrzyga `prognoza_plynnosci.dzien_pozycji`,
    jedyny nosnik reguly „kiedy pozycja schodzi z konta", razem z zalozeniem
    najgorszego przy pozycji bez dnia platnosci (wydatek na 1., przychod na
    ostatni). Wlasne porownanie dnia rozjechaloby sie z osia Plynnosci.
    """
    wybrany = budzet.plan_na_miesiac(plan, rok, miesiac)
    if wybrany.empty:
        return ()
    wynik = []
    for _, w in wybrany.iterrows():
        dzien_platnosci, _domniemany = pp.dzien_pozycji(rok, miesiac, w)
        surowy = w.get("dzien")
        wynik.append(kontrakt.PozycjaPlanu(
            id=int(w["id"]), typ=str(w["typ"]), kategoria=str(w["kategoria"]),
            opis=str(w.get("opis", "") or ""),
            kwota=napis_kwoty(w["kwota_planowana"]),
            dzien=(None if surowy is None or pd.isna(surowy) else int(surowy)),
            coIleMiesiecy=int(w.get("co_ile_miesiecy", 1) or 1),
            czeka=dzien_platnosci >= dzis))
    return tuple(sorted(wynik, key=lambda p: (p.typ, p.kategoria, p.opis)))


# --- cele ------------------------------------------------------------------

def cele_na_ekran(cele: pd.DataFrame, wpisy: pd.DataFrame, *, dzis: date,
                  napis_kwoty: NapisKwoty
                  ) -> tuple[kontrakt.CelNaEkranie, ...]:
    """Cele razem z postepem liczonym Z WPISOW przez `budzet.postep_celu`.

    `tempoNapis` jest jedynym napisem skladanym tutaj i sklada sie z dwoch
    liczb, ktore i tak musialyby przejsc granice osobno („2 000,00 zl / mc
    przez 15 mc"). `None` znaczy „nie ma czego dogadniac albo nie ma juz
    czasu" — cel osiagniety albo po terminie. Napis „0,00 zl / mc" w tym
    miejscu byl by odpowiedzia na pytanie, ktorego nikt nie zadal.
    """
    if cele.empty:
        return ()
    wynik = []
    for _, c in cele.iterrows():
        termin = c["termin"]
        termin = termin if isinstance(termin, date) else date.fromisoformat(
            str(termin))
        postep = budzet.postep_celu(
            wpisy, nazwa=str(c["nazwa"]), kategoria=str(c["kategoria"]),
            kwota_docelowa=Decimal(str(c["kwota_docelowa"])), termin=termin,
            dzis=dzis)
        tempo = (None if postep.tempo_miesieczne is None else
                 f"{prezentacja.zloty(postep.tempo_miesieczne)} / mc przez "
                 f"{postep.miesiecy_do_terminu} mc")
        wynik.append(kontrakt.CelNaEkranie(
            id=int(c["id"]), nazwa=postep.nazwa, kategoria=postep.kategoria,
            kwotaDocelowa=napis_kwoty(postep.kwota_docelowa),
            uzbierane=napis_kwoty(postep.uzbierane),
            brakuje=napis_kwoty(postep.brakuje),
            procent=prezentacja.procent_wykonania(postep.procent),
            procentPaska=_pasek(postep.procent),
            termin=postep.termin.isoformat(), tempoNapis=tempo,
            osiagniety=postep.osiagniety, poTerminie=postep.po_terminie))
    return tuple(wynik)


# --- caly ekran ------------------------------------------------------------

def zbierz(polaczenie, *, dzis: date, napis_kwoty: NapisKwoty,
           miesiac: "str | None" = None) -> kontrakt.DaneBudzetu:
    """Cienki zbieracz: czyta baze przez ISTNIEJACE nosniki, sklada ksztalt.

    ANI JEDNEGO WLASNEGO ZAPYTANIA SQL — wzorzec ten sam co
    `ekran_ksiegowanie.zbierz` i `ekran_plynnosc.zbierz`, i z tego samego
    powodu: kazde powtorzenie odczytu to kolejna okazja, zeby jedno z nich
    podalo silnikowi co innego (zmierzone u poprzednika 2026-08-26: ekran
    mowil -6 098,11 zl, doradca +8 007,89 zl o tej samej rzeczy w tej samej
    chwili).

    HORYZONT (D-23): do wszystkich liczb wchodza WYLACZNIE wpisy od dnia
    rozpoczecia dzialalnosci. 204 wpisy z 2025 sa historia i nie maja
    ustawiac ani wykonania planu, ani postepu celow w 2026 roku.
    """
    rok, numer_miesiaca = rozloz_miesiac(miesiac, dzis)
    dzialalnosc_od = magazyn.odczytaj_dzialalnosc_od(polaczenie)
    wpisy = magazyn.wczytaj_wpisy(polaczenie, od=dzialalnosc_od)
    plan = magazyn.wczytaj_plan(polaczenie)
    cele = magazyn.wczytaj_cele(polaczenie)

    sumy = budzet.sumy_planu(plan, rok, numer_miesiaca)
    rezerwa, wyjasnienie = _rezerwa_albo_odmowa(polaczenie, wpisy=wpisy,
                                                dzis=dzis)
    pozycje = pozycje_planu(plan, rok=rok, miesiac=numer_miesiaca, dzis=dzis,
                            napis_kwoty=napis_kwoty)
    cele_ekranu = cele_na_ekran(cele, wpisy, dzis=dzis,
                                napis_kwoty=napis_kwoty)
    w_miesiacu = budzet.wpisy_miesiaca(wpisy, rok, numer_miesiaca)
    wykonanie_wydatkow = budzet.wykonanie_typu(
        wpisy, plan, rok, numer_miesiaca, budzet.TYP_WYDATKI)
    zrodlo_kopii = _miesiac_wczesniej(rok, numer_miesiaca)
    przebieg = magazyn.ostatni_przebieg_straznika(polaczenie)

    return kontrakt.DaneBudzetu(
        dzisiaj=dzis.isoformat(),
        miesiac=_napis_miesiaca(rok, numer_miesiaca),
        miesiacNapis=prezentacja.etykieta_okresu(
            _napis_miesiaca(rok, numer_miesiaca)),
        nazwaMiesiaca=prezentacja.MIESIACE_MIEJSCOWNIK[numer_miesiaca - 1],
        # NAGLOWEK RAMKI LICZY TAKZE CELE („4 pozycje planu" = trzy wydatki
        # + jeden cel). Sama dlugosc `pozycjePlanu` dalaby trzy, a etykieta
        # opisywalaby wtedy inna liczbe niz ta, ktora widac pod spodem.
        liczbaPozycjiPlanu=len(pozycje) + len(cele_ekranu),
        liczbaWpisow=len(w_miesiacu),
        kafelki=kafelki(plan_wydatkow=sumy[budzet.TYP_WYDATKI],
                        rezerwa=rezerwa, wyjasnienie_rezerwy=wyjasnienie,
                        napis_kwoty=napis_kwoty),
        planPrzychodow=napis_kwoty(sumy[budzet.TYP_PRZYCHODY]),
        planWydatkow=napis_kwoty(sumy[budzet.TYP_WYDATKI]),
        planOszczednosci=napis_kwoty(sumy[budzet.TYP_OSZCZEDNOSCI]),
        # Bilans planu — jedyne odejmowanie na tym ekranie i dokladnie to,
        # co obiecuje etykieta „tyle zostanie, gdy zrealizujesz plan co do
        # zlotowki". `budzet.do_alokacji_z_planu` NIE nadaje sie tutaj: on
        # zwraca `None` przy miesiacu bez planu i wyklucza kategorie podatkow,
        # bo odpowiada na inne pytanie (wolne srodki po rezerwie).
        bilansPlanu=napis_kwoty(sumy[budzet.TYP_PRZYCHODY]
                                - sumy[budzet.TYP_WYDATKI]
                                - sumy[budzet.TYP_OSZCZEDNOSCI]),
        wykonaneWydatki=napis_kwoty(wykonanie_wydatkow.wykonane),
        pozycjeWykonania=pozycje_wykonania(
            budzet.wykonanie_planu(wpisy, plan, rok, numer_miesiaca),
            pozycje, napis_kwoty=napis_kwoty),
        pozycjePlanu=pozycje,
        cele=cele_ekranu,
        # WSZYSTKIE wpisy miesiaca, nie szesc: tabela „Historia" sluzy do
        # poprawiania pomylek, wiec urwana na szostym wpisie zostawialaby
        # siodmy bez drogi do poprawki. Zamiana wiersza na ksztalt kontraktu
        # idzie przez JEDEN nosnik — ten sam, ktory sklada „Ostatnie wpisy".
        historia=ostatnie_wpisy(w_miesiacu, napis_kwoty=napis_kwoty,
                                ile=len(w_miesiacu)),
        miesiacKopiujZ=_napis_miesiaca(*zrodlo_kopii),
        napisKopiujZ=("Skopiuj z "
                      + prezentacja.MIESIACE_DOPELNIACZ[zrodlo_kopii[1] - 1]),
        # `None` = straznik NIGDY nie dzialal i tylko to (regula D11).
        # Zdanie sklada jedyny nosnik: `prezentacja.podpis_straznika`.
        ostatnieSprawdzenie=(None if przebieg is None
                             else prezentacja.podpis_straznika(przebieg, dzis)))


# --- cztery zapisy ---------------------------------------------------------

def ustaw_pozycje(polaczenie, *, miesiac, typ, kategoria, kwota, opis=None,
                  dzien=None, co_ile_miesiecy=None, dzis: date,
                  napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """„Dodaj pozycje planu" — regula obowiazujaca OD wskazanego miesiaca.

    WOLA `ustal_regule_planu`, NIE `zapisz_plan`. Roznica jest regula
    produktowa, nie szczegolem: `zapisz_plan` zapisuje plan na JEDEN miesiac,
    a pozycja zalozona na ekranie Budzet ma obowiazywac do odwolania —
    dokladnie dlatego jej kosz nazywa sie „Zakoncz", a nie „Usun". Gdyby
    pozycje byly jednomiesieczne, konczyc nie byloby czego.

    KWOTA JEST NAPISEM PO OBU STRONACH GRANICY. `Decimal(str(...))` przyjmuje
    napis z zadania HTTP i nie przechodzi przez liczbe zmiennoprzecinkowa
    ani przez chwile — u poprzednika taka chwila gubila grosze i zwracala 200.
    """
    rok, numer = rozloz_miesiac(miesiac, dzis)
    # SPRAWDZENIE PRZED ZAPISEM, a nie po. `ustal_regule_planu` kategorii NIE
    # sprawdza — jest wolane takze przez import arkusza, ktory zasiewa slownik
    # i plan w jednym przebiegu. Zadanie HTTP bez kategorii dawalo bez tego
    # pozycje planu o nazwie „None": kwote w planie, ktorej zaden wpis nigdy
    # nie wykona i ktora nie wyglada na blad. Regula jest wolana z jedynego
    # nosnika (`magazyn.wymagaj_kategorii`), nie powtorzona tutaj.
    kategoria = magazyn.wymagaj_kategorii(
        polaczenie, magazyn.wymagaj_typu(typ), kategoria)
    wynik = magazyn.ustal_regule_planu(
        polaczenie, rok=rok, miesiac=numer, typ=typ, kategoria=kategoria,
        kwota_planowana=_kwota_do_zapisu(kwota), opis=opis or "", dzien=dzien,
        co_ile_miesiecy=co_ile_miesiecy)
    return _odpowiedz(polaczenie, stan=STAN_PLAN_USTAWIONY, wynik=wynik,
                      numer=None, miesiac=miesiac, dzis=dzis,
                      napis_kwoty=napis_kwoty)


def zmien_pozycje(polaczenie, *, plan_id: int, miesiac, kwota, dzien=None,
                  co_ile_miesiecy=None, dzis: date,
                  napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """„Zmien pozycje planu" — zmiana obowiazuje OD wskazanego miesiaca w przod.

    TOZSAMOSC POZYCJI BIERZE SIE Z WIERSZA, NIE Z ZADANIA. Numer wskazuje
    pozycje; typ, kategoria i opis sa odczytane z bazy i ta trasa ich NIE
    zmienia. Zmiana kategorii przez ta droge nie jest poprawka tej samej
    pozycji, tylko podmiana jednej pozycji na inna — a wykonanie policzone
    juz w starej kategorii zostaloby przy niej i wiersz tabeli rozjechalby
    sie z historia. Kto chce innej kategorii, konczy pozycje i zaklada nowa.

    HISTORIA ZOSTAJE NIETKNIETA: `ustal_regule_planu` przy regule ciagnacej
    sie z wczesniej ZAMYKA ja na M−1 i zaklada nowa od M, zamiast nadpisac
    kwote takze w miesiacach juz zamknietych.
    """
    wiersz = magazyn.wczytaj_pozycje_planu(polaczenie, plan_id=int(plan_id))
    rok, numer = rozloz_miesiac(miesiac, dzis)
    wynik = magazyn.ustal_regule_planu(
        polaczenie, rok=rok, miesiac=numer, typ=str(wiersz["typ"]),
        kategoria=str(wiersz["kategoria"]),
        kwota_planowana=_kwota_do_zapisu(kwota),
        opis=str(wiersz.get("opis", "") or ""), dzien=dzien,
        co_ile_miesiecy=co_ile_miesiecy)
    return _odpowiedz(polaczenie, stan=STAN_PLAN_USTAWIONY, wynik=wynik,
                      numer=int(plan_id), miesiac=miesiac, dzis=dzis,
                      napis_kwoty=napis_kwoty)


def zakoncz_pozycje(polaczenie, *, plan_id: int, miesiac, zakres=None,
                    dzis: date, napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """„Zakoncz te pozycje od <miesiac>" — KONIEC REGULY, NIGDY KASOWANIE.

    Po ludzku: pazdziernik i listopad nadal pokazuja, ze pozycja byla
    zaplanowana i ile z niej wykonano. Zmienia sie wylacznie PRZYSZLOSC —
    od wskazanego miesiaca w przod pozycja przestaje sie pojawiac w planie.

    `magazyn.usun_plan` istnieje i jest SWIADOMIE nieuzyty (Z-9). Nowa
    aplikacja ma to zachowanie przejac, nie „naprawic". Wiersz znika z bazy
    w jednym przypadku i tylko w nim: gdy regula ZACZYNA sie w tym samym
    miesiacu, w ktorym ja konczymy — bo wtedy nie ma zadnej przeszlosci do
    zachowania. Rozstrzyga to `magazyn.zakoncz_plan`, nie ta funkcja.
    """
    wiersz = magazyn.wczytaj_pozycje_planu(polaczenie, plan_id=int(plan_id))
    rok, numer = rozloz_miesiac(miesiac, dzis)
    wynik = magazyn.zakoncz_plan(
        polaczenie, rok=rok, miesiac=numer, typ=str(wiersz["typ"]),
        kategoria=str(wiersz["kategoria"]),
        opis=str(wiersz.get("opis", "") or ""),
        zakres=zakres or magazyn.ZAKRES_TEN_I_NASTEPNE)
    return _odpowiedz(polaczenie, stan=STAN_PLAN_ZAKONCZONY, wynik=wynik,
                      numer=int(plan_id), miesiac=miesiac, dzis=dzis,
                      napis_kwoty=napis_kwoty)


def kopiuj(polaczenie, *, miesiac, z_miesiaca=None, dzis: date,
           napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """„Skopiuj z wrzesnia" — plan poprzedniego miesiaca na wskazany.

    ZRODLO WYPROWADZA SIE Z CELU, gdy nie podano go wprost — tym samym
    nosnikiem, ktorym ekran sklada napis przycisku (`_miesiac_wczesniej`).
    Gdyby przegladarka podawala oba miesiace z wlasnego rachunku, napis
    „Skopiuj z wrzesnia" i faktycznie skopiowany miesiac mialyby dwa rozne
    nosniki i rozjechalyby sie na Nowym Roku.

    NIE NADPISUJE pozycji juz istniejacych w miesiacu docelowym — reczna
    poprawka jest cenniejsza niz kopia. `magazyn.kopiuj_plan` zwraca DWIE
    liczby (skopiowane, pominiete), bo „skopiowano 12" nie odroznia pelnego
    przeniesienia od takiego, ktore ominelo polowe pozycji.
    """
    rok, numer = rozloz_miesiac(miesiac, dzis)
    z_rok, z_numer = (rozloz_miesiac(z_miesiaca, dzis) if z_miesiaca
                      else _miesiac_wczesniej(rok, numer))
    skopiowane, pominiete = magazyn.kopiuj_plan(
        polaczenie, z_roku=z_rok, z_miesiaca=z_numer, do_roku=rok,
        do_miesiaca=numer)
    return _odpowiedz(
        polaczenie, stan=STAN_PLAN_SKOPIOWANY,
        wynik=f"skopiowane {skopiowane}, pominiete {pominiete}", numer=None,
        miesiac=miesiac, dzis=dzis, napis_kwoty=napis_kwoty)


def dodaj_cel(polaczenie, *, nazwa, kategoria, kwota_docelowa, termin,
              miesiac=None, dzis: date,
              napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """„Dodaj cel" — cel oszczednosciowy wskazujacy kategorie oszczednosci.

    Ze kategoria MUSI byc typu „Oszczednosci", rozstrzyga `magazyn.zapisz_cel`
    i nic tego tutaj nie zmiekcza: cel wskazujacy kategorie wydatku liczylby
    postep z pieniedzy WYDANYCH — pasek pokazywalby, ze zbierasz na wakacje,
    im wiecej wydajesz na zakupy.
    """
    numer = magazyn.zapisz_cel(
        polaczenie, nazwa=nazwa, kategoria=kategoria,
        kwota_docelowa=_kwota_do_zapisu(kwota_docelowa),
        termin=_termin(termin))
    return _odpowiedz(polaczenie, stan=STAN_CEL_DODANY, wynik="nowy",
                      numer=int(numer), miesiac=miesiac, dzis=dzis,
                      napis_kwoty=napis_kwoty)


# --- wspolne dla zapisow ---------------------------------------------------

def _kwota_do_zapisu(surowa) -> Decimal:
    """Napis z zadania HTTP na typ dziesietny, BEZ liczby zmiennoprzecinkowej.

    `Decimal(str(x))`, nie `Decimal(x)`: gdyby po drugiej stronie granicy
    ktos przyslal liczbe zmiennoprzecinkowa, `Decimal(0.1)` zapisalby
    0,1000000000000000055511151231257827. Napis jest tu jedyna droga i to
    jest ta sama regula, ktora rzadzi kwotami w odpowiedzi.
    """
    # Spacja zwykla i NIEROZDZIELAJACA (U+00A0). Ta druga wraca do nas
    # z pola, w ktorym uzytkownik nie wyczyscil sformatowanej kwoty —
    # `prezentacja.SEPARATOR_TYSIECY` wstawia wlasnie ja.
    tekst = str(surowa).strip().replace(" ", "").replace("\u00a0", "")
    if not tekst:
        raise magazyn.BladMagazynu(
            "Kwota jest pusta. Podaj kwotę, na przykład 660,00.")
    return Decimal(tekst.replace(",", "."))


def _termin(surowy) -> date:
    if isinstance(surowy, date):
        return surowy
    if surowy in (None, ""):
        raise magazyn.BladMagazynu(
            "Cel bez terminu jest życzeniem, nie celem. Podaj datę, do której "
            "chcesz uzbierać.")
    return date.fromisoformat(str(surowy))


def _odpowiedz(polaczenie, *, stan: str, wynik: str, numer: "int | None",
               miesiac, dzis: date,
               napis_kwoty: NapisKwoty) -> OdpowiedzBudzetu:
    """Ekran PO zapisie — jeden nosnik skladania odpowiedzi wszystkich zapisow."""
    return OdpowiedzBudzetu(
        stan=stan, wynik=wynik, id=numer,
        dane=zbierz(polaczenie, dzis=dzis, napis_kwoty=napis_kwoty,
                    miesiac=miesiac))

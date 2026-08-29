"""Prognoza plynnosci na osi DZIENNEJ — czysta arytmetyka (Z62, zdolnosc A1).

OSOBNY MODUL, nie rozszerzenie `rdzen/prognoza.py`. Tamten odpowiada na inne
pytanie — kiedy przychod przetnie prog skladki zdrowotnej — pracuje na osi
miesiecznej i nie zna ani salda konta, ani wydatkow. Doklejenie tu salda
zrobiloby z niego modul o dwoch niepowiazanych regulach.

DLACZEGO OS JEST DZIENNA (specyfikacja §4.2). Dwudziestego wychodzi ZUS
i zaliczka, dwudziestego piatego VAT. Jesli faktura wplynie dwudziestego
szostego, przez szesc dni saldo jest ujemne, a na koniec miesiaca dodatnie.
Prognoza miesieczna tego NIE POKAZE — a to jest dokladnie ten stan, przed
ktorym aplikacja ma ostrzegac.

DLACZEGO FUNKCJA CZYSTA. Zmierzone na czystej kopii commita `8c119a0`:
`wolne_srodki(plan, miesiace, Decimal("0"))` — zdjecie rezerwy podatkowej,
zawyzenie naglowka o 5 768,11 zl — przeszlo caly przebieg 532 testow.
Straznik postawiony na ARGUMENTACH funkcji czystej lapie te klase mutacji.
Straznik postawiony na funkcji czytajacej baze nie lapie nic, bo argumenty
powstaja w jej srodku. Czytanie bazy jest w `prognozuj` (Z63), tutaj nie ma
ani jednego zapytania.

KOLEJNOSC OBLICZEN — jeden przebieg w przod, bez iteracji. Danina zalezy od
przychodu, przychod od linii, saldo od daniny — ale **danina nigdy nie zalezy
od salda**, wiec petla sie nie zamyka.

CZEGO TEN MODUL SWIADOMIE NIE ROBI:
  * kolejnosci zdarzen w obrebie dnia — bank tez jej nie gwarantuje; dzien
    domykajacy sie na zerze raportujemy jako „nie ponizej zera";
  * rat z tabeli `zobowiazania` — wynik niesie ich pelna liste, a ekran mowi
    „sprawdz, czy te dwie sa w planie". Dopasowywanie po nazwie bylo by
    zgadywaniem, a raty siedza i w tabeli, i w planie (`budzet.py:242-243`);
  * pasma ufnosci — dwa nazwane scenariusze, oba policzone dokladnie;
  * swiat — dziedziczymy `terminy.ZALOZENIA`;
  * kosztow firmowych w przyszlych miesiacach — prognoza ich nie zna
    i zalozenie zerowe jest tu OSTROZNE (koszt obniza dochod, wiec zerowy
    koszt zawyza danine, nie saldo).

DATA EFEKTYWNA (R7) NIE DOTYCZY TEGO MODULU — pyta o miesiac BUDZETU,
a prognoza pyta o konto. Nazwane jawnie, bo inaczej ktos to „naprawi".
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from silnik.rdzen import budzet, magazyn, podatki, stawki, terminy

#: Stan wyniku. TRZY, nie dwa — patrz specyfikacja §5.2.
STAN_POLICZONA = "policzona"
STAN_NIE_WIEM = "nie_wiem"
STAN_NIEAKTUALNA = "nieaktualna"

#: Rodzaje zdarzen na osi. Rozdzielone, bo swiezosc kotwicy (R18) liczy sie
#: WYLACZNIE z danin, zaleglosci i pozycji planu — nigdy z przewidywanego
#: wplywu, ktory jeszcze nie nastapil.
RODZAJ_PLAN = "plan"
RODZAJ_DANINA = "danina"
RODZAJ_ZALEGLOSC = "zaleglosc"
RODZAJ_PRZYCHOD_JDG = "przychod_jdg"
#: Wpis faktyczny — to, co sie WYDARZYLO. Osobny rodzaj od `plan`, bo
#: prognoza musi umiec powiedziec, ktora czesc osi jest realizacja,
#: a ktora przewidywaniem (D-20).
RODZAJ_WPIS = "wpis"

#: PODZIAL RODZAJOW NA WPLYWY I WYPLYWY — JEDEN NOSNIK, od Z7b tutaj.
#:
#: Do Z7b podzial stal w `co_mnie_czeka.py` jako SWIADOMY drugi nosnik,
#: z jawnym progiem konsolidacji: *„PIERWSZY NOWY RODZAJ ZDARZENIA
#: w `prognoza_plynnosci`. Wtedy podzial przenosi sie do nosnika prognozy,
#: a tutaj zostaje wolanie."* `RODZAJ_WPIS` (D-20) jest tym pierwszym nowym
#: rodzajem, wiec **prog zadzialal i dlug zostaje splacony**, a nie przesuniety.
#: Wykryl to straznik `test_RODZAJE_WYPLYWU_pokrywaja_KOMPLET_rodzajow_prognozy`,
#: nie czujnosc autora.
#:
#: `RODZAJ_WPIS` jest po stronie WYPLYWOW, mimo ze wpis bywa przychodem:
#: znak rozstrzyga wolajacy osobno (`if kwota >= 0: continue`), a ta krotka
#: odpowiada wylacznie na pytanie „czy ten rodzaj W OGOLE moze byc wyplywem".
RODZAJE_WYPLYWU = (RODZAJ_DANINA, RODZAJ_ZALEGLOSC, RODZAJ_PLAN, RODZAJ_WPIS)
RODZAJE_WPLYWU = (RODZAJ_PRZYCHOD_JDG,)

#: Kody zastrzezen — ekran renderuje `tekst` od silnika bez przeredagowania,
#: a `kod` sluzy do rozpoznania rodzaju bez parsowania zdania.
KOD_BRAK_KOTWICY = "brak_kotwicy"
KOD_BRAK_WOLUMENU = "brak_wolumenu"
KOD_BRAK_WOLUMENU_REALNEGO = "brak_wolumenu_realnego"
KOD_BRAK_FORMY = "brak_formy"
KOD_DZIEN_DOMNIEMANY = "dzien_domniemany"
KOD_KOTWICA_NIEAKTUALNA = "kotwica_nieaktualna"
KOD_MIESIACE_BEZ_PLANU = "miesiace_bez_planu"
KOD_NARASTAJACO_OD_ZERA = "narastajaco_od_zera"

#: Szesc miesiecy — nie z gustu. Danina ostatniego miesiaca placi sie POZA
#: horyzontem, wiec ogon jest z natury zawyzony; przy trzech miesiacach trzeci
#: bylby bezuzyteczny. `"6"` juz istnieje w `NASTAWY_OKRESU`, a kazde szesc
#: miesiecy przechodzi przez przelom roku — czyli cwiczy `_nastepny_miesiac`
#: i reset przychodu narastajaco.
HORYZONT_DOMYSLNY = 6

#: Twardy sufit swiezosci kotwicy (R18), obok reguly zdarzeniowej.
SUFIT_SWIEZOSCI_DNI = 31


@dataclass(frozen=True)
class Kotwica:
    """Stan konta odczytany danego dnia. JEDYNY dopuszczalny punkt startu.

    Saldo ksiegowe nim nie jest: to suma znakowana wpisow od pazdziernika,
    a nie pieniadze na koncie (R11, specyfikacja §4.3).
    """

    data: date
    kwota: Decimal


@dataclass(frozen=True)
class Wolumen:
    """Godziny miesiecznie w dwoch scenariuszach plus stawka godzinowa.

    `ostrozny is None` ODMAWIA obu linii (R17): rysowanie samej realnej
    daloby zielony obraz z wylaczonym mechanizmem ostrzegania.
    """

    ostrozny: Decimal | None
    realny: Decimal | None
    stawka: Decimal


@dataclass(frozen=True)
class Zastrzezenie:
    """Czego ta prognoza NIE obejmuje — kod, zdanie od silnika i liczba.

    Liczba nie jest ozdoba: „7 pozycji nie ma dnia" mowi cos innego niz
    „niektore pozycje nie maja dnia", a ekran ma powtorzyc zdanie silnika,
    nie napisac wlasne.
    """

    kod: str
    tekst: str
    liczba: int | None = None


@dataclass(frozen=True)
class Zdarzenie:
    """Jeden ruch na koncie danego dnia, ze znakiem. Ujemna kwota = wyplyw.

    DWIE kwoty, bo daniny licza sie OSOBNO dla kazdej linii (§4.2): wyzszy
    przychod to wyzszy VAT i wyzsza zaliczka. To dwa pelne scenariusze,
    nie dwie linie przychodu na jednym koszcie.
    """

    nazwa: str
    rodzaj: str
    kwota_ostrozna: Decimal
    kwota_realna: Decimal
    dzien_domniemany: bool = False


@dataclass(frozen=True)
class Dzien:
    """Jeden dzien osi: obie linie w JEDNYM wierszu, zdarzenia doczepione.

    Gesta seria dzienna, a nie lista zdarzen — lista zmusilaby przegladarke
    do kumulacji, czyli uczynila ja DRUGIM NOSNIKIEM reguly salda.
    """

    data: date
    saldo_ostrozne: Decimal
    saldo_realne: Decimal
    zdarzenia: tuple[Zdarzenie, ...] = ()


@dataclass(frozen=True)
class Prognoza:
    """Wynik. „Nie wiem" ma TRZY nosniki naraz, bo trzy braki moga wystapic
    jednoczesnie:

    * `stan` — policzona / nie_wiem / nieaktualna;
    * `dni is None` — JEDYNY dyskryminator „nie liczylem". `pierwszy_dzien_
      ujemny is None` przy `stan="policzona"` znaczy cos przeciwnego:
      **dobra wiadomosc**;
    * `zastrzezenia` — kod, zdanie i liczba.
    """

    stan: str
    dni: tuple[Dzien, ...] | None
    zastrzezenia: tuple[Zastrzezenie, ...] = ()
    daniny_policzone: bool = False
    dzien_domniemany: bool = False
    ostatni_dzien_pelny: date | None = None
    pierwszy_dzien_ujemny: date | None = None
    minimum: Decimal | None = None
    brakuje: Decimal | None = None
    zobowiazania_spoza_planu: tuple = ()
    horyzont_miesiecy: int = HORYZONT_DOMYSLNY


# --- pomocnicze: kalendarz osi -------------------------------------------

def _miesiace_osi(od: date, ile: int) -> list[tuple[int, int]]:
    """Miesiace osi, liczac od miesiaca KOTWICY. Wola nosnik z `terminy`."""
    lista = [(od.year, od.month)]
    for _ in range(ile - 1):
        lista.append(terminy._nastepny_miesiac(*lista[-1]))
    return lista


def _ostatni_dzien(rok: int, miesiac: int) -> date:
    return terminy.dzien_w_miesiacu(rok, miesiac, terminy.DZIEN_MAX)


def _dzien_pozycji(rok: int, miesiac: int, wiersz) -> tuple[date, bool]:
    """Kiedy pozycja planu schodzi z konta. Zwraca date i „czy domniemana".

    Bez dnia platnosci zakladamy NAJGORZEJ, konsekwentnie wg kierunku:
    wydatek i oszczednosc na 1. (pieniadz wychodzi jak najwczesniej),
    przychod na ostatni (wchodzi jak najpozniej). Obie linie ta sama regula —
    inaczej roznica miedzy nimi niosla by takze roznice zalozen.
    """
    surowy = wiersz.get("dzien")
    if surowy is None or (isinstance(surowy, float) and pd.isna(surowy)) \
            or pd.isna(surowy):
        if wiersz["typ"] == budzet.TYP_PRZYCHODY:
            return _ostatni_dzien(rok, miesiac), True
        return date(rok, miesiac, 1), True
    return terminy.dzien_w_miesiacu(rok, miesiac, int(surowy)), False


# --- pomocnicze: daniny --------------------------------------------------

def _argumenty_daniny(forma: magazyn.FormaRoku, *, netto: Decimal,
                      przychod: Decimal, dochod: Decimal,
                      zaliczki: Decimal) -> dict:
    """Argumenty dla `podatki.policz` — rozne dla obu form.

    Ten modul NIE liczy podatku ANI nie wie, ktorej formie co przysluguje.
    Od 2026-08-28 komplet argumentow ma JEDEN nosnik —
    `podatki.argumenty_dla_formy` — a ta funkcja jest jego cienkim wolaczem,
    ktory dokłada dwie nastawy wlasciwe prognozie: stawke VAT domyslna
    i `skladki_juz_naliczone_w_miesiacu=False` (prognoza planuje przyszlosc,
    w ktorej nic jeszcze naliczone nie jest).

    Powod konsolidacji: ta wiedza byla tu PRYWATNA, wiec formularz faktury
    i narzedzie doradcy nie mialy jej skad wziac i wolaly ryczalt na sztywno.
    """
    return podatki.argumenty_dla_formy(
        forma.forma, kwota_netto=netto,
        stawka_vat=stawki.STAWKA_VAT_DOMYSLNA,
        stawka_ryczaltu=forma.stawka_ryczaltu,
        przychod_narastajaco=przychod, dochod_narastajaco=dochod,
        zaliczki_naliczone=zaliczki,
        skladki_juz_naliczone_w_miesiacu=False, koszty=Decimal("0"))


def _kwoty_danin(wyliczenie, nazwa_podatku: str) -> dict[str, Decimal]:
    """Rozbicie faktury na daniny NAZWANE tak, jak nazywa je `terminy`.

    Nazwy musza sie zgadzac z nosnikiem terminow, bo to po nazwie dopina sie
    date platnosci. Rozjazd nazw dalby danine bez terminu — czyli kwote,
    ktora nigdy nie schodzi z konta.
    """
    return {
        "VAT": wyliczenie.vat,
        "ZUS": wyliczenie.zdrowotna + wyliczenie.spoleczne,
        nazwa_podatku: wyliczenie.pit,
    }


def _nazwa_podatku(forma: magazyn.FormaRoku) -> str:
    return "Ryczałt" if forma.forma == magazyn.FORMA_RYCZALT else "PIT"


# --- rdzen ---------------------------------------------------------------

@dataclass(frozen=True)
class PozycjaOsi:
    """Jedna pozycja gotowa do wstawienia na os — plan albo wpis."""

    dzien: date
    nazwa: str
    kwota: Decimal          # ZE ZNAKIEM: wydatek ujemny, przychod dodatni
    rodzaj: str
    domniemany: bool = False


def podziel_os(*, pozycje_planu, wpisy, dzis: date) -> tuple[PozycjaOsi, ...]:
    """JEDEN NOSNIK REGULY PODZIALU OSI — D-20 i D-61 razem.

    D-20 (decyzja Darka 2026-08-28, g. 18:04): **dni minione licza sie
    z rzeczywistych wpisow, dni przyszle z planu.** Darek odrzucil proste
    odejmowanie wydanego od planu, bo *„dziala tylko w jedna strone i grozi
    podwojnym liczeniem"*. Os ma DWA ZRODLA, nie jedno zrodlo z korekta.

    Bez tej reguly kto wydal ponad plan, widzi sytuacje LEPSZA, niz jest:
    plan mowi, ze wyda 330 zl, wiec os odejmuje 330 zl — niezaleznie od tego,
    czy wydal 274 zl, 500 zl, czy nic.

    D-61 (Sophia, 2026-08-29) domyka jedyna luke, ktorej D-20 nie zamykala:
    **co z pozycja planu na dzien PRZYSZLY w kategorii, w ktorej wydatek juz
    padl.** Bez niej podwojne liczenie wchodzi innymi drzwiami — nie przez
    odejmowanie, lecz przez pozycje planu, ktora nie wie, ze zostala
    zaplacona. Zmierzone na bazie-wzorcu: plan X 2026 ma „Energia
    Elektryczna" 330,00 zl na 20 X; wpis 274,06 zl pada 6 X; bez reguly os
    policzylaby **604,06 zl za prad w jednym miesiacu**.

    **Regula: wpis konsumuje pozycje planu tej samej kategorii w tym samym
    miesiacu, az do zera, w kolejnosci dat. Nadwyzka ponad plan obciaza os
    w calosci i bez kompensaty** — to asymetria D-9 przeniesiona z kafelka
    na os: nadwyzka wydatku pogarsza obraz, nadwyzka przychodu go nie
    poprawia.

    KONSUMPCJA DOTYCZY WYLACZNIE POZYCJI, KTORE ZOSTAJA NA OSI (dzien > dzis).
    Pozycja planu na dzien miniony znika niezaleznie od wpisow — przeszlosc
    opisuja wpisy, nie zamiary. To jest literalne czytanie slowa „pozostale"
    z D-61 i **jedyna niejednoznacznosc tej reguly**: gdy kategoria ma w tym
    samym miesiacu pozycje planu i minione, i przyszle, wpis konsumuje
    przyszla, a miniona i tak odpada. Nazwane wprost, zeby nastepny wykonawca
    nie musial tego odgadywac z kodu.

    KLUCZ KONSUMPCJI TO (typ, kategoria), nie sama kategoria. Wpis
    przychodowy nie ma konsumowac planu wydatku o tej samej nazwie —
    to bylaby kompensata, ktorej D-9 zabrania.

    Zwraca pozycje gotowe na os. NIE dotyka bazy, nie zna kotwicy ani
    horyzontu — obciecie do okna robi wolajacy.
    """
    wpisy = tuple(wpisy or ())
    plan = tuple(pozycje_planu or ())

    # KROK 1 (D-20): plan opisuje wylacznie PRZYSZLOSC.
    przyszly_plan = sorted((p for p in plan if p.dzien > dzis),
                           key=lambda p: (p.dzien, p.nazwa))

    # KROK 2 (D-61): ile kazda para (typ, kategoria) juz skonsumowala.
    do_skonsumowania: dict[tuple[str, str], Decimal] = {}
    for w in wpisy:
        klucz = (w.rodzaj_typ, w.kategoria)
        do_skonsumowania[klucz] = (do_skonsumowania.get(klucz, Decimal("0"))
                                   + abs(w.kwota))

    # KROK 3: konsumpcja w kolejnosci dat, az do zera.
    zostaje: list[PozycjaOsi] = []
    for p in przyszly_plan:
        klucz = (p.rodzaj_typ, p.kategoria)
        budzet_konsumpcji = do_skonsumowania.get(klucz, Decimal("0"))
        if budzet_konsumpcji <= 0:
            zostaje.append(p.na_os())
            continue
        wartosc = abs(p.kwota)
        zjedzone = min(wartosc, budzet_konsumpcji)
        do_skonsumowania[klucz] = budzet_konsumpcji - zjedzone
        reszta = wartosc - zjedzone
        if reszta > 0:
            znak_pozycji = -1 if p.kwota < 0 else 1
            zostaje.append(p.na_os(kwota=znak_pozycji * reszta))
        # reszta == 0 -> pozycja zjedzona w calosci, nie wchodzi na os

    # KROK 4: wpisy wchodza W CALOSCI, na wlasnych datach.
    zostaje.extend(w.na_os() for w in wpisy)
    return tuple(zostaje)


@dataclass(frozen=True)
class _Wejscie:
    """Pozycja przed podzialem osi — plan albo wpis, w jednym ksztalcie.

    `rodzaj_typ` to typ budzetowy (`Wydatki`/`Przychody`/`Oszczednosci`),
    a nie rodzaj zdarzenia — nazwa jest niezreczna, ale rozroznienie jest
    konieczne: klucz konsumpcji stoi na typie budzetowym.
    """

    dzien: date
    nazwa: str
    kwota: Decimal
    rodzaj: str
    rodzaj_typ: str
    kategoria: str
    domniemany: bool = False

    def na_os(self, kwota: "Decimal | None" = None) -> PozycjaOsi:
        return PozycjaOsi(
            dzien=self.dzien, nazwa=self.nazwa,
            kwota=self.kwota if kwota is None else kwota,
            rodzaj=self.rodzaj, domniemany=self.domniemany)


def _wpisy_wg_miesiaca(wpisy) -> dict[tuple[int, int], tuple[_Wejscie, ...]]:
    """Wpisy faktyczne przelozone na pozycje osi, pogrupowane po miesiacu.

    DWIE KATEGORIE ODPADAJA, obie z tego samego powodu co po stronie planu
    (`budzet.bez_podatkow`): daniny wchodza na os przez `podatki.do_zaplaty`,
    a przychod JDG przez godziny i stawke. Wpuszczone tedy weszlyby DRUGI RAZ.
    To jest ta sama pulapka, przed ktora broni D-20 — tylko po stronie wpisow.

    ZWRACA PUSTY SLOWNIK DLA PUSTEGO WEJSCIA i to jest stan poprawny:
    „nie zapisano niczego" znaczy, ze przeszlosc jest pusta, a nie ze mamy
    wrocic do planu. Fallback na plan bylby cichym powrotem do zachowania
    sprzed D-20.
    """
    wynik: dict[tuple[int, int], list[_Wejscie]] = {}
    if wpisy is None or getattr(wpisy, "empty", False):
        return {}
    for _, w in wpisy.iterrows():
        kategoria = str(w["kategoria"])
        if kategoria in (budzet.KATEGORIA_PODATKI, budzet.KATEGORIA_PRZYCHOD_JDG):
            continue
        dzien_w = date.fromisoformat(str(w["data"]))
        kwota = stawki.do_groszy(Decimal(str(w["kwota"])))
        wynik.setdefault((dzien_w.year, dzien_w.month), []).append(_Wejscie(
            dzien=dzien_w,
            nazwa=str(w["szczegoly"] or kategoria),
            kwota=kwota * budzet.znak(str(w["typ"])),
            rodzaj=RODZAJ_WPIS,
            rodzaj_typ=str(w["typ"]),
            kategoria=kategoria))
    return {k: tuple(v) for k, v in wynik.items()}


def zbuduj(*, plan, kotwica: Kotwica | None, wolumen: Wolumen | None,
           forma: magazyn.FormaRoku, zaleglosci, przychod_narastajaco: Decimal,
           dzis: date, horyzont_miesiecy: int = HORYZONT_DOMYSLNY,
           dochod_narastajaco: Decimal = Decimal("0"),
           zaliczki_naliczone: Decimal = Decimal("0"),
           zobowiazania=None, wpisy=None) -> Prognoza:
    """Saldo dzienne w dwoch liniach przez `horyzont_miesiecy`. BEZ BAZY.

    Trzy argumenty poza litera planu wykonawczego, wszystkie z wartoscia
    domyslna zachowujaca jego sygnature:

    * `dochod_narastajaco` i `zaliczki_naliczone` — SKALA liczy zaliczke
      narastajaco, wiec bez stanu roku od jego poczatku pierwsza prognozowana
      zaliczka startowala by od zera i zaniżala PIT. Zaniżenie idzie
      w kierunku, ktory poprawia obraz — czyli w najgorszym mozliwym.
    * `zobowiazania` — wynik ma niesc ich pelna liste (`zobowiazania_spoza_
      planu`), a nie da sie jej zwrocic, nie dostawszy jej.
    * `wpisy` (D-20, Z7b) — RZECZYWISTE wpisy budzetowe. Bez nich os biegla
      w calosci z planu, wiec wpisanie wydatku nie zmienialo na Plynnosci
      NICZEGO, a kto wydal ponad plan, widzial sytuacje lepsza, niz jest.
      Wartosc domyslna `None` znaczy „nie zapisano zadnego wpisu", a nie
      „nie stosuj reguly": plan i tak opisuje wylacznie dni przyszle.

    CO PRZEZ TE ZMIANE PRZESTAJE DZIALAC, nazwane wprost: **zgodnosc liczb
    prognozy z kazdym zrzutem sprzed D-20**. Pozycja planu na dzien miniony
    nie obciaza juz osi — przeszlosc opisuja wpisy, nie zamiary. Skutek
    zamierzony (plan implementacji, krok 1.2).
    """
    zastrzezenia: list[Zastrzezenie] = []

    # --- KROK 0: „nie wiem" zamiast zera --------------------------------
    if kotwica is None:
        zastrzezenia.append(Zastrzezenie(
            KOD_BRAK_KOTWICY,
            "Nie policzę prognozy: nie wiem, ile masz na koncie. Saldo "
            "z budżetu to suma wpisów, a nie pieniądze — prognoza zbudowana "
            "na nim startowałaby z punktu, który nie istnieje. Wpisz stan "
            "konta i datę odczytu."))
    if wolumen is None or wolumen.ostrozny is None:
        zastrzezenia.append(Zastrzezenie(
            KOD_BRAK_WOLUMENU,
            "Nie policzę prognozy: nie wiem, ile godzin uznajesz za pewne. "
            "Sama linia realna dałaby zielony obraz z wyłączonym mechanizmem "
            "ostrzegania, bo ostrzeżenie zapala się na linii ostrożnej."))
    if zastrzezenia:
        return Prognoza(stan=STAN_NIE_WIEM, dni=None,
                        zastrzezenia=tuple(zastrzezenia),
                        horyzont_miesiecy=horyzont_miesiecy)

    godziny_ostrozne = Decimal(wolumen.ostrozny)
    if wolumen.realny is None:
        godziny_realne = godziny_ostrozne
        zastrzezenia.append(Zastrzezenie(
            KOD_BRAK_WOLUMENU_REALNEGO,
            "Nie podałeś wolumenu realnego — obie linie liczę wolumenem "
            "ostrożnym. Wykres pokaże jedną linię zamiast dwóch."))
    else:
        godziny_realne = Decimal(wolumen.realny)

    # --- KROK 1: os dzienna, NIGDY przed kotwica ------------------------
    miesiace = _miesiace_osi(kotwica.data, horyzont_miesiecy)
    koniec = _ostatni_dzien(*miesiace[-1])

    daniny_policzone = forma.forma in magazyn.FORMY_ZAPISYWALNE
    if not daniny_policzone:
        zastrzezenia.append(Zastrzezenie(
            KOD_BRAK_FORMY,
            "Forma opodatkowania na ten rok nie jest wskazana, więc linie "
            "biegną BEZ podatków i składek. To znaczy, że są zawyżone — "
            "wskaż formę w Ustawieniach, a policzę daniny."))

    zdarzenia: dict[date, list[Zdarzenie]] = {}

    def dodaj(dzien: date, zdarzenie: Zdarzenie) -> None:
        if dzien < kotwica.data or dzien > koniec:
            return
        zdarzenia.setdefault(dzien, []).append(zdarzenie)

    # --- KROK 2: kalendarz planu, DOKLADNIE horyzont wywolan ------------
    bez_domniemania = 0
    domniemane = 0
    miesiecy_bez_planu = 0
    przychody_planu: dict[tuple[int, int], Decimal] = {}

    wpisy_wg_miesiaca = _wpisy_wg_miesiaca(wpisy)

    for rok, miesiac in miesiace:
        wiersze = budzet.plan_na_miesiac(plan, rok, miesiac)
        # Podatki liczy silnik, przychod JDG liczą godziny — obie kategorie
        # wypadają z planu, inaczej wchodzą do salda drugi raz.
        wiersze = budzet.bez_podatkow(wiersze)
        wejscia_planu: list[_Wejscie] = []
        suma_przychodow = Decimal("0.00")
        if wiersze.empty:
            miesiecy_bez_planu += 1
        else:
            for _, w in wiersze.iterrows():
                if w["kategoria"] == budzet.KATEGORIA_PRZYCHOD_JDG:
                    continue
                kwota = stawki.do_groszy(Decimal(str(w["kwota_planowana"])))
                ze_znakiem = kwota * budzet.znak(w["typ"])
                dzien_p, domniemany = _dzien_pozycji(rok, miesiac, w)
                if w["typ"] == budzet.TYP_PRZYCHODY:
                    suma_przychodow += kwota
                wejscia_planu.append(_Wejscie(
                    dzien=dzien_p, nazwa=str(w["opis"] or w["kategoria"]),
                    kwota=ze_znakiem, rodzaj=RODZAJ_PLAN,
                    rodzaj_typ=str(w["typ"]), kategoria=str(w["kategoria"]),
                    domniemany=domniemany))
        przychody_planu[(rok, miesiac)] = suma_przychodow

        # D-20 + D-61 — JEDEN NOSNIK. Tu tylko wolanie i wstawienie na os.
        for pozycja in podziel_os(pozycje_planu=wejscia_planu,
                                  wpisy=wpisy_wg_miesiaca.get((rok, miesiac), ()),
                                  dzis=dzis):
            if pozycja.rodzaj == RODZAJ_PLAN:
                if pozycja.domniemany:
                    domniemane += 1
                else:
                    bez_domniemania += 1
            dodaj(pozycja.dzien, Zdarzenie(
                nazwa=pozycja.nazwa, rodzaj=pozycja.rodzaj,
                kwota_ostrozna=pozycja.kwota, kwota_realna=pozycja.kwota,
                dzien_domniemany=pozycja.domniemany))

    if domniemane:
        zastrzezenia.append(Zastrzezenie(
            KOD_DZIEN_DOMNIEMANY,
            f"{domniemane} pozycji planu nie ma dnia płatności — założyłem "
            "najgorszy: wydatki i oszczędności pierwszego dnia miesiąca, "
            "przychody ostatniego. Wpisz dni, a prognoza się wypłaszczy.",
            liczba=domniemane))
    if miesiecy_bez_planu:
        zastrzezenia.append(Zastrzezenie(
            KOD_MIESIACE_BEZ_PLANU,
            f"{miesiecy_bez_planu} z {horyzont_miesiecy} miesięcy horyzontu "
            "nie ma ani jednej pozycji planu — tam linie pokazują sam "
            "przychód i daniny.",
            liczba=miesiecy_bez_planu))

    # --- KROKI 3-6: przychod linii, narastajaco, daniny, terminy --------
    rok_bazowy = kotwica.data.year
    narastajaco = {
        "ostrozna": dict(przychod=Decimal(przychod_narastajaco),
                         dochod=Decimal(dochod_narastajaco),
                         zaliczki=Decimal(zaliczki_naliczone)),
        "realna": dict(przychod=Decimal(przychod_narastajaco),
                       dochod=Decimal(dochod_narastajaco),
                       zaliczki=Decimal(zaliczki_naliczone)),
    }
    if forma.forma == magazyn.FORMA_SKALA and not dochod_narastajaco \
            and not zaliczki_naliczone:
        zastrzezenia.append(Zastrzezenie(
            KOD_NARASTAJACO_OD_ZERA,
            "Zaliczkę na skali liczę od zera narastająco — nie dostałem "
            "dochodu ani zaliczek z tego roku sprzed prognozy. Przy dochodzie "
            "bliskim progu 120 000 zł kwota może być zaniżona."))

    godziny = {"ostrozna": godziny_ostrozne, "realna": godziny_realne}
    # (data, nazwa) -> [kwota_ostrozna, kwota_realna]
    daniny: dict[tuple[date, str], list[Decimal]] = {}

    for rok, miesiac in miesiace:
        # Reset narastajaco na przelomie roku — kazde szesc miesiecy przez
        # niego przechodzi, wiec regula jest cwiczona zawsze, nie czasem.
        if rok != rok_bazowy:
            for linia in narastajaco.values():
                if linia.get("_rok_zresetowany") != rok:
                    linia["przychod"] = Decimal("0")
                    linia["dochod"] = Decimal("0")
                    linia["zaliczki"] = Decimal("0")
                    linia["_rok_zresetowany"] = rok

        # Przychod JDG wchodzi na konto OSTATNIEGO dnia miesiaca — ta sama
        # regula ostroznosci co dla pozycji planu bez dnia. Przychody planu
        # spoza kategorii JDG maja wlasne dni i weszly wyzej.
        #
        # STOI PRZED bramka `daniny_policzone` SWIADOMIE. Bez formy linia ma
        # biec BEZ PODATKOW (specyfikacja §5.5) — czyli wyzej, nie plasko.
        # Linia plaska na kotwicy czyta sie jako „nic nie wplynie" i produkuje
        # falszywy alarm dokladnie tam, gdzie brakuje jednej nastawy.
        dodaj(_ostatni_dzien(rok, miesiac), Zdarzenie(
            nazwa="Przychód JDG", rodzaj=RODZAJ_PRZYCHOD_JDG,
            kwota_ostrozna=stawki.do_groszy(
                godziny_ostrozne * Decimal(wolumen.stawka)),
            kwota_realna=stawki.do_groszy(
                godziny_realne * Decimal(wolumen.stawka))))

        if not daniny_policzone:
            continue

        for nazwa_linii, ile_godzin in godziny.items():
            netto = stawki.do_groszy(ile_godzin * Decimal(wolumen.stawka))
            stan = narastajaco[nazwa_linii]
            wyliczenie = podatki.policz(
                forma.forma,
                **_argumenty_daniny(forma, netto=netto,
                                    przychod=stan["przychod"],
                                    dochod=stan["dochod"],
                                    zaliczki=stan["zaliczki"]))
            stan["przychod"] += netto
            if forma.forma == magazyn.FORMA_SKALA:
                stan["dochod"] = wyliczenie.dochod_narastajaco
                # PRZED zaokragleniem — tak kumuluje `podatki.stan_roku_skali`.
                # Kumulowanie zaokraglonych daloby drugi nosnik tej reguly.
                stan["zaliczki"] += wyliczenie.zaliczka_przed_zaokragleniem

            kwoty = _kwoty_danin(wyliczenie, _nazwa_podatku(forma))
            okres = date(rok, miesiac, 1)
            for termin in terminy.TERMINY:
                if termin.roczny or not terminy.dotyczy_formy(termin, forma.forma):
                    continue
                kwota = kwoty.get(termin.nazwa)
                if kwota is None or kwota <= 0:
                    continue
                platnosc = terminy._data_platnosci(termin, okres)
                klucz = (platnosc, termin.nazwa)
                pozycja = daniny.setdefault(
                    klucz, [Decimal("0.00"), Decimal("0.00")])
                pozycja[0 if nazwa_linii == "ostrozna" else 1] -= kwota


    # --- KROK 7: zaleglosc na dzis — i NIE dwa razy ---------------------
    # Zaleglosc pochodzi z REALNYCH faktur (`podatki.do_zaplaty` rozbija
    # saldo rezerwy), prognoza z zalozenia. Gdy obie trafiaja w ten sam
    # termin i te sama danine, wygrywa zaleglosc — a danina prognozy znika,
    # zamiast zejsc z konta drugi raz.
    for pozycja in (zaleglosci or []):
        klucz = (pozycja.termin, pozycja.nazwa)
        daniny.pop(klucz, None)
        kwota = -stawki.do_groszy(Decimal(pozycja.kwota))
        dodaj(pozycja.termin, Zdarzenie(
            nazwa=pozycja.nazwa, rodzaj=RODZAJ_ZALEGLOSC,
            kwota_ostrozna=kwota, kwota_realna=kwota))

    for (platnosc, nazwa), (ostrozna, realna) in daniny.items():
        dodaj(platnosc, Zdarzenie(nazwa=nazwa, rodzaj=RODZAJ_DANINA,
                                  kwota_ostrozna=ostrozna,
                                  kwota_realna=realna))

    # --- KROK 8: kumulacja, pierwszy dzien ujemny, minimum --------------
    saldo_o = Decimal(kotwica.kwota)
    saldo_r = Decimal(kotwica.kwota)
    dni: list[Dzien] = []
    dzien = kotwica.data
    pierwszy_ujemny = None
    minimum = None

    while dzien <= koniec:
        tego_dnia = tuple(sorted(zdarzenia.get(dzien, []),
                                 key=lambda z: (z.rodzaj, z.nazwa)))
        for z in tego_dnia:
            saldo_o += z.kwota_ostrozna
            saldo_r += z.kwota_realna
        saldo_o = stawki.do_groszy(saldo_o)
        saldo_r = stawki.do_groszy(saldo_r)
        dni.append(Dzien(data=dzien, saldo_ostrozne=saldo_o,
                         saldo_realne=saldo_r, zdarzenia=tego_dnia))
        # Ostrzezenie zapala sie na linii OSTROZNEJ (R6). Dzien domykajacy
        # sie na zerze to „nie ponizej zera" — kolejnosci zdarzen w obrebie
        # dnia nie gwarantuje nawet bank.
        if saldo_o < 0 and pierwszy_ujemny is None:
            pierwszy_ujemny = dzien
        minimum = saldo_o if minimum is None else min(minimum, saldo_o)
        dzien += timedelta(days=1)

    # --- swiezosc kotwicy: ZDARZENIE, nie kalendarz (R18) ---------------
    stan = STAN_POLICZONA
    rozliczajace = {RODZAJ_DANINA, RODZAJ_ZALEGLOSC, RODZAJ_PLAN}
    minelo = [d for d, lista in zdarzenia.items()
              if kotwica.data < d <= dzis
              and any(z.rodzaj in rozliczajace for z in lista)]
    dni_od_odczytu = (dzis - kotwica.data).days
    if minelo or dni_od_odczytu > SUFIT_SWIEZOSCI_DNI:
        stan = STAN_NIEAKTUALNA
        powod = (f"od jego daty minęły terminy: {len(minelo)}" if minelo
                 else f"minęło {dni_od_odczytu} dni")
        zastrzezenia.append(Zastrzezenie(
            KOD_KOTWICA_NIEAKTUALNA,
            f"Stan konta jest z {kotwica.data.isoformat()} i {powod} — "
            "prognoza biegnie od liczby, która mogła się już zmienić. "
            "Odśwież stan konta.",
            liczba=len(minelo)))

    # Ostatni miesiac osi nie ma na niej WLASNEJ daniny (placi sie w miesiacu
    # nastepnym, poza horyzontem), wiec jego ogon jest z natury zawyzony.
    pelny = _ostatni_dzien(*miesiace[-2]) if len(miesiace) >= 2 else koniec

    lista_zobowiazan = ()
    if zobowiazania is not None and not getattr(zobowiazania, "empty", True):
        lista_zobowiazan = tuple(
            (str(w["nazwa"]), Decimal(str(w["rata_minimalna"])))
            for _, w in zobowiazania.iterrows())

    return Prognoza(
        stan=stan, dni=tuple(dni), zastrzezenia=tuple(zastrzezenia),
        daniny_policzone=daniny_policzone,
        dzien_domniemany=domniemane > 0,
        ostatni_dzien_pelny=pelny,
        pierwszy_dzien_ujemny=pierwszy_ujemny,
        minimum=minimum,
        brakuje=(-minimum if minimum is not None and minimum < 0 else None),
        zobowiazania_spoza_planu=lista_zobowiazan,
        horyzont_miesiecy=horyzont_miesiecy)


# --- warstwa zbierajaca: czyta baze, wola `zbuduj`, ZERO rachunku (Z63) ---

#: Wartosci STARTOWE nastaw prognozy (R17, decyzja Darka 2026-08-27).
#: Startowe, nie zaszyte: Darek zmienia je w Ustawieniach bez ruszania kodu.
#: 120 h uznane za pewne, 160 h realne, 70 zl netto za godzine (§3 umowy B2B).
WOLUMEN_OSTROZNY_STARTOWY = Decimal("120")
WOLUMEN_REALNY_STARTOWY = Decimal("160")
STAWKA_GODZINOWA_STARTOWA = Decimal("70")


def ostatnia_kotwica(polaczenie) -> Kotwica | None:
    """Kotwica OBOWIAZUJACA — jeden nosnik odpowiedzi „ktora to".

    `magazyn.wczytaj_kotwice` zwraca cala historie od najnowszej; ta funkcja
    nazywa regule „pierwszy wiersz obowiazuje", zeby ekran, punkt koncowy API
    i straznik w tle nie odpowiadaly na to pytanie kazdy po swojemu.

    Brak odczytu daje `None`, nie zero: zero to najlepszy mozliwy stan konta
    pokazany wtedy, gdy nie wiadomo nic (R11, regula D11).
    """
    # Regula „obowiazuje NAJNOWSZY odczyt" ma jeden nosnik i jest nim
    # `magazyn.ostatni_odczyt_salda` — ta sama funkcja, ktora zasila wartosc
    # rachunku rozliczeniowego w majatku (D10). Liczona tu po swojemu
    # znaczylaby dwie rozne rzeczy przy pierwszej zmianie sortowania.
    odczyt = magazyn.ostatni_odczyt_salda(polaczenie)
    if odczyt is None:
        return None
    return Kotwica(data=odczyt.data, kwota=odczyt.kwota)


def wolumen_z_bazy(polaczenie) -> Wolumen:
    """Nastawy prognozy z bazy albo wartosci startowe. Puste = WYCZYSZCZONE."""
    return Wolumen(
        ostrozny=magazyn.odczytaj_liczbe_ustawienia(
            polaczenie, magazyn.KLUCZ_WOLUMEN_OSTROZNY,
            WOLUMEN_OSTROZNY_STARTOWY),
        realny=magazyn.odczytaj_liczbe_ustawienia(
            polaczenie, magazyn.KLUCZ_WOLUMEN_REALNY,
            WOLUMEN_REALNY_STARTOWY),
        stawka=magazyn.odczytaj_liczbe_ustawienia(
            polaczenie, magazyn.KLUCZ_STAWKA_GODZINOWA,
            STAWKA_GODZINOWA_STARTOWA) or STAWKA_GODZINOWA_STARTOWA)


def prognozuj(polaczenie, *, dzis: date | None = None,
              horyzont_miesiecy: int = HORYZONT_DOMYSLNY) -> Prognoza:
    """Cienki zbieracz: czyta baze, wola `zbuduj`, ZERO rachunku.

    Ten sam rozdzial co przy `podatki.rezerwa_z_bazy` (Z55) i z tego samego
    powodu: bez niego kazdy konsument — ekran, punkt koncowy API, straznik
    w tle — powtarzalby ten sam zestaw odczytow, a kazde powtorzenie to
    okazja, zeby jeden z nich podal silnikowi co innego. Zmierzone: ekran
    pokazywal -6 098,11 zl, a doradca +8 007,89 zl o tej samej rzeczy
    w tej samej chwili (audyt 2026-08-26).
    """
    dzis = dzis or date.today()
    forma = magazyn.forma_na_rok(polaczenie, dzis.year)
    wpisy = magazyn.wczytaj_wpisy(polaczenie)
    faktury = magazyn.wczytaj_faktury(polaczenie)

    rezerwa = podatki.rezerwa_z_bazy(polaczenie, wpisy=wpisy, dzis=dzis)
    zaleglosci = podatki.do_zaplaty(rezerwa, dzis, wpisy)

    # Stan roku dla skali WOLANY, nie liczony — jeden nosnik przebiegu
    # narastajaco siedzi w `podatki.stan_roku_skali` (Z63).
    stan_roku = podatki.stan_roku_skali(faktury, dzis.year)

    return zbuduj(
        plan=magazyn.wczytaj_plan(polaczenie),
        kotwica=ostatnia_kotwica(polaczenie),
        wolumen=wolumen_z_bazy(polaczenie),
        forma=forma,
        zaleglosci=zaleglosci,
        przychod_narastajaco=magazyn.przychod_narastajaco(polaczenie, dzis.year),
        dzis=dzis,
        horyzont_miesiecy=horyzont_miesiecy,
        dochod_narastajaco=stan_roku.dochod_narastajaco,
        zaliczki_naliczone=stan_roku.zaliczki_przed_zaokragleniem,
        zobowiazania=magazyn.wczytaj_zobowiazania(polaczenie),
        # D-20: os dzieli sie na dniu dzisiejszym. Bez tego argumentu
        # `zbuduj` widzi wylacznie plan, a wpis uzytkownika nie rusza
        # Plynnosci — cala sciezka „wpisz wydatek i zobacz skutek" byla
        # wtedy teatrem (zmierzone w Z7: 8 335,87 -> 8 335,87 -> 8 335,87).
        wpisy=wpisy)

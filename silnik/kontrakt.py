# -*- coding: utf-8 -*-
"""KSZTALT DANYCH PO STRONIE PYTHONA — odpowiednik `interfejs/lib/kontrakt.ts`.

KIERUNEK ZGODNOSCI JEST JEDNOSTRONNY. Wzorcem jest `kontrakt.ts`; ten plik sie
do niego DOPASOWUJE. Powod: tamte typy powstaly Z EKRANU, a oba ekrany sa juz
zbudowane wobec nich i przechodza bramke odwzorowania. Gdy cos nie pasuje,
zmienia sie Python.

SWIADOMY DRUGI NOSNIK — z tym plikiem wiaze sie dlug, nazwany wprost.
Ten sam ksztalt zyje w dwoch miejscach, bo granica HTTP dzieli dwa jezyki.
`CLAUDE.md` §3.2 dopuszcza to WYLACZNIE ze straznikiem i z jawnym progiem:
  * straznik: `testy/test_kontrakt_dwa_nosniki.py` — czyta OBA pliki, porownuje
    nazwy pol i pilnuje, ze kwoty sa napisami po obu stronach;
  * PROG KONSOLIDACJI: **przy pierwszym dopisaniu pola** do ktoregokolwiek
    ksztaltu generujemy `kontrakt.ts` z `kontrakt.py` i drugi nosnik znika.
Odlozenie bez straznika i progu byloby dlugiem ukrytym, nie decyzja.

NAZWY POL SA IDENTYCZNE PO OBU STRONACH — `saldoPoDniu`, nie `saldo_po_dniu`.
To nie jest niedbalstwo o konwencje. Te nazwy sa NAZWAMI POL W JSON: przechodza
granice HTTP i musza sie zgadzac co do znaku. Warstwa tlumaczaca snake_case na
camelCase bylaby TRZECIM nosnikiem tej samej reguly — i takim, ktory rozjezdza
sie cicho. Nazwy pozostaja polskie i bez znakow diakrytycznych (`CLAUDE.md` §4).

KAZDA KWOTA JEST NAPISEM. `Kwota = str`, nigdy `float`, nigdy `Decimal` na
drucie. Poprzednia aplikacja zamieniala `Decimal` na `float` w warstwie
sieciowej, gubila grosze i ZWRACALA 200 — awaria, ktora meldowala sukces.
Zamiane `Decimal` -> napis robi JEDEN nosnik: `api/kwoty.py`.

CZEGO TU NIE MA I DLACZEGO. Zadnego rachunku. Ten plik opisuje KSZTALT,
nie regule liczenia — z jednym wyjatkiem opisanym przy `zbij_saldo_raz_na_dzien`,
gdzie regula dotyczy tego, co widac na ekranie, a nie tego, ile czegos jest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# --- typy proste ----------------------------------------------------------

#: "274.06" — kropka dziesietna, bez separatorow tysiecy, bez waluty.
#: Formatowanie do postaci widocznej na ekranie NIE nalezy do kontraktu.
Kwota = str

#: "2026-10-06" — ISO 8601, zawsze pelna data.
Data = str

TypWpisu = Literal["Przychody", "Wydatki", "Oszczędności"]

#: Trzy pozycje przelacznika typu. Wolane z jednego miejsca po obu stronach —
#: czwarty typ pojawilby sie TU, a nie w ukladzie ekranu.
TYPY: tuple[TypWpisu, ...] = ("Przychody", "Wydatki", "Oszczędności")


class BladKontraktu(ValueError):
    """Ksztalt danych lamie regule kontraktu.

    Osobny typ, a nie golemu `ValueError`, bo warstwa sieciowa ma odrozniac
    „uzytkownik podal cos nie tak" od „nasz kod zlozyl zla odpowiedz".
    """


# --- ekran Ksiegowanie ----------------------------------------------------

@dataclass(frozen=True, slots=True)
class Kategoria:
    nazwa: str
    aktywna: bool
    systemowa: bool


@dataclass(frozen=True, slots=True)
class WpisDoZapisu:
    """Wpis idacy do zapisu.

    REGULA O KONSEKWENCJI ZEWNETRZNEJ: `kwota` jest ZAWSZE DODATNIA.
    Kierunek niesie `typ`, nie znak liczby. Ekran Ksiegowanie mowi o tym
    uzytkownikowi wprost („minus jest w typie wpisu") i nie przyjmuje znaku,
    wiec kwota ujemna, ktora tu dotrze, jest bledem NASZEGO kodu — najczesciej
    pomyleniem wydatku ze zwrotem. Zapisana po cichu odjelaby sie dwa razy.

    Sprawdzenie stoi TUTAJ, w kontrakcie, a nie w trasie: trasa jest jedna
    z wielu, a kontrakt jest jeden. Straznik:
    `testy/test_kontrakt_dwa_nosniki.py::test_kwota_do_zapisu_NIE_PRZYJMUJE_znaku`.
    """

    data: Data
    typ: TypWpisu
    kategoria: str
    kwota: Kwota
    szczegoly: str

    def __post_init__(self) -> None:
        surowa = str(self.kwota).strip()
        if surowa.startswith("-") or surowa.startswith("−"):
            raise BladKontraktu(
                f"kwota wpisu niesie znak minus ({self.kwota!r}). Kierunek "
                f"niesie `typ` ({self.typ!r}), nie znak — inaczej wydatek "
                f"odejmie sie dwa razy.")
        if surowa.startswith("+"):
            raise BladKontraktu(
                f"kwota wpisu niesie znak plus ({self.kwota!r}). Kontrakt "
                f"przewiduje sama liczbe; znak nalezy do warstwy widoku.")


@dataclass(frozen=True, slots=True)
class WierszSkutku:
    """Jeden wiersz karty „Co ruszy ten wpis".

    `po is None` znaczy „ta liczba sie NIE zmienia" — i wtedy `wyjasnienie`
    mowi dlaczego. To jest czwarty wiersz karty: mowi, co sie NIE ruszylo.
    Bez niego uzytkownik nie wie, czy liczba stoi, bo wpis jej nie dotyczy,
    czy dlatego, ze cos nie zadzialalo.
    """

    etykieta: str
    przed: str
    po: str | None
    wyjasnienie: str | None = None


@dataclass(frozen=True, slots=True)
class PodgladSkutku:
    kwota: Kwota
    # BEZ WARTOSCI DOMYSLNEJ — swiadomie. W `kontrakt.ts` to pole jest
    # WYMAGANE, a wartosc domyslna po stronie Pythona uczynilaby je opcjonalnym
    # tylko tutaj. Straznik porownuje takze opcjonalnosc, nie same nazwy.
    wiersze: tuple[WierszSkutku, ...]


@dataclass(frozen=True, slots=True)
class OstatniWpis:
    id: int
    data: Data
    typ: TypWpisu
    kategoria: str
    kwota: Kwota
    szczegoly: str


@dataclass(frozen=True, slots=True)
class DaneKsiegowania:
    dzisiaj: Data
    typDomyslny: TypWpisu
    kategorie: tuple[Kategoria, ...]
    uzasadnienieKolejnosci: str
    ostatnieWpisy: tuple[OstatniWpis, ...]
    liczbaWpisowWMiesiacu: int
    nazwaMiesiaca: str
    podglad: PodgladSkutku
    #: Stopka straznika — TEN SAM fakt, co w `DanePlynnosci` (Z7b).
    #: Do Z7b tylko Plynnosc niosla to pole, wiec ekran Ksiegowanie mowil
    #: „nie wiem" o czyms, co aplikacja wiedziala. Dwa ekrany dawaly dwie
    #: odpowiedzi na jedno pytanie „czy to, co widze, jest aktualne".
    #: `None` = straznik nigdy nie dzialal — i tylko to.
    ostatnieSprawdzenie: str | None


# --- ekran Plynnosc -------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PozycjaKsiegi:
    """Wiersz ksiegi płynności.

    `kwota is None` = wiersz otwarcia; na ekranie „—", nigdy zero.
    `saldoPoDniu` — patrz `zbij_saldo_raz_na_dzien`.
    """

    dzien: Data
    pozycja: str
    kwota: Kwota | None
    saldoPoDniu: Kwota | None
    dopisek: str | None = None


@dataclass(frozen=True, slots=True)
class PunktWykresu:
    dzien: Data
    saldo: Kwota


@dataclass(frozen=True, slots=True)
class DanePlynnosci:
    odczyt: Data
    okresNapis: str
    ksiega: tuple[PozycjaKsiegi, ...]
    wykres: tuple[PunktWykresu, ...]
    dzienPodKreska: Data | None
    saldoMinimalne: Kwota | None
    dataSaldaMinimalnego: Data | None
    zdanieWerdyktu: str
    horyzontDni: int
    #: `None` = NIE POLICZYLEM. Przy odmowie prognozy wychodzilo stad zero,
    #: ktore czyta sie jako „policzylem i nic Cie nie czeka" — najlepsza
    #: mozliwa odpowiedz podana wtedy, gdy nie wiadomo nic. To ta sama klasa
    #: wady co forma opodatkowania zgadnieta wartoscia domyslna (Z7b).
    liczbaPozycjiCoMnieCzeka: int | None
    koniecOknaCoMnieCzeka: Data
    ostatnieSprawdzenie: str | None


# --- ekran Budzet (W9b) ---------------------------------------------------
#
# GRANICA MIEDZY SILNIKIEM A WIDOKIEM, NAZWANA RAZ DLA CALEGO EKRANU:
# silnik oddaje LICZBY i NAZWY MIESIECY, widok sklada z nich PROZE. Ta sama
# granica biegnie juz na Ksiegowaniu (`DaneKsiegowania.nazwaMiesiaca` +
# `interfejs/lib/napisy.ts`) i na Plynnosci — z jednym wyjatkiem po obu
# stronach: zdanie, ktore niesie liczbe ALBO odmowe silnika, sklada silnik
# (`zdanieWerdyktu`, `KafelekBudzetu.wyjasnienie`, `CelNaEkranie.tempoNapis`).
# Zapis rzymski dnia („20 X") sklada `interfejs/lib/kwota.ts` i dostaje dzien
# POLEM (`PozycjaPlanu.dzien`) — dlatego zaden napis stad go nie zawiera.


@dataclass(frozen=True, slots=True)
class KafelekBudzetu:
    """Jeden z trzech kafelkow nad bilansem planu.

    `klucz` istnieje, zeby widok NIE SIEGAL PO INDEKS. Kolejnosc listy jest
    wlasnoscia silnika, a `kafelki[1]` w komponencie bylaby zalozeniem o tej
    kolejnosci — cichym i zlym dokladnie wtedy, gdy dolozymy czwarty kafelek.

    `kwota is None` znaczy NIE POLICZYLEM i wtedy `wyjasnienie` mowi, czego
    brakuje (§3.7). Rezerwa na podatki bez wskazanej formy opodatkowania jest
    dokladnie tym przypadkiem: silnik ODMAWIA liczenia, bo zgadniecie formy
    to zmierzona szkoda, a nie niedokladnosc raportu. Zero w tym miejscu
    czytaloby sie jako „nic nie jestes winien urzedowi".
    """

    klucz: str
    tytul: str
    kwota: Kwota | None
    dopisek: str
    wyjasnienie: str | None


@dataclass(frozen=True, slots=True)
class PozycjaWykonania:
    """Wiersz tabeli „Plan kontra wykonanie" — jeden na pare (typ, kategoria).

    NIE JEST TO POZYCJA PLANU i mylenie tych dwoch rzeczy jest tu glowna
    pulapka. Wpis budzetu nie wskazuje, ktora POZYCJE planu realizuje —
    niesie tylko typ i kategorie — wiec „wykonane" da sie policzyc wylacznie
    per kategoria. Kategoria z dwoma pozycjami planu (dwa kredyty, trzy
    rachunki za gaz) ma tu JEDEN wiersz o zsumowanym planie.

    `idPozycjiPlanu` jest `None`, gdy za wierszem stoi zero pozycji planu
    (kategoria tknieta wpisem, nieplanowana) ALBO wiecej niz jedna — bo wtedy
    „popraw te pozycje" nie ma jednej odpowiedzi. `liczbaPozycjiPlanu`
    rozroznia te dwa przypadki; sam `None` by ich nie rozroznil.

    `procent is None` znaczy „planu nie ma" (`budzet.Wykonanie.procent`).
    Zero klamaloby, ze wydatek zmiescil sie w budzecie.
    """

    typ: TypWpisu
    kategoria: str
    plan: Kwota
    wykonane: Kwota
    #: `wykonane - plan`, czyli kolumna „Odchylenie" z ramki. Ujemne = jeszcze
    #: nie wydane. To ta sama liczba co `budzet.Wykonanie.pozostalo` ze
    #: zmienionym znakiem — wolana, nie policzona drugi raz.
    odchylenie: Kwota
    procent: str | None
    #: Szerokosc paska postepu, punkty procentowe PRZYCIETE do 0–100. Pasek
    #: dluzszy niz jego tor nie istnieje wizualnie, wiec przekroczenie planu
    #: niesie `przekroczone`, a nie 340 na pasku.
    procentPaska: int | None
    przekroczone: bool
    idPozycjiPlanu: int | None
    liczbaPozycjiPlanu: int


@dataclass(frozen=True, slots=True)
class PozycjaPlanu:
    """Regula planu obowiazujaca w wybranym miesiacu — to, co edytuje panel.

    `id` jest tym, co jedzie do `PUT /api/plan/{id}` i
    `POST /api/plan/{id}/zakoncz`. `dzien` jedzie POLEM, bo zapis rzymski
    („20 X") sklada widok — silnik nie ma drugiego nosnika tej konwencji.

    `czeka` = dzien pozycji jeszcze nie minal w tym miesiacu. Regula liczona
    w silniku, bo decyduje o zdaniu „trzy pozycje czekaja na swoje dni",
    a to zdanie odpowiada uzytkownikowi na pytanie o pieniadze.
    """

    id: int
    typ: TypWpisu
    kategoria: str
    opis: str
    kwota: Kwota
    dzien: int | None
    coIleMiesiecy: int
    czeka: bool


@dataclass(frozen=True, slots=True)
class CelNaEkranie:
    """Jeden cel oszczednosciowy razem z postepem liczonym Z WPISOW.

    `uzbierane` nigdy nie jest liczba wpisana recznie (`budzet.PostepCelu`):
    pasek napedzany reczna liczba pokazuje to, co uzytkownik wpisal, a nie
    to, co ma — czyli dokladnie odwrotnie, niz obiecuje.

    `tempoNapis is None` znaczy „nie ma czego dogadniac albo nie ma juz
    czasu" — cel osiagniety lub po terminie. Napis „0,00 zl / mc" w tym
    miejscu bylby odpowiedzia na pytanie, ktorego nikt nie zadal.
    """

    id: int
    nazwa: str
    kategoria: str
    kwotaDocelowa: Kwota
    uzbierane: Kwota
    brakuje: Kwota
    procent: str
    procentPaska: int
    termin: Data
    tempoNapis: str | None
    osiagniety: bool
    poTerminie: bool


@dataclass(frozen=True, slots=True)
class DaneBudzetu:
    """Caly ekran Budzet w jednej odpowiedzi.

    W CALOSCI, nie w kawalkach — z tego samego powodu, dla ktorego zapis
    kotwicy oddaje cala Plynnosc: kazdy zapis na tym ekranie (nowa pozycja,
    zmiana kwoty, zakonczenie reguly, kopia z poprzedniego miesiaca, nowy
    cel) rusza NARAZ kafelki, bilans, tabele i licznik naglowka. Odpowiedz
    „zapisano" kazalaby przegladarce zlozyc te liczby po swojemu (drugi
    nosnik kazdej z nich) albo odpytac drugi raz (dwa rachunki dla jednej
    chwili).

    `liczbaPozycjiPlanu` LICZY TAKZE CELE — tak, jak liczy je naglowek ramki
    („4 pozycje planu" = trzy wydatki + jeden cel). Sama dlugosc
    `pozycjePlanu` dalaby trzy i etykieta opisywalaby inna liczbe niz ta,
    ktora widac pod spodem (§3.5).
    """

    dzisiaj: Data
    #: „2026-10" — miesiac, ktorego dotyczy caly ekran. Ten sam ksztalt
    #: przyjmuje `prezentacja.etykieta_okresu`, wiec format ma jeden nosnik.
    miesiac: str
    miesiacNapis: str                 # „październik 2026" — selektor
    nazwaMiesiaca: str                # „październiku" — miejscownik dla widoku
    liczbaPozycjiPlanu: int
    liczbaWpisow: int
    kafelki: tuple[KafelekBudzetu, ...]
    planPrzychodow: Kwota
    planWydatkow: Kwota
    planOszczednosci: Kwota
    #: Plan przychodow minus plan wydatkow minus plan oszczednosci. Rezerwa
    #: podatkowa NIE WCHODZI — stoi w kafelku, osobno, bo nie jest wydatkiem
    #: tego miesiaca, tylko saldem dlugu wobec urzedu.
    bilansPlanu: Kwota
    wykonaneWydatki: Kwota
    pozycjeWykonania: tuple[PozycjaWykonania, ...]
    pozycjePlanu: tuple[PozycjaPlanu, ...]
    cele: tuple[CelNaEkranie, ...]
    #: Wpisy TEGO miesiaca, od najnowszego — tabela „Historia". Ksztalt ten
    #: sam co „Ostatnie wpisy" na Ksiegowaniu, bo to ta sama rzecz.
    historia: tuple[OstatniWpis, ...]
    miesiacKopiujZ: str               # „2026-09"
    napisKopiujZ: str                 # „Skopiuj z września"
    ostatnieSprawdzenie: str | None


# --- jedyna regula w tym pliku -------------------------------------------

def zbij_saldo_raz_na_dzien(
        pozycje: "list[PozycjaKsiegi] | tuple[PozycjaKsiegi, ...]",
) -> tuple[PozycjaKsiegi, ...]:
    """Saldo pokazuje sie RAZ NA DZIEN — druga i dalsza pozycja tego samego
    dnia dostaje `saldoPoDniu = None`.

    DLACZEGO TO JEST WYMOG, A NIE UPROSZCZENIE. Silnik podaje saldo per
    pozycja, wiec dwie pozycje z jednego dnia dostaja TE SAMA wartosc.
    Powtorzona liczba w kolumnie „Saldo" wyglada jak blad — czytelnik widzi
    dwa razy to samo i szuka, gdzie zniknely pieniadze, zamiast czytac
    ksiege. `null` mowi „to jest ten sam dzien", a puste miejsce w kolumnie
    jest tansze poznawczo niz powtorzenie.

    JEDEN NOSNIK. Ta funkcja jest jedynym miejscem, w ktorym ta regula zyje.
    Widok jej nie powtarza — dostaje `null` i rysuje puste miejsce. Gdyby
    liczyl to u siebie, regula mialaby tyle nosnikow, ile ekranow niesie
    ksiege (dzis dwa: Plynnosc i Co mnie czeka).

    NIE MODYFIKUJE WEJSCIA — zwraca nowa krotke. Pozycje sa zamrozone.
    """
    widziane: set[str] = set()
    wynik: list[PozycjaKsiegi] = []
    for p in pozycje:
        pierwsza_tego_dnia = p.dzien not in widziane
        widziane.add(p.dzien)
        if pierwsza_tego_dnia:
            wynik.append(p)
            continue
        wynik.append(PozycjaKsiegi(
            dzien=p.dzien, pozycja=p.pozycja, kwota=p.kwota,
            saldoPoDniu=None, dopisek=p.dopisek))
    return tuple(wynik)


#: Wszystkie ksztalty kontraktu — JEDEN nosnik odpowiedzi „co porownuje
#: straznik". Bez tej listy straznik parametryzowalby sie tym, co akurat
#: znajdzie w module, i nowy ksztalt dolaczylby do porownania po cichu albo
#: nie dolaczyl wcale. Kolejnosc jak w `kontrakt.ts`.
KSZTALTY = (
    Kategoria, WpisDoZapisu, WierszSkutku, PodgladSkutku, OstatniWpis,
    DaneKsiegowania, PozycjaKsiegi, PunktWykresu, DanePlynnosci,
    KafelekBudzetu, PozycjaWykonania, PozycjaPlanu, CelNaEkranie, DaneBudzetu,
)

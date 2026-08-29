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
    liczbaPozycjiCoMnieCzeka: int
    koniecOknaCoMnieCzeka: Data
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
)

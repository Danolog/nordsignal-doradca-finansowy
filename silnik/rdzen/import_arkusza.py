"""Import wpisów, planu i słownika kategorii z arkusza `Budżet Osobisty`.

Arkusz jest **czytany, nigdy zapisywany**. openpyxl przy zapisie usuwa
formatowanie warunkowe, walidację danych i rozszerzenia, o czym uprzedza
trzema ostrzeżeniami przy otwarciu. Plik źródłowy zostaje nietknięty.

Pułapki układu, wszystkie zmierzone na prawdziwym pliku 2026-08-25:

* **Tabela zaczyna się w kolumnie C, nie A.** Kolumny A, B i J są puste.
* **`ws.max_row` kłamie.** Przy 204 wpisach pokazuje 338, bo wiersze poniżej
  danych mają wciąż żywe formuły w kolumnach H i I. Warunkiem stopu jest
  **typ komórki daty**, nie rozmiar arkusza.
* **Kolumn H i I nie wolno importować.** H (Saldo) to formuła tablicowa o tej
  samej wartości w całym bloku; I (Data Efektywna) przesuwa przychody z dnia
  ≥ 20 na następny miesiąc. Obie są wynikiem, nie danymi.
* **Kwoty są mieszane:** 58 wartości typu `int`, 146 typu `float`. Droga do
  `Decimal` prowadzi wyłącznie przez `str`, nigdy przez `float`.
* **Kategorie NIE leżą w arkuszu `Dane List Rozwijanych`** — wbrew nazwie są
  tam wyłącznie listy filtrów. Prawdziwym nośnikiem są **zakresy tabel**
  `Przychody`, `Wydatki`, `Oszczędności` w arkuszu `Planowanie Budżetu`.
  Poza tymi zakresami leżą sloty-zachęty („Wprowadź Kategorię…") i siedem
  powtórzeń „Inne", których wciągnięcie dałoby duplikaty.
* **`Inne` należy jednocześnie do Przychodów i Wydatków** — klucz kategorii
  to para (typ, nazwa).
"""

import datetime
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

from silnik.rdzen import budzet, magazyn, stawki

ARKUSZ_WPISOW = "Śledzenie Budżetu"
ARKUSZ_PLANU = "Planowanie Budżetu"

#: Nagłówek tabeli wpisów stoi w wierszu 11, dane zaczynają się w 12.
PIERWSZY_WIERSZ_DANYCH = 12

#: Numery kolumn (1 = A). Tabela jest wcięta o dwie kolumny.
KOL_DATA, KOL_TYP, KOL_KATEGORIA, KOL_KWOTA, KOL_SZCZEGOLY = 3, 4, 5, 6, 7

#: Kolumna z nazwami kategorii w arkuszu planu; miesiące zaczynają się od E.
KOL_KATEGORII_PLANU = 3
PIERWSZA_KOL_MIESIACA = 5


class BladImportu(Exception):
    """Arkusza nie da się przeczytać — z komunikatem po polsku."""


@dataclass(frozen=True)
class Wpis:
    data: datetime.date
    typ: str
    kategoria: str
    kwota: Decimal
    szczegoly: str = ""


@dataclass(frozen=True)
class RaportImportu:
    """Cztery liczby i zdanie — nigdy samo „gotowe".

    Import, który zapisał zero, ma to powiedzieć liczbą. Meldunek o powodzeniu
    bez liczby wygląda identycznie przy 204 wpisach i przy zerze.
    """

    przeczytane: int
    zapisane: int
    pominiete_jako_powtorzenia: int
    odrzucone: int
    powody: dict[str, int]
    kategorie_dodane: int
    pozycje_planu: int
    komunikat: str


def _otworz(sciezka: Path):
    try:
        return openpyxl.load_workbook(sciezka, data_only=True)
    except FileNotFoundError as e:
        raise BladImportu(
            f"Nie znalazłem arkusza pod ścieżką {sciezka}. Sprawdź, czy plik "
            "jest pobrany z iCloud, a nie tylko widoczny jako nazwa.") from e
    except Exception as e:
        raise BladImportu(f"Nie udało się otworzyć arkusza {sciezka}. "
                          f"Szczegół: {e}") from e


def _bez_znakow_diakrytycznych(napis: str) -> str:
    rozlozony = unicodedata.normalize("NFKD", str(napis))
    return "".join(z for z in rozlozony if not unicodedata.combining(z)).lower()


def _na_decimal(wartosc) -> Decimal | None:
    """Liczba z komórki na `Decimal` — wyłącznie przez tekst.

    `Decimal(13.99)` daje 13.990000000000000213..., bo `float` nie umie zapisać
    tej wartości dokładnie. `Decimal(str(13.99))` daje 13.99.

    Sprawdzenie typu odrzuca komórkę z **tekstem**: `Decimal("13.99")` jest
    poprawne, więc bez niego napis wszedłby jako kwota. Wyjątek niżej łapie
    tylko zapisy nie do sparsowania, na przykład z przecinkiem.

    Człon o `bool` jest **niepotwierdzony testem i takim pozostaje**: `bool`
    jest w Pythonie podklasą `int`, ale `Decimal(str(True))` i tak podnosi
    wyjątek, więc żadne wejście nie odróżnia kodu z tym członem od kodu bez
    niego. Zostaje jako zapis intencji, nie jako strażnik — zmierzone
    2026-08-25 przy mutacji M22.
    """
    if isinstance(wartosc, bool) or not isinstance(wartosc, (int, float)):
        return None
    try:
        # Zaokraglenie idzie przez `stawki.do_groszy` - jedyny nosnik konwencji
        # pienieznej w projekcie (ROUND_HALF_UP). Domyslne `quantize` zaokragla
        # BANKIERSKO: 2,665 daje 2,66 zamiast 2,67. W aplikacji podatkowej dwie
        # konwencje zaokraglania obok siebie to wada, nie szczegol.
        return stawki.do_groszy(Decimal(str(wartosc)))
    except (InvalidOperation, ValueError):
        return None


def wczytaj_wpisy_z_arkusza(sciezka: Path) -> tuple[list[Wpis], dict[str, int]]:
    """Wpisy z arkusza `Śledzenie Budżetu` plus powody odrzuceń.

    Czytanie **zatrzymuje się** na pierwszym wierszu, w którym kolumna daty nie
    zawiera daty. Pomijanie takich wierszy zamiast zatrzymania wciągnęłoby
    wszystko, co ktokolwiek zapisał poniżej tabeli.
    """
    skoroszyt = _otworz(sciezka)
    if ARKUSZ_WPISOW not in skoroszyt.sheetnames:
        raise BladImportu(
            f"W skoroszycie nie ma arkusza {ARKUSZ_WPISOW!r}. Znalazłem: "
            + ", ".join(skoroszyt.sheetnames) + ".")
    ws = skoroszyt[ARKUSZ_WPISOW]

    wpisy: list[Wpis] = []
    powody: dict[str, int] = {}
    wiersz = PIERWSZY_WIERSZ_DANYCH
    while True:
        komorka_daty = ws.cell(wiersz, KOL_DATA).value
        if not isinstance(komorka_daty, datetime.datetime):
            break

        typ = ws.cell(wiersz, KOL_TYP).value
        kategoria = ws.cell(wiersz, KOL_KATEGORIA).value
        kwota = _na_decimal(ws.cell(wiersz, KOL_KWOTA).value)
        szczegoly = ws.cell(wiersz, KOL_SZCZEGOLY).value

        if typ not in budzet.TYPY:
            powod = f"typ spoza słownika: {typ!r} (wiersz {wiersz})"
            powody[powod] = powody.get(powod, 0) + 1
        elif not str(kategoria or "").strip():
            powod = f"pusta kategoria (wiersz {wiersz})"
            powody[powod] = powody.get(powod, 0) + 1
        elif kwota is None:
            powod = (f"kwota nie jest liczbą: "
                     f"{ws.cell(wiersz, KOL_KWOTA).value!r} (wiersz {wiersz})")
            powody[powod] = powody.get(powod, 0) + 1
        else:
            wpisy.append(Wpis(
                data=komorka_daty.date(), typ=typ,
                kategoria=str(kategoria).strip(), kwota=kwota,
                szczegoly=str(szczegoly).strip() if szczegoly else ""))
        wiersz += 1

    return wpisy, powody


def _sekcje_planu(ws) -> dict[str, tuple[int, list[tuple[int, str]]]]:
    """Mapa typ -> (wiersz nagłówka sekcji, [(wiersz, nazwa kategorii)]).

    Nazwy sekcji bierzemy z **definicji tabel**, nie z tekstu w komórkach:
    tylko one wyznaczają, gdzie kończy się słownik, a zaczynają sloty-zachęty.
    """
    sekcje: dict[str, tuple[int, list[tuple[int, str]]]] = {}
    po_nazwie = {_bez_znakow_diakrytycznych(t): t for t in budzet.TYPY}

    for nazwa_tabeli, zakres in ws.tables.items():
        typ = po_nazwie.get(_bez_znakow_diakrytycznych(nazwa_tabeli))
        if typ is None:
            continue
        odwolanie = zakres.ref if hasattr(zakres, "ref") else str(zakres)
        poczatek, koniec = odwolanie.split(":")
        wiersz_naglowka = int("".join(z for z in poczatek if z.isdigit()))
        wiersz_konca = int("".join(z for z in koniec if z.isdigit()))
        pozycje = []
        for wiersz in range(wiersz_naglowka + 1, wiersz_konca + 1):
            nazwa = ws.cell(wiersz, KOL_KATEGORII_PLANU).value
            if nazwa and str(nazwa).strip():
                pozycje.append((wiersz, str(nazwa).strip()))
        sekcje[typ] = (wiersz_naglowka, pozycje)
    return sekcje


def wczytaj_kategorie_z_arkusza(sciezka: Path) -> dict[str, list[str]]:
    """Słownik kategorii w kolejności z arkusza, po jednej liście na typ."""
    skoroszyt = _otworz(sciezka)
    if ARKUSZ_PLANU not in skoroszyt.sheetnames:
        raise BladImportu(f"W skoroszycie nie ma arkusza {ARKUSZ_PLANU!r}.")
    ws = skoroszyt[ARKUSZ_PLANU]
    sekcje = _sekcje_planu(ws)
    if not sekcje:
        raise BladImportu(
            "W arkuszu planu nie ma definicji tabel Przychody / Wydatki / "
            "Oszczędności. Bez nich nie da się odróżnić kategorii od slotów "
            "na przyszłe wpisy.")
    return {typ: [nazwa for _, nazwa in pozycje]
            for typ, (_, pozycje) in sekcje.items()}


def wczytaj_plan_z_arkusza(sciezka: Path) -> list[tuple[int, int, str, str, Decimal]]:
    """Plan jako krotki (rok, miesiąc, typ, kategoria, kwota).

    Miesiące bierzemy z **dat** w wierszu nagłówka sekcji, nie z etykiet
    tekstowych — te niosą emoji statusu („sty ✅") i nie mówią o roku.
    Pozycje zerowe pomijamy: w arkuszu plan jest wypełniony tylko dla trzech
    miesięcy, a jedenaście miesięcy zer to szum, nie dane.
    """
    skoroszyt = _otworz(sciezka)
    ws = skoroszyt[ARKUSZ_PLANU]
    pozycje = []
    for typ, (wiersz_naglowka, kategorie) in _sekcje_planu(ws).items():
        miesiace = []
        for kolumna in range(PIERWSZA_KOL_MIESIACA, ws.max_column + 1):
            naglowek = ws.cell(wiersz_naglowka, kolumna).value
            if isinstance(naglowek, datetime.datetime):
                miesiace.append((kolumna, naglowek.year, naglowek.month))
        for wiersz, kategoria in kategorie:
            for kolumna, rok, miesiac in miesiace:
                kwota = _na_decimal(ws.cell(wiersz, kolumna).value)
                if kwota is not None and kwota != 0:
                    pozycje.append((rok, miesiac, typ, kategoria, kwota))
    return pozycje


def _klucz(data: str, typ: str, kategoria: str, kwota, szczegoly: str) -> tuple:
    """Klucz odsiewania duplikatow przy imporcie.

    Zaokraglenie przez `stawki.do_groszy`, tak jak w `_liczba` wyzej. Do Z4
    stalo tu wlasne `quantize` bez trybu — czyli TEN SAM wpis mogl dostac dwa
    rozne klucze zaleznie od tego, ktora sciezka go zaokraglila, i przeslizgnac
    sie przez odsiewanie jako „nowy".
    """
    return (str(data), str(typ), str(kategoria),
            str(stawki.do_groszy(Decimal(str(kwota)))), str(szczegoly))


def importuj(polaczenie, sciezka: Path) -> RaportImportu:
    """Wciąga słownik, wpisy i plan. Zwraca cztery liczby i zdanie.

    **Deduplikacja liczy krotność, nie unikalność.** Kolumna `Szczegóły` jest
    pusta we wszystkich 204 wierszach źródła, więc klucz „data + typ +
    kategoria + kwota + szczegóły" nie odróżnia dwóch prawdziwych kaw po 12 zł
    tego samego dnia. Import porównuje **liczbę wystąpień** klucza w pliku
    z liczbą w bazie i wstawia wyłącznie nadwyżkę: ponowny import
    niezmienionego arkusza zapisuje zero, a dwa bliźniacze wpisy wchodzą oba.
    Więz `UNIQUE` zjadłby tu prawdziwe dane.
    """
    sciezka = Path(sciezka)

    kategorie_dodane = 0
    for typ, nazwy in wczytaj_kategorie_z_arkusza(sciezka).items():
        istniejace = set(magazyn.wczytaj_kategorie(polaczenie, typ=typ)["nazwa"])
        for nazwa in nazwy:
            if nazwa not in istniejace:
                magazyn.dodaj_kategorie(polaczenie, typ=typ, nazwa=nazwa)
                kategorie_dodane += 1

    wpisy, powody = wczytaj_wpisy_z_arkusza(sciezka)
    przeczytane = len(wpisy) + sum(powody.values())

    w_bazie = magazyn.wczytaj_wpisy(polaczenie)
    juz_sa: Counter = Counter()
    for _, w in w_bazie.iterrows():
        juz_sa[_klucz(w["data"], w["typ"], w["kategoria"], w["kwota"],
                      w["szczegoly"])] += 1

    zapisane = pominiete = 0
    for wpis in wpisy:
        klucz = _klucz(wpis.data.isoformat(), wpis.typ, wpis.kategoria,
                       wpis.kwota, wpis.szczegoly)
        if juz_sa[klucz] > 0:
            juz_sa[klucz] -= 1
            pominiete += 1
            continue
        try:
            magazyn.zapisz_wpis(polaczenie, data=wpis.data, typ=wpis.typ,
                                kategoria=wpis.kategoria, kwota=wpis.kwota,
                                szczegoly=wpis.szczegoly)
            zapisane += 1
        except magazyn.BladMagazynu as e:
            powod = f"odrzucony przez magazyn: {e}"
            powody[powod] = powody.get(powod, 0) + 1

    pozycje_planu = 0
    for rok, miesiac, typ, kategoria, kwota in wczytaj_plan_z_arkusza(sciezka):
        try:
            magazyn.zapisz_plan(polaczenie, rok=rok, miesiac=miesiac, typ=typ,
                                kategoria=kategoria, kwota_planowana=kwota)
            pozycje_planu += 1
        except magazyn.BladMagazynu as e:
            powod = f"plan odrzucony: {e}"
            powody[powod] = powody.get(powod, 0) + 1

    odrzucone = sum(powody.values())
    return RaportImportu(
        przeczytane=przeczytane, zapisane=zapisane,
        pominiete_jako_powtorzenia=pominiete, odrzucone=odrzucone,
        powody=powody, kategorie_dodane=kategorie_dodane,
        pozycje_planu=pozycje_planu,
        komunikat=(
            f"Przeczytano {przeczytane} wpisów, zapisano {zapisane}, "
            f"pominięto jako powtórzenia {pominiete}, odrzucono {odrzucone}. "
            f"Kategorii dopisanych: {kategorie_dodane}. "
            f"Pozycji planu: {pozycje_planu}."))

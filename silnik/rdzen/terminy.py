"""Terminy zapłaty podatku i składek — czysta arytmetyka kalendarza.

DLACZEGO TE DATY NIE SĄ ZASZYTE NA WIARĘ. Termin wpisany na sztywno i cicho
nieaktualny jest gorszy niż brak terminu: użytkownik zaplanuje przelew na zły
dzień i dowie się o tym z odsetkami. Każdy termin niesie więc `fraza` —
zdanie, które MUSI występować na stronie źródłowej — i przechodzi przez ten
sam mechanizm weryfikacji, co stawki (§6 specyfikacji, `rdzen.weryfikacja`).

Pomiar źródeł 2026-08-25:
  VAT      `biznes.gov.pl/pl/portal/00232` — „zapłacić wynikający z niej
           podatek przy rozliczeniu miesięcznym – do 25. dnia następnego
           miesiąca, na przykład za maj do 25 czerwca"
  ryczałt  `biznes.gov.pl/pl/portal/00263` — „wpłacać go w terminie: do 20.
           dnia następnego miesiąca za miesiąc poprzedni, za grudzień – do
           20 stycznia następnego roku podatkowego"
  ZUS      `biznes.gov.pl/pl/portal/00274` — „do 20. dnia następnego miesiąca
           – dla pozostałych płatników składek" (JDG nie ma osobowości prawnej,
           więc jest „pozostałym płatnikiem")
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

#: Uproszczenia, które jadą razem z wynikiem. Wynik bez widocznych założeń
#: udaje precyzję, której nie ma.
ZALOZENIA = [
    "Weekend przesuwa termin na poniedziałek; dni ustawowo wolne (święta) "
    "NIE są modelowane — sprawdź kalendarz, gdy termin wypada blisko święta.",
    "Rozliczenie miesięczne. Przy kwartalnym VAT terminy są inne.",
]


@dataclass(frozen=True)
class Termin:
    """Jedna danina: który dzień, czym to udowodnić i kogo dotyczy."""

    nazwa: str
    dzien: int
    zrodlo: str      # klucz w `stawki.ZRODLA`
    fraza: str       # musi wystąpić na stronie źródłowej
    formy: tuple[str, ...] = ()   # puste = dotyczy każdej formy
    roczny: bool = False          # True: raz w roku, nie co miesiąc
    miesiac_roczny: int | None = None


#: Wszystkie daniny wszystkich form, JEDEN nośnik. Lista jest **kompletna**
#: i taka zostaje; filtrowanie po aktywnej formie robi WYŁĄCZNIE ekran
#: (`najblizsze(dzis, forma=...)`).
#:
#: Powód jest zmierzony, nie estetyczny: `weryfikacja.oczekiwane_frazy`
#: iteruje po tej liście i z niej buduje listę fraz sprawdzanych u źródła.
#: Gdyby pozycja znikała stąd przy nieaktywnej formie, **fraza tej formy
#: przestałaby być sprawdzana** — po cichu i przy zielonej suicie.
#: Nośnik pełny, widok wąski.
TERMINY: tuple[Termin, ...] = (
    Termin("VAT", 25, "vat", "do 25. dnia następnego miesiąca"),
    Termin("Ryczałt", 20, "ryczalt", "do 20. dnia następnego miesiąca",
           formy=("RYCZALT",)),
    # Zaliczka PIT na skali — ten sam 20. dzień, inna strona źródłowa
    # i inna fraza (plan formy §8 poz. 1).
    Termin("PIT", 20, "skala",
           "do 20. dnia miesiąca następującego po miesiącu",
           formy=("SKALA",)),
    Termin("ZUS", 20, "spoleczne", "do 20. dnia następnego miesiąca"),
    # Czwarty termin, którego lista nie znała (plan formy §3, różnica 9):
    # roczne rozliczenie składki zdrowotnej — dopłata do 20 maja roku
    # następnego. Nie mieści się w rytmie „20. dnia następnego miesiąca",
    # więc niesie własny cykl zamiast udawać miesięczny.
    Termin("Zdrowotna — dopłata roczna", 20, "zdrowotna",
           "rozliczenie roczne składki zdrowotnej",
           roczny=True, miesiac_roczny=5),
)


@dataclass(frozen=True)
class NajblizszyTermin:
    nazwa: str
    data: date          # dzień zapłaty, już po przesunięciu z weekendu
    za_okres: date      # pierwszy dzień miesiąca, którego dotyczy


#: Najwiekszy dzien miesiaca, jaki wolno WPISAC. Kraniec wspolny z
#: `magazyn._wymagaj_dnia` — dwa nosniki dwoch roznych regul (zapis sprawdza,
#: odczyt rozwiazuje), pilnowane strażnikiem zgody
#: `test_ZGODA_dwoch_nosnikow_dnia_na_krancu_zakresu`. Prog konsolidacji:
#: pierwsza zmiana zakresu dnia w ktorymkolwiek z tych dwoch miejsc.
DZIEN_MAX = 31


def dzien_w_miesiacu(rok: int, miesiac: int, dzien: int) -> date:
    """Data platnosci w danym miesiacu. Dzien dluzszy niz miesiac = OSTATNI.

    Regula byla **udokumentowana w `magazyn._wymagaj_dnia` i nigdzie
    niezaimplementowana**: „dzien wiekszy niz dlugosc miesiaca (np. 31
    w lutym) jest dopuszczalny i znaczy ostatni dzien — inaczej rachunek
    platny 31. trzeba by wpisywac dwa razy, raz dla lutego". Prognoza
    plynnosci jest jej pierwszym konsumentem: pozycja, ktora nie trafi
    w luty, wypada z osi dziennej bez sladu.

    Dzien spoza zakresu 1..DZIEN_MAX jest BLEDEM, nie kwota do przyciecia —
    to wpis, ktorego magazyn nigdy nie przyjal, a ciche przyciecie zamienilo
    by blad w liczbe.
    """
    numer = int(dzien)
    if not 1 <= numer <= DZIEN_MAX:
        raise ValueError(
            f"Nie ma takiego dnia miesiaca ({dzien}). Podaj liczbe "
            f"1-{DZIEN_MAX}.")
    dlugosc = calendar.monthrange(int(rok), int(miesiac))[1]
    return date(int(rok), int(miesiac), min(numer, dlugosc))


def _nastepny_miesiac(rok: int, miesiac: int) -> tuple[int, int]:
    return (rok + 1, 1) if miesiac == 12 else (rok, miesiac + 1)


def _poprzedni_miesiac(rok: int, miesiac: int) -> tuple[int, int]:
    return (rok - 1, 12) if miesiac == 1 else (rok, miesiac - 1)


def _dzien_roboczy(dzien: date) -> date:
    """Sobota i niedziela przesuwają się na poniedziałek.

    Święta NIE — patrz `ZALOZENIA`. Modelowanie ich wymaga kalendarza dni
    ustawowo wolnych, w tym Wielkanocy ruchomej; wpisanie połowy tej listy
    dałoby przesunięcia poprawne w części przypadków, a to gorsze niż jawne
    „nie modelujemy", bo wygląda na kompletne.
    """
    while dzien.weekday() >= 5:
        dzien += timedelta(days=1)
    return dzien


def _data_platnosci(termin: Termin, okres: date) -> date:
    rok, miesiac = _nastepny_miesiac(okres.year, okres.month)
    return _dzien_roboczy(date(rok, miesiac, termin.dzien))


def dotyczy_formy(termin: Termin, forma: str | None) -> bool:
    """Czy ta danina dotyczy podanej formy. `None` znaczy „wszystkie"."""
    return forma is None or not termin.formy or forma in termin.formy


def _data_roczna(termin: Termin, dzis: date) -> tuple[date, date]:
    """Termin roczny: dzień `miesiac_roczny` za rok poprzedni; po jego minięciu
    ten sam dzień w roku następnym. Okres to 1 stycznia rozliczanego roku."""
    platnosc = _dzien_roboczy(date(dzis.year, termin.miesiac_roczny, termin.dzien))
    rok_okresu = dzis.year - 1
    if platnosc < dzis:
        platnosc = _dzien_roboczy(
            date(dzis.year + 1, termin.miesiac_roczny, termin.dzien))
        rok_okresu = dzis.year
    return platnosc, date(rok_okresu, 1, 1)


def platnosc_za_okres(nazwa: str, okres: date) -> date:
    """Dzień zapłaty daniny `nazwa` za `okres` (pierwszy dzień miesiąca).

    Publiczne wejście do tej samej arytmetyki, z której korzysta `najblizsze` —
    dzień miesiąca i przesunięcie z weekendu zostają w JEDNYM miejscu. Bez tego
    konsument rozbijający daninę na okresy (ZUS per miesiąc, wada 2) musiałby
    powtórzyć regułę „20. dnia następnego miesiąca, a jak weekend to w poniedziałek"
    u siebie — i rozjechać się przy pierwszej zmianie.
    """
    termin = next((t for t in TERMINY if t.nazwa == nazwa), None)
    if termin is None:
        raise ValueError(
            f"Nie znam daniny {nazwa!r}. Znane: "
            + ", ".join(t.nazwa for t in TERMINY) + ".")
    return _data_platnosci(termin, okres)


def najblizsze(dzis: date, forma: str | None = None,
               dzialalnosc_od: date | None = None) -> list[NajblizszyTermin]:
    """Najbliższy termin każdej daniny, licząc od `dzis` włącznie.

    Dzień terminu NIE jest przeterminowany — przesunięcie go o miesiąc
    kazałoby zapłacić za późno, a aplikacja pokazywałaby przy tym spokój.

    `dzialalnosc_od` — **żaden termin miesięczny nie może dotyczyć okresu
    sprzed pierwszego miesiąca działalności** (naprawa 2026-08-28). Bez tego
    przy odczycie 15 września 2026 wszystkie daniny wychodziły „za sierpień",
    czyli za miesiąc, w którym działalności nie było, z terminem 21 września —
    **aplikacja kazała zapłacić urzędowi miesiąc za wcześnie**. Kwota była
    dobra, data nie. Darek, 2026-08-28 godz. 19:14: *„pierwsze zobowiązanie
    ZUS będzie za wrzesień w październiku"*.

    Pominięcie argumentu zostawia zachowanie sprzed naprawy — data nie jest
    zgadywana. Termin **roczny** tej regule nie podlega: ma własny cykl,
    a odcięcie go zabrałoby jedyną pozycję pilnującą dopłaty rocznej.

    `forma` zawęża wynik do danin tej formy. Zawężenie jest TUTAJ, a nie
    w `TERMINY`, bo lista jest nośnikiem także dla `weryfikacja` — patrz
    komentarz przy `TERMINY`.
    """
    wynik = []
    for termin in TERMINY:
        if not dotyczy_formy(termin, forma):
            continue
        if termin.roczny:
            platnosc, okres = _data_roczna(termin, dzis)
            wynik.append(NajblizszyTermin(termin.nazwa, platnosc, okres))
            continue
        okres = date(*_poprzedni_miesiac(dzis.year, dzis.month), 1)
        platnosc = _data_platnosci(termin, okres)
        if platnosc < dzis:
            okres = date(dzis.year, dzis.month, 1)
            platnosc = _data_platnosci(termin, okres)
        if dzialalnosc_od is not None:
            pierwszy = date(dzialalnosc_od.year, dzialalnosc_od.month, 1)
            if okres < pierwszy:
                okres = pierwszy
                platnosc = _data_platnosci(termin, okres)
        wynik.append(NajblizszyTermin(termin.nazwa, platnosc, okres))
    return sorted(wynik, key=lambda t: (t.data, t.nazwa))

"""Oś terminów — „co mnie czeka" (Z72, zdolności B1-B4).

TEN MODUŁ NIE LICZY ANI JEDNEJ KWOTY. Wszystkie kwoty i daty policzyła już
`prognoza_plynnosci.zbuduj`: daniny per forma, zaległości z realnych faktur,
pozycje planu z dniem płatności, raty siedzące w planie. Tutaj są WYBIERANE,
GRUPOWANE i NAZWANE pilnością.

Powód jest zmierzony, nie estetyczny. Ta sama liczba policzona drugi raz
w drugim miejscu dała 2026-08-26 ekran z `-6 098,11 zł` obok doradcy
z `+8 007,89 zł` — o tej samej rzeczy, w tej samej chwili, przy zielonej suicie.
Reguła „jeden nośnik" (CLAUDE.md §8 v1.17) ma tu postać twardą: jeżeli ten plik
kiedykolwiek zacznie mnożyć, dodawać albo zaokrąglać kwoty, jest błędem.

CZEGO TU ŚWIADOMIE NIE MA:
  * rat z tabeli `zobowiazania`, których nie ma w planie — prognoza niesie ich
    pełną listę i mówi „sprawdź, czy są w planie"; dopisanie ich do osi
    policzyłoby je drugi raz (`prognoza_plynnosci` §CZEGO NIE ROBI);
  * wpływów — oś odpowiada na pytanie „co mam zapłacić", a przychód na tej
    liście czytałby się jak zobowiązanie;
  * własnej definicji „nie wiem" — stan przechodzi z prognozy w całości.

JEDYNY WYJĄTEK OD „NIE LICZY", nazwany, żeby nagłówek nie obiecywał więcej,
niż kod dotrzymuje: `powod_powiadomienia` zmienia znak kwoty (`-pierwsza.kwota`)
przed wypisaniem jej w zdaniu powiadomienia. Oś trzyma wypływy ze znakiem
minus, a zdanie „ZUS — 1 926,76 zł" czyta się jak rachunek do zapłacenia,
podczas gdy „-1 926,76 zł" czyta się jak zwrot. To zmiana ZNAKU przy
prezentacji, nie wyliczenie wartości ekonomicznej — żadna kwota nie powstaje
tu z dodawania, mnożenia ani zaokrąglania. Gdyby kiedykolwiek pojawiła się
druga operacja arytmetyczna, ten akapit ma zostać przepisany albo operacja
usunięta.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from silnik.rdzen import podatki, prezentacja, prognoza_plynnosci as pp

#: Ile dni osi pokazujemy. Czterdzieści pięć, nie trzydzieści: przy oknie
#: miesięcznym danina płacona 20. dnia następnego miesiąca wypada z widoku
#: dokładnie wtedy, gdy trzeba na nią odłożyć.
OKNO_DNI_DOMYSLNE = 45

#: Kiedy pozycja jest PILNA — próg dni. Trzy, bo przelew między bankami
#: potrafi iść dobę, a decyzja „skąd wziąć" wymaga jeszcze jednej.
PROG_PILNOSCI_DNI = 3

#: Jak blisko musi być zejście pod kreskę, żeby obudzić system (C4, decyzja
#: Darka 2026-08-27). Czternaście dni to horyzont, w którym da się jeszcze
#: przesunąć płatność albo zafakturować.
PROG_UJEMNEJ_LINII_DNI = 14

#: Rodzaje zdarzeń, które są WYPŁYWEM — **WOŁANE, nie powtórzone** (Z7b).
#:
#: DŁUG SPŁACONY, NIE PRZESUNIĘTY. Do Z7b stał tu świadomy drugi nośnik
#: z jawnym progiem konsolidacji: „PIERWSZY NOWY RODZAJ ZDARZENIA
#: w `prognoza_plynnosci`". `RODZAJ_WPIS` (D-20) jest tym pierwszym nowym
#: rodzajem, więc próg zadziałał i podział przeniósł się do nośnika prognozy.
#: Tutaj zostaje jedno wołanie.
#:
#: Wykrył to strażnik `test_RODZAJE_WYPLYWU_pokrywaja_KOMPLET_rodzajow_prognozy`,
#: nie czujność autora — i to jest dokładnie ta praca, do której go napisano:
#: bez niego nowy rodzaj wypadłby z osi PO CICHU, przy zielonej suicie.
RODZAJE_WYPLYWU = pp.RODZAJE_WYPLYWU


@dataclass(frozen=True)
class Pozycja:
    """Jedna rzecz do zapłacenia: kiedy, ile, i czy będzie z czego."""

    data: date
    nazwa: str
    rodzaj: str
    kwota: Decimal
    saldo_po: Decimal
    dni_do: int
    pilna: bool
    dzien_domniemany: bool = False


@dataclass(frozen=True)
class CoMnieCzeka:
    """Oś terminów plus to, co ekran musi powiedzieć obok niej.

    `rezerwa is None` znaczy „nie liczyłem rezerwy", nie „rezerwa zero" —
    ta sama reguła D11 co wszędzie indziej w tym projekcie.
    """

    stan: str
    pozycje: tuple[Pozycja, ...] = ()
    okno_dni: int = OKNO_DNI_DOMYSLNE
    #: `None` znaczy „NIE LICZYŁEM", `0` znaczy „policzyłem i nie ma".
    #: Rozstrzygnięcie Olivera (Z73p2, wariant a). Wartość domyślna `0`
    #: kazała gałęzi „nie wiem" mówić „zero pilnych" — czyli DOBRĄ
    #: WIADOMOŚĆ tam, gdzie nie ma żadnej wiadomości. To pole przechodzi
    #: granicę HTTP (Z76) i trafia na ekran (Z79), więc kłamstwo dojechałoby
    #: do człowieka. Ta sama reguła D11, którą ten dataclass stosuje już do
    #: `rezerwa` i `najblizszy_wyplyw` — trzy pola, jedna reguła, zero
    #: wyjątków.
    pilnych: int | None = None
    najblizszy_wyplyw: date | None = None
    rezerwa: podatki.RezerwaPodatkowa | None = None
    raty_spoza_planu: tuple = ()
    zastrzezenia: tuple = ()


def pilna(*, kwota: Decimal, saldo_po: Decimal, dni_do: int) -> bool:
    """JEDEN NOŚNIK reguły pilności. Trzy warunki naraz.

    Wołają ją: oś terminów, ekran (baner) i strażnik w tle (powiadomienie).
    Trzy konsumenty jednej reguły to dokładnie ta sytuacja, w której druga
    kopia rozjeżdża się po cichu — strażnik budziłby system wtedy, gdy ekran
    mówi „spokojnie".

    Warunek trzeci — `saldo_po < 0` — jest tym, który odróżnia „termin blisko"
    od „nie będzie z czego zapłacić". Bez niego powiadomienie chodziłoby
    dwudziestego każdego miesiąca i przestałoby cokolwiek znaczyć.
    """
    return bool(kwota < 0 and dni_do <= PROG_PILNOSCI_DNI and saldo_po < 0)


def zbuduj(*, prognoza: pp.Prognoza, rezerwa, dzis: date,
           okno_dni: int = OKNO_DNI_DOMYSLNE) -> CoMnieCzeka:
    """Oś terminów z gotowej prognozy. BEZ BAZY i BEZ RACHUNKU."""
    if prognoza.dni is None:
        return CoMnieCzeka(stan=prognoza.stan, okno_dni=okno_dni,
                           rezerwa=rezerwa,
                           raty_spoza_planu=prognoza.zobowiazania_spoza_planu,
                           zastrzezenia=prognoza.zastrzezenia)

    pozycje: list[Pozycja] = []
    for dzien in prognoza.dni:
        dni_do = (dzien.data - dzis).days
        if dni_do < 0 or dni_do > okno_dni:
            continue
        for zdarzenie in dzien.zdarzenia:
            if zdarzenie.rodzaj not in RODZAJE_WYPLYWU:
                continue
            if zdarzenie.kwota_ostrozna >= 0:
                continue
            pozycje.append(Pozycja(
                data=dzien.data, nazwa=zdarzenie.nazwa, rodzaj=zdarzenie.rodzaj,
                kwota=zdarzenie.kwota_ostrozna, saldo_po=dzien.saldo_ostrozne,
                dni_do=dni_do,
                pilna=pilna(kwota=zdarzenie.kwota_ostrozna,
                            saldo_po=dzien.saldo_ostrozne, dni_do=dni_do),
                dzien_domniemany=zdarzenie.dzien_domniemany))

    return CoMnieCzeka(
        stan=prognoza.stan, pozycje=tuple(pozycje), okno_dni=okno_dni,
        # Licznik liczony Z LISTY, nie osobno — dwa niezależne przebiegi tej
        # samej reguły rozjeżdżają się przy pierwszej jej zmianie.
        pilnych=sum(1 for p in pozycje if p.pilna),
        # WYBÓR, nie rachunek: `min`, a nie `pozycje[0]`. Silnik oddaje
        # `prognoza.dni` posortowane rosnąco (gęsta seria dzienna), ale ta
        # kolejność jest własnością CUDZEJ listy, a nazwa pola jest naszą
        # OBIETNICĄ wobec ekranu. `pozycje[0]` przy wejściu w innej kolejności
        # pokazywałby wypływ najdalszy pod etykietą „najbliższy" — i wyglądał
        # przy tym na poprawny.
        najblizszy_wyplyw=min((p.data for p in pozycje), default=None),
        rezerwa=rezerwa,
        raty_spoza_planu=prognoza.zobowiazania_spoza_planu,
        zastrzezenia=prognoza.zastrzezenia)


def zestaw(polaczenie, *, dzis: date | None = None,
           okno_dni: int = OKNO_DNI_DOMYSLNE) -> CoMnieCzeka:
    """Cienki zbieracz: czyta bazę przez ISTNIEJĄCE nośniki, woła `zbuduj`.

    Ani jednego własnego zapytania SQL — `prognoza_plynnosci.prognozuj`
    i `podatki.rezerwa_z_bazy` już wiedzą, co odczytać. Powtórzenie ich
    odczytów byłoby czwartą drogą tych samych danych do silnika i czwartą
    okazją, żeby jedna z nich podała co innego (Z55).
    """
    dzis = dzis or date.today()
    prognoza = pp.prognozuj(polaczenie, dzis=dzis)
    rezerwa = podatki.rezerwa_z_bazy(polaczenie, dzis=dzis)
    return zbuduj(prognoza=prognoza, rezerwa=rezerwa, dzis=dzis,
                  okno_dni=okno_dni)


def powod_powiadomienia(wynik: CoMnieCzeka, *, prognoza: pp.Prognoza,
                        dzis: date) -> str | None:
    """Zdanie, którym strażnik budzi system — albo `None`. JEDEN NOŚNIK.

    Decyzja Darka 2026-08-27: budzą WYŁĄCZNIE pieniądze pod kreską. Dwa
    wyzwalacze i ani jednego więcej:

    1. jest pozycja pilna (termin ≤ 3 dni, saldo dnia ujemne);
    2. linia ostrożna schodzi poniżej zera w ciągu `PROG_UJEMNEJ_LINII_DNI`.

    KOLEJNOŚĆ NIE JEST DOWOLNA i nie jest ta, którą miała pierwsza wersja
    (poprawka Z73p, rozstrzygnięcie Olivera 2026-08-27). Do poprawki gałąź
    linii ujemnej stała PIERWSZA — i wtedy gałąź pozycji pilnej była
    **martwa**. Zmierzone, nie wywnioskowane: mutacja M347 (`pilne = []`)
    przeżyła całą suitę 856 testów, bo nie miała czego zepsuć.

    Dlaczego była martwa: `prognoza_plynnosci.zbuduj` ustawia
    `pierwszy_dzien_ujemny` na PIERWSZYM dniu, w którym linia ostrożna
    schodzi pod zero, a `pilna()` wymaga salda ujemnego przy terminie ≤ 3
    dni. Każda pozycja pilna leży więc w dniu ujemnym oddalonym o ≤ 3 dni,
    czyli ZAWSZE wewnątrz progu 14 dni drugiego wyzwalacza. Gałąź stojąca
    wyżej wracała pierwsza i druga nie wykonywała się nigdy.

    Po odwróceniu OBIE gałęzie są osiągalne i każda ma swój przedział:

    * jest pozycja pilna (zejście pod kreskę w ≤ 3 dni) → zdanie z NAZWĄ
      pozycji, jej terminem, kwotą i saldem tego dnia;
    * zejście pod kreskę dalej niż 3 dni, ale w ciągu 14 → nie ma pozycji
      pilnej, więc odpala zdanie o linii ostrożnej i brakującej kwocie;
    * zejście dalej niż 14 dni albo wcale → `None`, system śpi.

    Zdanie z nazwą pozycji wygrywa świadomie, gdy zachodzą oba warunki
    naraz. „ZUS — termin 2026-09-19, 1 926,76 zł, a saldo tego dnia wynosi
    -500,00 zł" mówi, co zrobić. „Linia ostrożna schodzi poniżej zera"
    mówi tylko, że jest źle. Powiadomienie ma jedno zdanie i jedną szansę.
    Cena wymiany nazwana wprost: przy pozycji pilnej powiadomienie NIE poda
    kwoty „brakuje" z prognozy — nazwa, termin i saldo dnia niosą więcej.

    Warunki obu wyzwalaczy są bez zmian wobec decyzji Darka; zmieniło się
    wyłącznie to, które zdanie wygrywa, gdy zachodzą jednocześnie.

    Rozbieżność stawek u źródła (B5) i przebieg bez znalezisk trafiają na
    pasek ekranu, nie do powiadomienia. Powód: powiadomienie, które przychodzi
    codziennie, przestaje się czytać — a wtedy przestaje działać to jedno ważne.

    Stan „nie wiem" NIE budzi. Brak wiedzy nie jest ostrzeżeniem ani spokojem;
    ekran mówi o nim wprost, system nie.
    """
    if prognoza.dni is None:
        return None

    pilne = [p for p in wynik.pozycje if p.pilna]
    if pilne:
        # Ta sama reguła co przy `najblizszy_wyplyw`: powiadomienie ma
        # nazwać pozycję NAJBLIŻSZĄ, a nie pierwszą na liście.
        pierwsza = min(pilne, key=lambda p: p.data)
        return (f"{pierwsza.nazwa} — termin {pierwsza.data.isoformat()}, "
                f"{prezentacja.zloty(-pierwsza.kwota)}, a saldo tego dnia "
                f"wynosi {prezentacja.zloty(pierwsza.saldo_po)}.")

    if prognoza.pierwszy_dzien_ujemny is not None:
        za_ile = (prognoza.pierwszy_dzien_ujemny - dzis).days
        if za_ile <= PROG_UJEMNEJ_LINII_DNI:
            brakuje = ("" if prognoza.brakuje is None
                       else f" Brakuje {prezentacja.zloty(prognoza.brakuje)}.")
            return (f"Linia ostrożna schodzi poniżej zera "
                    f"{prognoza.pierwszy_dzien_ujemny.isoformat()}"
                    f" (za {za_ile} dni).{brakuje}")

    return None

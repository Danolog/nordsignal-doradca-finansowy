"""Arytmetyka budzetu osobistego - czyste funkcje, zero SQL, zero interfejsu.

Ten modul jest jedynym nosnikiem trzech rzeczy: dozwolonych typow wpisu,
startowego slownika kategorii i regul liczenia (znak, saldo, do alokacji,
plan kontra wykonanie). `magazyn` i `pulpit` te reguly **wolaja**, nie
powtarzaja.

Dlaczego osobny modul, a nie doklejka do `magazyn.py`: arytmetyka budzetu ma
byc sprawdzalna bez bazy danych. Test, ktory musi najpierw zalozyc tabele,
zeby policzyc sume trzech liczb, mierzy dwie rzeczy naraz i przy czerwieni
nie mowi, ktora z nich pekla.

Kierunek zaleznosci jest jednostronny: `magazyn` importuje `budzet`, nigdy
odwrotnie.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from silnik.rdzen import stawki

#: Trzy dozwolone typy wpisu. Jedyny nosnik tej trojki w calym projekcie.
#: Nazwane stale zamiast golych napisow, zeby literowka w wywolaniu byla bledem
#: przy imporcie modulu, a nie cicho pustym wynikiem filtrowania.
TYP_PRZYCHODY = "Przychody"
TYP_WYDATKI = "Wydatki"
TYP_OSZCZEDNOSCI = "Oszczędności"

TYPY = (TYP_PRZYCHODY, TYP_WYDATKI, TYP_OSZCZEDNOSCI)

#: Kategorie odczytane z arkusza `Budzet Osobisty 2025` 2026-08-25, z definicji
#: tabel `Przychody` (C9:C13), `Wydatki` (C22:C37) i `Oszczednosci` (C41:C45)
#: w arkuszu `Planowanie Budzetu`. Sloty-placeholdery spoza zakresow tabel
#: (siedem powtorzen `Inne` i wiersze `Wprowadz Kategorie...`) sa odfiltrowane.
#:
#: `Inne` wystepuje w DWOCH typach naraz - dlatego kluczem kategorii jest para
#: (typ, nazwa), nigdy sama nazwa.
#: Kategoria, w ktorej ladują zaplaty podatku i skladek. Jedyny nosnik tej
#: nazwy w calym projekcie — `rdzen.podatki` odejmuje po niej zaplaty od
#: naliczonych zobowiazan, a lista startowa nizej uzywa tej samej stalej.
#: Napis przepisany w dwoch miejscach rozjechalby sie przy pierwszej korekcie
#: i saldo rezerwy przestaloby spadac, nie zglaszajac bledu.
KATEGORIA_PODATKI = "Podatki i ZUS"

#: Kategoria, w ktorej ladują koszty JDG zapisane w zakladce „JDG i podatki".
#: Ta nazwa POCHODZI Z ARKUSZA (jest w `WYDATKI_Z_ARKUSZA` nizej) — stala
#: istnieje po to, zeby `magazyn.zapisz_koszt` nie powtarzal napisu.
KATEGORIA_KOSZTY_JDG = "Firmowe"

#: Kategoria, w ktorej laduja przychody z zaplaconych faktur JDG. „Wynagrodzenie",
#: bo przy jednoosobowej dzialalnosci to jest to samo co pensja — z ta roznica,
#: ze wszystkie obciazenia placisz sam. Nazwa POCHODZI Z ARKUSZA.
KATEGORIA_PRZYCHOD_JDG = "Wynagrodzenie"

#: Kategorie wydatkow ODCZYTANE Z ARKUSZA `Budzet Osobisty 2025`, 2026-08-25.
#: Ta krotka jest zapisem POMIARU i zmienia sie wylacznie wtedy, gdy zmieni
#: sie arkusz. Straznik liczy jej dlugosc wprost (15) — dlatego dolozenie
#: wlasnej kategorii TUTAJ zaklamaloby przeslanke „slownik odpowiada arkuszowi".
WYDATKI_Z_ARKUSZA: tuple[str, ...] = (
    "Energia Elektryczna", "Gaz", "Telefon i Internet", "Transport",
    "Czesne", "Kredyty", "Zdrowie", "Zakupy", "Subskrypcje",
    "Monika i Ada", "Jedzenie poza domem", "Praca", "PUWIS",
    KATEGORIA_KOSZTY_JDG,
    "Inne",
)

#: Kategorie DOLOZONE SWIADOMIE, spoza arkusza — kazda z powodem i data.
#: Rozdzial pochodzenia jest po to, zeby pytanie „czy slownik zgadza sie
#: z arkuszem" dalo sie zadac takze po naszych dolozeniach.
#:
#: - `Podatki i ZUS` (2026-08-25, decyzja D3): bez niej nie ma gdzie zapisac
#:   zaplaty podatku, a rezerwa liczona jako saldo nigdy nie spada.
KATEGORIE_SPOZA_ARKUSZA: tuple[str, ...] = (KATEGORIA_PODATKI,)

KATEGORIE_STARTOWE: dict[str, tuple[str, ...]] = {
    "Przychody": (
        KATEGORIA_PRZYCHOD_JDG, "Własna Inicjatywa", "Zwrot wydatków", "Inne",
    ),
    "Wydatki": WYDATKI_Z_ARKUSZA + KATEGORIE_SPOZA_ARKUSZA,
    "Oszczędności": (
        "Poduszka finansowa", "Inwestycje", "Nadpłata Kredytów",
        "Reszta Revolut",
    ),
}

#: Kwoty zaokraglamy przez `stawki.do_groszy` - jeden nosnik konwencji
#: pienieznej w projekcie (ROUND_HALF_UP, nie bankierskie).
_DZIESIETNA = Decimal("0.1")


def _procent(x: Decimal) -> Decimal:
    return Decimal(x).quantize(_DZIESIETNA, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Wykonanie:
    """Jedna pozycja zestawienia plan kontra wykonanie za konkretny miesiac.

    `procent` jest `None`, gdy planu nie ma. Zero klamaloby, ze wydatek
    zmiescil sie w budzecie, a sto - ze go wyczerpal; jedno i drugie to
    odpowiedz na pytanie, ktorego nikt nie zadal.
    """

    typ: str
    kategoria: str
    planowane: Decimal
    wykonane: Decimal
    procent: Decimal | None
    pozostalo: Decimal
    przekroczone: bool


def znak(typ: str) -> int:
    """Kierunek, w ktorym wpis przesuwa srodki do dyspozycji.

    Oszczednosci maja znak ujemny tak samo jak wydatki: pieniadz odlozony na
    cel przestaje byc do wydania. To jest cala idea budzetu zerowego - kazda
    zlotowka ma przypisane miejsce, a "do alokacji" pokazuje reszte.
    """
    if typ not in TYPY:
        raise ValueError(
            f"Nieznany typ wpisu: {typ}. Dozwolone sa wylacznie: "
            + ", ".join(TYPY) + "."
        )
    return 1 if typ == "Przychody" else -1


def _miesiac(wpisy: pd.DataFrame, rok: int, miesiac: int) -> pd.DataFrame:
    """Wiersze z danego miesiaca. Daty sa tekstem ISO, wiec filtr po prefiksie."""
    if wpisy.empty:
        return wpisy
    return wpisy[wpisy["data"].astype(str).str.startswith(f"{rok:04d}-{miesiac:02d}")]


def saldo_narastajaco(wpisy: pd.DataFrame) -> list[Decimal]:
    """Saldo po kazdym kolejnym wpisie, w kolejnosci podanej w ramce.

    Zwraca liste tej samej dlugosci co ramka - jeden element na wpis. Krotsza
    lista znaczylaby, ze czesc wpisow wypadla po drodze, a ostatnia wartosc
    i tak wygladalaby wiarygodnie.
    """
    if wpisy.empty:
        return []
    biezace = Decimal("0.00")
    wynik: list[Decimal] = []
    for _, w in wpisy.iterrows():
        biezace += znak(w["typ"]) * Decimal(str(w["kwota"]))
        wynik.append(stawki.do_groszy(biezace))
    return wynik


def saldo_dzienne(wpisy: pd.DataFrame) -> list[tuple[str, Decimal]]:
    """Saldo na koniec każdego dnia — po jednym punkcie na dzień.

    Wykres z jednym punktem na **wpis** ma oś, na której ta sama data powtarza
    się kilka razy pod rząd; wygląda to, jakby dni było więcej, niż jest,
    i rozciąga skoki, które zdarzyły się w jednej chwili.
    """
    salda = saldo_narastajaco(wpisy)
    if not salda:
        return []
    punkty: dict[str, Decimal] = {}
    for (_, wiersz), saldo in zip(wpisy.iterrows(), salda):
        punkty[str(wiersz["data"])] = saldo
    return list(punkty.items())


def do_alokacji(wpisy: pd.DataFrame, rok: int, miesiac: int) -> Decimal:
    """Przychody minus wydatki minus oszczednosci w danym miesiacu.

    Glowna liczba budzetu zerowego. Pominiecie skladnika oszczednosci daje
    wynik zawyzony i zacheca do wydania pieniedzy, ktore maja juz przeznaczenie.
    """
    biezace = _miesiac(wpisy, rok, miesiac)
    if biezace.empty:
        return Decimal("0.00")
    suma = sum(
        (znak(w["typ"]) * Decimal(str(w["kwota"])) for _, w in biezace.iterrows()),
        Decimal("0.00"),
    )
    return stawki.do_groszy(suma)


@dataclass(frozen=True)
class Alokacja:
    """Kwota do rozdysponowania w okresie RAZEM z pokryciem planu.

    Sama kwota klamalaby przy okresie rocznym z planem na kwartal: wygladalaby
    na odpowiedz o caly rok, bedac odpowiedzia o trzy miesiace, i bylaby
    zanizona o dziewiec miesiecy nie mowiac o tym ani slowem.

    `kwota is None` znaczy "zaden miesiac okresu nie ma planu" i jest czym
    INNYM niz `Decimal("0.00")`, ktore znaczy "plan jest i wychodzi na zero".
    Zero na ekranie wyglada jak budzet spiety co do grosza — najlepszy mozliwy
    stan — wiec brak planu nie ma prawa go udawac.
    """

    kwota: Decimal | None
    miesiecy_z_planem: int
    miesiecy_w_okresie: int


def plan_na_miesiac(plan: pd.DataFrame, rok: int, miesiac: int) -> pd.DataFrame:
    """Reguly planu rozwiniete do JEDNEGO miesiaca — jedyny nosnik tej reguly.

    Pozycja trwala obowiazuje OD swojego miesiaca do odwolania, wiec „plan na
    wrzesien" nie jest juz filtrem po wierszach wrzesniowych, tylko pytaniem
    „ktora wersja tej pozycji obowiazuje we wrzesniu".

    Gdy kandydatow jest kilku, wygrywa NAJPOZNIEJSZY start — to jest definicja
    „zmiana obowiazuje od tego miesiaca w przod". Remis niemozliwy: broni go
    UNIQUE(rok, miesiac, typ, kategoria).
    """
    if plan.empty:
        return plan
    punkt = rok * 12 + (miesiac - 1)
    wybrane: dict[tuple[str, str, str], tuple[int, object]] = {}
    for _, w in plan.iterrows():
        start = int(w["rok"]) * 12 + (int(w["miesiac"]) - 1)
        if start > punkt:
            continue
        if not int(w.get("powtarzalna", 0) or 0):
            # Ramka bez tej kolumny znaczy „jednorazowa", dokladnie tak samo
            # jak DEFAULT 0 w bazie — jeden nosnik znaczenia domyslnego.
            if start != punkt:
                continue
        else:
            if pd.notna(w.get("do_roku")):
                koniec = int(w["do_roku"]) * 12 + (int(w["do_miesiaca"]) - 1)
                if koniec < punkt:
                    continue
            # Cykl: rachunek co dwa miesiace wraca co DRUGI miesiac, liczac
            # od swojego startu. Na osi absolutnej, wiec listopad + 2 to
            # styczen nastepnego roku, nie „miesiac 13".
            co_ile = int(w.get("co_ile_miesiecy", 1) or 1)
            if co_ile > 1 and (punkt - start) % co_ile:
                continue
        # Pozycje rozpoznaje KATEGORIA + OPIS, a nie sama kategoria: w jednej
        # kategorii miesci sie „Kredyt Revolut" i „Kredyt Alior", a takze trzy
        # rachunki za gaz. Pusty opis to pozycja bezimienna — taka, jaka
        # tworzy import arkusza.
        klucz = (w["typ"], w["kategoria"], str(w.get("opis", "") or ""))
        if klucz not in wybrane or start > wybrane[klucz][0]:
            wybrane[klucz] = (start, w)
    if not wybrane:
        return plan.iloc[0:0]
    return pd.DataFrame([w for _, w in wybrane.values()])


def _plan_miesiaca(plan: pd.DataFrame, rok: int, miesiac: int) -> pd.DataFrame:
    """Wiersze planu obowiazujace w danym miesiacu. Wola jedyny nosnik reguly."""
    return plan_na_miesiac(plan, rok, miesiac)


def sumy_planu(plan: pd.DataFrame, rok: int, miesiac: int) -> dict[str, Decimal]:
    """Suma planu per typ dla JEDNEGO miesiaca.

    Typ bez pozycji dostaje zero, a nie znika ze slownika — brak klucza
    zmuszalby kazdego wolajacego do pamietania o `.get(..., 0)`, a jeden
    zapomni.
    """
    wybrany = _plan_miesiaca(plan, rok, miesiac)
    wynik = {typ: Decimal("0.00") for typ in TYPY}
    if wybrany.empty:
        return wynik
    for _, w in wybrany.iterrows():
        wynik[w["typ"]] += Decimal(str(w["kwota_planowana"]))
    return {typ: stawki.do_groszy(kwota) for typ, kwota in wynik.items()}


def do_alokacji_z_planu(plan: pd.DataFrame,
                        miesiace: list[tuple[int, int]]) -> Alokacja:
    """Plan przychodow minus plan wydatkow minus plan oszczednosci, po okresie.

    Wpisy rzeczywiste NIE wchodza do tej liczby — i to jest cala roznica wobec
    `do_alokacji`. Pozycja wpisana w plan przestaje byc do dyspozycji w chwili
    WPISANIA, nie w chwili zaplaty, dokladnie jak rezerwa na podatki. Zaplacenie
    rachunku niczego tu nie zmienia, bo pieniadz mial juz przypisane miejsce —
    a to jest cala definicja budzetu zerowego.

    Funkcja jest okresowa OD RAZU: pojedynczy miesiac to lista jednoelementowa.
    Osobna wersja miesieczna byla by ta sama regula w drugim nosniku.
    """
    suma = Decimal("0.00")
    z_planem = 0
    for rok, miesiac in miesiace:
        if _plan_miesiaca(plan, rok, miesiac).empty:
            continue
        z_planem += 1
        sumy = sumy_planu(plan, rok, miesiac)
        suma += (sumy[TYP_PRZYCHODY] - sumy[TYP_WYDATKI]
                 - sumy[TYP_OSZCZEDNOSCI])
    if z_planem == 0:
        return Alokacja(None, 0, len(miesiace))
    return Alokacja(stawki.do_groszy(suma), z_planem, len(miesiace))


def bez_podatkow(ramka: pd.DataFrame) -> pd.DataFrame:
    """Wiersze bez kategorii „Podatki i ZUS".

    PUBLICZNA od Z61: prognoza plynnosci wola ten filtr zamiast go kopiowac.
    Kopia bylaby drugim nosnikiem reguly o podwojnym podatku — a ta regula
    decyduje o liczbie, ktora uzytkownik zobaczy jako „wolne srodki".

    Podatki maja w tej aplikacji JEDEN nosnik: saldo rezerwy
    (`podatki.rezerwa_na_podatki`). Danina moze wejsc do liczby trzema
    drogami naraz — jako rezerwa, jako pozycja planu i jako zaplacony wydatek
    w tej kategorii — wiec czesc planowa wyklucza ja u siebie i zostawia
    rezerwie.
    """
    if ramka.empty:
        return ramka
    return ramka[ramka["kategoria"] != KATEGORIA_PODATKI]


def wolne_srodki(plan: pd.DataFrame, miesiace: list[tuple[int, int]],
                 rezerwa: Decimal) -> Alokacja:
    """Ile zostanie, gdy poniesiesz wszystko z planu i odlozysz na podatki.

    `do_alokacji_z_planu` minus saldo rezerwy podatkowej. Rezerwa to
    pieniadze, ktore leza na koncie i nie sa Twoje — liczba nazwana „wolne
    srodki" nie ma prawa ich obiecywac.

    Rezerwa jest SALDEM jednego dlugu, nie kwota miesieczna, wiec odejmuje sie
    ja RAZ, niezaleznie od dlugosci okresu. Brak planu zostaje brakiem planu
    (`kwota is None`): sama rezerwa nie mowi, ile jest wolne — mowi tylko,
    ile jest zajete.
    """
    z_planu = do_alokacji_z_planu(bez_podatkow(plan), miesiace)
    if z_planu.kwota is None:
        return z_planu
    return Alokacja(stawki.do_groszy(z_planu.kwota - Decimal(str(rezerwa))),
                    z_planu.miesiecy_z_planem, z_planu.miesiecy_w_okresie)


@dataclass(frozen=True)
class DoZaplacenia:
    """Ile z tego miesiaca zostalo jeszcze do zaplacenia.

    Cztery liczby, nie jedna: samo „pozostalo" nie odroznia planu wykonanego
    w polowie od planu przekroczonego i domknietego danina. `przekroczony_plan`
    jest osobnym polem, bo ujemne „pozostalo" bez slowa wyjasnienia wyglada
    jak wada obliczen, a nie jak informacja o przekroczeniu budzetu.
    """

    zaplanowane: Decimal
    zaplacone: Decimal
    podatki: Decimal
    pozostalo: Decimal
    przekroczony_plan: bool

    @property
    def nadwyzka(self) -> Decimal:
        """O ile wykonanie przekroczylo plan wydatkow. Zero, gdy nie przekroczylo.

        JEDEN nosnik odpowiedzi „o ile" (v1.17). `przekroczony_plan` mowi
        TYLKO „czy", a ekran musi powiedziec „o ile" — bez tego pola kazdy
        wolajacy odejmowalby sam i pierwsza pomylka w znaku byla by niewidoczna.
        Liczone z tych samych dwoch pol co `przekroczony_plan`, wiec te dwie
        odpowiedzi nie moga sie rozjechac.
        """
        return max(self.zaplacone - self.zaplanowane, Decimal("0.00"))


def pozostalo_do_zaplacenia(wpisy: pd.DataFrame, plan: pd.DataFrame,
                            miesiace: list[tuple[int, int]],
                            rezerwa: Decimal) -> DoZaplacenia:
    """Plan wydatkow minus to, co juz zaplacone, plus rezerwa podatkowa.

    Maleje z kazda wprowadzona transakcja — jak kolumna „Remaining"
    w arkuszu zrodlowym. Podatki wchodza tu SALDEM rezerwy i znikaja z niej
    same, gdy dania zostanie zaplacona przyciskiem „Zaplacone" (ten zapisuje
    wpis w kategorii `KATEGORIA_PODATKI`, ktora czesc planowa wyklucza).
    """
    zaplanowane = Decimal("0.00")
    zaplacone = Decimal("0.00")
    for rok, miesiac in miesiace:
        wybrany = bez_podatkow(_plan_miesiaca(plan, rok, miesiac))
        if not wybrany.empty:
            for _, w in wybrany[wybrany["typ"] == TYP_WYDATKI].iterrows():
                zaplanowane += Decimal(str(w["kwota_planowana"]))
        biezace = bez_podatkow(_miesiac(wpisy, rok, miesiac))
        if not biezace.empty:
            for _, w in biezace[biezace["typ"] == TYP_WYDATKI].iterrows():
                zaplacone += Decimal(str(w["kwota"]))
    rezerwa = Decimal(str(rezerwa))
    return DoZaplacenia(
        zaplanowane=stawki.do_groszy(zaplanowane),
        zaplacone=stawki.do_groszy(zaplacone),
        podatki=stawki.do_groszy(rezerwa),
        pozostalo=stawki.do_groszy(zaplanowane - zaplacone + rezerwa),
        przekroczony_plan=zaplacone > zaplanowane,
    )


@dataclass(frozen=True)
class PostepCelu:
    """Stan jednego celu oszczędnościowego, policzony z REALNYCH wpisów.

    `uzbierane` to suma wpisów typu „Oszczędności" w kategorii celu — nigdy
    liczba wpisana ręcznie. Pasek postępu napędzany ręczną liczbą pokazuje to,
    co użytkownik wpisał, a nie to, co faktycznie ma; czyli dokładnie odwrotnie,
    niż obiecuje.
    """

    nazwa: str
    kategoria: str
    kwota_docelowa: Decimal
    uzbierane: Decimal
    procent: Decimal
    brakuje: Decimal
    termin: date
    miesiecy_do_terminu: int
    tempo_miesieczne: Decimal | None
    osiagniety: bool
    po_terminie: bool


def _miesiecy_miedzy(od: date, do: date) -> int:
    """Pełne miesiące od `od` do `do`; nigdy mniej niż zero."""
    roznica = (do.year - od.year) * 12 + (do.month - od.month)
    if do.day < od.day:
        roznica -= 1
    return max(roznica, 0)


def postep_celu(wpisy: pd.DataFrame, *, nazwa: str, kategoria: str,
                kwota_docelowa: Decimal, termin: date,
                dzis: date | None = None) -> PostepCelu:
    """Postęp celu liczony wyłącznie z wpisów oszczędnościowych jego kategorii.

    `dzis` jest parametrem, nie odczytem zegara w środku: funkcja liczy zawsze
    to samo dla tych samych danych, więc da się ją sprawdzić bez podmieniania
    czasu systemowego.
    """
    dzis = dzis or date.today()
    kwota_docelowa = stawki.do_groszy(kwota_docelowa)

    uzbierane = Decimal("0.00")
    if not wpisy.empty:
        wybrane = wpisy[(wpisy["typ"] == TYP_OSZCZEDNOSCI)
                        & (wpisy["kategoria"] == kategoria)]["kwota"]
        uzbierane = stawki.do_groszy(
            sum((Decimal(str(k)) for k in wybrane), Decimal("0.00")))

    procent = (Decimal("0.0") if kwota_docelowa == 0
               else _procent(uzbierane / kwota_docelowa * 100))
    brakuje = stawki.do_groszy(max(kwota_docelowa - uzbierane, Decimal("0.00")))
    miesiecy = _miesiecy_miedzy(dzis, termin)
    # Cel bez tempa jest życzeniem. Ta liczba mówi wprost, czy termin jest realny.
    tempo = (stawki.do_groszy(brakuje / miesiecy)
             if miesiecy > 0 and brakuje > 0 else None)

    return PostepCelu(
        nazwa=nazwa, kategoria=kategoria, kwota_docelowa=kwota_docelowa,
        uzbierane=uzbierane, procent=procent, brakuje=brakuje, termin=termin,
        miesiecy_do_terminu=miesiecy, tempo_miesieczne=tempo,
        osiagniety=uzbierane >= kwota_docelowa, po_terminie=termin < dzis,
    )


def wydatki_wg_kategorii(wpisy: pd.DataFrame, rok: int,
                        miesiac: int) -> list[tuple[str, Decimal]]:
    """Sumy wydatków per kategoria w danym miesiącu, od największej.

    Wyłącznie typ „Wydatki". Przychód albo oszczędność na wykresie wydatków to
    nie ozdoba, tylko kłamstwo o tym, na co poszły pieniądze.

    Wykres pierścieniowy myli cicho: brakująca kategoria po prostu nie ma
    wycinka i nikt nie zauważy, że suma udziałów rozjechała się z sumą wpisów.
    Dlatego ta funkcja nie odrzuca ani nie zaokrągla niczego po drodze.
    """
    biezace = _miesiac(wpisy, rok, miesiac)
    if biezace.empty:
        return []
    wydatki = biezace[biezace["typ"] == TYP_WYDATKI]
    if wydatki.empty:
        return []
    sumy: dict[str, Decimal] = {}
    for _, w in wydatki.iterrows():
        sumy[w["kategoria"]] = sumy.get(w["kategoria"], Decimal("0.00")) \
            + Decimal(str(w["kwota"]))
    return sorted(((k, stawki.do_groszy(v)) for k, v in sumy.items()),
                  key=lambda pozycja: (-pozycja[1], pozycja[0]))


@dataclass(frozen=True)
class Okres:
    """Zakres miesiecy, po ktorym liczy sie kazdy podglad.

    Pojedynczy miesiac jest tu przypadkiem jednoelementowym, nie osobnym
    trybem — inaczej ta sama regula sumowania mialaby dwa nosniki.
    """

    od: tuple[int, int]
    do: tuple[int, int]

    def miesiace(self) -> list[tuple[int, int]]:
        """Miesiace od `od` do `do` wlacznie, rosnaco.

        Liczone na osi absolutnej `rok * 12 + miesiac`, dokladnie jak
        `ostatnie_miesiace`: odejmowanie samego numeru miesiaca daje przy
        przejsciu przez Nowy Rok zero i liczby ujemne, czyli miesiace,
        ktorych nie ma.
        """
        poczatek = self.od[0] * 12 + (self.od[1] - 1)
        koniec = self.do[0] * 12 + (self.do[1] - 1)
        if koniec < poczatek:
            raise ValueError(
                f"Okres kończy się przed początkiem: {self.od} … {self.do}. "
                "Pusta lista wyglądałaby jak miesiąc bez danych.")
        return [(punkt // 12, punkt % 12 + 1)
                for punkt in range(poczatek, koniec + 1)]


def ostatnie_miesiace(rok: int, miesiac: int, ile: int) -> list[tuple[int, int]]:
    """`ile` kolejnych miesięcy kończąc na podanym, od najstarszego.

    Odejmowanie samego numeru miesiąca daje przy przejściu przez Nowy Rok
    zero i liczby ujemne — miesiące, których nie ma. Liczymy więc na osi
    absolutnej: rok × 12 + miesiąc.
    """
    if ile < 1:
        return []
    koniec = rok * 12 + (miesiac - 1)
    return [((koniec - przesuniecie) // 12, (koniec - przesuniecie) % 12 + 1)
            for przesuniecie in range(ile - 1, -1, -1)]


def sumy_miesieczne(wpisy: pd.DataFrame,
                    miesiace: list[tuple[int, int]]) -> dict:
    """Sumy per typ dla każdego z podanych miesięcy.

    Miesiąc bez danych dostaje zera, a nie znika ze słownika. Brak klucza
    znaczyłby brak słupka, a brak słupka wygląda na wykresie identycznie jak
    słupek zerowy — tyle że przesuwa oś czasu i przekłamuje trend.
    """
    wynik = {}
    for rok, miesiac in miesiace:
        biezace = _miesiac(wpisy, rok, miesiac)
        pozycja = {typ: Decimal("0.00") for typ in TYPY}
        if not biezace.empty:
            for typ in TYPY:
                wybrane = biezace[biezace["typ"] == typ]["kwota"]
                pozycja[typ] = stawki.do_groszy(
                    sum((Decimal(str(k)) for k in wybrane), Decimal("0.00")))
        wynik[(rok, miesiac)] = pozycja
    return wynik


def _pozycje_z_sum(planowane: dict, wykonane: dict) -> list[Wykonanie]:
    """Jedyny nosnik wyprowadzania pol pochodnych zestawienia.

    Wersja miesieczna i okresowa roznia sie WYLACZNIE tym, jak zbieraja sumy;
    to, co z sum wynika, ma jedno miejsce.
    """
    pozycje = []
    for typ, kategoria in sorted(set(wykonane) | set(planowane),
                                 key=lambda k: (TYPY.index(k[0]), k[1])):
        p = stawki.do_groszy(planowane.get((typ, kategoria), Decimal("0.00")))
        w = stawki.do_groszy(wykonane.get((typ, kategoria), Decimal("0.00")))
        procent = None if p == 0 else _procent(w / p * 100)
        pozycje.append(Wykonanie(
            typ=typ, kategoria=kategoria, planowane=p, wykonane=w,
            procent=procent, pozostalo=stawki.do_groszy(p - w),
            przekroczone=w > p,
        ))
    return pozycje


def wykonanie_planu(wpisy: pd.DataFrame, plan: pd.DataFrame,
                    rok: int, miesiac: int) -> list[Wykonanie]:
    """Zestawienie plan kontra wykonanie dla JEDNEGO miesiaca.

    Plan rozwija `plan_na_miesiac` — ta funkcja NIE filtruje sama, bo wlasny
    filtr byl drugim nosnikiem reguly i po Z42 nie widzialby pozycji trwalej
    zaczetej wczesniej. Sumowanie planu rocznie zanizyloby procent
    dwunastokrotnie i pokazywalo miesczenie sie w budzecie tam, gdzie go nie ma.

    Na liscie sa pary (typ, kategoria) z OBU zrodel: kategoria zaplanowana
    i nietknieta to informacja, nie brak danych.
    """
    biezace = _miesiac(wpisy, rok, miesiac)

    wykonane: dict[tuple[str, str], Decimal] = {}
    if not biezace.empty:
        for _, w in biezace.iterrows():
            klucz = (w["typ"], w["kategoria"])
            wykonane[klucz] = wykonane.get(klucz, Decimal("0.00")) \
                + Decimal(str(w["kwota"]))

    planowane: dict[tuple[str, str], Decimal] = {}
    if not plan.empty:
        wybrany = plan_na_miesiac(plan, rok, miesiac)
        for _, w in wybrany.iterrows():
            klucz = (w["typ"], w["kategoria"])
            planowane[klucz] = planowane.get(klucz, Decimal("0.00")) \
                + Decimal(str(w["kwota_planowana"]))

    return _pozycje_z_sum(planowane, wykonane)


def wykonanie_typu(wpisy: pd.DataFrame, plan: pd.DataFrame,
                   rok: int, miesiac: int, typ: str) -> Wykonanie:
    """Plan kontra wykonanie dla CALEGO typu w miesiacu — jedna pozycja.

    Powstalo w Z6 dla trzeciego wiersza karty „Co ruszy ten wpis"
    („Plan wydatkow wykonany: 0,0% -> 10,5%"). Ten wiersz mowi o CALYM planie
    wydatkow miesiaca, nie o planie jednej kategorii — a `wykonanie_planu`
    rozbija zestawienie na pary (typ, kategoria) i sumy typu nie zwraca.

    ANI JEDNEJ WLASNEJ LICZBY. Sumy zbieraja istniejace nosniki (`sumy_planu`,
    `sumy_miesieczne`), a pola pochodne — procent, pozostalo, przekroczone —
    liczy ten sam `_pozycje_z_sum` co obie wersje zestawienia. Wlasny rachunek
    `wykonane / planowane * 100` bylby DRUGIM NOSNIKIEM reguly procentu
    i rozjechalby sie przy pierwszej zmianie zaokraglenia.

    `kategoria` w wyniku jest pusta: to jest pozycja o typie, nie o kategorii.
    """
    if typ not in TYPY:
        raise ValueError(
            f"Nieznany typ wpisu: {typ}. Dozwolone sa wylacznie: "
            + ", ".join(TYPY) + ".")
    planowane = {(typ, ""): sumy_planu(plan, rok, miesiac)[typ]}
    wykonane = {(typ, ""): sumy_miesieczne(wpisy, [(rok, miesiac)])[
        (rok, miesiac)][typ]}
    return _pozycje_z_sum(planowane, wykonane)[0]


def wykonanie_planu_okres(wpisy: pd.DataFrame, plan: pd.DataFrame,
                          miesiace: list[tuple[int, int]]) -> list[Wykonanie]:
    """Zestawienie plan kontra wykonanie dla CALEGO okresu.

    Sumuje po miesiacach, a pola pochodne liczy tym samym pomocnikiem co
    wersja miesieczna. Procent liczy sie od sumy planu okresu, nie od sredniej
    miesiecznej — srednia zaklamywalaby miesiac, w ktorym planu nie bylo.
    """
    planowane: dict[tuple[str, str], Decimal] = {}
    wykonane: dict[tuple[str, str], Decimal] = {}
    for rok, miesiac in miesiace:
        biezace = _miesiac(wpisy, rok, miesiac)
        if not biezace.empty:
            for _, w in biezace.iterrows():
                klucz = (w["typ"], w["kategoria"])
                wykonane[klucz] = wykonane.get(klucz, Decimal("0.00")) \
                    + Decimal(str(w["kwota"]))
        wybrany = _plan_miesiaca(plan, rok, miesiac)
        if not wybrany.empty:
            for _, w in wybrany.iterrows():
                klucz = (w["typ"], w["kategoria"])
                planowane[klucz] = planowane.get(klucz, Decimal("0.00")) \
                    + Decimal(str(w["kwota_planowana"]))
    return _pozycje_z_sum(planowane, wykonane)


def wydatki_wg_kategorii_okres(
        wpisy: pd.DataFrame,
        miesiace: list[tuple[int, int]]) -> list[tuple[str, Decimal]]:
    """Sumy wydatkow per kategoria w calym okresie, od najwiekszej.

    Nic po drodze nie jest odrzucane ani zaokraglane — wykres pierscieniowy
    myli cicho, bo brakujaca kategoria po prostu nie ma wycinka.
    """
    sumy: dict[str, Decimal] = {}
    for rok, miesiac in miesiace:
        for kategoria, kwota in wydatki_wg_kategorii(wpisy, rok, miesiac):
            sumy[kategoria] = sumy.get(kategoria, Decimal("0.00")) + kwota
    return sorted(((k, stawki.do_groszy(v)) for k, v in sumy.items()),
                  key=lambda pozycja: (-pozycja[1], pozycja[0]))

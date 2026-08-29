# -*- coding: utf-8 -*-
"""SKLADANIE ODPOWIEDZI EKRANU KSIEGOWANIE. Ksztalt bierze z `kontrakt.py`.

DLACZEGO TEN PLIK ISTNIEJE, A TRASA NIE ROBI TEGO SAMA. Zadanie Z6 ma dwie
zasady twarde i ta druga brzmi: **zero rachunku w trasie**. Ekran Ksiegowania
potrzebuje jednak rzeczy, ktorych silnik dotad nie liczyl — kolejnosci
kategorii, licznika wpisow w miesiacu i karty „Co ruszy ten wpis". Kazda z nich
jest REGULA o konsekwencji zewnetrznej: decyduje o tym, co czlowiek zobaczy.
Policzona w warstwie sieciowej mialaby tylu nosnikow, ile tras ja wola.

DLACZEGO NAPIS KWOTY WCHODZI ARGUMENTEM, A NIE IMPORTEM. Zamiana `Decimal`
na napis ma w tym projekcie JEDEN nosnik i jest nim `api/kwoty.py`, ktory stoi
na `fastapi`. Silnik nie ma prawa wiedziec, ze HTTP istnieje (straznik:
`testy/test_granice.py::test_silnik_nie_wie_o_istnieniu_HTTP`), wiec funkcji
zamieniajacej nie moze zaimportowac — dostaje ja od wolajacego. Skutek jest
dokladnie ten zamierzony: zaokraglenie do groszy zapada RAZ, w `kwoty.kwota()`,
a ten plik go nie powtarza.

BEZ WARTOSCI DOMYSLNEJ DLA `napis_kwoty` — swiadomie, dokladnie tak jak forma
opodatkowania nie ma wartosci domyslnej (`testy/test_forma_bez_domyslnej.py`).
Domyslne `str` bylo by drugim nosnikiem konwersji, cichym i poprawnym
w dziewieciu przypadkach na dziesiec.

CZEGO TU NIE MA: ani jednej stawki (CLAUDE.md §3.3) i ani jednego odczytu
bazy poza `zbierz` — funkcje rachunkowe biora ramki danych argumentem, zeby
dalo sie je sprawdzic bez bazy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

import pandas as pd

from silnik import kontrakt
from silnik.rdzen import budzet, magazyn, prezentacja
from silnik.rdzen import prognoza_plynnosci as pp

#: Funkcja zamieniajaca kwote na napis kontraktu. W produkcji `api.kwoty.kwota`.
NapisKwoty = Callable[..., "str | None"]

#: Typ, ktory przelacznik pokazuje po wejsciu na ekran (§41.4 poz. 1).
#: 88,7% wpisow to wydatki — domyslna pozycja zdejmuje jedno klikniecie
#: z trzech, ktore sa bramka tego ekranu.
TYP_DOMYSLNY = budzet.TYP_WYDATKI

#: Ile ostatnich wpisow niesie ekran (§41.4 poz. 11).
ILE_OSTATNICH_WPISOW = 6

#: Kategoria kosztu firmowego NIE STOI na tym ekranie (D-24): koszt firmowy
#: ma jedno miejsce — ekran Firma, razem z VAT-em i numerem dokumentu.
#: Wolane, nie przepisane: nazwa zyje w `budzet.KATEGORIA_KOSZTY_JDG`.
KATEGORIE_POZA_EKRANEM = (budzet.KATEGORIA_KOSZTY_JDG,)

#: Czwarty wiersz karty „Co ruszy ten wpis" — jedyny, ktory mowi, co sie NIE
#: ruszylo. Brzmienia stoja tutaj, bo `WierszSkutku.etykieta` i `.wyjasnienie`
#: przechodza granice HTTP jako DANE: przegladarka je pokazuje, nie sklada.
ETYKIETA_WOLNYCH_SRODKOW = "Wolne środki"
WYJASNIENIE_WOLNYCH_SRODKOW = "bez zmian — liczą się z planu, nie z wpisów"

#: PIATY wiersz — „Plynnosc" (D-62). Brzmienia stoja OBOK siostrzanego
#: „Wolne srodki", bo obie odpowiadaja na to samo pytanie: co ten wpis robi
#: z liczba, ktorej uzytkownik na tej karcie NIE WIDZI.
#:
#: DLACZEGO TEN WIERSZ MUSIAL POWSTAC. Po D-20/D-61 wpis miesczacy sie
#: w planie NIE ZMIENIA sumy prognozy — konsumuje pozycje planu, ktora i tak
#: mial zaplacic. Karta bez tego wiersza milczala, wiec uzytkownik nie mial
#: jak odroznic POPRAWNEGO DZIALANIA od AWARII: wpisal 274,06 zl, Plynnosc
#: pokazala te sama liczbe, i to wyglada identycznie jak zepsuty zapis.
#:
#: KAZDE Z TYCH BRZMIEN NIESIE WIELKOSC, nie samo slowo (CLAUDE.md §3.5):
#: „bez zmian" bez liczby jest tym samym, czym byla cisza.
ETYKIETA_PLYNNOSCI = "Płynność"

#: Trzeci wiersz, gdy planu na ten miesiac nie ma. `po=None` znaczy „ta liczba
#: sie nie zmienia" — i wtedy wyjasnienie mowi dlaczego. Zero procent
#: klamaloby, ze wydatek zmiescil sie w budzecie (`budzet.Wykonanie` §procent).
WYJASNIENIE_BEZ_PLANU = "planu na ten miesiąc nie ma — nie ma czego wykonać"

#: Dwa stany, ktore moze zwrocic `rozstrzygnij_kwote`.
STAN_PRZYJETA = "przyjeta"
STAN_PYTANIE_O_MINUS = "pytanie_o_minus"

#: Znaki minusa, ktore moga przyjsc z pola tekstowego: dywiz ASCII i minus
#: typograficzny U+2212 (ten drugi wstawia `interfejs/lib/kwota.ts`, wiec
#: wraca do nas wtedy, gdy uzytkownik nie wyczyscil sformatowanej kwoty).
ZNAKI_MINUSA = ("-", "−")


@dataclass(frozen=True, slots=True)
class Rozstrzygniecie:
    """Co zrobic z kwota, ktora przyszla z ekranu.

    NIE JEST TO BLAD I NIE JEST TO ZGODA. Kwota ujemna w polu znaczy, ze
    uzytkownik powiedzial prawde w zlym jezyku: minus jest juz w typie wpisu.
    Zapisanie wartosci bezwzglednej po cichu byloby interfejsem, ktory
    poprawia liczby uzytkownika bez jego wiedzy; odmowa z komunikatem bledu
    kazalaby mu poprawiac cos, co dla niego bylo poprawne. Zostaje trzecie:
    PYTANIE z kwota, ktora zapiszemy, jesli potwierdzi.

    `kwota` jest ZAWSZE dodatnia — takze w stanie pytania. To jest ta sama
    liczba, ktora pojdzie do bazy po potwierdzeniu, wiec ekran ma ja pokazac
    w pytaniu doslownie, a nie skladac wlasna.
    """

    stan: str
    kwota: Decimal
    typ: str


def rozstrzygnij_kwote(surowa, typ: str, *,
                       potwierdzone: bool = False) -> Rozstrzygniecie:
    """JEDEN NOSNIK reguly „minus jest juz w typie wpisu" (§41.5 przypadek d).

    Wolaja to dwie trasy — zapis i podglad — i obie musza odpowiedziec tak
    samo. Regula policzona w kazdej z nich osobno rozjechalaby sie przy
    pierwszej zmianie: podglad pokazywalby skutek kwoty, ktorej zapis nie
    przyjmuje.

    `potwierdzone=True` to odpowiedz „Tak, zapisz" na pytanie z poprzedniego
    zadania. Wtedy — i tylko wtedy — minus schodzi bez pytania.
    """
    tekst = str(surowa).strip()
    ujemna = tekst.startswith(ZNAKI_MINUSA)
    for znak in ZNAKI_MINUSA:
        tekst = tekst.lstrip(znak) if tekst.startswith(znak) else tekst
    kwota = Decimal(tekst)
    if ujemna and not potwierdzone:
        return Rozstrzygniecie(stan=STAN_PYTANIE_O_MINUS, kwota=kwota, typ=typ)
    return Rozstrzygniecie(stan=STAN_PRZYJETA, kwota=kwota, typ=typ)


# --- kolejnosc kategorii --------------------------------------------------

def _liczba_wpisow(wpisy: pd.DataFrame, typ: str) -> dict[str, int]:
    """Ile razy uzyto kazdej kategorii danego typu. Liczy WIERSZE, nie kwoty."""
    if wpisy.empty:
        return {}
    wybrane = wpisy[wpisy["typ"] == typ]
    if wybrane.empty:
        return {}
    return {str(k): int(v)
            for k, v in wybrane["kategoria"].value_counts().items()}


def _kategorie_planu(plan: pd.DataFrame, rok: int, miesiac: int,
                     typ: str) -> set[str]:
    """Kategorie, ktore maja pozycje planu w tym miesiacu. Wola jedyny nosnik
    reguly „ktore pozycje obowiazuja w miesiacu M" (`budzet.plan_na_miesiac`)."""
    if plan.empty:
        return set()
    wybrany = budzet.plan_na_miesiac(plan, rok, miesiac)
    if wybrany.empty:
        return set()
    return {str(w["kategoria"]) for _, w in wybrany.iterrows()
            if w["typ"] == typ}


def kolejnosc_kategorii(nazwy, *, wpisy: pd.DataFrame, plan: pd.DataFrame,
                        typ: str, rok: int, miesiac: int) -> tuple[str, ...]:
    """JEDEN NOSNIK reguly kolejnosci kafelkow kategorii.

    Klucz sortowania ma trzy czlony i to JEDNA regula, nie dwie:

        (-ile razy uzyta, -czy jest w planie tego miesiaca, nazwa)

    Przy pustej historii pierwszy czlon jest staly dla wszystkich kategorii
    i regula sama zwija sie do „najpierw pozycje planu, potem alfabetycznie" —
    dokladnie to, co pokazuje ramka. Osobna galaz „jesli nie ma wpisow"
    bylaby DRUGIM NOSNIKIEM tej samej kolejnosci i rozjechalaby sie przy
    pierwszym wpisie.

    Alfabetycznie znaczy po polsku: `Ą` stoi po `A`, nie po `Z`. Sortowanie
    po surowych punktach kodowych stawia `Środki` za `Zakupy`.
    """
    liczba = _liczba_wpisow(wpisy, typ)
    z_planu = _kategorie_planu(plan, rok, miesiac, typ)

    def klucz(nazwa: str):
        return (-liczba.get(nazwa, 0), 0 if nazwa in z_planu else 1,
                _alfabetycznie(nazwa))

    return tuple(sorted(nazwy, key=klucz))


#: Litery polskie sprowadzone do liter bazowych — do porownywania nazw.
#: `locale.strcoll` wymagalby ustawionej lokalizacji systemowej, a ta bywa
#: rozna na laptopie i w przebiegu testow: sortowanie zalezne od srodowiska
#: dawaloby dwie rozne kolejnosci tego samego pasma kategorii.
_BEZ_OGONKOW = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def _alfabetycznie(nazwa: str) -> tuple[str, str]:
    """Klucz porzadku polskiego: najpierw bez ogonkow, potem oryginal.

    Drugi czlon rozstrzyga remisy („Los" przed „Łos"), zeby dwie rozne nazwy
    nigdy nie mialy identycznego klucza — inaczej kolejnosc miedzy nimi
    zalezalaby od kolejnosci wejscia, czyli od bazy.
    """
    obnizona = nazwa.casefold()
    return (obnizona.translate(_BEZ_OGONKOW), obnizona)


def uzasadnienie_kolejnosci(*, wpisow: int, z_planu: int, rok: int,
                            miesiac: int, nazwa_miesiaca: str) -> str:
    """Zdanie pod pasmem kategorii — mowi, SKAD ta kolejnosc.

    Bez niego pasmo jest lista bez porzadku, a uzytkownik szuka kategorii
    wzrokiem zamiast siegnac po nia z pamieci. Zdanie ma dwa brzmienia, bo
    regula ma dwa stany: policzona z historii i jeszcze niepoliczona.
    """
    if wpisow:
        return (f"Kolejność liczy się z częstości wpisów — {wpisow} "
                f"{'wpis' if wpisow == 1 else 'wpisów'} w "
                f"{nazwa_miesiaca}, remisy alfabetycznie.")
    if z_planu:
        return (f"Kolejność ma się liczyć z częstości wpisów, a tych jeszcze "
                f"nie ma — więc na początku {'stoi' if z_planu == 1 else 'stoją'} "
                f"{prezentacja.odmien_kategorie(z_planu)} z planu na "
                f"{prezentacja.MIESIACE[miesiac - 1]} {rok}, dalej "
                f"alfabetycznie. Przeliczy się sama, gdy wpisy będą.")
    return ("Kolejność ma się liczyć z częstości wpisów, a tych jeszcze nie "
            f"ma — planu na {prezentacja.MIESIACE[miesiac - 1]} {rok} też "
            "nie ma, więc kategorie stoją alfabetycznie. Przeliczy się sama, "
            "gdy wpisy będą.")


# --- karta „Co ruszy ten wpis" -------------------------------------------

def _wykonane_kategorii(wpisy: pd.DataFrame, plan: pd.DataFrame, rok: int,
                        miesiac: int, typ: str, kategoria: str) -> Decimal:
    """Ile juz wydano w tej kategorii w tym miesiacu. WOLA zestawienie planu,
    nie sumuje samo — inaczej ta sama suma powstawalaby dwa razy."""
    for pozycja in budzet.wykonanie_planu(wpisy, plan, rok, miesiac):
        if pozycja.typ == typ and pozycja.kategoria == kategoria:
            return pozycja.wykonane
    return Decimal("0.00")


def wyjasnienie_plynnosci(skutek: "pp.SkutekNaOs", *, dzien: date) -> str:
    """JEDEN NOSNIK brzmien wiersza „Plynnosc" — piec stanow, kazdy z wielkoscia.

    Stany sa PIEC, nie trzy, i dwa dolozone nie sa ozdoba:

    * `poza_osia` — kategoria, ktorej wpisy silnik liczy z innego zrodla
      (daniny z faktur, przychod JDG z godzin). Wpis w niej naprawde nie
      rusza osi, ale z zupelnie innego powodu niz brak planu — zlanie tych
      dwoch stanow w jedno zdanie mowiloby, ze kategoria „nie ma pozycji
      planu", podczas gdy ona po prostu nie nalezy do tej osi;
    * kwota zerowa — karta na wejsciu, zanim uzytkownik cokolwiek wpisal.
      Zdanie „niżej o 0,00 zl" byloby tu falszywym alarmem.

    DLACZEGO ZDANIE NIE MOWI „cala pozycja przesuwa sie na dzis". Bo sie nie
    przesuwa. Wpis 274,06 zl z pozycji 330,00 zl zostawia 55,94 zl na dniu
    tej pozycji (D-61: konsumpcja idzie AZ DO ZERA, nie caloscia). Reszta
    jest w zdaniu wymieniona z kwota i z data — inaczej nastepny czytelnik
    zobaczylby na Plynnosci wyplyw, o ktorym karta powiedziala, ze zniknal.

    OBIE DATY POCHODZA Z DANYCH, zadna nie jest wzorcem tekstowym: dzien
    pozycji z `skutek.data_pozycji`, dzien wpisu z argumentu.
    """
    if skutek.poza_osia:
        return ("bez zmian — daniny i przychód z faktur liczy silnik "
                "z własnych źródeł, nie z wpisów")
    if skutek.roznica == 0 and skutek.pochloniete == 0:
        return "bez zmian — dopóki nie wpiszesz kwoty, nie ma czego przeliczyć"

    kierunek = ("niżej" if skutek.roznica < 0 else "wyżej")
    wielkosc = prezentacja.zloty(abs(skutek.roznica))

    if skutek.pochloniete == 0:
        return (f"{kierunek} o {wielkosc} — kategoria nie ma pozycji planu "
                f"na ten miesiąc")

    kiedy_plan = _slownie(skutek.data_pozycji)
    if skutek.roznica != 0:
        return (f"{kierunek} o {wielkosc} — o tyle wydatek przekracza "
                f"pozycję planu {prezentacja.zloty(skutek.kwota_pozycji)} "
                f"z {kiedy_plan}")

    ogon = (f"; zostaje z niej {prezentacja.zloty(skutek.reszta_pozycji)} "
            f"na {kiedy_plan}" if skutek.reszta_pozycji > 0
            else "; pozycja schodzi z osi w całości")
    return (f"bez zmian co do sumy — {prezentacja.zloty(skutek.pochloniete)} "
            f"wchodzi na {_slownie(dzien)} w miejsce pozycji planu "
            f"{prezentacja.zloty(skutek.kwota_pozycji)} z {kiedy_plan}{ogon}")


def _slownie(dzien: date) -> str:
    """„20 października" — dzien i miesiac w dopelniaczu.

    Ten sam zapis, ktorym zdania serwera mowia o datach gdzie indziej
    (`ekran_plynnosc.zdanie_werdyktu`). Zapis rzymski z ramki („20 X")
    sklada `interfejs/lib/kwota.ts` i robi to dla dat, ktore dostaje POLEM;
    tutaj data siedzi WEWNATRZ zdania, wiec sklada ja ta strona granicy.
    """
    return f"{dzien.day} {prezentacja.MIESIACE_DOPELNIACZ[dzien.month - 1]}"


def podglad(*, wpisy: pd.DataFrame, plan: pd.DataFrame, typ: str,
            kategoria: str, kwota: Decimal, dzien: date, dzis: date,
            napis_kwoty: NapisKwoty) -> kontrakt.PodgladSkutku:
    """„Co ruszy ten wpis" — PIEC wierszy, dwa ostatnie mowia, co sie NIE ruszylo.

    Czwarty i piaty wiersz nie sa wypelniaczem do rownej liczby. Sa jedynym
    miejscem, w ktorym uzytkownik dowiaduje sie, czego wpis NIE dotknal —
    bez nich szukalby ruchu, ktorego nie ma, i uznalby jego brak za wade
    obliczen.

    * WOLNE SRODKI licza sie z planu, a nie z wpisow (budzet zerowy:
      pieniadz przestaje byc do dyspozycji w chwili WPISANIA go w plan, nie
      w chwili zaplaty — `budzet.do_alokacji_z_planu`);
    * PLYNNOSC (D-62) po D-20/D-61 czesto NIE ZMIENIA sumy, bo wpis
      konsumuje pozycje planu, ktora i tak miala byc zaplacona. Milczenie
      karty w tym stanie jest nieodroznialne od awarii zapisu — dlatego
      wiersz stoi ZAWSZE i ZAWSZE niesie wielkosc.

    ANI JEDNEJ KWOTY POLICZONEJ TU OD ZERA. Sumy przychodza z `budzet`,
    formatowanie z `prezentacja`, zamiana na napis kontraktu z `napis_kwoty`.
    Jedyna arytmetyka to `przed + kwota` — czyli to, co ta karta OBIECUJE
    pokazac.
    """
    rok, miesiac = dzien.year, dzien.month
    nazwa_miesiaca = prezentacja.MIESIACE_MIEJSCOWNIK[miesiac - 1]

    typu = budzet.wykonanie_typu(wpisy, plan, rok, miesiac, typ)
    kategorii = _wykonane_kategorii(wpisy, plan, rok, miesiac, typ, kategoria)

    wiersze = [
        kontrakt.WierszSkutku(
            etykieta=f"{typ} w {nazwa_miesiaca}",
            przed=prezentacja.liczba(typu.wykonane),
            po=prezentacja.zloty(typu.wykonane + kwota)),
        kontrakt.WierszSkutku(
            etykieta=kategoria,
            przed=prezentacja.liczba(kategorii),
            po=prezentacja.zloty(kategorii + kwota)),
    ]

    tytul_planu = prezentacja.TYTUL_PLANU_WYKONANEGO[typ]
    if typu.planowane == 0:
        wiersze.append(kontrakt.WierszSkutku(
            etykieta=tytul_planu, przed="", po=None,
            wyjasnienie=WYJASNIENIE_BEZ_PLANU))
    else:
        po_wpisie = budzet.wykonanie_typu(
            _z_dolozonym_wpisem(wpisy, dzien=dzien, typ=typ,
                                kategoria=kategoria, kwota=kwota),
            plan, rok, miesiac, typ)
        wiersze.append(kontrakt.WierszSkutku(
            etykieta=tytul_planu,
            przed=prezentacja.procent_wykonania(typu.procent),
            po=prezentacja.procent_wykonania(po_wpisie.procent)))

    wiersze.append(kontrakt.WierszSkutku(
        etykieta=ETYKIETA_WOLNYCH_SRODKOW, przed="", po=None,
        wyjasnienie=WYJASNIENIE_WOLNYCH_SRODKOW))

    # Wielkosc liczy `podziel_os` — TEN SAM nosnik, ktory rysuje Plynnosc.
    # Wlasny rachunek „kwota minus plan" zgadzalby sie do pierwszej zmiany
    # D-61 i rozjechal cicho: karta obiecywalaby ruch inny niz ekran.
    wiersze.append(kontrakt.WierszSkutku(
        etykieta=ETYKIETA_PLYNNOSCI, przed="", po=None,
        wyjasnienie=wyjasnienie_plynnosci(
            pp.skutek_wpisu_na_os(
                plan=plan, wpisy=wpisy, typ=typ, kategoria=kategoria,
                kwota=kwota, dzien=dzien, dzis=dzis),
            dzien=dzien)))

    return kontrakt.PodgladSkutku(kwota=napis_kwoty(kwota),
                                  wiersze=tuple(wiersze))


def _z_dolozonym_wpisem(wpisy: pd.DataFrame, *, dzien: date, typ: str,
                        kategoria: str, kwota: Decimal) -> pd.DataFrame:
    """Ramka wpisow POWIEKSZONA o wpis, ktorego jeszcze nie ma w bazie.

    Procent po wpisie liczy sie tym SAMYM `budzet.wykonanie_typu` co procent
    przed nim — na danych z dolozonym wierszem. Wlasny rachunek
    `(wykonane + kwota) / planowane * 100` bylby drugim nosnikiem reguly
    procentu i zaokraglalby inaczej niz pierwszy.

    NIE DOTYKA BAZY i nie modyfikuje wejscia — `concat` zwraca nowa ramke.
    """
    nowy = pd.DataFrame([{
        "data": dzien.isoformat(), "typ": typ, "kategoria": kategoria,
        "kwota": str(kwota), "szczegoly": ""}])
    if wpisy.empty:
        return nowy
    return pd.concat([wpisy, nowy], ignore_index=True)


# --- caly ekran -----------------------------------------------------------

def _podpis_straznika(polaczenie, dzis: date) -> "str | None":
    """Zdanie stopki albo `None`, gdy straznik nigdy nie dzialal.

    `None` znaczy „nigdy nie sprawdzal" i NIE WOLNO go zamienic na zdanie
    o sprawdzeniu (regula D11: zero nigdy nie zastepuje braku wiedzy).
    """
    przebieg = magazyn.ostatni_przebieg_straznika(polaczenie)
    if przebieg is None:
        return None
    return prezentacja.podpis_straznika(przebieg, dzis)


def zbierz(polaczenie, *, dzis: date, napis_kwoty: NapisKwoty,
           typ: str = TYP_DOMYSLNY,
           kwota_podgladu: Decimal = Decimal("0.00"),
           kategoria_podgladu: "str | None" = None) -> kontrakt.DaneKsiegowania:
    """Cienki zbieracz: czyta baze przez ISTNIEJACE nosniki, sklada ksztalt.

    Ani jednego wlasnego zapytania SQL — `magazyn` juz wie, co odczytac.
    Wzorzec ten sam co `prognoza_plynnosci.prognozuj` i `co_mnie_czeka.zestaw`,
    i z tego samego powodu: kazde powtorzenie odczytu to kolejna okazja, zeby
    jedno z nich podalo silnikowi co innego (zmierzone u poprzednika
    2026-08-26: ekran mowil -6 098,11 zl, doradca +8 007,89 zl o tej samej
    rzeczy w tej samej chwili).

    HORYZONT (D-23): do czestosci kategorii i do licznika wpisow wchodza
    WYLACZNIE wpisy od dnia rozpoczecia dzialalnosci. 204 wpisy z 2025 sa
    historia i nie maja ustawiac kolejnosci kafelkow w 2026 roku.
    """
    dzialalnosc_od = magazyn.odczytaj_dzialalnosc_od(polaczenie)
    wpisy = magazyn.wczytaj_wpisy(polaczenie, od=dzialalnosc_od)
    plan = magazyn.wczytaj_plan(polaczenie)
    slownik = magazyn.wczytaj_kategorie(polaczenie, typ)

    nazwy = [str(w["nazwa"]) for _, w in slownik.iterrows()
             if str(w["nazwa"]) not in KATEGORIE_POZA_EKRANEM]
    aktywne = {str(w["nazwa"]): bool(w["aktywna"])
               for _, w in slownik.iterrows()}
    uporzadkowane = kolejnosc_kategorii(
        nazwy, wpisy=wpisy, plan=plan, typ=typ,
        rok=dzis.year, miesiac=dzis.month)

    w_miesiacu = _wpisy_miesiaca(wpisy, dzis.year, dzis.month)
    kategoria = kategoria_podgladu or (
        uporzadkowane[0] if uporzadkowane else "")

    return kontrakt.DaneKsiegowania(
        # STOPKA STRAZNIKA — ten sam fakt i TEN SAM NOSNIK zdania, co na
        # Plynnosci (`prezentacja.podpis_straznika`). Do Z7b to pole istnialo
        # wylacznie w `DanePlynnosci`, wiec ekran Ksiegowanie mowil „nie wiem"
        # o czyms, co aplikacja wiedziala — dwa ekrany dawaly dwie odpowiedzi
        # na jedno pytanie „czy to, co widze, jest aktualne".
        #
        # ZDANIE SKLADA JEDEN NOSNIK, nie ten plik. Gdyby ekran skladal je
        # u siebie, brzmienie stopki mialoby tyle wersji, ile ekranow — i to
        # jest dokladnie ta wada, ktora domykamy, tylko o warstwe wyzej.
        ostatnieSprawdzenie=_podpis_straznika(polaczenie, dzis),
        dzisiaj=dzis.isoformat(),
        typDomyslny=typ,
        kategorie=tuple(
            kontrakt.Kategoria(
                nazwa=nazwa, aktywna=aktywne.get(nazwa, True),
                # `systemowa` nie ma kolumny w bazie — to nie brak, tylko
                # wlasnosc SLOWNIKA STARTOWEGO: systemowa jest kategoria,
                # ktora dolozyl silnik, bo sam jej potrzebuje (dzis: „Podatki
                # i ZUS", w ktora laduja zaplaty danin). Wolane z jedynego
                # nosnika, nie przepisane.
                systemowa=nazwa in budzet.KATEGORIE_SPOZA_ARKUSZA)
            for nazwa in uporzadkowane),
        uzasadnienieKolejnosci=uzasadnienie_kolejnosci(
            wpisow=len(w_miesiacu),
            z_planu=len(_kategorie_planu(plan, dzis.year, dzis.month, typ)
                        - set(KATEGORIE_POZA_EKRANEM)),
            rok=dzis.year, miesiac=dzis.month,
            nazwa_miesiaca=prezentacja.MIESIACE_MIEJSCOWNIK[dzis.month - 1]),
        ostatnieWpisy=ostatnie_wpisy(wpisy, napis_kwoty=napis_kwoty),
        liczbaWpisowWMiesiacu=len(w_miesiacu),
        nazwaMiesiaca=prezentacja.MIESIACE_MIEJSCOWNIK[dzis.month - 1],
        podglad=podglad(wpisy=wpisy, plan=plan, typ=typ, kategoria=kategoria,
                        kwota=kwota_podgladu, dzien=dzis, dzis=dzis,
                        napis_kwoty=napis_kwoty))


def _wpisy_miesiaca(wpisy: pd.DataFrame, rok: int, miesiac: int) -> pd.DataFrame:
    if wpisy.empty:
        return wpisy
    return wpisy[wpisy["data"].astype(str)
                 .str.startswith(f"{rok:04d}-{miesiac:02d}")]


def ostatnie_wpisy(wpisy: pd.DataFrame, *,
                   napis_kwoty: NapisKwoty) -> tuple[kontrakt.OstatniWpis, ...]:
    """Sześć ostatnich wpisow, od najnowszego.

    `magazyn.wczytaj_wpisy` oddaje je rosnaco po dacie i numerze, wiec
    „ostatnie" to ogon listy odwrocony. Kolejnosc jest tu OBIETNICA wobec
    ekranu („Ostatnie wpisy"), a nie wlasnoscia cudzej listy — dlatego
    odwracamy jawnie, zamiast ufac, ze ktos posortowal malejaco.
    """
    if wpisy.empty:
        return ()
    ogon = wpisy.tail(ILE_OSTATNICH_WPISOW)
    return tuple(
        kontrakt.OstatniWpis(
            id=int(w["id"]), data=str(w["data"]), typ=str(w["typ"]),
            kategoria=str(w["kategoria"]), kwota=napis_kwoty(w["kwota"]),
            szczegoly=str(w["szczegoly"] or ""))
        for _, w in reversed(list(ogon.iterrows())))


# --- zapis i wycofanie ----------------------------------------------------

@dataclass(frozen=True, slots=True)
class OdpowiedzZapisu:
    """Wynik proby zapisu albo wycofania — razem z odswiezonym ekranem.

    `dane` jedzie w komplecie SWIADOMIE. Po zapisie zmieniaja sie trzy rzeczy
    naraz: licznik wpisow, lista ostatnich wpisow i kolejnosc kafelkow
    (czestosc kategorii). Ekran, ktory po zapisie dolicza je sobie sam, jest
    DRUGIM NOSNIKIEM kazdej z tych regul — a rozjazd byloby widac dopiero przy
    odswiezeniu strony.

    `stan` rozstrzyga, czy cokolwiek trafilo do bazy. Kod HTTP tego nie
    rozstrzyga i nie ma: pytanie o minus to nie jest blad zadania.
    """

    stan: str
    id: "int | None"
    kwota: "str | None"
    typ: "str | None"
    dane: kontrakt.DaneKsiegowania


#: Stan trzeci obok `STAN_PRZYJETA` i `STAN_PYTANIE_O_MINUS` — wylacznie
#: w odpowiedzi, nigdy w rozstrzygnieciu kwoty.
STAN_ZAPISANY = "zapisany"
STAN_WYCOFANY = "wycofany"


def zapisz(polaczenie, *, data, typ: str, kategoria: str, kwota,
           szczegoly: "str | None" = None, potwierdzone: bool = False,
           dzis: date,
           napis_kwoty: NapisKwoty) -> OdpowiedzZapisu:
    """Zapis wpisu ALBO pytanie o minus — decyzja zapada TUTAJ, nie w trasie.

    Trasa ma byc pozbawiona rozgalezien (zasada twarda Z6: „zero rachunku
    w trasie"), a wybor miedzy zapisem a pytaniem jest regula o konsekwencji
    zewnetrznej: rozstrzyga, czy pieniadze trafily do bazy. Regula w trasie
    mialaby tylu nosnikow, ile tras ja wola.

    JEDEN PISZACY NA JEDEN OBSZAR: do tabeli wpisow pisze wylacznie
    `magazyn.zapisz_wpis`. Zlamanie tej zasady dalo u poprzednika zmierzone
    400 prob zapisu -> 274 wiersze — wpisy ginely bez sygnalu.

    `WpisDoZapisu` z kontraktu jest budowany PRZED zapisem, nawet gdy nikt
    go dalej nie czyta: to on niesie sprawdzenie „kwota bez znaku" i ma paść,
    zanim cokolwiek dotknie bazy.
    """
    rozstrzygniecie = rozstrzygnij_kwote(kwota, typ, potwierdzone=potwierdzone)
    dzien = data if isinstance(data, date) else date.fromisoformat(str(data))

    if rozstrzygniecie.stan == STAN_PYTANIE_O_MINUS:
        return OdpowiedzZapisu(
            stan=STAN_PYTANIE_O_MINUS, id=None,
            kwota=napis_kwoty(rozstrzygniecie.kwota), typ=typ,
            dane=zbierz(polaczenie, dzis=dzis, napis_kwoty=napis_kwoty,
                        typ=typ, kwota_podgladu=rozstrzygniecie.kwota,
                        kategoria_podgladu=kategoria))

    kontrakt.WpisDoZapisu(
        data=dzien.isoformat(), typ=typ, kategoria=kategoria,
        kwota=str(rozstrzygniecie.kwota), szczegoly=szczegoly or "")

    numer = magazyn.zapisz_wpis(
        polaczenie, data=dzien, typ=typ, kategoria=kategoria,
        kwota=rozstrzygniecie.kwota, szczegoly=szczegoly or "")

    return OdpowiedzZapisu(
        stan=STAN_ZAPISANY, id=int(numer),
        kwota=napis_kwoty(rozstrzygniecie.kwota), typ=typ,
        dane=zbierz(polaczenie, dzis=dzis, napis_kwoty=napis_kwoty, typ=typ,
                    kategoria_podgladu=kategoria))


def wycofaj(polaczenie, *, wpis_id: int, dzis: date, typ: str = TYP_DOMYSLNY,
            napis_kwoty: NapisKwoty) -> OdpowiedzZapisu:
    """Wycofanie jednego wpisu razem z odswiezonym ekranem.

    Brak wiersza o podanym numerze jest BLEDEM, nie cicha zgoda — decyduje
    o tym `magazyn.usun_wpis` i tutaj nic tego nie zmiekcza. Pomylka
    w numerze, ktora melduje sukces, jest gorsza niz odmowa.
    """
    magazyn.usun_wpis(polaczenie, wpis_id=int(wpis_id))
    return OdpowiedzZapisu(
        stan=STAN_WYCOFANY, id=int(wpis_id), kwota=None, typ=None,
        dane=zbierz(polaczenie, dzis=dzis, napis_kwoty=napis_kwoty, typ=typ))


def podglad_z_bazy(polaczenie, *, typ: str, kategoria: str, kwota,
                   dzien: date, dzis: date, napis_kwoty: NapisKwoty
                   ) -> kontrakt.PodgladSkutku:
    """„Co ruszy ten wpis" dla wpisu, ktorego jeszcze nie ma w bazie.

    KWOTA UJEMNA POKAZUJE SKUTEK WARTOSCI BEZWZGLEDNEJ, bo taka wlasnie
    trafi do bazy po potwierdzeniu (`rozstrzygnij_kwote`). Podglad, ktory
    pokazywalby skutek kwoty ze znakiem, obiecywalby ruch w druga strone niz
    zapis — a to jest dokladnie ta klasa rozjazdu, ktorej broni wspolny
    nosnik reguly. Podglad nie PYTA o minus; pyta zapis.
    """
    rozstrzygniecie = rozstrzygnij_kwote(kwota, typ, potwierdzone=True)
    dzialalnosc_od = magazyn.odczytaj_dzialalnosc_od(polaczenie)
    return podglad(
        wpisy=magazyn.wczytaj_wpisy(polaczenie, od=dzialalnosc_od),
        plan=magazyn.wczytaj_plan(polaczenie), typ=typ, kategoria=kategoria,
        kwota=rozstrzygniecie.kwota, dzien=dzien, dzis=dzis,
        napis_kwoty=napis_kwoty)

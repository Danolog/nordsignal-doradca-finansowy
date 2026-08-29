# -*- coding: utf-8 -*-
"""SKLADANIE ODPOWIEDZI EKRANU PLYNNOSC. Ksztalt bierze z `kontrakt.py`.

TEN PLIK NIE LICZY ANI JEDNEJ KWOTY — dokladnie jak `rdzen/co_mnie_czeka.py`
i z tego samego powodu. Wszystkie salda, daniny i pozycje planu policzyla juz
`prognoza_plynnosci.zbuduj`. Tutaj sa WYBIERANE, PRZYCINANE DO OKNA i NAZWANE
zdaniem werdyktu. Gdyby ten plik kiedykolwiek zaczal dodawac albo zaokraglac
kwoty, jest bledem: zmierzone u poprzednika 2026-08-26 — ekran pokazywal
-6 098,11 zl, a doradca +8 007,89 zl o tej samej rzeczy w tej samej chwili,
przy zielonej suicie.

DLACZEGO NAPIS KWOTY WCHODZI ARGUMENTEM: uzasadnienie w naglowku
`silnik/ekran_ksiegowanie.py`. Krotko: `api/kwoty.py` stoi na `fastapi`,
a silnik nie ma prawa wiedziec, ze HTTP istnieje.

OKNO WYKRESU JEST RUCHOME I TO JEST REGULA, NIE WYGODA. Konczy sie na
`dzis + okno_dni`, ale rozciaga sie dalej, jesli dzien pod kreska albo dzien
najnizszego salda wypada pozniej. Bez tego werdykt mowilby „25 wrzesnia
schodzisz ponizej zera", a wykres tego dnia by nie pokazywal — czyli ekran
ostrzegalby o czyms, czego nie widac. Zla wiadomosc ucieta oknem to zla
wiadomosc przemilczana.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Callable

from silnik import kontrakt
from silnik.rdzen import co_mnie_czeka, magazyn, prezentacja
from silnik.rdzen import prognoza_plynnosci as pp

NapisKwoty = Callable[..., "str | None"]

#: Wiersz otwarcia ksiegi — kotwica stoi WEWNATRZ prognozy, drobnym drukiem,
#: z wiekiem odczytu. Osobna karta obok byla nazwana wada (§4.1): odczyt salda
#: bez prognozy nie odpowiada na zadne pytanie, a prognoza bez odczytu nie
#: mowi, skad startuje.
POZYCJA_OTWARCIA = "Stan na dziś"


def _dopisek_kotwicy(kotwica: "pp.Kotwica | None") -> "str | None":
    """Drobny druk przy wierszu otwarcia: ile i z ktorego dnia.

    WIEK ODCZYTU JEST CZESCIA LICZBY, nie ozdoba. Saldo sprzed trzech tygodni
    i saldo z dzisiaj wygladaja identycznie, a znacza co innego — dlatego
    `magazyn.OdczytSalda` niesie date i dlatego ona tu wychodzi na ekran.
    """
    if kotwica is None:
        return None
    dzien = kotwica.data
    return (f"— z odczytu {prezentacja.zloty(kotwica.kwota)} z "
            f"{dzien.day} {prezentacja.MIESIACE_DOPELNIACZ[dzien.month - 1]}")


def najnizszy_punkt(dni) -> "tuple[date, Decimal] | None":
    """Pierwszy dzien o najnizszym saldzie ostroznym — JEDEN NOSNIK.

    ODPOWIADA NA INNE PYTANIE NIZ `prognoza.minimum`, mimo podobienstwa:
    tamto jest wartoscia liczona nad CALYM horyzontem prognozy (szesc
    miesiecy), a ta funkcja odnajduje DZIEN tej wartosci w podanej serii.
    Kontrakt potrzebuje obu (`saldoMinimalne` i `dataSaldaMinimalnego`),
    a data nie da sie wyprowadzic z samej kwoty.

    „Pierwszy", nie „ostatni": gdy dwa dni maja to samo minimum, uzytkownik
    ma zobaczyc ten, ktory nadchodzi wczesniej — bo to on jest terminem
    decyzji.
    """
    if not dni:
        return None
    najnizszy = min(dni, key=lambda d: d.saldo_ostrozne)
    for d in dni:
        if d.saldo_ostrozne == najnizszy.saldo_ostrozne:
            return d.data, d.saldo_ostrozne
    return najnizszy.data, najnizszy.saldo_ostrozne


def zdanie_werdyktu(*, prognoza: pp.Prognoza, najnizsze, dni_w_oknie) -> str:
    """Zdanie pod wielka liczba — JEDEN NOSNIK wzorca zlej wiadomosci.

    Wzorzec brzmi: liczba, zdanie, dzialanie. Zdanie ma NAZWAC PRZYCZYNE,
    nie powtorzyc fakt: „schodzisz ponizej zera" zostawia lek bez wyjscia,
    „tego dnia wychodzi VAT i czesne" mowi, gdzie szukac ruchu.

    TRZY STANY PROGNOZY, NIE DWA (regula D11) — i kazdy inaczej:

    * `nie_wiem` — prognozy NIE MA. Zdanie jest wtedy ZDANIEM SILNIKA
      w calosci, bez przeredagowania: on wie, czego mu brakuje, ekran nie;
    * `nieaktualna` — prognoza JEST, ale biegnie od liczby, ktora mogla sie
      juz zmienic. Werdykt o pieniadzach zostaje, a zdanie silnika o wieku
      odczytu doklada sie do niego. Samo zastrzezenie zamiast werdyktu
      ukrywaloby zla wiadomosc za uwaga porzadkowa; sam werdykt bez
      zastrzezenia obiecywalby swiezosc, ktorej nie ma;
    * `policzona` — sam werdykt.

    ZASTRZEZENIE WYBIERANE PO KODZIE, NIE PO POZYCJI. Pierwsza wersja brala
    `zastrzezenia[0]` i w przebiegu kontrolnym 2026-08-29 pokazala pod wielka
    liczba zdanie o miesiacu bez planu, podczas gdy prognoza byla nieaktualna
    z zupelnie innego powodu. Kolejnosc listy jest wlasnoscia CUDZEGO kodu;
    kod zastrzezenia jest umowa.
    """
    if prognoza.dni is None or prognoza.stan == pp.STAN_NIE_WIEM:
        if prognoza.zastrzezenia:
            return " ".join(z.tekst for z in prognoza.zastrzezenia)
        return ("Nie policzę prognozy i nie umiem powiedzieć dlaczego — "
                "zgłoś to, zanim podejmiesz decyzję o pieniądzach.")

    zdanie = _werdykt_o_pieniadzach(prognoza=prognoza, najnizsze=najnizsze,
                                    dni_w_oknie=dni_w_oknie)
    nieaktualna = [z.tekst for z in prognoza.zastrzezenia
                   if z.kod == pp.KOD_KOTWICA_NIEAKTUALNA]
    return " ".join([zdanie] + nieaktualna)


def _werdykt_o_pieniadzach(*, prognoza: pp.Prognoza, najnizsze,
                           dni_w_oknie) -> str:
    """Sam werdykt: schodzisz albo nie schodzisz, i z jakiego powodu."""
    dzien_pod_kreska = prognoza.pierwszy_dzien_ujemny
    if dzien_pod_kreska is not None:
        powod = _co_wychodzi_tego_dnia(dni_w_oknie, dzien_pod_kreska)
        kiedy = (f"{dzien_pod_kreska.day} "
                 f"{prezentacja.MIESIACE_DOPELNIACZ[dzien_pod_kreska.month - 1]}")
        if powod:
            return f"{kiedy} schodzisz poniżej zera — tego dnia wychodzi {powod}."
        return (f"{kiedy} schodzisz poniżej zera — tego dnia nie ma żadnej "
                f"pozycji, więc saldo schodzi z dni wcześniejszych.")

    if najnizsze is None:
        return "Prognoza nie ma ani jednego dnia — nie ma czego pokazać."
    dzien, saldo = najnizsze
    kiedy = f"{dzien.day} {prezentacja.MIESIACE_DOPELNIACZ[dzien.month - 1]}"
    return (f"Nie schodzisz poniżej zera — najniżej masz "
            f"{prezentacja.zloty(saldo)} {kiedy}.")


def _co_wychodzi_tego_dnia(dni, dzien: date) -> str:
    """Nazwy wyplywow danego dnia, po polsku, z „i" przed ostatnia.

    Wyplywy, nie wszystkie zdarzenia: przychod wymieniony w zdaniu
    o zejsciu ponizej zera czytalby sie jak przyczyna klopotu.
    Rodzaje wolane z `co_mnie_czeka.RODZAJE_WYPLYWU` — jeden nosnik podzialu.
    """
    nazwy = [z.nazwa for d in dni if d.data == dzien for z in d.zdarzenia
             if z.rodzaj in co_mnie_czeka.RODZAJE_WYPLYWU
             and z.kwota_ostrozna < 0]
    if not nazwy:
        return ""
    if len(nazwy) == 1:
        return nazwy[0]
    return ", ".join(nazwy[:-1]) + f" i {nazwy[-1]}"


def zbuduj(*, prognoza: pp.Prognoza, kotwica: "pp.Kotwica | None",
           czeka: co_mnie_czeka.CoMnieCzeka, przebieg: "dict | None",
           dzis: date, okno_dni: int, napis_kwoty: NapisKwoty,
           ) -> kontrakt.DanePlynnosci:
    """Ksztalt ekranu z gotowej prognozy. BEZ BAZY i BEZ RACHUNKU."""
    wszystkie = list(prognoza.dni or ())

    # Okno ruchome — uzasadnienie w naglowku pliku. Rozciaga sie WYLACZNIE
    # na dzien pod kreska, nigdy na dzien najnizszego salda: minimum
    # zdrowej prognozy wypada zwykle na koncu szesciomiesiecznego horyzontu,
    # wiec rozciaganie okna do niego zamienialo wykres 45-dniowy w 177-dniowy
    # (zmierzone w przebiegu kontrolnym 2026-08-29). Zla wiadomosc rozciaga
    # okno; dobra nie ma prawa go rozciagac.
    koniec_okna = dzis + timedelta(days=okno_dni)
    if prognoza.pierwszy_dzien_ujemny is not None:
        koniec_okna = max(koniec_okna, prognoza.pierwszy_dzien_ujemny)

    # Ksiega i wykres zaczynaja sie DZIS, nie w dniu odczytu salda. Kotwica
    # bywa starsza od dzis (odczyt sprzed tygodnia), a wiersz otwarcia nosi
    # napis „Stan na dziś" — datowany dniem odczytu klamalby wprost. Wiek
    # odczytu niesie `dopisek`, i to jest jego jedyne miejsce.
    dni_w_oknie = [d for d in wszystkie if dzis <= d.data <= koniec_okna]

    # `saldoMinimalne` jest minimum TEGO, CO POKAZUJEMY, a nie calego
    # horyzontu (`prognoza.minimum`). Etykieta „NAJNIŻEJ — 25 WRZEŚNIA" stoi
    # nad wykresem i opisuje wykres; liczba spoza rysunku byla by etykieta
    # opisujaca cos, czego nie widac (CLAUDE.md §3.5). Zla wiadomosc nie
    # ucieka tym oknem, bo dzien pod kreska rozciaga je wyzej.
    najnizsze = najnizszy_punkt(dni_w_oknie)

    ksiega: list[kontrakt.PozycjaKsiegi] = []
    if dni_w_oknie:
        pierwszy = dni_w_oknie[0]
        ksiega.append(kontrakt.PozycjaKsiegi(
            dzien=pierwszy.data.isoformat(), pozycja=POZYCJA_OTWARCIA,
            # `kwota=None` = wiersz otwarcia; na ekranie „—", nigdy zero.
            # Stan konta nie jest ruchem na koncie.
            kwota=None, saldoPoDniu=napis_kwoty(pierwszy.saldo_ostrozne),
            dopisek=_dopisek_kotwicy(kotwica)))
    for d in dni_w_oknie:
        for z in d.zdarzenia:
            ksiega.append(kontrakt.PozycjaKsiegi(
                dzien=d.data.isoformat(), pozycja=z.nazwa,
                kwota=napis_kwoty(z.kwota_ostrozna),
                saldoPoDniu=napis_kwoty(d.saldo_ostrozne)))

    horyzont = prognoza.pierwszy_dzien_ujemny or koniec_okna
    return kontrakt.DanePlynnosci(
        odczyt=dzis.isoformat(),
        okresNapis=_okres_napis(dni_w_oknie, okno_dni),
        # Zwezenie salda do jednego na dzien robi JEDYNY nosnik tej reguly —
        # `kontrakt.zbij_saldo_raz_na_dzien`. Ekran go nie powtarza: dostaje
        # `null` i rysuje puste miejsce.
        ksiega=kontrakt.zbij_saldo_raz_na_dzien(ksiega),
        wykres=tuple(kontrakt.PunktWykresu(
            dzien=d.data.isoformat(), saldo=napis_kwoty(d.saldo_ostrozne))
            for d in dni_w_oknie),
        dzienPodKreska=(None if prognoza.pierwszy_dzien_ujemny is None
                        else prognoza.pierwszy_dzien_ujemny.isoformat()),
        saldoMinimalne=(None if najnizsze is None
                        else napis_kwoty(najnizsze[1])),
        dataSaldaMinimalnego=(None if najnizsze is None
                              else najnizsze[0].isoformat()),
        zdanieWerdyktu=zdanie_werdyktu(
            prognoza=prognoza, najnizsze=najnizsze, dni_w_oknie=dni_w_oknie),
        # „Masz N dni." Nigdy liczba ujemna: dzien pod kreska w przeszlosci
        # dalby „Masz -3 dni" — napis, ktorego nikt nie napisal celowo.
        horyzontDni=max((horyzont - dzis).days, 0),
        liczbaPozycjiCoMnieCzeka=len(czeka.pozycje),
        koniecOknaCoMnieCzeka=(dzis + timedelta(days=okno_dni)).isoformat(),
        # `None` znaczy „straznik NIGDY nie dzialal" i nie wolno go zamienic
        # na zdanie o sprawdzeniu (regula D11). Zdanie sklada jedyny nosnik:
        # `prezentacja.podpis_straznika`.
        ostatnieSprawdzenie=(None if przebieg is None
                             else prezentacja.podpis_straznika(przebieg, dzis)))


def _okres_napis(dni, okno_dni: int) -> str:
    """„wrzesień 2026 · 45 dni naprzód" — miesiac startu i rozpietosc serii."""
    if not dni:
        return f"brak prognozy · okno {okno_dni} dni"
    pierwszy, ostatni = dni[0].data, dni[-1].data
    return (f"{prezentacja.etykieta_okresu(pierwszy.strftime('%Y-%m'))} · "
            f"{(ostatni - pierwszy).days} dni naprzód")


def zbierz(polaczenie, *, dzis: date, napis_kwoty: NapisKwoty,
           okno_dni: int = co_mnie_czeka.OKNO_DNI_DOMYSLNE,
           ) -> kontrakt.DanePlynnosci:
    """Cienki zbieracz: czyta baze przez ISTNIEJACE nosniki, wola `zbuduj`.

    JEDEN PRZEBIEG PROGNOZY, nie dwa. Os terminow dostaje TE SAMA prognoze
    (`co_mnie_czeka.zbuduj`), zamiast liczyc wlasna przez `zestaw` — dwa
    niezalezne przebiegi tego samego rachunku to dwie okazje, zeby ekran
    i przycisk „Co mnie czeka" powiedzialy co innego o tej samej chwili.

    AWARIA DO STANU UZYTECZNEGO, NIE DO ZERA (CLAUDE.md §3.7). Gdy forma
    opodatkowania nie jest wskazana, `podatki.rezerwa_na_podatki` ODMAWIA
    liczenia — i ma racje, bo zgadywanie formy jest zmierzonym mechanizmem
    awarii (`testy/test_forma_bez_domyslnej.py`). Odmowa nie ma jednak prawa
    wyjsc na ekran jako pusty ekran ani jako 500: zamieniamy ja na prognoze
    w stanie „nie wiem", ktora niesie ZDANIE SILNIKA w calosci.
    """
    try:
        prognoza = pp.prognozuj(polaczenie, dzis=dzis)
    except magazyn.BladMagazynu as blad:
        prognoza = pp.Prognoza(
            stan=pp.STAN_NIE_WIEM, dni=None,
            zastrzezenia=(pp.Zastrzezenie(pp.KOD_BRAK_FORMY, str(blad)),))

    return zbuduj(
        prognoza=prognoza,
        kotwica=pp.ostatnia_kotwica(polaczenie),
        # `rezerwa=None` swiadomie: os terminow trzyma ja wylacznie po to,
        # zeby oddac ja SWOIM konsumentom, a ten ekran jej nie pokazuje.
        # Policzenie jej tutaj byloby drugim przebiegiem rachunku podatkowego
        # dla wyniku, ktorego nikt nie czyta.
        czeka=co_mnie_czeka.zbuduj(prognoza=prognoza, rezerwa=None, dzis=dzis,
                                   okno_dni=okno_dni),
        przebieg=magazyn.ostatni_przebieg_straznika(polaczenie),
        dzis=dzis, okno_dni=okno_dni, napis_kwoty=napis_kwoty)


def zapisz_kotwice(polaczenie, *, data, kwota, dzis: date,
                   napis_kwoty: NapisKwoty,
                   okno_dni: int = co_mnie_czeka.OKNO_DNI_DOMYSLNE,
                   ) -> kontrakt.DanePlynnosci:
    """Odczyt stanu konta — ZRODLO kotwicy prognozy — i ekran po nim.

    KWOTA MOZE BYC UJEMNA i jest jedyna taka w tej bazie: konto na debecie to
    realny stan konta, a nie blad wpisu. Regula „minus jest w typie wpisu"
    NIE OBOWIAZUJE tutaj i to nie jest wyjatek dla wygody — tam kierunek
    niesie typ pozycji, tu znak jest czescia odczytu. Pilnuje tego
    `magazyn.zapisz_stan_konta`, jedyny pisarz tego obszaru.

    Ekran wraca w calosci, bo po nowym odczycie zmienia sie WSZYSTKO:
    prognoza startuje z innego punktu, wiec inny jest werdykt, inny dzien pod
    kreska i inne saldo minimalne. Odpowiedz „zapisano" kazalaby przegladarce
    zlozyc te liczby po swojemu albo odpytac drugi raz.
    """
    dzien = data if isinstance(data, date) else date.fromisoformat(str(data))
    magazyn.zapisz_stan_konta(polaczenie, data=dzien, kwota=kwota)
    return zbierz(polaczenie, dzis=dzis, napis_kwoty=napis_kwoty,
                  okno_dni=okno_dni)

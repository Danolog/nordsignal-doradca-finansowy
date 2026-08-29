"""Narzędzia doradcy — wykonywane LOKALNIE, zwracające agregaty.

Zasada konstrukcyjna: **model nigdy nie widzi bazy**. Widzi wyniki funkcji,
które wykonały się na tym komputerze. Poza laptop wychodzi instrukcja
systemowa, pytanie i to, co zwróciły te funkcje — nic więcej.

**Reguła twarda, wymuszona strukturalnie:** żadne narzędzie nie zwraca nazwy
klienta, kontrahenta, numeru faktury ani treści notatki. Nie dlatego, że model
został o to poproszony, tylko dlatego, że **te pola nie istnieją na ścieżce
wyjścia**. Podstawa: §7 ust. 4 lit. a umowy B2B z NMI ERP — tajemnica o
klientach Zleceniodawcy, obowiązująca 3 lata po zakończeniu umowy.

Kwoty zwracane jako **napisy**, nie liczby zmiennoprzecinkowe: `Decimal`
nie przechodzi przez JSON, a `float` gubi grosze.
"""

from datetime import date
from decimal import Decimal
from typing import Callable

from datetime import date as _date

from silnik.rdzen import (budzet, formy, godziny, magazyn, podatki, prezentacja,
                   prognoza, stawki, weryfikacja)
from silnik.rdzen import majatek as rdzen_majatek

STAWKA_GODZINOWA = Decimal("70")

#: Nazwy wszystkich narzędzi. Kontrola liczności w testach opiera się na tej liście.
NAZWY = (
    "stan_finansow", "prognoza_roczna", "policz_podatek", "porownaj_formy",
    "rozklad_godzin", "agregat_faktur", "zobowiazania_i_majatek", "stan_stawek",
    "wydatki_wg_kategorii", "wykonanie_planu", "postep_celow",
    "saldo_narastajaco",
)

#: Argumenty do przebiegu strażnika poufności — każde narzędzie musi dać się
#: wywołać w teście, także to z wymaganymi parametrami.
ARGUMENTY_TESTOWE: dict[str, dict] = {
    "prognoza_roczna": {"godziny_miesiecznie": 160},
    "policz_podatek": {"kwota_netto": "11200"},
    "porownaj_formy": {"przychod_roczny": "134400"},
    "rozklad_godzin": {"od": "2026-01-01", "do": "2026-12-31"},
    "wydatki_wg_kategorii": {"rok": 2025, "miesiac": 10},
    "wykonanie_planu": {"rok": 2025, "miesiac": 10},
    "saldo_narastajaco": {"rok": 2025, "miesiac": 10},
}


def _kwota(x) -> str:
    """Kwota jako napis dla modelu jezykowego.

    Zaokraglenie idzie przez `stawki.do_groszy` — jedyny nosnik konwencji
    pienieznej (ROUND_HALF_UP). Do Z4 stalo tu wlasne `quantize` BEZ trybu,
    czyli zaokraglenie BANKIERSKIE: 1 305,045 dawalo 1 305,04 zamiast
    1 305,05. Dwie konwencje zaokraglania obok siebie w aplikacji podatkowej
    to wada, nie szczegol — a ta akurat karmila model liczbami innymi niz
    te, ktore pokazuje ekran.
    """
    return str(stawki.do_groszy(Decimal(str(x))))


def zbuduj(polaczenie) -> dict[str, Callable]:
    """Zwraca komplet narzędzi z domkniętym połączeniem do bazy.

    Połączenie jest domknięte w funkcji, a nie parametrem — model nie ma jak
    wskazać innej bazy ani podejrzeć, że baza w ogóle istnieje.
    """

    def stan_finansow() -> dict:
        """Podaje bieżący stan finansów: ile realnie zostaje, ile jest już
        zarezerwowane na podatki, jaka jest poduszka finansowa i ile wyniosły
        wydatki bieżącego miesiąca. Wszystkie kwoty w złotych, jako napisy.
        """
        faktury = magazyn.wczytaj_faktury(polaczenie)
        majatek = magazyn.wczytaj_majatek(polaczenie)
        # Filtr typu jest warunkiem poprawnosci, nie wygoda: po wchlonieciu
        # starej tabeli wydatkow jedna tabela trzyma takze przychody
        # i oszczednosci. Bez filtru ta suma wyglada jak wydatki i nia nie jest.
        wydatki = magazyn.wczytaj_wpisy(polaczenie, typ=budzet.TYP_WYDATKI)
        dzis = date.today()

        # Jeden nosnik reguly rezerwy — ta sama funkcja, ktora liczy kafel
        # Pulpitu. Wczesniej formula stala tu przepisana i mogla sie rozjechac.
        wszystkie_wpisy = magazyn.wczytaj_wpisy(polaczenie)
        rezerwa = podatki.rezerwa_z_bazy(
            polaczenie, wpisy=wszystkie_wpisy, dzis=dzis)

        zostaje = Decimal("0")
        if not faktury.empty:
            zostaje = sum(faktury["zysk_netto"], Decimal("0"))

        # Jeden nosnik reguly poduszki — ta sama funkcja, ktora liczy kafelek
        # Pulpitu (D-36). Do 2026-08-28 stal tu wlasny filtr po napisie
        # „poduszka", czyli druga kopia tej samej reguly.
        poduszka = rdzen_majatek.poduszka_finansowa(majatek)

        wydatki_mc = Decimal("0")
        if not wydatki.empty:
            prefiks = f"{dzis.year:04d}-{dzis.month:02d}"
            wydatki_mc = sum(wydatki[wydatki["data"].str.startswith(prefiks)]["kwota"],
                             Decimal("0"))

        # „Wolne srodki" maja JEDEN nosnik i jest nim `budzet.wolne_srodki`
        # (Z56). Do niego stalo tu `zostaje - wydatki_mc` — zysk z faktur
        # minus wydatki miesiaca — czyli DRUGA formula tej samej liczby.
        # Zmierzone 2026-08-26: ekran −6 098,11 zl, doradca +8 007,89 zl,
        # te same dane, ta sama chwila.
        #
        # Plan dociagany bez filtru miesiaca, tak jak w `wykonanie_planu`:
        # pozycja trwala zaczeta wczesniej obowiazuje takze tutaj, a rozwija
        # ja `budzet.plan_na_miesiac` — jedyny nosnik tej reguly.
        plan = magazyn.wczytaj_plan(polaczenie)
        wolne = budzet.wolne_srodki(plan, [(dzis.year, dzis.month)],
                                    rezerwa.saldo)

        return {
            "zostaje_po_podatkach": _kwota(zostaje),
            "zarezerwowane_na_podatki": _kwota(rezerwa.saldo),
            "podatki_naliczone_razem": _kwota(rezerwa.naliczone_razem),
            "podatki_juz_zaplacone": _kwota(rezerwa.zaplacone),
            "poduszka_finansowa": _kwota(poduszka),
            "wydatki_biezacego_miesiaca": _kwota(wydatki_mc),
            # Brak planu zostaje BRAKIEM PLANU, nie zerem (D11): zero
            # wygladaloby jak budzet spiety co do grosza.
            "wolne_srodki": None if wolne.kwota is None else _kwota(wolne.kwota),
            "wolne_srodki_komentarz": (
                "brak planu na ten miesiac — nie wiem, ile jest wolne"
                if wolne.kwota is None else
                "plan przychodow minus zaplanowane wydatki i oszczednosci "
                "minus saldo rezerwy podatkowej"),
        }

    def prognoza_roczna(godziny_miesiecznie: int) -> dict:
        """Prognozuje, w którym miesiącu przychód narastająco przetnie progi
        składki zdrowotnej (60 000 zł i 300 000 zł) przy podanej liczbie godzin
        miesięcznie. Stawka godzinowa z umowy wynosi 70 zł netto.
        Podaje też, o ile miesięcznie wzrośnie wtedy składka.
        """
        narastajaco = magazyn.przychod_narastajaco(polaczenie, date.today().year)
        przeciecia = prognoza.prognozuj(Decimal(godziny_miesiecznie), STAWKA_GODZINOWA,
                                        miesiecy=12, przychod_poczatkowy=narastajaco)
        return {
            "godziny_miesiecznie": godziny_miesiecznie,
            "przychod_miesieczny": _kwota(Decimal(godziny_miesiecznie) * STAWKA_GODZINOWA),
            "przychod_narastajaco_teraz": _kwota(narastajaco),
            "prog_60_tys": {
                "miesiac": przeciecia[0].miesiac,
                "wzrost_skladki_miesiecznie": _kwota(przeciecia[0].wzrost_skladki),
            },
            "prog_300_tys": {
                "miesiac": przeciecia[1].miesiac,
                "wzrost_skladki_miesiecznie": _kwota(przeciecia[1].wzrost_skladki),
            },
            "uwaga": "160 godzin to wartość planistyczna z umowy, nie gwarancja "
                     "(§6 ust. 2 nie gwarantuje minimum ani maksimum zleceń).",
        }

    def policz_podatek(kwota_netto: str) -> dict:
        """Rozbija fakturę o podanej kwocie netto na VAT, składkę zdrowotną,
        składki społeczne, podatek dochodowy i kwotę, która realnie zostaje.
        Liczy formą opodatkowania zapisaną w ustawieniach użytkownika — sam
        jej nie wybierasz i nie podajesz stawki. Zwraca też nazwę formy
        i listę założeń, na których stoi to wyliczenie.
        """
        # FORMA NIE JEST PARAMETREM TEGO NARZEDZIA — SWIADOMIE. Do 2026-08-28
        # narzedzie brało stawke ryczaltu od modelu i wolalo `policz_ryczalt`
        # bezwarunkowo, wiec doradca liczyl ryczaltem komus, kto jest na skali
        # (Darek jest na skali od 2026). Model nie ma prawa wybierac formy
        # opodatkowania uzytkownika ani jej zgadywac — forma jest ustawieniem
        # i mieszka w bazie. Nosnik: `podatki.policz_fakture_z_bazy`.
        forma, w = podatki.policz_fakture_z_bazy(
            polaczenie, kwota_netto=Decimal(kwota_netto),
            stawka_vat=stawki.STAWKA_VAT_DOMYSLNA, dzien=date.today())
        wynik = {
            "forma_opodatkowania": prezentacja.NAZWY_FORM.get(forma.forma,
                                                              forma.forma),
            "kwota_netto": str(w.kwota_netto), "vat_nalezny": str(w.vat),
            "skladka_zdrowotna": str(w.zdrowotna),
            "skladki_spoleczne": str(w.spoleczne),
            "nazwa_podatku": podatki.NAZWA_PODATKU[forma.forma],
            "pit": str(w.pit), "do_dyspozycji": str(w.do_dyspozycji),
            "zalozenia": w.zalozenia,
        }
        # Pola wlasciwe JEDNEJ formie ida tylko z ta forma. „Podstawa
        # ryczaltu" w wyniku dla skali bylaby pojeciem, ktorego w skali nie
        # ma — a model powtorzylby ja uzytkownikowi jako fakt.
        if forma.forma == magazyn.FORMA_RYCZALT:
            wynik["podstawa_ryczaltu"] = str(w.podstawa_ryczaltu)
            wynik["prog_zdrowotnej"] = w.prog_zdrowotnej
        else:
            wynik["dochod_narastajaco"] = str(w.dochod_narastajaco)
            wynik["obowiazek_wplaty_zaliczki"] = w.obowiazek_wplaty
        return wynik

    def porownaj_formy(przychod_roczny: str, miesiecy: int = 12,
                       rok_kosztow: int | None = None) -> dict:
        """Porównuje cztery formy opodatkowania przy podanym przychodzie rocznym:
        ryczałt 8,5 procent, ryczałt 15 procent, skalę podatkową i podatek liniowy.
        Podaje PIT, składkę zdrowotną, składki społeczne i sumę obciążeń dla każdej.
        Parametr miesiecy pozwala policzyć rok niepełny. Koszty uzyskania
        przychodu brane są z ewidencji kosztów JDG za rok podany w parametrze
        rok_kosztow, domyślnie bieżący; skala i liniowy je odliczają, ryczałt nie.
        """
        rok = rok_kosztow or date.today().year
        koszty = magazyn.koszty_netto_w_roku(polaczenie, rok)
        wyniki = formy.porownaj_formy(Decimal(przychod_roczny), miesiecy,
                                      koszty=koszty)
        return {
            "przychod_roczny": _kwota(przychod_roczny),
            "koszty_uzyskania_netto": _kwota(koszty),
            "rok_kosztow": rok,
            "miesiecy": miesiecy,
            "formy": [{
                "forma": f.nazwa, "pit": str(f.pit), "zdrowotna": str(f.zdrowotna),
                "spoleczne": str(f.spoleczne), "razem_obciazenia": str(f.razem),
                "do_dyspozycji": str(f.do_dyspozycji),
                "zastrzezenia": f.zastrzezenia,
            } for f in wyniki],
            "najtansza": wyniki[0].nazwa,
        }

    def rozklad_godzin(od: str, do: str) -> dict:
        """Podaje rozkład przepracowanych godzin według rodzaju czynności
        w podanym okresie. Daty w formacie RRRR-MM-DD.
        Odpowiada na pytanie, jaka część pracy to sprzedaż, a jaka analityka.
        """
        try:
            poczatek, koniec = date.fromisoformat(od), date.fromisoformat(do)
        except ValueError:
            return {"blad": "Daty muszą być w formacie RRRR-MM-DD."}
        rozklad = godziny.rozklad(polaczenie, poczatek, koniec)
        suma = sum(rozklad.values(), Decimal("0"))
        return {
            "od": od, "do": do, "suma_godzin": str(suma),
            "wedlug_rodzaju": {k: str(v) for k, v in rozklad.items()},
            "udzial_procentowy": {
                k: f"{v / suma * 100:.0f}" for k, v in rozklad.items()
            } if suma else {},
            "pozycje_faktury_per_pkwiu": [{
                "pkwiu": p.pkwiu, "godziny": str(p.godziny), "netto": str(p.netto),
            } for p in godziny.agreguj(polaczenie, poczatek, koniec, STAWKA_GODZINOWA)],
        }

    def agregat_faktur(rok: int = 0) -> dict:
        """Podaje zbiorcze liczby o wystawionych fakturach w podanym roku
        (0 oznacza rok bieżący): ile ich było, jaka jest suma netto, VAT
        i odłożonych składek. Nie podaje pojedynczych faktur ani kontrahentów.
        """
        df = magazyn.wczytaj_faktury(polaczenie)
        rok = rok or date.today().year
        if not df.empty:
            df = df[df["data"].str.startswith(f"{rok:04d}-")]
        if df.empty:
            return {"rok": rok, "liczba_faktur": 0, "suma_netto": "0.00",
                    "suma_vat": "0.00", "suma_skladek": "0.00", "suma_zostaje": "0.00"}
        return {
            "rok": rok,
            "liczba_faktur": int(len(df)),
            "suma_netto": _kwota(sum(df["kwota_netto"], Decimal("0"))),
            "suma_vat": _kwota(sum(df["kwota_vat"], Decimal("0"))),
            "suma_skladek": _kwota(sum(df["zaplacony_zus"], Decimal("0"))),
            "suma_zostaje": _kwota(sum(df["zysk_netto"], Decimal("0"))),
            "uzyte_pkwiu": sorted(set(df["pkwiu"])),
        }

    def zobowiazania_i_majatek() -> dict:
        """Podaje zbiorczy stan zobowiązań (łączny kapitał i suma rat miesięcznych)
        oraz majątku w podziale na kategorie. Nie podaje nazw poszczególnych
        kredytów ani aktywów.
        """
        zob = magazyn.wczytaj_zobowiazania(polaczenie)
        maj = magazyn.wczytaj_majatek(polaczenie)
        wynik = {
            "liczba_zobowiazan": int(len(zob)),
            "laczny_kapital": _kwota(sum(zob["kapital"], Decimal("0"))) if not zob.empty else "0.00",
            "suma_rat_miesiecznych": _kwota(sum(zob["rata_minimalna"], Decimal("0"))) if not zob.empty else "0.00",
            "majatek_wedlug_kategorii": {},
            "majatek_razem": "0.00",
        }
        if not maj.empty:
            wedlug = {}
            for kategoria in sorted(set(maj["kategoria"])):
                wedlug[kategoria] = _kwota(
                    sum(maj[maj["kategoria"] == kategoria]["wartosc"], Decimal("0")))
            wynik["majatek_wedlug_kategorii"] = wedlug
            wynik["majatek_razem"] = _kwota(sum(maj["wartosc"], Decimal("0")))
        return wynik

    def stan_stawek() -> dict:
        """Podaje, kiedy ostatnio potwierdzono stawki podatkowe na oficjalnych
        stronach rządowych i czy rejestr zgadza się ze źródłem. Podaje też
        aktualne progi składki zdrowotnej i wysokość składek społecznych.
        """
        raport = weryfikacja.sprawdz()
        return {
            "wynik_weryfikacji": raport.wynik.value,
            "komunikat": raport.komunikat,
            "rozbiezne": raport.rozbiezne,
            "zrodla": raport.zrodla,
            "data_odczytu_rejestru": stawki.ZRODLA["zdrowotna"].data_odczytu.isoformat(),
            # Mnozniki WOLANE z nosnika, nie wpisane (Z4 krok 4.5) — do
            # przenosin staly tu trzecia kopia tabeli progow.
            **{f"skladka_zdrowotna_prog_{i}": str(kwota) for i, kwota
               in enumerate(stawki.skladki_zdrowotne_progow(), start=1)},
            "skladki_spoleczne_miesiecznie": str(stawki.suma_spolecznych(True)),
        }

    def wydatki_wg_kategorii(rok: int, miesiac: int) -> dict:
        """Podaje, na co poszły pieniądze w danym miesiącu: sumy wydatków
        w podziale na kategorie, od największej. Podaj rok czterocyfrowo
        i miesiąc jako liczbę od 1 do 12. Kwoty w złotych, jako napisy.
        """
        wpisy = magazyn.wczytaj_wpisy(polaczenie)
        udzialy = budzet.wydatki_wg_kategorii(wpisy, rok, miesiac)
        return {
            "rok": rok, "miesiac": miesiac,
            "liczba_kategorii": len(udzialy),
            "razem": _kwota(sum((k for _, k in udzialy), Decimal("0"))),
            "wedlug_kategorii": {nazwa: _kwota(kwota) for nazwa, kwota in udzialy},
        }

    def wykonanie_planu(rok: int, miesiac: int) -> dict:
        """Porównuje plan budżetu z tym, co faktycznie wydano i zarobiono
        w danym miesiącu, kategoria po kategorii. Podaje też „do alokacji",
        czyli plan przychodów minus plan wydatków minus plan oszczędności.
        Gdy na dany miesiąc nie ma żadnej pozycji planu, „do alokacji" jest
        puste — to znaczy „brak planu", a nie „zero do rozdysponowania".
        """
        wpisy = magazyn.wczytaj_wpisy(polaczenie)
        # Pelny plan, bez filtru miesiaca: pozycja trwala zaczeta wczesniej
        # obowiazuje takze tutaj, a rozwinieciem regul zajmuje sie
        # `budzet.plan_na_miesiac` — jedyny nosnik tej reguly.
        plan = magazyn.wczytaj_plan(polaczenie)
        pozycje = budzet.wykonanie_planu(wpisy, plan, rok, miesiac)
        # `do_alokacji_z_planu`, nie `do_alokacji(wpisy, ...)`: ekran przeszedl
        # na plan w Z41, a to narzedzie zostalo na wpisach i podawalo Darkowi
        # inna liczbe niz pulpit. Jedna liczba ma jeden nosnik.
        alokacja = budzet.do_alokacji_z_planu(plan, [(rok, miesiac)])
        return {
            "rok": rok, "miesiac": miesiac,
            "do_alokacji": None if alokacja.kwota is None
                           else _kwota(alokacja.kwota),
            "do_alokacji_komentarz": (
                "brak planu na ten miesiąc" if alokacja.kwota is None
                else "plan przychodów minus plan wydatków minus plan oszczędności"),
            "liczba_pozycji": len(pozycje),
            "pozycje": [{
                "typ": p.typ, "kategoria": p.kategoria,
                "planowane": _kwota(p.planowane), "wykonane": _kwota(p.wykonane),
                "procent": None if p.procent is None else str(p.procent),
                "pozostalo": _kwota(p.pozostalo),
                "przekroczone": p.przekroczone,
            } for p in pozycje],
        }

    def postep_celow() -> dict:
        """Podaje stan celów oszczędnościowych: ile już uzbierano, ile brakuje,
        do kiedy i ile trzeba odkładać miesięcznie, żeby zdążyć. Postęp liczony
        z realnych wpisów w kategorii celu.
        """
        cele = magazyn.wczytaj_cele(polaczenie)
        wpisy = magazyn.wczytaj_wpisy(polaczenie)
        pozycje = []
        for _, wiersz in cele.iterrows():
            p = budzet.postep_celu(
                wpisy, nazwa=wiersz["nazwa"], kategoria=wiersz["kategoria"],
                kwota_docelowa=wiersz["kwota_docelowa"],
                termin=_date.fromisoformat(wiersz["termin"]))
            pozycje.append({
                "cel": p.nazwa, "kategoria": p.kategoria,
                "kwota_docelowa": _kwota(p.kwota_docelowa),
                "uzbierane": _kwota(p.uzbierane), "procent": str(p.procent),
                "brakuje": _kwota(p.brakuje), "termin": p.termin.isoformat(),
                "miesiecy_do_terminu": p.miesiecy_do_terminu,
                "tempo_miesieczne": (None if p.tempo_miesieczne is None
                                     else _kwota(p.tempo_miesieczne)),
                "osiagniety": p.osiagniety, "po_terminie": p.po_terminie,
            })
        return {"liczba_celow": len(pozycje), "cele": pozycje}

    def saldo_narastajaco(rok: int, miesiac: int) -> dict:
        """Podaje przebieg salda w danym miesiącu: ile zostawało po każdym
        kolejnym dniu z wpisami. Przychody dodają, wydatki i oszczędności
        odejmują.
        """
        wpisy = magazyn.wczytaj_wpisy(polaczenie)
        biezace = wpisy
        if not wpisy.empty:
            biezace = wpisy[wpisy["data"].astype(str).str.startswith(
                f"{rok:04d}-{miesiac:02d}")]
        punkty = budzet.saldo_dzienne(biezace)
        return {
            "rok": rok, "miesiac": miesiac,
            "liczba_dni_z_wpisami": len(punkty),
            "saldo_na_koniec": _kwota(punkty[-1][1]) if punkty else _kwota(0),
            "po_dniach": {data: _kwota(saldo) for data, saldo in punkty},
        }

    return {
        "stan_finansow": stan_finansow,
        "prognoza_roczna": prognoza_roczna,
        "policz_podatek": policz_podatek,
        "porownaj_formy": porownaj_formy,
        "rozklad_godzin": rozklad_godzin,
        "agregat_faktur": agregat_faktur,
        "zobowiazania_i_majatek": zobowiazania_i_majatek,
        "stan_stawek": stan_stawek,
        "wydatki_wg_kategorii": wydatki_wg_kategorii,
        "wykonanie_planu": wykonanie_planu,
        "postep_celow": postep_celow,
        "saldo_narastajaco": saldo_narastajaco,
    }

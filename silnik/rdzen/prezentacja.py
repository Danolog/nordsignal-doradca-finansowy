"""Formatowanie kwot i reguly koloru karty — JEDEN nosnik dla calego projektu.

Z51. Te cztery funkcje mieszkaly w `pulpit/wspolne.py`, ktory importuje
`nicegui` (`wspolne.py:10`). Warstwa `api/` nie moze go zawolac, bo zaciagnelaby
caly interfejs do procesu odpowiadajacego na HTTP — a skopiowanie formatowania
do `api/` utworzyloby drugi nosnik reguly, dokladnie ten, przed ktorym broni
docstring `rola_alokacji`.

Modul ma byc **czysty**: zero bazy, zero interfejsu, zero wejscia-wyjscia.
Pilnuje tego `testy/test_granice.py`, ktory parametryzuje sie po `rdzen/*.py`.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from silnik import pieniadz
from silnik.rdzen import budzet

if TYPE_CHECKING:                      # tylko dla typow
    from silnik.rdzen.magazyn import FormaRoku, OpisBazy  # noqa: F401

#: Separator tysiecy — spacja nierozdzielajaca. Zapisana ucieczka `\u00a0`,
#: bo wklejona wprost jest w kodzie znakiem nie do odroznienia od zwyklej
#: spacji; tak przezyla w `pulpit/wspolne.py:29` do Z51.
#: Nierozdzielajaca i przed separatorem tysiecy, i przed „zl" — liczba nie
#: powinna sie lamac na koncu wiersza ani rozstawac z jednostka.
SEPARATOR_TYSIECY = "\u00a0"

#: Znak minus przy kwocie — MINUS TYPOGRAFICZNY U+2212, nie dywiz ASCII (D-58).
#: Zapisany ucieczka z tego samego powodu co separator: wklejony wprost jest
#: w kodzie nie do odroznienia wzrokiem od dywizu `-`.
#:
#: DLACZEGO RAMKA WYGRYWA Z SILNIKIEM. Ramka jest wiazaca specyfikacja wygladu
#: (CLAUDE.md §3.6), a bramka odwzorowania porownuje zrzuty maszynowo — dywiz
#: i minus maja rozna szerokosc i rozna wysokosc, wiec kazda ujemna kwota
#: dokladalaby sie do odsetka rozniacych sie pikseli. Zmierzone: 24 z 41 ramek
#: niesie U+2212, `interfejs/lib/kwota.ts:21` rowniez.
#:
#: DLACZEGO POPRAWKA JEST TU, A NIE PO STRONIE INTERFEJSU. `prezentacja.py`
#: jest JEDYNYM nosnikiem formatowania kwot w calym projekcie (CLAUDE.md §5).
#: Podmiana znaku w widoku utworzylaby drugi nosnik tej samej reguly — i to
#: taki, ktory rozjezdza sie cicho, bo obie wersje wygladaja prawie tak samo.
MINUS = "\u2212"

#: Myslnik dla stanu „nie wiem". Zero nigdy nie zastepuje braku wiedzy (D11).
BRAK_KWOTY = "—"


def liczba(x: Decimal | float | int) -> str:
    """Kwota w formacie polskim, bez jednostki.

    Osobno od `zloty`, bo `rdzen.prognoza` doklejalo „zl" samo w zdaniu
    („Jestes X zl od progu Y zl") i do Z51 mialo z tego powodu wlasna kopie
    calej reguly razem z wlasna stala separatora.
    """
    # ZAOKRAGLENIE WOLANE Z JEDYNEGO NOSNIKA, nie robione opisem formatu
    # (przeglad Z10, Leo — prog konsolidacji z `testy/test_zaokraglenie_ekranu.py`
    # zadzialal: „przy pierwszej zmianie `prezentacja.liczba`").
    #
    # Do tej zmiany zaokraglenie zapadalo TUTAJ, przez `f"{x:,.2f}"`, czyli
    # regula ROUND_HALF_EVEN z domyslnego kontekstu dziesietnego — a silnik
    # liczy ROUND_HALF_UP. Zmierzone 2026-08-29, trzy z szesciu wartosci
    # dawaly INNY GROSZ:
    #     0.145  -> silnik 0,15   ekran 0,14
    #     0.005  -> silnik 0,01   ekran 0,00
    #    12.345  -> silnik 12,35  ekran 12,34
    # W aplikacji podatkowej znaczylo to, ze ekran i przelew moga sie roznic
    # groszem — i ze roznica jest niewidoczna, bo obie liczby wygladaja
    # poprawnie.
    #
    # `Decimal(str(x))` PRZED wolaniem jest SWIADOME i wezsze niz mogloby byc:
    # `pieniadz.do_groszy` odmawia liczby zmiennoprzecinkowej, a ta funkcja
    # ma w sygnaturze `float` i dzis go przyjmuje. To osobna wada, opisana
    # jako dlug z progiem w naglowku tego pliku — naprawiam REGULE
    # ZAOKRAGLENIA, nie przy okazji granice typu.
    sformatowana = (f"{pieniadz.do_groszy(Decimal(str(x))):,.2f}"
                    .replace(",", SEPARATOR_TYSIECY).replace(".", ","))
    # Minus TYLKO na poczatku — D-58. Zamiana globalna byla by szersza niz
    # regula: dywiz wystepuje takze w datach ISO, ktore przechodza przez
    # sasiednie funkcje tego modulu.
    if sformatowana.startswith("-"):
        return MINUS + sformatowana[1:]
    return sformatowana


def zloty(x: Decimal | float | int | None) -> str:
    """Kwota w formacie polskim, ze spacjami nierozdzielajacymi i jednostka."""
    if x is None:
        return BRAK_KWOTY
    return f"{liczba(x)}{SEPARATOR_TYSIECY}zł"


def procent(x: Decimal) -> str:
    """8,5% zamiast 8,500% — `normalize` obcina zera nieznaczace."""
    wartosc = (Decimal(str(x)) * 100).normalize()
    return f"{wartosc}".replace(".", ",") + "%"


def rola_alokacji(alokacja: budzet.Alokacja) -> str:
    """Rola koloru karty „Do alokacji" — JEDYNY nosnik tej reguly.

    Trzy stany, nie dwa. Brak planu (`kwota is None`) jest **neutralny**:
    zielony znaczylby „wszystko gra", a przeciez nie wiemy nic. To ta sama
    regula co decyzja D11 po stronie tekstu („brak planu to napis, nie zero"),
    tylko po stronie koloru — i tak samo jak tam, zero jest stanem DOBRYM
    (budzet spiety co do grosza), wiec dostaje zielen.

    Przed Z45 ta regula stala przepisana w `pulpit/dashboard.py` i
    `pulpit/budzet.py` — obie kopie mialy te sama wade (`kwota or 0`
    zamienialo brak planu w zero), wiec poprawienie jednej zostawiloby druga.
    """
    if alokacja.kwota is None:
        return "neutralny"
    return "przychody" if alokacja.kwota >= 0 else "blad"


def opis_alokacji(alokacja: budzet.Alokacja) -> tuple[str, str]:
    """Zwraca (tekst glowny, podpis) karty „Wolne srodki".

    Czysta funkcja, a nie kod wewnatrz karty, bo TO jest decyzja o tym, co
    uzytkownik zobaczy — a takie decyzje maja u nas straznikow, w odroznieniu
    od ukladu graficznego.

    Podpis niesie CALY wzor, lacznie z podatkami: to jedyne miejsce, w ktorym
    da sie sprawdzic, czemu liczba jest taka, a nie inna.
    """
    if alokacja.kwota is None:
        return ("Brak planu w wybranym okresie",
                "skopiuj plan z poprzedniego miesiąca albo dodaj pozycje "
                "w zakładce Budżet")
    podpis = ("plan przychodów − zaplanowane wydatki − oszczędności "
              "− podatki; tyle zostanie, gdy poniesiesz wszystko z planu")
    if alokacja.miesiecy_z_planem < alokacja.miesiecy_w_okresie:
        podpis += (f" · uwaga: plan obejmuje "
                   f"{alokacja.miesiecy_z_planem} z "
                   f"{alokacja.miesiecy_w_okresie} miesięcy okresu")
    return (zloty(alokacja.kwota), podpis)


#: Podpis w pasku aplikacji przy bazie domyslnej. Wolny od nazwy pliku
#: swiadomie — nazwa przy kazdym uruchomieniu bylaby szumem i przestalaby
#: znaczyc „uwaga, to nie Twoja baza".
PODPIS_ZRODLA_DOMYSLNY = "finanse osobiste i JDG · dane wyłącznie lokalnie"


def podpis_zrodla(opis: "OpisBazy") -> str:
    """Co pasek aplikacji mowi o zrodle danych.

    Tryb awarii, przed ktorym to broni, brzmi „patrzylem w niewlasciwa baze
    i wygladalo dobrze" (plan Z52). Sama zmienna srodowiskowa go nie zamyka —
    zamyka go dopiero WIDOCZNOSC tego, co zostalo otwarte.

    Nazwa pliku, nie sciezka: sciezka w pasku to szum, a szum sie przestaje
    czytac.
    """
    if opis.domyslna:
        return PODPIS_ZRODLA_DOMYSLNY
    return f"{PODPIS_ZRODLA_DOMYSLNY} · baza: {opis.sciezka.name}"


#: Nazwy miesiecy w mianowniku — „wrzesien 2026". Nosnik przeniesiony tutaj
#: z `pulpit/wspolne.py` w Z65: trzecim konsumentem stala sie warstwa HTTP,
#: ktora `pulpit/` importowac NIE MOZE (granica z `test_granice.py`).
MIESIACE = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
            "lipiec", "sierpień", "wrzesień", "październik", "listopad",
            "grudzień"]

#: Nazwy miesiecy w dopelniaczu — forma po slowie „od". Nosnik stoi tutaj,
#: bo od Z54 tej samej listy uzywa pasek ustawien i (od Z62) zastrzezenia
#: prognozy. `pulpit/wspolne.py` ma wlasna kopie od Z50; konsolidacja jest
#: DLUGIEM JAWNYM z progiem: przy pierwszej zmianie ktorejkolwiek z list
#: `pulpit.wspolne.MIESIACE_DOPELNIACZ` staje sie re-eksportem tej.
#: DLUG SPLACONY w Z65 (2026-08-27): prog „pierwsza zmiana ktorejkolwiek
#: z list" zadzialal, gdy warstwa HTTP potrzebowala nazw miesiecy —
#: `pulpit.wspolne` re-eksportuje obie listy, nie powtarza ich.
MIESIACE_DOPELNIACZ = ["stycznia", "lutego", "marca", "kwietnia", "maja",
                       "czerwca", "lipca", "sierpnia", "września",
                       "października", "listopada", "grudnia"]


def podpis_dzialalnosci(od) -> str:
    """Co ekran mowi o dacie rozpoczecia dzialalnosci.

    Brak daty to „nie wiem" z POWODEM (specyfikacja §5.2), nigdy zero i nigdy
    milczenie: bez tej daty rezerwa ZUS nie ma z czego sie policzyc, a pusty
    ekran wyglada jak brak skladek do zaplacenia.
    """
    if od is None:
        return ("Data rozpoczęcia działalności nie została podana — "
                "bez niej nie policzę rezerwy na ZUS.")
    return f"Działalność od {MIESIACE_DOPELNIACZ[od.month - 1]} {od.year}."


def podpis_rezerwy(rezerwa) -> str:
    """Podpis kafelka „Zarezerwowane na podatki" — jeden nosnik tego zdania.

    Nazywa REGULE, nie tylko kwote. Do Z55 ZUS liczyl sie z kolumny
    `zaplacony_zus`, czyli z liczby FAKTUR; teraz z liczby MIESIECY
    dzialalnosci. Bez tego zdania te dwie liczby wygladaja identycznie —
    a roznia sie o pelna skladke za kazdy miesiac bez zlecenia.

    Rozbicie faktury w zakladce JDG odpowiada na inne pytanie („co mi z niej
    zostaje") niz rezerwa („ile mam odlozyc"). Te liczby MAJA PRAWO sie
    roznic; wada polegala na pokazaniu jednej pod etykieta drugiej.
    """
    czesci = [f"naliczone {zloty(rezerwa.naliczone_razem)} "
              f"− zapłacone {zloty(rezerwa.zaplacone)}; "
              f"te pieniądze nie są Twoje"]
    if rezerwa.miesiace_zus is None:
        czesci += list(rezerwa.zastrzezenia)
    else:
        czesci.append(
            f"ZUS z {rezerwa.miesiace_zus} miesięcy działalności, "
            f"nie z liczby faktur — miesiąc bez zlecenia też ma składkę")
    return " · ".join(czesci)


#: Nazwy form po polsku. Nosnik jest jeden, bo tych samych napisow uzywa pole
#: wyboru w Ustawieniach i podpis pod nim.
NAZWY_FORM = {
    "SKALA": "skala podatkowa (zasady ogólne)",
    "RYCZALT": "ryczałt od przychodów ewidencjonowanych",
}


def podpis_formy(forma: "FormaRoku") -> str:
    """Co ekran mowi o formie opodatkowania na dany rok.

    Stan `NIEROZSTRZYGNIETA` daje POLECENIE, nie kwote i nie milczenie
    (plan formy, Z29). Milczenie wygladalo by jak „wszystko ustawione".
    """
    if forma.forma == "NIEROZSTRZYGNIETA":
        return (f"Wskaż formę opodatkowania na rok {forma.rok} — "
                f"aplikacja jej nie zgadnie. Bez niej nie policzy rezerwy "
                f"ani rozbicia faktury.")
    nazwa = NAZWY_FORM.get(forma.forma, forma.forma)
    if forma.stawka_ryczaltu is not None:
        return f"Rok {forma.rok}: {nazwa}, stawka {procent(forma.stawka_ryczaltu)}."
    return f"Rok {forma.rok}: {nazwa}."


def ostrzezenia_formy(rok: int) -> tuple[str, ...]:
    """Dwa ostrzezenia przy wyborze formy (plan formy, Z29).

    (a) Zapis w aplikacji NIE jest zgloszeniem do urzedu — to jest ta klasa
    pomylki, ktora kosztuje rok rozliczenia.
    (b) Przy roku 2026 dodatkowo termin i skutek milczenia (§0 planu formy).
    """
    ostrzezenia = [
        "Zapis w aplikacji NIE jest zgłoszeniem do urzędu. Zmiana formy "
        "wymaga oświadczenia złożonego w ustawowym terminie — aplikacja "
        "tylko liczy według tego, co jej wskażesz.",
    ]
    if rok == 2026:
        ostrzezenia.append(
            "Rok 2026: oświadczenie o wyborze innej formy składa się "
            "do 20.10.2026. Milczenie zostawia skalę podatkową — także "
            "na lata następne, do czasu zmiany.")
    return tuple(ostrzezenia)


def etykieta_okresu(okres: str) -> str:
    """„2026-09" -> „wrzesien 2026". Jeden nosnik dla pulpitu i warstwy HTTP.

    Przegladarka nigdy nie sklada nazw miesiecy sama — z tego samego powodu,
    z ktorego nie formatuje kwot: bylaby drugim nosnikiem.
    """
    rok, miesiac = str(okres).split("-")
    return f"{MIESIACE[int(miesiac) - 1]} {rok}"


def etykieta_okresu_dopelniacz(okres: str) -> str:
    """Nazwa okresu w formie po slowie „od": „od sierpnia 2026"."""
    rok, miesiac = str(okres).split("-")
    return f"{MIESIACE_DOPELNIACZ[int(miesiac) - 1]} {rok}"


def odmien_pozycje(ile: int) -> str:
    """Liczebnik z odmienioną frazą „pilna pozycja" — JEDEN NOŚNIK odmiany.

    Cztery formy polskie, nie dwie:

    * `1`            → „1 pilną pozycję"   (biernik liczby pojedynczej)
    * `2`–`4`        → „2 pilne pozycje"
    * `5`+           → „5 pilnych pozycji"
    * `12`–`14`      → jak `5`+, mimo końcówki 2–4

    Ostatnia reguła jest tą, która wypada z każdej naiwnej implementacji,
    dlatego strażnik sprawdza `12` i `22` obok siebie.

    Wydzielone z `podpis_straznika` przy poprawce W4-rundy: zdanie o strażniku
    mówiło „znalazł 1 pilne pozycje" — jedyny nośnik odmiany po polsku
    odmieniał źle, a to zdanie idzie na pasek jako sygnał od mechanizmu
    mającego budzić przy braku pieniędzy.
    """
    ostatnia = ile % 10
    dwie_ostatnie = ile % 100
    if ile == 1:
        return f"{ile} pilną pozycję"
    if 2 <= ostatnia <= 4 and not 12 <= dwie_ostatnie <= 14:
        return f"{ile} pilne pozycje"
    return f"{ile} pilnych pozycji"


def podpis_zrodel(raport) -> str:
    """Zdanie o stanie sprawdzenia stawek u źródła — JEDEN NOŚNIK.

    TRZY STANY, NIE DWA (reguła D11). Obok „zgodne" i „rozbieżne" istnieje
    `None`: **nikt jeszcze nie sprawdzał**. Od Z77 stara aplikacja czyta
    raport z podręcznego zapisu (`weryfikacja.z_cache`) zamiast odpytywać
    pięć stron rządowych przy każdym starcie — a podręczny zapis przed
    pierwszym przebiegiem strażnika w tle po prostu nie istnieje.

    Tego stanu NIE WOLNO zwinąć do żadnego z dwóch pozostałych ani podmienić
    wartością zastępczą: „nikt nie pytał" to nie jest „wszystko się zgadza",
    a cisza na pasku jest zakazana wprost (§5.1). Aplikacja finansowa, która
    milczy o tym, czy jej liczby ktokolwiek potwierdził, wygląda dokładnie
    tak samo jak aplikacja, która je potwierdziła.

    Raport niezerowy oddaje SWÓJ komunikat bez przeredagowania — to też jest
    §5.1: komunikat rdzenia dociera w całości. Ta funkcja nie jest tu po to,
    żeby go poprawiać, tylko po to, żeby czwarty przypadek miał gdzie
    mieszkać. Strażnicy: `test_podpis_zrodel_BRAK_raportu_to_ZDANIE_a_nie_cisza`
    i `test_podpis_zrodel_ODDAJE_komunikat_rdzenia_BEZ_przeredagowania`
    (mutacje M414, M415).

    Typ argumentu podany opisowo, a nie importem `weryfikacja.Raport`:
    `prezentacja` nie zależy dziś od `weryfikacja` i nie ma powodu zaczynać.
    """
    if raport is None:
        return ("Nikt jeszcze nie sprawdzał stawek u źródła. Liczby pochodzą "
                "z rejestru w aplikacji i są niepotwierdzone. Sprawdza je "
                "strażnik w tle, raz dziennie.")
    return raport.komunikat


def podpis_straznika(przebieg: "dict | None", dzis: date) -> str:
    """Zdanie o strażniku w tle — JEDEN NOŚNIK. Wołają je pasek nowego
    ekranu i log przebiegu.

    Powód, dla którego to zdanie w ogóle istnieje, jest w specyfikacji §5.4:
    brak powiadomienia znaczy jednocześnie „nic pilnego" i „nie zadziałałem",
    a te dwa stany wymagają przeciwnych reakcji.

    KOLEJNOŚĆ GAŁĘZI JEST REGUŁĄ, NIE STYLEM. Gałąź „nie wiem" stoi PRZED
    gałęzią „nic pilnego": kolumna `pilnych` jest `INTEGER NOT NULL` i przy
    stanie „nie wiem" zapisuje `0`, więc samo `pilnych == 0` nie odróżnia
    „sprawdziłem i jest dobrze" od „nie wiem, czy jest dobrze". Rozróżnienie
    niesie `stan_prognozy`. Strażnik: `test_ZERO_pilnych_przy_stanie_NIE_WIEM_
    NIE_uspokaja`, mutacja M394.

    Wszystkie trzy pola przebiegu czytane są TWARDO (`przebieg["…"]`).
    Miękkie `.get("stan_prognozy")` dawało przy literówce w nazwie kolumny
    `None`, warunek nie zachodził i funkcja mówiła „nic pilnego nie znalazł" —
    cichy powrót dokładnie do stanu, przed którym broni gałąź wyżej.
    Strażnik: `test_BRAK_klucza_stan_prognozy_to_awaria_GLOSNA_nie_uspokojenie`,
    mutacja M398.

    Stan na Z75, zmierzony: WOŁAJĄCYCH JESZCZE NIE MA. Pakiet `straznik/`
    nie istnieje, trasy `/api/straznik` w `api/router.py` nie ma. Nośnik
    powstaje PIERWSZY po to, żeby przebieg w tle (Z76) i pasek nowego ekranu
    nie złożyły tego zdania każdy po swojemu — nie dlatego, że ktoś już go
    woła. To zdanie przestaje być prawdziwe w chwili dopięcia Z76.
    """
    if przebieg is None:
        return ("Strażnik w tle NIGDY nie działał — nikt nie sprawdzał "
                "Twoich terminów poza tym oknem.")
    kiedy = datetime.fromisoformat(str(przebieg["kiedy"]))
    ile_dni = (dzis - kiedy.date()).days
    # `<=`, nie `==`. Ujemna liczba dni znaczy przebieg SWIEZSZY niz dzien,
    # o ktory pytamy — zegar przestawiony o dobe albo przebieg tuz po
    # polnocy. Bez tej galezi zdanie brzmi „-1 dni temu": napis, ktorego
    # nikt nie napisal celowo. Straznik:
    # `test_przebieg_Z_PRZYSZLOSCI_czyta_sie_jak_DZIS_...` (mutacja M395).
    if ile_dni <= 0:
        kiedy_slowem = "dziś"
    elif ile_dni == 1:
        kiedy_slowem = "wczoraj"
    else:
        kiedy_slowem = f"{ile_dni} dni temu"
    godzina = kiedy.strftime("%H:%M")
    pilnych = int(przebieg["pilnych"])
    # Kolejnosc galezi jest regula — uzasadnienie w docstringu wyzej.
    if pilnych:
        co = f"znalazł {odmien_pozycje(pilnych)}"
    elif str(przebieg["stan_prognozy"]) == "nie_wiem":
        co = "nie policzył prognozy (brakuje danych)"
    else:
        co = "nic pilnego nie znalazł"
    return f"Ostatnie sprawdzenie: {kiedy_slowem} {godzina} — {co}."


def podpis_terminu(dni_do: int) -> str:
    """Ile zostało do terminu, po polsku. Zero to „dziś", nie „za 0 dni".

    OSTRZEŻENIE DLA NASTĘPNEGO WOŁAJĄCEGO: liczba UJEMNA czyta się tu też
    jako „dziś", czyli termin PRZETERMINOWANY wygląda jak dzisiejszy.
    Dziś nieosiągalne, bo `co_mnie_czeka.zbuduj` odsiewa `dni_do < 0`
    i na oś terminów takie pozycje nie trafiają. Kto zawoła tę funkcję
    z innego miejsca, musi albo odsiać ujemne sam, albo dołożyć tu gałąź
    „po terminie" razem ze strażnikiem — obecne zachowanie jest granicą
    zakresu Z75, nie rozstrzygnięciem, że przeterminowane to dziś.
    """
    if dni_do <= 0:
        return "dziś"
    if dni_do == 1:
        return "jutro"
    return f"za {dni_do} dni"


#: Tytul kafelka nad kwota `budzet.pozostalo_do_zaplacenia(...).pozostalo`.
#: JEDEN nosnik napisu (v1.17) — `pulpit/` i kazdy przyszly widok go WOLAJA.
#:
#: Do 2026-08-28 kafelek nosil tytul „Zaplanowane wydatki" i pokazywal pod nim
#: reszte planu PO WYKONANIU, powiekszona o rezerwe podatkowa. Tytul mowil
#: o planie, podpis tej samej karty o reszcie, a liczba byla ta druga.
#: Regula, ktora z tego wynika: `docs/2026-08-28-regula-etykieta-opisuje-liczbe.md`.
TYTUL_DO_ZAPLACENIA = "Zostało do zapłacenia"


def podpis_do_zaplacenia(stan) -> str:
    """Z czego SKLADA sie kwota kafelka — jedno zdanie pod liczba.

    Rezerwa podatkowa wchodzi do tej kwoty i musi byc NAZWANA, bo potrafi
    odwrocic jej wymowe: przy planie przekroczonym o 859,49 zl i rezerwie
    2 576,00 zl kafelek pokazuje dodatnie 1 716,51 zl. Dodatnie wylacznie
    dlatego, ze zawiera pieniadze, ktore nie sa uzytkownika.

    Przy rezerwie zerowej zdanie o niej NIE PADA — obietnica skladnika,
    ktorego nie ma, jest tym samym rodzajem klamstwa co zly tytul.
    """
    if stan.podatki:
        return "reszta planu wydatków + rezerwa na podatki"
    return "reszta planu wydatków w tym okresie"


def opis_do_zaplacenia(stan) -> list[str]:
    """Wiersze pod kwota kafelka „Zostało do zapłacenia".

    Sama kwota nie mowi, ile z niej to plan, a ile danina — a to sa dwie
    rozne rzeczy: plan da sie zmienic, terminu podatku nie.

    PRZEKROCZENIE PODAJE WIELKOSC, NIE SAMO SLOWO. Poprzednie brzmienie —
    „plan wydatkow przekroczony — kwota nizej niz powinna" — mowilo
    uzytkownikowi rzecz przeciwna do prawdy: kwota jest ZAWYZONA rezerwa,
    a nie zanizona. Wielkosc bierze sie z `stan.nadwyzka`, czyli z tego
    samego nosnika co `przekroczony_plan`.

    Ton: informuje, nie alarmuje (§4.3 fundamentu UI). Ten kafelek Darek
    oglada codziennie, a ostrzezenie widziane trzydziesci razy w miesiacu
    przestaje byc ostrzezeniem.
    """
    wiersze = [f"z planu {zloty(stan.zaplanowane)} "
               f"· zapłacone {zloty(stan.zaplacone)}"]
    if stan.podatki:
        wiersze.append(f"w tym podatki i ZUS: {zloty(stan.podatki)}")
    if stan.przekroczony_plan:
        wiersze.append("plan wydatków przekroczony o "
                       f"{zloty(stan.nadwyzka)}")
    return wiersze


# --- ekran Ksiegowanie (Z6) ----------------------------------------------

#: Nazwy miesiecy w MIEJSCOWNIKU — forma po slowie „w". TRZECI przypadek obok
#: mianownika (`MIESIACE`) i dopelniacza (`MIESIACE_DOPELNIACZ`), a nie ich
#: wariant: „0 w wrzesien" i „0 w wrzesnia" sa oba zle po polsku, a to zdanie
#: idzie na ekran Ksiegowania dwa razy — jako licznik wpisow
#: (`NAPISY.licznikWpisow` w `interfejs/lib/napisy.ts`) i jako etykieta
#: pierwszego wiersza karty „Co ruszy ten wpis".
#:
#: Nosnik stoi tutaj, a nie w module ekranu, z tego samego powodu co dwie
#: listy wyzej: nazwy miesiecy po polsku maja w tym projekcie JEDNO miejsce
#: (CLAUDE.md §5, wiersz „Napisy i formatowanie kwot").
MIESIACE_MIEJSCOWNIK = ["styczniu", "lutym", "marcu", "kwietniu", "maju",
                        "czerwcu", "lipcu", "sierpniu", "wrześniu",
                        "październiku", "listopadzie", "grudniu"]

#: Tytul trzeciego wiersza karty „Co ruszy ten wpis", per typ wpisu. Napis
#: skladany z typu („Plan " + typ + " wykonany") dawalby „Plan Wydatki
#: wykonany" — dopelniacz nie wynika z mianownika przez doklejenie.
TYTUL_PLANU_WYKONANEGO = {
    "Przychody": "Plan przychodów wykonany",
    "Wydatki": "Plan wydatków wykonany",
    "Oszczędności": "Plan oszczędności wykonany",
}


def procent_wykonania(x: "Decimal | None") -> str:
    """Procent wykonania planu z JEDNYM miejscem po przecinku: „10,5%".

    OSOBNO OD `procent`, a nie zamiast niego — to sa dwie rozne rzeczy i
    zwiniecie ich w jedna zepsuloby obie:

    * `procent` bierze UŁAMEK (0,085) i obcina zera nieznaczace („8,5%",
      ale tez „0%"). Sluzy stawkom podatkowym, gdzie „8,5%" i „8,50%" to ta
      sama stawka, a zero nie wystepuje;
    * ta funkcja bierze PUNKTY PROCENTOWE (`budzet.Wykonanie.procent`, czyli
      wykonane/planowane*100) i zawsze pokazuje jedno miejsce po przecinku.
      Ramka `Ksiegowanie.dc.html` niesie „0,0%" obok „10,5%" — kolumna liczb
      o roznej liczbie miejsc po przecinku czyta sie jako blad, a nie jako
      precyzja.

    `None` znaczy „planu nie ma", nie „zero procent" (`budzet.Wykonanie`
    §procent). Zero klamaloby, ze wydatek zmiescil sie w budzecie.
    """
    if x is None:
        return BRAK_KWOTY
    return f"{Decimal(str(x)).quantize(Decimal('0.1'))}".replace(".", ",") + "%"


def odmien_kategorie(ile: int) -> str:
    """Liczebnik z odmieniona fraza „kategoria" w MIANOWNIKU — jeden nosnik.

    Cztery formy polskie, te same co w `odmien_pozycje`, ale w innym
    przypadku gramatycznym: tam fraza stoi po „znalazl" (biernik), tutaj po
    „stoja" (mianownik). Wspolna implementacja musialaby przyjac przypadek
    jako argument i zwrocic napis skladany z kawalkow — a skladanie napisu
    z kawalkow zabiera straznikowi zakresu mozliwosc znalezienia frazy.
    """
    ostatnia = ile % 10
    dwie_ostatnie = ile % 100
    if ile == 1:
        return f"{ile} kategoria"
    if 2 <= ostatnia <= 4 and not 12 <= dwie_ostatnie <= 14:
        return f"{ile} kategorie"
    return f"{ile} kategorii"

# -*- coding: utf-8 -*-
"""Strażnik ZAKRESU ekranu Budżet — tego, którego brak sprawia, że prognoza
Płynności pokazuje pustą przyszłość i wygląda lepiej, niż jest.

PODZIAŁ PRACY MIĘDZY BRAMKAMI. Wyglądu pilnuje porównanie zrzutów
(`interfejs/narzedzia/porownaj-z-makieta.mjs`), poprawności liczb — strażnicy
silnika (`test_budzet.py`, `test_magazyn_budzet.py`), a kształtu odpowiedzi —
`test_trasy_budzet.py`. Tutaj stoi to, czego obraz nie widzi: czy fraza z ramki
jest w źródle, czy kosz planu nie zaczął nazywać się „usuń", czy kwota nie
staje się liczbą i czy każda z sześciu tras ma na ekranie wołającego.

DWIE KLASY SPRAWDZEŃ, BO JEDNA NIE WYSTARCZA. Sprawdzenia TREŚCI pytają
„czy ta rzecz jest taka, jaka ma być"; sprawdzenia LICZNOŚCI pytają „ile
rzeczy pomiar w ogóle zobaczył". Bez tych drugich obchód po pustym zbiorze
melduje sukces — zmierzone w tej sesji dziesięć razy.
"""
import pathlib
import re

from pomocnicze import bez_komentarzy

KATALOG = pathlib.Path(__file__).resolve().parent.parent

EKRAN = KATALOG / "interfejs" / "app" / "budzet" / "ekran.tsx"
WEJSCIE = KATALOG / "interfejs" / "app" / "budzet" / "page.tsx"
PANEL = KATALOG / "interfejs" / "app" / "budzet" / "panel-planu.tsx"
PANEL_CELU = KATALOG / "interfejs" / "app" / "budzet" / "panel-celu.tsx"
STYL = KATALOG / "interfejs" / "app" / "budzet" / "style.module.css"
NAPISY = KATALOG / "interfejs" / "lib" / "napisy.ts"
DANE = KATALOG / "interfejs" / "lib" / "dane" / "budzet.ts"
KWOTA = KATALOG / "interfejs" / "lib" / "kwota.ts"
KONTRAKT_TS = KATALOG / "interfejs" / "lib" / "kontrakt.ts"
TRASY = KATALOG / "api" / "trasy.py"
SILNIK = KATALOG / "silnik" / "ekran_budzet.py"
RAMKI = KATALOG / "makiety"
RAMKA = RAMKI / "Budzet.dc.html"

#: Zrodla EKRANU — pliki, w ktorych czegos NIE WOLNO znalezc.
ZRODLA_EKRANU = (EKRAN, WEJSCIE, PANEL, PANEL_CELU, DANE)


def _polacz(zrodla) -> str:
    obecne = [p for p in zrodla if p.exists()]
    # KONTROLA LICZNOSCI. Sprawdzenie, do ktorego nic nie dociera, melduje
    # sukces: po przemianowaniu pliku kazda asercja „tej frazy NIE MA"
    # przechodzilaby na pustym tekscie.
    assert len(obecne) == len(zrodla), (
        f"brak plików ekranu Budżet: {sorted(set(zrodla) - set(obecne))}")
    return "\n".join(bez_komentarzy(p.read_text(encoding="utf-8")) for p in obecne)


def _tekst_ekranu() -> str:
    return _polacz(ZRODLA_EKRANU)


def _tekst_z_napisami() -> str:
    return _polacz(ZRODLA_EKRANU + (NAPISY,))


# --- TRESC: frazy z ramki ---------------------------------------------------

#: Frazy przeniesione z `makiety/Budzet.dc.html`. Kazda z nich NAZYWA rzecz,
#: ktorej brak zmienia znaczenie ekranu, a nie jego wyglad — wiec bramka
#: odwzorowania ich nie zlapie.
FRAZY_Z_RAMKI = (
    "Budżet",
    "Wydatki osobiste z planu",     # tytul kafelka — sklada silnik
    "Rezerwa na podatki",
    "Plan miesiąca razem",
    "Bilans planu",
    "tyle zostanie, gdy zrealizujesz plan co do złotówki",
    "Plan kontra wykonanie",
    "największe odchylenie u góry",
    "Dodaj pozycję planu",
    "Cele oszczędnościowe",
    "postęp liczy się z wpisów w kategorii celu, nie z ręcznie wpisanej liczby",
    "Dodaj cel",
    "Historia",
    "zaznacz wiersz, żeby poprawić pomyłkę",
    "Usuń zaznaczone",
    "Odchylenie",
    "Wykonanie",
    "Postęp",
)


def test_kazda_fraza_z_ramki_JEST_na_ekranie():
    """§3.6: makieta jest wiążącą specyfikacją ZAKRESU, nie tylko wyglądu.

    Trzy frazy mieszkają po stronie silnika (tytuły kafelków — bo §3.5 wiąże
    etykietę z liczbą, a obie mają wychodzić z jednego miejsca), więc szukamy
    ich także tam. Kontrola liczności: ramka musi zostać faktycznie odczytana.
    """
    assert RAMKA.exists(), "nie ma ramki Budzet.dc.html"
    tresc_ramki = RAMKA.read_text(encoding="utf-8")
    assert len(tresc_ramki) > 10_000, "ramka Budżetu jest podejrzanie krótka"

    gdzie = _tekst_z_napisami() + "\n" + bez_komentarzy(SILNIK.read_text(encoding="utf-8"))
    sprawdzonych = 0
    brakujace = []
    for fraza in FRAZY_Z_RAMKI:
        assert fraza in tresc_ramki, f"ramka nie niesie frazy {fraza!r} — spis do przeliczenia"
        sprawdzonych += 1
        if fraza not in gdzie:
            brakujace.append(fraza)
    assert sprawdzonych == len(FRAZY_Z_RAMKI), "pomiar nie objął wszystkich fraz"
    assert brakujace == [], f"frazy z ramki, których nie ma na ekranie: {brakujace}"


# --- TRESC: kosz konczy regule, nie kasuje ---------------------------------


def test_kosz_planu_KONCZY_regule_i_MOWI_O_TYM_trzy_razy():
    """Z-9. Gdy Darek „wyrzuca" pozycję planu, historia się NIE zmienia —
    wcześniejsze miesiące nadal pokazują, że pozycja była zaplanowana i ile
    z niej wykonano. Zmienia się wyłącznie przyszłość.

    Ekran ma to mówić w TRZECH miejscach naraz, bo każde z nich człowiek
    czyta osobno: w napisie kontrolki, w zdaniu potwierdzenia i w metodzie
    żądania. Sprawdzenie samego jednego przechodziłoby przy kontrolce, która
    nazywa się „Zakończ", a wywołuje `DELETE`.
    """
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    dane = bez_komentarzy(DANE.read_text(encoding="utf-8"))
    panel = bez_komentarzy(PANEL.read_text(encoding="utf-8"))

    # (1) napis kontrolki niesie slowo „Zakoncz" I miesiac, od ktorego skutek
    #     obowiazuje — §3.5: stan wyjatkowy podaje WIELKOSC, nie samo slowo.
    zakoncz = re.search(r"zakonczOd:\s*\([^)]*\)\s*=>\s*`([^`]*)`", napisy)
    assert zakoncz, "nie znalazłem brzmienia kontrolki końca reguły"
    assert "Zakończ" in zakoncz.group(1), (
        f"kontrolka końca reguły brzmi teraz: {zakoncz.group(1)!r}")
    assert "${" in zakoncz.group(1), "napis nie niesie miesiąca, od którego skutek obowiązuje"

    # (2) zdanie potwierdzenia mowi wprost, co sie NIE zmieni.
    potwierdzenie = re.search(
        r"potwierdzenieZakonczenia:\s*\([^)]*\)\s*=>\s*\n?\s*`([^`]*)`", napisy)
    assert potwierdzenie, "nie znalazłem zdania potwierdzenia końca reguły"
    assert "Wcześniejsze miesiące zostają bez zmian" in potwierdzenie.group(1), (
        f"potwierdzenie brzmi teraz: {potwierdzenie.group(1)!r} — nie mówi, "
        "że historia zostaje nietknięta")

    # (3) metoda zadania. `DELETE` obiecywalby usuniecie, a tu nic sie nie usuwa.
    zakonczenie = re.search(
        r"export function zakonczPozycjePlanu.*?\n}", dane, re.S)
    assert zakonczenie, "nie znalazłem funkcji kończącej pozycję planu"
    assert '"POST"' in zakonczenie.group(0), "koniec reguły nie idzie metodą POST"
    assert "/zakoncz" in zakonczenie.group(0), "koniec reguły nie woła trasy /zakoncz"

    # Zadne slowo o kasowaniu nie ma prawa stac przy planie — ani w kontrolce,
    # ani w warstwie danych. „Usun zaznaczone" dotyczy WPISOW, nie planu,
    # i mieszka w innym miejscu (`NAPISY_BUDZETU`), wiec panel go nie zna.
    for zakazane in ("Usuń", "usuń", "Skasuj", "skasuj", "DELETE"):
        assert zakazane not in panel, f"słowo o kasowaniu w panelu pozycji planu: {zakazane}"


def test_zadna_trasa_planu_NIE_JEST_kasujaca():
    """Kontrola liczności PO STRONIE INTERFEJSU. Odpowiednik strażnika
    `test_nosniki.py::test_kosz_planu_KONCZY_regule_a_nie_kasuje`, który
    pilnuje spisu tras — tutaj pilnujemy WOŁAJĄCEGO. Trasa może nie istnieć,
    a `fetch` i tak da się napisać ręcznie."""
    dane = bez_komentarzy(DANE.read_text(encoding="utf-8"))
    kasujace = re.findall(r'metoda:\s*"DELETE"[^}]*?', dane)
    # Jedyne dozwolone kasowanie na tym ekranie dotyczy WPISU, nie planu.
    wywolania = re.findall(r'wywolaj<[^>]*>\(\s*`?([^`",]+)`?[^)]*metoda:\s*"DELETE"',
                           dane, re.S)
    assert len(kasujace) <= 1, f"więcej niż jedno kasowanie w danych Budżetu: {kasujace}"
    for adres in wywolania:
        assert "/plan" not in adres, f"kasowanie celuje w plan: {adres}"
        assert "/api/wpisy" in adres, f"nieznane kasowanie: {adres}"


# --- TRESC: kwota zostaje napisem ------------------------------------------


def test_kwota_NIE_STAJE_SIE_liczba_nigdzie_na_ekranie():
    """§3.1. Zmierzona awaria u poprzednika: warstwa sieciowa zamieniała
    `Decimal` na `float`, gubiła grosze i ZWRACAŁA 200. Wariant znaleziony
    w tej sesji kłamie nawet napisem: „8623.10" wychodziło jako „8623.1".

    `Number()` wolno w tych plikach dotknąć wyłącznie LICZNIKÓW — dnia
    miesiąca, cyklu i numeru dnia z daty — w których nie ma groszy do
    zgubienia. Rozstrzyga to, co stoi w tej samej linii."""
    for plik in ZRODLA_EKRANU:
        kod = bez_komentarzy(plik.read_text(encoding="utf-8"))
        for zakazane in ("parseFloat", "parseInt", "toFixed", "valueAsNumber"):
            assert zakazane not in kod, f"{zakazane} w {plik.name}"
        for numer, wiersz in enumerate(kod.splitlines(), 1):
            if "Number(" not in wiersz:
                continue
            wolno = any(s in wiersz for s in
                        ("dzien", "Dzien", "cykl", "Cykl", "licznik", "Licznik"))
            assert wolno, f"{plik.name}:{numer} zamienia coś na liczbę: {wiersz.strip()!r}"


def test_ekran_NIE_MA_wpisanej_recznie_kwoty():
    """Kwota w komponencie to drugi nośnik danych — i pierwszy kandydat do
    rozjazdu z silnikiem przy najbliższej zmianie rachunku."""
    for plik in (EKRAN, PANEL, PANEL_CELU, DANE):
        kod = bez_komentarzy(plik.read_text(encoding="utf-8"))
        assert re.findall(r"\d+[,.]\d{2}\s*zł", kod) == [], (
            f"kwota wpisana ręcznie w {plik.name}")


# --- TRESC: zero i brak wiedzy to dwie rozne rzeczy ------------------------


def test_odmowa_silnika_NIE_STAJE_SIE_zerem():
    """`kwota: null` znaczy NIE POLICZYŁEM, a nie zero. Zero pod tytułem
    „Rezerwa na podatki" czyta się jako „nic nie jesteś winien urzędowi" —
    czyli najlepsza możliwa odpowiedź podana wtedy, gdy nie ma żadnej.
    To ta sama klasa wady co forma opodatkowania zgadnięta wartością
    domyślną (regula D11)."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "k.kwota === null" in ekran, (
        "ekran nie rozpoznaje odmowy silnika — kafelek pokaże zero zamiast zdania")
    assert "k.wyjasnienie" in ekran, "ekran nie pokazuje, czego silnikowi zabrakło"
    # Zastrzezenie przy kwocie, ktora JEST — musi stac przy tej liczbie (§3.5).
    assert "k.kwota !== null && k.wyjasnienie" in ekran, (
        "zastrzeżenie silnika nie stoi przy liczbie, której dotyczy")


def test_kafelki_BIERZE_SIE_PO_KLUCZU_nie_po_indeksie():
    """Kolejność tablicy `kafelki` jest własnością silnika, nie umową
    z widokiem. Odczyt po indeksie przeżyłby przestawienie kafelków w silniku
    i podstawiłby rezerwę podatkową pod tytuł „Wydatki osobiste z planu"."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    trafienia = re.findall(r"kafelki\s*\[\s*\d+\s*\]", ekran)
    assert trafienia == [], f"kafelek brany po indeksie: {trafienia}"
    assert "k.klucz" in ekran, "kafelki nie są identyfikowane kluczem"


def test_link_zmiany_STOI_TYLKO_przy_JEDNEJ_pozycji_planu():
    """`idPozycjiPlanu === null` znaczy „zero pozycji ALBO więcej niż jedna" —
    w obu przypadkach „popraw tę pozycję" nie ma jednej odpowiedzi. Link
    postawiony bezwarunkowo otwierałby panel bez pozycji albo z przypadkową."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert ekran.count("idPozycjiPlanu === null") >= 2, (
        "ekran nie sprawdza, czy za wierszem stoi dokładnie jedna pozycja planu — "
        "sprawdzenie ma być i przy otwieraniu panelu, i przy rysowaniu kontrolki")


# --- TRESC: zdania, ktore nie moga klamac ---------------------------------


def test_stan_pusty_NIE_TWIERDZI_ujemnego_bilansu_gdy_bilans_JEST_ZEREM():
    """WYKRYTE OBEJRZENIEM EKRANU, NIE TESTEM (sierpień 2026, żywy silnik).

    Ramka pisze jednym ciągiem: „nie zaplanowałeś ani przychodu, ani
    oszczędności — dlatego bilans planu jest ujemny o całą kwotę wydatków",
    bo NA RAMCE bilans jest ujemny. W miesiącu bez ani jednej pozycji planu
    bilans wynosi 0,00 zł, a zdanie twierdziło, że jest ujemny — cztery
    centymetry poniżej liczby, która mówi co innego (§3.5)."""
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))

    bez_przychodow = re.search(r"bezPrzychodow:\s*\([^)]*\)\s*=>\s*\n?\s*`([^`]*)`", napisy)
    assert bez_przychodow, "nie znalazłem stanu pustego grupy przychodów"
    assert "ujemny" not in bez_przychodow.group(1), (
        f"zdanie bezwarunkowe twierdzi ujemny bilans: {bez_przychodow.group(1)!r}")
    assert "bezPrzychodowOgon" in napisy, "brak warunkowego ogona zdania"
    assert "bilansUjemny && NAPISY_BUDZETU.bezPrzychodowOgon" in ekran, (
        "ogon zdania nie jest uzależniony od znaku bilansu")


def test_miesiac_bez_planu_NIE_PODAJE_zera_jako_wyniku():
    """PRD §12.8: pusty miesiąc pokazuje stan pusty z wejściem do działania,
    NIGDY zera udającego wynik. „Z planu 0,00 zł nie wydałeś jeszcze nic"
    jest formalnie prawdziwe i podaje zero jako wynik tam, gdzie planu nie ma
    wcale. Wykryte obejrzeniem ekranu, nie testem."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    assert "DANE.pozycjePlanu.length === 0" in ekran, (
        "ekran nie odróżnia miesiąca bez planu od miesiąca z planem zerowym")
    assert "bezPlanu:" in napisy, "brak brzmienia dla miesiąca bez planu"
    assert "NAPISY_BUDZETU.bezPlanu(" in ekran, "brzmienie bez planu nie ma wołającego"


def test_ekran_NIE_WPISUJE_nazw_miesiecy_na_sztywno():
    """Ramka pisze „ta sama liczba wraca w listopadzie i w grudniu" — zdanie
    prawdziwe wyłącznie w październiku. Nazwa miesiąca wpisana w brzmienie
    kłamie w każdym innym miesiącu, a żaden test liczb tego nie widzi."""
    tekst = _tekst_z_napisami()
    miesiace = ("stycznia", "styczniu", "lutego", "lutym", "marca", "marcu",
                "kwietnia", "kwietniu", "maja", "maju", "czerwca", "czerwcu",
                "lipca", "lipcu", "sierpnia", "sierpniu", "września", "wrześniu",
                "października", "październiku", "listopada", "listopadzie",
                "grudnia", "grudniu")
    # `lib/kwota.ts` NIESIE tablicę odmiany i to jest jej rola — jeden nośnik
    # na cały interfejs. Tutaj sprawdzamy zdania, nie tablicę.
    znalezione = [m for m in miesiace if m in tekst]
    assert znalezione == [], (
        f"nazwa miesiąca wpisana w brzmienie ekranu Budżet: {znalezione}. "
        "Zdanie z nazwą miesiąca jest prawdziwe w jednym miesiącu na dwanaście.")


def test_ekran_NIE_MOWI_o_formie_opodatkowania():
    """Darek jest na SKALI PODATKOWEJ. Ryczałt jest wadą, nie opcją domyślną —
    w poprzedniej aplikacji był wartością domyślną w trzech miejscach i podawał
    kwoty wyliczone formą, której Darek nie ma. Kafelek „Rezerwa na podatki"
    idzie przez rachunek podatkowy, więc to jest ekran, na którym forma mogłaby
    się przemycić."""
    tekst = _tekst_z_napisami()
    for slowo in ("ryczałt", "Ryczałt", "ryczalt", "liniowy", "liniowa"):
        assert slowo not in tekst, f"forma opodatkowania na ekranie Budżet: {slowo}"
    # Kontrola liczności po drugiej stronie: ramka też ma być czysta.
    assert "ryczał" not in RAMKA.read_text(encoding="utf-8").lower()


def test_styl_NIE_MA_wpisanej_recznie_barwy():
    """Każda barwa idzie ze zmiennej. Wartość szesnastkowa to drugi nośnik
    palety — rozjazd o jeden ton łamie bramkę odwzorowania, a oba pliki nadal
    wyglądają na zadbane."""
    # BEZ KOMENTARZY — proza wyjaśniająca regułę nie jest jej złamaniem.
    # Nagłówek klasy `.linkCichy` CYTUJE barwę z ramki (`a { color: … }`),
    # żeby powiedzieć, skąd ona jest. Ten wzorzec zaczerwienił strażników
    # w tym projekcie już trzy razy (M3 w Z1, M-Z7-1c w Z7, przegląd Z10)
    # i po raz czwarty tutaj — na pierwszym przebiegu tego pliku.
    wpisane = re.findall(r"#[0-9A-Fa-f]{3,8}\b",
                         bez_komentarzy(STYL.read_text(encoding="utf-8")))
    assert wpisane == [], f"barwy wpisane ręcznie w {STYL.name}: {wpisane}"


def test_zapis_ODDAJE_odswiezony_ekran_zamiast_pytac_drugi_raz():
    """Jeden zapis planu rusza NARAZ trzy kafelki, bilans, tabelę i licznik
    nagłówka. Odpowiedź `POST`/`PUT` niesie je w komplecie, więc drugi odczyt
    dla jednej chwili byłby drugim nośnikiem każdej z tych liczb."""
    for plik in (PANEL, PANEL_CELU):
        kod = bez_komentarzy(plik.read_text(encoding="utf-8"))
        for zakazane in ("router.refresh", "location.reload", "pobierzBudzet"):
            assert zakazane not in kod, (
                f"{zakazane} w {plik.name} — to drugi przebieg rachunku planu "
                "dla jednej chwili")
        assert "poZapisie(" in kod, f"{plik.name} nie oddaje odświeżonego ekranu"


def test_wycofanie_wpisu_ODPYTUJE_BUDZET_bo_trasa_oddaje_inny_ekran():
    """JEDYNY dozwolony drugi odczyt na tym ekranie — i stoi z powodem.
    `DELETE /api/wpisy/{id}` należy do Księgowania i oddaje `DaneKsiegowania`.
    Złożenie z tamtej odpowiedzi danych Budżetu w przeglądarce byłoby drugim
    nośnikiem całego rachunku planu.

    PRÓG: gdy trasa zacznie oddawać ekran wołającego, drugie wywołanie znika."""
    dane = bez_komentarzy(DANE.read_text(encoding="utf-8"))
    funkcja = re.search(r"export async function wycofajWpisZBudzetu.*?\n}", dane, re.S)
    assert funkcja, "brak wycofania wpisu z ekranu Budżet"
    assert '"DELETE"' in funkcja.group(0), "wycofanie wpisu nie kasuje wpisu"
    assert "pobierzBudzet(" in funkcja.group(0), (
        "wycofanie nie odświeża Budżetu — ekran pokazałby stan sprzed wycofania")


# --- LICZNOSC: ile rzeczy pomiar zobaczyl ---------------------------------


def _trasy_budzetu() -> list:
    """Ścieżki tras ekranu Budżet — Z JEDYNEGO SPISU, nie z listy wpisanej tu.

    Lista wpisana w teście rozjechałaby się ze spisem przy pierwszej nowej
    trasie i strażnik nadal meldowałby sukces."""
    zrodlo = TRASY.read_text(encoding="utf-8")
    return re.findall(r'Trasa\(\s*"(\w+)",\s*"([^"]+)",\s*"budzet"', zrodlo)


def test_KAZDA_z_szesciu_tras_Budzetu_MA_WOLAJACEGO_na_ekranie():
    """TO JEST STRAŻNIK KLASY W8, powtórzony świadomie. W W8 cała warstwa pod
    spodem była gotowa i NIKT jej nie wołał: trasa stała, funkcja była
    napisana i miała zero wołających, a człowiek nie miał gdzie wpisać stanu
    konta. Zielona suita tego nie widzi — kod poprawny, testy przechodzą,
    funkcji nikt nie używa.

    Mierzymy POŁĄCZENIE, nie istnienie: trasa → funkcja danych → komponent."""
    trasy = _trasy_budzetu()
    # Kontrola licznosci: spis musi zostac faktycznie odczytany.
    assert len(trasy) == 6, f"spis tras oddał {len(trasy)} tras Budżetu zamiast sześciu: {trasy}"

    dane = bez_komentarzy(DANE.read_text(encoding="utf-8"))
    bez_wolajacego = []
    for metoda, sciezka in trasy:
        # `{id}` w spisie odpowiada `${id}` w napisie adresu po stronie widoku.
        wzorzec = sciezka.replace("{id}", "${id}")
        if wzorzec not in dane:
            bez_wolajacego.append(f"{metoda} {sciezka}")
    assert bez_wolajacego == [], (
        f"trasy Budżetu bez wołającego w warstwie danych: {bez_wolajacego}")


def test_KAZDA_funkcja_danych_Budzetu_MA_WOLAJACEGO_w_komponencie():
    """Druga połowa tego samego pytania. Funkcja danych z zerem wołających
    jest tym samym, czym była `zapiszKotwice` przed W8 — napisaną warstwą,
    do której człowiek nie ma drogi."""
    dane = bez_komentarzy(DANE.read_text(encoding="utf-8"))
    funkcje = re.findall(r"export (?:async )?function (\w+)", dane)
    # Kontrola licznosci: siedem funkcji (szesc tras + wycofanie wpisu).
    assert len(funkcje) == 7, f"warstwa danych Budżetu ma {len(funkcje)} funkcji: {funkcje}"

    komponenty = "\n".join(
        bez_komentarzy(p.read_text(encoding="utf-8"))
        for p in (EKRAN, WEJSCIE, PANEL, PANEL_CELU))
    bez_wolajacego = [f for f in funkcje if f"{f}(" not in komponenty]
    assert bez_wolajacego == [], (
        f"funkcje danych bez wołającego — warstwa gotowa, człowiek bez drogi: "
        f"{bez_wolajacego}")


def test_KAZDE_pole_kontraktu_Budzetu_MA_CZYTAJACEGO():
    """Pole kontraktu, którego nikt nie czyta, to obietnica bez odbiorcy:
    silnik je liczy, granica je przenosi, a człowiek go nie widzi. Ten
    strażnik nie mówi, GDZIE pole ma stać — mówi tylko, że ktoś po nie sięga."""
    kontrakt = bez_komentarzy(KONTRAKT_TS.read_text(encoding="utf-8"))
    blok = re.search(r"export interface DaneBudzetu \{(.*?)\n\}", kontrakt, re.S)
    assert blok, "nie znalazłem kształtu DaneBudzetu w kontrakcie"
    pola = re.findall(r"^\s{2}(\w+)\??:", blok.group(1), re.M)
    # Kontrola licznosci — kontrakt niesie 19 pol (naglowek „EKRAN BUDZET").
    assert len(pola) == 19, f"DaneBudzetu ma {len(pola)} pól zamiast 19: {pola}"

    czytajacy = "\n".join(
        bez_komentarzy(p.read_text(encoding="utf-8"))
        for p in (EKRAN, PANEL, PANEL_CELU))
    # `miesiacKopiujZ` jest SWIADOMIE nieczytane przez widok: zrodlo kopii
    # wyprowadza silnik tym samym nosnikiem, ktorym sklada napis przycisku
    # (`napisKopiujZ`). Podane z przegladarki byloby drugim nosnikiem.
    ZNANE_NIECZYTANE = {"miesiacKopiujZ"}
    bez_czytajacego = {p for p in pola if f".{p}" not in czytajacy} - ZNANE_NIECZYTANE
    assert bez_czytajacego == set(), (
        f"pola kontraktu, których ekran nie czyta: {sorted(bez_czytajacego)}")


# --- LICZNOSC: dlugi z jawnym progiem -------------------------------------


def test_ramka_Budzetu_NIE_RYSUJE_kontrolki_zmiany_ani_konca_reguly():
    """ODSTĘPSTWO OD §3.6, ZAPISANE JAWNIE — nie milcząca decyzja wykonawcy.

    Ekran ma dwie trasy, dla których ramka nie rysuje żadnego elementu:
    `PUT /api/plan/{id}` i `POST /api/plan/{id}/zakoncz`. Wiersze kategorii
    w tabeli to gołe `<span>`, a jedyny kosz na ramce stoi w Historii i dotyczy
    transakcji. Rozstrzygnięcie Mili (`docs/2026-08-29-spis-ekran-budzet.md`
    §4): nazwa kategorii staje się kontrolką i otwiera panel w trybie zmiany.

    Ten strażnik pilnuje PRAWDZIWOŚCI zdania wyżej: gdy Mila dorysuje te dwa
    elementy, test się zaczerwieni i każe odwzorować ramkę zamiast dalej
    improwizować. PRÓG: pierwsza ramka Budżetu z kontrolką zmiany pozycji."""
    ramki = sorted(RAMKI.glob("Budzet*.dc.html"))
    # Kontrola licznosci: sprawdzenie po pustym zbiorze meldowaloby sukces.
    assert len(ramki) >= 2, f"pomiar objął tylko {len(ramki)} ramek Budżetu"
    z_kontrolka = []
    for plik in ramki:
        tresc = plik.read_text(encoding="utf-8")
        for fraza in ("Zmień pozycję", "Zakończ tę pozycję", "Zmień pozycję planu"):
            if fraza in tresc:
                z_kontrolka.append(f"{plik.name}: {fraza}")
    assert z_kontrolka == [], (
        f"ramka rysuje już kontrolkę zmiany albo końca reguły: {z_kontrolka} — "
        "odstępstwo wygasło, panel trzeba odwzorować z ramki")


def test_popraw_zaznaczony_CZEKA_na_trase_zmiany_wpisu():
    """DŁUG JAWNY, ze strażnikiem i progiem. Ramka rysuje w Historii odsyłacz
    „Popraw zaznaczony", a w całym spisie 36 tras NIE MA trasy zmiany wpisu —
    jest wyłącznie `DELETE /api/wpisy/{id}`. Odsyłacz, który nic nie robi,
    jest gorszy niż jego brak (§3.7), więc ekran go nie rysuje.

    PRÓG: pierwsza trasa zmieniająca wpis. Wtedy ten test się zaczerwieni
    i każe kontrolkę z ramki narysować."""
    assert "Popraw zaznaczony" in RAMKA.read_text(encoding="utf-8"), (
        "ramka przestała rysować »Popraw zaznaczony« — dług trzeba przeliczyć")
    zrodlo = TRASY.read_text(encoding="utf-8")
    zmiana_wpisu = re.findall(r'Trasa\(\s*"(?:PUT|PATCH)",\s*"(/api/wpisy[^"]*)"', zrodlo)
    assert zmiana_wpisu == [], (
        f"trasa zmiany wpisu już istnieje: {zmiana_wpisu} — próg osiągnięty, "
        "»Popraw zaznaczony« trzeba narysować")


def test_prog_poduszki_CZEKA_na_pole_kontraktu():
    """DŁUG JAWNY (PRD §10.3, rozstrzygnięcie S-2). Próg poduszki finansowej
    ma być LICZONY — sześciokrotność wydatków niezbędnych — a wartość
    nadpisana ręcznie widocznie oznaczona. `CelNaEkranie` nie niesie ani
    liczonego progu, ani znacznika nadpisania, a `POST /api/cele` przyjmuje
    wyłącznie kwotę wpisaną. Wyliczenie tego w przeglądarce byłoby drugim
    nośnikiem reguły budżetowej i nie miałoby skąd wziąć „wydatków
    niezbędnych".

    Ekran mówi o tym wprost, zamiast udawać, że liczba pochodzi z rachunku.
    PRÓG: pole liczonego progu albo znacznika nadpisania w `CelNaEkranie`."""
    kontrakt = bez_komentarzy(KONTRAKT_TS.read_text(encoding="utf-8"))
    blok = re.search(r"export interface CelNaEkranie \{(.*?)\n\}", kontrakt, re.S)
    assert blok, "nie znalazłem kształtu CelNaEkranie"
    for pole in ("progWyliczony", "nadpisanyRecznie", "kwotaWyliczona"):
        assert pole not in blok.group(1), (
            f"kontrakt niesie już `{pole}` — próg osiągnięty, oznaczenie "
            "wartości nadpisanej trzeba narysować")
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    assert "progRecznie:" in napisy, "ekran milczy o tym, że kwota celu jest ręczna"


def test_kontrolka_Wybrany_miesiac_ZOSTAJE_poza_zakresem():
    """Rozstrzygnięcie Mili (spis §7): fraza „Wybrany miesiąc" ma nośnik
    wyłącznie w opisie Raportów — nigdzie w opisie Budżetu. §3.6 czyni
    zakresem to, co ramka OBIECUJE człowiekowi; element bez opisanej funkcji
    niczego nie obiecuje.

    PRÓG: opis funkcji tej kontrolki w dokumentacji Budżetu."""
    assert "Wybrany miesiąc" in RAMKA.read_text(encoding="utf-8"), (
        "ramka przestała rysować drugi selektor — rozstrzygnięcie do przeliczenia")
    tekst = _tekst_z_napisami()
    assert "Wybrany miesiąc" not in tekst, (
        "ekran buduje kontrolkę, której funkcji nikt nie opisał")

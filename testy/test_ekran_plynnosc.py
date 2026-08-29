# -*- coding: utf-8 -*-
"""Strażnik ZAKRESU ekranu Płynność — pierwszego, który Darek otwiera.

Wyglądu pilnuje porównanie zrzutów, a geometrii wykresu `testy/wykres.test.ts`
(porównanie znak po znaku z atrybutem `d` z ramki). Tutaj stoi to, czego obraz
nie widzi: czy każda fraza z ramki jest w źródle, czy nie dołożono rzeczy
jawnie wykluczonych i czy liczby nie wjechały do komponentu.
"""
import pathlib
import re

from pomocnicze import bez_komentarzy

KATALOG = pathlib.Path(__file__).resolve().parent.parent

# W7: ekran przeniesiony z `app/page.tsx` pod swoj wlasny klucz, zeby
# odsylacz paska `/plynnosc` prowadzil do niego, a nie do strony 404.
# Straznik idzie za ekranem do jego nowego nosnika.
EKRAN = KATALOG / "interfejs" / "app" / "plynnosc" / "page.tsx"
NAPISY = KATALOG / "interfejs" / "lib" / "napisy.ts"
DANE = KATALOG / "interfejs" / "lib" / "dane" / "plynnosc.ts"
WYKRES = KATALOG / "interfejs" / "lib" / "wykres.ts"
STYL = KATALOG / "interfejs" / "app" / "plynnosc" / "style.module.css"
EKRANY = KATALOG / "interfejs" / "lib" / "ekrany.ts"
POWLOKA_CSS = KATALOG / "interfejs" / "app" / "powloka.css"
KARTA = KATALOG / "interfejs" / "lib" / "karta-dzialania.ts"
RAMKI = KATALOG / "makiety"
# Po podpieciu (Z7) czesc frazy z ramki — „Stan na dziś", dopisek kotwicy —
# przeszla z warstwy danych DO SILNIKA, bo to on sklada ksiege plynnosci.
# Straznik idzie za frazą do jej nowego nosnika, zamiast obnizyc wymaganie.
SILNIK = KATALOG / "silnik" / "ekran_plynnosc.py"

FRAZY_Z_RAMKI = (
    "Najniżej",              # etykieta wielkiej liczby
    "Co mnie czeka",         # jedyne wezwanie na ekranie
    "Stan na dziś",          # kotwica wewnątrz prognozy
    "Ostatnie sprawdzenie",  # stopka strażnika
    "Księga płynności",
    "Saldo po tym dniu",
    "pod kreską",
    "Masz ",
    "Co mam zrobić",   # karta stoi na tym ekranie od D-54
)


def _zrodla() -> list[pathlib.Path]:
    """Zrodla, w ktorych czegos NIE WOLNO znalezc — sam interfejs."""
    return [EKRAN, NAPISY, DANE, WYKRES, STYL, KARTA]


def _zrodla_frazy() -> list[pathlib.Path]:
    """Zrodla, w ktorych fraza z ramki MOZE mieszkac — razem z silnikiem."""
    return _zrodla() + [SILNIK]


def _polacz(zrodla: list[pathlib.Path]) -> str:
    obecne = [p for p in zrodla if p.exists()]
    # Kontrola liczności: sprawdzenie, do którego nic nie dociera, melduje
    # sukces. Bez tej asercji przemianowanie pliku dałoby zielone testy.
    assert len(obecne) == len(zrodla), f"brak plików ekranu: {set(zrodla) - set(obecne)}"
    return "\n".join(bez_komentarzy(p.read_text(encoding="utf-8")) for p in obecne)


def _tekst_ekranu() -> str:
    return _polacz(_zrodla())


def test_kazda_fraza_z_ramki_JEST_na_ekranie():
    brakujace = [f for f in FRAZY_Z_RAMKI if f not in _polacz(_zrodla_frazy())]
    assert brakujace == [], f"frazy z ramki, których nie ma na ekranie: {brakujace}"


def test_etykieta_NAJNIZEJ_stoi_przy_wielkiej_liczbie():
    """Bez niej wielka liczba stoi w wierszu VAT-u i czyta się jako kwota
    VAT-u. To jest zmiana ZNACZENIA ekranu, nie jego wyglądu, więc obraz jej
    nie złapie — bramka odwzorowania widziałaby tylko „mniej pikseli"."""
    napisy = bez_komentarzy(NAPISY.read_text(encoding="utf-8"))
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    # Trafiamy w TEN KLUCZ, nie w plik. Zmierzone (przebieg Z2, mutacja P1):
    # sprawdzenie „słowo »Najniżej« jest gdzieś w nośniku" przechodziło mimo
    # podmiany właśnie tego brzmienia, bo słowo stało jeszcze przy drugim,
    # nieużywanym kluczu. Drugi klucz skasowany, sprawdzenie zawężone.
    klucz = re.search(r"najnizej:\s*\([^)]*\)\s*=>\s*`([^`]*)`", napisy)
    assert klucz, "nie znalazłem brzmienia etykiety wielkiej liczby w nośniku"
    assert "Najniżej" in klucz.group(1), (
        f"etykieta wielkiej liczby brzmi teraz: {klucz.group(1)!r}. "
        "Bez slowa Najnizej liczba stoi w wierszu VAT-u i czyta sie jako kwota VAT-u."
    )
    assert "NAPISY_PLYNNOSCI.najnizej(" in ekran, "ekran nie woła etykiety wielkiej liczby"


def test_ekran_NIE_MA_wpisanej_recznie_kwoty():
    """Kwota w komponencie to drugi nośnik danych."""
    kod = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert re.findall(r"\d+[,.]\d{2}\s*zł", kod) == []


def test_kwota_STAJE_SIE_liczba_tylko_w_module_wykresu():
    """§3.1: liczba zmiennoprzecinkowa w ścieżce kwoty gubi grosze. Rysunek
    wymaga współrzędnych, więc gdzieś kwota musi przestać być napisem — ale
    dokładnie w JEDNYM miejscu, i tym miejscem jest `lib/wykres.ts`,
    z którego wychodzą wyłącznie piksele."""
    for plik in (EKRAN, DANE, KATALOG / "interfejs" / "lib" / "kwota.ts"):
        kod = bez_komentarzy(plik.read_text(encoding="utf-8"))
        for zakazane in ("parseFloat", "parseInt", "Number(p.saldo", "Number(kwota"):
            assert zakazane not in kod, f"{zakazane} w {plik.name}"


def test_ekran_NIE_KLAMIE_o_ratach_spoza_planu():
    """Zdanie „Prognoza ich NIE dolicza" mówi nieprawdę: prognoza te raty
    odejmuje, tylko drugą drogą, jako pozycje planu. Kontrola Leo, §4.2."""
    assert "NIE dolicza" not in _tekst_ekranu()


def test_ekran_NIE_MA_kafelkow_z_innego_pytania():
    """Przychody / wydatki / oszczędności odpowiadają na inne pytanie i mają
    inny ekran. Jeden ekran na jedno pytanie."""
    tekst = _tekst_ekranu()
    for slowo in ("Przychody", "Oszczędności", "Poduszka", "Cele oszczędnościowe"):
        assert slowo not in tekst, f"kafelek z innego pytania: {slowo}"


def test_werdykt_NIE_DOSTAJE_ikony():
    """Werdykt niosą już słowo, barwa i pozycja. Ikona byłaby trzecim
    nośnikiem tej samej rzeczy, czyli szumem."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    blok = ekran[ekran.index("s.werdykt") : ekran.index("s.wierszWezwania")]
    assert "svg" not in blok.lower(), "ikona w bloku werdyktu"


def test_prognoza_JEST_kreska_przerywana():
    """Linia ciągła twierdziłaby wiedzę; to jest przewidywanie. Różnicę
    niesie kształt kreski, nie barwa (bramka: barwa nie jest jedynym
    nośnikiem znaczenia)."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert ekran.count("strokeDasharray") >= 2, "prognoza albo odcinek pod kreską są ciągłe"


def test_ekran_NIE_POWTARZA_reguly_saldo_raz_na_dzien():
    """Regula „saldo bite RAZ NA DZIEN" ma po podpieciu JEDEN nosnik i jest nim
    `silnik/kontrakt.py::zbij_saldo_raz_na_dzien` (straznik:
    `test_kontrakt_dwa_nosniki.py::test_ksiega_bije_saldo_RAZ_NA_DZIEN`,
    mutacja M-Z6-4). Do Z6 druga kopia reguly stala w danych ekranu i tamten
    egzemplarz mierzyl wlasnie ten plik.

    Tutaj zostaje POLOWA po stronie ekranu, i tylko ona: ekran ma DOSTAC
    `null` i narysowac puste miejsce, a NIE liczyc, ktora pozycja jest
    pierwsza w swoim dniu. Gdyby liczyl, regula mialaby tyle nosnikow, ile
    ekranow niesie ksiege (dzis dwa: Plynnosc i Co mnie czeka)."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "w.saldoPoDniu === null" in ekran, (
        "ekran nie rozpoznaje pustego salda — musi je dostac, nie policzyc")
    # Zakaz liczenia reguly u siebie: zaden warunek na ekranie nie porownuje
    # dnia BIEZACEJ pozycji z dniem NASTEPNEJ po to, zeby ukryc saldo.
    # (Porownanie dni na potrzeby KRESKI miedzy dniami zostaje — to uklad,
    # nie regula o liczbie; stad zawezenie do `saldoPoDniu` w tym samym
    # wyrazeniu.)
    for wiersz in ekran.splitlines():
        if "saldoPoDniu" in wiersz and ("tenSamDzien" in wiersz or "kontynuacja" in wiersz):
            raise AssertionError(
                f"ekran liczy regule salda u siebie: {wiersz.strip()!r}")


def test_kotwica_NIESIE_WIEK_odczytu():
    """Kotwica stoi wewnątrz prognozy, drobnym drukiem, z wiekiem odczytu.
    Osobna karta obok była wadą nazwaną na Z67.

    Po podpięciu (Z7) dopisek składa silnik — `_dopisek_kotwicy` — bo to on
    zna datę odczytu. Strażnik mierzy więc DWIE połowy: że silnik go składa
    i że ekran go rysuje. Sprawdzenie samej połowy przechodziłoby przy
    dopisku, którego nikt nie pokazuje, i przy ekranie rysującym pustkę."""
    silnik = bez_komentarzy(SILNIK.read_text(encoding="utf-8"))
    assert "dopisek=" in silnik, "silnik nie składa dopisku kotwicy"
    assert "z odczytu" in silnik, "dopisek nie mówi, skąd wzięło się saldo"
    assert "MIESIACE_DOPELNIACZ" in silnik, "dopisek nie niesie dnia odczytu"

    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "w.dopisek" in ekran, "ekran nie rysuje dopisku kotwicy"
    assert "s.dopisek" in ekran, "dopisek nie dostaje własnego, drobnego stopnia"


def test_podwojna_linia_jest_ATRAMENTEM_nie_liniatura():
    """Podwójna kreska zamknięcia NIESIE znaczenie; liniatura wierszy jest
    dowiedzioną dekoracją (1,29:1). Gdyby wyglądały tak samo, oko wrzuciłoby
    niosącą do klasy ozdobnych."""
    css = bez_komentarzy(STYL.read_text(encoding="utf-8"))
    kreska = re.search(r"\.kreska\s*\{[^}]*\}", css)
    assert kreska, "brak klasy podwójnej linii"
    assert "--atrament-cichy" in kreska.group(0), "podwójna linia rysowana liniaturą"


def test_styl_NIE_MA_wpisanej_recznie_barwy():
    """Każda barwa idzie ze zmiennej. Wartość szesnastkowa to drugi nośnik
    palety — rozjazd o jeden ton łamie bramkę odwzorowania, a oba pliki
    nadal wyglądają na zadbane."""
    for plik in (STYL, KATALOG / "interfejs" / "app" / "ksiegowanie" / "style.module.css"):
        wpisane = re.findall(r"#[0-9A-Fa-f]{3,8}\b", plik.read_text(encoding="utf-8"))
        assert wpisane == [], f"barwy wpisane ręcznie w {plik.name}: {wpisane}"


def test_ekran_NIE_MOWI_o_formie_opodatkowania():
    """Darek jest na skali podatkowej. Ryczałt jest wadą, nie opcją domyślną."""
    tekst = _tekst_ekranu()
    for slowo in ("ryczałt", "Ryczałt", "ryczalt", "liniowy"):
        assert slowo not in tekst, f"forma opodatkowania na ekranie płynności: {slowo}"


# --- znak słowny: dwa nośniki jednej rzeczy, które już raz się rozjechały ---

# Wzorzec trafia w znak słowny nagłówka, nie w dowolne wystąpienie słowa:
# szuka spanu o wadze 700 i wersalikach, czyli dokładnie tej roli.
WZORZEC_ZNAKU = re.compile(
    r'font-weight: 700; letter-spacing: (0\.\d+)em; text-transform: uppercase;">([^<]+)<'
)


def test_znak_slowny_MA_JEDNA_wartosc_w_kodzie_i_w_ramkach():
    """D-57. Ramki niosły „AI CFO", kod „Doradca" — dwa nośniki jednej rzeczy,
    rozjechane w ciągu doby. Ten strażnik czerwieni się, gdy znów powiedzą
    co innego, i podaje, która strona odstaje."""
    kod = re.search(r'ZNAK_SLOWNY = "([^"]+)"', EKRANY.read_text(encoding="utf-8"))
    assert kod, "nie znalazłem stałej ZNAK_SLOWNY w lib/ekrany.ts"
    z_kodu = kod.group(1)

    trafienia = []
    for plik in sorted(RAMKI.glob("*.dc.html")):
        trafienia += [(plik.name, s, w) for s, w in WZORZEC_ZNAKU.findall(plik.read_text(encoding="utf-8"))]

    # Kontrola liczności: pomiar, do którego nic nie dociera, melduje sukces.
    # Znak słowny stoi w każdej ramce niosącej nagłówek — tych jest kilkadziesiąt.
    assert len(trafienia) >= 30, f"wzorzec znaku słownego trafił tylko {len(trafienia)} razy"

    odstajace = sorted({(n, w) for n, _, w in trafienia if w != z_kodu})
    assert odstajace == [], (
        f"kod niesie {z_kodu!r}, a ramki co innego: {odstajace}"
    )

    # ŚWIATŁO. Wiążące są ramki, które aplikacja odwzorowuje; ramki
    # kierunków odrzuconych (pismo ręczne, §12.3 nośnika projektowego) nie
    # są ekranami i zostały przy 0,16 em. Sprawdzamy więc dwie rzeczy:
    # (a) każda ramka WIĄŻĄCA niesie 0,12 em,
    # (b) odstępstwa nie wychodzą poza znany zbiór eksploracji — gdyby
    #     doszła trzecia ramka z innym światłem, ten strażnik ją pokaże.
    WIAZACE = {
        "Main.dc.html", "Main-Ciemny.dc.html", "Main-Dobrze.dc.html",
        "NieWiem.dc.html", "Ksiegowanie.dc.html", "CoMamZrobic.dc.html",
    }
    ZNANE_EKSPLORACJE = {"Main-Reka.dc.html", "Main-Reka-Papier.dc.html"}

    zle_wiazace = sorted({(n, s) for n, s, _ in trafienia if n in WIAZACE and s != "0.12"})
    assert zle_wiazace == [], f"ramki wiążące ze światłem innym niż 0,12 em: {zle_wiazace}"
    # Kontrola liczności: wszystkie sześć ramek wiążących musi mieć znak słowny,
    # inaczej sprawdzenie wyżej przechodzi na pustym zbiorze.
    zmierzone_wiazace = {n for n, _, _ in trafienia} & WIAZACE
    assert zmierzone_wiazace == WIAZACE, f"bez znaku słownego: {sorted(WIAZACE - zmierzone_wiazace)}"

    odstepstwa = {n for n, s, _ in trafienia if s != "0.12"}
    assert odstepstwa <= ZNANE_EKSPLORACJE, (
        f"nowe ramki ze światłem innym niż 0,12 em: {sorted(odstepstwa - ZNANE_EKSPLORACJE)}"
    )

    css = re.search(r"\.znak-slowny\s*\{[^}]*letter-spacing:\s*([0-9.]+)em", POWLOKA_CSS.read_text(encoding="utf-8"))
    assert css, "nie znalazłem światła znaku słownego w powloce"
    assert css.group(1) == "0.12", f"powłoka niesie światło {css.group(1)}em zamiast 0.12em"


def test_pelna_nazwa_aplikacji_ZOSTAJE_w_tytule_okna():
    """D-47 nazywa aplikację, D-57 tylko napis w pasku. Nazwa nie może zniknąć
    z systemu — stoi w tytule okna."""
    layout = (KATALOG / "interfejs" / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert "Doradca Finansowy" in layout


# --- drabina wielkości: 56 / 28 / 20 / 15 ---


def test_kotwica_STOI_STOPIEN_WYZEJ_niz_salda_posrednie():
    """Test pięciu sekund przechodził dla „co mnie czeka", a nie przechodził
    dla „ile mam pieniędzy": stan na dziś stał w tej samej wadze co cztery
    salda pośrednie. 56/28 = 2,00× wobec progu 1,5×."""
    css = bez_komentarzy(STYL.read_text(encoding="utf-8"))
    kotwica = re.search(r"\.komorkaSaldaKotwicy\s*\{[^}]*font-size:\s*(\d+)px", css)
    zamkniecie = re.search(r"\.liczbaZamkniecia\s*\{[^}]*font-size:\s*(\d+)px", css)
    assert kotwica and zamkniecie, "brak stopnia kotwicy albo wiersza zamknięcia"
    assert int(kotwica.group(1)) == 28, f"kotwica ma {kotwica.group(1)}px, ma mieć 28px"
    assert int(zamkniecie.group(1)) == 56, f"zamknięcie ma {zamkniecie.group(1)}px, ma mieć 56px"
    assert int(zamkniecie.group(1)) / int(kotwica.group(1)) >= 1.5

    # Reguła stoi PO `.komorkaSalda`, bo obie mają tę samą szczegółowość
    # i rozstrzyga kolejność. Zmierzone: przy odwrotnej kolejności kotwica
    # zostawała przy 15 px, a strażnik czytający sam arkusz tego nie widział.
    assert css.index(".komorkaSaldaKotwicy") > css.index(".komorkaSalda {"), (
        "reguła kotwicy stoi PRZED `.komorkaSalda` i zostanie przez nią nadpisana"
    )


def test_ekran_WOLA_stopien_kotwicy_dla_wiersza_otwarcia():
    """Sam arkusz stylów nie wystarcza: klasa musi być komuś przypisana."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "s.komorkaSaldaKotwicy" in ekran, "stopień kotwicy nie jest wołany przez ekran"
    assert "w.kwota === null" in ekran, "ekran nie rozpoznaje wiersza otwarcia"


# --- karta „Co mam zrobić" ---


def test_karta_STOI_NA_EKRANIE_miedzy_werdyktem_a_wezwaniem():
    """D-54: karta jest komponentem podrzędnym wobec wiersza zamknięcia
    i stoi między werdyktem a przyciskiem „Co mnie czeka"."""
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert "<KartaDzialania " in ekran, "karty nie ma na ekranie"
    assert ekran.index("s.werdykt") < ekran.index("<KartaDzialania ") < ekran.index("s.wierszWezwania"), (
        "karta stoi poza miejscem wyznaczonym przez D-54"
    )


def test_karta_NIE_ZNIKA_w_zadnym_stanie():
    """Karta znikająca uczy, że jej pojawienie się oznacza kłopot — a to
    buduje odruch nieotwierania aplikacji wtedy, gdy jest najbardziej
    potrzebna. Trzy stany, każdy z własną gałęzią w kodzie."""
    karta = bez_komentarzy(KARTA.read_text(encoding="utf-8"))
    for stan in ('"deficyt"', '"nadwyzka"', '"brak-danych"'):
        assert stan in karta, f"brak stanu karty: {stan}"
    ekran = bez_komentarzy(EKRAN.read_text(encoding="utf-8"))
    assert 'karta.stan === "brak-danych"' in ekran, "ekran nie obsługuje stanu bez danych"


def test_karta_NIE_LICZY_niczego_nowego():
    """Karta czyta `saldoMinimalne` — tę samą liczbę, która stoi w wierszu
    zamknięcia. Własny rachunek byłby drugim nośnikiem tej liczby."""
    karta = bez_komentarzy(KARTA.read_text(encoding="utf-8"))
    for zakazane in ("+", "*", "/", "Number(", "parseFloat"):
        assert f" {zakazane} " not in karta.replace("=>", ""), f"rachunek w karcie: {zakazane}"
    assert "saldoMinimalne" in karta


def test_karta_NIE_DORABIA_drugiego_dzialania():
    """D-56: zakres v1 to dokładnie JEDNO działanie (C1). C2 czeka na
    oprocentowanie zobowiązań — bez niego „zysk na odsetkach" trzeba by
    zmyślić."""
    tekst = _tekst_ekranu()
    for slowo in ("nadpłat", "odsetk", "oprocentowan"):
        assert slowo not in tekst.lower(), f"drugie działanie w karcie: {slowo}"


def test_element_zdjety_decyzja_D55_NIE_WRACA():
    """D-16 (Darek) uchyliła D-10: `9 920,79 + (−10 131,46) = −210,67`, czyli
    co do grosza liczba, którą wiersz zamknięcia pokazuje wyżej na tym samym
    ekranie. Miejscem docelowym jest ekran Budżet."""
    tekst = _tekst_ekranu()
    assert "rozdysponować" not in tekst
    assert "10 131,46" not in tekst and "10131.46" not in tekst

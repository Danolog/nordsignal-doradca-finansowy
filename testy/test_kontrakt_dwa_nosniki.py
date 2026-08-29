# -*- coding: utf-8 -*-
"""STRAZNIK SWIADOMEGO DRUGIEGO NOSNIKA — kontrakt po obu stronach granicy.

DLACZEGO TEN DLUG WOLNO MIEC. `CLAUDE.md` §3.2 mowi: reguła o konsekwencji
zewnetrznej ma jeden nosnik, a swiadomy drugi jest dopuszczalny WYLACZNIE
z testem-strażnikiem i z jawnym progiem konsolidacji. Ksztalt danych zyje
w dwoch plikach, bo granica HTTP dzieli dwa jezyki:

    interfejs/lib/kontrakt.ts   <- WZORZEC (typy powstaly z ekranu)
    silnik/kontrakt.py          <- dopasowuje sie do wzorca

PROG KONSOLIDACJI, JAWNY: **przy pierwszym dopisaniu pola** do ktoregokolwiek
ksztaltu generujemy `kontrakt.ts` z `kontrakt.py` i drugi nosnik znika. Do tego
czasu pilnuje tego ten plik. Odlozenie bez progu byloby dlugiem ukrytym.

KIERUNEK ZGODNOSCI JEST JEDNOSTRONNY I TO NIE JEST DETAL. Oba ekrany sa juz
zbudowane wobec `kontrakt.ts` i przechodza bramke odwzorowania. Gdy straznik
sie czerwieni, poprawia sie PYTHON — chyba ze zmiana po stronie TypeScriptu
byla swiadoma i opisana.

KONTROLA LICZNOSCI JEST TU OBOWIAZKOWA, NIE OZDOBNA. Porownanie zbioru pustego
ze zbiorem pustym przechodzi na zielono i nie widzi niczego: gdyby wzorzec
przestal cokolwiek parsowac — bo ktos zmienil formatowanie pliku albo przeniosl
go gdzie indziej — wszystkie asercje rownosci nadal by przechodzily. Dlatego
kazde porownanie stoi obok liczby, ktora policzylo, a ta liczba jest sprawdzana.
"""

import dataclasses
import re
from decimal import Decimal
from pathlib import Path

import pytest

from silnik import kontrakt

KORZEN = Path(__file__).resolve().parent.parent
WZORZEC = KORZEN / "interfejs" / "lib" / "kontrakt.ts"

#: Minimalna liczba pol, ponizej ktorej pomiar uznajemy za zepsuty, a nie za
#: prawdziwy. Dzis ksztaltow jest dziewiec i niosą 46 pol; prog 40 zostawia
#: miejsce na usuniecie jednego ksztaltu bez faluszywego alarmu, a lapie
#: awarie „parser przestal cokolwiek widziec".
PROG_LICZNOSCI = 40


# --- odczyt wzorca (TypeScript) ------------------------------------------

def _bez_komentarzy(tekst: str) -> str:
    tekst = re.sub(r"/\*.*?\*/", "", tekst, flags=re.S)
    return "\n".join(w.split("//")[0] for w in tekst.splitlines())


def _wzorzec_ts() -> dict[str, dict[str, dict]]:
    """Ksztalty ze wzorca: nazwa -> pole -> {typ, opcjonalne, kwota}."""
    zrodlo = _bez_komentarzy(WZORZEC.read_text(encoding="utf-8"))
    ksztalty: dict[str, dict[str, dict]] = {}
    for nazwa, cialo in re.findall(
            r"export\s+interface\s+(\w+)\s*\{([^}]*)\}", zrodlo):
        pola: dict[str, dict] = {}
        for wiersz in cialo.splitlines():
            m = re.match(r"\s*(\w+)(\??)\s*:\s*(.+?);\s*$", wiersz)
            if not m:
                continue
            pole, znak_zapytania, typ = m.group(1), m.group(2), m.group(3).strip()
            pola[pole] = {
                "typ": typ,
                "opcjonalne": bool(znak_zapytania) or "null" in typ,
                "kwota": bool(re.search(r"\bKwota\b", typ)),
            }
        ksztalty[nazwa] = pola
    return ksztalty


def _aliasy_ts() -> dict[str, str]:
    zrodlo = _bez_komentarzy(WZORZEC.read_text(encoding="utf-8"))
    return dict(re.findall(r"export\s+type\s+(\w+)\s*=\s*([^;]+);", zrodlo))


# --- odczyt strony Pythona ------------------------------------------------

def _ksztalty_py() -> dict[str, dict[str, dict]]:
    ksztalty: dict[str, dict[str, dict]] = {}
    for klasa in kontrakt.KSZTALTY:
        pola: dict[str, dict] = {}
        for f in dataclasses.fields(klasa):
            typ = str(f.type)
            pola[f.name] = {
                "typ": typ,
                "opcjonalne": ("None" in typ
                               or f.default is not dataclasses.MISSING),
                "kwota": bool(re.search(r"\bKwota\b", typ)),
            }
        ksztalty[klasa.__name__] = pola
    return ksztalty


TS = _wzorzec_ts()
PY = _ksztalty_py()
WSPOLNE = sorted(set(TS) & set(PY))


# --- 0. kontrola licznosci — PRZED jakimkolwiek porownaniem ---------------

def test_parser_wzorca_NAPRAWDE_cokolwiek_przeczytal():
    """Bez tego testu cala reszta pliku jest bezwartosciowa.

    Gdyby `_wzorzec_ts` zwrocil pusty slownik — zly plik, zmienione
    formatowanie, przeniesiony katalog — wszystkie porownania nizej
    parametryzowalyby sie po zbiorze pustym i suita bylaby zielona.
    """
    assert WZORZEC.is_file(), f"brak wzorca {WZORZEC}"
    assert len(TS) >= 9, f"parser widzi {len(TS)} ksztaltow we wzorcu: {sorted(TS)}"
    pol = sum(len(p) for p in TS.values())
    assert pol >= PROG_LICZNOSCI, (
        f"parser wzorca przeczytal {pol} pol, prog to {PROG_LICZNOSCI} — "
        f"to nie jest zgodnosc, to slepy pomiar")


def test_strona_pythona_wystawia_komplet_ksztaltow():
    """Kontrola licznosci po drugiej stronie. `KSZTALTY` jest recznie
    utrzymywana krotka, wiec nowy ksztalt moze do niej nie trafic —
    i wtedy nie bylby porownywany z niczym."""
    pol = sum(len(p) for p in PY.values())
    assert len(PY) >= 9, f"po stronie Pythona {len(PY)} ksztaltow: {sorted(PY)}"
    assert pol >= PROG_LICZNOSCI, (
        f"strona Pythona wystawia {pol} pol, prog to {PROG_LICZNOSCI}")


def test_obie_strony_znaja_TE_SAME_ksztalty():
    """Rozjazd na poziomie ksztaltow, nie pol: ksztalt obecny tylko po jednej
    stronie nie zostalby porownany przez zadna z asercji nizej."""
    assert set(TS) == set(PY), (
        f"tylko we wzorcu: {sorted(set(TS) - set(PY))}; "
        f"tylko w Pythonie: {sorted(set(PY) - set(TS))}")
    assert len(WSPOLNE) == len(TS) == len(PY)


# --- 1. nazwy pol ---------------------------------------------------------

@pytest.mark.parametrize("ksztalt", WSPOLNE)
def test_nazwy_pol_sie_ZGADZAJA(ksztalt):
    we_wzorcu, w_pythonie = set(TS[ksztalt]), set(PY[ksztalt])
    assert we_wzorcu, f"{ksztalt}: parser nie przeczytal ANI JEDNEGO pola"
    assert we_wzorcu == w_pythonie, (
        f"{ksztalt}: tylko we wzorcu {sorted(we_wzorcu - w_pythonie)}; "
        f"tylko w Pythonie {sorted(w_pythonie - we_wzorcu)}. "
        f"Wzorcem jest `kontrakt.ts` — poprawia sie Python.")


@pytest.mark.parametrize("ksztalt", WSPOLNE)
def test_OPCJONALNOSC_pol_sie_zgadza(ksztalt):
    """Sama nazwa nie wystarczy. Pole wymagane po jednej stronie i opcjonalne
    po drugiej daje `undefined` tam, gdzie ekran spodziewa sie wartosci —
    i widac to dopiero na ekranie, nie w tescie."""
    we = {p for p, o in TS[ksztalt].items() if o["opcjonalne"]}
    py = {p for p, o in PY[ksztalt].items() if o["opcjonalne"]}
    assert we == py, (
        f"{ksztalt}: opcjonalne tylko we wzorcu {sorted(we - py)}; "
        f"opcjonalne tylko w Pythonie {sorted(py - we)}")


# --- 2. kwoty sa napisami po obu stronach --------------------------------

def test_alias_Kwota_jest_NAPISEM_po_obu_stronach():
    aliasy = _aliasy_ts()
    assert aliasy.get("Kwota", "").strip() == "string", (
        f"wzorzec: Kwota = {aliasy.get('Kwota')!r}, ma byc `string`")
    assert aliasy.get("Data", "").strip() == "string"
    assert kontrakt.Kwota is str, "Python: Kwota ma byc `str`"
    assert kontrakt.Data is str, "Python: Data ma byc `str`"


@pytest.mark.parametrize("ksztalt", WSPOLNE)
def test_TE_SAME_pola_sa_kwotami(ksztalt):
    """Rozjazd, ktory da sie zrobic nie ruszajac ani jednej nazwy: pole
    otypowane `Kwota` po jednej stronie i `number` po drugiej."""
    we = {p for p, o in TS[ksztalt].items() if o["kwota"]}
    py = {p for p, o in PY[ksztalt].items() if o["kwota"]}
    assert we == py, (
        f"{ksztalt}: kwota tylko we wzorcu {sorted(we - py)}; "
        f"kwota tylko w Pythonie {sorted(py - we)}")


def test_ZADNE_pole_kwotowe_nie_jest_liczba():
    """Kontrola przekrojowa z wlasnym licznikiem: przechodzi po WSZYSTKICH
    polach obu stron i pilnuje, ze nigdzie nie stoi typ liczbowy tam, gdzie
    kontrakt mowi o kwocie. Licznik jest po to, zeby pusty przebieg nie
    zameldowal sukcesu."""
    sprawdzonych = 0
    for ksztalt in WSPOLNE:
        for strona, pola in (("wzorzec", TS[ksztalt]), ("python", PY[ksztalt])):
            for pole, opis in pola.items():
                if not opis["kwota"]:
                    continue
                sprawdzonych += 1
                assert not re.search(r"\b(number|float|Decimal)\b", opis["typ"]), (
                    f"{strona} {ksztalt}.{pole}: {opis['typ']} — kwota "
                    f"przechodzi granice WYLACZNIE napisem")
    assert sprawdzonych >= 12, (
        f"kontrola objela {sprawdzonych} pol kwotowych — za malo, zeby cos "
        f"znaczyla; kwot w kontrakcie jest dzis dziewiec po kazdej stronie")


def test_ZADNE_pole_kontraktu_nie_jest_liczba_zmiennoprzecinkowa():
    """Kontrola dwustronna do testu wyzej: tam pytamy o pola OZNACZONE jako
    kwota, tu o WSZYSTKIE. Pole nazwane inaczej, ale niosace pieniadze,
    przeszloby tamten test przez pomylke."""
    sprawdzonych = 0
    for ksztalt in WSPOLNE:
        for strona, pola in (("wzorzec", TS[ksztalt]), ("python", PY[ksztalt])):
            for pole, opis in pola.items():
                sprawdzonych += 1
                assert not re.search(r"\b(float|Decimal)\b", opis["typ"]), (
                    f"{strona} {ksztalt}.{pole}: {opis['typ']}")
    assert sprawdzonych >= 2 * PROG_LICZNOSCI, (
        f"kontrola objela {sprawdzonych} pol — parser widzi za malo")


def test_TypWpisu_ma_te_same_TRZY_wartosci():
    zrodlo = _bez_komentarzy(WZORZEC.read_text(encoding="utf-8"))
    m = re.search(r"export\s+type\s+TypWpisu\s*=\s*([^;]+);", zrodlo)
    assert m, "wzorzec nie niesie typu TypWpisu"
    we_wzorcu = tuple(x.strip().strip('"') for x in m.group(1).split("|"))
    assert len(we_wzorcu) == 3, we_wzorcu
    assert we_wzorcu == kontrakt.TYPY, (
        f"wzorzec: {we_wzorcu}, Python: {kontrakt.TYPY}")


# --- 3. dwie reguly, ktore kontrakt niesie oprocz ksztaltu ---------------

def test_kwota_do_zapisu_NIE_PRZYJMUJE_znaku():
    """Kierunek niesie `typ`, nie znak. Kwota ujemna zapisana po cichu
    odjelaby sie dwa razy."""
    poprawny = kontrakt.WpisDoZapisu(
        data="2026-09-15", typ="Wydatki", kategoria="Zakupy",
        kwota="274.06", szczegoly="")
    assert poprawny.kwota == "274.06"
    for zly in ("-274.06", "−274.06", "+274.06"):
        with pytest.raises(kontrakt.BladKontraktu) as blad:
            kontrakt.WpisDoZapisu(data="2026-09-15", typ="Wydatki",
                                  kategoria="Zakupy", kwota=zly, szczegoly="")
        assert "typ" in str(blad.value).lower() or "znak" in str(blad.value).lower()


def test_saldo_bite_RAZ_NA_DZIEN():
    """Druga i dalsza pozycja tego samego dnia dostaje `None`. Silnik podaje
    saldo per pozycja, wiec bez tej reguly kolumna pokazywalaby te sama
    liczbe dwa razy — a powtorzona liczba wyglada jak blad."""
    surowe = [
        kontrakt.PozycjaKsiegi("2026-09-01", "Otwarcie", None, "9920.79"),
        kontrakt.PozycjaKsiegi("2026-09-02", "Zakupy", "-120.00", "9800.79"),
        kontrakt.PozycjaKsiegi("2026-09-02", "Paliwo", "-200.00", "9800.79"),
        kontrakt.PozycjaKsiegi("2026-09-02", "Kawa", "-15.00", "9800.79"),
        kontrakt.PozycjaKsiegi("2026-09-03", "Wplyw", "1000.00", "10800.79"),
    ]
    zbite = kontrakt.zbij_saldo_raz_na_dzien(surowe)
    assert len(zbite) == len(surowe), "regula zgubila pozycje"
    assert [p.saldoPoDniu for p in zbite] == [
        "9920.79", "9800.79", None, None, "10800.79"]
    # Kontrola dwustronna: nic poza saldem sie nie zmienilo.
    assert [p.pozycja for p in zbite] == [p.pozycja for p in surowe]
    assert [p.kwota for p in zbite] == [p.kwota for p in surowe]
    # Kontrola licznosci: gdyby wejscie bylo puste, asercje wyzej przeszlyby.
    assert sum(1 for p in zbite if p.saldoPoDniu is None) == 2


def test_saldo_raz_na_dzien_NIE_MODYFIKUJE_wejscia():
    surowe = (kontrakt.PozycjaKsiegi("2026-09-02", "A", "-1.00", "5.00"),
              kontrakt.PozycjaKsiegi("2026-09-02", "B", "-1.00", "5.00"))
    kontrakt.zbij_saldo_raz_na_dzien(surowe)
    assert surowe[1].saldoPoDniu == "5.00", "regula nadpisala wejscie"


# --- 4. serializacja: jeden nosnik, obchod calego drzewa -----------------

def test_kwota_wychodzi_NAPISEM_i_zaokragla_sie_RAZ():
    from api import kwoty

    assert kwoty.kwota(Decimal("274.055")) == "274.06"
    assert kwoty.kwota(Decimal("1305.05")) == "1305.05"
    assert kwoty.kwota(None) is None, "brak wiedzy ma zostac brakiem wiedzy, nie zerem"
    with pytest.raises(TypeError):
        kwoty.kwota(0.1)


def test_policz_liscie_dociera_w_GLAB_i_mowi_ile_zobaczyl():
    """Kwota ukryta w trzecim zagniezdzeniu jest tak samo zla jak na wierzchu —
    a wszystkie kwoty tego projektu siedza wlasnie tam (`ksiega`, `wykres`)."""
    from api import kwoty

    drzewo = {"a": 1, "b": {"c": [{"d": "x"}, {"d": 2.5}]}, "e": [[3.5]]}
    sciezki, lisci = kwoty.policz_liscie(drzewo)
    assert sciezki == ["$.b.c[1].d", "$.e[0][0]"], sciezki
    # Czterу liscie: $.a, $.b.c[0].d, $.b.c[1].d, $.e[0][0]. Slowniki
    # i listy NIE sa liscmi — licznik ma mowic, ile WARTOSCI obejrzano.
    assert lisci == 4, f"obchod odwiedzil {lisci} lisci zamiast 4"


def test_policz_liscie_na_PUSTYM_drzewie_zglasza_ZERO_lisci():
    """Kontrola licznosci samego licznika. Bez niej „zero trafien" i „obchod
    nigdzie nie dotarl" sa nieodroznialne — a to jest ta klasa awarii, przed
    ktora ten licznik istnieje."""
    from api import kwoty

    assert kwoty.policz_liscie({}) == ([], 0)
    assert kwoty.policz_liscie([]) == ([], 0)
    assert kwoty.policz_liscie({"a": {}, "b": []}) == ([], 0)


def test_odpowiedz_ODMAWIA_liczby_zmiennoprzecinkowej_w_glebi():
    from api import kwoty

    odpowiedz = kwoty.OdpowiedzJSON(content={"ok": True})
    with pytest.raises(TypeError) as blad:
        odpowiedz.render({"ksiega": [{"dzien": "2026-09-01", "kwota": 274.06}]})
    assert "$.ksiega[0].kwota" in str(blad.value), str(blad.value)
    assert "lisci" in str(blad.value), "komunikat ma podac, ile lisci przejrzano"


def test_odpowiedz_ODMAWIA_golego_Decimala():
    """Konwersja jest gorsza niz blad: zaokraglenie do groszy ma zapasc RAZ,
    w `kwoty.kwota()`, a nie przy okazji serializacji."""
    from api import kwoty

    with pytest.raises(TypeError) as blad:
        kwoty.OdpowiedzJSON(content={}).render({"kwota": Decimal("274.06")})
    assert "kwota()" in str(blad.value)


def test_odpowiedz_PRZEPUSZCZA_poprawna_odpowiedz():
    """Kontrola dwustronna: bramka, ktora blokuje wszystko, nie jest bramka."""
    from api import kwoty

    tresc = {"odczyt": "2026-10-06", "horyzontDni": 23,
             "ksiega": [{"dzien": "2026-09-01", "kwota": None,
                         "saldoPoDniu": "9920.79"}]}
    surowe = kwoty.OdpowiedzJSON(content={}).render(tresc)
    assert b'"9920.79"' in surowe
    assert b"9920.79," not in surowe, "kwota wyszla jako liczba, nie napis"


def test_klasa_odpowiedzi_ma_JEDEN_nosnik():
    """Do Z5 warstwa sieciowa miala wlasna klase odpowiedzi obok tej — i ta
    druga NIE sprawdzala liczb zmiennoprzecinkowych wcale."""
    from api import index, kwoty

    assert index.trasy.default_response_class is kwoty.OdpowiedzJSON
    assert index.aplikacja.router.default_response_class is kwoty.OdpowiedzJSON
    zrodlo = (KORZEN / "api" / "index.py").read_text(encoding="utf-8")
    assert "class Odpowiedz" not in zrodlo, \
        "w `api/index.py` znowu stoi wlasna klasa odpowiedzi"


# --- 5. dlug nazwany: formatowanie ma DWA nosniki i one sie ROZNIA -------

def test_dwa_nosniki_formatowania_kwoty_sa_PRZYPIETE():
    """TO NIE JEST TEST ZGODNOSCI — to test PRZYPINAJACY znany rozjazd.

    Zmierzone 2026-08-29: `silnik/rdzen/prezentacja.py` sklada kwote ze spacja
    NIEROZDZIELAJACA (U+00A0), a `interfejs/lib/kwota.ts` ze zwykla spacja
    (U+0020). Ramki niosa zwykla spacje — sprawdzone na wszystkich siedmiu
    kwotach z separatorem tysiecy w `makiety/*.dc.html` — wiec to strona
    TypeScriptu zgadza sie z ramka, a Python od niej odstaje.

    DLACZEGO NIE NAPRAWIAM TEGO TUTAJ. Rozstrzygniecie dotyczy tego, co widzi
    uzytkownik, i nalezy do Darka; oba nosniki maja tez rozne uzasadnienia
    (spacja nierozdzielajaca chroni kwote przed zlamaniem na koncu wiersza).
    Do czasu decyzji rozjazd ma byc GLOSNY, a nie cichy: ten test czerwieni sie,
    gdy ktorakolwiek strona zmieni separator, wiec nikt nie przesunie tej
    granicy przypadkiem.

    PROG: przy pierwszym napisie skladanym w Pythonie, ktory trafia na ekran
    (`zdanieWerdyktu`, `okresNapis`, `uzasadnienieKolejnosci` z kontraktu),
    rozjazd przestaje byc teoretyczny i wymaga decyzji.
    """
    from silnik.rdzen import prezentacja

    assert prezentacja.SEPARATOR_TYSIECY == " ", \
        "Python zmienil separator — rozjazd z `kwota.ts` mogl zostac zamkniety"
    zrodlo_ts = (KORZEN / "interfejs" / "lib" / "kwota.ts").read_text(encoding="utf-8")
    m = re.search(r'replace\(/\\B\(\?=\(\\d\{3\}\)\+\(\?!\\d\)\)/g,\s*"(.*?)"\)',
                  zrodlo_ts)
    assert m, "nie znalazlem separatora tysiecy w `interfejs/lib/kwota.ts`"
    assert m.group(1) == " ", (
        f"TypeScript zmienil separator na U+{ord(m.group(1)):04X} — rozjazd "
        f"z `prezentacja.py` mogl zostac zamkniety; zaktualizuj ten straznik")


def test_MINUS_jest_TEN_SAM_po_obu_stronach():
    """Kontrola dwustronna do testu wyzej: nie kazda roznica miedzy nosnikami
    jest dopuszczona. Minus typograficzny (D-58) ma byc identyczny — i jest,
    wiec ten test pilnuje stanu ZGODNEGO, tamten stanu ROZJECHANEGO."""
    from silnik.rdzen import prezentacja

    zrodlo_ts = (KORZEN / "interfejs" / "lib" / "kwota.ts").read_text(encoding="utf-8")
    assert prezentacja.MINUS == "−"
    assert '"−"' in zrodlo_ts, \
        "`kwota.ts` nie uzywa juz minusa typograficznego U+2212 (D-58)"


# --- 6. raport licznosci — liczba, na ktora mozna sie powolac ------------

#: Stan zmierzony 2026-08-29. Liczby stoja TUTAJ, a nie w raporcie do
#: czlowieka, zeby kazda ich zmiana byla zmiana KODU, widoczna w historii.
#: Nie sa progiem („co najmniej"), tylko stanem („dokladnie") — prog
#: przepusciłby ciche usuniecie pola, a to jest wlasnie ta zmiana, ktorej
#: ten plik ma nie przepuscic bez decyzji.
ZMIERZONE = {
    "ksztaltow": 14,    # Z7b: 9 -> W9b: 14 (piec ksztaltow ekranu Budzet)
    "pol": 102,         # Z5: 47 -> Z7b: 48 -> W9b: 102
    "pol_kwotowych": 7 + 13,   # W9b: +13 (kafelek, tabela, plan, cel, bilans)
    "per_ksztalt": {
        "Kategoria": 3, "WpisDoZapisu": 5, "WierszSkutku": 4,
        "PodgladSkutku": 2, "OstatniWpis": 6,
        "DaneKsiegowania": 9,   # Z7b: +`ostatnieSprawdzenie` (luka kontraktu)
        "PozycjaKsiegi": 5, "PunktWykresu": 2, "DanePlynnosci": 12,
        # W9b — ekran Budzet. `OstatniWpis` jest WOLANY przez `DaneBudzetu`
        # (tabela „Historia"), nie powtorzony: to ta sama rzecz co „Ostatnie
        # wpisy" na Ksiegowaniu, wiec nie dostaje wlasnego ksztaltu.
        "KafelekBudzetu": 5, "PozycjaWykonania": 10, "PozycjaPlanu": 8,
        "CelNaEkranie": 12, "DaneBudzetu": 19,
    },
}

# PROG KONSOLIDACJI ZADZIALAL W Z7b — I NIE ZOSTAL SPLACONY. Nazwane wprost.
#
# Naglowek tego pliku mowi: „przy pierwszym dopisaniu pola generujemy
# `kontrakt.ts` z `kontrakt.py` i drugi nosnik znika". W Z7b dopisano pole
# (`DaneKsiegowania.ostatnieSprawdzenie`), wiec warunek zostal spelniony.
#
# GENERATORA NIE ZBUDOWANO i to jest decyzja do podjecia, nie przeoczenie:
#   * prog zapisano w Z5 z kierunkiem „`.ts` z `.py`", a Sophia i Oliver
#     ustalili kierunek ODWROTNY (wzorcem jest `.ts`) — prog i decyzja
#     o kierunku sa ze soba sprzeczne i nie da sie spelnic obu;
#   * `kontrakt.py` niesie nie tylko ksztalt, ale i REGULY
#     (`WpisDoZapisu.__post_init__`, `zbij_saldo_raz_na_dzien`), ktorych
#     zaden generator ksztaltu nie odtworzy — wiec „generujemy" musialoby
#     znaczyc „generujemy CZESC pliku", a to jest trzeci nosnik, nie zero.
#
# DO CZASU DECYZJI dlug jest pilnowany tym plikiem i opisany etykieta
# „prog zadzialal, niesplacony" — zgodnie z `CLAUDE.md` §3.2 etykieta jest
# dopuszczalna, udawanie splaty nie jest.
# DRUGIE ZADZIALANIE PROGU — W9b, 2026-08-29. Zapisane, nie przemilczane.
# Ekran Budzet dolozyl PIEC ksztaltow i 54 pola naraz (48 -> 102). To jest
# najwieksza jednorazowa zmiana kontraktu w tym projekcie i tym mocniejszy
# argument za generatorem — a jednoczesnie tym gorszy moment, zeby go pisac
# w zadaniu o trasach. Sprzecznosc opisana wyzej (prog mowi „`.ts` z `.py`",
# decyzja o kierunku mowi „wzorcem jest `.ts`") jest NADAL nierozstrzygnieta
# i to ona blokuje splate, nie brak czasu. Do rozstrzygniecia przez Ethana.
#
# CO PRZEZ TO NIE DZIALA: nic sie nie psuje, ale koszt kazdej nastepnej
# zmiany ksztaltu rosnie — dwa pliki do recznego zrownania zamiast jednego.
# Pilnuje tego wylacznie ten plik i pilnuje SKUTECZNIE (mutacja niżej).
PROG_ZADZIALAL_NIESPLACONY = (
    "Z7b — dopisano DaneKsiegowania.ostatnieSprawdzenie; "
    "W9b — dopisano piec ksztaltow ekranu Budzet (9 -> 14 ksztaltow, "
    "48 -> 102 pola)")


def test_RAPORT_ile_pol_porownano_po_kazdej_stronie():
    """Liczba, ktora straznik faktycznie porownal — po obu stronach osobno.

    To jest odpowiedz na pytanie „ile rzeczy pomiar zobaczyl", zadana wprost,
    a nie wyprowadzona z tego, ze inne asercje przeszly. Zbior pusty rowna sie
    zbiorowi pustemu i pierwsze osiem sekcji tego pliku bylo by wtedy zielone.

    Zmiana ktorejkolwiek z tych liczb jest zmiana kontraktu i ma byc decyzja:
    dopisales pole — podnies liczbe TUTAJ, i przy okazji przypomnij sobie prog
    konsolidacji z naglowka (pierwsze dopisane pole = generujemy `.ts` z `.py`).
    """
    ts_pol = sum(len(p) for p in TS.values())
    py_pol = sum(len(p) for p in PY.values())
    ts_kwot = sum(1 for p in TS.values() for o in p.values() if o["kwota"])
    py_kwot = sum(1 for p in PY.values() for o in p.values() if o["kwota"])

    assert (len(TS), ts_pol, ts_kwot) == (
        ZMIERZONE["ksztaltow"], ZMIERZONE["pol"], ZMIERZONE["pol_kwotowych"]), (
        f"wzorzec: {len(TS)} ksztaltow, {ts_pol} pol, {ts_kwot} kwotowych — "
        f"oczekiwano {ZMIERZONE}")
    assert (len(PY), py_pol, py_kwot) == (
        ZMIERZONE["ksztaltow"], ZMIERZONE["pol"], ZMIERZONE["pol_kwotowych"]), (
        f"python: {len(PY)} ksztaltow, {py_pol} pol, {py_kwot} kwotowych")

    for ksztalt, ile in ZMIERZONE["per_ksztalt"].items():
        assert len(TS[ksztalt]) == ile, f"wzorzec {ksztalt}: {len(TS[ksztalt])} pol"
        assert len(PY[ksztalt]) == ile, f"python {ksztalt}: {len(PY[ksztalt])} pol"


# --- 7. przebieg przez cala granice, na ksztalcie z kontraktu ------------

def test_ODPOWIEDZ_zlozona_z_kontraktu_przechodzi_granice_bez_ani_jednej_liczby():
    """Przebieg koncowy: silnik -> `kwoty.kwota` -> `OdpowiedzJSON` -> bajty.

    Sekcje wyzej sprawdzaja czesci osobno; ta sprawdza ZLOZENIE. Wada, ktora
    ta asercja lapie, a tamte nie: `kwota()` zaczyna zwracac liczbe. Kazdy
    test czesci nadal by przechodzil — `policz_liscie` dziala, `OdpowiedzJSON`
    dziala — a odpowiedz wychodzilaby z liczba zmiennoprzecinkowa i kodem 200.

    Kontrola licznosci: liczymy liscie odpowiedzi i zadamy, zeby bylo ich
    tyle, ile pol faktycznie zlozylismy. Przebieg po pustym drzewie nie ma
    czego zgubic i zameldowalby sukces.
    """
    from api import kwoty

    ksiega = kontrakt.zbij_saldo_raz_na_dzien([
        kontrakt.PozycjaKsiegi("2026-09-01", "Otwarcie", None,
                               kwoty.kwota(Decimal("9920.79")),
                               dopisek="z odczytu 1 wrzesnia"),
        kontrakt.PozycjaKsiegi("2026-09-02", "Zakupy",
                               kwoty.kwota(Decimal("-120.00")),
                               kwoty.kwota(Decimal("9800.79"))),
        kontrakt.PozycjaKsiegi("2026-09-02", "Paliwo",
                               kwoty.kwota(Decimal("-200.00")),
                               kwoty.kwota(Decimal("9600.79"))),
    ])
    tresc = {
        "odczyt": "2026-10-06",
        "horyzontDni": 23,
        "saldoMinimalne": kwoty.kwota(Decimal("-210.67")),
        "dataSaldaMinimalnego": "2026-09-25",
        "ksiega": [dataclasses.asdict(p) for p in ksiega],
        "wykres": [dataclasses.asdict(kontrakt.PunktWykresu(
            "2026-09-01", kwoty.kwota(Decimal("9920.79"))))],
    }

    sciezki, lisci = kwoty.policz_liscie(tresc)
    assert sciezki == [], f"liczba zmiennoprzecinkowa w odpowiedzi: {sciezki}"
    # 21 lisci: cztery pola wierzchnie + trzy pozycje ksiegi po piec pol
    # + jeden punkt wykresu po dwa.
    assert lisci == 21, (
        f"obchod odwiedzil {lisci} lisci — odpowiedz ma inny ksztalt, niz "
        f"zaklada ten test, wiec pomiar nie mowi tego, co mysli, ze mowi")

    surowe = kwoty.OdpowiedzJSON(content={}).render(tresc)
    assert b'"saldoMinimalne":"-210.06"' not in surowe
    assert b'"saldoMinimalne":"-210.67"' in surowe
    assert b'"saldoPoDniu":null' in surowe, "saldo nie zostalo zbite raz na dzien"
    assert b'"horyzontDni":23' in surowe, \
        "liczba calkowita ma przejsc liczba — nie ma groszy do zgubienia"

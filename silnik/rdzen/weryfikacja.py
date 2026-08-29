"""Weryfikacja stawek u źródła — porównanie, nigdy nadpisanie.

Realizuje wymaganie „stawki sprawdzane i potwierdzane na oficjalnych stronach
przed wyliczeniem" (decyzja Darka 2026-08-25) w wariancie, który **porównuje**
rejestr ze stroną i **nigdy go nie zmienia**.

Dlaczego nie automatyczne nadpisywanie: pobieracz, który przestał trafiać
w liczbę, wygląda dokładnie tak samo jak pobieracz, który trafia. Zmierzono to
przy projektowaniu — pierwsze podejście zgłosiło brak trzech kwot, które na
stronie były. Gdyby mechanizm miał prawo zapisu, wpisałby do podatków ciszę
zamiast liczby.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path

import httpx

from silnik.rdzen import stawki

SCIEZKA_CACHE = Path.home() / ".cache" / "ai-cfo" / "weryfikacja.json"
LIMIT_CZASU_S = 20
NAGLOWKI = {"User-Agent": "Mozilla/5.0 (AI CFO, weryfikacja stawek)"}


class Wynik(Enum):
    ZGODNE = "zgodne"
    ROZBIEZNE = "rozbiezne"
    NIEDOSTEPNE = "niedostepne"


@dataclass(frozen=True)
class Raport:
    wynik: Wynik
    data: datetime
    zrodla: list[str]
    rozbiezne: list[str]
    komunikat: str


def normalizuj(html: str) -> str:
    """Sprowadza stronę do postaci, w której da się szukać kwot.

    Cztery kroki, każdy potrzebny z osobnego powodu:
    1. NFKC — spacja nierozdzielająca (U+00A0) i wąska stają się zwykłą spacją;
    2. usunięcie znaczników HTML;
    3. sklejenie białych znaków;
    4. usunięcie separatora tysięcy — ale WYŁĄCZNIE przed grupą dokładnie
       trzech cyfr zakończoną granicą słowa. Bez tego warunku „12 1234"
       stałoby się „121234" i pomiar zacząłby widzieć liczby, których na
       stronie nie ma.
    """
    tekst = unicodedata.normalize("NFKC", html)
    tekst = re.sub(r"<[^>]+>", " ", tekst)
    tekst = re.sub(r"\s+", " ", tekst)
    return re.sub(r"(?<=\d) (?=\d{3}\b)", "", tekst)


def warianty_zapisu(kwota: Decimal) -> list[str]:
    """Dopuszczalne zapisy tej samej kwoty na stronie rządowej.

    Strony zapisują kwoty niekonsekwentnie: „5 652 zł" obok „1495,04 zł".
    Wariant bez końcówki zerowej jest tu po to, żeby pomiar nie zgłaszał
    rozbieżności tam, gdzie jest tylko inna konwencja zapisu.
    """
    podstawowy = f"{kwota}".replace(".", ",")
    lista = [podstawowy]
    if podstawowy.endswith(",00"):
        lista.append(podstawowy[:-3])
    return lista


def oczekiwane_wartosci() -> dict[str, list[Decimal]]:
    """Wartości z rejestru, pogrupowane wg strony, na której mają się znaleźć."""
    spoleczne = stawki.skladki_spoleczne(z_chorobowa=True)
    return {
        # Mnozniki WOLANE z nosnika (Z4 krok 4.5) — do przenosin stala tu
        # czwarta kopia tabeli progow. Rozpakowanie zamiast trzech wywolan:
        # gdy przybedzie prog, ta lista rosnie sama, zamiast cicho pomijac go
        # przy odczycie strony.
        stawki.ZRODLA["zdrowotna"].url: [
            *stawki.skladki_zdrowotne_progow(),
            stawki.PRZECIETNE_WYNAGRODZENIE_IV_KW,
        ],
        stawki.ZRODLA["spoleczne"].url: [
            spoleczne["emerytalna"],
            spoleczne["rentowa"],
            spoleczne["chorobowa"],
            spoleczne["wypadkowa"],
            stawki.suma_spolecznych(z_chorobowa=True),
            stawki.PODSTAWA_SPOLECZNYCH,
        ],
        # Z58 — WARUNEK UKONCZENIA silnika skali, nie ozdoba. Pomiar
        # 2026-08-26: sprawdzanych bylo 10 liczb i ANI JEDNA nie dotyczyla
        # skali. Drugi silnik podatkowy bez pokrycia mechanizmem, ktory ma
        # pierwszy — i to silnik bedacy po ustaleniu §0 sciezka podstawowa.
        #
        # Stawki podane RAZY STO, bo strona pisze „12%", nie „0,12".
        # Slabosc tego pomiaru nazwana wprost w `stawki.ZRODLA["skala"]`.
        stawki.ZRODLA["skala"].url: [
            stawki.STAWKA_SKALI_PIERWSZA * 100,
            stawki.STAWKA_SKALI_DRUGA * 100,
            stawki.PROG_SKALI,
            stawki.KWOTA_ZMNIEJSZAJACA_PODATEK,
            stawki.STAWKA_ZDROWOTNEJ_SKALA * 100,
            stawki.ZDROWOTNA_MIN_MIESIECZNA,
        ],
    }


def oczekiwane_frazy() -> dict[str, list[str]]:
    """Zdania, które muszą wystąpić na stronie źródłowej, pogrupowane wg strony.

    Kwota to nie jedyna rzecz, którą da się zweryfikować — termin płatności
    też. Sprawdzenie po samej liczbie („20", „25") nie znaczyłoby nic, bo te
    cyfry są na każdej stronie z liczbami; sprawdzana jest więc CAŁA FRAZA,
    która niesie regułę.

    Nośnikiem terminów jest `rdzen.terminy.TERMINY` — tutaj są tylko czytane.
    """
    from silnik.rdzen import terminy

    wynik: dict[str, list[str]] = {}
    for termin in terminy.TERMINY:
        url = stawki.ZRODLA[termin.zrodlo].url
        wynik.setdefault(url, [])
        if termin.fraza not in wynik[url]:
            wynik[url].append(termin.fraza)
    return wynik


def _pobierz(url: str) -> str:
    """Wydzielone, żeby test mógł podstawić własną odpowiedź bez sieci."""
    odpowiedz = httpx.get(url, timeout=LIMIT_CZASU_S, follow_redirects=True,
                          headers=NAGLOWKI)
    odpowiedz.raise_for_status()
    return odpowiedz.text


def _wczytaj_cache(wazny_godzin: int) -> Raport | None:
    if wazny_godzin <= 0 or not SCIEZKA_CACHE.exists():
        return None
    try:
        dane = json.loads(SCIEZKA_CACHE.read_text(encoding="utf-8"))
        data = datetime.fromisoformat(dane["data"])
    except (ValueError, KeyError, OSError):
        return None
    if datetime.now() - data > timedelta(hours=wazny_godzin):
        return None
    return Raport(Wynik(dane["wynik"]), data, dane["zrodla"],
                  dane["rozbiezne"], dane["komunikat"])


def _zapisz_cache(raport: Raport) -> None:
    """Zapisuje WYNIK sprawdzenia — nigdy same stawki."""
    try:
        SCIEZKA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SCIEZKA_CACHE.write_text(json.dumps({
            "wynik": raport.wynik.value,
            "data": raport.data.isoformat(),
            "zrodla": raport.zrodla,
            "rozbiezne": raport.rozbiezne,
            "komunikat": raport.komunikat,
        }, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass   # brak cache nie jest awarią — najwyżej sprawdzimy ponownie


def z_cache(wazny_godzin: int = 24) -> "Raport | None":
    """Ostatni raport sprawdzenia u źródła — BEZ SIECI. `None` = nigdy.

    Rozdział ról wprowadzony w Z74 (B5): `sprawdz()` chodzi do sieci i należy
    do strażnika w tle (Z76), `z_cache()` odpowiada natychmiast i należy do
    nowego ekranu oraz trasy HTTP.

    Powód, zmierzony 2026-08-27: `sprawdz()` odpytuje **5 stron** z limitem
    czasu 20 s każda (`LIMIT_CZASU_S`), czyli do **100 sekund** przy braku
    sieci i pustym albo przeterminowanym podręcznym zapisie.

    Czego to zadanie NIE zmienia: stara aplikacja nadal woła `sprawdz()`
    przy starcie (`app.py:90`, `zbuduj_interfejs`) i Z74 tego nie rusza.
    Ta funkcja jest wyłącznie **drugim wejściem** do tych samych danych,
    nie zamianą pierwszego.

    `None` jest TRZECIĄ możliwością obok ZGODNE i ROZBIEŻNE i nie wolno jej
    zwinąć do żadnej z nich: „nikt nie pytał" to nie jest „wszystko się zgadza".
    """
    return _wczytaj_cache(wazny_godzin)


def blokuje_formularz(raport: "Raport | None") -> bool:
    """Czy formularz faktury ma być zablokowany. JEDEN NOŚNIK reguły z §6.

    Do Z77 ta reguła stała jednym wyrażeniem w `pulpit/jdg.py`
    (`raport.wynik is Wynik.ROZBIEZNE`) i to wystarczało, bo `raport` nigdy
    nie bywał pusty — `app.py` wołało `sprawdz()`, które **zawsze** oddaje
    raport. Po P2 wołający dostaje `weryfikacja.z_cache()`, czyli także
    `None`, i wyrażenie w interfejsie wywracałoby całą zakładkę.

    BLOKUJE WYŁĄCZNIE ROZBIEŻNOŚĆ — jeden stan z czterech, nie „wszystko
    poza zgodnym". Brak wiedzy (`None`, czyli nikt nie sprawdzał) i brak
    dostępu (NIEDOSTEPNE) to **nie są** sygnały, że rejestr się rozjechał
    z przepisem; blokada na nich zamurowałaby aplikację do pierwszego
    udanego przebiegu strażnika w tle. Specyfikacja mówi o NIEDOSTEPNE
    wprost: „formularz działa, wynik oznaczony" — a „nikt nie pytał" jest
    stanem jeszcze słabszym, nie mocniejszym.

    Strażnik: `test_BRAK_raportu_NIE_blokuje_formularza_a_rozbieznosc_blokuje`
    sprawdza wszystkie cztery przypadki (mutacja M416).
    """
    return raport is not None and raport.wynik is Wynik.ROZBIEZNE


def sprawdz(cache_wazny_godzin: int = 24) -> Raport:
    """Porównuje rejestr stawek ze stronami rządowymi. Trzy możliwe wyjścia.

    ZGODNE      — wszystkie wartości znalezione; formularz odblokowany.
    ROZBIEZNE   — którejś nie ma na stronie; formularz zablokowany do decyzji.
    NIEDOSTEPNE — brak sieci albo błąd; formularz działa, wynik oznaczony.

    Żadne z tych wyjść nie zmienia ani jednej liczby w `rdzen.stawki`.
    """
    z_cache = _wczytaj_cache(cache_wazny_godzin)
    if z_cache is not None:
        return z_cache

    oczekiwane = oczekiwane_wartosci()
    frazy = oczekiwane_frazy()
    strony = list(dict.fromkeys(list(oczekiwane) + list(frazy)))
    rozbiezne: list[str] = []
    teraz = datetime.now()

    for url in strony:
        wartosci = oczekiwane.get(url, [])
        try:
            tekst = normalizuj(_pobierz(url))
        except Exception as e:
            raport = Raport(
                Wynik.NIEDOSTEPNE, teraz, strony, [],
                f"Nie udało się sprawdzić stawek ani terminów u źródła "
                f"({type(e).__name__}). "
                f"Liczby pochodzą z rejestru odczytanego "
                f"{stawki.ZRODLA['zdrowotna'].data_odczytu.isoformat()} i są "
                f"niepotwierdzone od tamtej pory.",
            )
            _zapisz_cache(raport)
            return raport
        for kwota in wartosci:
            if not any(w in tekst for w in warianty_zapisu(kwota)):
                rozbiezne.append(f"{kwota} — nie znaleziona na {url}")
        for fraza in frazy.get(url, []):
            if fraza not in tekst:
                rozbiezne.append(f"termin „{fraza}” — nie znaleziony na {url}")

    if rozbiezne:
        raport = Raport(
            Wynik.ROZBIEZNE, teraz, strony, rozbiezne,
            f"Rozbieżność między rejestrem a źródłem: {len(rozbiezne)} "
            f"z {sum(len(v) for v in oczekiwane.values()) + sum(len(v) for v in frazy.values())} "
            f"sprawdzanych pozycji nie znaleziono. "
            "Formularz faktury zablokowany — sprawdź, czy przepis się zmienił, "
            "czy zmienił się układ strony. Rejestru nie ruszono.",
        )
    else:
        raport = Raport(
            Wynik.ZGODNE, teraz, strony, [],
            f"Stawki i terminy potwierdzone u źródła "
            f"{teraz.strftime('%Y-%m-%d %H:%M')}.",
        )
    _zapisz_cache(raport)
    return raport

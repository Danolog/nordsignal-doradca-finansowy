"""Doradca agentowy nad własnymi danymi — Gemini API.

**Model nigdy nie widzi bazy.** Widzi wyniki narzędzi z `rdzen.narzedzia`,
które wykonują się lokalnie na tym komputerze. Poza laptop wychodzą wyłącznie:
instrukcja systemowa, pytanie i wartości zwrócone przez narzędzia.

**Żadnej liczby z głowy.** Model, który podaje kwotę wyliczoną we własnym
rozumowaniu, to dokładnie ten mechanizm, przed którym broni cała reszta tego
projektu: sygnał bez sprawdzenia. Dlatego dwie warstwy — instrukcja systemowa
oraz `sprawdz_pokrycie_kwot`, która po odpowiedzi zestawia każdą kwotę
z tym, co realnie zwróciły narzędzia.

**Poziom płatny Gemini API jest wymogiem, nie luksusem.** Na poziomie darmowym
Google używa promptów do ulepszania produktów; przy zobowiązaniu z §7 umowy
B2B (tajemnica o klientach NMI, 3 lata po zakończeniu) to jest nie do przyjęcia,
nawet gdy narzędzia zwracają wyłącznie agregaty — bo pytania i kwoty wychodzą.
"""

import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from silnik.rdzen import magazyn, narzedzia, stawki

#: Wybór Darka 2026-08-25, godz. 20:5x: **Gemini Flash zamiast Pro**, wariant
#: najnowszy z dostępnych. `gemini-3.7-flash` nie ma w nazwie „preview" —
#: to wydanie zwykłe, nie zapowiedź.
#:
#: Zmierzone przed podmianą (2026-08-25, ten sam komplet 12 narzędzi
#: i ta sama instrukcja systemowa): Flash 3.7 **wołał właściwe narzędzie
#: w każdym z czterech pytań** (rozbicie faktury, próg składki, porównanie
#: form, wykonanie planu), a kontrola pokrycia kwot nie zgłosiła ani jednej
#: liczby bez pokrycia. Czas odpowiedzi 2,9–7,3 s wobec 13,2 s dla Pro.
#:
#: To był warunek podmiany, a nie jej skutek uboczny: mniejszy model kusi,
#: żeby policzyć arytmetykę samodzielnie zamiast zawołać narzędzie — a wtedy
#: doradca podaje kwotę, której nikt nie sprawdził.
MODEL = "gemini-3.7-flash"

#: Wariant zapasowy, gdyby najnowszy zniknął. Świadomie starszy i sprawdzony,
#: nie alias `gemini-flash-latest`: alias zmienia model pod aplikacją bez
#: śladu, a w narzędziu podatkowym ta sama odpowiedź ma zostać tą samą
#: odpowiedzią za pół roku.
MODEL_STABILNY = "gemini-2.5-flash"

ZMIENNE_KLUCZA = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
MAKS_WYWOLAN_NARZEDZI = 12

#: Zdanie o formie opodatkowania — JEDYNE miejsce instrukcji, które o niej
#: mówi. Wstawia się przez `{forma}` i pochodzi z BAZY, nigdy ze stałej.
#:
#: Do 2026-08-28 stała tu fraza „rozliczanej ryczałtem od przychodów
#: ewidencjonowanych". Darek jest na skali podatkowej od 2026
#: (`docs/plan-forma-opodatkowania.md` v0.5 §0), więc instrukcja podawała
#: modelowi FAŁSZ o użytkowniku — i to fałsz, którego model nie miał jak
#: sprawdzić, bo narzędzia formy nie zwracały. Model uprzejmie mówił
#: „przy Twoim ryczałcie…" nad kwotami policzonymi skalą.
SZABLON_INSTRUKCJI = """\
Jesteś doradcą finansowym jednoosobowej działalności gospodarczej {forma}, \
przy VAT 23%. Odpowiadasz po polsku, konkretnie, bez ogólników.

REGUŁY TWARDE, których nie wolno złamać:

1. Każda kwota w Twojej odpowiedzi pochodzi WPROST z wyniku narzędzia. \
Nie wykonujesz ŻADNYCH działań na liczbach — nawet oczywistych. Zakazane są \
w szczególności: sumowanie kilku kwot z wyniku narzędzia, przeliczanie netto \
na brutto, obliczanie różnic, procentów i średnich. Jeśli liczby nie ma \
w wyniku narzędzia, NIE PISZ JEJ — powiedz, że nie masz czym jej policzyć. \
Liczba policzona w rozumowaniu wygląda tak samo jak sprawdzona i właśnie \
dlatego jest groźna.

2. Kwalifikacja PKWiU i wybór formy opodatkowania to decyzja użytkownika \
podejmowana z księgowym. Liczysz scenariusze i pokazujesz różnice; nie orzekasz, \
która stawka przysługuje.

3. Nigdy nie pytaj o nazwy klientów ani kontrahentów i nie proś użytkownika \
o ich podanie. Narzędzia celowo ich nie zwracają — obowiązuje umowna tajemnica \
handlowa.

4. Gdy wynik narzędzia niesie listę założeń, wymień je razem z liczbą. Kwota \
bez widocznych założeń udaje precyzję, której nie ma.
"""

#: Opis formy wstawiany w `{forma}`. Nierozstrzygnięta NIE dostaje żadnej
#: nazwy formy — model ma powiedzieć „wskaż formę", nie zgadywać za
#: użytkownika. To ta sama reguła co w `podatki.policz`, tylko po stronie słów.
OPIS_FORMY = {
    magazyn.FORMA_RYCZALT: ("rozliczanej ryczałtem od przychodów "
                            "ewidencjonowanych"),
    magazyn.FORMA_SKALA: ("rozliczanej według skali podatkowej "
                          "(zasady ogólne)"),
}
OPIS_FORMY_NIEZNANEJ = ("o NIEROZSTRZYGNIĘTEJ formie opodatkowania — jeśli "
                        "pytanie zależy od formy, powiedz, że trzeba ją "
                        "najpierw wskazać w Ustawieniach, i nie zgaduj")


def instrukcja_systemowa(polaczenie=None, dzis: "date | None" = None) -> str:
    """Instrukcja z formą opodatkowania ODCZYTANĄ Z BAZY, nie zaszytą.

    Bez połączenia zwraca wariant „forma nieznana" — bo tak jest naprawdę,
    a instrukcja twierdząca jakąkolwiek formę bez odczytu byłaby dokładnie tą
    wadą, którą ta funkcja zastąpiła.
    """
    opis = OPIS_FORMY_NIEZNANEJ
    if polaczenie is not None:
        rok = (dzis or date.today()).year
        try:
            forma = magazyn.forma_na_rok(polaczenie, rok)
            opis = OPIS_FORMY.get(forma.forma, OPIS_FORMY_NIEZNANEJ)
        except magazyn.BladMagazynu:
            opis = OPIS_FORMY_NIEZNANEJ
    return SZABLON_INSTRUKCJI.format(forma=opis)


ODPOWIEDZ_BEZ_KLUCZA = (
    "Doradca nie jest podłączony — brak klucza API.\n\n"
    "Wpisz klucz do pliku `.env` w katalogu aplikacji, w postaci\n"
    "`GEMINI_API_KEY=twój-klucz`, i uruchom aplikację ponownie.\n\n"
    "Plik, a nie profil powłoki: aplikacja uruchomiona ikoną dostaje "
    "środowisko od systemu, nie z `~/.zshrc`, więc klucza z powłoki nie "
    "zobaczy. Użyj płatnego poziomu Gemini API — na darmowym Google używa "
    "promptów do ulepszania produktów, a Twoje pytania niosą kwoty przychodów."
)

#: Kwota w tekście: 830,58 · 4 200,00 · 11 200,00 · 11200.00 (także ze spacją
#: nierozdzielającą jako separatorem tysięcy).
_WZORZEC_KWOTY = re.compile(r"\d[\d\u00a0\u202f ]*[.,]\d{2}\b")


def dostepny() -> bool:
    """Czy doradca ma czym odpowiadać — klucz w środowisku."""
    return any(os.environ.get(zmienna) for zmienna in ZMIENNE_KLUCZA)


def _znormalizuj(napis: str) -> str | None:
    """Sprowadza zapis kwoty do postaci porównywalnej: 11 200,00 -> 11200.00."""
    oczyszczony = (napis.replace(" ", "").replace("\u00a0", "")
                   .replace("\u202f", "").replace(",", "."))
    try:
        # Przez `stawki.do_groszy` — jedyny nosnik konwencji pienieznej.
        # To jest KLUCZ POROWNANIA: gdyby normalizacja zaokraglala inaczej niz
        # `_kwota` w `narzedzia.py`, ta sama kwota mialaby dwie postacie
        # i kontrola pokrycia zglaszalaby liczbe modelu jako niepotwierdzona,
        # choc narzedzie ja zwrocilo.
        return str(stawki.do_groszy(Decimal(oczyszczony)))
    except (InvalidOperation, ValueError):
        return None


def znajdz_kwoty(tekst: str) -> set[str]:
    """Wszystkie kwoty w tekście, w postaci znormalizowanej."""
    znalezione = set()
    for dopasowanie in _WZORZEC_KWOTY.findall(tekst or ""):
        znormalizowana = _znormalizuj(dopasowanie)
        if znormalizowana:
            znalezione.add(znormalizowana)
    return znalezione


def _kwoty_z_wynikow(obiekt, zebrane: set | None = None) -> set[str]:
    """Schodzi rekurencyjnie po wynikach narzędzi i zbiera każdą liczbę."""
    zebrane = set() if zebrane is None else zebrane
    if isinstance(obiekt, dict):
        for wartosc in obiekt.values():
            _kwoty_z_wynikow(wartosc, zebrane)
    elif isinstance(obiekt, (list, tuple, set)):
        for wartosc in obiekt:
            _kwoty_z_wynikow(wartosc, zebrane)
    else:
        znormalizowana = _znormalizuj(str(obiekt))
        if znormalizowana:
            zebrane.add(znormalizowana)
        zebrane |= znajdz_kwoty(str(obiekt))
    return zebrane


def sprawdz_pokrycie_kwot(odpowiedz: str, wyniki_narzedzi: list) -> str | None:
    """Zwraca ostrzeżenie, jeśli w odpowiedzi jest kwota bez pokrycia w narzędziach.

    Zielona odpowiedź nie jest dowodem, że model nic nie policzył z głowy —
    dowodem jest zestawienie każdej kwoty z tym, co realnie wróciło z narzędzi.
    """
    w_odpowiedzi = znajdz_kwoty(odpowiedz)
    if not w_odpowiedzi:
        return None
    z_narzedzi = _kwoty_z_wynikow(wyniki_narzedzi)
    bez_pokrycia = sorted(w_odpowiedzi - z_narzedzi)
    if not bez_pokrycia:
        return None
    lista = ", ".join(k.replace(".", ",") for k in bez_pokrycia)
    return (f"Uwaga: te kwoty nie pochodzą z żadnego narzędzia — {lista}. "
            "Mogły zostać policzone w rozumowaniu modelu. Sprawdź je, zanim "
            "podejmiesz na ich podstawie decyzję.")


def _wyniki_z_historii(odpowiedz_modelu) -> list:
    """Wyciąga wartości zwrócone przez narzędzia z zapisu wywołań."""
    wyniki = []
    historia = getattr(odpowiedz_modelu, "automatic_function_calling_history", None) or []
    for tura in historia:
        for czesc in getattr(tura, "parts", None) or []:
            reakcja = getattr(czesc, "function_response", None)
            if reakcja is not None and getattr(reakcja, "response", None) is not None:
                wyniki.append(reakcja.response)
    return wyniki


def _uzyte_narzedzia(odpowiedz_modelu) -> list[str]:
    nazwy = []
    historia = getattr(odpowiedz_modelu, "automatic_function_calling_history", None) or []
    for tura in historia:
        for czesc in getattr(tura, "parts", None) or []:
            wywolanie = getattr(czesc, "function_call", None)
            if wywolanie is not None and getattr(wywolanie, "name", None):
                nazwy.append(wywolanie.name)
    return nazwy


def diagnoza_bledu(blad: Exception) -> str:
    """Zamienia wyjątek SDK na zdanie mówiące, co jest NAPRAWDĘ nie tak.

    Geneza, 2026-08-25: doradca odpowiadał „Sprawdź klucz API" na każdą awarię.
    Klucz był poprawny, model istniał, kod działał — Google odrzucało wywołanie
    kodem 429 z adnotacją `limit: 0` dla darmowego poziomu. Jeden komunikat na
    wszystkie awarie **wysyła użytkownika w złą stronę**, a to jest gorsze niż
    brak diagnozy: kosztowało godzinę szukania nie tam, gdzie trzeba.

    Gałąź nierozpoznana cytuje typ i treść wyjątku zamiast zgadywać przyczynę.
    """
    tresc = str(blad)
    nazwa = type(blad).__name__

    if "RESOURCE_EXHAUSTED" in tresc or "429" in tresc:
        darmowy = "free_tier" in tresc or "limit: 0" in tresc
        czesc = ("Ten model nie ma ŻADNEGO przydziału na darmowym poziomie "
                 "(Google zwraca `limit: 0`)." if darmowy else
                 "Przekroczony przydział zapytań.")
        return (
            f"Google odrzuciło wywołanie: przekroczony limit. {czesc}\n\n"
            "To nie jest problem z kluczem — klucz działa, model istnieje. "
            "Włącz płatny poziom (billing) dla projektu w Google AI Studio: "
            "https://aistudio.google.com/apikey\n\n"
            "Płatny poziom jest tu wymogiem, nie wygodą. Na darmowym Google "
            "używa promptów do ulepszania produktów, a §7 ust. 4 umowy z NMI "
            "zobowiązuje Cię do tajemnicy o klientach Zleceniodawcy przez "
            "3 lata po zakończeniu współpracy."
        )

    if ("API key" in tresc or "API_KEY" in tresc or "UNAUTHENTICATED" in tresc
            or "PERMISSION_DENIED" in tresc):
        return (
            "Google odrzuciło klucz API.\n\n"
            f"Sprawdź {ZMIENNE_KLUCZA[0]} w pliku `.env` w katalogu aplikacji "
            "— czy jest ustawiony i czy nie został unieważniony. Aplikacja "
            "uruchomiona ikoną NIE widzi zmiennych z `~/.zshrc`: środowisko "
            "dostaje od systemu, nie z powłoki. Dlatego klucz mieszka w pliku "
            "obok aplikacji, a nie w profilu powłoki."
        )

    if "NOT_FOUND" in tresc or "404" in tresc:
        return (
            f"Google nie zna modelu {MODEL}.\n\n"
            "Model mógł zostać wycofany bez zapowiedzi. Wariant zapasowy to "
            f"{MODEL_STABILNY} — podmiana to jedna linia w `rdzen/doradca.py` "
            "(stała `MODEL`)."
        )

    if ("Errno 8" in tresc or "nodename" in tresc or "Temporary failure" in tresc
            or "Connection" in tresc or "Timeout" in tresc):
        return ("Nie udało się połączyć z Google — sprawdź sieć.\n\n"
                f"Szczegół: {nazwa}: {tresc[:200]}")

    return (f"Nie udało się zapytać modelu.\n\n{nazwa}: {tresc[:400]}\n\n"
            "Tej awarii aplikacja nie rozpoznaje, więc nie zgaduje przyczyny — "
            "powyżej stoi to, co przyszło z serwera.")


async def odpowiedz(pytanie: str, polaczenie=None) -> str:
    """Odpowiada na pytanie, licząc wyłącznie narzędziami wykonanymi lokalnie."""
    if not dostepny():
        return ODPOWIEDZ_BEZ_KLUCZA
    if polaczenie is None:
        return "Brak połączenia z bazą — doradca nie ma czego czytać."

    from google import genai
    from google.genai import types

    klient = genai.Client()
    funkcje = list(narzedzia.zbuduj(polaczenie).values())

    try:
        wynik = await klient.aio.models.generate_content(
            model=MODEL,
            contents=pytanie,
            config=types.GenerateContentConfig(
                system_instruction=instrukcja_systemowa(polaczenie),
                tools=funkcje,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=MAKS_WYWOLAN_NARZEDZI,
                ),
            ),
        )
    except Exception as e:
        return diagnoza_bledu(e)

    tekst = (wynik.text or "").strip() or "Model nie zwrócił odpowiedzi."
    uzyte = _uzyte_narzedzia(wynik)
    ostrzezenie = sprawdz_pokrycie_kwot(tekst, _wyniki_z_historii(wynik))

    czesci = [tekst]
    if uzyte:
        czesci.append("— policzone narzędziami: " + ", ".join(dict.fromkeys(uzyte)))
    elif znajdz_kwoty(tekst):
        czesci.append("— UWAGA: odpowiedź zawiera kwoty, a model nie zawołał "
                      "żadnego narzędzia.")
    if ostrzezenie:
        czesci.append(ostrzezenie)
    return "\n\n".join(czesci)

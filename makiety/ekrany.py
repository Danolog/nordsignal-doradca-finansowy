# -*- coding: utf-8 -*-
"""JEDEN NOSNIK MAPY EKRANOW (M1) — kto jest w pasku, w jakiej kolejnosci
i na jakie pytanie odpowiada.

DLACZEGO OSOBNY PLIK, A NIE LISTA W SKRYPCIE BUDUJACYM. Ta sama lista jest
potrzebna w trzech miejscach: buduje pasek nawigacji (`buduj-makiety.py`),
mierzy sie jej szerokosc (`miara.py`) i cytuje sie ja w dokumencie
(`decyzje-projektowe.md`, sekcja 27). Trzy kopie rozjechalyby sie przy
pierwszej zmianie nazwy — a zmiana nazwy pozycji jest tu najbardziej
prawdopodobna zmiana ze wszystkich (CLAUDE.md par. 8, regula v1.17).

CO NIESIE KAZDA POZYCJA:
  klucz    — nazwa uzywana w kodzie makiet, bez polskich znakow;
  napis    — to, co widac w pasku;
  pytanie  — pytanie uzytkownika, na ktore ten ekran odpowiada. To ONO
             rozstrzyga spory graniczne („gdzie nalezy ZUS"), a nie
             podobienstwo nazw. Zapisane tutaj, bo rozstrzygniecie bez
             kryterium jest opinia, a nie decyzja;
  plik     — ramka makiety albo None, gdy ekran jeszcze nie powstal;
  wysokosc — ZMIERZONA wysokosc dokumentu w pikselach przy szerokosci 1440,
             odczytana z `render.py`, nie oszacowana. Ramka na kanwie dostaje
             dokladnie te liczbe, wiec ekran wyzszy niz okno widac na kanwie
             jako ramke wyzsza od pozostalych — zamiast ucinac go po cichu.

KSIEGOWANIE NIE JEST POZYCJA PASKA — i to jest decyzja, nie przeoczenie.
Pasek odpowiada na pytanie „gdzie jestem", a ksiegowanie na pytanie „co
robie". Darek wskazal mu miejsce OBOK znaku slownego, a nie w rzedzie
z majatkiem i ustawieniami (P-3, 2026-08-28). Stoi wiec w `AKCJA`.

OD 2026-08-28 WIECZOR KSIEGOWANIE MA JUZ SWOJ EKRAN — i to zmienia jedna
rzecz, nie dwie. Zostaje w `AKCJA`, bo powod rozdzielenia byl znaczeniowy,
a nie brak miejsca w pasku (po zdjeciu przelacznika motywu i odsylacza do
starej aplikacji zapasu jest 331,3 px, czyli WIECEJ niz trzeba na dziewiata
pozycje — pomiar wiec tego sporu NIE rozstrzyga, dokument sekcja 41.3).
Zmienia sie natomiast to, ze kontrolka musi umiec niesc stan „tu jestem":
skoro ksiegowanie jest teraz takze MIEJSCEM, pasek bez zadnej pozycji czynnej
klamalby o tym, gdzie uzytkownik stoi.

SPROSTOWANIE (2026-08-28, kontrola Mili, krok 2.1). Zdanie wyzej do dzis
konczylo sie „Stad pole `aktywna_w_pasku`" — ale takiego pola `Ekran` nigdy
nie mial (`__slots__` nizej go nie niesie) i zaden plik go nie czyta (pomiar:
`grep -rn aktywna_w_pasku .` w calym repo daje TYLKO to zdanie, 2026-08-28).
Zdolnosc, o ktorej mowi ten akapit, powstala — tylko INACZEJ, niz akapit
zapowiadal: `buduj-makiety.py::z_paskiem` liczy `w_pasku = aktywna in
ekrany.KLUCZE` z tej samej krotki `KLUCZE`, ktora i tak juz tu jest, zamiast
trzymac drugi, rownolegly bit na kazdym `Ekran`. To WYGRYWA z polem — pole
musialoby byc `True` dla wszystkich dziewieciu pozycji `PASEK` i `False` dla
`AKCJA`, czyli bylby to DRUGI NOSNIK faktu, ktory `KLUCZE`/`PASEK` juz niesie
(CLAUDE.md par. 8, regula v1.17: jeden nosnik). Dokument opisywal wiec plan
sprzed wyboru ostatecznej drogi implementacji i nikt go nie zaktualizowal,
gdy droga sie zmienila — poprawka jest tu, nie w kodzie: kodu nie trzeba
dotykac, bo nic w nim nie brakuje.
"""


class Ekran:
    """Jedna pozycja mapy. Zwykla klasa zamiast slownika, zeby literowka
    w nazwie pola byla bledem przy budowaniu, a nie cicha dziura w pasku."""

    __slots__ = ("klucz", "napis", "pytanie", "plik", "wysokosc")

    def __init__(self, klucz, napis, pytanie, plik=None, wysokosc=900):
        self.klucz, self.napis = klucz, napis
        self.pytanie, self.plik = pytanie, plik
        self.wysokosc = wysokosc


#: Kolejnosc jest trescia, nie porzadkiem alfabetycznym: idzie od pytania
#: zadawanego najczesciej (D-8: „czy dam rade") do zadawanego najrzadziej
#: (nastawy aplikacji). Trzy pierwsze pozycje to pieniadze w czasie —
#: przyszlosc, biezacy miesiac, postanowienia.
PASEK = (
    Ekran("plynnosc", "Płynność",
          "Czy dam radę do końca okresu?", "Main.dc.html", 900),
    Ekran("miesiac", "Miesiąc",
          "Jak mi poszło w tym miesiącu?", "Miesiac.dc.html", 900),
    Ekran("budzet", "Budżet",
          "Co zaplanowałem i jak plan się trzyma?", "Budzet.dc.html", 1483),
    #: Z-30 (2026-08-28, polecenie Darka godz. 18:22): przeszlosc dostaje
    #: swoje miejsce. Stoi CZWARTA, bo trzy pierwsze to pieniadze w czasie
    #: (przyszlosc, biezacy miesiac, postanowienia) — raporty domykaja te
    #: rodzine czwartym czasem: tym, ktory juz byl. Dalej idzie firma, czyli
    #: inna dziedzina, nie inny czas.
    Ekran("raporty", "Raporty",
          "Ile wydałem na to przez dłuższy czas — i na co poszło najwięcej?",
          "Raporty.dc.html", 900),
    Ekran("firma", "Firma",
          "Ile z tego, co zarobiłem, jest moje, a ile urzędu?",
          "Firma.dc.html", 1701),
    Ekran("majatek", "Majątek",
          "Ile jestem wart i komu ile jestem winien?", "Majatek.dc.html", 900),
    Ekran("godziny", "Godziny",
          "Czym się rozliczam — co i przez ile godzin robiłem?",
          "Godziny.dc.html", 900),
    Ekran("doradca", "Doradca",
          "Zapytam o swoje pieniądze własnymi słowami.", "Doradca.dc.html", 900),
    Ekran("ustawienia", "Ustawienia",
          "Jak ta aplikacja ma działać?", "Ustawienia.dc.html", 1639),
)

#: Akcja przy znaku slownym — czynnosc, ktora od 2026-08-28 ma takze swoj
#: ekran. Wysokosc ZMIERZONA renderem, jak u kazdej pozycji paska.
AKCJA = Ekran("ksiegowanie", "Księgowanie",
              "Dopisz wydatek albo przychód — teraz, z każdego miejsca.",
              "Ksiegowanie.dc.html", 972)

#: TRZECIA KATEGORIA, obok `PASEK` i `AKCJA` — rozwiniecie, nie miejsce.
#: „Co mnie czeka" nie jest pozycja paska (pasek ma dziewiec, decyzja P-3)
#: i nie jest akcja przy znaku slownym jak `AKCJA` (nie stoi obok „AI CFO",
#: nie ma wlasnego stanu „tu jestem" — na artboardzie `CoMnieCzeka.dc.html`
#: pasek pokazuje czynna pozycje PLYNNOSC, bo `buduj-makiety.py` renderuje
#: go z `pasek="plynnosc"`, nie z wlasnym kluczem). Dlatego NIE dolacza do
#: `MIEJSCA` nizej: `z_paskiem` nigdy nie dostaje `"co-mnie-czeka"` jako
#: `aktywna`, wiec dopisanie go tam poszerzyloby zbior o wartosc, ktorej
#: nikt nie uzywa jako stanu paska. To jest DRUGIE odgalezienie tego
#: samego pytania co `plynnosc` („Czy dam rade do konca okresu?"), rozbite
#: na pozycje — otwierane z przycisku „Co mnie czeka — N pozycji do …" na
#: ekranie Plynnosci, nigdy z paska ani ze znaku slownego.
#: Wysokosc ZMIERZONA `render.py docs/makiety-v2/CoMnieCzeka.dc.html`
#: (odczyt 2026-08-28: `{"doc": 1080, ...}`), zgodna z `canvas.json`.
ROZWINIECIA = (
    Ekran("co-mnie-czeka", "Co mnie czeka",
          "Co dokładnie nadejdzie do końca okna prognozy — jaki dzień, "
          "jaka pozycja, ile?",
          "CoMnieCzeka.dc.html", 1080),
)
CO_MNIE_CZEKA = ROZWINIECIA[0]

#: Wszystkie miejsca, na ktorych uzytkownik moze STAC — dziewiec pozycji
#: paska plus ksiegowanie. Rozne od `PASEK`, bo ksiegowanie nie jest pozycja
#: paska; rozne od `KLUCZE`, bo `KLUCZE` odpowiada na pytanie „co jest
#: w rzedzie". Trzeci zbior istnieje po to, zeby `buduj-makiety.py` nie
#: musial pisac `KLUCZE + (AKCJA.klucz,)` w trzech miejscach — to byloby te
#: same trzy kopie jednej reguly, przed ktorymi broni ten plik.
#: SPROSTOWANIE (2026-08-28, kontrola Mili): do dzis stalo tu „osiem pozycji
#: paska" — nieprawdziwe od P-3/Z-30, kiedy `PASEK` urosl do dziewieciu
#: (dowod: `len(PASEK)` nizej). `ROZWINIECIA` swiadomie NIE wchodzi do tej
#: sumy — patrz komentarz wyzej.
MIEJSCA = tuple(e.klucz for e in PASEK) + (AKCJA.klucz,)
assert len(PASEK) == 9, \
    f"komentarz MIEJSCA zaklada dziewiec pozycji paska, jest {len(PASEK)}"

#: Ramki, ktore NIE sa ekranami aplikacji i dlatego paska nie dostaja:
#: wzornik reguly barwy i slad wyboru miedzy kierunkami.
BEZ_PASKA = ("TrzyStany.dc.html", "TrzyStany-Ciemny.dc.html",
             "Main-B.dc.html", "Main-Papier.dc.html",
             "Main-Papier-Granat.dc.html", "Main-Papier-Jasny.dc.html")

NAPISY = tuple(e.napis for e in PASEK)
KLUCZE = tuple(e.klucz for e in PASEK)

assert len(set(KLUCZE)) == len(KLUCZE), "klucze ekranow musza byc rozlaczne"
assert len(set(NAPISY)) == len(NAPISY), "napisy w pasku musza byc rozlaczne"
assert AKCJA.klucz not in KLUCZE, \
    "ksiegowanie jest akcja, nie pozycja paska — nie moze byc w obu miejscach"


def tabela():
    """Blok tabeli do dokumentu. Dokument WOLA ten plik, nie przepisuje go."""
    w = ["| # | Pozycja paska | Na jakie pytanie odpowiada | Ramka |",
         "|---|---|---|---|"]
    for numer, e in enumerate(PASEK, start=1):
        plik = f"`{e.plik}`" if e.plik else "**nie powstała**"
        w.append(f"| {numer} | **{e.napis}** | {e.pytanie} | {plik} |")
    plik = f"`{AKCJA.plik}`" if AKCJA.plik else "**nie powstała**"
    w.append(f"| — | *{AKCJA.napis}* (akcja przy znaku słownym, "
             f"nie pozycja paska) | {AKCJA.pytanie} | {plik} |")
    return "\n".join(w)


if __name__ == "__main__":
    print(tabela())

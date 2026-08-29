// JEDEN NOSNIK MAPY EKRANOW PO STRONIE INTERFEJSU.
//
// Odpowiednik `makiety/ekrany.py`. Dwa nosniki tej samej listy to swiadomy
// dlug, dopuszczony pod warunkiem straznika i jawnego progu (CLAUDE.md §3.2):
//   STRAZNIK: `testy/test_mapa_ekranow.py` porownuje oba pliki i czerwieni sie,
//             gdy sie rozjada.
//   PROG:     przy pierwszym dopisaniu albo przemianowaniu pozycji paska —
//             wtedy generujemy ten plik z `ekrany.py` zamiast utrzymywac recznie.
//
// KOLEJNOSC JEST TRESCIA, nie porzadkiem alfabetycznym: idzie od pytania
// zadawanego najczesciej do zadawanego najrzadziej. Trzy pierwsze pozycje to
// pieniadze w czasie — przyszlosc, biezacy miesiac, postanowienia; czwarta
// domyka te rodzine czasem, ktory juz byl.

// ZNAK SLOWNY — jeden nosnik napisu w naglowku.
//
// ODSTEPSTWO OD RAMKI, NAZWANE I ZMIERZONE. Ramki niosą znak „AI CFO"
// (64,5 px przy 15 px / waga 700 / odstep liter 0,16em). Aplikacja nazywa sie
// „Doradca Finansowy" (D-47), a AI CFO jest wygaszane (D-37) — wiec napisu
// z ramki przepisac nie mozna. Pelna nazwa w tej samej typografii ma jednak
// 213,2 px, czyli o 148,7 px wiecej, a caly wiersz naglowka ma zapasu
// 26,2 px (pomiar rendera ramki, 2026-08-29): naglowek by sie rozjechal
// i wiersz przestalby miescic sie w 1440 px.
// Stoi tu wiec forma krotka — 92,6 px, +28,1 px wobec ramki. To jedyne
// miejsce, w ktorym trzeba to zmienic, gdy zapadnie decyzja projektowa.
export const ZNAK_SLOWNY = "Doradca";

export type Ekran = {
  klucz: string;
  napis: string;
  pytanie: string;
  ramka: string;
};

export const PASEK: readonly Ekran[] = [
  { klucz: "plynnosc",   napis: "Płynność",   pytanie: "Czy dam radę do końca okresu?",                         ramka: "Main.dc.html" },
  { klucz: "miesiac",    napis: "Miesiąc",    pytanie: "Jak mi poszło w tym miesiącu?",                          ramka: "Miesiac.dc.html" },
  { klucz: "budzet",     napis: "Budżet",     pytanie: "Co zaplanowałem i jak plan się trzyma?",                 ramka: "Budzet.dc.html" },
  { klucz: "raporty",    napis: "Raporty",    pytanie: "Ile wydałem na to przez dłuższy czas — i na co poszło najwięcej?", ramka: "Raporty.dc.html" },
  { klucz: "firma",      napis: "Firma",      pytanie: "Ile z tego, co zarobiłem, jest moje, a ile urzędu?",     ramka: "Firma.dc.html" },
  { klucz: "majatek",    napis: "Majątek",    pytanie: "Ile jestem wart i komu ile jestem winien?",              ramka: "Majatek.dc.html" },
  { klucz: "godziny",    napis: "Godziny",    pytanie: "Czym się rozliczam — co i przez ile godzin robiłem?",    ramka: "Godziny.dc.html" },
  { klucz: "doradca",    napis: "Doradca",    pytanie: "Zapytam o swoje pieniądze własnymi słowami.",            ramka: "Doradca.dc.html" },
  { klucz: "ustawienia", napis: "Ustawienia", pytanie: "Jak ta aplikacja ma działać?",                           ramka: "Ustawienia.dc.html" },
] as const;

// Ksiegowanie NIE JEST pozycja paska — pasek odpowiada na "gdzie jestem",
// ksiegowanie na "co robie". Stoi OBOK znaku slownego (decyzja Darka P-3).
// Ma jednak wlasny stan "tu jestem", bo od 2026-08-28 jest takze miejscem.
export const AKCJA: Ekran = {
  klucz: "ksiegowanie", napis: "Księgowanie",
  pytanie: "Dopisz wydatek albo przychód — teraz, z każdego miejsca.",
  ramka: "Ksiegowanie.dc.html",
};

// Rozwiniecie, nie miejsce: otwierane z przycisku na ekranie Plynnosci,
// nigdy z paska. Na ramce pasek pokazuje czynna pozycje PLYNNOSC.
export const CO_MNIE_CZEKA: Ekran = {
  klucz: "co-mnie-czeka", napis: "Co mnie czeka",
  pytanie: "Co dokładnie nadejdzie do końca okna prognozy?",
  ramka: "CoMnieCzeka.dc.html",
};

export const MIEJSCA = [...PASEK.map((e) => e.klucz), AKCJA.klucz] as const;

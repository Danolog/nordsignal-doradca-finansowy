// JEDEN NOSNIK MAPY EKRANOW PO STRONIE INTERFEJSU.
//
// Odpowiednik `makiety/ekrany.py`. Dwa nosniki tej samej listy to swiadomy
// dlug, dopuszczony pod warunkiem straznika i jawnego progu (CLAUDE.md §3.2):
//   STRAZNIK: `testy/test_nosniki.py::test_mapa_ekranow_NIE_ROZJECHALA_sie_
//             miedzy_jezykami` porownuje oba pliki i czerwieni sie, gdy sie
//             rozjada. SPROSTOWANIE (W7, 2026-08-29): do dzis stalo tu
//             `testy/test_mapa_ekranow.py` — takiego pliku NIE MA (pomiar:
//             `ls testy/test_mapa_ekranow.py` → No such file or directory).
//             Straznik istnieje, tylko pod innym adresem; blad byl w tym
//             komentarzu, nie w kodzie.
//   PROG:     przy pierwszym dopisaniu albo przemianowaniu pozycji paska —
//             wtedy generujemy ten plik z `ekrany.py` zamiast utrzymywac recznie.
//
// KOLEJNOSC JEST TRESCIA, nie porzadkiem alfabetycznym: idzie od pytania
// zadawanego najczesciej do zadawanego najrzadziej. Trzy pierwsze pozycje to
// pieniadze w czasie — przyszlosc, biezacy miesiac, postanowienia; czwarta
// domyka te rodzine czasem, ktory juz byl.

// ZNAK SLOWNY — jeden nosnik napisu w naglowku po stronie kodu.
//
// WARTOSC WIAZACA: „FINANSE", swiatlo 0,12 em (D-57, PRD v1.4 §16).
// Ramki niosly „AI CFO", kod „Doradca" — byly to DWA NOSNIKI jednej rzeczy
// i rozjechaly sie w ciagu jednej doby. Od Z3 ramki niosa „FINANSE";
// straznik `test_znak_slowny_MA_JEDNA_wartosc_w_kodzie_i_w_ramkach`
// czerwieni sie, gdy kod i ramki znowu powiedza co innego.
//
// DLACZEGO NIE PELNA NAZWA. Budzet wiersza naglowka to 1360 px przy ramce
// 1440 px. Pomiar 2026-08-29 z doliczonym wskaznikiem daty (171,2 px):
// „Doradca Finansowy" przy 0,12 em daje 1439,2 px, czyli zapas −79,2 px —
// nie miesci sie. „Doradca" miesci sie, ale to samo slowo stoi w pasku jako
// nazwa ekranu i znaczyloby w jednym wierszu dwie rzeczy.
// Pelna nazwa aplikacji (D-47) zyje w tytule okna — `app/layout.tsx`.
export const ZNAK_SLOWNY = "FINANSE";

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

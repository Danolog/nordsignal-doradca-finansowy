// JEDYNY NOSNIK KSZTALTU DANYCH PO STRONIE INTERFEJSU.
// Typy powstaja Z EKRANU, nie z wyobrazenia o bazie. `silnik/kontrakt.py`
// niesie odpowiednik; straznik pilnuje, zeby sie nie rozjechaly (CLAUDE.md §3.2).
//
// KAZDA KWOTA JEST NAPISEM. Nigdy `number` — zamiana na liczbe
// zmiennoprzecinkowa gubi grosze (CLAUDE.md §3.1).

export type Kwota = string;   // "274.06" — kropka, bez separatorow
export type Data = string;    // "2026-10-06" — ISO
export type TypWpisu = "Przychody" | "Wydatki" | "Oszczędności";

export interface Kategoria {
  nazwa: string;
  aktywna: boolean;
  systemowa: boolean;
}

export interface WpisDoZapisu {
  data: Data;
  typ: TypWpisu;
  kategoria: string;
  kwota: Kwota;       // ZAWSZE dodatnia — kierunek niesie `typ`, nie znak
  szczegoly: string;
}

// „Co ruszy ten wpis" — PIEC wierszy; dwa ostatnie mowia, co sie NIE
// ruszylo: „Wolne srodki" (licza sie z planu, nie z wpisow) i „Plynnosc"
// (D-62). Piaty powstal, bo po D-20/D-61 wpis miesczacy sie w planie NIE
// ZMIENIA sumy prognozy — a karta, ktora o tym milczy, czyni poprawne
// dzialanie nieodroznialnym od awarii zapisu. KSZTALT SIE NIE ZMIENIL:
// `wiersze` bylo i jest lista, wiec `silnik/kontrakt.py` nie wymagal
// dopasowania. Zmienil sie wylacznie ten komentarz — czyli nosnik
// LICZBY wierszy, ktory po D-62 mowilby nieprawde.
// `po: null` znaczy „ta liczba sie nie zmienia" i wtedy `wyjasnienie` mowi
// dlaczego. Etykieta opisuje liczbe, ktora pokazuje (CLAUDE.md §3.5).
export interface WierszSkutku {
  etykieta: string;
  przed: string;
  po: string | null;
  // `string | null`, NIE `?`. Pole przychodzi z Pythona ZAWSZE — klucz
  // jest w JSON, a wartoscia bywa `null`. `?` obiecywal, ze klucza moze
  // nie byc, czyli typ mowil o kontrakcie cos, czego kontrakt nie robi.
  // Nastepny wykonawca zbudowalby na gwarancji, ktorej nie ma (Z7b).
  wyjasnienie: string | null;
}

export interface PodgladSkutku {
  kwota: Kwota;
  wiersze: readonly WierszSkutku[];
}

export interface OstatniWpis {
  id: number;
  data: Data;
  typ: TypWpisu;
  kategoria: string;
  kwota: Kwota;
  szczegoly: string;
}

export interface DaneKsiegowania {
  dzisiaj: Data;
  typDomyslny: TypWpisu;            // "Wydatki" — 88,7% wpisow
  kategorie: readonly Kategoria[];  // kolejnosc JUZ ustalona przez silnik
  uzasadnienieKolejnosci: string;   // zdanie pod pasmem
  ostatnieWpisy: readonly OstatniWpis[];  // maks. 6
  liczbaWpisowWMiesiacu: number;
  nazwaMiesiaca: string;
  podglad: PodgladSkutku;
  // STOPKA STRAZNIKA — ten sam fakt, co w `DanePlynnosci` (Z7b).
  // Do Z7b tylko Plynnosc miala to pole, wiec Ksiegowanie mowilo „nie wiem"
  // o czyms, co aplikacja WIEDZIALA — dwa ekrany, dwie odpowiedzi na jedno
  // pytanie „czy to, co widze, jest aktualne". `null` = straznik nigdy nie
  // dzialal i tylko to.
  ostatnieSprawdzenie: string | null;
}

// Typy sa wolane z jednego miejsca takze przez trzy pozycje przelacznika —
// czwarty typ pojawilby sie tu, a nie w ukladzie ekranu.
export const TYPY: readonly TypWpisu[] = ["Przychody", "Wydatki", "Oszczędności"] as const;

// Napis przelacznika jest w LICZBIE POJEDYNCZEJ („Wydatek"), a wartosc
// kontraktu w mnogiej („Wydatki") — to dwa rozne jezyki, wiec przeklad
// ma jeden nosnik, zamiast stac w komponencie.
export const NAPIS_TYPU: Readonly<Record<TypWpisu, string>> = {
  Przychody: "Przychód",
  Wydatki: "Wydatek",
  Oszczędności: "Oszczędność",
} as const;

// Dopelniacz liczby mnogiej — „15 kategorii WYDATKOW", podpis pasma kategorii.
// Stoi TU, obok mianownika, a nie w `lib/napisy.ts`: to jest ta sama tabela
// nazw trzech typow, tylko w drugim przypadku. Rozdzielone na dwa pliki byly
// by dwoma nosnikami jednej listy — i przy czwartym typie jeden z nich
// zostalby uzupelniony, a drugi nie.
//
// Straznik zakresu ekranu Plynnosci szuka slowa „Przychody" w zrodlach TEGO
// ekranu (`lib/napisy.ts`, `app/page.tsx`, ...) i ma prawo go tam nie znalezc:
// przychody odpowiadaja na inne pytanie i maja inny ekran. `kontrakt.ts` jest
// wspolny dla wszystkich ekranow, wiec nazwy typow mieszkaja wlasnie tu.
export const DOPELNIACZ_TYPU: Readonly<Record<TypWpisu, string>> = {
  Przychody: "przychodów",
  Wydatki: "wydatków",
  Oszczędności: "oszczędności",
} as const;

/* ---------- EKRAN PLYNNOSCI (Z2) ---------- */

// Wiersz ksiegi. `kwota` moze niesc wiodacy minus — to jest kierunek pozycji,
// nie ozdoba; `znakKwoty()` w `lib/kwota.ts` jest jedynym miejscem, ktore go
// odczytuje, a `sformatujKwote` nadal DOSTAJE znak jako osobny parametr.
export interface PozycjaKsiegi {
  dzien: Data;
  pozycja: string;
  dopisek: string | null;    // "z odczytu 9 920,79 zl z 1 wrzesnia";
                             // `null`, nie brak klucza — patrz WierszSkutku
  kwota: Kwota | null;       // null = wiersz otwarcia, na ekranie „—"
  saldoPoDniu: Kwota | null; // bite RAZ NA DZIEN; null dla kolejnej pozycji tego dnia
}

export interface PunktWykresu {
  dzien: Data;
  saldo: Kwota;
}

export interface DanePlynnosci {
  odczyt: Data;                       // "2026-10-06"
  okresNapis: string;                 // "wrzesien 2026 · 45 dni naprzod"
  ksiega: readonly PozycjaKsiegi[];
  wykres: readonly PunktWykresu[];
  dzienPodKreska: Data | null;        // null = zaden dzien nie schodzi pod zero
  // `null` w obu polach = STAN STARTOWY: nie ma kotwicy, wiec prognozy nie ma
  // od czego liczyc. Rozszerzenie kontraktu z planu, wymuszone D-54: karta
  // „Co mam zrobic" stoi TAKZE w tym stanie i musi umiec powiedziec, czego
  // brakuje, zamiast pokazac obietnice bez pokrycia (§3.7).
  saldoMinimalne: Kwota | null;
  dataSaldaMinimalnego: Data | null;
  zdanieWerdyktu: string;             // nazywa PRZYCZYNE, nie tylko fakt
  horyzontDni: number;                // „Masz 23 dni."
  // `null` = NIE POLICZYLEM, a nie „policzylem i nie ma" (Z7b).
  // Przy odmowie prognozy (brak kotwicy, brak wolumenu) wychodzilo stad
  // `0`, ktore na ekranie czyta sie jako „zero pozycji Cie czeka" — czyli
  // najlepsza mozliwa odpowiedz podana wtedy, gdy nie wiadomo nic.
  // TO JEST TA SAMA KLASA WADY co forma opodatkowania zgadnieta wartoscia
  // domyslna: zero i brak wiedzy wygladaja identycznie, a znacza co innego.
  liczbaPozycjiCoMnieCzeka: number | null;
  koniecOknaCoMnieCzeka: Data;
  ostatnieSprawdzenie: string | null; // null = straznik nigdy nie dzialal
}

/* ---------- EKRAN BUDZET (W9b) ---------- */

// GRANICA MIEDZY SILNIKIEM A WIDOKIEM, NAZWANA RAZ DLA CALEGO EKRANU:
// silnik oddaje LICZBY i NAZWY MIESIECY, widok sklada z nich PROZE (napisy.ts).
// Wyjatek po obu stronach: zdanie niosace liczbe ALBO odmowe silnika sklada
// silnik — `KafelekBudzetu.wyjasnienie`, `CelNaEkranie.tempoNapis`.
// Zapis rzymski dnia („20 X") sklada `lib/kwota.ts` i dostaje dzien POLEM
// (`PozycjaPlanu.dzien`), wiec zaden napis z silnika go nie zawiera.

// `kwota: null` = NIE POLICZYLEM; wtedy `wyjasnienie` mowi, czego brakuje.
// Rezerwa na podatki bez wskazanej formy opodatkowania jest tym przypadkiem:
// zero czytaloby sie jako „nic nie jestes winien urzedowi".
// `klucz` istnieje po to, zeby komponent NIE SIEGAL PO INDEKS tablicy.
export interface KafelekBudzetu {
  klucz: string;                 // "wydatkiZPlanu" | "rezerwa" | "razem"
  tytul: string;
  kwota: Kwota | null;
  dopisek: string;
  wyjasnienie: string | null;
}

// Wiersz tabeli „Plan kontra wykonanie" — jeden na pare (typ, kategoria),
// NIE jeden na pozycje planu. Wpis budzetu nie wskazuje, ktora pozycje planu
// realizuje, wiec „wykonane" da sie policzyc wylacznie per kategoria.
export interface PozycjaWykonania {
  typ: TypWpisu;
  kategoria: string;
  plan: Kwota;
  wykonane: Kwota;
  odchylenie: Kwota;             // wykonane - plan; ujemne = jeszcze nie wydane
  procent: string | null;        // null = planu nie ma; NIGDY "0,0%" w tym stanie
  procentPaska: number | null;   // punkty procentowe przyciete do 0–100
  przekroczone: boolean;
  // null = zero pozycji planu za tym wierszem ALBO wiecej niz jedna. Te dwa
  // przypadki rozroznia `liczbaPozycjiPlanu`; sam null by ich nie rozroznil.
  // Link „zmien pozycje planu" wolno postawic wylacznie, gdy to nie jest null.
  idPozycjiPlanu: number | null;
  liczbaPozycjiPlanu: number;
}

// Regula planu obowiazujaca w wybranym miesiacu — to, co edytuje panel.
// `id` jedzie do `PUT /api/plan/{id}` i `POST /api/plan/{id}/zakoncz`.
export interface PozycjaPlanu {
  id: number;
  typ: TypWpisu;
  kategoria: string;
  opis: string;
  kwota: Kwota;
  dzien: number | null;          // dzien miesiaca; zapis rzymski sklada kwota.ts
  coIleMiesiecy: number;         // 1 = co miesiac, 2 = co drugi
  czeka: boolean;                // dzien jeszcze nie minal w tym miesiacu
}

// Postep liczony Z WPISOW, nigdy z liczby wpisanej recznie: pasek napedzany
// reczna liczba pokazuje to, co uzytkownik wpisal, a nie to, co ma.
export interface CelNaEkranie {
  id: number;
  nazwa: string;
  kategoria: string;
  kwotaDocelowa: Kwota;
  uzbierane: Kwota;
  brakuje: Kwota;
  procent: string;
  procentPaska: number;
  termin: Data;
  tempoNapis: string | null;     // "2 000,00 zl / mc przez 15 mc"; null = nie ma czego dogadniac
  osiagniety: boolean;
  poTerminie: boolean;
}

// Caly ekran w jednej odpowiedzi — kazdy zapis rusza NARAZ kafelki, bilans,
// tabele i licznik naglowka, wiec odpowiedz „zapisano" kazalaby przegladarce
// zlozyc te liczby po swojemu albo odpytac drugi raz.
export interface DaneBudzetu {
  dzisiaj: Data;
  miesiac: string;                  // "2026-10"
  miesiacNapis: string;             // "październik 2026" — selektor
  nazwaMiesiaca: string;            // "październiku" — miejscownik dla napisy.ts
  // LICZY TAKZE CELE — tak, jak liczy je naglowek ramki („4 pozycje planu"
  // = trzy wydatki + jeden cel). Sama dlugosc `pozycjePlanu` dalaby trzy.
  liczbaPozycjiPlanu: number;
  liczbaWpisow: number;
  kafelki: readonly KafelekBudzetu[];
  planPrzychodow: Kwota;
  planWydatkow: Kwota;
  planOszczednosci: Kwota;
  // Rezerwa podatkowa NIE WCHODZI w te liczbe — stoi w kafelku, osobno.
  bilansPlanu: Kwota;
  wykonaneWydatki: Kwota;
  pozycjeWykonania: readonly PozycjaWykonania[];
  pozycjePlanu: readonly PozycjaPlanu[];
  cele: readonly CelNaEkranie[];
  historia: readonly OstatniWpis[]; // wpisy TEGO miesiaca, od najnowszego
  miesiacKopiujZ: string;           // "2026-09"
  napisKopiujZ: string;             // "Skopiuj z września"
  ostatnieSprawdzenie: string | null;
}

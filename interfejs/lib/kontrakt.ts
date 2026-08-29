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

// „Co ruszy ten wpis" — cztery wiersze; czwarty mowi, co sie NIE ruszylo.
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

// STRAŻNIK WZORCOWEGO ZESTAWU DANYCH — liczby WYCIĘTE Z RAMEK, nie przepisane.
//
// PO CO. Od Z7c bramka odwzorowania mierzy ekran na wzorcowym zestawie danych
// (D-63), a nie na żywym miesiącu. Wzorzec, który rozjedzie się z ramką, jest
// GORSZY niż brak wzorca: bramka meldowałaby wtedy zgodność z rysunkiem,
// którego nikt już nie rysuje, a różnica 0,00% znaczyłaby tylko tyle, że dwa
// nasze własne pliki zgadzają się ze sobą.
//
// W CO TEN STRAŻNIK TRAFIA. W kwoty wycięte z `makiety/*.dc.html` przy KAŻDYM
// przebiegu, porównane z kwotami, które ekran narysuje ze wzorca — złożonymi
// przez `lib/kwota.ts`, czyli TEN SAM nośnik formatowania, którego używa ekran.
// Własna kopia reguły formatowania byłaby drugim nośnikiem i przepuściłaby
// dokładnie te wady, których ma pilnować.
//
// ILE RZECZY WIDZI. Pierwszy test pyta, ile kwot wycięcie w ogóle znalazło.
// Bez tego pomiar na zmienionym znaczniku ramki (zero trafień) porównywałby
// pustą listę z pustą listą i meldował sukces.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";
import { sformatujKwote, znakKwoty } from "../lib/kwota.ts";
import { ZESTAWY, ZNACZNIK_WZORCA } from "../narzedzia/dane-wzorcowe.mjs";

const KATALOG = dirname(fileURLToPath(import.meta.url));
const RAMKI = join(KATALOG, "..", "..", "makiety");

/** Kwoty stojące w ramce, w kolejności rysowania. */
function kwotyZRamki(nazwa) {
  const html = readFileSync(join(RAMKI, `${nazwa}.dc.html`), "utf8");
  return [...html.matchAll(/>([^<>]*zł)</g)]
    .map((m) => m[1].replace(/&nbsp;/g, " ").trim())
    // Kwota w dopisku („z odczytu … zł z 1 września") nie jest komórką
    // rubryki — stoi wewnątrz zdania i wchodzi na ekran jako część `dopisek`,
    // nie przez `sformatujKwote`. Porównujemy ją osobno, niżej.
    .filter((k) => /^[−+]?[\d  ]+,\d{2} zł$/.test(k));
}

/** Kwoty, które ekran narysuje ze wzorca — w tej samej kolejności. */
function kwotyZeWzorca(zestaw) {
  const wynik = [];
  for (const p of zestaw.ksiega) {
    if (p.kwota !== null) wynik.push(sformatujKwote(p.kwota, znakKwoty(p.kwota)));
    if (p.saldoPoDniu !== null) wynik.push(sformatujKwote(p.saldoPoDniu, "neutralna"));
  }
  if (zestaw.saldoMinimalne !== null) {
    wynik.push(sformatujKwote(zestaw.saldoMinimalne, znakKwoty(zestaw.saldoMinimalne)));
  }
  return wynik;
}

// Ramka pisze rozdzielacz tysięcy jako `&nbsp;`, a `lib/kwota.ts` — zwykłą
// spacją. To jest ZNANY, ZMIERZONY dług spacji: kosztował 0 pikseli, bo oba
// znaki rysują się identycznie i żaden z nich nie łamie tu wiersza. Nośnikiem
// poprawki jest `silnik/prezentacja.py`, nie ten test — więc porównujemy
// kwoty po sprowadzeniu obu spacji do jednej.
const jednaSpacja = (k) => k.replace(/ /g, " ");

test("wycięcie kwot z ramek NAPRAWDĘ coś znalazło", () => {
  expect(kwotyZRamki("Main").length).toBe(10);
  expect(kwotyZRamki("Main-Dobrze").length).toBe(14);
});

test("wzorzec Main niesie DOKŁADNIE kwoty ramki, w kolejności rysowania", () => {
  expect(kwotyZeWzorca(ZESTAWY.main.plynnosc).map(jednaSpacja))
    .toEqual(kwotyZRamki("Main").map(jednaSpacja));
});

test("wzorzec Main-Dobrze niesie DOKŁADNIE kwoty ramki, w kolejności rysowania", () => {
  expect(kwotyZeWzorca(ZESTAWY["main-dobrze"].plynnosc).map(jednaSpacja))
    .toEqual(kwotyZRamki("Main-Dobrze").map(jednaSpacja));
});

test("dopisek wiersza otwarcia jest przepisany z ramki znak po znaku", () => {
  for (const [nazwa, klucz] of [["Main", "main"], ["Main-Dobrze", "main-dobrze"]]) {
    const html = readFileSync(join(RAMKI, `${nazwa}.dc.html`), "utf8");
    const wRamce = html.match(/— z odczytu[^<]*/)[0].replace(/&nbsp;/g, " ");
    expect(jednaSpacja(ZESTAWY[klucz].plynnosc.ksiega[0].dopisek)).toBe(jednaSpacja(wRamce));
  }
});

test("zdanie werdyktu stoi w ramce dosłownie", () => {
  for (const [nazwa, klucz] of [["Main", "main"], ["Main-Dobrze", "main-dobrze"]]) {
    const html = readFileSync(join(RAMKI, `${nazwa}.dc.html`), "utf8").replace(/&nbsp;/g, " ");
    expect(html).toContain(jednaSpacja(ZESTAWY[klucz].plynnosc.zdanieWerdyktu));
  }
});

// ZNACZNIK WZORCA jest jedyną obroną bramki odwzorowania przed zmierzeniem
// żywych danych zamiast wzorca. Musi więc naprawdę stać w ramkach — i musi
// stać w KAŻDYM zestawie, bo bramka szuka go na ekranie niezależnie od tego,
// który wzorzec jest podstawiony.
test("znacznik wzorca stoi w ramkach i w każdym zestawie", () => {
  for (const nazwa of ["Main", "Main-Dobrze", "Ksiegowanie"]) {
    expect(readFileSync(join(RAMKI, `${nazwa}.dc.html`), "utf8")).toContain(ZNACZNIK_WZORCA);
  }
  const zestawy = Object.values(ZESTAWY);
  expect(zestawy.length).toBe(5);
  for (const z of zestawy) {
    expect(z.plynnosc.ostatnieSprawdzenie).toBe(ZNACZNIK_WZORCA);
    expect(z.ksiegowanie.ostatnieSprawdzenie).toBe(ZNACZNIK_WZORCA);
  }
});

// Ramka Księgowania rysuje kartę „Co ruszy ten wpis" w stanie po wpisaniu
// 274,06 zł — i to jest jedyny stan, który bramka odwzorowania ogląda.
test("wzorzec karty Księgowania niesie liczby z ramki", () => {
  const html = readFileSync(join(RAMKI, "Ksiegowanie.dc.html"), "utf8");
  const wiersze = ZESTAWY.ksiegowanie.ksiegowanie.podglad.wiersze;
  expect(wiersze.length).toBe(4);
  for (const w of wiersze) {
    expect(html).toContain(w.etykieta);
    if (w.po !== null) expect(html).toContain(w.po.replace(/ /g, "&nbsp;"));
    if (w.wyjasnienie !== null) expect(html).toContain(w.wyjasnienie);
  }
});

// LICZBA WIERSZY KARTY — strażnik długu opisanego w `dane-wzorcowe.mjs`.
//
// Po D-62 produkcja rysuje w karcie „Co ruszy ten wpis" PIĘĆ wierszy, a ramka
// nadal cztery. Wzorzec trzyma się ramki, więc bramka odwzorowania jest wobec
// piątego wiersza ślepa — 0,12% i przed D-62, i po nim. To jest świadomy dług,
// a świadomy dług wolno zostawić WYŁĄCZNIE ze strażnikiem i progiem (§3.2).
//
// W CO TEN STRAŻNIK TRAFIA: w liczbę wierszy SIATKI w ramce, między nagłówkiem
// „Co ruszy ten wpis" a „Czego tu nie ma" — nie w tekst brzmienia. Brzmienie
// należy do silnika i przepisane tutaj byłoby jego drugim nośnikiem; liczba
// wierszy należy do rysunku i tu jest na miejscu.
//
// PRÓG: w chwili, w której Mila dorysuje piąty wiersz, ten test się czerwieni
// i wzorzec dostaje piąty wiersz razem z jego brzmieniem z ramki.
test("liczba wierszy karty w ramce zgadza się z wzorcem", () => {
  const html = readFileSync(join(RAMKI, "Ksiegowanie.dc.html"), "utf8");
  const od = html.indexOf("Co ruszy ten wpis");
  const doJ = html.indexOf("Czego tu nie ma");
  expect(od).toBeGreaterThan(-1);
  expect(doJ).toBeGreaterThan(od);
  const wycinek = html.slice(od, doJ);
  const wierszeRamki = [...wycinek.matchAll(/<div style="display: grid;/g)].length;
  // Kontrola liczności: wycinek, w którym nie ma ANI JEDNEGO wiersza, znaczy,
  // że zmieniła się budowa ramki i pomiar patrzy w puste miejsce.
  expect(wierszeRamki).toBeGreaterThan(0);
  expect(wierszeRamki).toBe(ZESTAWY.ksiegowanie.ksiegowanie.podglad.wiersze.length);
});

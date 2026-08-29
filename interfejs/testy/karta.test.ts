// STRAZNIK KARTY „CO MAM ZROBIC" — trzy stany, brzmienia WYCIETE Z RAMEK.
//
// Testy nie porownuja z napisem przepisanym do testu, tylko z tekstem
// wyjetym z `makiety/CoMamZrobic.dc.html` przy kazdym przebiegu. Roznica jest
// istotna: przepisany napis to trzeci nosnik jednego zdania i rozjezdza sie
// po cichu — dokladnie tak, jak rozjechal sie znak slowny miedzy ramkami
// a kodem.
//
// Karta musi dzialac w KAZDYM z trzech stanow, takze w dobrym miesiacu
// i w stanie startowym. Karta znikajaca uczylaby, ze jej pojawienie sie
// oznacza klopot, a to buduje odruch nieotwierania aplikacji wtedy, gdy jest
// najbardziej potrzebna — dlatego stan 2 i stan 3 maja tu wlasne testy,
// mimo ze bramka odwzorowania oglada wylacznie stan 1.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";
import { ulozKarte } from "../lib/karta-dzialania";
import { NAPISY_KARTY } from "../lib/napisy";

const KATALOG = dirname(fileURLToPath(import.meta.url));
const RAMKI = join(KATALOG, "..", "..", "makiety");

function ramka(nazwa: string): string {
  return readFileSync(join(RAMKI, `${nazwa}.dc.html`), "utf8");
}

function bezZnacznikow(html: string): string {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/ /g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// Wycina akapity z KART w ramce: kazdy blok zaczyna sie od naglowka
// „Co mam zrobić" i konczy na zamknieciu karty. Zwraca liste list akapitow.
function karty(nazwa: string): string[][] {
  const html = ramka(nazwa);
  const wynik: string[][] = [];
  let od = 0;
  for (;;) {
    const i = html.indexOf(">Co mam zrobić</span>", od);
    if (i === -1) break;
    // Karta konczy sie na pierwszym pustym wierszu po niej — tak sa
    // sformatowane wszystkie ramki tego projektu.
    const koniec = html.indexOf("\n\n", i);
    const blok = html.slice(i, koniec === -1 ? html.length : koniec);
    const akapity = [...blok.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map((m) => bezZnacznikow(m[1]));
    wynik.push(akapity);
    od = i + 1;
  }
  return wynik;
}

const SPECYFIKACJA = karty("CoMamZrobic");

test("ramka specyfikacji niesie DOKLADNIE trzy stany karty", () => {
  // Kontrola licznosci: sprawdzenie, do ktorego dociera pusty zbior, melduje
  // sukces. Gdyby wycinanie przestalo cokolwiek znajdowac, wszystkie
  // porownania nizej przechodzilyby na pustych napisach.
  expect(SPECYFIKACJA.length).toBe(3);
  expect(SPECYFIKACJA[0].length).toBe(2);
  expect(SPECYFIKACJA[1].length).toBe(2);
  expect(SPECYFIKACJA[2].length).toBe(1);
});

test("stan 1 — jest co robic: brzmienie zgadza sie z ramka co do znaku", () => {
  const k = ulozKarte({ saldoMinimalne: "-210.67", dataSaldaMinimalnego: "2026-09-25" });
  expect(k.stan).toBe("deficyt");
  expect(k.stan !== "brak-danych" && k.zdanie).toBe(SPECYFIKACJA[0][0]);
  expect(k.stan !== "brak-danych" && k.koszt).toBe(SPECYFIKACJA[0][1]);
});

test("stan 2 — wszystko w porzadku: karta NIE ZNIKA i nie dorabia drugiego dzialania", () => {
  const k = ulozKarte({ saldoMinimalne: "2468.39", dataSaldaMinimalnego: "2026-10-12" });
  expect(k.stan).toBe("nadwyzka");
  expect(k.stan !== "brak-danych" && k.zdanie).toBe(SPECYFIKACJA[1][0]);
  expect(k.stan !== "brak-danych" && k.koszt).toBe(SPECYFIKACJA[1][1]);
});

test("stan 3 — brak danych: karta mowi, CZEGO brakuje, i nie zmysla liczby", () => {
  const k = ulozKarte({ saldoMinimalne: null, dataSaldaMinimalnego: null });
  expect(k.stan).toBe("brak-danych");
  expect(k.zdanie).toBe(SPECYFIKACJA[2][0]);
  // Zdanie stanu 3 nie moze niesc ZADNEJ kwoty — obietnica bez pokrycia
  // jest gorsza niz brak obietnicy (§3.7).
  expect(k.zdanie).not.toMatch(/\d+[,.]\d{2}/);
});

test("brak samej daty tez znaczy nie wiem, a nie zero", () => {
  expect(ulozKarte({ saldoMinimalne: "-210.67", dataSaldaMinimalnego: null }).stan).toBe("brak-danych");
  expect(ulozKarte({ saldoMinimalne: null, dataSaldaMinimalnego: "2026-09-25" }).stan).toBe("brak-danych");
});

test("karta stoi we WSZYSTKICH stanach ekranu pierwszego, nie tylko w zlym", () => {
  for (const nazwa of ["Main", "Main-Ciemny", "Main-Dobrze", "NieWiem"]) {
    expect(karty(nazwa).length, `ramka ${nazwa} nie niesie karty`).toBe(1);
  }
});

test("karta na ramce Main niesie DOKLADNIE to, co uklada kod", () => {
  const k = ulozKarte({ saldoMinimalne: "-210.67", dataSaldaMinimalnego: "2026-09-25" });
  expect(karty("Main")[0]).toEqual([
    k.stan !== "brak-danych" ? k.zdanie : "",
    k.stan !== "brak-danych" ? k.koszt : "",
  ]);
});

test("nosnik brzmien nie zawiera drugiego dzialania — zakres v1 to dokladnie jedno", () => {
  const klucze = Object.keys(NAPISY_KARTY);
  expect(klucze).toEqual([
    "tytul",
    "deficytZdanie",
    "deficytKoszt",
    "nadwyzkaZdanie",
    "nadwyzkaKoszt",
    "brakDanych",
  ]);
});

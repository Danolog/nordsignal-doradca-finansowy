// ODCZYT TEGO, CO CZLOWIEK WPISAL — jeden nosnik dla dwoch ekranow (W8).
//
// Do W8 ta regula stala wylacznie w `app/ksiegowanie/formularz.tsx` i NIE MIALA
// ANI JEDNEGO TESTU: sprawdzalo ja dopiero klikanie po ekranie. Kontrolka stanu
// konta potrzebuje jej co do znaku identycznie, wiec regula wyszla do
// `lib/kwota.ts` — a wyjscie bez strazniika bylo by przeniesieniem ryzyka,
// nie jego zdjeciem.
//
// NAJWAZNIEJSZY PRZYPADEK JEST NA KONCU: kwota ujemna. Konto na debecie to
// realny stan konta, a nie blad wpisu, i jest to JEDYNE miejsce w aplikacji,
// w ktorym minus jest czescia liczby. Zgubiony tutaj minus zamienia debet
// 1 240 zl w majatek 1 240 zl — przy zielonej suicie i kodzie 200.

import { expect, test } from "vitest";
import { dataJestCzytelna, odczytajKwote } from "../lib/kwota";

test("kwota z przecinkiem czytana jest jako kwota z kropką", () => {
  expect(odczytajKwote("9920,79")).toEqual({ stan: "ok", kwota: "9920.79" });
});

test("jednostka i spacje nie przeszkadzają — człowiek pisze, jak mu wygodnie", () => {
  expect(odczytajKwote(" 9 920,79 zł ")).toEqual({ stan: "ok", kwota: "9920.79" });
});

test("spacja nierozdzielająca też schodzi — tak kwotę oddaje `sformatujKwote`", () => {
  expect(odczytajKwote("9 920,79 zł")).toEqual({ stan: "ok", kwota: "9920.79" });
});

test("grosz kończący się zerem NIE ginie — napis zostaje napisem", () => {
  // Wada zmierzona w tej sesji po drugiej stronie granicy: "8623.10" wychodziło
  // jako "8623.1" z kodem 200. Odczyt nie ma prawa jej wprowadzić u siebie.
  expect(odczytajKwote("8623,10")).toEqual({ stan: "ok", kwota: "8623.10" });
});

test("puste pole to STAN PUSTY, a nie zero", () => {
  // Zero jest odpowiedzią („mam zero na koncie"), pustka jest jej brakiem.
  // Zlanie tych dwóch rzeczy to ta sama klasa wady, co forma opodatkowania
  // zgadnięta wartością domyślną.
  expect(odczytajKwote("   ")).toEqual({ stan: "pusta" });
  expect(odczytajKwote("0")).toEqual({ stan: "ok", kwota: "0" });
});

test("trzy miejsca po przecinku są nieczytelne, nie zaokrąglane po cichu", () => {
  expect(odczytajKwote("100,005")).toEqual({ stan: "nieczytelna" });
  expect(odczytajKwote("dużo")).toEqual({ stan: "nieczytelna" });
});

test("kwota UJEMNA jest rozpoznana, a nie odrzucona — konto na debecie", () => {
  expect(odczytajKwote("-1240,50")).toEqual({ stan: "ujemna", kwota: "1240.50" });
});

test("data czytana w czasie powszechnym — 6 X 2026 jest czytelna", () => {
  // Zmierzone 2026-08-29: przy odczycie w czasie lokalnym poprawna data
  // wypadała jako nieczytelna i blokowała KAŻDY zapis.
  expect(dataJestCzytelna("2026-10-06")).toBe(true);
  expect(dataJestCzytelna("2026-09-01")).toBe(true);
});

test("data nieistniejąca i data w złym zapisie są odrzucone", () => {
  expect(dataJestCzytelna("2026-02-30")).toBe(false);
  expect(dataJestCzytelna("06.10.2026")).toBe(false);
});

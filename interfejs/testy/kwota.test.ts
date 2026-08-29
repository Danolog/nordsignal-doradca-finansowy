// Test PADAJACY napisany PRZED modulem `lib/kwota.ts` (krok 2 planu Z1).
// Bramka: ma paczc na BRAKU MODULU. Test, ktory przeszedl od razu, nie dowodzi niczego.
import { expect, test } from "vitest";
import { sformatujDate, sformatujDzien, sformatujDzienSlownie, sformatujKwote, znakKwoty } from "../lib/kwota";

test("kwota dodatnia dostaje znak plus i spację jako separator tysięcy", () => {
  expect(sformatujKwote("11200.00", "dodatnia")).toBe("+11 200,00 zł");
});
test("kwota ujemna dostaje znak minus", () => {
  expect(sformatujKwote("210.67", "ujemna")).toBe("−210,67 zł");
});
test("kwota neutralna nie dostaje znaku", () => {
  expect(sformatujKwote("274.06", "neutralna")).toBe("274,06 zł");
});
test("grosze nie giną — kwota jest napisem, nie liczbą", () => {
  expect(sformatujKwote("1305.05", "neutralna")).toBe("1 305,05 zł");
});
test("data w zapisie rzymskim miesiąca, jak na ramkach", () => {
  expect(sformatujDate("2026-10-06")).toBe("6 X 2026");
});

test("dzień bez roku — kolumna księgi nie powtarza roku w każdym wierszu", () => {
  expect(sformatujDzien("2026-09-02")).toBe("2 IX");
  expect(sformatujDzien("2026-10-17")).toBe("17 X");
});
test("dzień słownie — data stojąca w zdaniu, nie w kolumnie liczb", () => {
  expect(sformatujDzienSlownie("2026-09-25")).toBe("25 września");
  expect(sformatujDzienSlownie("2026-10-17")).toBe("17 października");
});
test("kierunek odczytany z zapisu kwoty ma jeden nośnik", () => {
  expect(znakKwoty("-1305.05")).toBe("ujemna");
  expect(znakKwoty("9601.03")).toBe("neutralna");
});
test("znak nadal jest osobnym parametrem — zapis ujemny da się pokazać bez znaku", () => {
  expect(sformatujKwote("-210.67", "neutralna")).toBe("210,67 zł");
});

// ZNAK WIODĄCY W ZAPISIE KWOTY (Z7c). `znakKwoty` rozpoznaje trzy zapisy —
// „-…", „+…" i goły — więc `sformatujKwote` musi umieć zdjąć każdy z nich.
// Do Z7c zdejmowany był wyłącznie minus i kwota z plusem wracała jako
// „++2 468,39 zł". Wada nie miała jak paść, bo żywy silnik dodatniego salda
// minimalnego nie podpisuje; czekała na pierwszy dobry miesiąc.
test("wiodący plus jest ZDEJMOWANY, nie doklejany drugi raz", () => {
  expect(sformatujKwote("+2468.39", "dodatnia")).toBe("+2 468,39 zł");
  expect(sformatujKwote("+2468.39", "neutralna")).toBe("2 468,39 zł");
});
test("minus typograficzny wraca z tej funkcji taki sam, jak z niej wyszedł", () => {
  const raz = sformatujKwote("210.67", "ujemna");
  expect(raz).toBe("−210,67 zł");
  expect(sformatujKwote("−210.67", "ujemna")).toBe(raz);
});
test("para znakKwoty + sformatujKwote czyta ten sam zbiór zapisów", () => {
  for (const [zapis, oczekiwany] of [
    ["-210.67", "−210,67 zł"],
    ["+2468.39", "+2 468,39 zł"],
    ["9601.03", "9 601,03 zł"],
  ] as const) {
    expect(sformatujKwote(zapis, znakKwoty(zapis))).toBe(oczekiwany);
  }
});

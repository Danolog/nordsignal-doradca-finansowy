// Test PADAJACY napisany PRZED modulem `lib/kwota.ts` (krok 2 planu Z1).
// Bramka: ma paczc na BRAKU MODULU. Test, ktory przeszedl od razu, nie dowodzi niczego.
import { expect, test } from "vitest";
import { sformatujKwote, sformatujDate } from "../lib/kwota";

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

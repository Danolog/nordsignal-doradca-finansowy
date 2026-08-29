// STRAŻNIK ROZRÓŻNIENIA „NIE WIEM" OD „ZERO" (D-64).
//
// PO CO ISTNIEJE. `DanePlynnosci.liczbaPozycjiCoMnieCzeka` jest od Z7b
// `number | null`: `null` znaczy „NIE POLICZYŁEM", `0` znaczy „policzyłem
// i nie ma". Do Z7b stał tam goły `number`, więc przy odmowie prognozy
// wychodziło „Co mnie czeka — 0 pozycji", czyli NAJLEPSZA MOŻLIWA WIADOMOŚĆ
// podana wtedy, gdy nie ma żadnej wiadomości. To jest ta sama klasa wady co
// forma opodatkowania zgadnięta wartością domyślną: brak wiedzy udający wiedzę.
//
// Strona Pythona jest już pilnowana (`testy/test_luki_kontraktu_z7b.py`).
// Ten strażnik pilnuje strony EKRANU — tego, że oba stany dają dwa RÓŻNE
// zdania. Kontrakt może nieść rozróżnienie, którego napis i tak nie pokazuje.
//
// KONTROLA DWUSTRONNA. Nie wystarczy sprawdzić, że `null` daje zdanie
// o niepoliczeniu: test przeszedłby także wtedy, gdyby TO SAMO zdanie
// wychodziło dla zera. Dlatego każdy przypadek ma parę „zawiera" +
// „NIE zawiera", a na koniec stoi pytanie wprost: czy te dwa zdania w ogóle
// się różnią.

import { expect, test } from "vitest";
import { NAPISY_PLYNNOSCI, NAPISY_POWLOKI } from "../lib/napisy";

const DZIEN = "17 października";

test("null czyta się jako NIE POLICZYŁEM, nigdy jako zero", () => {
  const zdanie = NAPISY_PLYNNOSCI.coMnieCzeka(null, DZIEN);
  expect(zdanie).toContain("jeszcze nie policzyłem");
  expect(zdanie).not.toContain("0");
  expect(zdanie).not.toContain("pozycji");
});

test("zero czyta się jako POLICZYŁEM I NIE MA, nigdy jako brak wiedzy", () => {
  const zdanie = NAPISY_PLYNNOSCI.coMnieCzeka(0, DZIEN);
  expect(zdanie).toContain("0 pozycji");
  expect(zdanie).toContain(DZIEN);
  expect(zdanie).not.toContain("nie policzyłem");
});

test("oba stany dają DWA RÓŻNE zdania — bez tego rozróżnienie jest na papierze", () => {
  expect(NAPISY_PLYNNOSCI.coMnieCzeka(null, DZIEN))
    .not.toBe(NAPISY_PLYNNOSCI.coMnieCzeka(0, DZIEN));
});

test("liczba dodatnia nadal podaje liczbę i dzień końca okna", () => {
  expect(NAPISY_PLYNNOSCI.coMnieCzeka(7, DZIEN)).toBe(`Co mnie czeka — 7 pozycji do ${DZIEN}`);
});

// TA SAMA RODZINA WADY, DRUGI EKRAN. Stopka strażnika: `null` znaczy
// „strażnik nigdy nie działał" i musi mówić o tym wprost, zamiast podawać
// datę sprawdzenia, którego nie było (§3.7).
test("stopka strażnika, który nigdy nie działał, mówi o tym wprost", () => {
  expect(NAPISY_POWLOKI.straznikNieDzialal).toContain("brak danych");
  expect(NAPISY_POWLOKI.straznikNieDzialal).not.toMatch(/\d{1,2}:\d{2}/);
});

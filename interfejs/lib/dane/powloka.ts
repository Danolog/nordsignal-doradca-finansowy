// DANE POWLOKI — wspolne dla wszystkich jedenastu ekranow.
//
// Stad je wyjeto: do Z2 mieszkaly w `dane/ksiegowanie.ts`, wiec ekran
// Plynnosci musialby wolac dane Ksiegowania, zeby poznac wlasny naglowek.
// Zaleznosc byla falszywa: to nie jest wiedza jednego ekranu.
//
// ODCZYT NAGLOWKA jest STALY, nie z zegara systemowego. Bramka odwzorowania
// porownuje zrzuty, a ruchoma godzina dawalaby inny wynik przy kazdym
// przebiegu. Zegar wchodzi razem z trasami (Z6).

export const ODCZYT_NAGLOWKA = "6 października 2026 · 09:40";

// Stan strażnika. `null` znaczy „strażnik nigdy nie działał" i NIE wolno go
// zamieniać na zdanie o sprawdzeniu — zero nigdy nie zastępuje „nie wiem".
export const OSTATNIE_SPRAWDZENIE: string | null =
  "Ostatnie sprawdzenie: dziś 06:00 — nic pilnego nie znalazł.";

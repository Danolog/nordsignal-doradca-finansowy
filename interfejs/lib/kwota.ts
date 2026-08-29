// JEDEN NOSNIK FORMATOWANIA KWOT I DAT PO STRONIE INTERFEJSU.
// Odpowiednik `silnik/prezentacja.py`. Widok WOLA, nigdy nie formatuje sam.
//
// KWOTA PRZYCHODZI JAKO NAPIS I TAK ZOSTAJE. Zamiana na `number` gubi grosze —
// poprzednia aplikacja robila to w warstwie sieciowej i ZWRACALA 200.
// Stad zero `parseFloat` i zero `Number()` na sciezce kwoty; jedyne `Number`
// w tym pliku stoi na SKLADNIKACH DATY, gdzie nie ma groszy do zgubienia.
//
// ZNAK JEST OSOBNYM PARAMETREM, nie jest wyprowadzany ze znaku liczby.
// Powod jest dostepnosciowy, nie estetyczny: barwa nie moze byc jedynym
// nosnikiem znaczenia, a zielen dobrana pod rowna wage z czerwienia ma po
// odbarwieniu roznice 0,00. Znak "+"/"−" jest wiec WYMOGIEM.

export type ZnakKwoty = "dodatnia" | "ujemna" | "neutralna";

const RZYMSKIE = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];

export function sformatujKwote(kwota: string, znak: ZnakKwoty): string {
  const [calosc, grosze = "00"] = kwota.replace("-", "").split(".");
  const zSpacjami = calosc.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const prefiks = znak === "dodatnia" ? "+" : znak === "ujemna" ? "−" : "";
  return `${prefiks}${zSpacjami},${grosze.padEnd(2, "0")} zł`;
}

export function sformatujDate(iso: string): string {
  const [rok] = iso.split("-");
  return `${sformatujDzien(iso)} ${rok}`;
}

// Jedyne miejsce, ktore ODCZYTUJE kierunek z zapisu kwoty. `sformatujKwote`
// nadal dostaje znak jako OSOBNY parametr — ta funkcja go nie omija, tylko
// nazywa krok, w ktorym ksiega mowi, w ktora strone plyna pieniadze.
// Bez niej kazdy widok robilby `kwota.startsWith("-")` u siebie, czyli
// reguly kierunku bylaby tyle, ile ekranow.
export function znakKwoty(kwota: string): ZnakKwoty {
  if (kwota.startsWith("-")) return "ujemna";
  if (kwota.startsWith("+")) return "dodatnia";
  return "neutralna";
}

// Dzien bez roku — „2 IX". Kolumna „Dzien" w ksiedze i podpisy osi wykresu
// nie powtarzaja roku przy kazdym wierszu.
export function sformatujDzien(iso: string): string {
  const [, miesiac, dzien] = iso.split("-");
  return `${Number(dzien)} ${RZYMSKIE[Number(miesiac) - 1]}`;
}

// Dzien z nazwa miesiaca — „25 wrzesnia". Uzywany tam, gdzie data stoi
// w zdaniu, a nie w kolumnie liczb.
const MIESIACE_DOPELNIACZ = [
  "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
  "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
];

export function sformatujDzienSlownie(iso: string): string {
  const [, miesiac, dzien] = iso.split("-");
  return `${Number(dzien)} ${MIESIACE_DOPELNIACZ[Number(miesiac) - 1]}`;
}

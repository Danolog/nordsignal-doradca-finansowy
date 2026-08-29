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
  const [rok, miesiac, dzien] = iso.split("-");
  return `${Number(dzien)} ${RZYMSKIE[Number(miesiac) - 1]} ${rok}`;
}

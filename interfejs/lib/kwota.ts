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

// ZNAK WIODĄCY ZDEJMUJEMY W KOMPLECIE, nie samym minusem — poprawka Z7c.
// `znakKwoty()` niżej ROZPOZNAJE trzy zapisy: „-…", „+…" i goły. Tutaj
// zdejmowany był wyłącznie minus, więc kwota z wiodącym plusem wracała jako
// „++2 468,39 zł": prefiks doklejał się do plusa, który już w niej stał.
// Zmierzone na wzorcu ramki `Main-Dobrze.dc.html`, gdzie wiersz „Najniżej"
// niesie „+2 468,39 zł". Żywy silnik dodatniego salda minimalnego dziś nie
// podpisuje, więc ta wada nie miała jak paść — a to jest dokładnie ten
// rodzaj wady, który czeka do pierwszego dobrego miesiąca.
// Minus typograficzny (U+2212) też, bo tym znakiem pisze ta funkcja: kwota
// raz sformatowana i wpuszczona z powrotem nie ma się rozsypać.
export function sformatujKwote(kwota: string, znak: ZnakKwoty): string {
  const [calosc, grosze = "00"] = kwota.replace(/^[-+\u2212]/, "").split(".");
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

// Dzien miesiaca zapisem rzymskim — „20 X". Jedyny nosnik tego zapisu dla
// pozycji planu, ktora dostaje dzien POLEM (`PozycjaPlanu.dzien`), a nie data:
// regula planu obowiazuje do odwolania, wiec nie ma jednej daty, ktora by ja
// opisywala. Zaden napis z silnika tego zapisu nie zawiera — mowi o tym wprost
// naglowek „EKRAN BUDZET" w `lib/kontrakt.ts`.
//
// TABLICA JEST TA SAMA, ktorej uzywa `sformatujDzien` — jeden nosnik zapisu
// rzymskiego po stronie interfejsu, nie drugi.
export function dzienWMiesiacu(dzien: number, miesiac: string): string {
  const [, numer] = miesiac.split("-");
  return `${dzien} ${RZYMSKIE[Number(numer) - 1]}`;
}

// „Czy ta kwota jest zerem" — PRACA WYLACZNIE NA NAPISIE, jak wszystko na
// sciezce kwoty (§3.1). Odpowiedz jest potrzebna tam, gdzie zero i brak
// znacza dla czytajacego co innego: „nie wydales jeszcze nic" brzmi inaczej
// niz „wydales 0,00 zl", a „oszczednosci nie zaplanowales" inaczej niz
// „plan oszczednosci 0,00 zl". Regula ma jeden nosnik, bo inaczej kazdy
// ekran rozstrzygalby ja u siebie — i pierwszy, ktory zapomni o wiodacym
// znaku, pokaze zdanie o niezaplanowanych oszczednosciach przy kwocie.
export function kwotaJestZerem(kwota: string): boolean {
  return /^[-+−]?0+([.,]0+)?$/.test(kwota.trim());
}

// Miesiac w dopelniaczu razem z rokiem — „października 2026". Stoi w zdaniu
// „Zakoncz te pozycje OD …" i w potwierdzeniu konca reguly (Budzet, W9c).
//
// DLACZEGO SKLADA TO WIDOK, A NIE SILNIK. Kontrakt niesie miesiac w dwoch
// przypadkach: mianowniku (`miesiacNapis` — „październik 2026", napis
// selektora) i miejscowniku (`nazwaMiesiaca` — „październiku"). Dopelniacza
// nie ma i dokladanie go do kontraktu byloby trzecia forma tej samej nazwy
// przesylana przez granice po to, zeby zlozyc jedno zdanie — a granica
// warstw mowi wprost: silnik oddaje NAZWY MIESIECY, proze sklada widok
// (`lib/kontrakt.ts`, naglowek „EKRAN BUDZET").
//
// TABLICA JEST TA SAMA, ktora sluzy `sformatujDzienSlownie` — jeden nosnik
// odmiany po stronie interfejsu, nie drugi. Odpowiednik po stronie silnika
// (`silnik/prezentacja.MIESIACE_DOPELNIACZ`) istnial przed ta funkcja i nie
// przybywa przez nia ani jeden nosnik.
export function sformatujMiesiacDopelniacz(miesiac: string): string {
  const [rok, numer] = miesiac.split("-");
  return `${MIESIACE_DOPELNIACZ[Number(numer) - 1]} ${rok}`;
}

// Odczyt w naglowku — „6 października 2026". Odpowiada na pytanie „z ktorego
// dnia jest to, co widze", i od Z7 bierze ten dzien Z DANYCH: `DanePlynnosci.
// odczyt` albo `DaneKsiegowania.dzisiaj`, czyli dokladnie ten dzien, dla
// ktorego silnik policzyl liczby nizej.
//
// GODZINY TU NIE MA I TO JEST DECYZJA, NIE BRAK. Do Z7 naglowek niosl stala
// „6 października 2026 · 09:40" — godzina nie miala zadnego nosnika i po
// podpieciu byla by liczba z nieznanego zrodla obok liczb ze zrodla znanego
// (CLAUDE.md §3.5, §3.7). Wraca w chwili, gdy kontrakt zacznie niesc znacznik
// czasu odczytu, a nie sama date.
export function sformatujOdczyt(iso: string): string {
  const [rok] = iso.split("-");
  return `${sformatujDzienSlownie(iso)} ${rok}`;
}

/* ---------- ODCZYT TEGO, CO CZLOWIEK WPISAL (W8) ---------- */

// JEDEN NOSNIK KSZTALTU WPISANEJ KWOTY. Do W8 ta regula stala wylacznie
// w `app/ksiegowanie/formularz.tsx`; kontrolka stanu konta potrzebuje jej
// co do znaku identycznie — a druga kopia rozjechalaby sie przy pierwszej
// zmianie (CLAUDE.md §3.2). Rozdzielone zostaje to, co NAPRAWDE rozne:
// odczyt mowi, ze kwota jest ujemna, a KAZDY ekran sam rozstrzyga, co z tym
// zrobic. Ksiegowanie pyta („minus jest w typie wpisu"), stan konta
// przyjmuje bez pytania (konto na debecie to realny stan konta).
//
// PRACA WYLACZNIE NA NAPISIE: zdejmujemy jednostke i separatory, zamieniamy
// przecinek na kropke i sprawdzamy KSZTALT wyrazeniem regularnym. Nigdzie
// nie powstaje liczba, wiec nie ma gdzie zgubic groszy (CLAUDE.md §3.1).
export type OdczytKwoty =
  | { stan: "pusta" }
  | { stan: "nieczytelna" }
  | { stan: "ujemna"; kwota: string }   // kwota BEZ minusa — znak niesie `stan`
  | { stan: "ok"; kwota: string };

export function odczytajKwote(tekst: string): OdczytKwoty {
  const oczyszczony = tekst
    .replace(/zł/gi, "")
    .replace(/[\s ]/g, "")
    .replace(",", ".")
    .trim();
  if (oczyszczony === "") return { stan: "pusta" };
  if (!/^-?\d+(\.\d{1,2})?$/.test(oczyszczony)) return { stan: "nieczytelna" };
  if (oczyszczony.startsWith("-")) return { stan: "ujemna", kwota: oczyszczony.slice(1) };
  return { stan: "ok", kwota: oczyszczony };
}

// Data budowana i czytana W CZASIE POWSZECHNYM (UTC), nigdy lokalnym.
// Zmierzone 2026-08-29: `new Date("2026-10-06T00:00:00")` to czas LOKALNY,
// wiec w strefie letniej Warszawy `getUTCDate()` zwracal 5, nie 6 — i poprawna
// data 6 X 2026 wypadala jako nieczytelna, blokujac KAZDY zapis.
export function dataJestCzytelna(iso: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return false;
  const [rok, miesiac, dzien] = iso.split("-");
  const d = new Date(Date.UTC(Number(rok), Number(miesiac) - 1, Number(dzien)));
  return (
    !Number.isNaN(d.getTime()) &&
    d.getUTCFullYear() === Number(rok) &&
    d.getUTCMonth() + 1 === Number(miesiac) &&
    d.getUTCDate() === Number(dzien)
  );
}

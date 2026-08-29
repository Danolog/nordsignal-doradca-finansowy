// JEDEN NOSNIK GEOMETRII WYKRESU PLYNNOSCI.
//
// PO CO OSOBNY MODUL. Rysunek wymaga wspolrzednych, a wspolrzedne wymagaja
// liczb — wiec gdzies kwota musi przestac byc napisem. Ten modul jest tym
// jedynym miejscem i mowi to wprost, zamiast rozsypywac `Number()` po
// komponencie. Wynik tej zamiany NIGDY nie wraca na ekran jako kwota:
// wychodza stad wylacznie piksele. Kwoty pokazuje `sformatujKwote`,
// ktora liczby nie widzi (CLAUDE.md §3.1).
//
// STRAZNIK: `testy/wykres.test.ts` porownuje wynik ZNAK PO ZNAKU z atrybutem
// `d` z ramki `makiety/Main.dc.html`. Nie „mniej wiecej ta sama linia" —
// dokladnie ten sam napis. Bez tego bramka odwzorowania mierzylaby zgodnosc
// rysunku dopiero na pikselach, czyli za pozno, zeby powiedziec dlaczego.

import type { PunktWykresu } from "./kontrakt";

// Miary z ramki: pole rysunku 1040 x 64 px, linia biegnie miedzy 10 a 54 px.
// Gorny i dolny margines sa nierowne celowo — dolny miesci grubosc odcinka
// pod kreska (3 px) i znacznik dnia zejscia (promien 4,5 px).
export const SZEROKOSC = 1040;
export const WYSOKOSC = 64;
const GORA = 10;
const DOL = 54;

export interface PunktRysunku {
  x: number;
  y: number;
  podKreska: boolean;
}

function jakoLiczba(kwota: string): number {
  return Number(kwota);
}

export function punkty(seria: readonly PunktWykresu[]): PunktRysunku[] {
  const wartosci = seria.map((p) => jakoLiczba(p.saldo));
  const gorne = Math.max(...wartosci);
  const dolne = Math.min(...wartosci);
  const rozpietosc = gorne - dolne || 1;
  const krok = seria.length > 1 ? SZEROKOSC / (seria.length - 1) : 0;
  return wartosci.map((v, i) => ({
    x: i * krok,
    y: GORA + ((gorne - v) / rozpietosc) * (DOL - GORA),
    podKreska: v < 0,
  }));
}

function przecinek(p: PunktRysunku): string {
  return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
}

export function sciezka(pkt: readonly PunktRysunku[]): string {
  if (pkt.length === 0) return "";
  return `M${przecinek(pkt[0])}` + pkt.slice(1).map((p) => ` L${przecinek(p)}`).join("");
}

// Linia zera. `null`, gdy zero nie miesci sie w rozpietosci serii — wtedy
// kreski nie ma, zamiast rysowac ja na krawedzi i klamac o polozeniu.
export function liniaZera(seria: readonly PunktWykresu[]): number | null {
  const wartosci = seria.map((p) => jakoLiczba(p.saldo));
  const gorne = Math.max(...wartosci);
  const dolne = Math.min(...wartosci);
  if (gorne < 0 || dolne > 0) return null;
  const rozpietosc = gorne - dolne || 1;
  return GORA + (gorne / rozpietosc) * (DOL - GORA);
}

// Odcinek pod kreska rysowany jest TA SAMA czerwienia co kwota zamkniecia.
// To cala jego robota: oko wiaze dolek z liczba, zanim ktokolwiek przeczyta
// cyfry. Zwracamy pusty napis, gdy prognoza nie schodzi pod zero.
export function odcinekPodKreska(pkt: readonly PunktRysunku[]): string {
  const pod = pkt.filter((p) => p.podKreska);
  return sciezka(pod);
}

export function pierwszyPunktPodKreska(pkt: readonly PunktRysunku[]): PunktRysunku | null {
  return pkt.find((p) => p.podKreska) ?? null;
}

// STRAZNIK GEOMETRII WYKRESU — porownanie ZNAK PO ZNAKU z ramka.
//
// Napisy nizej sa WYCIETE z `makiety/Main.dc.html`, nie przepisane z pamieci.
// Gdyby skala, marginesy albo krok osi rozjechaly sie choc o dziesiata czesc
// piksela, ten test pada, podajac ktore wspolrzedne — a bramka odwzorowania
// powiedzialaby tylko „rozni sie 0,4%".
import { expect, test } from "vitest";
import { DANE } from "../lib/dane/plynnosc";
import { liniaZera, odcinekPodKreska, pierwszyPunktPodKreska, punkty } from "../lib/wykres";

const D_Z_RAMKI =
  "M0.0,10.0 L23.1,10.0 L46.2,10.0 L69.3,10.0 L92.4,10.0 L115.6,10.0 L138.7,10.0 " +
  "L161.8,10.0 L184.9,10.0 L208.0,10.0 L231.1,15.9 L254.2,15.9 L277.3,15.9 L300.4,16.5 " +
  "L323.6,16.5 L346.7,16.5 L369.8,16.5 L392.9,16.5 L416.0,16.5 L439.1,39.5 L462.2,39.5 " +
  "L485.3,39.5 L508.4,39.5 L531.6,54.0 L554.7,54.0 L577.8,54.0 L600.9,54.0 L624.0,54.0 " +
  "L647.1,16.3 L670.2,17.8 L693.3,17.8 L716.4,17.8 L739.6,17.8 L762.7,17.8 L785.8,17.8 " +
  "L808.9,17.8 L832.0,17.8 L855.1,17.8 L878.2,17.8 L901.3,17.8 L924.4,23.6 L947.6,23.6 " +
  "L970.7,23.6 L993.8,23.6 L1016.9,23.6 L1040.0,23.6";

const D_ODCINKA_Z_RAMKI = "M531.6,54.0 L554.7,54.0 L577.8,54.0 L600.9,54.0 L624.0,54.0";

test("seria ma czterdziesci szesc dni — 2 IX do 17 X wlacznie", () => {
  expect(DANE.wykres.length).toBe(46);
  expect(DANE.wykres[0].dzien).toBe("2026-09-02");
  expect(DANE.wykres[45].dzien).toBe("2026-10-17");
});

test("sciezka prognozy odtwarza sie z ramki co do dziesiatej czesci piksela", () => {
  const pkt = punkty(DANE.wykres);
  const wynik = `M${pkt[0].x.toFixed(1)},${pkt[0].y.toFixed(1)}` +
    pkt.slice(1).map((p) => ` L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join("");
  expect(wynik).toBe(D_Z_RAMKI);
});

test("odcinek pod kreska to piec dni, 25-29 IX, i tylko one", () => {
  expect(odcinekPodKreska(punkty(DANE.wykres))).toBe(D_ODCINKA_Z_RAMKI);
});

test("linia zera stoi tam, gdzie w ramce", () => {
  expect(liniaZera(DANE.wykres)!.toFixed(1)).toBe("53.1");
});

test("znacznik dnia zejscia stoi na pierwszym dniu pod kreska", () => {
  const p = pierwszyPunktPodKreska(punkty(DANE.wykres))!;
  expect([p.x.toFixed(1), p.y.toFixed(1)]).toEqual(["531.6", "54.0"]);
});

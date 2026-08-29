"use client";

// EKRAN KSIEGOWANIE — jedyny ekran, na ktorym uzytkownik COS ROBI.
// Uklad przeniesiony wezel po wezle z `makiety/Ksiegowanie.dc.html`.
//
// TRZY KLIKNIECIA DO ZAPISU, i to jest bramka, nie ambicja:
//   1. wejscie na ekran  -> formularz GOTOWY: data = dzis, typ = Wydatek,
//                           KURSOR JUZ STOI W POLU KWOTY (`autoFocus`),
//   2. kafelek kategorii -> wybor z pasma widocznego, bez rozwijania listy,
//   3. „Zapisz wpis"     -> wpis w bazie.
// Wpisanie kwoty nie kosztuje kliknieca, bo kursor tam stoi — to wlasnie
// `autoFocus` zdejmuje trzecie kliknienie. Usuniecie go lamie bramke.
//
// ZERO KWOT W TYM PLIKU. Kazda liczba przychodzi z `lib/dane/ksiegowanie.ts`
// i jest formatowana przez `lib/kwota.ts`. Pilnuje tego straznik
// `test_ekran_NIE_MA_wpisanej_recznie_kwoty`.
//
// ZERO BRZMIEN W TYM PLIKU. Wszystkie siedem stanow bledu i wszystkie
// etykiety wola `lib/napisy.ts`.
//
// KWOTA JEST NAPISEM OD POCZATKU DO KONCA. Zero `parseFloat`, zero `Number()`
// na jej sciezce — zamiana na liczbe zmiennoprzecinkowa gubi grosze
// (CLAUDE.md §3.1).

import { useId, useState } from "react";
import { Powloka } from "../powloka";
import { NAPISY, PROZA, type Czlon } from "@/lib/napisy";
import { sformatujDate, sformatujKwote } from "@/lib/kwota";
import { NAPIS_TYPU, TYPY, type Kwota, type TypWpisu } from "@/lib/kontrakt";
import {
  DANE,
  ODCZYT_NAGLOWKA,
  PODPIS_PASMA,
  STAN_POKAZOWY,
  STRAZNIK_STOPKI,
} from "@/lib/dane/ksiegowanie";
import s from "./style.module.css";

/* ---------- odczyt tego, co uzytkownik wpisal ---------- */

type OdczytKwoty =
  | { stan: "pusta" }
  | { stan: "nieczytelna" }
  | { stan: "ujemna"; kwota: Kwota }
  | { stan: "ok"; kwota: Kwota };

// Praca WYLACZNIE na napisie: zdejmujemy jednostke i separatory, zamieniamy
// przecinek na kropke i sprawdzamy KSZTALT wyrazeniem regularnym. Nigdzie
// nie powstaje liczba, wiec nie ma gdzie zgubic groszy.
function odczytajKwote(tekst: string): OdczytKwoty {
  const oczyszczony = tekst
    .replace(/zł/gi, "")
    .replace(/[\s ]/g, "")
    .replace(",", ".")
    .trim();
  if (oczyszczony === "") return { stan: "pusta" };
  if (!/^-?\d+(\.\d{1,2})?$/.test(oczyszczony)) return { stan: "nieczytelna" };
  if (oczyszczony.startsWith("-")) return { stan: "ujemna", kwota: oczyszczony.slice(1) };
  return { stan: "ok", kwota: oczyszczony };
}

// Data budowana i czytana W CZASIE POWSZECHNYM (UTC), nigdy lokalnym.
// Zmierzone 2026-08-29: `new Date("2026-10-06T00:00:00")` to czas LOKALNY,
// wiec w strefie letniej Warszawy `getUTCDate()` zwraca 5, nie 6 — i poprawna
// data 6 X 2026 wypadala jako przypadek (a) z §41.5, blokujac KAZDY zapis.
// Brzmienia bledu nie cytujemy nawet w komentarzu: ma JEDEN nosnik
// (`lib/napisy.ts`) i pilnuje tego `test_siedem_brzmien_bledu_MA_JEDEN_nosnik`.
function dataJestCzytelna(iso: string): boolean {
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

/* ---------- znaki rysowane, przeniesione z ramki ---------- */

function Ptaszek() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 7.4l2.6 2.6L11 4.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Strzalka() {
  return (
    <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
      <path d="M0 5h12M8.5 1.5L12 5l-3.5 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Daszek() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Plus() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 3.5v9M3.5 8h9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function Proza({ czlony, klasa }: { czlony: readonly Czlon[]; klasa: string }) {
  return (
    <p className={klasa}>
      {czlony.map((c, i) =>
        c.akcent ? (
          <span key={i} className={s.akcent}>
            {c.tekst}
          </span>
        ) : (
          <span key={i}>{c.tekst}</span>
        )
      )}
    </p>
  );
}

/* ---------- ekran ---------- */

export default function Ksiegowanie() {
  const idKwoty = useId();
  const idSzczegolow = useId();

  const [typ, setTyp] = useState<TypWpisu>(DANE.typDomyslny);
  const [data] = useState(DANE.dzisiaj);
  const [kwotaTekst, setKwotaTekst] = useState(
    sformatujKwote(STAN_POKAZOWY.kwota, "neutralna")
  );
  const [szczegoly, setSzczegoly] = useState(STAN_POKAZOWY.szczegoly);
  const [kategoria, setKategoria] = useState<string | null>(STAN_POKAZOWY.kategoria);
  const [bladDaty, setBladDaty] = useState<string | null>(null);
  const [bladKwoty, setBladKwoty] = useState<string | null>(null);
  const [pytanieOMinus, setPytanieOMinus] = useState<Kwota | null>(null);
  const [bladKategorii, setBladKategorii] = useState<string | null>(null);
  const [bladTypu, setBladTypu] = useState<string | null>(null);

  const odczyt = odczytajKwote(kwotaTekst);
  const podpisPodgladu =
    odczyt.stan === "ok" || odczyt.stan === "ujemna"
      ? sformatujKwote(odczyt.kwota, "neutralna")
      : sformatujKwote(DANE.podglad.kwota, "neutralna");

  // Zmiana typu zdejmuje wybor kategorii, bo kategoria nalezy do slownika
  // JEDNEGO typu — zostawiona po przelaczeniu bylaby wyborem z cudzej listy.
  // Pasmo nadal pokazuje slownik wydatkow: kategorie przychodow i oszczednosci
  // przychodza z silnika (`magazyn.wczytaj_kategorie(typ)`) razem z trasami.
  function zmienTyp(nowy: TypWpisu) {
    setTyp(nowy);
    setKategoria(null);
    wyczyscBledy();
  }

  function wyczyscBledy() {
    setBladDaty(null);
    setBladKwoty(null);
    setPytanieOMinus(null);
    setBladKategorii(null);
    setBladTypu(null);
  }

  // Zapis: siedem stanow z §41.5, kazdy z osobnym brzmieniem. Wspolny
  // komunikat „blad" dla siedmiu przyczyn jest tym samym, co brak komunikatu.
  function zapisz() {
    wyczyscBledy();
    let wolno = true;

    if (!TYPY.includes(typ)) {                       // (g) — niemozliwe z konstrukcji
      setBladTypu(NAPISY.blad.typNieznany);
      wolno = false;
    }
    if (!dataJestCzytelna(data)) {                   // (a)
      setBladDaty(NAPISY.blad.dataNieczytelna);
      wolno = false;
    }
    if (odczyt.stan === "pusta") {                   // (b)
      setBladKwoty(NAPISY.blad.kwotaPusta);
      wolno = false;
    }
    if (odczyt.stan === "nieczytelna") {             // (c)
      setBladKwoty(NAPISY.blad.kwotaNieczytelna);
      wolno = false;
    }
    if (odczyt.stan === "ujemna") {                  // (d) — PYTANIE, nie blad
      setPytanieOMinus(odczyt.kwota);
      wolno = false;
    }

    const wybrana = DANE.kategorie.find((k) => k.nazwa === kategoria);
    if (!wybrana) {                                  // (e)
      setBladKategorii(NAPISY.blad.kategoriaNiewybrana);
      wolno = false;
    } else if (!wybrana.aktywna) {                   // (f)
      setBladKategorii(NAPISY.blad.kategoriaNieaktywna(wybrana.nazwa));
      wolno = false;
    }

    if (!wolno) return;
    przekaz(odczyt.stan === "ok" ? odczyt.kwota : "");
  }

  // Po zapisie zostaja data, typ i kategoria; czysci sie kwota i szczegoly.
  // Trasa zapisu powstaje w Z6 — do tego czasu formularz zachowuje sie tak,
  // jak ma sie zachowac, i NIE udaje, ze cokolwiek trafilo do bazy.
  function przekaz(_kwota: Kwota) {
    setKwotaTekst("");
    setSzczegoly("");
  }

  return (
    <Powloka aktywny="ksiegowanie" odczyt={ODCZYT_NAGLOWKA} straznik={STRAZNIK_STOPKI}>
      <section className={s.ekran}>

        {/* 1-2. przelacznik typu + data wpisu */}
        <div className={s.sekcjaNaglowka}>
          <div className={s.wierszNaglowka}>
            <span className={s.tytulEkranu}>{NAPISY.tytul}</span>

            <div className={s.przelacznik} role="radiogroup" aria-label={NAPISY.tytul}>
              {TYPY.map((t, i) => (
                <span key={t} style={{ display: "contents" }}>
                  {i > 0 && <span className={s.rozdzielacz} />}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={t === typ}
                    aria-current={t === typ ? "true" : undefined}
                    className={t === typ ? `${s.pozycja} ${s.pozycjaCzynna}` : s.pozycja}
                    onClick={() => zmienTyp(t)}
                  >
                    {t === typ && <Ptaszek />}
                    <span>{NAPIS_TYPU[t]}</span>
                  </button>
                </span>
              ))}
            </div>

            <span className={s.rozpychacz} />
            <span className={s.etykieta}>{NAPISY.etykietaDatyWpisu}</span>
            <button type="button" className={s.kontrolkaDaty}>
              <span className={s.dataSzeryfowa}>{sformatujDate(data)}</span>
              <Daszek />
            </button>
          </div>
          <div className={s.kreska} />
          <div className={s.przerwa} />
          <div className={s.kreska} />
          {bladDaty && (
            <span className={s.podpisUwagi} role="alert">
              {bladDaty}
            </span>
          )}
          {bladTypu && (
            <span className={s.podpisUwagi} role="alert">
              {bladTypu}
            </span>
          )}
        </div>

        {/* 3-5. kwota, podpis o znaku, szczegoly */}
        <div className={s.wierszPol}>
          <div className={s.kolumnaKwoty}>
            <label className={s.etykieta} htmlFor={idKwoty}>
              {NAPISY.etykietaKwoty}
            </label>
            <span className={bladKwoty ? `${s.ramkaKwoty} ${s.uwaga}` : s.ramkaKwoty}>
              <input
                id={idKwoty}
                className={s.wpisKwoty}
                inputMode="decimal"
                autoFocus
                aria-required="true"
                aria-invalid={bladKwoty ? true : undefined}
                value={kwotaTekst}
                onChange={(e) => setKwotaTekst(e.target.value)}
              />
            </span>
            {/* Podpis stoi ZAWSZE, nie tylko po bledzie — po to, zeby blad (d)
                zdarzal sie rzadziej, a nie zeby go tlumaczyc po fakcie.
                Obszar mowiacy (`aria-live`) obejmuje podpis RAZEM z bledami,
                zamiast stac obok pusty: pusty obszar byl by czwartym dzieckiem
                kolumny i dokladal 8 px odstepu, ktorego ramka nie ma. */}
            <div className={s.podKwota} aria-live="polite">
              <span className={s.podpis}>{NAPISY.bezZnaku}</span>
              {bladKwoty && <span className={s.podpisUwagi}>{bladKwoty}</span>}
              {pytanieOMinus && (
                <>
                  <span className={s.podpisUwagi}>
                    {NAPISY.blad.kwotaUjemna(
                      sformatujKwote(pytanieOMinus, "neutralna"),
                      NAPIS_TYPU[typ]
                    )}
                  </span>{" "}
                  <button
                    type="button"
                    className={s.potwierdzenie}
                    onClick={() => {
                      const potwierdzona = pytanieOMinus;
                      setPytanieOMinus(null);
                      przekaz(potwierdzona);
                    }}
                  >
                    {NAPISY.blad.kwotaUjemnaPotwierdzenie}
                  </button>
                </>
              )}
            </div>
          </div>

          <div className={s.kolumnaSzczegolow}>
            <label className={s.etykieta} htmlFor={idSzczegolow}>
              {NAPISY.etykietaSzczegolow}
            </label>
            <span className={s.ramkaSzczegolow}>
              <input
                id={idSzczegolow}
                className={s.wpisSzczegolow}
                value={szczegoly}
                onChange={(e) => setSzczegoly(e.target.value)}
              />
            </span>
          </div>
        </div>

        {/* 6-7. pasmo kategorii + podpis o kolejnosci */}
        <div className={s.sekcjaKategorii}>
          <div className={s.wierszEtykietyKategorii}>
            <span className={s.etykieta}>{NAPISY.etykietaKategorii}</span>
            <span className={s.podpis}>{PODPIS_PASMA}</span>
          </div>
          <div
            className={s.pasmo}
            role="radiogroup"
            aria-label={NAPISY.etykietaKategorii}
            aria-invalid={bladKategorii ? true : undefined}
          >
            {DANE.kategorie.map((k) => {
              const czynny = k.nazwa === kategoria;
              const klasa = [
                s.kafelek,
                czynny ? s.kafelekCzynny : "",
                k.aktywna ? "" : s.kafelekNieaktywny,
                bladKategorii && !czynny ? s.uwaga : "",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <button
                  key={k.nazwa}
                  type="button"
                  role="radio"
                  aria-checked={czynny}
                  aria-current={czynny ? "true" : undefined}
                  className={klasa}
                  onClick={() => setKategoria(k.nazwa)}
                >
                  {czynny && <Ptaszek />}
                  <span>{k.nazwa}</span>
                </button>
              );
            })}
          </div>
          {/* Ten sam powod co przy kwocie: obszar mowiacy obejmuje podpis
              o kolejnosci, zamiast stac obok pusty. */}
          <div className={s.podPasmem} aria-live="polite">
            {bladKategorii && <span className={s.podpisUwagi}>{bladKategorii}</span>}
            <span className={s.podpis}>{DANE.uzasadnienieKolejnosci}</span>
          </div>
        </div>

        {/* 8-9. zapis + podpis o tym, co po nim zostaje */}
        <div className={s.wierszZapisu}>
          <button type="button" className={s.przyciskZapisz} onClick={zapisz}>
            <Plus />
            <span>{NAPISY.zapisz}</span>
          </button>
          <span className={s.podpisZapisu}>
            {NAPISY.coZostajePoZapisie}
            <span className={s.akcent}>{NAPISY.coZostajePoZapisieAkcent}</span>
            {NAPISY.coZostajePoZapisieOgon}
          </span>
        </div>

        {/* 10-12. co ruszy ten wpis · czego tu nie ma · ostatnie wpisy */}
        <div className={s.dwieKolumny}>
          <div className={s.kolumna}>
            <div className={s.naglowekBloku}>
              <span className={s.etykieta}>{NAPISY.tytulPodgladu}</span>
              <span className={s.podpis}>{NAPISY.podpisPodgladu(podpisPodgladu)}</span>
            </div>

            {DANE.podglad.wiersze.map((w) =>
              w.po === null ? (
                // Czwarty wiersz mowi, co sie NIE ruszylo, i to jest wazniejsze
                // od trzech pierwszych: bez niego Darek szukalby ruchu, ktorego
                // nie ma, i uznalby to za wade obliczen.
                <div key={w.etykieta} className={s.wierszBezZmian}>
                  <span className={s.etykietaWierszaCicha}>{w.etykieta}</span>
                  <span className={s.etykietaWierszaCicha}>{w.wyjasnienie}</span>
                </div>
              ) : (
                <div key={w.etykieta} className={s.wierszSkutku}>
                  <span className={s.etykietaWiersza}>{w.etykieta}</span>
                  <span className={s.liczbaPrzed}>{w.przed}</span>
                  <Strzalka />
                  <span className={s.liczbaPo}>{w.po}</span>
                </div>
              )
            )}

            <div className={s.naglowekBlokuDalszego}>
              <span className={s.etykieta}>{NAPISY.tytulCzegoTuNieMa}</span>
            </div>
            <Proza czlony={PROZA.czegoTuNieMa} klasa={s.proza} />
          </div>

          <div className={s.kolumna}>
            <div className={s.naglowekBloku}>
              <span className={s.etykieta}>{NAPISY.tytulOstatnichWpisow}</span>
              <span className={s.podpis}>
                {NAPISY.licznikWpisow(DANE.liczbaWpisowWMiesiacu, DANE.nazwaMiesiaca)}
              </span>
            </div>

            {DANE.ostatnieWpisy.length === 0 ? (
              <>
                <p className={s.pustaHistoria}>{NAPISY.pustaHistoria}</p>
                <Proza czlony={PROZA.pustaHistoriaPowod} klasa={s.prozaBlisko} />
                <Proza czlony={PROZA.pustaHistoriaHoryzont} klasa={s.prozaBlisko} />
              </>
            ) : (
              <div className={s.listaWpisow}>
                {DANE.ostatnieWpisy.slice(0, 6).map((w) => (
                  <div key={w.id} className={s.wierszWpisu}>
                    <span className={s.etykietaWierszaCicha}>{sformatujDate(w.data)}</span>
                    <span className={s.etykietaWiersza}>{w.kategoria}</span>
                    <span className={s.liczbaPo}>
                      {sformatujKwote(w.kwota, w.typ === "Przychody" ? "dodatnia" : "ujemna")}
                    </span>
                    <button type="button" className={s.wycofaj}>
                      wycofaj
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </section>
    </Powloka>
  );
}

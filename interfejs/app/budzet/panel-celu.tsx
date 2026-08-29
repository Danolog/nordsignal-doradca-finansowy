"use client";

// PANEL CELU OSZCZEDNOSCIOWEGO — kontrolka „Dodaj cel" z ramki (W9c).
//
// DLACZEGO OSOBNY PLIK, A NIE TRZECI TRYB PANELU PLANU. Pozycja planu i cel
// odpowiadaja na dwa rozne pytania i maja rozne pola: pozycja ma typ, dzien
// miesiaca i cykl, cel ma termin i nie ma zadnego z tamtych trzech. Wspolny
// komponent z dwoma rozlacznymi zestawami pol bylby jednym plikiem udajacym
// dwie rzeczy — a rozjazd miedzy nimi bylby niewidoczny.
//
// CZEGO RAMKA NIE RYSUJE: samych pol. `makiety/Budzet.dc.html` rysuje wezwanie
// „Dodaj cel" i nic poza nim; uklad ponizej jest ODSTEPSTWEM od §3.6 tej samej
// klasy co panel pozycji planu i tej samej klasy co kontrolka stanu konta
// z W8. Zgloszone, nie milczace; straznik z progiem w `test_ekran_budzet.py`.
//
// KATEGORIA MUSI BYC TYPU „Oszczednosci" i rozstrzyga to `magazyn.zapisz_cel`,
// nie ten plik. Cel wskazujacy kategorie wydatku liczylby postep z pieniedzy
// WYDANYCH — pasek pokazywalby, ze zbierasz na wakacje, im wiecej wydajesz
// na zakupy. Odmowa silnika wraca tu w calosci, jego slowami (§3.7).
//
// PROG WYLICZANY (PRD §10.3, S-2) — DLUG JAWNY, NIE PRZEOCZENIE.
// PRD rozstrzyga, ze prog poduszki finansowej jest LICZONY (6 x wydatki
// niezbedne), a wartosc nadpisana recznie ma byc widocznie oznaczona.
// `CelNaEkranie` nie niesie ani liczonego progu, ani znacznika nadpisania,
// a `POST /api/cele` przyjmuje wylacznie kwote wpisana. Wyliczenie progu
// w przegladarce byloby drugim nosnikiem reguly podatkowo-budzetowej i nie
// mialoby skad wziac „wydatkow niezbednych". Luka zgloszona;
// straznik z progiem: `testy/test_ekran_budzet.py::
// test_prog_poduszki_CZEKA_na_pole_kontraktu`.

import { useId, useRef, useState } from "react";
import { dataJestCzytelna, odczytajKwote } from "@/lib/kwota";
import { NAPISY_CELU, NAPISY_PANELU } from "@/lib/napisy";
import type { DaneBudzetu } from "@/lib/kontrakt";
import { dodajCel } from "@/lib/dane/budzet";
import { BladWarstwySieciowej } from "@/lib/dane/warstwa-sieciowa";
import s from "./style.module.css";

function opisBledu(blad: unknown): string {
  if (blad instanceof BladWarstwySieciowej) return `${blad.czegoBrakuje} ${blad.coZrobic}`;
  return NAPISY_PANELU.awariaNieznana;
}

export function PanelCelu({
  DANE,
  dzis,
  poZapisie,
  zamknij,
}: {
  DANE: DaneBudzetu;
  dzis: string | null;
  poZapisie: (dane: DaneBudzetu) => void;
  zamknij: () => void;
}) {
  const idNazwy = useId();
  const idKategorii = useId();
  const idKwoty = useId();
  const idTerminu = useId();

  const [nazwa, setNazwa] = useState("");
  const [kategoria, setKategoria] = useState("");
  const [kwotaTekst, setKwotaTekst] = useState("");
  const [termin, setTermin] = useState("");

  const [bladNazwy, setBladNazwy] = useState<string | null>(null);
  const [bladKwoty, setBladKwoty] = useState<string | null>(null);
  const [bladTerminu, setBladTerminu] = useState<string | null>(null);
  const [bladWarstwy, setBladWarstwy] = useState<string | null>(null);

  const zamek = useRef(false);
  const [wLocie, setWLocie] = useState(false);

  async function zapisz() {
    if (zamek.current) return;
    setBladNazwy(null);
    setBladKwoty(null);
    setBladTerminu(null);
    setBladWarstwy(null);

    const odczyt = odczytajKwote(kwotaTekst);
    let wolno = true;

    if (nazwa.trim() === "") {
      setBladNazwy(NAPISY_CELU.nazwaPusta);
      wolno = false;
    }
    if (odczyt.stan === "pusta") {
      setBladKwoty(NAPISY_PANELU.kwotaPusta);
      wolno = false;
    }
    if (odczyt.stan === "nieczytelna") {
      setBladKwoty(NAPISY_PANELU.kwotaNieczytelna);
      wolno = false;
    }
    if (odczyt.stan === "ujemna") {
      setBladKwoty(NAPISY_CELU.kwotaUjemna);
      wolno = false;
    }
    if (!dataJestCzytelna(termin)) {
      setBladTerminu(NAPISY_CELU.terminNieczytelny);
      wolno = false;
    }
    if (!wolno || odczyt.stan !== "ok") return;

    zamek.current = true;
    setWLocie(true);
    try {
      const odpowiedz = await dodajCel(
        { nazwa: nazwa.trim(), kategoria: kategoria.trim(), kwotaDocelowa: odczyt.kwota, termin },
        { miesiac: DANE.miesiac, dzis },
      );
      poZapisie(odpowiedz.dane);
      zamknij();
    } catch (blad: unknown) {
      setBladWarstwy(opisBledu(blad));
    } finally {
      zamek.current = false;
      setWLocie(false);
    }
  }

  function naKlawiszu(zdarzenie: React.KeyboardEvent) {
    if (zdarzenie.key === "Enter") void zapisz();
    if (zdarzenie.key === "Escape") zamknij();
  }

  return (
    <div className={s.panel} role="group" aria-label={NAPISY_CELU.tytul}>
      <span className={s.etykietaSekcji}>{NAPISY_CELU.tytul}</span>

      <div className={s.wierszPol}>
        <div className={`${s.kolumnaPola} ${s.kolumnaKategorii}`}>
          <label className={s.etykietaKolumny} htmlFor={idNazwy}>{NAPISY_CELU.etykietaNazwy}</label>
          <span className={bladNazwy ? `${s.ramkaPola} ${s.uwaga}` : s.ramkaPola}>
            <input
              id={idNazwy}
              className={s.wpisTekstu}
              autoFocus
              value={nazwa}
              onChange={(e) => setNazwa(e.target.value)}
              onKeyDown={naKlawiszu}
            />
          </span>
          {bladNazwy && <span className={s.podpisUwagi} role="alert">{bladNazwy}</span>}
        </div>

        <div className={`${s.kolumnaPola} ${s.kolumnaKategorii}`}>
          <label className={s.etykietaKolumny} htmlFor={idKategorii}>
            {NAPISY_CELU.etykietaKategorii}
          </label>
          <span className={s.ramkaPola}>
            <input
              id={idKategorii}
              className={s.wpisTekstu}
              value={kategoria}
              onChange={(e) => setKategoria(e.target.value)}
              onKeyDown={naKlawiszu}
            />
          </span>
          <span className={s.podpis}>{NAPISY_CELU.kategoriaOszczednosci}</span>
        </div>

        <div className={`${s.kolumnaPola} ${s.kolumnaKwoty}`}>
          <label className={s.etykietaKolumny} htmlFor={idKwoty}>{NAPISY_CELU.etykietaKwoty}</label>
          <span className={bladKwoty ? `${s.ramkaPola} ${s.uwaga}` : s.ramkaPola}>
            <input
              id={idKwoty}
              className={s.wpisKwoty}
              inputMode="decimal"
              value={kwotaTekst}
              onChange={(e) => setKwotaTekst(e.target.value)}
              onKeyDown={naKlawiszu}
            />
            <span className={s.jednostka}>zł</span>
          </span>
          {bladKwoty && <span className={s.podpisUwagi} role="alert">{bladKwoty}</span>}
        </div>

        <div className={`${s.kolumnaPola} ${s.kolumnaKategorii}`}>
          <label className={s.etykietaKolumny} htmlFor={idTerminu}>
            {NAPISY_CELU.etykietaTerminu}
          </label>
          <input
            id={idTerminu}
            type="date"
            className={`${s.kafelekTypu} ${s.przycisk}`}
            value={termin}
            onChange={(e) => setTermin(e.target.value)}
            onKeyDown={naKlawiszu}
          />
          {/* DATA POWTORZONA PO POLSKU — pole `type="date"` rysuje sobie
              przegladarka WEDLUG USTAWIEN SYSTEMU. Zmierzone 2026-08-29 na tym
              laptopie: 2 wrzesnia 2026 pokazalo sie jako „09/02/2026", czyli
              w zapisie, ktory po polsku czyta sie jako 9 LUTEGO. Pomylka
              o siedem miesiecy w terminie celu nie zostawia po sobie sladu. */}
          {dataJestCzytelna(termin) && (
            <span className={s.podpis}>{NAPISY_CELU.terminSlownie(termin)}</span>
          )}
          {bladTerminu && <span className={s.podpisUwagi} role="alert">{bladTerminu}</span>}
        </div>

        <div className={s.kolumnaZapisu}>
          <button
            type="button"
            className={s.wezwaniePanelu}
            onClick={() => void zapisz()}
            disabled={wLocie}
            aria-busy={wLocie}
          >
            {NAPISY_CELU.zapisz}
          </button>
          <button type="button" className={s.rezygnuje} onClick={zamknij}>
            {NAPISY_PANELU.rezygnuje}
          </button>
        </div>
      </div>

      <p className={s.tozsamosc}>{NAPISY_CELU.progRecznie}</p>

      {bladWarstwy && <span className={s.podpisUwagi} role="alert">{bladWarstwy}</span>}
    </div>
  );
}

"use client";

// EKRAN BUDZET — odpowiada na pytanie „co zaplanowalem i jak plan sie trzyma".
//
// PO CO JEST NAJWAZNIEJSZY Z EKRANOW DRUGIEGO RZUTU. Bez planu wydatkow
// prognoza Plynnosci pokazuje PUSTA PRZYSZLOSC i wyglada znacznie lepiej, niz
// jest: po wpisaniu samego stanu konta aplikacja mowi „nie schodzisz ponizej
// zera" — i to jest prawda o danych, ktore ma, a nie o pieniadzach Darka.
// Ten ekran zamienia tamta wypowiedz w uczciwa.
//
// ROZDZIAL NA DWA PLIKI — wzorzec wolany z `app/ksiegowanie/page.tsx`, nie
// powtarzany: dane wejsciowe sa z natury serwerowe (`GET /api/budzet` ma stac
// w PIERWSZYM rysowaniu, inaczej pierwsze spojrzenie pada na pustke, ktorej
// §3.7 zabrania), a uklad jest z natury kliencki, bo kazdy z czterech zapisow
// oddaje CALY nowy ekran i `DANE` musza byc stanem.
//
// ZERO KWOT W TYM PLIKU. Kazda liczba przychodzi z `lib/dane/budzet.ts`
// i jest formatowana przez `lib/kwota.ts`. Zero rachunku: ani jednego
// dodawania, ani jednego procentu — wszystkie policzyl silnik, bo kazda z tych
// liczb jest wynikiem reguly budzetu, a regula ma miec jeden nosnik.
// Pilnuje tego straznik `testy/test_ekran_budzet.py`.
//
// CZEGO TU NIE MA I NIE WOLNO DOLOZYC:
//  * DRUGIEGO SELEKTORA („Wybrany miesiąc" z ramki). Fraza ma nosnik wylacznie
//    w opisie Raportow — element bez opisanej funkcji niczego nie obiecuje
//    (rozstrzygniecie Mili, spis §7).
//  * KONTROLKI „Popraw zaznaczony". Ramka ja rysuje, ale w calym spisie 36
//    tras (`api/trasy.py`) NIE MA trasy zmiany wpisu — jest wylacznie
//    `DELETE /api/wpisy/{id}`. Odsylacz, ktory nic nie robi, jest gorszy niz
//    jego brak. Odstepstwo zgloszone; straznik z progiem stoi w
//    `test_ekran_budzet.py::test_popraw_zaznaczony_CZEKA_na_trase_zmiany_wpisu`.
//  * ZADNEJ TRASY KASUJACEJ PLAN. Kosz przy pozycji planu KONCZY REGULE
//    od wskazanego miesiaca w przod (Z-9) — patrz `panel-planu.tsx`.

import { useState } from "react";
import { Powloka } from "../powloka";
import { PanelPlanu, type TrybPanelu } from "./panel-planu";
import { PanelCelu } from "./panel-celu";
import { NAPISY_BUDZETU } from "@/lib/napisy";
import { PROZA } from "@/lib/napisy";
import {
  dzienWMiesiacu,
  kwotaJestZerem,
  sformatujDzien,
  sformatujKwote,
  sformatujOdczyt,
  znakKwoty,
} from "@/lib/kwota";
import { NAPIS_TYPU, type DaneBudzetu, type PozycjaWykonania } from "@/lib/kontrakt";
import { kopiujPlan, wycofajWpisZBudzetu } from "@/lib/dane/budzet";
import s from "./style.module.css";

function IkonaPlus() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 3.5v9M3.5 8h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
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

// PASEK POSTEPU. `procentPaska === null` znaczy „planu nie ma", wiec paska tez
// nie ma — pusty pasek czytalby sie jako „nic nie wydales z planu, ktory jest".
function Pasek({ procent, przekroczone }: { procent: number | null; przekroczone: boolean }) {
  if (procent === null) return <span />;
  return (
    <span className={s.pasek}>
      <span className={s.paskoTlo} />
      <span
        className={przekroczone ? `${s.paskoWypelnienie} ${s.paskoPrzekroczone}` : s.paskoWypelnienie}
        style={{ width: `${procent}%` }}
      />
    </span>
  );
}

export function Ekran({
  poczatkowe,
  dzis,
}: {
  poczatkowe: DaneBudzetu;
  dzis: string | null;
}) {
  const [DANE, setDane] = useState<DaneBudzetu>(poczatkowe);
  const [panel, setPanel] = useState<TrybPanelu | null>(null);
  const [panelCelu, setPanelCelu] = useState(false);
  const [zaznaczony, setZaznaczony] = useState<number | null>(null);
  const [wLocie, setWLocie] = useState(false);

  // Dzien miesiaca to LICZNIK, nie kwota — nie ma tu groszy do zgubienia.
  const dzienMiesiaca = Number(DANE.dzisiaj.split("-")[2]);

  const czekajace = DANE.pozycjePlanu.filter((p) => p.czeka);
  const wydatki = DANE.pozycjeWykonania.filter((w) => w.typ === "Wydatki");
  const pozostale = DANE.pozycjeWykonania.filter((w) => w.typ !== "Wydatki");
  const bilansUjemny = znakKwoty(DANE.bilansPlanu) === "ujemna";

  /** Otwarcie panelu w trybie zmiany — wylacznie gdy wiersz wskazuje JEDNA
   *  pozycje planu. `idPozycjiPlanu === null` znaczy „zero albo wiecej niz
   *  jedna", a te dwa przypadki rozroznia `liczbaPozycjiPlanu`. */
  function otworzZmiane(wiersz: PozycjaWykonania) {
    if (wiersz.idPozycjiPlanu === null) return;
    const pozycja = DANE.pozycjePlanu.find((p) => p.id === wiersz.idPozycjiPlanu);
    if (pozycja) setPanel({ rodzaj: "zmiana", pozycja });
  }

  async function skopiuj() {
    if (wLocie) return;
    setWLocie(true);
    try {
      const odpowiedz = await kopiujPlan({ miesiac: DANE.miesiac, dzis });
      setDane(odpowiedz.dane);
    } finally {
      setWLocie(false);
    }
  }

  async function wycofaj() {
    if (zaznaczony === null || wLocie) return;
    setWLocie(true);
    try {
      setDane(await wycofajWpisZBudzetu(zaznaczony, dzis));
      setZaznaczony(null);
    } finally {
      setWLocie(false);
    }
  }

  return (
    <Powloka
      aktywny="budzet"
      odczyt={sformatujOdczyt(DANE.dzisiaj)}
      straznik={DANE.ostatnieSprawdzenie}
      pion="srodek"
      odstepStopki={28}
    >
      <section className={s.ekran}>

        {/* ---- kafelki planu i bilans ---- */}
        <div className={s.blok}>
          <div className={s.naglowekKarty}>
            <span className={s.etykietaSekcji}>{NAPISY_BUDZETU.tytul}</span>
            <span className={s.podpis}>
              {NAPISY_BUDZETU.licznikNaglowka(DANE.liczbaPozycjiPlanu, DANE.liczbaWpisow)}
            </span>
            <span className={s.rozpychacz} />
            {/* Na ramce to SPAN, nie odsylacz — okresu nie da sie tu zmienic
                i tak zostaje, dopoki ktos nie opisze, co robi klik. */}
            <span className={s.selektorOkresu}>
              <span>{DANE.miesiacNapis}</span>
              <Daszek />
            </span>
          </div>

          {/* KAFELKI BIERZE SIE PO KLUCZU, a nie po indeksie — kolejnosc
              tablicy jest wlasnoscia silnika, nie umowa z widokiem. */}
          <div className={s.naglowkiKafelkow}>
            {DANE.kafelki.map((k) => (
              <span key={k.klucz} className={s.etykietaKolumny}>{k.tytul}</span>
            ))}
          </div>
          <div className={s.kwotyKafelkow}>
            {DANE.kafelki.map((k) =>
              // `kwota: null` znaczy NIE POLICZYLEM, a nie zero. Zero pod
              // tytulem „Rezerwa na podatki" czytaloby sie jako „nic nie
              // jestes winien urzedowi" — najlepsza mozliwa odpowiedz podana
              // wtedy, gdy nie ma zadnej. W miejscu liczby staje zdanie
              // silnika o tym, czego mu brakuje.
              k.kwota === null ? (
                <span key={k.klucz} className={s.odmowaKafelka}>{k.wyjasnienie}</span>
              ) : (
                <span key={k.klucz} className={s.kwotaKafelka}>
                  {sformatujKwote(k.kwota, "neutralna")}
                </span>
              ),
            )}
          </div>
          <div className={s.dopiskiKafelkow}>
            {DANE.kafelki.map((k) => (
              // Zastrzezenie silnika stoi PRZY LICZBIE, ktorej dotyczy (§3.5).
              // Pojawia sie, gdy kwota JEST, ale silnik ma do niej uwage —
              // inaczej niz odmowa wyzej, ktora liczbe zastepuje.
              <span key={k.klucz} className={s.dopisekKafelka}>
                {k.kwota !== null && k.wyjasnienie
                  ? `${k.dopisek} — ${k.wyjasnienie}`
                  : k.dopisek}
              </span>
            ))}
          </div>

          <div className={s.kreska} />
          <div className={s.przerwa} />
          <div className={s.kreska} />

          <p className={s.zdanieRezerwy}>{NAPISY_BUDZETU.rezerwaZdanie}</p>

          <div className={s.liniaBilansu} />
          <div className={s.wierszBilansu}>
            <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.bilansEtykieta}</span>
            <span
              className={
                bilansUjemny ? `${s.liczbaBilansu} ${s.bilansPonizejZera}` : s.liczbaBilansu
              }
            >
              {sformatujKwote(DANE.bilansPlanu, znakKwoty(DANE.bilansPlanu))}
            </span>
            <span className={s.podpisBilansu}>{NAPISY_BUDZETU.bilansPodpis}</span>
          </div>
          <p className={s.prozaBilansu}>
            {NAPISY_BUDZETU.bilansProza(
              sformatujKwote(DANE.planPrzychodow, "neutralna"),
              sformatujKwote(DANE.planWydatkow, "neutralna"),
              kwotaJestZerem(DANE.planOszczednosci)
                ? null
                : sformatujKwote(DANE.planOszczednosci, "neutralna"),
            )}
            {bilansUjemny && NAPISY_BUDZETU.bilansUjemny}
            {NAPISY_BUDZETU.bilansRezerwa}
          </p>
        </div>

        {/* ---- narracja: ile z planu poszlo i co jeszcze czeka ---- */}
        <div className={s.narracja}>
          {/* MIESIAC BEZ PLANU MA WLASNE ZDANIE. „Z planu 0,00 zl nie wydales
              jeszcze nic" podaje ZERO JAKO WYNIK tam, gdzie planu nie ma
              wcale — a PRD §12.8 zabrania tego wprost. Wykryte OBEJRZENIEM
              ekranu na sierpniu 2026, nie testem. */}
          <p className={s.zdanieGlowne}>
            {DANE.pozycjePlanu.length === 0
              ? NAPISY_BUDZETU.bezPlanu(DANE.miesiacNapis)
              : kwotaJestZerem(DANE.wykonaneWydatki)
                ? NAPISY_BUDZETU.zPlanuNic(
                    sformatujKwote(DANE.planWydatkow, "neutralna"),
                    dzienMiesiaca,
                  )
                : NAPISY_BUDZETU.zPlanuWydane(
                    sformatujKwote(DANE.planWydatkow, "neutralna"),
                    sformatujKwote(DANE.wykonaneWydatki, "neutralna"),
                    dzienMiesiaca,
                  )}
          </p>
          <p className={s.zdaniePoboczne}>
            {czekajace.length > 0 && (
              <>
                {NAPISY_BUDZETU.czekajaNaDni(czekajace.length)}
                {czekajace.map((p, i) => (
                  <span key={p.id}>
                    {i > 0 ? ", " : ""}
                    {p.kategoria}
                    {p.opis ? ` ${p.opis}` : ""} {sformatujKwote(p.kwota, "neutralna")}
                    {p.dzien === null ? "" : ` (${dzienWMiesiacu(p.dzien, DANE.miesiac)})`}
                  </span>
                ))}
                {". "}
              </>
            )}
            {NAPISY_BUDZETU.firmowe}
          </p>
        </div>

        {/* ---- plan kontra wykonanie ---- */}
        <div className={s.blok}>
          <div className={s.naglowekBloku}>
            <span className={s.etykietaSekcji}>{NAPISY_BUDZETU.planKontraWykonanie}</span>
            <span className={s.podpis}>{NAPISY_BUDZETU.podpisOdchylenia}</span>
            <span className={s.rozpychacz} />
            <button
              type="button"
              className={s.przycisk}
              onClick={() => setPanel({ rodzaj: "dodanie" })}
            >
              <IkonaPlus />
              <span>{NAPISY_BUDZETU.dodajPozycje}</span>
            </button>
            <button
              type="button"
              className={s.przycisk}
              onClick={() => void skopiuj()}
              disabled={wLocie}
              aria-busy={wLocie}
            >
              {DANE.napisKopiujZ}
            </button>
          </div>

          {/* PANEL ZAMKNIETY NIE WCHODZI DO DRZEWA — zmierzone w W8: kontrolka
              dolozona do ukladu w spoczynku zepchnela ekran o 80 px w dol
              i odwzorowanie skoczylo z 0,07% na 14,38% przy progu 2%. */}
          {panel !== null && (
            <PanelPlanu
              tryb={panel}
              DANE={DANE}
              dzis={dzis}
              poZapisie={setDane}
              zamknij={() => setPanel(null)}
            />
          )}

          <div className={s.naglowkiKolumn}>
            <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaKategoria}</span>
            <span className={`${s.etykietaKolumny} ${s.doPrawej}`}>{NAPISY_BUDZETU.kolumnaPlan}</span>
            <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaPostep}</span>
            <span className={`${s.etykietaKolumny} ${s.doPrawej}`}>{NAPISY_BUDZETU.kolumnaWykonanie}</span>
            <span className={`${s.etykietaKolumny} ${s.doPrawej}`}>{NAPISY_BUDZETU.kolumnaOdchylenie}</span>
          </div>

          <div className={s.grupa}>
            <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.grupaWydatki}</span>
          </div>
          {wydatki.length === 0 ? (
            <p className={s.stanPusty}>{NAPISY_BUDZETU.bezWydatkow(DANE.miesiacNapis)}</p>
          ) : (
            wydatki.map((w) => (
              <WierszWykonania key={`${w.typ}-${w.kategoria}`} wiersz={w} otworz={otworzZmiane} />
            ))
          )}

          <div className={s.grupa}>
            <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.grupaPrzychodyIOszczednosci}</span>
          </div>
          {pozostale.length === 0 ? (
            // WZORZEC POPRAWNEGO STANU PUSTEGO na tej ramce: akapit pelnej
            // szerokosci, POZA siatka kolumn.
            <p className={s.stanPusty}>
              {NAPISY_BUDZETU.bezPrzychodow(DANE.miesiacNapis)}
              {/* Ogon TYLKO przy ujemnym bilansie — inaczej zdanie twierdzi
                  o liczbie stojacej wyzej cos, czego ta liczba nie mowi. */}
              {bilansUjemny && NAPISY_BUDZETU.bezPrzychodowOgon}
            </p>
          ) : (
            pozostale.map((w) => (
              <WierszWykonania key={`${w.typ}-${w.kategoria}`} wiersz={w} otworz={otworzZmiane} />
            ))
          )}
        </div>

        {/* ---- cele oszczednosciowe ---- */}
        <div className={s.blok}>
          <div className={s.naglowekBloku}>
            <span className={s.etykietaSekcji}>{NAPISY_BUDZETU.cele}</span>
            <span className={s.podpis}>{NAPISY_BUDZETU.podpisCelow}</span>
            <span className={s.rozpychacz} />
            <button
              type="button"
              className={s.przycisk}
              onClick={() => setPanelCelu(true)}
            >
              <IkonaPlus />
              <span>{NAPISY_BUDZETU.dodajCel}</span>
            </button>
          </div>

          {panelCelu && (
            <PanelCelu
              DANE={DANE}
              dzis={dzis}
              poZapisie={setDane}
              zamknij={() => setPanelCelu(false)}
            />
          )}

          {DANE.cele.length === 0 ? (
            <p className={s.stanPusty}>{NAPISY_BUDZETU.bezCelow}</p>
          ) : (
            DANE.cele.map((c) => (
              <div key={c.id} className={s.wierszCelu}>
                <span className={s.komorkaNazwy}>{c.nazwa}</span>
                <span className={s.komorkaKwoty}>{sformatujKwote(c.kwotaDocelowa, "neutralna")}</span>
                <Pasek procent={c.procentPaska} przekroczone={false} />
                <span className={s.komorkaKwoty}>{sformatujKwote(c.uzbierane, "neutralna")}</span>
                {/* `null` = nie ma czego dogadniac (cel osiagniety albo po
                    terminie). „0,00 zl / mc" bylo by odpowiedzia na pytanie,
                    ktorego nikt nie zadal. */}
                <span className={s.tempoCelu}>{c.tempoNapis ?? ""}</span>
              </div>
            ))
          )}
        </div>

        {/* ---- historia miesiaca ---- */}
        <div className={s.blok}>
          <div className={s.naglowekBloku}>
            <span className={s.etykietaSekcji}>{NAPISY_BUDZETU.historia}</span>
            <span className={s.podpis}>{NAPISY_BUDZETU.podpisHistorii}</span>
            <span className={s.rozpychacz} />
            <button
              type="button"
              className={s.linkCichy}
              onClick={() => void wycofaj()}
              disabled={zaznaczony === null || wLocie}
            >
              {NAPISY_BUDZETU.usunZaznaczone}
            </button>
          </div>

          {DANE.historia.length === 0 ? (
            // ODSTEPSTWO OD RAMKI, NAZWANE. Ramka wsadza oba akapity do siatki
            // pieciu kolumn i zdanie lamie sie w kolumnie 110 px — pionowy
            // slupek liter. Ta sama ramka robi to poprawnie w sekcji
            // „Przychody i oszczednosci" i wg tamtego wzorca budujemy tutaj
            // (spis Mili §6). Drugie zdanie WOLA istniejacy nosnik
            // `PROZA.pustaHistoriaHoryzont` — fakt o 204 wpisach sprzed
            // wznowienia dzialalnosci ma w tym projekcie jedno miejsce.
            <div className={s.stanPustyHistorii}>
              <p className={s.pustyTytul}>{NAPISY_BUDZETU.pustaHistoria(DANE.nazwaMiesiaca)}</p>
              <p className={s.pustyPowod}>
                {PROZA.pustaHistoriaHoryzont.map((czlon, i) => (
                  <span key={i} className={czlon.akcent ? s.akcent : undefined}>
                    {czlon.tekst}
                  </span>
                ))}
              </p>
            </div>
          ) : (
            <>
              <div className={s.naglowkiHistorii}>
                <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaData}</span>
                <span className={`${s.etykietaKolumny} ${s.doPrawej}`}>{NAPISY_BUDZETU.kolumnaKwota}</span>
                <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaOpis}</span>
                <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaKategoria}</span>
                <span className={s.etykietaKolumny}>{NAPISY_BUDZETU.kolumnaTyp}</span>
              </div>
              {DANE.historia.map((w) => (
                <button
                  key={w.id}
                  type="button"
                  aria-pressed={zaznaczony === w.id}
                  className={
                    zaznaczony === w.id
                      ? `${s.wierszHistorii} ${s.wierszZaznaczony}`
                      : s.wierszHistorii
                  }
                  onClick={() => setZaznaczony(zaznaczony === w.id ? null : w.id)}
                >
                  <span className={s.komorkaDnia}>{sformatujDzien(w.data)}</span>
                  <span className={s.komorkaKwoty}>{sformatujKwote(w.kwota, "neutralna")}</span>
                  <span className={s.komorkaOpisu}>{w.szczegoly}</span>
                  <span className={s.komorkaOpisu}>{w.kategoria}</span>
                  <span className={s.komorkaDnia}>{NAPIS_TYPU[w.typ]}</span>
                </button>
              ))}
            </>
          )}
        </div>

      </section>
    </Powloka>
  );
}

/** Wiersz tabeli „Plan kontra wykonanie". Nazwa kategorii jest kontrolka
 *  WYLACZNIE wtedy, gdy za wierszem stoi DOKLADNIE jedna pozycja planu —
 *  inaczej „popraw te pozycje" nie ma jednej odpowiedzi. */
function WierszWykonania({
  wiersz,
  otworz,
}: {
  wiersz: PozycjaWykonania;
  otworz: (w: PozycjaWykonania) => void;
}) {
  return (
    <div className={s.wierszTabeli}>
      {wiersz.idPozycjiPlanu === null ? (
        <span className={s.komorkaNazwy}>{wiersz.kategoria}</span>
      ) : (
        <button
          type="button"
          className={s.nazwaJakoLink}
          onClick={() => otworz(wiersz)}
          aria-label={`Zmień pozycję planu: ${wiersz.kategoria}`}
        >
          {wiersz.kategoria}
        </button>
      )}
      <span className={s.komorkaKwoty}>{sformatujKwote(wiersz.plan, "neutralna")}</span>
      <Pasek procent={wiersz.procentPaska} przekroczone={wiersz.przekroczone} />
      <span className={s.komorkaKwoty}>{sformatujKwote(wiersz.wykonane, "neutralna")}</span>
      <span className={`${s.komorkaKwoty} ${s.komorkaOdchylenia}`}>
        {sformatujKwote(wiersz.odchylenie, znakKwoty(wiersz.odchylenie))}
      </span>
    </div>
  );
}

// EKRAN PLYNNOSC — pierwszy, ktory Darek otwiera. Odpowiada na pytanie
// „czy dam rade do konca okresu".
//
// KRYTERIUM ODBIORU JEST JEDNO: jesli w pierwszej sekundzie nie widac,
// czy jest dobrze czy zle, ekran zawiodl — niezaleznie od poprawnosci
// liczb nizej. Stad JEDNA wielka liczba (56 px wobec 20 px zdania,
// czyli 2,80x przy progu hierarchii 1,5x) i jedna wyrozniona kontrolka.
//
// CZEGO TU NIE MA I NIE WOLNO DOLOZYC: kafelkow przychody/wydatki/
// oszczednosci, celow, majatku, ikony przy werdykcie (werdykt niosa juz
// slowo, barwa i pozycja — ikona bylaby trzecim nosnikiem tej samej rzeczy)
// oraz zdania „Prognoza ich NIE dolicza", ktore MOWI NIEPRAWDE: prognoza
// te raty odejmuje, tyle ze druga droga, jako pozycje planu.
//
// ZERO KWOT W TYM PLIKU. Kazda liczba przychodzi z `lib/dane/plynnosc.ts`
// i jest formatowana przez `lib/kwota.ts`; wspolrzedne rysunku liczy
// `lib/wykres.ts`. Pilnuje tego straznik `testy/test_ekran_plynnosc.py`.

import { Powloka } from "./powloka";
import { NAPISY_PLYNNOSCI } from "@/lib/napisy";
import { sformatujDzien, sformatujDzienSlownie, sformatujKwote, znakKwoty } from "@/lib/kwota";
import { DANE } from "@/lib/dane/plynnosc";
import { ODCZYT_NAGLOWKA } from "@/lib/dane/powloka";
import {
  SZEROKOSC,
  WYSOKOSC,
  liniaZera,
  odcinekPodKreska,
  pierwszyPunktPodKreska,
  punkty,
  sciezka,
} from "@/lib/wykres";
import s from "./style.module.css";

function Strzalka() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3 8h9M8.5 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Prognoza rysowana KRESKA PRZERYWANA. Linia ciagla twierdzilaby wiedze;
// to jest przewidywanie. Roznica niesie sie bez barwy, a jezyk zostaje
// zarezerwowany: gdy narosnie historia, przeszlosc bedzie ciagla.
function Wykres() {
  const pkt = punkty(DANE.wykres);
  const zero = liniaZera(DANE.wykres);
  const pod = odcinekPodKreska(pkt);
  const znacznik = pierwszyPunktPodKreska(pkt);
  const opis =
    `Prognoza od ${sformatujDzienSlownie(DANE.wykres[0].dzien)} do ` +
    `${sformatujDzienSlownie(DANE.koniecOknaCoMnieCzeka)}; kreską przerywaną, bo to ` +
    (DANE.dzienPodKreska
      ? `przewidywanie; od ${sformatujDzienSlownie(DANE.dzienPodKreska)} biegnie pod kreską zera.`
      : "przewidywanie; nie schodzi pod kreskę zera.");

  return (
    <svg width={SZEROKOSC} height={WYSOKOSC} viewBox={`0 0 ${SZEROKOSC} ${WYSOKOSC}`} role="img" aria-label={opis}>
      {/* Linia zera jest ODCIETA od liniatury rubryki: ta niesie znaczenie,
          tamta jest dekoracja. Gdyby wygladaly tak samo, oko wrzucilo by
          niosaca do klasy ozdobnych — a klasyfikuje z wygladu, zanim
          przeczyta. */}
      {zero !== null && (
        <line x1="0" y1={zero.toFixed(1)} x2={SZEROKOSC} y2={zero.toFixed(1)} stroke="var(--atrament-cichy)" strokeWidth="1" />
      )}
      <path d={sciezka(pkt)} fill="none" stroke="var(--atrament)" strokeWidth="1.6" strokeDasharray="6 4" />
      {pod && (
        <path d={pod} fill="none" stroke="var(--saldo-ujemne)" strokeWidth="3" strokeDasharray="6 4" />
      )}
      {znacznik && (
        <circle cx={znacznik.x.toFixed(1)} cy={znacznik.y.toFixed(1)} r="4.5" fill="var(--saldo-ujemne)" />
      )}
    </svg>
  );
}

export default function Plynnosc() {
  const ksiega = DANE.ksiega;
  const tenSamDzien = (a: number, b: number) =>
    a >= 0 && b < ksiega.length && ksiega[a]?.dzien === ksiega[b]?.dzien;

  const saldoUjemne = znakKwoty(DANE.saldoMinimalne) === "ujemna";

  return (
    <Powloka
      aktywny="plynnosc"
      odczyt={ODCZYT_NAGLOWKA}
      straznik={DANE.ostatnieSprawdzenie}
      pion="srodek"
      odstepStopki={28}
    >
      <section className={s.ekran}>

        <div className={s.ksiega}>
          <div className={s.tytulBloku}>
            <span className={s.etykietaSekcji}>{NAPISY_PLYNNOSCI.tytul}</span>
            <span className={s.podpis}>{DANE.okresNapis}</span>
          </div>

          <div className={s.kafelWykresu}>
            <Wykres />
            <div className={s.osDat}>
              <span className={s.podpisOsi}>
                {NAPISY_PLYNNOSCI.osDzis(sformatujDzien(DANE.wykres[0].dzien))}
              </span>
              <span className={s.rozpychacz} />
              {DANE.dzienPodKreska && (
                <>
                  <span className={s.podpisOsiPodKreska}>
                    {NAPISY_PLYNNOSCI.osPodKreska(sformatujDzien(DANE.dzienPodKreska))}
                  </span>
                  <span className={s.rozpychacz} />
                </>
              )}
              <span className={s.podpisOsi}>
                {sformatujDzien(DANE.koniecOknaCoMnieCzeka)}
              </span>
            </div>
          </div>

          <div className={s.wierszKolumn}>
            <span className={s.naglowekKolumny}>{NAPISY_PLYNNOSCI.kolumnaDzien}</span>
            <span className={s.naglowekKolumny}>{NAPISY_PLYNNOSCI.kolumnaPozycja}</span>
            <span className={`${s.naglowekKolumny} ${s.doPrawej}`}>{NAPISY_PLYNNOSCI.kolumnaKwota}</span>
            <span className={`${s.naglowekKolumny} ${s.doPrawej}`}>{NAPISY_PLYNNOSCI.kolumnaSaldo}</span>
          </div>

          {ksiega.map((w, i) => {
            // Data pisze sie raz na dzien, a kreska rozdziela DNI, nie wiersze.
            const kontynuacja = tenSamDzien(i - 1, i);
            const przedDalszym = tenSamDzien(i, i + 1);
            const klasa = [
              s.wiersz,
              przedDalszym ? s.wierszPrzedDalszym : "",
              kontynuacja ? s.wierszDalszyZDnia : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={`${w.dzien}-${w.pozycja}`} className={klasa}>
                <span className={s.komorkaDnia}>{kontynuacja ? "" : sformatujDzien(w.dzien)}</span>
                <span className={s.komorkaPozycji}>
                  {w.pozycja}
                  {/* Odstep stoi PRZED znacznikiem, nie w srodku: wewnatrz mial by
                      13 px zamiast 15 px i dopisek przesuwal by sie o piksel w lewo. */}
                  {w.dopisek && <>{" "}<span className={s.dopisek}>{w.dopisek}</span></>}
                </span>
                {w.kwota === null ? (
                  <span className={s.komorkaBezKwoty}>{NAPISY_PLYNNOSCI.brakKwoty}</span>
                ) : (
                  <span className={s.komorkaKwoty}>
                    {sformatujKwote(w.kwota, znakKwoty(w.kwota))}
                  </span>
                )}
                <span className={s.komorkaSalda}>
                  {w.saldoPoDniu === null ? "" : sformatujKwote(w.saldoPoDniu, "neutralna")}
                </span>
              </div>
            );
          })}

          <div className={s.wierszZamkniecia}>
            <span />
            <span className={s.etykietaZamkniecia}>
              {NAPISY_PLYNNOSCI.najnizej(sformatujDzienSlownie(DANE.dataSaldaMinimalnego))}
            </span>
            <span />
            <span
              className={`${s.liczbaZamkniecia} ${
                saldoUjemne ? s.zamknieciePonizejZera : s.zamknieciePowyzejZera
              }`}
            >
              {sformatujKwote(DANE.saldoMinimalne, znakKwoty(DANE.saldoMinimalne))}
            </span>
          </div>
          <div className={s.kreska} />
          <div className={s.przerwa} />
          <div className={s.kreska} />
        </div>

        <div className={s.werdykt}>
          <p className={s.zdanieWerdyktu}>{DANE.zdanieWerdyktu}</p>
          <p className={s.horyzont}>{NAPISY_PLYNNOSCI.horyzont(DANE.horyzontDni)}</p>
        </div>

        <div className={s.wierszWezwania}>
          <span className={s.rozpychacz} />
          <a className={`${s.wezwanie} ${s.przycisk}`} href="/co-mnie-czeka">
            <span>
              {NAPISY_PLYNNOSCI.coMnieCzeka(
                DANE.liczbaPozycjiCoMnieCzeka,
                sformatujDzienSlownie(DANE.koniecOknaCoMnieCzeka)
              )}
            </span>
            <Strzalka />
          </a>
        </div>

      </section>
    </Powloka>
  );
}

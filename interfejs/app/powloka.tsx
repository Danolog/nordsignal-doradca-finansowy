// POWLOKA WSPOLNA DLA WSZYSTKICH JEDENASTU EKRANOW — przeniesiona wezel po
// wezle z ramek `makiety/*.dc.html`. Ramka jest wiazaca specyfikacja wygladu
// (CLAUDE.md §3.6), wiec uklad naglowka i stopki nie jest tu wymyslony.
//
// STAN „TU JESTEM" niesie ALBO pozycja paska, ALBO kontrolka `Ksiegowanie` —
// nigdy obie i nigdy zadna. Gdyby zadna go nie niosla, naglowek na ekranie
// Ksiegowania klamalby przez przemilczenie (§41.3 specyfikacji).
//
// STOPKA NIE JEST OZDOBA. Odpowiada na pytanie „czy to, co widze, jest
// aktualne" i jest jedynym miejscem, w ktorym cichy straznik mowi, ze istnieje.

import { AKCJA, PASEK, ZNAK_SLOWNY } from "@/lib/ekrany";
import { NAPISY_POWLOKI } from "@/lib/napisy";

function IkonaPlus({ rozmiar = 16 }: { rozmiar?: number }) {
  return (
    <svg width={rozmiar} height={rozmiar} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 3.5v9M3.5 8h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function Powloka({
  aktywny,
  odczyt,
  straznik,
  children,
  pion = "gora",
  odstepStopki = 24,
}: {
  aktywny: string;
  odczyt: string;
  straznik: string | null;
  children: React.ReactNode;
  // Ramki roznia sie w dwoch miarach powloki i te roznice sa prawdziwe:
  // Ksiegowanie stawia tresc pod naglowkiem (`gora`), Plynnosc srodkuje ja
  // w pionie (`srodek`), a odstep stopki wynosi 24 px na jednym ekranie
  // i 28 px na drugim. Wartosci podaje EKRAN, bo to on ma swoja ramke.
  pion?: "gora" | "srodek";
  odstepStopki?: number;
}) {
  const wKsiegowaniu = aktywny === AKCJA.klucz;
  return (
    <div
      className="arkusz"
      style={
        {
          "--pion-tresci": pion === "srodek" ? "center" : "flex-start",
          "--odstep-stopki": `${odstepStopki}px`,
        } as React.CSSProperties
      }
    >
      <div className="naglowek">
        <div className="naglowek-wiersz">
          <span className="znak-slowny">{ZNAK_SLOWNY}</span>

          <a
            className={wKsiegowaniu ? "akcja akcja-czynna" : "akcja"}
            href={`/${AKCJA.klucz}`}
            aria-current={wKsiegowaniu ? "page" : undefined}
          >
            <IkonaPlus />
            <span>{AKCJA.napis}</span>
          </a>

          <nav className="pasek" aria-label="Obszary aplikacji">
            {PASEK.map((e) => (
              <a
                key={e.klucz}
                href={`/${e.klucz}`}
                title={e.pytanie}
                aria-current={aktywny === e.klucz ? "page" : undefined}
              >
                {e.napis}
              </a>
            ))}
          </nav>

          <span className="rozpychacz" />
          <span className="odczyt">{odczyt}</span>
        </div>

        <div className="kreska" />
        <div className="przerwa" />
        <div className="kreska" />
      </div>

      <main>{children}</main>

      <div className="stopka">
        <div className="stopka-tresc">
          <span className="straznik">{straznik ?? NAPISY_POWLOKI.straznikNieDzialal}</span>
          <span className="rozpychacz" />
        </div>
      </div>
    </div>
  );
}

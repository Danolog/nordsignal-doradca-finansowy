// POWLOKA WSPOLNA DLA WSZYSTKICH JEDENASTU EKRANOW.
//
// Co niesie kazdy ekran (PRD §10.1, odczytane z ramek — nie wymyslone):
//   znak slowny + akcja "Ksiegowanie" OBOK niego (nie w pasku, decyzja P-3),
//   pasek dziewieciu pozycji,
//   data i godzina odczytu,
//   stopka straznika: "Ostatnie sprawdzenie: ... — nic pilnego nie znalazl".
//
// STOPKA NIE JEST OZDOBA. Odpowiada na piate pytanie uzytkownika — "czy to,
// co widze, jest aktualne" — i jest jedynym miejscem, w ktorym cichy straznik
// mowi, ze w ogole istnieje (w v1 nie ma powiadomien, decyzja Darka).

import type { Metadata } from "next";
import { AKCJA, PASEK } from "@/lib/ekrany";
import "./paleta.css";
import "./powloka.css";

export const metadata: Metadata = {
  title: "Doradca Finansowy",
  description: "Czy mam pieniądze, co mnie zaraz uderzy, co mam z tym zrobić.",
};

export default function Powloka({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body>
        <header className="naglowek">
          <div className="znak">
            <span className="znak-slowny">Doradca Finansowy</span>
            <a className="akcja" href={`/${AKCJA.klucz}`}>
              {AKCJA.napis}
            </a>
          </div>
          <nav className="pasek" aria-label="Obszary aplikacji">
            {PASEK.map((e) => (
              <a key={e.klucz} href={`/${e.klucz}`} title={e.pytanie}>
                {e.napis}
              </a>
            ))}
          </nav>
        </header>

        <main>{children}</main>

        {/* SZKIELET: tresc stopki pochodzi z GET /api/straznik/ostatni.
            Do czasu podpiecia mowi, ze nie wie — nigdy nie udaje, ze
            straznik patrzyl (CLAUDE.md §3.7: awaria do stanu uzytecznego). */}
        <footer className="straznik">
          Ostatnie sprawdzenie: <strong>brak danych</strong> — strażnik nie jest
          jeszcze podpięty.
        </footer>
      </body>
    </html>
  );
}

// Korzen dokumentu. Naglowek, pasek i stopka mieszkaja w `app/powloka.tsx`
// jako komponent wolany przez KAZDY ekran — bo stan „tu jestem" zalezy od
// ekranu, a uklad nie moze go zgadywac z adresu w dwoch miejscach naraz.

import type { Metadata } from "next";
import "./paleta.css";
import "./powloka.css";

export const metadata: Metadata = {
  title: "Doradca Finansowy",
  description: "Czy mam pieniądze, co mnie zaraz uderzy, co mam z tym zrobić.",
};

export default function Korzen({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body>{children}</body>
    </html>
  );
}

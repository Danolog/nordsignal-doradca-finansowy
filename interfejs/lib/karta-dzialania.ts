// JEDEN NOSNIK TRESCI KARTY „CO MAM ZROBIC".
//
// Karta odpowiada na trzecie pytanie aplikacji — „co mam z tym zrobic" —
// i stoi na ekranie Plynnosci miedzy werdyktem a przyciskiem „Co mnie czeka"
// (D-54). Wyboru stanu NIE robi komponent: robi go ta funkcja, zeby stan
// „wszystko w porzadku" i stan startowy dalo sie sprawdzic testem, a nie
// tylko obejrzec na rysunku.
//
// KARTA NIE LICZY NICZEGO NOWEGO. Bierze `saldoMinimalne` — te sama liczbe,
// ktora stoi w wierszu zamkniecia — i czyta ja inaczej: ujemna mowi, ile
// brakuje, dodatnia mowi, ile mozna odlozyc. Drugiego rachunku tu nie ma
// i nie moze byc, bo bylby drugim nosnikiem tej samej liczby.

import type { Data, Kwota } from "./kontrakt";
import { sformatujDzienSlownie, sformatujKwote, znakKwoty } from "./kwota";
import { NAPISY_KARTY } from "./napisy";

export type StanKarty =
  | { stan: "deficyt"; zdanie: string; koszt: string }
  | { stan: "nadwyzka"; zdanie: string; koszt: string }
  | { stan: "brak-danych"; zdanie: string };

export interface WejscieKarty {
  saldoMinimalne: Kwota | null;
  dataSaldaMinimalnego: Data | null;
}

export function ulozKarte(wejscie: WejscieKarty): StanKarty {
  const { saldoMinimalne, dataSaldaMinimalnego } = wejscie;

  // Brak KTOREJKOLWIEK z dwoch danych znaczy „nie wiem". Sprawdzamy obie,
  // bo kwota bez daty nie da sie opisac zdaniem, a data bez kwoty nie niesie
  // dzialania — a karta ma wtedy powiedziec, czego brakuje, nie zgadywac.
  if (saldoMinimalne === null || dataSaldaMinimalnego === null) {
    return { stan: "brak-danych", zdanie: NAPISY_KARTY.brakDanych };
  }

  // Znak czytamy tym samym nosnikiem, co reszta interfejsu. Kwota w zdaniu
  // stoi BEZ znaku: „brakuje 210,67 zl" — minus niesie juz slowo „brakuje".
  const kwota = sformatujKwote(saldoMinimalne, "neutralna");
  const dzien = sformatujDzienSlownie(dataSaldaMinimalnego);

  if (znakKwoty(saldoMinimalne) === "ujemna") {
    return {
      stan: "deficyt",
      zdanie: NAPISY_KARTY.deficytZdanie(kwota, dzien),
      koszt: NAPISY_KARTY.deficytKoszt(dzien),
    };
  }

  return {
    stan: "nadwyzka",
    zdanie: NAPISY_KARTY.nadwyzkaZdanie(kwota),
    koszt: NAPISY_KARTY.nadwyzkaKoszt,
  };
}

// AWARIA DO STANU UZYTECZNEGO, NIE DO ZERA (CLAUDE.md §3.7).
//
// Gdy silnik nie odpowiada albo odmawia liczenia, ekran MOWI, CZEGO BRAKUJE
// I CO Z TYM ZROBIC. Nie pokazuje pustki, nie pokazuje zera i nie pokazuje
// liczby z nieznanego zrodla. Pusty ekran i „0,00 zl" sa w aplikacji
// o pieniadzach tym samym: obiema drogami uzytkownik dowiaduje sie czegos
// nieprawdziwego o swoim koncie.
//
// POWLOKA ZOSTAJE. Ekran awarii bez naglowka i paska wyglada jak awaria
// przegladarki, a nie jak stan aplikacji — a uzytkownik ma z niego wyjsc
// na inny ekran jednym klikiem, nie przyciskiem „wstecz".
//
// ODCZYT W NAGLOWKU MOWI „NIE WIEM". Data odczytu przychodzi razem z danymi,
// wiec przy awarii jej nie ma. Wpisana tu na sztywno bylaby dokladnie tym,
// przed czym broni ten ekran.

import { Powloka } from "./powloka";
import { NAPISY_AWARII } from "@/lib/napisy";
import s from "./awaria.module.css";

export function Awaria({
  aktywny,
  czegoBrakuje,
  coZrobic,
}: {
  aktywny: string;
  czegoBrakuje: string;
  coZrobic: string;
}) {
  return (
    <Powloka aktywny={aktywny} odczyt={NAPISY_AWARII.odczytNieznany} straznik={null}>
      <section className={s.ekran} role="alert">
        <span className={s.etykieta}>{NAPISY_AWARII.tytul}</span>
        <p className={s.zdanie}>{czegoBrakuje}</p>
        <p className={s.instrukcja}>{coZrobic}</p>
      </section>
    </Powloka>
  );
}

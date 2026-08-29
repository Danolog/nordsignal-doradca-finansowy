// ADRES, POD KTORYM NIE MA EKRANU — STAN UZYTECZNY, NIE PUSTKA (§3.7).
//
// Do W7 kazdy taki adres oddawal surowa strone Next: „404: This page could
// not be found." — po angielsku, bez slowa o tym, co sie stalo i co z tym
// zrobic. Zmierzone 2026-08-29 na `/miesiac`: caly widoczny tekst strony to
// „Doradca Finansowy 404: This page could not be found. 404 This page could
// not be found." Osiem z dziewieciu pozycji paska prowadzilo dokladnie tam.
//
// POWLOKA ZOSTAJE — z tego samego powodu, co na ekranie awarii: strona bez
// naglowka i paska wyglada jak awaria przegladarki, a nie jak stan aplikacji,
// a uzytkownik ma z niej wyjsc jednym klikiem, nie przyciskiem „wstecz".
//
// WYGLAD WSPOLNY Z EKRANEM AWARII, TRESC WLASNA. Arkusz `awaria.module.css`
// jest tu WOLANY, nie kopiowany. To jest wyjatek nazwany z CLAUDE.md §3.2
// (Krug): regula ma miec jeden nosnik, WYGLAD nie musi byc unikalny — dwa
// stany „nie pokazuje liczb" maja prawo wygladac tak samo, bo czytaja sie
// tak samo.
//
// CZEGO TU NIE MA: `role="alert"`. Awaria silnika jest zdarzeniem, ktore
// wlasnie zaszlo; brak ekranu jest stanem, ktory trwa od poczatku. Krzyk
// czytnika ekranu na stan trwaly uczy go ignorowac.
//
// ODCZYT W NAGLOWKU MOWI „NIE WIEM" — nie bylo zadnego odczytu danych,
// wiec data odczytu wpisana tutaj bylaby liczba z nieznanego zrodla.

import { Powloka } from "./powloka";
import { NAPISY_AWARII } from "@/lib/napisy";
import s from "./awaria.module.css";

export function BezEkranu({
  aktywny,
  tytul,
  zdanie,
  instrukcja,
}: {
  aktywny: string;
  tytul: string;
  zdanie: string;
  instrukcja: string;
}) {
  return (
    <Powloka aktywny={aktywny} odczyt={NAPISY_AWARII.odczytNieznany} straznik={null}>
      <section className={s.ekran}>
        <span className={s.etykieta}>{tytul}</span>
        <p className={s.zdanie}>{zdanie}</p>
        <p className={s.instrukcja}>{instrukcja}</p>
      </section>
    </Powloka>
  );
}

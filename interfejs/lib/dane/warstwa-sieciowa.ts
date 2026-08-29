// JEDEN NOSNIK ADRESU SILNIKA I JEDEN NOSNIK ZACHOWANIA PRZY AWARII.
//
// Do Z7 pliki w `lib/dane/` niosly STALE przepisane z ramek. Od Z7 niosa
// WYWOLANIE TRASY — a ekran, ktory dostal te same typy, nie wie o zmianie.
// To byla cala teza podejscia „frontend najpierw": podpiecie ma byc PODMIANA
// ZRODLA, nie przepisaniem ekranu.
//
// DWA ADRESY, JEDNA ODPOWIEDZ NA PYTANIE „GDZIE STOI SILNIK".
// W przegladarce adres jest PUSTY, czyli wzgledny: `next.config.mjs` przekazuje
// `/api/*` na `http://127.0.0.1:8000`, wiec przegladarka widzi jeden adres
// i nie ma tu polityki pochodzenia (CORS) do obchodzenia. Po stronie serwera
// przekierowania nie ma — tam potrzebny jest adres pelny, i to jest jedyny
// powod, dla ktorego ta funkcja w ogole rozroznia obie strony.
//
// `cache: "no-store"` NIE JEST OSTROZNOSCIA, TYLKO WARUNKIEM BRAMKI Z7.
// Next.js buforuje `fetch` w komponentach serwerowych. Bramka tego zadania
// brzmi „prognoza po wpisie jest inna niz przed" — z wlaczonym buforem druga
// odpowiedz przychodzi z pamieci i liczba NIE RUSZA SIE nawet wtedy, gdy
// silnik policzyl inaczej. Bylaby to awaria, ktora melduje sukces: ekran
// wyglada poprawnie, a pokazuje stan sprzed wpisu.
//
// AWARIA DO STANU UZYTECZNEGO, NIE DO ZERA (CLAUDE.md §3.7). Kazda sciezka
// bledu konczy sie `BladWarstwySieciowej`, ktory niesie DWA zdania: czego
// brakuje i co z tym zrobic. Zwrocenie pustych danych albo zera byloby liczba
// z nieznanego zrodla — a to jest gorsze niz brak liczby, bo wyglada jak wynik.

/** Adres silnika po stronie serwera. Pusty napis = adres wzgledny (przegladarka). */
const ADRES_SERWEROWY = process.env.ADRES_SILNIKA ?? "http://127.0.0.1:8000";

function podstawa(): string {
  return typeof window === "undefined" ? ADRES_SERWEROWY : "";
}

/**
 * Awaria warstwy sieciowej opisana tak, zeby dalo sie z nia cos zrobic.
 *
 * `czegoBrakuje` mowi, co sie nie udalo; `coZrobic` mowi, jaki ruch to
 * odblokowuje. Rozdzielone, bo ekran pokazuje je w dwoch wagach — pierwsze
 * jako zdanie, drugie jako instrukcje pod nim.
 */
export class BladWarstwySieciowej extends Error {
  readonly czegoBrakuje: string;
  readonly coZrobic: string;

  constructor(czegoBrakuje: string, coZrobic: string) {
    super(`${czegoBrakuje} ${coZrobic}`);
    this.name = "BladWarstwySieciowej";
    this.czegoBrakuje = czegoBrakuje;
    this.coZrobic = coZrobic;
  }
}

/** Zdanie o braku polaczenia — jeden nosnik, wolany z dwoch miejsc nizej. */
const BRAK_POLACZENIA =
  "Nie mam połączenia z silnikiem — liczb nie ma skąd wziąć i żadnej nie zmyślam.";
const JAK_URUCHOMIC =
  "Uruchom warstwę sieciową: ./.venv/bin/python -m uvicorn api.index:aplikacja --port 8000 " +
  "w katalogu projektu, i odśwież stronę.";

type Opcje = {
  metoda?: "GET" | "POST" | "PUT" | "DELETE";
  tresc?: unknown;
  /** Dzien odniesienia. Trasa wystawia go DLA POMIARU ODBIORCZEGO — patrz
   *  `api/wspolne.py::dzien`. Pusty = silnik bierze dzien dzisiejszy. */
  dzis?: string | null;
};

export async function wywolaj<T>(sciezka: string, opcje: Opcje = {}): Promise<T> {
  const parametry = opcje.dzis ? `?dzis=${encodeURIComponent(opcje.dzis)}` : "";
  const adres = `${podstawa()}${sciezka}${parametry}`;

  let odpowiedz: Response;
  try {
    odpowiedz = await fetch(adres, {
      method: opcje.metoda ?? "GET",
      cache: "no-store",
      headers: opcje.tresc === undefined ? undefined : { "Content-Type": "application/json" },
      body: opcje.tresc === undefined ? undefined : JSON.stringify(opcje.tresc),
    });
  } catch {
    throw new BladWarstwySieciowej(BRAK_POLACZENIA, JAK_URUCHOMIC);
  }

  if (!odpowiedz.ok) {
    // ZDANIE SILNIKA ODDAJEMY W CALOSCI. `api/index.py` zamienia odmowe
    // liczenia na kod 400 z tym samym zdaniem, slowo w slowo — bo to silnik
    // wie, czego mu brakuje („Podaj stawke ryczaltu", „Nie ma wpisu o numerze
    // 7"). Skrocone do „Blad zadania" przestaje byc instrukcja.
    const zdanie = await odczytajOdmowe(odpowiedz);
    throw new BladWarstwySieciowej(
      zdanie ?? `Silnik odpowiedział kodem ${odpowiedz.status}, bez wyjaśnienia.`,
      zdanie
        ? "Uzupełnij to, o co prosi silnik, i spróbuj ponownie."
        : "Zgłoś to — odpowiedź bez zdania znaczy, że coś padło po naszej stronie.",
    );
  }

  try {
    return (await odpowiedz.json()) as T;
  } catch {
    throw new BladWarstwySieciowej(
      "Silnik odpowiedział czymś, co nie jest danymi.",
      "Zgłoś to — to jest wada po naszej stronie, nie brak w Twoich danych.",
    );
  }
}

async function odczytajOdmowe(odpowiedz: Response): Promise<string | null> {
  try {
    const tresc = (await odpowiedz.json()) as { detail?: unknown };
    return typeof tresc.detail === "string" ? tresc.detail : null;
  } catch {
    return null;
  }
}

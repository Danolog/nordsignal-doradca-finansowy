# Doradca Finansowy — plan sesji: chmura i pierwsze dane

> **Tryb wykonania jak w nocy 2026-08-29.** Oliver prowadzi, **nie wykonuje**. Każde zadanie dostaje
> **wyspecjalizowanego agenta we własnym oknie kontekstowym** (`../agents/*.md`). **Naraz pracuje
> dokładnie jeden** — Oliver powołuje po kolei i czeka na wynik. Do głównego okna wraca **wynik,
> nie przebieg**. Po każdym zadaniu: checkpoint wobec bramki, commit, gałąź `noc-2026-08-29`,
> autor `Darek <mubueu@gmail.com>`.

---

## Kontekst

Noc 2026-08-29 dała działającą pętlę: wpisujesz wydatek, prognoza się zmienia. 919 testów, dwa
ekrany odwzorowujące ramki co do piksela, sześć tras, silnik przeniesiony. Repozytorium stoi na
GitHubie (prywatne), projekt Vercel się buduje, baza Neon czeka pusta we Frankfurcie.

**Aplikacja jednak nie działa w chmurze i nie ma skąd wziąć Twoich danych.** Trzy rozpoznania
z 2026-08-29 (godz. 10:2x) pokazały dlaczego — i wszystkie trzy znaleziska są cięższe, niż
zakładał plan nocy:

1. **Nikt nie zmierzył, czy silnik zmieści się na Vercelu.** PRD nazywa to niewiadomą (§17 poz. 4,
   §18 poz. 3). Liczba jest konkretna: **pandas 72 MB + numpy 34 MB**. Cała architektura chmurowa
   stoi na niesprawdzonym założeniu.
2. **`silnik/baza/schemat.sql` nie jest gotowym celem migracji — jest szkicem z ubytkami.**
   Brakuje w nim **czterech kolumn `przychody_jdg`**, które kod aktywnie zapisuje i czyta
   (`stawka_ryczaltu`, `zaplacony_zus`, `zysk_netto`, `stawki_wersja`); brakuje **całej tabeli
   `rejestr_stawek`** (mieszka w `wiedza/rejestr.py`); a `data_obowiazku_vat NOT NULL` **zablokuje
   `zapisz_fakture`**, która tej kolumny nie wypełnia. Rozjazdów jest dziewięć i **nic ich nie
   pilnuje** — plik nie jest przez nikogo czytany.
3. **Dziewięć z dziewięciu odsyłaczy paska daje 404** — łącznie z Płynnością, bo pasek prowadzi na
   `/plynnosc`, a ekran stoi pod `/`. Brakujące strony pokazują surowy błąd Next, nie ekran
   `awaria.tsx` — **łamie §3.7**.

**Zamierzony wynik sesji:** aplikacja działa pod adresem w internecie, ma gdzie przyjąć stan konta
i plan, a pasek prowadzi tam, gdzie obiecuje.

---

## Decyzje wejściowe — rozstrzygnięte przez Darka, nie do ponownego otwierania

| Decyzja | Treść | Kiedy |
|---|---|---|
| **Pusty start** | Aplikacja startuje pusta od **1 IX 2026**. 204 wpisy i 46 pozycji planu **nie migrują**. Baza poprzednika zostaje **wyłącznie jako dane robocze do budowy** (`~/Dane-robocze-doradca-finansowy/`, prawa 600, poza repozytorium) | 08:44 i 09:19 |
| **Dane w chmurze** | Prawdziwe finanse **trafiają do Neona** (Frankfurt, UE) | 10:15 |
| **Dostęp** | ~~SSO Vercela wystarczy na teraz~~ — **przesłanka obalona pomiarem w W6.** Decyzja zastępcza Darka 2026-08-29, godz. 20:34: **aplikacja zostaje otwarta**; własne logowanie budujemy, gdy będzie w pełni gotowa | 10:3x, sprostowane 20:34 |
| **Kolejność** | **Najpierw pomiar Vercela**, potem migracja, potem wdrożenie | 10:3x |
| **Tryb pracy** | Jeden wyspecjalizowany agent na zadanie, własne okno kontekstowe | 10:38 |

---

## W0 — pomiar wykonalności · **Eva** · ~1 h · **rozstrzyga cały plan**

Godzina, która decyduje, czy reszta ma sens. Robimy ją **przed** migracją, bo wynik zmienia plan.

- Zmierzyć **rozmiar paczki funkcji Pythona** z `requirements.txt` wobec limitu Vercela
  (`fastapi`, `uvicorn`, `psycopg[binary,pool]`, `httpx`, `pydantic`, `openpyxl`, **`pandas` 72 MB**,
  **`numpy` 34 MB`**).
- Zmierzyć **czas zimnego startu** funkcji z tym importem.
- Jeśli się **nie mieści** — wypisać drogi wyjścia z kosztem każdej: zdjęcie `pandas` ze ścieżki
  żądania (używa go `_wczytaj` i **9 tabel / 17 kolumn** w `_KWOTOWE`), osobny host dla silnika,
  albo inna architektura. **Nie wybierać jej samemu — to wraca do Darka.**

**Bramka:** liczba MB, liczba sekund, werdykt **mieści się / nie mieści**, każde z cytatem wyjścia.
**Co przestanie działać:** nic — pomiar niczego nie zmienia.

---

## W1 — uzgodnienie dwóch schematów · **Ethan** · przed jakąkolwiek migracją

`_SCHEMAT` w `magazyn.py` (13 tabel, SQLite) i `silnik/baza/schemat.sql` (13 tabel, PostgreSQL)
rozjechały się w **dziewięciu miejscach** i nikt tego nie pilnuje.

- **Cztery brakujące kolumny `przychody_jdg`** — rozstrzygnąć: wracają do `schemat.sql`, czy schodzą
  z modelu. Kod je zapisuje (`zapisz_fakture`, `magazyn.py:835`) i czyta
  (`czy_skladki_naliczone_w_miesiacu`, `magazyn.py:870`).
- **`rejestr_stawek` dopisać do celu** — dziś żyje osobno w `wiedza/rejestr.py:54`. Postawienie bazy
  wymaga **dwóch** źródeł DDL. To dokładnie ta klasa przeoczenia, która daje „migracja przeszła,
  tylko rejestr pusty".
- **`data_obowiazku_vat NOT NULL`** — albo `zapisz_fakture` zaczyna ją wypełniać, albo więz schodzi.
- Pozostałe rozjazdy: `forma_opodatkowania` dopuszcza `LINIOWY`, którego `forma_na_rok` **odrzuci**;
  `kategorie.systemowa` i `cele.nadpisana_recznie` bez konsumenta; `termin` `TEXT NOT NULL` wobec
  `DATE` nullable; `pkwiu` z `DEFAULT ''` wobec `NOT NULL` bez default.

**Bramka:** **strażnik porównujący oba nośniki** — na wzór istniejącego
`testy/test_rejestr_sqlite.py:54` dla `rejestr.SCHEMAT` vs `SCHEMAT_SQLITE`, ale **porównujący też
typy i więzy, nie same nazwy kolumn**. Mutacja: rozjedź jedną kolumnę, strażnik ma się zaczerwienić.

---

## W2 — rozdzielić „otwórz" od „zmigruj" · **Ethan** · **jeszcze na SQLite**

`polacz()` (`magazyn.py:521`) robi **dwanaście rzeczy**: dwa `executescript`, dziewięć
`PRAGMA table_info`, dwie funkcje zasiewające, stempel wersji. Połączenie jest **per żądanie HTTP**
(`api/wspolne.py:23`). Przy pliku lokalnym to niewidoczne; **przy PostgreSQL to pełny DDL na każdym
żądaniu**.

Robimy to **osobnym krokiem, przed podmianą sterownika**, żeby nie mieszać dwóch zmian — inaczej
przy czerwonym teście nie wiadomo, która z nich zawiniła.

- `polacz()` **otwiera i tylko otwiera**.
- Migracja staje się osobnym wywołaniem, uruchamianym świadomie.
- Przy okazji: **trzy miejsca piszące bez `rollback`** (`ustaw_aktywnosc_kategorii:1391`,
  `usun_kategorie_trwale:1418`, `usun_koszt:2190`) i **dwa robiące dwa zapisy z `commit` w środku**
  (`zapisz_koszt:2149`, `oznacz_fakture_zaplacona:2221`) — w SQLite z autocommitem przechodzą,
  w PostgreSQL **zachowanie się zmieni**.

**Bramka:** `polacz()` nie wykonuje DDL (pokazać komendą) · **919 testów zielonych** · mutacja
potwierdzająca, że migracja nadal się wykonuje, gdy jest wołana.
**Co przestanie działać:** samoczynna migracja przy starcie — od tej chwili trzeba ją wywołać.

---

## W3 — strażniki **przed** migracją · **Quinn**

Trzy wady, które po migracji **nie dadzą żadnego sygnału**. Testy piszemy, póki jeszcze widać stan
poprawny.

1. **`Decimal` zamieniony na `float64` przez `pd.read_sql`.** Dziś `Decimal` jest wymuszany ręcznie
   (`_KWOTOWE`, `magazyn.py:143`), bo kolumny są `TEXT`. Po zmianie na `NUMERIC` psycopg zwróci
   `Decimal` — ale pandas może go po drodze zamienić i **nikt tego nie zauważy**, bo wszystkie
   asercje robią `Decimal(str(x))`, co działa na obu typach. **Test ma sprawdzać `type()`, nie
   wartość.** To jest dokładnie ta klasa wady, dla której zbudowano całą konstrukcję
   (`magazyn.py:7-8`).
2. **Komunikat „Faktura o tym numerze już jest".** `magazyn.py:810` łapie `sqlite3.IntegrityError`
   i **dopasowuje po treści komunikatu sterownika** (`if "numer_faktury" in str(e)`). PostgreSQL
   zwraca inny tekst — warunek cicho przestanie trafiać i użytkownik dostanie generyczne „Zapis
   odrzucony przez bazę".
3. **`NULL` → `NaN` w `wczytaj_zobowiazania`** (`magazyn.py:1965`) — `NaN` jest w warunku `if`
   **prawdziwy**, a `Decimal("0")` fałszywy. Normalizacja zostaje, ale z innego powodu; przetestować
   od nowa.

**Bramka:** trzy strażniki **czerwone na mutacji**, z nazwą testu, który padł.

---

## W4 — podmiana sterownika · **Ethan** · największe zadanie sesji

Zasięg zmierzony: **jeden plik** (`magazyn.py`, 2270 linii) plus testy. `api/` nie ma **ani jednego
literału SQL**, `interfejs/` nie importuje magazynu. Granica jest szczelna — to dobra wiadomość.

| Sprzężenie | Ile | Na co |
|---|---|---|
| placeholder `?` | **~89** (75 × `execute` + 14 × `_wczytaj`) | `%s` |
| `PRAGMA user_version` | 3 | tabela `wersja_schematu` — **PostgreSQL tego nie ma** |
| `PRAGMA table_info` | 3 | `information_schema.columns` (inny kształt wiersza — dziś `w[1]`) |
| `executescript` | 3 | `cursor.execute` — **inna semantyka transakcji**, brak implicit COMMIT |
| `kursor.lastrowid` | 1, ale **9 wołających** | `RETURNING id` |
| `INSERT OR IGNORE` | 1 | `ON CONFLICT DO NOTHING` — sprawdzić `rowcount` |
| `ON CONFLICT … excluded.*` | 4 | **przenosi się 1:1** — składnia SQLite pochodzi z PostgreSQL |
| `sqlite_master` | 1 | `information_schema.tables` |
| `AUTOINCREMENT` | 11 | `BIGSERIAL` |
| boole jako `INTEGER` | 8 miejsc | `BOOLEAN` — w tym **trójstan** `niezbedna` (NULL/0/1) |
| daty jako napisy | 20 × `isoformat()` | `DATE`; **`LIKE` na prefiksie daty przestanie działać** (2 miejsca) |
| kopia bazy przez plik | cała funkcja | `pg_dump` albo gałąź Neona — **nie ma odpowiednika w kodzie** |

**Trzy rzeczy do rozstrzygnięcia w tym zadaniu, nie do przemilczenia:**
- **`pd.read_sql` z gołym połączeniem psycopg** — pandas oficjalnie wspiera surowe połączenia tylko
  dla sqlite3. Albo SQLAlchemy Engine, albo `cursor.fetchall()` + `pd.DataFrame(...)`.
- **`SELECT *` w `_wczytaj`** — kolumna dołożona `ALTER TABLE` ląduje na końcu w bazie starej,
  a w środku w świeżej. Dziś ratuje to dostęp po nazwie; przy migracji to mina.
- **`_stawka_z_wiersza`** (`magazyn.py:701`) — **13 pozycji indeksowanych liczbą**, sparowanych
  z ręcznie wypisaną kolejnością w `SELECT`. Dopisanie kolumny w środku psuje wszystko po cichu.
  Moment na `dict_row`.

**Ryzyka wstrzyknięcia SQL nie ma** — sprawdzone: **14 z 14** nazw tabel w `_wczytaj` to literały
w kodzie, nic nie pochodzi od wołającego. Ale wzorzec *wygląda* jak dziura na tyle, że warto go
domknąć przy okazji.

**Bramka:** **919 testów zielonych na PostgreSQL** · `grep` na `sqlite3` w `silnik/` daje zero ·
`policz_liscie` zero trafień `float` · mutacja dla każdego nowego strażnika.
**Co przestanie działać:** kopia bazy przez skopiowanie pliku — **zastępnik buduje się w tym samym
zadaniu**, nie później. Strażnik ścieżki bazy (`STRAZNICY_SCIEZKI`) **słabnie**: `Path.resolve()`
traci sens, a ten sam host da się zapisać na kilka sposobów. To nazwana utrata siły.

---

## W5 — testy migracji · **Quinn**

**~101 testów w 11 plikach** ma jawne założenia SQLite. Z tego **~40 nie ma odpowiednika 1:1** —
to testy migracji, wersjonowania i kopii, których treścią jest „baza w starym stanie"
(`test_kopia_przed_migracja.py` w całości, `test_magazyn_budzet.py`, `test_trzy_kolumny.py`).
Pozostałe **~60** przechodzą po podmianie fikstury.

Do przepisania także: `test_granice.py:99` (asercja, że magazyn importuje `sqlite3` — **padnie**),
`test_magazyn_budzet.py:530` (`sqlite3.threadsafety` — traci przedmiot, zastępuje go pytanie o pulę
połączeń), cztery miejsca łapiące `sqlite3.IntegrityError`.

**Bramka:** zero testów pominiętych po cichu. **Uwaga zmierzona: bez `DATABASE_URL` suita potrafi
skończyć kodem 0 z „N skipped", co wygląda jak sukces.**

---

## W6 — wdrożenie silnika · **Eva**, przy udziale **Maxa** · **warunkowe wobec W0**

Dziś wdrożenie buduje **11 lambd, wszystkie z Next.js, zero funkcji Pythona**. Pięć rzeczy do
naprawy, każda zmierzona:

| Co | Stan |
|---|---|
| obiekt FastAPI | nazywa się **`aplikacja`**, nie `app` (`api/index.py:53`) — runtime szukający `app` go nie znajdzie |
| `api/__init__.py` | **nie istnieje** — pakiet działa jako namespace package |
| `next.config.mjs` | przepisuje `/api/*` na **twardy `http://127.0.0.1:8000`**, bez rozgałęzienia na środowisko — na Vercelu prowadzi donikąd |
| `DATABASE_URL` | **nie jest czytany nigdzie w kodzie Pythona** (zero trafień) — silnik czyta `AI_CFO_BAZA`, ścieżkę pliku |
| klucz modelu | `.env.example` deklaruje `AI_GATEWAY_API_KEY`, a kod czyta `GEMINI_API_KEY`/`GOOGLE_API_KEY` (`doradca.py:47`) |

Plus: `.env.example` chce `DATABASE_URL_BEZPOSREDNI`, Neon daje `DATABASE_URL_UNPOOLED`.
Zmienna `ADRES_SILNIKA` **już istnieje** (`warstwa-sieciowa.ts:28`) — to jest szew do użycia,
nie do zbudowania.

**Bramka:** wdrożony adres oddaje **prawdziwą liczbę z bazy Neona**, nie stronę błędu · pełna pętla
w przeglądarce na wdrożeniu: wpis → prognoza się zmienia → wycofanie przywraca.

---

## W7 — pasek prowadzi tam, gdzie obiecuje · **Jack** · tanie, widoczne natychmiast

**Dziewięć z dziewięciu odsyłaczy paska daje 404.** `powloka.tsx:70` renderuje `href="/{klucz}"`
dla wszystkich pozycji, a trasy Next istnieją dwie. **Nawet Płynność**: pasek prowadzi na
`/plynnosc`, ekran stoi pod `/`.

Do rozstrzygnięcia przez wykonawcę, z uzasadnieniem: przeniesienie ekranu do `app/plynnosc/` z
przekierowaniem z `/`, czy pole `adres` w mapie ekranów. **Uwaga:** mapa ma **dwa nośniki**
(`makiety/ekrany.py` + `interfejs/lib/ekrany.ts`) pilnowane strażnikiem
`test_mapa_ekranow_NIE_ROZJECHALA_sie_miedzy_jezykami`, a `ekrany.py` **odrzucił już raz** analogiczne
pole z uzasadnieniem „to byłby DRUGI NOSNIK faktu".

Drugie: **brakujące strony pokazują surowy 404 Next, nie `awaria.tsx`** — łamie §3.7 („awaria do
stanu użytecznego, nigdy do pustki"). Ekran ma powiedzieć, że tej części jeszcze nie ma.

**Bramka:** każdy odsyłacz paska prowadzi do ekranu albo do uczciwej informacji — **zmierzone
przejściem po wszystkich dziewięciu**, nie deklaracją.

---

## W8 — pole na stan konta · **Jack** · **najtańsza pozycja w całym planie**

Pozycja 1 z ośmiu pierwszego uruchomienia. **Cała warstwa poniżej jest gotowa**: trasa
`PUT /api/kotwica` stoi (`api/trasy_plynnosc.py:35`), `zapiszKotwice` jest napisana
(`lib/dane/plynnosc.ts:32`) i ma **zero wołających**. Brakuje **wyłącznie kontrolki i jej podpięcia**.

Bez tego prognoza nie ma punktu startu — `GET /api/plynnosc` zwraca `saldoMinimalne: null` i zdanie
„Nie policzę prognozy: nie wiem, ile masz na koncie".

Efekt uboczny: `straznik-ekran-wobec-silnika.mjs` przestaje wymagać ręcznego zapisu kotwicy przed
przebiegiem (dziś bez niej **mierzy ślepo**, linia 231).

**Bramka:** wpisujesz stan konta na wdrożonym adresie → prognoza zaczyna liczyć · odwzorowanie
`Main` ≤ 2% nie pogorszone · mutacja strażnika.

---

## W9 — ekran Budżet · **Mila** (ramka gotowa) → **Max** (trasy) → **Jack** (ekran)

Pozycja 2 pierwszego uruchomienia i **Plasterek 2** z `docs/plan-wydawania.md`. Najdroższe
i najbardziej odblokowujące: bez planu prognoza pokazuje pustą przyszłość i **wygląda znacznie
lepiej, niż jest**.

Sześć tras: `GET /api/budzet`, `POST /api/plan`, `PUT /api/plan/{id}`, `POST /api/plan/{id}/zakoncz`,
`POST /api/plan/kopiuj`, `POST /api/cele`. **Trzy z nich to warunek wyłączenia starej zakładki**
(`api/trasy.py:109`, asercja `len(WARUNEK_WYLACZENIA) == 5`, zbudowane 2 z 5).

Ramka `Budzet.dc.html` (1483 px) i źródło **już istnieją** — Mila weryfikuje, nie projektuje od zera.

**Bramka:** cztery operacje P-1 działają · **kosz planu kończy regułę zamiast kasować**
(pilnowane przez `test_nosniki.py`) · odwzorowanie ≤ 2%.

---

## W10 — przegląd i raport · **Leo**, potem **Oliver**

Leo przegląda całość wg standardu 14 domen. **Może zablokować.**

Szuka szczególnie: czy któraś ścieżka woła rachunek podatkowy **bez jawnej formy** (ryczałt był
domyślny w trzech miejscach), czy `float` nie wszedł na ścieżkę kwoty po obu stronach granicy HTTP,
i **których strażników nikt nie zmutował**.

Materiał wejściowy: `testy/MUTACJE.md` — **100 mutacji, 93 czerwone, 8 zdarzeń, w których strażnik
nie zadziałał**. Każdy przebieg ma sekcję „Czego ten przebieg NIE objął" — to gotowa lista długu.

---

## Dług zapisany świadomie, z progiem

| Dług | Próg powrotu |
|---|---|
| **Aplikacja jest OTWARTA dla każdego, kto zna adres** — nie „chroni ją SSO”. **Sprostowanie z pomiaru W6, 2026-08-29:** SSO Vercela chroni wyłącznie adresy pojedynczych wdrożeń (`...-949s2pc45-...` → 302); adres, pod który się wchodzi, nie jest chroniony przez nic. Zmierzone bez żadnych poświadczeń, dwukrotnie i niezależnie (wykonawca W6 i Oliver): `GET /` → 200, `GET /api/plynnosc` → 200 z pełną treścią bazy, **`PUT /api/kotwica` → 200**. Ostatnia pozycja jest najcięższa: **zapis** przechodzi bez uwierzytelnienia, więc każdy, kto zna adres, może kwoty nie tylko odczytać, ale i zmienić. Zamknięcie przez `deploymentType: "all"` zepsułoby aplikację — przepisanie z interfejsu do silnika jest żądaniem serwer-do-serwera i nie niesie sesji przeglądarki. **Decyzja Darka 2026-08-29, godz. 20:34: zostawiamy otwarte; własne logowanie budujemy, gdy aplikacja będzie w pełni gotowa.** Świadomy dług podjęty na zmierzonej przesłance — nie na tej z godz. 10:3x, która była nieprawdziwa. **Skutek do wiadomości: od tej chwili każda prawdziwa kwota wpisana do aplikacji leży w bazie dostępnej publicznie.** | **aplikacja w pełni gotowa** → własne logowanie (decyzja Darka). Progi wcześniejsze, gdyby zaszły przed tamtym: pierwsza prośba o pokazanie komuś aplikacji; pierwszy adres, który wyszedł poza Darka |
| **Rejestr stawek ma 19 pozycji i zero konsumentów** — silnik liczy z 28 stałych w `stawki.py`. Zatwierdzenie stawki przez Darka **nie zmienia dziś żadnej liczby** | pierwsza zmiana wartości w `stawki.py` albo w `wiedza/stawki_poczatkowe.py` |
| **`PUT /api/forma` i `PUT /api/dzialalnosc` nie istnieją nawet w spisie tras** — luka o poziom wyżej niż brak implementacji: brak decyzji, gdzie te dane wchodzą | przed pozycjami 4 i 7 pierwszego uruchomienia |
| **Spacja przed „zł"**: `prezentacja.py` daje U+00A0, ramki i `kwota.ts` U+0020 | pierwszy napis składany w Pythonie, który trafia na ekran |
| **Rozjazd liczby stawek w dokumentach** — trzy dokumenty mówią „18", kod daje **19** | przy najbliższej edycji któregokolwiek |

---

## Weryfikacja końcowa

```bash
cd "Doradca Finansowy"
./.venv/bin/python -m pytest testy/ -q            # zielone, z liczbą; zero cichych pominięć
cd interfejs && npx tsc --noEmit && npm run build
npx vitest run
node narzedzia/porownaj-z-makieta.mjs Ksiegowanie http://localhost:3000/ksiegowanie --wzorzec
node narzedzia/porownaj-z-makieta.mjs Main        http://localhost:3000/ --wzorzec
node narzedzia/straznik-ekran-wobec-silnika.mjs
node narzedzia/straznik-podwojne-klikniecie.mjs
cd ../makiety && python3 buduj-makiety.py --kontrola   # exit 0, ≥ 42 pliki
```

**Sesja jest zaliczona, gdy:** wchodzisz na adres w internecie, wpisujesz stan konta, wpisujesz
wydatek — i **prognoza pokazuje Twoją liczbę, nie liczbę z ramki**. Wszystko inne jest drogą do
tego zdania.

**Bramka zerowa:** jeśli **W0** pokaże, że silnik nie mieści się na Vercelu — **W4 i W6 nie ruszają**,
a plan wraca do Darka z wypisanymi drogami wyjścia i kosztem każdej. Migracja na PostgreSQL (W1–W3,
W5) ma wartość niezależnie od wyniku W0; wdrożenie nie.

---

## Prompt startowy dla Olivera — do wklejenia w nowej sesji

Poniższy tekst jest **samodzielny**: nie zakłada, że nowa sesja zna cokolwiek z poprzednich.

```
Jesteś Oliver, COO nordsignal. Prowadzisz cel do wyniku — sam nie wykonujesz.

KATALOG ROBOCZY
/Users/dariuszgradzik/Claude_Projekty/nordsignal-operating-system/Doradca Finansowy

PRZECZYTAJ NAJPIERW, W TEJ KOLEJNOŚCI
1. CLAUDE.md                        — konstytucja projektu; sekcja 8 opisuje tryb tej pracy
2. docs/plan-chmura-2026-08-29.md   — plan, który wykonujesz; JEDYNY nośnik kolejności
3. docs/PRD.md                      — wymagania i bramki odbioru (sekcja 12)
Nie czytaj niczego więcej z góry. Resztę czytają specjaliści w swoich oknach.

CEL, JEDNYM ZDANIEM
Wchodzisz na adres w internecie, wpisujesz stan konta, wpisujesz wydatek — i prognoza
pokazuje Twoją liczbę, nie liczbę z ramki. Wszystko inne jest drogą do tego.

STAN, W KTÓRYM ZACZYNASZ — zbudowane w nocy 2026-08-29
- 919 testów zielonych, 0 pominiętych; vitest 38; tsc i build bez błędów
- dwa ekrany (Płynność, Księgowanie) odwzorowują ramki CO DO PIKSELA na wzorcowym
  zestawie danych: 0,07% i 0,12% przy progu 2%
- sześć tras, silnik przeniesiony, podział osi prognozy działa: wpis 500 zł ponad plan
  obniża saldo na dziś o 500,00 zł, wycofanie przywraca
- repo prywatne: github.com/Danolog/nordsignal-doradca-finansowy (gałąź main)
- Vercel: projekt nordsignal-doradca-finansowy w zespole dareks-projects-da398fc0,
  build przechodzi, adres OTWARTY (SSO chroni tylko adresy pojedynczych wdrozen - pomiar W6)
- Neon: projekt doradca-finansowy (purple-hat-65403365), aws-eu-central-1, Postgres 18,
  DATABASE_URL w zmiennych Vercela. BAZA JEST PUSTA — zero schematu, zero danych
- baza robocza z prawdziwymi danymi Darka: ~/Dane-robocze-doradca-finansowy/ (prawa 600,
  POZA repozytorium — nie kopiuj jej nigdzie)
- narzędzia: interfejs/narzedzia/{porownaj-z-makieta,straznik-ekran-wobec-silnika,
  straznik-podwojne-klikniecie,silnik-wzorcowy,dane-wzorcowe}.mjs

ZACZYNAJ OD W0 — I TO JEST BRAMKA, NIE FORMALNOŚĆ
W0 mierzy, czy silnik z pandas (72 MB) i numpy (34 MB) mieści się w funkcji Vercela
i jak długo wstaje na zimno. Nikt tego nie sprawdził, a cała architektura chmurowa
na tym stoi. Godzina pracy rozstrzyga plan.
JEŚLI SIĘ NIE MIEŚCI: W4 i W6 NIE RUSZAJĄ. Wracasz do Darka z drogami wyjścia
i kosztem każdej. Migracja na PostgreSQL (W1-W3, W5) ma wartość niezależnie od wyniku;
wdrożenie nie.

JAK PRACUJESZ — reguły twarde, nie preferencje
- Powołujesz specjalistów z ../agents/ narzędziem Agent. Przydział stoi w planie przy
  każdym zadaniu: Eva (środowisko, wdrożenie, pomiar), Ethan (architektura, silnik,
  migracja), Max (trasy), Jack (interfejs), Mila (projekt ekranu), Quinn (testy
  i mutacje), Leo (przegląd), Sophia (decyzje produktowe), Ryan (ryzyko, dane osobowe).
- NARAZ PRACUJE DOKŁADNIE JEDEN AGENT, WE WŁASNYM OKNIE KONTEKSTOWYM. Powołujesz po
  kolei i czekasz na wynik. To jest wymóg Darka, nie sufit wydajności.
- Pilnujesz głównego okna kontekstowego. Praca szczegółowa — czytanie plików, przebiegi
  testów, mutacje — dzieje się w oknie specjalisty. Do Ciebie wraca WYNIK, nie przebieg.
- Sam nie piszesz kodu, nie diagnozujesz logów, nie prowadzisz gita ani migracji.
  Wahasz się, czy zadanie jest techniczne — traktuj jak techniczne i deleguj.
- Zlecenie dla agenta ma być SAMODZIELNE: nie zakłada, że zna poprzednie zadania.
  Wklejasz mu stan wejściowy, zmierzone liczby i bramkę odbioru.
- Po każdym zadaniu: checkpoint wobec bramki z planu. Bramka niespełniona = zawracasz
  do agenta z NAZWANĄ luką, nie przechodzisz dalej.
- Commit po każdym zadaniu, autor Darek <mubueu@gmail.com>, TYLKO własne ścieżki,
  NIGDY `git add -A` — w repozytorium pracują równolegle inne sesje.

CZEGO ŻĄDASZ OD KAŻDEGO AGENTA
- Dowód z komendy, nie deklaracja. Cytat realnego wyjścia albo etykieta „niezweryfikowane".
- Najpierw nośnik, potem pomiar: „nośnik twierdzi X, pomiar pokazuje Y", nigdy „nie wiadomo".
- Mutacja dla każdego strażnika przywołanego jako dowód: co zmieniono, NAZWA testu, który
  padł, data, kontrola po cofnięciu. Kopia drzewa poza repozytorium.
- Kontrola liczności: ILE rzeczy pomiar faktycznie widział. Ta noc dała 100 mutacji,
  93 czerwone i OSIEM zdarzeń, w których strażnik nie zadziałał — jeden trafiał
  w komentarz, drugi w nieużywany duplikat klucza, kontrola ramek meldowała 21/21 exit 0
  nie obejmując pliku, który zadanie właśnie wytworzyło, a narzędzie pomiarowe drukowało
  odwrotność prawdy. Sprawdzenie, do którego nic nie dociera, melduje sukces.
- Przed działaniem nieodwracalnym: osobna pozycja „co przez to przestanie działać".

REGUŁY MERYTORYCZNE, KTÓRE POWTARZASZ W KAŻDYM ZLECENIU
Darek jest na SKALI PODATKOWEJ, duży ZUS, VAT 23% memoriałowo, działalność od 2026-09-01,
horyzont od IX 2026. RYCZAŁT JEST WADĄ, NIE OPCJĄ DOMYŚLNĄ — w poprzedniej aplikacji był
wartością domyślną w trzech miejscach i liczył cudzą formą. Kwota jest napisem po obu
stronach granicy HTTP; liczba zmiennoprzecinkowa w ścieżce kwoty to wada krytyczna.

CZEGO NIE ROBISZ BEZ DARKA
Dziewięć czerwonych linii z ../CLAUDE.md sekcja 4 zostaje w mocy: żadnego wydatku (Vercel
hobby + Neon free — jeśli cokolwiek proponuje płatny plan, ZATRZYMAJ SIĘ i zgłoś), żadnego
nowego MCP, żadnej edycji plików rządzenia firmy (../CLAUDE.md, ../agents/*.md, ../hooks/).
NIE dotykaj cudzych zasobów: projektów Neona SkillBridge/nordsignal-kb/asystent-ai/nela/
MyHelper, projektów Vercela skill-bridge-ai i my-helper-2, katalogu ../AI CFO (tam żyje
historia 204 wpisów) ani SkillBridge/.
Cisza nigdy nie autoryzuje czerwonej linii.

CO PISZESZ DO DARKA
Tylko to, czego od niego potrzebujesz — decyzji, danych, dostępu, sign-offu. Wtedy: czego
potrzebujesz, po co, i co się bez tego nie wydarzy. JEDNA PROŚBA NARAZ. NIE piszesz,
dlaczego coś nie zadziałało ani jakie wybory techniczne podjęto — to idzie do dokumentów,
opisów commitów i testy/MUTACJE.md. Na koniec jeden raport: co jest zrobione wobec bramek,
co zostało otwarte i dlaczego, czego potrzebujesz. Raport prowadzi do decyzji, nie informuje.

ZACZYNAJ OD ZADANIA W0.
```

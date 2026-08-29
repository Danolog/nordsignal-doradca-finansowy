# W12 — domknięcie wdrożenia: zdanie celu sesji jest prawdziwe na adresie w internecie

**Data:** 2026-08-30 · **Wykonanie:** Eva (Platform/DevOps) · **Zlecenie:** Oliver (COO)
**Gałąź:** `noc-2026-08-29`, głowa wejściowa `1403c01`
**Wersja:** v1.0

---

## 0. Jednym zdaniem

*„Darek wchodzi na adres w internecie, wpisuje stan konta, wpisuje wydatek — i prognoza
pokazuje jego liczbę."* — **przejdzone na wdrożeniu 2026-08-30**, przez ekran, nie przez trasę.
Wpis 500 zł obniżył saldo o **500,00 zł**, ta sama liczba, co w nocy na środowisku lokalnym.

Wejściowo zdanie było fałszywe: dziewięć z jedenastu adresów paska odpowiadało `404`,
a `/api/budzet` nie istniał na wdrożeniu.

---

## 1. Wdrożenie stało na stanie sprzed W0 — przyczyna i naprawa

### 1.1 Nośnik twierdzi X, pomiar pokazuje Y

| Nośnik | Co twierdził | Co pokazał pomiar |
|---|---|---|
| `docs/2026-08-29-wdrozenie-silnika-W6.md:305` | „pierwsze wdrożenie z gita zbuduje wersję **sprzed W6**" | wersję **sprzed W0** — `main` repozytorium wdrożeniowego stał na `7f92e98`, czyli na stanie sprzed pierwszego commita sesji chmurowej |
| przegląd Leo (`02a7f47`) | „**dwanaście** commitów w tyle" | **siedemnaście**. `git rev-list --count 680d87a..wycinek` → `17` |

**Przyczyna:** wdrożenia z W6 szły z wiersza poleceń (`source=cli`), z pominięciem gita.
Repozytorium wdrożeniowe jest **osobne** (`Danolog/nordsignal-doradca-finansowy`) i nikt go
nie dogonił.

### 1.2 Mechanizm synchronizacji — ustalony pomiarem, nie zgadnięty

Katalog roboczy leży w repozytorium **firmy** (`nordsignal-operating-system`), a repozytorium
wdrożeniowe ma zawartość `Doradca Finansowy/` **w swoim korzeniu**. Droga między nimi nie była
nigdzie zapisana. Ustalona eksperymentem:

```
$ git subtree split --prefix="Doradca Finansowy" -b wycinek     # w klonie repozytorium firmy
Created branch 'wycinek'
$ git rev-parse 680d87a
680d87a527ff922c29db40b76d7d8b80c74057c4
   repozytorium wdrozeniowe, ten sam commit:
680d87a527ff922c29db40b76d7d8b80c74057c4
```

Wycinek odtwarza identyfikator co do znaku — **poprzednia synchronizacja szła tą samą drogą**.
Dzięki temu scalenie jest przewinięciem historii, a nie jej przepisaniem: żaden commit nie
został nadpisany, `git push --force` nie był potrzebny, a commit `7f92e98`
(`.vercel/` w `.gitignore`, istniejący **tylko** w repozytorium wdrożeniowym) zachował się przez
scalenie — `.gitignore:46` nadal niesie `.vercel/`.

### 1.3 Kontrola lustra

```
KONTROLA LICZNOSCI: plikow sledzonych w repozytorium wdrozeniowym = 236
  identycznych z drzewem roboczym : 234
  ROZNYCH                          : 2 ['.gitignore', 'interfejs/next-env.d.ts']
  brak w drzewie roboczym          : 0 []
```

Obie różnice są zamierzone i nazwane:
- `.gitignore` — repozytorium wdrożeniowe niesie dodatkowy wpis `.vercel/` (commit `7f92e98`).
- `interfejs/next-env.d.ts` — **kopia w drzewie roboczym jest brudna**: `next dev` przepisał
  ścieżki na `./.next/dev/types/...`. Do repozytoriów idzie wersja z commita
  (`./.next/types/...`), czyli ta, którą wytwarza budowanie produkcyjne. Świadomy wybór:
  wariant deweloperski w repozytorium wdrożeniowym wskazywałby pliki, których budowanie
  produkcyjne nie tworzy.

---

## 2. Powiązanie z gitem — luka Leo domknięta

Leo nie zdołał tego ustalić: jego token nie miał uprawnień do listy instalacji aplikacji
GitHuba (`403: You must authenticate with an access token authorized to a GitHub App`),
a `gh api .../hooks` zwraca `[]`, bo integracja Vercela chodzi przez aplikację GitHuba, nie
przez webhooki.

**Domknięte odczytem ze źródła autorytatywnego — interfejsu programowego Vercela, nie ze
zrzutu konfiguracji.** `GET /v9/projects?limit=100`, 2026-08-30:

| Projekt | Katalog główny | Powiązanie z gitem |
|---|---|---|
| `nordsignal-doradca-finansowy` | `interfejs` | **JEST** — `{"type":"github","org":"Danolog","repo":"nordsignal-doradca-finansowy","productionBranch":"main"}` |
| `nordsignal-doradca-silnik` | *(korzeń)* | **`link: null`** — nie jest powiązany z żadnym repozytorium |

**Potwierdzenie behawioralne, nie tylko odczyt konfiguracji:** push do `main` wywołał
wdrożenie `dpl_FparMj8N4jL95h8dYCLKk4Gzw2wM`, `source=git`, `target=production`,
`githubCommitSha = 8f639a3afabc7b9e14d3ad90c3d8d8ec40b3d546`. Projekt silnika żadnego
wdrożenia po pushu nie dostał.

### 2.1 Dlatego kolejność była silnik → interfejs, a nie odwrotnie

Skutek, którego uniknięto: gdyby najpierw poszedł push, podniósłby **tylko** interfejs do W11,
a silnik został na W6 — ekran `/budzet` wyrenderowałby się i uderzył w `/api/budzet`, którego
silnik nie ma. **Ekran żyje, dane 404.** Wykonana kolejność:

1. `vercel deploy --prod` projektu **silnika** (jedyna droga — projekt nie ma powiązania z gitem),
2. `git push origin main` do repozytorium wdrożeniowego → automatyczne wdrożenie **interfejsu**.

**Dług nazwany, nienaprawiony:** asymetria zostaje. Silnik wdraża się wyłącznie z wiersza
poleceń, więc **nic nie gwarantuje, że wdrożony silnik odpowiada zawartości repozytorium**.
Dziś odpowiada — wdrożenie szło z tego samego drzewa co push, minutę wcześniej. Próg
domknięcia: powiązanie projektu silnika z tym samym repozytorium przy katalogu głównym
w korzeniu. Nie zrobione, bo zmiana katalogu głównego i powiązania projektów Vercela leży
poza zakresem tego zadania (rozstrzygnięcie W6 o dwóch projektach zostaje).

---

## 3. Kontrola liczności wdrożeń

Odczyt z `/v11/deployments/{id}/builds`, 2026-08-30:

| Projekt | Wdrożenie | Lambd | Środowisko wykonawcze | Region każdej lambdy |
|---|---|---|---|---|
| `nordsignal-doradca-silnik` | `dpl_6BmhMYbWXKVo99rG5cyt1nCCWLjQ` | **1** | `python3.12` | `fra1` |
| `nordsignal-doradca-finansowy` | `dpl_FparMj8N4jL95h8dYCLKk4Gzw2wM` | **17** | `nodejs24.x` | `fra1` |

**Razem 18 lambd, z tego 1 funkcja Pythona, 18/18 we Frankfurcie.**
Rozmiar funkcji silnika: `69,73 MB` przy limicie 500 MB (`vercel inspect`).

To jest kontrola przeciw awarii z W0, gdzie wdrożenie z błędną konfiguracją **zakończyło się
sukcesem w 20 ms, budując zero funkcji** (`Builds: . [0ms]`) — zielone i puste.

---

## 4. Zdanie celu sesji, przejdzone na wdrożeniu

Wszystkie liczby z jednego przebiegu, 2026-08-30, przeglądarka Chromium, adres
`https://nordsignal-doradca-finansowy.vercel.app`.

| Krok | Stan przed | Akcja | Stan po |
|---|---|---|---|
| 1. wejście na adres | — | `GET /plynnosc` | `http=200`; `saldoMinimalne = null`; pozycji księgi `0`; na ekranie „brak prognozy · okno 45 dni"; werdykt: *„Nie policzę prognozy: nie wiem, ile masz na koncie…"* |
| 2. stan konta **przez ekran** | `saldoMinimalne = null` | klik „Podaj stan konta" (przycisków na ekranie: **1**), pole kwoty **1**, data wypełniona z góry `"2026-08-29"`, wpisane `12345,67`, Enter — **dwa dotknięcia** | `saldoMinimalne = "12345.67"` (typ `string`), pozycji księgi `5`, werdykt *„Nie schodzisz poniżej zera — najniżej masz 12 345,67 zł 29 sierpnia."*; **na ekranie bez odświeżenia strony**: `12 345,67 zł` |
| 3. wydatek **przez ekran** | `"12345.67"` | Księgowanie → typ „Wydatek" → kwota `500,00` → kategoria „Inne" → „Zapisz wpis" | `saldoMinimalne = "11845.67"`, pozycji księgi `6` · **RÓŻNICA = 500,00** |
| 4. prognoza pokazuje liczbę | — | `GET /plynnosc` | ekran zawiera `11 845,67`: **true**; ekran zawiera `10 000,00` (kotwica pomiarowa W6): **false** |
| 5. wycofanie **przez ekran** | `"11845.67"` | klik „wycofaj" (przycisków: **1**) | `saldoMinimalne = "12345.67"` · **RÓŻNICA wobec stanu sprzed wpisu = 0,00** |

**Zmierzone w nocy lokalnie: 500,00 zł. Na wdrożeniu: 500,00 zł.** Ta sama liczba.
Błędów strony (`pageerror`) w całym przejściu: **0**.

### 4.1 Kwota jest napisem po obu stronach granicy — na wdrożeniu

```
typ saldoMinimalne w JSON: string
surowy JSON zawiera "12345.67": true
surowy JSON zawiera "12345.6" (wariant gubiacy koncowa cyfre, wada z W5): false
liczb zmiennoprzecinkowych w calej odpowiedzi: 0
```

Kontrola liczności na czterech trasach silnika: **120 liści przejrzanych, 0 typu `float`**
(`/api/zdrowie` 9, `/api/plynnosc` 10, `/api/ksiegowanie` 72, `/api/budzet` 29).

### 4.2 Jedenaście adresów paska

| | przed W12 | po W12 |
|---|---|---|
| sprawdzonych | 11 | 11 |
| odpowiada `200` | **2** (`/`, `/ksiegowanie`) | **11** |
| `/api/budzet` na silniku | `404` | `200`, prawdziwe dane z Neona |

### 4.3 Reguła merytoryczna — forma opodatkowania

Baza produkcyjna, odczyt bezpośredni: `forma_opodatkowania = [(2026, 'SKALA')]`.
Omiecenie jedenastu ekranów wdrożenia: **ekranów pobranych 11, ze słowem „ryczałt…" = 0.**

Kafelek „Rezerwa na podatki" **odmawia**, zgodnie z naprawą z W11:
```json
{"klucz":"rezerwa","tytul":"Rezerwa na podatki","kwota":null,
 "dopisek":"saldo narastające, nie wydatek miesiąca",
 "wyjasnienie":"Składki ZUS nie zostały policzone: nie znam daty rozpoczęcia działalności…"}
```
`0,00 zł` pod tym tytułem czytałoby się jako „nic nie jesteś winien urzędowi" — i dlatego
kwoty tam nie ma.

---

## 5. Kotwica pomiarowa skasowana

### 5.1 Co przez to przestanie działać — pozycja wypisana PRZED akcją (§3.11)

**Konsumenci `stan_konta`, policzeni:** pisarz jeden (`magazyn.zapisz_stan_konta`),
czytelnik jeden (`magazyn.wczytaj_stan_konta` → `silnik/ekran_plynnosc.py`), trasa jedna
(`PUT /api/kotwica`). Poza prognozą płynności **nikt tej tabeli nie czyta** — pięć plików
w ogóle wymienia jej nazwę, żaden spoza tej ścieżki.

**Utracona zdolność:** prognoza przestaje mieć punkt startu i **wraca do stanu „nie wiem, ile
masz na koncie"**. To jest stan zamierzony, nie awaria — zdanie odmowy istnieje właśnie na tę
okoliczność. Nic poza tym nie przestaje działać: księgowanie, budżet, kategorie i rejestr
stawek nie czytają `stan_konta`.

**Czego nie tracimy:** żadnych danych Darka — kasowana wartość jest **pomiarowa**
(`docs/2026-08-29-wdrozenie-silnika-W6.md:191`), a `wpisów budżetu` było `0`.

### 5.2 Stan przed / akcja / stan po

```
BAZA (bez poswiadczen): postgresql://<uzytkownik:haslo>@ep-old-waterfall-b16ho6yq-pooler.c-5.eu-central-1.aws.neon.tech/neondb
wersja serwera : 18.6 (c5250a2) | nazwa bazy: neondb | tabel w schemacie public: 15

--- STAN PRZED ---
stan_konta: WIERSZY = 1
   data=2026-09-15 kwota=10000.00
wpisy_budzetu 0 | cele_oszczednosciowe 0 | majatek 0 | zobowiazania 0
kategorie 24 | rejestr_stawek 19 | forma_opodatkowania [(2026, 'SKALA')]

KONTROLA LICZNOSCI PRZED: wierszy pasujacych do warunku = 1
AKCJA: DELETE FROM stan_konta WHERE data = '2026-09-15' AND kwota = 10000.00
   wierszy usunietych (rowcount): 1

--- STAN PO ---
stan_konta: WIERSZY = 0 []
wpisy_budzetu 0 | kategorie 24 | rejestr_stawek 19
forma_opodatkowania: [(2026, 'SKALA')]
```

Skutek na wdrożeniu, zmierzony po akcji:
```
saldoMinimalne         None
pozycji ksiegi         0
zdanieWerdyktu         'Nie policzę prognozy: nie wiem, ile masz na koncie…'
```

**Warunki twarde dotrzymane:** wyłącznie celowany `DELETE … WHERE` po dwóch kolumnach naraz,
z kontrolą liczności **przed** (`= 1`, inaczej skrypt odmawia) i asercją `rowcount == 1`
**po**. Żadnego `DROP`, żadnego `TRUNCATE`, żadnego `DELETE` bez `WHERE`.

**Adres bazy brany ze źródła autorytatywnego** — z magazynu zmiennych projektu Vercela, który
zasila wdrożoną funkcję (`GET /v1/projects/{id}/env/{envId}`), a nie ze zrzutu `.env` na dysku.
Zrzut opisuje stan sprzed chwili i renderuje kilka różnych stanów świata identycznie.
Wartość poświadczenia nie została nigdzie wypisana.

### 5.3 Sprzątanie po przejściu

Przejście z §4 samo zapisało kotwicę `12 345,67 zł` na `2026-08-29`. Skasowana tą samą drogą
(`DELETE … WHERE data = '2026-08-29' AND kwota = 12345.67`, `rowcount = 1`).
Wpis 500 zł został wycofany przez ekran i **nie zostawił wiersza** — `wpisy_budzetu` = `0`.

**Stan końcowy bazy produkcyjnej:** `stan_konta` **0 wierszy**, `wpisy_budzetu` **0**,
`kategorie` 24, `rejestr_stawek` 19, `forma_opodatkowania` `[(2026, 'SKALA')]`.
Prognoza mówi „nie wiem, ile masz na koncie" — i czeka na pierwszą liczbę Darka.

---

## 6. Strażnik regionu

Opis mutacji: `testy/MUTACJE.md`, sekcja „W12".
Zmiana w jednym pliku: `testy/test_wejscie_platformy.py` (4 testy → 6).

Skrót: `test_funkcja_silnika_STOI_W_UNII` czytał **wyłącznie** `vercel.json` z korzenia, więc
mutacja Leo M-L12 na `interfejs/vercel.json` dawała `1113 passed`. Po naprawie ta sama mutacja
czerwieni `test_projekt_STOI_W_UNII[interfejs/vercel.json]`. Dołożona kontrola liczności
(`test_spis_projektow_OBEJMUJE_KAZDY_plik_konfiguracji`) porównuje **zbiór plików `vercel.json`
w drzewie** ze spisem `PROJEKTY_VERCELA` — trzeci projekt nie wejdzie poza pomiar po cichu.

---

## 7. Suita

| | przed W12 | po W12 |
|---|---|---|
| `pytest testy/ -rs` | `1115 passed, 3 deselected` | **`1117 passed, 3 deselected`** |
| pominiętych | 0 | **0** |

Przyrost `+2` to rozbicie jednego strażnika regionu na dwa sparametryzowane przypadki plus
strażnik liczności. Suita uruchamiana wobec PostgreSQL w kontenerze `doradca-postgres`
(port 5434, baza `doradca_test`); bez bazy czerwieni się celowo (`pytest.UsageError`, kod 4).

---

## 8. Czego W12 NIE objął

| Nieobjęte | Skutek / próg |
|---|---|
| **Powiązanie projektu silnika z gitem** | zostaje wdrażany z wiersza poleceń. Nic nie gwarantuje maszynowo, że wdrożony silnik odpowiada zawartości repozytorium. Próg: pierwsze wdrożenie silnika robione nie z tego samego drzewa co push |
| **Region sprawdzany na wdrożeniu, nie tylko w pliku** | strażnik czyta `vercel.json` w repozytorium; region zmieniony ręcznie w konsoli byłby poza jego zasięgiem. Zmierzone dziś ręcznie: 18/18 lambd `fra1`. Automatu na to nie ma |
| **Wygląd ekranów po wdrożeniu** | porównanie z ramkami robione było lokalnie; na wdrożeniu nieporównane — tak samo jak po W6 |
| **Ochrona dostępu** | adres jest **otwarty**, świadomie (decyzja Darka 2026-08-29 godz. 20:34). Zapis stanu konta nadal przechodzi bez uwierzytelnienia — od chwili, gdy Darek wpisze swoje liczby, będą dostępne dla każdego, kto zna adres |
| **Klucz modelu językowego** | rozjazd `AI_GATEWAY_API_KEY` vs `GEMINI_API_KEY` z W6 nadal nienaprawiony; żadnej zmiennej klucza nie ma w żadnym z dwóch projektów |
| **Zachowanie bez JavaScriptu, czytnik ekranu** | poza zakresem |

**Wady spoza zakresu, zapisane nie naprawiane:** brak.
Ostrzeżenie platformy przy każdym wdrożeniu silnika:
`Provided memory setting in vercel.json is ignored on Active CPU billing` —
ustawienie `memory: 1024` w `vercel.json` nie robi dziś nic. Nie ruszone, bo to zmiana
konfiguracji poza zleconym zakresem; strażnik `maxDuration` jej nie dotyczy.

---

## 9. Ślad operacji na cudzych zasobach

| Zasób | Stan |
|---|---|
| `skill-bridge-ai`, `my-helper-2` (Vercel) | **nietknięte** — wyłącznie odczyt listy projektów |
| projekty Neona SkillBridge / nordsignal-kb / asystent-ai / nela / MyHelper | **nietknięte** |
| gałąź produkcyjna i projekt Neona `doradca-finansowy` | **nietknięte** — żadnego kasowania gałęzi, żadnej zmiany schematu |
| `~/Dane-robocze-doradca-finansowy/` | **nietknięte, niekopiowane** |
| Katalog główny projektów Vercela | **bez zmian** (`interfejs` / korzeń) |
| Ochrona wdrożenia (SSO) | **nietknięta** — ani włączona, ani wyłączona |
| Wydatek | **zero.** Vercel `hobby`, Neon `free`; nic nie proponowało płatnego planu |
| Repozytorium firmy | **żadnego commita** — zmiany zostawione w drzewie roboczym do commitu przez Olivera |

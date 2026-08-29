# W6 — wdrożenie silnika. Przebieg, pomiary, decyzje

**Wersja:** v1.0 · 2026-08-29 · autor: Eva (Platform/DevOps) · gałąź `noc-2026-08-29`, głowa wejściowa `a73473a`
**Charakter dokumentu:** przebieg prac i dowody. Raport dla Olivera jest osobny i krótszy.

---

## 0. Wynik

Aplikacja **działa pod adresem w internecie i liczy na prawdziwej bazie**:

```
GET https://nordsignal-doradca-finansowy.vercel.app/  -> http=200
    "Nie schodzisz poniżej zera — najniżej masz 10 000,00 zł 15 września."
```

Silnik Pythona stoi jako funkcja we **Frankfurcie** (`fra1`), baza Neona w `eu-central-1`.
**Siedem z siedmiu tras odpowiada kodem 200.** Pełna pętla (stan konta → prognoza → wpis →
zmiana o dokładnie 500,00 zł → wycofanie → powrót) zmierzona **na wdrożeniu**, nie lokalnie.

---

## 1. Nośniki sprawdzone PRZED pomiarem (§3.10)

| Nośnik | Co twierdzi | Odczytany |
|---|---|---|
| `docs/plan-chmura-2026-08-29.md`, W6 | pięć rzeczy do naprawy | tak |
| `docs/2026-08-29-pomiar-vercel-silnik.md` (W0, moje) | mieści się: 198,14 MB / 500 MB; dwa blokery; region `iad1` | tak |
| `api/index.py` | obiekt nazywa się `aplikacja` (nośnik mówi: linia 53) | tak |
| `api/wspolne.py` | połączenie na żądanie; miejsce na pulę nazwane | tak |
| `interfejs/next.config.mjs` | przepisanie na `http://127.0.0.1:8000` bez rozgałęzienia | tak |
| `interfejs/lib/dane/warstwa-sieciowa.ts` | `ADRES_SILNIKA` istnieje (linia 28) | tak |
| `.env.example` | `DATABASE_URL_BEZPOSREDNI` wobec `DATABASE_URL_UNPOOLED` | tak |

### Nośnik twierdzi X, pomiar pokazuje Y

| Rzecz | Nośnik | Pomiar 2026-08-29 |
|---|---|---|
| obiekt FastAPI w `api/index.py` | „linia 53" | **linia 79**; nazwa `aplikacja` — zgadza się |
| `api/__init__.py` | nie istnieje | **nie istniał**; utworzony |
| `next.config.mjs` prowadzi donikąd | twierdzenie | **potwierdzone nagłówkiem**: `x-vercel-error: DNS_HOSTNAME_RESOLVED_PRIVATE`, `http=404` |
| `DATABASE_URL` nie czytany nigdzie | „zero trafień; silnik czyta `AI_CFO_BAZA`" | **NIEAKTUALNE — W4 to zmieniło.** `magazyn.py:67 ZMIENNA_BAZY = "DATABASE_URL"`; `AI_CFO_BAZA` ma dziś **jedno** trafienie i to w komentarzu testu |
| `DATABASE_URL_BEZPOSREDNI` vs `_UNPOOLED` | rozjazd nazw | **rozwiązane w W4**: `magazyn.adres_migracji` czyta obie (`magazyn.py:80-81`) |
| klucz modelu | `.env.example` chce `AI_GATEWAY_API_KEY`, kod czyta `GEMINI_API_KEY`/`GOOGLE_API_KEY` | **potwierdzone**, `doradca.py:47`. **Nie ruszone — poza zakresem W6** (doradca nie wchodzi w pętlę tego zadania), zapisane jako dług |
| ochrona SSO | „adres za ochroną SSO"; „SSO wystarczy na teraz" | **FAŁSZ dla adresu produkcyjnego** — patrz §6 |

---

## 2. Architektura wdrożenia — i dlaczego nie prostsza

**Wynik: dwa projekty Vercela w jednym repozytorium.**

| Projekt | Katalog główny | Co buduje | Region |
|---|---|---|---|
| `nordsignal-doradca-finansowy` | `interfejs` | Next.js, 11 wyjść (5 lambd widocznych + 6 pozycji) | `fra1` |
| `nordsignal-doradca-silnik` | korzeń | **1 lambda `api/index` (69,64 MB)** | `fra1` |

Przeglądarka widzi **jeden adres**. `/api/*` przepisuje `next.config.mjs` na adres silnika
(zmienna `ADRES_SILNIKA`). To nie jest wygoda — `app/ksiegowanie/formularz.tsx` ma `"use client"`
i zapisuje wpis **z przeglądarki**; silnik pod osobnym adresem znaczyłby politykę pochodzenia
(CORS) do obejścia i drugą powierzchnię do zabezpieczenia.

### Dwie drogi odrzucone, obie po pomiarze — nie po namyśle

**(a) Jeden projekt, katalog główny = korzeń, framework Next.**
Odrzucone przez platformę przy budowie:

```
No Next.js version detected. Make sure your package.json has "next" in either
"dependencies" or "devDependencies". Also check your Root Directory setting
matches the directory of your package.json file.
```

Vercel przy frameworku Next wymaga `package.json` **w katalogu głównym projektu**; nasz stoi
w `interfejs/`. Przeniesienie go do korzenia to zmiana struktury całego repozytorium — poza
zakresem W6.

**(b) Jeden projekt, dwaj budowniczowie w `vercel.json` (`builds`: `@vercel/next` + `@vercel/python`).**
Budowa **przechodziła** (`Build Completed in /vercel/output [28s]`, oba budowniczowie widoczne
w `deployment.builds`), ale funkcja Pythona **była nieosiągalna**: `/api/zdrowie`, `/api/index`
i `/api/plynnosc` zwracały stronę 404 Next.js. Próbowane w czterech wariantach: przepisanie
w `next.config.mjs` na `/api/index`, jawne `routes` w `vercel.json`, obie kolejności `builds`.
Trasy generowane przez `@vercel/next` przechwytują żądanie przed lambdą Pythona.
Po drodze wyszedł też błąd platformy niezwiązany z naszym kodem:

```
Cannot patch preview comments when immutable static file upload is enabled.
Upgrade to next@v16.3.0-canary.32 or newer to resolve this.
```

Obchodzi się go wyłączeniem komentarzy podglądowych (`enablePreviewFeedback: false`,
`enableProductionFeedback: false`) — zrobione na **obu** projektach, bo dotyczyłoby i tego
wdrożenia, które przeszło.

**Dowód, że wariant rozdzielony działa**, zanim cokolwiek dotknęło projektu finansowego —
wdrożenie próbne bez zmiennych bazy odpowiedziało kodem 500 z **naszym** zdaniem:

```
File "/var/task/api/index.py", line 95, in cykl_zycia
    magazyn.zmigruj()
File "/var/task/silnik/rdzen/magazyn.py", line 157, in _rozwiaz_adres
silnik.rdzen.magazyn.BladMagazynu: Nie wiem, ktora baze otworzyc: zmienna
srodowiskowa DATABASE_URL jest pusta albo jej nie ma.
```

Ścieżka `/var/task/silnik/rdzen/magazyn.py` dowodzi, że **silnik trafił do paczki funkcji
sam**, bez `includeFiles`.

---

## 3. Uchwyt cyklu życia — pytanie z W2 rozstrzygnięte pomiarem

Nośnik (zlecenie W6, punkt 3) mówił: **niezmierzone**, czy uchwyt biegnie raz na zimny start,
czy raz na wywołanie. Gdyby raz na wywołanie — migracja wróciłaby na ścieżkę żądania tylnymi
drzwiami (stan sprzed W2: 98 poleceń SQL, 59 piszących, na każde żądanie).

Do rozstrzygnięcia dołożone są do `/api/zdrowie` trzy liczniki (`pid`,
`uruchomien_cyklu_zycia`, `zadan_zdrowia_w_tym_procesie`). Osiem kolejnych żądań:

```
pid=4 cykl_zycia=1 zadan=6  ms_od_importu= 51796 region=fra1
pid=4 cykl_zycia=1 zadan=7  ms_od_importu= 52144 region=fra1
...
pid=4 cykl_zycia=1 zadan=13 ms_od_importu= 53387 region=fra1
```

**Uchwyt biegnie raz na proces.** Trzynaście żądań, jeden proces, jedno uruchomienie migracji.
Kontrola w drugą stronę: `kopii przed migracja (przestrzenie): 0` — migracja przy zimnym starcie
nie tworzy kopii, bo wersja bazy równa się wersji kodu (12).

**Pole `sekund_od_importu_modulu` musiało zejść na milisekundy jako liczba całkowita.**
Pierwsza wersja oddawała ułamek i wdrożenie odpowiedziało kodem 500:

```
TypeError: Liczba zmiennoprzecinkowa w odpowiedzi HTTP: $.sekund_od_importu_modulu
(przejrzano 9 lisci).
```

To zachowanie `api/kwoty.py` jest **poprawne i zostaje**; pole się do niego dostosowało.
Uboczny dowód: bramka kwot działa na produkcji, nie tylko w testach.

---

## 4. Pomiary wdrożonej funkcji

### 4.1 Zimny start — dług z W0 domknięty

| Co | Liczba | Metoda |
|---|---|---|
| **pierwsze żądanie po wdrożeniu** | **1,449 s** | świeże wdrożenie, oczekiwanie na `READY` przez interfejs programowy (bez dotykania funkcji), potem **jedno** żądanie |
| ciepłe żądanie | 0,328 s / 0,17–0,25 s | drugie żądanie i seria |
| **zimny start przy skalowaniu** | **2,80–3,12 s** | fala 12 równoległych żądań; 7 z 12 trafiło na instancje tworzone od zera |

W0 mierzyło lokalnie (M1/3.14): wykres importu 0,37 s ciepło, 1,09 s zimno. Wdrożona funkcja
dokłada pobranie paczki, połączenie z bazą i migrację.

**Pierwszy pomiar zimnego startu był zafałszowany i zostaje to zapisane.** Próba rozpoznania
świeżej instancji po `zadan_zdrowia_w_tym_procesie == 1` dała trzy „zimne starty" po 0,23 s
przy `milisekund_od_importu_modulu = 400 349` — sprzeczność, która obaliła metodę: licznik liczy
**tylko trasę zdrowia**, więc instancja żyjąca od 400 s, ale obsługująca dotąd wyłącznie
`/api/plynnosc`, wyglądała jak nowa.

### 4.2 Sesje do bazy — pula na razie niepotrzebna, ale pomiar ma nazwaną granicę

12 równoległych żądań, 31 próbek `pg_stat_activity`, **szczyt: 1 sesja** — i to była sesja
samego pomiaru. **Ten wynik NIE znaczy „funkcja nie bierze sesji".** Znaczy, że
`pg_stat_activity` odczytany **przez pulę Neona** nie widzi sesji innych klientów puli.
Etykieta: **liczba sesji funkcji — niezweryfikowana**, luka nazwana.

Co zmierzone naprawdę: 12 równoległych żądań **wszystkie odpowiedziały kodem 200**, żadne nie
padło na limicie połączeń. Przy aplikacji jednoosobowej to wystarcza.

**Rozstrzygnięcie: puli nie dokładamy teraz.** Próg powrotu: pierwsza odpowiedź z błędem
połączenia do bazy albo pierwszy pomiar pokazujący sesje narastające; miejsce jest nazwane
w `api/wspolne.py`.

### 4.3 Rozmiar

Vercel raportuje lambdę silnika jako **69,64 MB** (`vercel inspect`). W0 mierzyło 198,14 MB
niekompresowane przy limicie 500 MB. Zapas nietknięty.

**`uvicorn[standard]` (23,78 MB) i `pytest` (13,59 MB) zostają w `requirements.txt`** —
jednym zdaniem: przy 69,64 MB zbudowanej funkcji i limicie 500 MB oszczędność nie kupuje
niczego, a rozdzielenie pliku zależności kosztuje drugi nośnik wersji bibliotek.

---

## 5. Pętla odbiorcza — zmierzona na wdrożeniu

```
PUT  /api/kotwica  {"data":"2026-09-15","kwota":"10000.00"}   http=200
     saldoMinimalne = '10000.00'   werdykt: „najniżej masz 10 000,00 zł 15 września"
POST /api/wpisy    {"kwota":"500.00", typ Wydatki, Inne}      http=200  id=1
     saldoMinimalne '10000.00' -> '9500.00'      RÓŻNICA = 500.00
     saldo na 2026-09-15: '10000.00' -> '9500.00'  RÓŻNICA = 500.00
DELETE /api/wpisy/1                                            http=200  stan=wycofany
     saldoMinimalne '9500.00' -> '10000.00'      RÓŻNICA wobec stanu sprzed = 0.00
```

**Ta sama liczba co w nocy na środowisku lokalnym: 500,00 zł.**

### Kwota jest napisem po obu stronach granicy — sprawdzone na wdrożeniu

```
POST /api/wpisy {"kwota":"8623.10"}  ->  kwota w odpowiedzi = '8623.10' (typ str)
surowy JSON zawiera "8623.10": True
surowy JSON zawiera "8623.1":  False      <- wariant z W5 NIE występuje
liczb zmiennoprzecinkowych w surowym JSON: 0
```

Kontrola liczności na całej odpowiedzi `/api/plynnosc`: **122 liście przejrzane, 0 typu float**,
2 typu int.

### Forma opodatkowania — odczyt ze źródła autorytatywnego, nie ze zrzutu

```
adres bazy (bez hasla): ep-old-waterfall-b16ho6yq-pooler.c-5.eu-central-1.aws.neon.tech/neondb
wersja serwera: 18.6 | wersja schematu: 12 | tabel: 15
FORMA OPODATKOWANIA: [(2026, 'SKALA')]
kategorii: 24 | stawek w rejestrze: 19 | wpisow budzetu: 0
```

**SKALA, zgodnie z §2 konstytucji projektu.** Ryczałtu nie ma.

---

## 6. Znalezisko o wadze: ochrona SSO nie obejmuje adresu, pod którym się wchodzi

Nośnik (plan sesji, decyzja Darka godz. 10:3x) twierdzi: *„SSO Vercela wystarczy na teraz —
świadomy dług, nie przeoczenie"*. **Pomiar pokazuje, że SSO nie chroni adresu produkcyjnego
w ogóle** — ani przed odczytem, ani przed zapisem:

```
https://nordsignal-doradca-finansowy.vercel.app/                       http=200
https://nordsignal-doradca-finansowy-949s2pc45-...vercel.app/          http=302
https://nordsignal-doradca-silnik.vercel.app/api/zdrowie               http=200
https://nordsignal-doradca-silnik-o77p59isp-...vercel.app/api/zdrowie  http=302

PUT https://nordsignal-doradca-finansowy.vercel.app/api/kotwica        http=200
```

Ustawienie brzmi `ssoProtection: {"deploymentType": "all_except_custom_domains"}` i obejmuje
**adresy pojedynczych wdrożeń**, a nie adres produkcyjny projektu. Ostatnia linia jest
najcięższa: **zapis stanu konta przechodzi bez żadnego uwierzytelnienia.**

Dziś realnych danych nie ma (0 wpisów budżetu). Od chwili, w której Darek wpisze swoje liczby,
będą one dostępne dla każdego, kto zna adres.

**Nie naprawiam tego sama i to jest decyzja, nie przeoczenie.** Zamknięcie
(`deploymentType: "all"`) **zepsułoby aplikację**: przepisanie z interfejsu do silnika jest
żądaniem serwer-do-serwera i nie niesie sesji przeglądarki. Naprawa wymaga wyboru drogi —
patrz raport, pozycja dla Darka.

---

## 7. Co zostało zmienione w repozytorium

| Plik | Zmiana | Dlaczego |
|---|---|---|
| `api/index.py` | `app = aplikacja`; liczniki cyklu życia; cztery pola pomiarowe w `/api/zdrowie` | wymaganie platformy + rozstrzygnięcie pytania z W2 |
| `api/__init__.py` | **nowy** | pakiet zwykły zamiast pakietu przestrzeni nazw |
| `vercel.json` | **nowy**, w korzeniu | konfiguracja projektu silnika: `maxDuration`, region `fra1`, przepisanie `/api/(.*)` |
| `interfejs/vercel.json` | **nowy** | region `fra1` dla lambd Next |
| `interfejs/next.config.mjs` | rozgałęzienie lokalne/platforma; adres ze zmiennej; przerwanie budowy przy braku zmiennej | jeden nośnik adresu silnika |
| `.vercelignore` | **nowy** | wdrożenie z wiersza poleceń nie wysyła `.venv`, `node_modules`, testów i dokumentów |
| `testy/test_wejscie_platformy.py` | **nowy**, 4 strażniki | trzy miejsca, w których błędna zmiana nie dawała żadnego sygnału |

Poza repozytorium (konto Vercela): nowy projekt `nordsignal-doradca-silnik`, zmienna
`ADRES_SILNIKA` w projekcie interfejsu, region `fra1` na obu projektach, komentarze podglądowe
wyłączone na obu, **projekt `probnik-silnik-python` skasowany**.

---

## 8. Strażnicy i ich mutacje (§3.8)

Kopia drzewa poza repozytorium; kontrola przed: `4 passed`.

| Mutacja | Który test padł | Wynik |
|---|---|---|
| `app = FastAPI()` zamiast `app = aplikacja` | `test_app_JEST_TYM_SAMYM_obiektem_co_aplikacja` | 1 failed, 3 passed |
| usunięty `maxDuration` z `vercel.json` | `test_funkcja_silnika_MA_JAWNY_limit_czasu` | 1 failed, 3 passed |
| `regions: ["iad1"]` | `test_funkcja_silnika_STOI_W_UNII` | 1 failed, 3 passed |
| adres wdrożenia wpisany na sztywno w osobnej stałej | `test_konfiguracja_next_NIE_NIESIE_adresu_silnika_na_sztywno` | **najpierw 4 passed — strażnik był atrapą**; po wzmocnieniu 1 failed, 3 passed |

Kontrola po cofnięciu wszystkich: `4 passed`.

**Czwarta pozycja jest tu najważniejsza.** Pierwsza wersja strażnika sprawdzała wyłącznie linie
zawierające `CEL_PRZEPISANIA`, `destination` albo `ADRES_SILNIKA =`. Mutacja wpisująca adres do
**osobnej stałej** (`const _CEL = "https://...vercel.app"`) przeszła na zielono. Wzorzec „lista
nazw, których ktoś użyje" zakłada wiedzę, której nie mamy. Wzmocnienie: żaden literał
`.vercel.app` w kodzie — ceną jest komunikat błędu bez przykładowego adresu.

---

## 9. Czego to zadanie NIE objęło

| Nieobjęte | Skutek |
|---|---|
| **Pasek nawigacji** — 9 z 9 odsyłaczy nadal daje 404 | W7, Jack. Aplikacja ma dziś dwa działające ekrany: `/` i `/ksiegowanie` |
| **Pole na stan konta w interfejsie** | W8, Jack. Trasa `PUT /api/kotwica` stoi i została zmierzona |
| **Ekran Budżet** | W9 |
| **Klucz modelu językowego** (`AI_GATEWAY_API_KEY` vs `GEMINI_API_KEY`) | rozjazd potwierdzony, nienaprawiony — doradca nie wchodzi w pętlę W6; żadnej zmiennej klucza nie ma dziś w żadnym projekcie |
| **Liczba sesji funkcji do bazy** | niezweryfikowana — pula Neona ukrywa je przed `pg_stat_activity` |
| **Czysty zimny start** (pobranie paczki + import + migracja, bez narzutu trasowania) | mierzone pośrednio: 2,80–3,12 s przy skalowaniu |
| **Synchronizacja repozytorium produktu** | projekt Vercela jest podpięty do `Danolog/nordsignal-doradca-finansowy` (osobne repozytorium, ostatni push 08:13Z). Wdrażałam **z wiersza poleceń**, pomijając gita. Zmiany z tej sesji trzeba tam wypchnąć, inaczej pierwsze wdrożenie z gita zbuduje wersję sprzed W6 |
| **Wygląd ekranów po wdrożeniu** | porównanie z ramkami robione było lokalnie; na wdrożeniu nieporównane |

**Ile rzeczy pomiar widział:** 7 tras odpytanych i 7 odpowiedzi 200 · 122 liście odpowiedzi
płynności · 13 żądań do jednego procesu funkcji · 12 żądań równoległych · 31 próbek
`pg_stat_activity` · 15 tabel i 24 kategorie odczytane z bazy · 4 mutacje · 1019 testów.

---

## 10. Ślad operacji na koncie Vercela

| Co | Stan |
|---|---|
| `nordsignal-doradca-silnik` | **utworzony**, produkcyjny, `fra1`, 2 zmienne (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`) |
| `nordsignal-doradca-finansowy` | region `fra1`, dodana `ADRES_SILNIKA`, wyłączone komentarze podglądowe, **katalog główny bez zmian** (`interfejs`) |
| `probnik-silnik-python` | **skasowany** (HTTP 204; adres odpowiada 404) |
| `skill-bridge-ai`, `my-helper-2` | **nietknięte** |
| Ochrona SSO | **nigdzie nie zdjęta ani nie zmieniona** |
| Wydatek | **zero**. Plan `hobby` bez zmian; nic nie proponowało płatnego planu. Region `fra1` na planie hobby przeszedł bez ostrzeżenia |
| Baza produkcyjna | 3 wpisy dodane i **wszystkie 3 wycofane** (`wpisow budzetu: 0`); **1 odczyt stanu konta zostaje** — 10 000,00 zł na 2026-09-15, wartość pomiarowa |
| Dane robocze Darka | `~/Dane-robocze-doradca-finansowy/` **nietknięte, niekopiowane** |

**Kasowanie próbnika — co przez to przestało działać (pomiar przed akcją):** zmiennych
środowiskowych **0**, powiązania z repozytorium **brak**, własnych domen **brak**, wdrożeń 10,
adres zwracał 500. Utracona zdolność: **miejsce do sprawdzania konfiguracji wdrożenia bez
ryzyka dla projektu produkcyjnego**. Następca: utworzenie nowego projektu-próbnika kosztuje
jedno wywołanie interfejsu programowego. Nic poza tym.

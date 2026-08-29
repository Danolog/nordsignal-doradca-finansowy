# Pomiar W0 — czy silnik Pythona mieści się w funkcji Vercela

**Wersja:** v1.0 · 2026-08-29 · autor: Eva (Platform/DevOps) · gałąź `noc-2026-08-29`, głowa `d0d53e2`
**Charakter dokumentu:** pomiar. Nic w kodzie aplikacji nie zostało zmienione.

---

## 0. Werdykt

**MIEŚCI SIĘ.** Paczka zależności silnika waży **198,14 MB** po kompilacji bajtkodu (tak, jak
robi to Vercel) przy limicie **500 MB** dla funkcji Pythona. Zajęte **39,6 %** limitu.
Budowa na Vercelu **przeszła** — próbnik z pełnym kompletem zależności zbudował się w 8 sekund.

**Ale nie zbuduje się dziś**, z dwóch powodów niezwiązanych z rozmiarem — oba zmierzone niżej
(§6): nazwa obiektu ASGI i katalog główny projektu.

---

## 1. Nośniki sprawdzone PRZED pomiarem (§3.10)

| Nośnik | Co twierdzi | Odczytany |
|---|---|---|
| `docs/plan-chmura-2026-08-29.md`, W0 | „**pandas 72 MB + numpy 34 MB**" | tak |
| `docs/PRD.md` §17 poz. 4 | „platforma obsługuje Python natywnie, ale **nie zmierzyłem** czasu zimnego startu ani rozmiaru paczki" | tak |
| `docs/PRD.md` §18 poz. 3 | „Cała architektura stoi na założeniu, że Python z tymi zależnościami zmieści się w funkcji." | tak |
| `requirements.txt` | 10 pozycji, w tym 2 testowe; `numpy` **nie stoi wprost** | tak |
| `vercel.json` w korzeniu | **nie istnieje** | tak |
| `interfejs/next.config.mjs` | przepisanie `/api/:sciezka*` na `http://127.0.0.1:8000` — **adres lokalny, wpisany na sztywno** | tak |

**Nośnik twierdzi X, pomiar pokazuje Y:**

| Rzecz | Nośnik (plan W0) | Pomiar (2026-08-29) | Różnica |
|---|---|---|---|
| pandas | 72 MB | **39,52 MB** | nośnik zawyża o 82 % |
| numpy | 34 MB | **28,60 MB** + `numpy.libs` **28,35 MB** = **56,95 MB** | nośnik zaniża o 68 % |
| numpy w `requirements.txt` | — | **nie ma go wprost**; wchodzi jako zależność pandas, wersja **2.5.2** | — |
| razem pandas+numpy | 106 MB | **96,47 MB** | zbliżone przypadkiem — obie składowe błędne w przeciwne strony |

Nośnik pominął `numpy.libs` — katalog z bibliotekami natywnymi (25,21 MB to jeden plik
`libscipy_openblas64_*.so`), czyli **najcięższy pojedynczy element całej paczki**.

---

## 2. Rozmiar paczki — pomiar

Metoda: instalacja kół (ang. *wheels*) dla **Linux x86_64 / CPython 3.12**, czyli tego, na czym
faktycznie stoi funkcja Vercela — nie dla macOS, na którym pracuję.

```
pip install --target paczka-linux \
  --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 \
  --python-version 3.12 --implementation cp --only-binary=:all: --no-compile -r req-prod.txt
```

Wyjście (ostatnia linia):

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.14.2 certifi-2026.7.22
click-8.5.0 et-xmlfile-2.0.0 fastapi-0.141.1 h11-0.16.0 httpcore-1.0.9 httptools-0.8.0
httpx-0.28.1 idna-3.19 numpy-2.5.2 openpyxl-3.1.5 pandas-3.0.5 psycopg-3.2.11
psycopg-binary-3.2.11 psycopg-pool-3.3.1 pydantic-2.12.4 pydantic-core-2.41.5
python-dateutil-2.9.0.post0 python-dotenv-1.2.1 pyyaml-6.0.3 six-1.17.0 starlette-1.6.0
typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.42.0 uvloop-0.22.1 watchfiles-1.2.0
websockets-17.1
```

### 2.1 Cztery warianty, zmierzone

```
find <katalog> -type f -exec stat -f %z {} \; | awk '{s+=$1;n++} END {printf "plikow=%d MB=%.2f\n", n, s/1000000}'
```

| Wariant | Bez bajtkodu | **Z bajtkodem** (tak liczy Vercel) | ZIP -9 | plików |
|---|---|---|---|---|
| **A** — dokładnie `requirements.txt` z repo (**z pytest**) | 151,83 MB | **211,73 MB** | — | 4 053 → 7 119 |
| **B** — bez zależności testowych | 145,24 MB | **198,14 MB** | **42,80 MB** | 3 549 → 6 162 |
| **C** — B minus `uvicorn[standard]` (Vercel woła ASGI wprost) | 121,46 MB | **172,16 MB** | 36,19 MB | 3 283 → 5 752 |
| **D** — C minus pandas i numpy | 24,10 MB | — | — | 814 |

Cytaty wyjścia:

```
=== SUMA BAJTOW RZECZYWISTA (bez dopelnienia blokow) ===
plikow=3549  bajtow=145244154  MB=145.24  MiB=138.52

=== PO KOMPILACJI BAJTKODU (tak robi Vercel: 'Compiling Python bytecode...') ===
plikow=6162  MB=198.14
=== ile plikow .pyc dolozono ===
    2613
pyc MB=52.89

=== WARIANT A + bajtkod (dokladnie requirements.txt z repo) ===
plikow=7119  MB=211.73
=== WARIANT C + bajtkod (bez uvicorn[standard], bez pytest) ===
plikow=5752  MB=172.16

ZIP -9: 42798279 bajtow = 42.80 MB = 40.82 MiB
```

### 2.2 Rozbicie na pakiety (wariant B, bez bajtkodu)

```
    39.516 MB   1516 plikow  pandas
    28.604 MB    902 plikow  numpy
    28.348 MB      3 plikow  numpy.libs
    16.364 MB     57 plikow  uvloop
    10.950 MB     14 plikow  psycopg_binary.libs
     5.088 MB      5 plikow  pydantic_core
     2.897 MB     18 plikow  yaml
     1.790 MB     15 plikow  httptools
     1.751 MB    107 plikow  pydantic
     1.158 MB      7 plikow  psycopg_binary
     1.149 MB     10 plikow  watchfiles
     0.844 MB    190 plikow  openpyxl
     0.816 MB     56 plikow  websockets
     0.789 MB     56 plikow  fastapi
     0.685 MB     84 plikow  psycopg
```

Największe pojedyncze pliki:

```
   25.21 MB  numpy.libs/libscipy_openblas64_-61654e39.so
   15.95 MB  uvloop/loop.cpython-312-x86_64-linux-gnu.so
   10.63 MB  numpy/_core/_multiarray_umath.cpython-312-x86_64-linux-gnu.so
    6.50 MB  psycopg_binary.libs/libcrypto-60d8fe35.so.3
    4.88 MB  pydantic_core/_pydantic_core.cpython-312-x86_64-linux-gnu.so
```

Kod własny aplikacji dokłada do tego **0,478 MB**:

```
silnik   plikow= 25  MB=0.420
api      plikow=  6  MB=0.027
wiedza   plikow=  6  MB=0.031
```

### 2.3 Kontrola niezależna — z maszyny Vercela

Vercel po zbudowaniu próbnika zapisał pamięć podręczną budowy:

```
2026-08-29T09:23:45.858Z  Uploading build cache [45.14 MB]
```

45,14 MB skompresowane wobec moich 42,80 MB — pamięć podręczna niesie dodatkowo pliki `.pyc`.
Rozbieżność 5 % w oczekiwaną stronę; pomiar lokalny się potwierdza.

### 2.4 Znalezisko przy okazji: pandas 3.0.5 wymaga nowszego Linuksa

Pierwsza próba (`--platform manylinux2014_x86_64`, glibc 2.17) **nie znalazła pandas 3.0.5**:

```
ERROR: Could not find a version that satisfies the requirement pandas==3.0.5
(from versions: 2.1.1, ..., 2.3.2)
```

Po zmianie na `manylinux_2_28_x86_64` (glibc 2.28) pandas 3.0.5 jest dostępny dla 3.12, 3.13 i 3.14.
Wniosek: pandas 3.0.5 wymaga glibc ≥ 2.28. Obraz budujący Vercela to spełnia — budowa przeszła
(§4). **Gdyby projekt kiedykolwiek zszedł na starszy obraz — pandas 3.0.5 zniknie z dostępnych.**

---

## 3. Limit Vercela — źródło i plan

**Plan zespołu — zmierzony, nie założony:**

```
curl -H "Authorization: Bearer $TOK" https://api.vercel.com/v2/teams
team: team_qnWb1456DZTUNonmsMg7qnvz dareks-projects-da398fc0 plan= hobby
```

**Tryb obliczeń — Fluid Compute WŁĄCZONY:**

```
curl .../v9/projects/nordsignal-doradca-finansowy
defaultResourceConfig = {"fluid": true, "functionDefaultRegions": ["iad1"],
  "functionDefaultTimeout": 300, "functionDefaultMemoryType": "standard", ...}
resourceConfig = {"fluid": true, "functionDefaultRegions": ["iad1"], ...}
```

**Limit — z dokumentacji Vercela** (`https://vercel.com/docs/functions/limitations`,
strona oznaczona „Last updated August 24, 2026", nagłówek tabeli: *„limits ... of using Vercel
Functions with Fluid compute"*), odczyt 2026-08-29:

> Size (uncompressed) **250 MB, or 500 MB for Python**. Large functions support up to 5 GB (Beta).

> For Vercel Functions, the maximum uncompressed size is 250 MB including layers ...
> **For Python functions, the maximum uncompressed size is 500 MB.**

**Limitu skompresowanego dokumentacja nie podaje.** Szukanie słów „compressed" i „zipped" na tej
stronie dało 4 + 2 trafienia i **żadne** nie ustanawia progu dla paczki spakowanej — wszystkie
mówią o `uncompressed` / `unzipped`. Wartość ZIP (42,80 MB) podaję więc jako liczbę pomocniczą,
**nie jako pomiar wobec progu**.

**Rozróżnienie planów:** tabela limitów różnicuje po planie **pamięć** (Hobby 2 GB) i **czas**
(Hobby 300 s), a **rozmiaru nie różnicuje** — 500 MB dla Pythona stoi bez przypisu o planie.
Potwierdza to wpis w dzienniku zmian z 24 II 2026:

> The bundle size limit for Vercel Functions using the Python runtime is now 500MB, increasing
> the maximum uncompressed deployment bundle size from 250MB.

**Wersja Pythona** (`https://vercel.com/docs/functions/runtimes/python`): „The available versions
are: **3.12 (default)**, 3.13, 3.14". Zmierzone na maszynie budującej: `Python 3.12.14`.

---

## 4. Budowa na Vercelu — próbnik przeszedł

Próbnik: minimalna funkcja FastAPI z **całym** kompletem zależności produkcyjnych,
osobny projekt `probnik-silnik-python`, wdrożenie podglądowe.

```
2026-08-29T09:23:07.766Z  Using Python 3.12 from .python-version
2026-08-29T09:23:07.812Z  Using uv 0.10.11
2026-08-29T09:23:07.813Z  Creating virtual environment at "/vercel/path0/.vercel/python/.venv"...
2026-08-29T09:23:08.140Z  Installing required dependencies from requirements.txt...
2026-08-29T09:23:09.845Z  Compiling Python bytecode...
2026-08-29T09:23:16.008Z  Build Completed in /vercel/output [8s]
2026-08-29T09:23:39.899Z  Deployment completed
2026-08-29T09:23:45.858Z  Created build cache / Uploading build cache [45.14 MB]
```

Instalacja objęła 31 pakietów, w tym `pandas==3.0.5`, `numpy==2.5.2`, `psycopg-binary==3.2.11`.
**Żadnego ostrzeżenia o rozmiarze. Żadnego błędu.**

---

## 5. Zimny start

### 5.1 Co zmierzone

Maszyna: Apple M1, arm64, macOS. Interpreter: CPython 3.14.6 (środowisko `.venv` projektu).
Bufor systemu plików **ciepły**. Pięć przebiegów, osobny proces każdy.

```
=== narzut startu interpretera (5x, s) ===
0.03 0.02 0.02 0.02 0.02

=== import calego kompletu poza psycopg (5x, s) ===
1.0869 0.418 0.4034 0.3964 0.3961

=== import api.index (aplikacja) — 5x, s ===
0.392 0.3731 0.3741 0.3705 0.3782
```

Rozbicie na moduły (`python -X importtime`, mikrosekundy, 5 przebiegów):

```
pandas:  449481 219118 266548 220567 217151
numpy:    35000  34817  34874  37871  34982
fastapi: 220793 148917 147200 160229 157992
openpyxl:114375  95690  87535  86683  87252
silnik.rdzen.magazyn: 260321 229305 228811 229981 227647
```

**Odczyt:** cały wykres importu aplikacji — `from api.index import aplikacja`, czyli FastAPI +
pandas + numpy + silnik — kosztuje **0,37 s** przy ciepłym buforze, z czego **0,22 s** to pandas.
Pierwszy przebieg (zimny bufor pliku) daje **1,09 s** — i to jest liczba bliższa temu, co robi
funkcja przy zimnym starcie.

Na maszynie budującej Vercela (x86_64 Linux, CPython 3.12.14) zmierzono narzut samego
interpretera: `NARZUT_STARTU_INTERPRETERA_S: 0.0108`.

### 5.2 Czego NIE zmierzono — i dlaczego

**Zimnego startu wdrożonej funkcji nie zmierzyłem. Etykieta: NIEZWERYFIKOWANE.**

Funkcja jest zbudowana i gotowa, ale **ochrona wdrożenia (SSO) odsyła każde żądanie zanim
funkcja zostanie wywołana**:

```
curl -w "http=%{http_code} total=%{time_total}s" https://probnik-silnik-python-nrnnzq7a7-...vercel.app/api/pomiar
http=302 total=0.322499s ttfb=0.320898s
Redirecting...
```

Zdjęcie ochrony — nawet na projekcie-próbniku, który **nie ma ani jednej zmiennej środowiskowej**
(pomiar: `liczba zmiennych: 0`, `nazwy: []`) i żadnego dostępu do bazy — leży poza moim mandatem.
Nie zrobiłem tego. Pozycja dla Darka: §8.

Próba obejścia przez pomiar na maszynie **budującej** Vercela (ten sam Linux x86_64, te same koła)
padła na artefakcie środowiskowym: `uv` włożył do środowiska 3.12 koło numpy zbudowane dla 3.14
(`_multiarray_umath.cpython-314-x86_64-linux-gnu.so`). To wada mojego próbnika, **nie** dowód
czegokolwiek o aplikacji; projekt pomiarowy skasowałem.

### 5.3 Co z tego wynika mimo braku liczby

Zimny start funkcji Pythona z paczką 198 MB to (a) pobranie i rozpakowanie paczki przez platformę,
(b) `import` wykresu modułów. Składnik (b) zmierzony: 0,37 s ciepło / 1,09 s zimno na M1.
Składnik (a) — **niezmierzony**. Rząd wielkości sumy jest **sekundowy, nie milisekundowy**,
i to jest istotne przy pytaniu „czy pierwsze wejście na ekran ma czekać".

---

## 6. Dwa blokery, które zatrzymają wdrożenie ZANIM rozmiar zacznie mieć znaczenie

### 6.1 Obiekt ASGI nazywa się `aplikacja`, a Vercel wymaga `app`

Zmierzone — próbnik z obiektem nazwanym jak w repo **odmówił budowy**:

```
Error: Found api/index.py but it does not define a top-level "app" FastAPI instance.
```

W repo (`api/index.py:53`):

```
53:aplikacja = FastAPI(title="Doradca Finansowy", default_response_class=OdpowiedzJSON)
```

Po dopisaniu `app = FastAPI()` budowa przeszła. Koszt naprawy: **jedna linia aliasu**.
Uwaga językowa: reguła §4 konstytucji projektu każe nazywać po polsku — tu nazwa `app` jest
**wymaganiem platformy**, nie wyborem stylu; alias `aplikacja = app` zachowuje obie strony.

### 6.2 Katalog główny projektu Vercela to `interfejs/` — silnik jest poza jego zasięgiem

```
curl .../v9/projects/nordsignal-doradca-finansowy
rootDirectory = "interfejs"
framework = "nextjs"
```

Vercel widzi **wyłącznie** `interfejs/`. Katalog `api/`, katalog `silnik/` i `requirements.txt`
leżą **poza** katalogiem głównym projektu, więc funkcja Pythona nie zostanie ani znaleziona,
ani zbudowana. Kontrola: `find interfejs -name "*.py"` → **zero plików**.

### 6.3 Znalezisko trzecie: zła konfiguracja **nie daje błędu**, tylko ciszę

Pierwsze wdrożenie próbnika miało `vercel.json` z `{"framework": null}`. Budowa zakończyła się
**sukcesem** w 20 ms, nie budując żadnej funkcji:

```
2026-08-29T...  Build Completed in /vercel/output [20ms]
2026-08-29T...  Deployment completed
```

`vercel inspect` pokazał `Builds: . [0ms]` — zero funkcji. Wdrożenie było „zielone" i puste.
To ta sama klasa awarii co strażnik-atrapa: **melduje sukces, nie zrobiwszy nic**.

---

## 7. Znaleziska poboczne (zapisane, nienaprawione — W0 niczego nie zmienia)

1. **`psycopg` jest w `requirements.txt`, a w kodzie nie ma ani jednego użycia.**
   `grep -rn "psycopg" silnik api wiedza migracja` → zero trafień. Waży 12,79 MB
   (`psycopg_binary.libs` 10,95 + `psycopg_binary` 1,16 + `psycopg` 0,69). Będzie potrzebny
   po W4 (podmiana sterownika) — dziś jest długiem, nie wadą.
2. **`uvicorn[standard]` waży 23,78 MB i na Vercelu jest zbędny** — platforma woła obiekt ASGI
   bezpośrednio, serwera nie uruchamia. `uvloop` sam to 16,36 MB. Zostaje potrzebny lokalnie.
3. **`pytest` w `requirements.txt`** dokłada 13,59 MB do paczki funkcji (211,73 vs 198,14 MB).
4. **Region funkcji to `iad1` — Waszyngton, USA.** Baza Neon stoi w `aws-eu-central-1`
   (Frankfurt). Każde zapytanie do bazy przechodzi przez Atlantyk w obie strony. To jest
   jednocześnie pozycja dla Ryana (dane finansowe przetwarzane poza UE) i pozycja wydajnościowa.
   `serverlessFunctionRegion = "iad1"`, `functionDefaultRegions: ["iad1"]`.
5. **`interfejs/next.config.mjs` przepisuje `/api/*` na `http://127.0.0.1:8000`** — adres lokalny
   wpisany na sztywno, bez rozgałęzienia na środowisko. W chmurze to przepisanie prowadzi donikąd.
6. **`_KWOTOWE` ma 9 tabel i 16 kolumn**, nie 17 jak mówi zlecenie:
   ```
   tabel: 9
   kolumn (wszystkie napisy minus nazwy tabel): 16
   ```

---

## 8. Pozycja dla Darka — jedna

**Czego potrzeba:** zgody na jednorazowe zdjęcie ochrony SSO **na projekcie-próbniku**
`probnik-silnik-python` (osobny projekt, zero zmiennych środowiskowych, zero dostępu do bazy,
zawartość: jedna funkcja zwracająca czasy importu) — albo, prościej, otwarcia w przeglądarce
adresu:

`https://probnik-silnik-python-nrnnzq7a7-dareks-projects-da398fc0.vercel.app/api/pomiar`

**Po co:** to jedyny brakujący pomiar bramki W0 — czas zimnego startu wdrożonej funkcji.
Wszystko poza nim jest zmierzone.

**Co się bez tego nie wydarzy:** werdykt „mieści się" zostaje w mocy (rozstrzyga go rozmiar, a ten
jest zmierzony), ale **decyzja o tym, czy użytkownik czeka sekundę czy pięć na pierwszym wejściu**,
zostanie podjęta bez liczby. Projekt finansowy `nordsignal-doradca-finansowy` **nie jest** i nie
ma być tą operacją dotknięty.

**Po pomiarze:** projekt `probnik-silnik-python` do skasowania. Co przez to przestanie działać:
nic — nie ma zmiennych, danych ani odbiorców.

---

## 9. Drogi wyjścia — nie są potrzebne do zmieszczenia się, ale mają cenę wpisaną tutaj

Werdykt to „mieści się", więc poniższe **nie są** wymuszone rozmiarem. Wchodzą w grę tylko wtedy,
gdy zmierzony (§8) zimny start okaże się nie do przyjęcia.

### Droga 1 — chudsza paczka bez ruszania architektury

Zdjęcie `pytest` i `uvicorn[standard]` z paczki funkcji: **211,73 → 172,16 MB** (−18,7 %).
Koszt: rozdzielenie `requirements.txt` na produkcyjny i testowy. Godziny, nie dni.
**Co przestanie działać:** uruchomienie testów z tego samego pliku zależności; lokalny start przez
`uvicorn` wymaga wtedy drugiego pliku.

### Droga 2 — zdjęcie `pandas` ze ścieżki żądania

Zmierzony zasięg (`grep -c` na plikach silnika):

| Plik | linii | `pd.` | `DataFrame` | `Series` | `.loc/.iloc/.iterrows` |
|---|---|---|---|---|---|
| `silnik/rdzen/budzet.py` | 672 | 20 | 19 | 0 | 13 |
| `silnik/ekran_ksiegowanie.py` | 613 | 11 | 10 | 0 | 4 |
| `silnik/rdzen/prognoza_plynnosci.py` | 922 | 2 | 0 | 0 | 3 |
| `silnik/rdzen/magazyn.py` | 2270 | 15 | 11 | 2 | 1 |
| `silnik/rdzen/majatek.py` | 92 | 3 | 3 | 0 | 0 |
| **razem** | **4569** | **51** | **43** | **2** | **21** |

Plus **16 z 58 plików testowych** dotyka `pandas` lub `DataFrame` (`grep -rln` → 16, `ls testy/*.py`
→ 58). Zysk: paczka **121,46 → 24,10 MB** bez bajtkodu (wariant D; z bajtkodem **nie zmierzone**),
a zimny start traci najcięższy składnik.

**Co przestanie działać:** `pd.read_sql` znika, a razem z nim **automatyczna normalizacja odczytu**,
na której stoi konstrukcja `_KWOTOWE` (9 tabel, 16 kolumn) wymuszająca `Decimal`. Wymuszanie
`Decimal` trzeba wtedy napisać od nowa na krotkach sterownika — to jest **ścieżka kwoty**, czyli
dokładnie ten kawałek, którego wada „gubi grosze i zwraca 200" (§3.1 konstytucji projektu).
Przepisania wymaga ok. **4 600 linii silnika i 16 plików testowych**. To nie jest tanie i nie jest
bezpieczne bez strażników z W3.

### Droga 3 — osobny host dla silnika, interfejs zostaje na Vercelu

Szew istnieje: `interfejs/lib/dane/warstwa-sieciowa.ts:28`

```
const ADRES_SERWEROWY = process.env.ADRES_SILNIKA ?? "http://127.0.0.1:8000";
```

Bezpłatny wariant w UE **istnieje** — Render, plan Free, region **Frankfurt**
(`https://render.com/docs/regions`, odczyt 2026-08-29: „Oregon, USA · Ohio, USA · Virginia, USA ·
**Frankfurt, Germany** · Singapore"). Jego zmierzony koszt (`https://render.com/docs/free`):

> Render spins down a Free web service that goes 15 minutes without receiving any inbound traffic.
> ... A Free web service spins back up whenever it next receives an HTTP request ...
> **This process takes about one minute.**

Czyli darmowy host w UE **zamienia zimny start sekundowy na minutowy** — dla aplikacji używanej
kilka razy dziennie to zmiana na gorsze, nie na lepsze. Dodatkowo:

> any changes to your web service's filesystem (uploaded images, **local SQLite databases**, etc.)
> are lost every time the service redeploys, restarts, or spins down

**Co przestanie działać:** jeden adres dla wszystkiego (dochodzi konfiguracja CORS i drugi sekret),
ochrona SSO Vercela **przestaje obejmować silnik** — trzeba go zabezpieczyć osobno, a to jest
dziś jedyna rzecz stojąca między finansami a publicznym internetem. Zysk: region UE zamiast
`iad1` i brak limitu rozmiaru.

### Droga 4 — zmiana regionu funkcji na `fra1` (moja, spoza listy)

Najtańsza rzecz z tej listy: `functionDefaultRegions` z `iad1` na `fra1`. Zdejmuje przelot przez
Atlantyk do bazy i wyprowadza przetwarzanie danych finansowych do UE.
**Co przestanie działać:** nic zmierzonego. Wymaga decyzji, nie przepisania kodu.

---

## 10. Czego ten pomiar NIE objął (§ kontrola liczności)

| Nieobjęte | Skutek |
|---|---|
| **Zimny start wdrożonej funkcji** | najważniejsza brakująca liczba; przyczyna: SSO (§5.2). NIEZWERYFIKOWANE |
| **Czas pobrania i rozpakowania paczki przez platformę** | mierzony byłby razem z powyższym |
| Interpreter 3.12 na x86_64 przy pomiarze importu | mierzyłam na 3.14/arm64; różnica nieznana, kierunek nieznany |
| Wielkość `.pyc` dla 3.12 | kompilowałam 3.14; `.pyc` różnią się między wersjami o pojedyncze procenty — **nie zmierzone** |
| Narzut samej platformy w paczce (obsługa Vercela, warstwy AWS) | dokumentacja mówi „including layers"; ile to jest — nie zmierzone. Margines do 500 MB wynosi 302 MB, więc nie zmienia werdyktu |
| Czy funkcja **działa** po zbudowaniu | zbudowała się; **nie została ani razu wywołana** |
| Zachowanie przy `maxDuration` i limicie pamięci 2 GB | poza zakresem W0 |
| `interfejs/` i 11 lambd Next.js | nietknięte; pomiar dotyczył wyłącznie funkcji Pythona |
| Realne dane Darka | `~/Dane-robocze-doradca-finansowy/` nietknięte, niekopiowane |

**Ile rzeczy pomiar widział:** 3 549 plików / 145 244 154 bajty (wariant B bez bajtkodu),
6 162 pliki / 198,14 MB po bajtkodzie, 31 zainstalowanych pakietów, 4 warianty paczki,
1 zbudowane wdrożenie próbne, 0 wywołań funkcji.

---

## 11. Ślad operacji na koncie Vercela

| Co | Stan |
|---|---|
| `probnik-import-linux` | utworzony i **skasowany** (`Success! Project probnik-import-linux removed [689ms]`) |
| `probnik-silnik-python` | **istnieje**, wdrożenie podglądowe `dpl_GDDGVc7eZmxwSKSC59ZQgtyFQ52T`, zero zmiennych środowiskowych; do skasowania po pomiarze z §8 |
| `nordsignal-doradca-finansowy` | **nietknięty** — zero zmian ustawień, zero wdrożeń |
| `skill-bridge-ai`, `my-helper-2` | **nietknięte** |
| Ochrona SSO | **nigdzie nie zdjęta** |
| Wydatek | **zero**. Plan `hobby` bez zmian; nic nie proponowało płatnego planu |
| Repozytorium | **zero zmian w kodzie**; ten plik to jedyny nowy plik |

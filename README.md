# Doradca Finansowy

Osobisty doradca finansowy dla jednoosobowej działalności gospodarczej w Polsce — **skala
podatkowa, pełny ZUS, VAT memoriałowo**. Odpowiada na trzy pytania: *czy mam pieniądze*,
*co mnie zaraz uderzy*, *co mam z tym zrobić*.

**Stan: szkielet.** Rejestr stawek działa i jest sprawdzony; ekrany i silnik do zbudowania.

## Od czego zacząć czytanie

| Plik | Co niesie |
|---|---|
| `CLAUDE.md` | konstytucja projektu — nastawy i jedenaście reguł twardych |
| `docs/PRD.md` | **wymagania** — co ma robić i po czym poznać, że skończone |
| `docs/plan-wydawania.md` | **kolejność prac** — sześć plasterków |
| `makiety/*.dc.html` | **wiążąca specyfikacja wyglądu i zakresu** — 41 ramek |
| `testy/MUTACJE.md` | dowód, że strażnicy potrafią się zaczerwienić |

## Uruchomienie

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # uzupełnij DATABASE_URL i AI_GATEWAY_API_KEY
./.venv/bin/python -m pytest testy/ -q

cd interfejs && npm install
node narzedzia/buduj-palete.mjs    # paleta.css powstaje z makiety/paleta.json
npm run dev
```

Backend osobno: `./.venv/bin/uvicorn api.index:aplikacja --reload` — migrację bazy robi
uchwyt startowy aplikacji. Ręcznie, bez stawiania serwera:
`./.venv/bin/python -m silnik.rdzen.magazyn`.

`magazyn.polacz()` **tylko otwiera** bazę i odmawia otwarcia bazy niezmigrowanej — schemat
stawia wyłącznie `magazyn.zmigruj()` (W2, 2026-08-29).

## Układ

```
silnik/     rachunek — Decimal, zero stawek w kodzie
wiedza/     rejestr stawek + czujka aktów prawnych (ELI, GUS)
api/        trasy HTTP — cienka warstwa, zero rachunku
interfejs/  Next.js; barwy WYŁĄCZNIE ze zmiennych generowanych z palety
makiety/    ramki + narzędzia pomiarowe (kontrast, miara)
testy/      strażnicy + ślad mutacji
migracja/   przeniesienie z SQLite z bramką dwóch liczb
```

## Trzy rzeczy, które łatwo złamać nieświadomie

1. **Kwota jako liczba zmiennoprzecinkowa.** `silnik/pieniadz.zabron_float` odmawia. Poprzednia
   aplikacja gubiła grosze i **zwracała 200**.
2. **Stawka wpisana w kod.** Każda liczba z ustawy mieszka w rejestrze, z podstawą prawną i podpisem.
   Automat **proponuje**, człowiek zatwierdza.
3. **Ryczałt.** Darek jest na **skali**. Słowo „ryczałt" wolno tu zobaczyć wyłącznie jako opcję
   w porównaniu form i jako wiedzę o prawie — każda inna rola jest wadą.

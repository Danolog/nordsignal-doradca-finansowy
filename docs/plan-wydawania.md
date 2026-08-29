# Doradca Finansowy — plan wydawania

**Wersja:** v1.0 · 2026-08-29 · autor: Oliver (COO) · **status: do sign-offu Darka**

> **Który nośnik kolejności obowiązuje — stan na 2026-08-29, godz. 10:45.**
> Noc 2026-08-29 **zakończona**; `docs/plan-nocy-2026-08-29.md` przechodzi do archiwum jako
> ślad wykonania. **Na najbliższą sesję kolejność niesie `docs/plan-chmura-2026-08-29.md`.**
> Ten dokument wraca do roli nośnika po jej zakończeniu. Wskazanie stoi tutaj, żeby nie było
> trzech nośników tej samej rzeczy bez rozstrzygnięcia, który obowiązuje.
>
> **Plasterek 1 wykonany w nocy** (Księgowanie + Płynność + podział osi prognozy, D-20/D-61).
> **Plasterek 0 przesunięty za pomiar wykonalności Vercela** — nikt nie zmierzył, czy silnik
> z pandas i numpy mieści się w funkcji; ten pomiar jest bramką zerową nowego planu.

**To jest jedyny nośnik KOLEJNOŚCI PRAC.** Nośnikiem wymagań jest `docs/PRD.md` — ten plan go
**woła**, nie powtarza. Zmiany tutaj: bump wersji i changelog na górze.

**Po co osobny dokument.** Zakres v1 to cała aplikacja (decyzja Darka). Poprzednie podejście z tym
samym zakresem dało dziesięć zaprojektowanych ekranów i **zero miejsc, w których da się wpisać
wydatek**. Ten plan istnieje po to, żeby to się nie powtórzyło: dzieli zakres na plasterki, z których
**każdy kończy się czymś, czego Darek może użyć**.

---

## Zasada porządkująca — jedno zdanie

**Najpierw to, po co otwierasz aplikację codziennie; potem to, co liczy; na końcu to, co doradza.**

Nie „najpierw fundament, potem ekrany". Fundament bez ekranu jest niesprawdzalny, a ekran bez
fundamentu kłamie — więc każdy plasterek niesie kawałek obu.

---

## Plasterek 0 — silnik ma czym liczyć · pół dnia

Bez tego żaden rachunek nie ma podstawy: rejestr stawek jest pusty w części `zatwierdzona`, więc
silnik **odmawia**, zamiast zgadywać.

1. Baza w Neonie założona, schemat z `silnik/baza/schemat.sql` wykonany.
2. `migracja/z_sqlite.py` dokończona i uruchomiona; **bramka: liczność i suma kontrolna kwot równe
   po obu stronach** — pomiar źródła już istnieje (204 wpisy, suma 41 887,33 zł).
3. 204 wpisy z 2025 dostają `zrodlo = 'historia-2025'`.
4. Darek zatwierdza 18 stawek początkowych w jednym przebiegu.

**Bramka:** `SELECT COUNT(*) FROM rejestr_stawek WHERE status='zatwierdzona'` ≥ 18, a przeniesienie
przechodzi kontrolę dwóch liczb.
**Co przestanie działać:** nic — stara aplikacja zostaje uruchamialna.

---

## Plasterek 1 — PIERWSZY MOMENT UŻYTECZNOŚCI · trzy dni

**To jest kamień milowy całego przedsięwzięcia:** Darek wpisuje wydatek i widzi, czy da radę do
końca okresu. Wszystko przed nim jest przygotowaniem, wszystko po nim rozszerzeniem.

1. **Księgowanie** — ekran wg `makiety/Ksiegowanie.dc.html`, z podglądem „Co ruszy ten wpis".
   Trasy: `POST /api/wpisy`, `DELETE /api/wpisy/{id}`, `POST /api/wpisy/podglad`.
2. **Płynność** — ekran wg `makiety/Main.dc.html`: księga, wykres z trzema punktami, saldo minimalne,
   zdanie wyjaśniające. Trasa `GET /api/plynnosc`, `PUT /api/kotwica`.
3. Naprawa długu: **oś prognozy dzieli się na dniu dzisiejszym** (D-20) — dni minione z wpisów,
   przyszłe z planu. Bez tego wpisanie wydatku nie zmienia niczego na Płynności i cały plasterek
   jest teatrem.

**Bramka:** wpisujesz wydatek 274,06 zł, wracasz na Płynność, **prognoza się zmienia**. Plus test
pięciu sekund na obu ekranach i porównanie maszynowe z ramkami.
**Co przestanie działać:** nic; stara aplikacja nadal działa równolegle.

---

## Plasterek 2 — plan i miesiąc · trzy dni

1. **Budżet** — komplet **czterech operacji z P-1** (dodać, wycofać, ustawić, **zakończyć** pozycję).
   Kosz kończy regułę od bieżącego miesiąca w przód — nie kasuje historii (Z-9).
2. **Miesiąc** — pięć kafelków, saldo narastające, linia przerywana dla braku przepływu.
3. **Co mnie czeka** — rozwinięcie Płynności.

**Bramka:** stara zakładka Budżet może zostać **wyłączona** — pilnuje tego
`testy/test_nosniki.py::test_cztery_operacje_P1_MAJA_swoje_trasy`.
**Co przestanie działać:** stara zakładka Budżet. To pierwszy moment, w którym coś tracimy — i
dlatego wyłączenie następuje **po** przejęciu wszystkich czterech operacji, nie przed.

---

## Plasterek 3 — firma i podatki · trzy dni

1. **Firma** — daniny z terminami, faktury, rozbicie faktury na siedem pozycji, koszty.
2. Naprawa długu: **kwota wymagalna na termin** — dziś na jeden termin spada suma za dwa okresy.
3. Naprawa długu: **VAT memoriałowo** (D-35) + poprawka ramki `Firma.dc.html` (sprzeczność S-1).
4. **Godziny** — bez konstrukcji ryczałtowej (D-25).

**Bramka:** przy odczycie 6 X 2026 ZUS pokazuje **2 359,30 zł** na termin 20 X (jeden okres, nie
dwa), a VAT z faktury wystawionej 5 X ma termin **25 XI**, nie 26 X.

---

## Plasterek 4 — majątek, raporty, ustawienia · dwa dni

1. **Majątek**, **Raporty** (stan pusty, gdy nie ma wpisów — D-33).
2. **Ustawienia**: słownik kategorii ze znacznikiem `niezbedna`, **rejestr stawek z zatwierdzaniem
   propozycji**, przeprojektowana sekcja „gdzie leżą dane" (sprzeczność S-3), import arkusza.

**Bramka:** Darek zaznacza kategorie niezbędne i **próg poduszki przestaje być przedziałem**.

---

## Plasterek 5 — doradca · trzy dni

1. **Karta „Co mam zrobić"** — najpierw **projekt ramki**, której dziś nie ma, potem budowa.
2. Silnik rad: wybór, kolejność, wyzwalacz. **Model tylko formułuje.**
3. **Ekran Doradca** z dwunastoma narzędziami.
4. Cichy strażnik: przebieg dobowy, stopka na każdym ekranie.

**Bramka — „doradca bez prądu":** odetnij klucz modelu, porównaj komplet rad i kwot.
**Żadna rada nie znika, żadna kwota się nie zmienia.**

---

## Czego w tym planie NIE MA

| Co | Kiedy wraca |
|---|---|
| Widok na telefonie | osobny etap projektowy po odbiorze v1 |
| Powiadomienia | gdy strażnik przez miesiąc znajdzie coś, czego Darek nie zauważył sam |
| Import wyciągu z banku | gdy ręczne wpisywanie znów zamrze na miesiąc |
| Skasowanie starej aplikacji | po plasterku 5, nie wcześniej |

---

## Reguła raportu odbioru

**Raport cytuje ZAKRES kontroli, nie samą jej ocenę.** „Zdane" bez zakresu jest nieodróżnialne od
„zdane w całości" — i tak właśnie zostało przeczytane u poprzednika: kontrola obejmowała wyłącznie
pasek nawigacji, meldunek brzmiał „zgadza się co do piksela", a treść ekranu była sprzed projektu.

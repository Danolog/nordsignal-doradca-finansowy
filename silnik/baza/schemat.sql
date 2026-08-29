-- SCHEMAT BAZY — PostgreSQL. Przeniesienie schematu 11 z SQLite plus rejestr stawek.
--
-- TRZY ZMIANY TYPOW WOBEC POPRZEDNIKA, wszystkie w jedna strone — mniej obejsc:
--   kwota TEXT   -> NUMERIC(14,2)  (SQLite nie ma typu dziesietnego)
--   data  TEXT   -> DATE           (koniec porownan dat na napisach)
--   flaga INTEGER-> BOOLEAN        (koniec pytania "czy 0 znaczy nie, czy brak")

-- ── slownik kategorii ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kategorie (
    id          BIGSERIAL PRIMARY KEY,
    typ         TEXT    NOT NULL,
    nazwa       TEXT    NOT NULL,
    kolejnosc   INT     NOT NULL DEFAULT 0,
    aktywna     BOOLEAN NOT NULL DEFAULT TRUE,
    systemowa   BOOLEAN NOT NULL DEFAULT FALSE,
    -- NOWE (PRD §6.3 p.1): czy kategoria liczy sie do progu poduszki.
    -- Bez tego prog poduszki jest PRZEDZIALEM 29 651–63 649 zl, nie liczba.
    -- NULL znaczy "Darek jeszcze nie rozstrzygnal" — i to jest stan rozny
    -- od "nie jest niezbedna". Aplikacja ma o tym mowic, nie zgadywac.
    niezbedna   BOOLEAN,
    UNIQUE (typ, nazwa),
    CONSTRAINT typ_znany CHECK (typ IN ('Przychody','Wydatki','Oszczędności'))
);

-- ── wpisy faktyczne ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wpisy_budzetu (
    id          BIGSERIAL PRIMARY KEY,
    data        DATE          NOT NULL,
    typ         TEXT          NOT NULL,
    kategoria   TEXT          NOT NULL,
    kwota       NUMERIC(14,2) NOT NULL,
    szczegoly   TEXT          NOT NULL DEFAULT '',
    -- NOWE (PRD §6.3 p.2): skad wpis pochodzi. To jest BRAMKA POPRAWNOSCI,
    -- nie metadana dla porzadku. Bez niej "wgrac historie 2025" i "nie liczyc
    -- jej do podatku 2026" sa dwiema regulami w dwoch miejscach, ktore
    -- rozjada sie przy pierwszej zmianie. Z nia jest JEDNA regula w jednym
    -- miejscu: do rachunku wchodza wylacznie wiersze o zrodle 'recznie'.
    zrodlo      TEXT          NOT NULL DEFAULT 'recznie',
    CONSTRAINT kwota_bez_znaku CHECK (kwota >= 0),
    CONSTRAINT zrodlo_znane CHECK (zrodlo IN ('recznie','historia-2025','import'))
);
CREATE INDEX IF NOT EXISTS wpisy_po_dacie ON wpisy_budzetu (data);
CREATE INDEX IF NOT EXISTS wpisy_do_rachunku ON wpisy_budzetu (data) WHERE zrodlo <> 'historia-2025';

-- ── plan budzetu ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plan_budzetu (
    id              BIGSERIAL PRIMARY KEY,
    rok             INT           NOT NULL,
    miesiac         INT           NOT NULL,
    typ             TEXT          NOT NULL,
    kategoria       TEXT          NOT NULL,
    kwota_planowana NUMERIC(14,2) NOT NULL,
    powtarzalna     BOOLEAN       NOT NULL DEFAULT FALSE,
    do_roku         INT,
    do_miesiaca     INT,
    opis            TEXT          NOT NULL DEFAULT '',
    dzien           INT,
    co_ile_miesiecy INT           NOT NULL DEFAULT 1,
    UNIQUE (rok, miesiac, typ, kategoria, opis),
    CONSTRAINT miesiac_sensowny CHECK (miesiac BETWEEN 1 AND 12),
    CONSTRAINT dzien_sensowny CHECK (dzien IS NULL OR dzien BETWEEN 1 AND 31)
);

-- ── dzialalnosc gospodarcza ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS przychody_jdg (
    id             BIGSERIAL PRIMARY KEY,
    numer_faktury  TEXT          NOT NULL UNIQUE,
    data           DATE          NOT NULL,   -- data WYSTAWIENIA
    data_zaplaty   DATE,
    kwota_netto    NUMERIC(14,2) NOT NULL,
    stawka_vat     NUMERIC(6,4)  NOT NULL,
    kwota_vat      NUMERIC(14,2) NOT NULL,
    -- NOWE (PRD §6.3 p.3, decyzja D-35): VAT liczy sie MEMORIALOWO —
    -- obowiazek powstaje z chwila WYSTAWIENIA faktury, nie jej zaplaty.
    -- Faktura wystawiona 5 X za wrzesien nalezy do okresu PAZDZIERNIK,
    -- termin 25 XI. Poprzednia aplikacja sumowala VAT ze WSZYSTKICH faktur
    -- bez wzgledu na okres — kwota siedziala w zlym miesiacu.
    data_obowiazku_vat DATE      NOT NULL,
    pkwiu          TEXT          NOT NULL DEFAULT '',
    wpis_budzetu_id BIGINT REFERENCES wpisy_budzetu(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS koszty_jdg (
    id              BIGSERIAL PRIMARY KEY,
    data            DATE          NOT NULL,
    opis            TEXT          NOT NULL,
    kwota_netto     NUMERIC(14,2) NOT NULL,
    kwota_vat       NUMERIC(14,2) NOT NULL,
    wpis_budzetu_id BIGINT REFERENCES wpisy_budzetu(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS godziny (
    id               BIGSERIAL PRIMARY KEY,
    data             DATE          NOT NULL,
    rodzaj_czynnosci TEXT          NOT NULL,
    liczba_godzin    NUMERIC(8,2)  NOT NULL,
    opis             TEXT          NOT NULL DEFAULT '',
    -- PKWiU zostaje w schemacie, ale SCHODZI Z EKRANU (D-25): przy skali
    -- jedna stawka od calosci dochodu, wiec rozdzielanie czynnosci nie sluzy
    -- kwalifikacji. Kolumny nie kasujemy — sluzy porownaniu form.
    pkwiu            TEXT          NOT NULL DEFAULT ''
);

-- ── majatek i dlugi ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS majatek (
    id           BIGSERIAL PRIMARY KEY,
    nazwa_aktywa TEXT          NOT NULL,
    kategoria    TEXT          NOT NULL,
    wartosc      NUMERIC(14,2) NOT NULL
);
-- Rachunek rozliczeniowy MOZE BYC TYLKO JEDEN (D-30): to ten, z ktorego ida
-- wydatki, i jego saldo wola kotwica prognozy. Dwa takie wiersze znaczylyby,
-- ze aplikacja nie wie, ktore saldo jest tym wlasciwym.
CREATE UNIQUE INDEX IF NOT EXISTS majatek_jeden_rozliczeniowy
    ON majatek ((kategoria)) WHERE kategoria = 'rachunek rozliczeniowy';

CREATE TABLE IF NOT EXISTS zobowiazania (
    id             BIGSERIAL PRIMARY KEY,
    nazwa          TEXT          NOT NULL,
    kapital        NUMERIC(14,2) NOT NULL,
    rata_minimalna NUMERIC(14,2) NOT NULL,
    -- JEDNOSTKA: PROCENT. 9 znaczy 9%. To jest rozjazd z `stawka_ryczaltu`,
    -- ktora trzyma ULAMEK — swiadomy, bo tak Darek podaje w formularzu.
    -- Pomnozenie kapitalu przez 9 zamiast 0,09 to blad stukrotny.
    -- NULL znaczy "nie wiem", 0 znaczy "zero procent" — to dwa rozne stany.
    oprocentowanie NUMERIC(6,3),
    CONSTRAINT oprocentowanie_sensowne CHECK (
        oprocentowanie IS NULL OR (oprocentowanie >= 0 AND oprocentowanie <= 100)
    )
);

-- ── plynnosc ──────────────────────────────────────────────────────────────
-- Kotwica prognozy. ZRODLEM JEST ODCZYT, majatek go wola (D-28/D10).
-- Kotwica NIGDY nie jest suma sald: odczyt niesie DATE, majatek nie —
-- wyprowadzenie kotwicy z majatku kazaloby date zmyslic, a prognoza
-- udawalaby swiezosc kazdego dnia bez nowego odczytu.
CREATE TABLE IF NOT EXISTS stan_konta (
    data  DATE PRIMARY KEY,
    kwota NUMERIC(14,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS cele_oszczednosciowe (
    id             BIGSERIAL PRIMARY KEY,
    nazwa          TEXT          NOT NULL UNIQUE,
    kategoria      TEXT          NOT NULL,
    kwota_docelowa NUMERIC(14,2) NOT NULL,
    termin         DATE,
    -- PRD §10.3 S-2: prog poduszki jest LICZONY (6 x wydatki niezbedne).
    -- Ta flaga oznacza wartosc nadpisana recznie — ekran ma pokazac obok
    -- wynik rachunku, zeby odstepstwo bylo widoczne, a nie ciche.
    nadpisana_recznie BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── nastawy ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS forma_opodatkowania (
    rok             INT PRIMARY KEY,
    forma           TEXT NOT NULL,
    stawka_ryczaltu NUMERIC(6,4),   -- ULAMEK. Wypelniona TYLKO przy ryczalcie.
    CONSTRAINT forma_znana CHECK (forma IN ('SKALA','LINIOWY','RYCZALT')),
    -- Stawka ryczaltu przy skali jest sprzecznoscia, a nie pustym polem.
    -- To jest ta sama klasa wady, ktora w poprzedniej aplikacji dawala
    -- kwoty liczone forma, ktorej Darek nie ma.
    CONSTRAINT stawka_tylko_przy_ryczalcie CHECK (
        (forma = 'RYCZALT' AND stawka_ryczaltu IS NOT NULL)
        OR (forma <> 'RYCZALT' AND stawka_ryczaltu IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS ustawienia (
    klucz   TEXT PRIMARY KEY,
    wartosc TEXT NOT NULL
);

-- ── cichy straznik ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS przebiegi_straznika (
    id                    BIGSERIAL PRIMARY KEY,
    kiedy                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    stan_prognozy         TEXT        NOT NULL,
    pierwszy_dzien_ujemny DATE,
    pilnych               INT         NOT NULL,
    powod                 TEXT,
    zrodla                TEXT        NOT NULL,
    komunikat             TEXT        NOT NULL,
    powiadomiono          BOOLEAN     NOT NULL DEFAULT FALSE
);

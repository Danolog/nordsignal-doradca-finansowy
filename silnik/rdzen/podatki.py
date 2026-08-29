"""Arytmetyka podatkowa jednoosobowej działalności — OBU form naraz.

Skala podatkowa i ryczałt od przychodów ewidencjonowanych. Moduł powstał pod
sam ryczałt (skala doszła w Z29–Z33) i przez to do 2026-08-28 ryczałt był
tu **wartością domyślną w trzech miejscach**: w `skladki_zus_za_miesiace`,
w polach `RezerwaPodatkowa.forma`/`nazwa_podatku` i w `rezerwa_na_podatki`.
Wołający, który formy nie podał, dostawał liczbę ryczałtową — cicho
i wiarygodnie. Dziś **forma jest argumentem wymaganym**: pominięcie jej jest
błędem w chwili wywołania, a nie złą liczbą na ekranie.

Zero zaszytych kwot — każda liczba pochodzi z `rdzen.stawki`. Ten moduł wie,
**jak** liczyć; nie wie, **ile** wynoszą stawki, ani **którą formą** — formę
podaje wołający, bo jest ustawieniem użytkownika, a nie stałą.

Wynik niesie listę `zalozenia` z jawnie nazwanymi uproszczeniami. Liczba bez
widocznych założeń udaje precyzję, której nie ma — a każde z tych uproszczeń
zostało rozstrzygnięte świadomie, nie po cichu.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from silnik.rdzen import budzet, magazyn, stawki
from silnik.rdzen.magazyn import BladMagazynu

__all_bledy__ = (BladMagazynu,)


@dataclass(frozen=True)
class Wyliczenie:
    """Rozbicie jednej faktury na rezerwy i kwotę, która realnie zostaje."""
    kwota_netto: Decimal
    vat: Decimal
    zdrowotna: Decimal          # 0, jeśli już naliczona w tym miesiącu
    spoleczne: Decimal          # 0, jeśli już naliczone w tym miesiącu
    podstawa_ryczaltu: Decimal
    pit: Decimal                # pełne złote (art. 63 Ordynacji podatkowej)
    do_dyspozycji: Decimal
    prog_zdrowotnej: int        # 1, 2 albo 3
    zalozenia: list[str]


def miesiace_dzialalnosci(od: date, do: date) -> int:
    """Ile miesiecy kalendarzowych trwa dzialalnosc miedzy dwiema datami.

    Miesiace, nie dni: skladka ZUS nalezy sie za MIESIAC, nie za jego dlugosc.
    Wrzesien–grudzien to cztery skladki niezaleznie od tego, czy grudzien
    liczy sie do czwartego czy do trzydziestego pierwszego.

    ZALOZENIE NAZWANE: miesiac rozpoczety liczy sie w calosci. Start
    15 wrzesnia daje wrzesien jako pelny miesiac skladkowy. To odczyt
    ostrozniejszy — zawyza rezerwe zamiast zanizac, a pomylka w te strone
    kosztuje nadmiar odlozonych pieniedzy, nie zaleglosc w ZUS.

    Odwrocone daty sa BLEDEM, nie ujemna liczba: rezerwa ujemna wygladalaby
    jak nadplata, czyli jak pieniadze do odzyskania.
    """
    if od > do:
        raise BladMagazynu(
            f"Data rozpoczecia dzialalnosci ({od.isoformat()}) jest pozniejsza "
            f"niz data, do ktorej liczymy ({do.isoformat()}). Sprawdz "
            f"ustawienie \u201edzialalnosc od\u201d w Ustawieniach.")
    return (do.year - od.year) * 12 + (do.month - od.month) + 1


def prog_dla_przychodu(przychod_narastajaco: Decimal) -> int:
    """Numer progu składki zdrowotnej (1, 2 albo 3) dla przychodu narastająco.

    **Nazwa zostaje, reguła się wyprowadziła.** Sama reguła mieszka od Z4
    w `stawki.prog_dla_przychodu` — jedynym nośniku. Ta funkcja ją woła
    i istnieje wyłącznie dlatego, że kilkadziesiąt testów i dwa moduły wołają
    ją pod tą nazwą; usunięcie nazwy byłoby zmianą bez wartości.
    """
    return stawki.prog_dla_przychodu(przychod_narastajaco)


def _zalozenia(prog: int, naliczone: bool) -> list[str]:
    zrodlo = stawki.ZRODLA["zdrowotna"]
    lista = [
        "Próg 60 000 zł liczony po osiągnięciu — przychód dokładnie równy progowi "
        "wchodzi na wyższą składkę (odczyt ostrożniejszy, pozycja 12.2 specyfikacji).",
        "Składki traktowane jako zapłacone w miesiącu, do którego są przypisane — "
        "przepis mówi o składkach zapłaconych, aplikacja liczy rezerwę.",
        "VAT to kwota należna. Aplikacja nie zna VAT-u naliczonego z zakupów, "
        "więc rezerwa na VAT jest oszacowaniem górnym, nie kwotą do przelewu.",
        f"Stawki z rejestru odczytanego {zrodlo.data_odczytu.isoformat()}, "
        f"źródło: {zrodlo.url}",
    ]
    if naliczone:
        lista.append(
            "Składki nie zostały naliczone przy tej fakturze — są cechą miesiąca, "
            "nie faktury, i zarezerwowano je przy wcześniejszej fakturze."
        )
    if prog == 3:
        lista.append(
            "Próg trzeci (powyżej 300 000 zł) jest przy obecnej umowie poza "
            "zasięgiem samej podstawy godzinowej — sprawdź, czy przychód jest realny."
        )
    return lista


def policz_ryczalt(
    kwota_netto: Decimal,
    stawka_ryczaltu: Decimal,
    stawka_vat: Decimal,
    przychod_narastajaco: Decimal,
    skladki_juz_naliczone_w_miesiacu: bool,
) -> Wyliczenie:
    """Rozbija fakturę RYCZAŁTOWĄ na VAT, składki, PIT i kwotę do dyspozycji.

    Do Z58 ta funkcja nazywała się `policz` — i była jedyna, bo aplikacja znała
    tylko ryczałt. Po Z58 `policz` rozstrzyga po formie, a każdy silnik ma
    jawną nazwę: pomylenie reguł skali i ryczałtu psuje każdą fakturę
    (zdrowotna odliczalna na jednym, nieodliczalna na drugim).

    `przychod_narastajaco` to suma przychodów od początku roku **bez** tej
    faktury — funkcja sama ją dolicza przed ustaleniem progu, bo miesiąc
    przekroczenia rozlicza się już według wyższego progu.
    """
    netto = Decimal(kwota_netto)
    vat = stawki.do_groszy(netto * Decimal(stawka_vat))

    numer_progu = prog_dla_przychodu(Decimal(przychod_narastajaco) + netto)
    mnoznik = stawki.PROGI_ZDROWOTNEJ[numer_progu - 1].mnoznik

    if skladki_juz_naliczone_w_miesiacu:
        zdrowotna = Decimal("0.00")
        spoleczne = Decimal("0.00")
    else:
        zdrowotna = stawki.skladka_zdrowotna(mnoznik)
        spoleczne = stawki.suma_spolecznych(z_chorobowa=True)

    # Podstawa ryczałtu: przychód minus zapłacone składki społeczne
    # minus POŁOWA zapłaconej składki zdrowotnej.
    podstawa = netto - spoleczne - stawki.do_groszy(zdrowotna / 2)
    podstawa = max(Decimal("0.00"), podstawa)

    pit = stawki.do_zlotych(podstawa * Decimal(stawka_ryczaltu))
    do_dyspozycji = netto - zdrowotna - spoleczne - pit

    return Wyliczenie(
        kwota_netto=netto,
        vat=vat,
        zdrowotna=zdrowotna,
        spoleczne=spoleczne,
        podstawa_ryczaltu=podstawa,
        pit=pit,
        do_dyspozycji=do_dyspozycji,
        prog_zdrowotnej=numer_progu,
        zalozenia=_zalozenia(numer_progu, skladki_juz_naliczone_w_miesiacu),
    )


# --- skala podatkowa ------------------------------------------------------

@dataclass(frozen=True)
class WyliczenieSkali:
    """Rozbicie faktury przy skali podatkowej, z zaliczką liczoną narastająco.

    Osobna od `Wyliczenie` (ryczałt), bo połowa pól tamtej nie ma tu sensu:
    `podstawa_ryczaltu` i `prog_zdrowotnej` są pojęciami ryczałtu. Pola
    wspólne noszą te same nazwy (`kwota_netto`, `vat`, `zdrowotna`,
    `spoleczne`, `pit`, `do_dyspozycji`, `zalozenia`), więc ekran czyta
    obie tak samo.
    """

    kwota_netto: Decimal
    vat: Decimal
    zdrowotna: Decimal          # 9% dochodu miesiąca, NIEODLICZALNA
    spoleczne: Decimal
    koszty: Decimal
    dochod_miesiaca: Decimal
    dochod_narastajaco: Decimal
    podatek_narastajaco: Decimal          # po kwocie zmniejszającej, przed zaliczkami
    zaliczka_przed_zaokragleniem: Decimal
    zaliczka: Decimal                     # pełne złote (art. 63 Ordynacji)
    obowiazek_wplaty: bool                # False, gdy zaliczka ≤ 1 000 zł
    pit: Decimal                          # = zaliczka, nazwa wspólna z ryczałtem
    do_dyspozycji: Decimal
    zalozenia: list[str]


#: Próg, poniżej którego zaliczki nie trzeba wpłacać w danym miesiącu.
#: `portal/00264`: „mogą nie wpłacać zaliczki […] jeżeli podatek należny
#: […] nie przekracza 1000 zł". Kwota jest jednak DALEJ NALICZONA — narzędzie
#: do odkładania pieniędzy ma ją zarezerwować, bo obowiązek wróci.
PROG_OBOWIAZKU_ZALICZKI = Decimal("1000")


def _podatek_skali(dochod: Decimal) -> Decimal:
    """Podatek od dochodu narastająco, po odjęciu kwoty zmniejszającej.

    Kwota zmniejszająca 3 600 zł bierze się w CAŁOŚCI, nie po 300 zł na
    miesiąc — podział po 300 zł to mechanizm PŁATNIKA (pracodawcy przy umowie
    o pracę), nie samodzielnie liczonej zaliczki przedsiębiorcy. Źródło
    `portal/00264`: „pomnóż podstawę opodatkowania przez 12% i odejmij 3600 zł".

    To się samo domyka: skoro liczymy narastająco i odejmujemy zaliczki już
    naliczone, wzięcie całości w miesiącu pierwszym NIE zawyża kolejnych —
    odracza tylko pierwsze wpłaty, aż podatek przekroczy 3 600 zł.
    """
    if dochod <= stawki.PROG_SKALI:
        podatek = stawki.STAWKA_SKALI_PIERWSZA * dochod
    else:
        podatek = (stawki.STAWKA_SKALI_PIERWSZA * stawki.PROG_SKALI
                   + stawki.STAWKA_SKALI_DRUGA * (dochod - stawki.PROG_SKALI))
    return max(Decimal("0"), podatek - stawki.KWOTA_ZMNIEJSZAJACA_PODATEK)


def policz_skala(*, kwota_netto: Decimal, stawka_vat: Decimal,
                 dochod_narastajaco: Decimal,
                 zaliczki_juz_naliczone: Decimal,
                 skladki_juz_naliczone_w_miesiacu: bool,
                 koszty: Decimal = Decimal("0")) -> WyliczenieSkali:
    """Rozbija fakturę przy SKALI podatkowej, licząc zaliczkę narastająco.

    CZTERY RÓŻNICE WOBEC RYCZAŁTU, które łatwo przeoczyć (plan formy §3):

    1. **Progi zdrowotnej 60/300 tys. nie istnieją.** Składka liczy się od
       DOCHODU miesiąca, nie od progu przychodu narastająco.
    2. **Zdrowotna NIE jest odliczalna** (od 2022, `portal/001052`). Na
       ryczałcie odlicza się 50% od przychodu — ta reguła przeniesiona na
       skalę zaniżałaby podstawę przy każdej fakturze.
    3. **Kwota zmniejszająca w całości**, nie po 1/12 — patrz `_podatek_skali`.
    4. **Zaliczka narastająco**: podatek od dochodu od początku roku minus
       zaliczki już naliczone; zaokrąglenie do pełnych złotych na końcu,
       nie po drodze.

    `dochod_narastajaco` to dochód od początku roku **bez** tej faktury —
    funkcja sam ją dolicza, tak samo jak `policz_ryczalt` dolicza przychód.
    """
    netto = Decimal(kwota_netto)
    vat = stawki.do_groszy(netto * Decimal(stawka_vat))
    koszty = Decimal(koszty)

    if skladki_juz_naliczone_w_miesiacu:
        spoleczne = Decimal("0.00")
    else:
        spoleczne = stawki.suma_spolecznych(z_chorobowa=True)

    dochod_miesiaca = netto - koszty - spoleczne
    dochod = Decimal(dochod_narastajaco) + dochod_miesiaca

    if skladki_juz_naliczone_w_miesiacu:
        zdrowotna = Decimal("0.00")
    else:
        zdrowotna = max(
            stawki.do_groszy(stawki.STAWKA_ZDROWOTNEJ_SKALA
                             * max(Decimal("0"), dochod_miesiaca)),
            stawki.ZDROWOTNA_MIN_MIESIECZNA)

    podatek = stawki.do_groszy(_podatek_skali(dochod))
    przed_zaokragleniem = podatek - Decimal(zaliczki_juz_naliczone)
    zaliczka = stawki.do_zlotych(max(Decimal("0"), przed_zaokragleniem))
    obowiazek = zaliczka > PROG_OBOWIAZKU_ZALICZKI

    return WyliczenieSkali(
        kwota_netto=netto, vat=vat, zdrowotna=zdrowotna, spoleczne=spoleczne,
        koszty=koszty, dochod_miesiaca=dochod_miesiaca,
        dochod_narastajaco=dochod, podatek_narastajaco=podatek,
        zaliczka_przed_zaokragleniem=przed_zaokragleniem, zaliczka=zaliczka,
        obowiazek_wplaty=obowiazek, pit=zaliczka,
        do_dyspozycji=netto - zdrowotna - spoleczne - zaliczka,
        zalozenia=[
            "Skala podatkowa: 12% do 120 000 zł dochodu, 32% powyżej.",
            "Kwota zmniejszająca 3 600 zł wzięta W CAŁOŚCI — podział po 300 zł "
            "to mechanizm płatnika, nie zaliczki przedsiębiorcy (portal/00264).",
            "Składka zdrowotna 9% dochodu i NIEODLICZALNA od podstawy "
            "(portal/001052).",
            "Zdrowotna za dany miesiąc płaci się od dochodu miesiąca "
            "poprzedniego — tu liczona od dochodu TEGO miesiąca, bo to on "
            "wyznaczy składkę do zapłacenia w miesiącu następnym.",
        ] + ([] if obowiazek else [
            f"Zaliczka {zaliczka} zł nie przekracza {PROG_OBOWIAZKU_ZALICZKI} zł "
            "— w tym miesiącu nie ma obowiązku wpłaty, ale kwota jest "
            "zarezerwowana, bo obowiązek wróci."
        ]),
    )


def policz(forma: str, **argumenty):
    """Wspólne wejście: rozstrzyga po formie, którego silnika użyć (Z58).

    Stan `NIEROZSTRZYGNIETA` ODMAWIA. Nie zgaduje — precedens we własnym
    kodzie: `weryfikacja.sprawdz` przy wyniku ROZBIEZNE blokuje formularz
    faktury, zamiast liczyć z niepewnych stawek. Odkładanie pieniędzy według
    zgadniętej formy to realna szkoda, nie niedokładność raportu (D6).
    """
    if forma == magazyn.FORMA_RYCZALT:
        return policz_ryczalt(**argumenty)
    if forma == magazyn.FORMA_SKALA:
        return policz_skala(**argumenty)
    raise BladMagazynu(
        f"Nie policzę podatku: forma opodatkowania to {forma!r}. "
        f"Wskaż formę na ten rok w Ustawieniach — aplikacja jej nie zgadnie, "
        f"bo odkładanie pieniędzy według zgadniętej formy to realna szkoda.")


def argumenty_dla_formy(forma: str, *, kwota_netto: Decimal,
                        stawka_vat: Decimal,
                        stawka_ryczaltu: "Decimal | None" = None,
                        przychod_narastajaco: Decimal = Decimal("0"),
                        dochod_narastajaco: Decimal = Decimal("0"),
                        zaliczki_naliczone: Decimal = Decimal("0"),
                        skladki_juz_naliczone_w_miesiacu: bool = False,
                        koszty: Decimal = Decimal("0")) -> dict:
    """Komplet argumentów dla `policz` — RÓŻNY dla każdej formy. Jeden nośnik.

    Do 2026-08-28 tę wiedzę („ryczałt potrzebuje przychodu narastająco, skala
    dochodu i zaliczek") niosła prywatna funkcja `prognoza_plynnosci.
    _argumenty_daniny`, więc każdy inny wołający `policz` musiał ją odtworzyć
    z pamięci. Odtworzył ją dokładnie NIKT: formularz faktury i narzędzie
    doradcy wołały `policz_ryczalt` wprost, z pominięciem formy.

    Forma NIEROZSTRZYGNIĘTA dostaje pusty słownik świadomie — wtedy `policz`
    odmawia z komunikatem mówiącym, gdzie formę wskazać. Zgadnięcie
    czegokolwiek tutaj byłoby dokładnie tą wadą, którą ten moduł naprawia.
    """
    if forma == magazyn.FORMA_RYCZALT:
        return dict(kwota_netto=kwota_netto, stawka_ryczaltu=stawka_ryczaltu,
                    stawka_vat=stawka_vat,
                    przychod_narastajaco=przychod_narastajaco,
                    skladki_juz_naliczone_w_miesiacu=(
                        skladki_juz_naliczone_w_miesiacu))
    if forma == magazyn.FORMA_SKALA:
        return dict(kwota_netto=kwota_netto, stawka_vat=stawka_vat,
                    dochod_narastajaco=dochod_narastajaco,
                    zaliczki_juz_naliczone=zaliczki_naliczone,
                    skladki_juz_naliczone_w_miesiacu=(
                        skladki_juz_naliczone_w_miesiacu),
                    koszty=koszty)
    return {}


# --- składki ZUS: za MIESIĄCE działalności, nie za faktury -----------------

@dataclass(frozen=True)
class SkladkiZus:
    """Składki za okres działalności, z liczbą miesięcy, które pomiar widział.

    `miesiace` i `progi` nie są ozdobą — to kontrola liczności. Sama kwota
    nie mówi, czy pomiar objął trzy miesiące, czy dwa; a właśnie ta różnica
    jest wadą, którą Z55 zamyka.
    """

    miesiace: int
    progi: tuple[int, ...]      # numer progu zdrowotnej dla każdego miesiąca
    spoleczne: Decimal
    zdrowotna: Decimal
    razem: Decimal

    #: Składka za KAŻDY miesiąc osobno: `(pierwszy dzień miesiąca, kwota)`.
    #: Dołożone 2026-08-28 (wada 2). Sama `razem` nie da się rozbić na terminy:
    #: składka za wrzesień jest płatna 20 października, a za październik
    #: 20 listopada — jedna zbiorcza kwota na jeden termin kazała zapłacić
    #: dwie składki w dniu, w którym wymagalna jest jedna.
    wg_miesiaca: tuple[tuple["date", Decimal], ...] = ()


def _przychod_do_konca_miesiaca(faktury, rok: int, miesiac: int) -> Decimal:
    """Przychód netto od początku ROKU do końca podanego miesiąca.

    Rok kalendarzowy, nie ruchome dwanaście miesięcy: próg składki zdrowotnej
    liczy się w roku podatkowym. Bez zerowania na przełomie roku po dobrym
    roku styczeń startowałby od najwyższego progu.
    """
    if faktury is None or faktury.empty or "data" not in faktury.columns:
        return Decimal("0.00")
    granica = f"{rok:04d}-{miesiac:02d}"
    wybrane = faktury[[str(d)[:7] >= f"{rok:04d}-01" and str(d)[:7] <= granica
                       for d in faktury["data"]]]
    if wybrane.empty:
        return Decimal("0.00")
    return stawki.do_groszy(
        sum((Decimal(str(x)) for x in wybrane["kwota_netto"]), Decimal("0.00")))


def _przychod_miesiaca(faktury, rok: int, miesiac: int) -> Decimal:
    """Przychód netto SAMEGO miesiąca — podstawa zdrowotnej na skali."""
    if faktury is None or faktury.empty or "data" not in faktury.columns:
        return Decimal("0.00")
    prefiks = f"{rok:04d}-{miesiac:02d}"
    wybrane = faktury[[str(d).startswith(prefiks) for d in faktury["data"]]]
    if wybrane.empty:
        return Decimal("0.00")
    return stawki.do_groszy(
        sum((Decimal(str(x)) for x in wybrane["kwota_netto"]), Decimal("0.00")))


def skladki_zus_za_miesiace(faktury, *, od: date, do: date,
                            forma: str) -> SkladkiZus:
    """Składki ZUS za każdy miesiąc działalności między dwiema datami.

    SEDNO ZADANIA Z55. Do niego rezerwa sumowała kolumnę
    `przychody_jdg.zaplacony_zus`, czyli mierzyła **liczbę faktur**. Miesiąc
    bez zlecenia nie naliczał składki — przy trzech miesiącach i dwóch
    fakturach dawało to 4 850,22 zł zamiast 7 275,33 zł.

    Kolumna `zaplacony_zus` **zostaje** w tabeli i nie jest tu czytana.
    Odpowiada na inne pytanie: „co mi z tej faktury zostaje". Rezerwa pyta
    „ile mam odłożyć". Te liczby mogą się różnić i to jest poprawne.

    Społeczne są stałe **i takie same w obu formach**; zdrowotna zależy od
    formy i to jest różnica, którą łatwo przeoczyć (Z59):

    - **ryczałt**: składka ryczałtowa, według progu **przychodu narastająco**
      (60/300 tys.). Próg rośnie w trakcie roku, więc składka za grudzień bywa
      wyższa niż za styczeń.
    - **skala**: 9% **dochodu miesiąca**, z minimum miesięcznym. Progi
      60/300 tys. tu nie istnieją.

    Ta sama rezerwa policzona nie tą metodą myli się o całą składkę miesięcznie.
    """
    liczba = miesiace_dzialalnosci(od, do)

    spoleczne_mc = stawki.suma_spolecznych(z_chorobowa=True)
    progi: list[int] = []
    zdrowotna = Decimal("0.00")
    wg_miesiaca: list[tuple[date, Decimal]] = []
    rok, miesiac = od.year, od.month
    for _ in range(liczba):
        zdrowotna_przed = zdrowotna
        if forma == "SKALA":
            # Progi 60/300 tys. NIE istnieją na skali — składka idzie
            # od dochodu miesiąca, z minimum (plan formy §3, różnice 1 i 3).
            przychod_mc = _przychod_miesiaca(faktury, rok, miesiac)
            dochod_mc = przychod_mc - spoleczne_mc
            progi.append(0)          # 0 = „progi ryczałtu nie dotyczą"
            zdrowotna += max(
                stawki.do_groszy(stawki.STAWKA_ZDROWOTNEJ_SKALA
                                 * max(Decimal("0"), dochod_mc)),
                stawki.ZDROWOTNA_MIN_MIESIECZNA)
        else:
            numer = prog_dla_przychodu(
                _przychod_do_konca_miesiaca(faktury, rok, miesiac))
            progi.append(numer)
            zdrowotna += stawki.skladka_zdrowotna(
                stawki.PROGI_ZDROWOTNEJ[numer - 1].mnoznik)
        wg_miesiaca.append((
            date(rok, miesiac, 1),
            stawki.do_groszy(spoleczne_mc + (zdrowotna - zdrowotna_przed))))
        miesiac += 1
        if miesiac > 12:
            rok, miesiac = rok + 1, 1

    spoleczne = spoleczne_mc * liczba
    return SkladkiZus(
        miesiace=liczba, progi=tuple(progi),
        spoleczne=stawki.do_groszy(spoleczne),
        zdrowotna=stawki.do_groszy(zdrowotna),
        razem=stawki.do_groszy(spoleczne + zdrowotna),
        wg_miesiaca=tuple(wg_miesiaca))


# --- rezerwa na podatki: naliczone minus zapłacone -------------------------

@dataclass(frozen=True)
class RezerwaPodatkowa:
    """Ile jeszcze wisi u urzędu — SALDO, nie suma.

    Decyzja Darka D3 z 2026-08-25 (`docs/plan-integracji-jdg-budzet.md` §9).
    Do tej pory kafel sumował VAT i ZUS ze wszystkich faktur od początku bazy
    i nigdy nie schodził w dół. Po przejściu na ujęcie kasowe zapłacony
    podatek jest wydatkiem — więc suma naliczonych rosłaby w nieskończoność
    i przestała cokolwiek znaczyć.
    """

    vat_nalezny: Decimal
    vat_naliczony: Decimal
    vat_do_zaplaty: Decimal      # nie mniej niż zero — patrz niżej
    zus: Decimal

    #: Podatek dochodowy — RYCZAŁT albo PIT wg skali. Do Z59 pole nazywało się
    #: `ryczalt`, bo aplikacja znała tylko jedną formę; nazwa trzymająca kwotę
    #: skali byłaby kłamstwem w kodzie.
    podatek_dochodowy: Decimal
    naliczone_razem: Decimal
    zaplacone: Decimal
    saldo: Decimal               # MOŻE być ujemne — patrz niżej

    #: Ile miesięcy działalności weszło do składek. `None` znaczy „NIE
    #: LICZYŁEM" — nie „zero miesięcy". To JEDYNY dyskryminator tego stanu:
    #: `zus == 0` samo w sobie znaczyłoby „składek nie ma", czyli najlepszy
    #: możliwy stan pokazany przy braku wiedzy (reguła D11).
    miesiace_zus: int | None = None

    #: Czego ta liczba NIE obejmuje, zdaniami od silnika. Pusta krotka, gdy
    #: nie ma czego zastrzegać — zastrzeżenie przy każdym uruchomieniu
    #: przestaje się czytać.
    zastrzezenia: tuple[str, ...] = ()

    #: Forma, według której policzono, i nazwa podatku dochodowego dla ekranu
    #: („Ryczałt" albo „PIT"). Ekran nie ma pokazywać pozycji „Ryczałt" komuś
    #: na skali — a nazwa musi pochodzić stąd, nie z drugiego rachunku.
    #:
    #: OBA POLA SĄ WYMAGANE (2026-08-28). Do tej daty niosły domyślnie
    #: `"RYCZALT"`/`"Ryczałt"`, więc każdy niepełny zapis tego obiektu
    #: **twierdził na ekranie ryczałt**, nie pytając nikogo o formę. Darek jest
    #: na skali od 2026 (`docs/plan-forma-opodatkowania.md` v0.5) i widział ten
    #: napis trzy razy w ciągu jednego dnia. `kw_only` jest tu konieczne
    #: technicznie: pole bez wartości domyślnej nie może stać za polami, które
    #: ją mają — a kolejność pól tego dataclassu jest częścią jego czytelności.
    forma: str = field(kw_only=True)
    nazwa_podatku: str = field(kw_only=True)

    #: Pierwszy dzień działalności. Niesiony TUTAJ, a nie dokładany jako
    #: argument u każdego konsumenta, bo odpowiada na pytanie „od kiedy w
    #: ogóle mogą istnieć terminy" — a konsumentów rezerwy jest kilku i
    #: pominięcie go u jednego dawałoby termin sprzed działalności tylko na
    #: jednym ekranie (naprawa 2026-08-28). `None` znaczy „nie wiem",
    #: wtedy terminy liczą się jak przed naprawą.
    dzialalnosc_od: "date | None" = None

    #: ZUS w rozbiciu na miesiące: `(pierwszy dzień miesiąca, kwota)`.
    #: Niesiony tu z tego samego powodu co `dzialalnosc_od`: konsumentów
    #: rezerwy jest kilku, a policzenie rozbicia u każdego z osobna wymagałoby
    #: faktur, których oni nie mają. Puste = „nie liczyłem" (jak `miesiace_zus`).
    zus_wg_miesiaca: tuple[tuple["date", Decimal], ...] = ()


def ryczalt_z_faktury(*, kwota_netto: Decimal, zaplacony_zus: Decimal,
                      zysk_netto: Decimal) -> Decimal:
    """Kwota ryczałtu odzyskana z zapisanej faktury.

    Tabela `przychody_jdg` nie ma kolumny z kwotą podatku — ma za to wszystko,
    z czego ta kwota wynika. `policz` liczy `do_dyspozycji = netto − składki
    − pit`, więc `pit = netto − składki − do_dyspozycji`. To **odwrócenie
    tożsamości**, nie oszacowanie: wszystkie trzy składniki są zapisane, więc
    wynik jest dokładny co do grosza, bez powtarzania zaokrągleń.

    Test `test_ryczalt_odzyskany_z_faktury_zgadza_sie_z_silnikiem` wiąże tę
    funkcję z `policz` — zmiana definicji zysku w silniku zaczerwieni go,
    zamiast po cichu rozjechać dwie drogi do tej samej liczby.
    """
    return (Decimal(kwota_netto) - Decimal(zaplacony_zus)
            - Decimal(zysk_netto))


def _suma(ramka, kolumna: str) -> Decimal:
    if ramka.empty or kolumna not in ramka.columns:
        return Decimal("0.00")
    return stawki.do_groszy(
        sum((Decimal(str(x)) for x in ramka[kolumna]), Decimal("0.00")))


def zaplaty_podatkowe(wpisy_budzetu):
    """Wpisy budżetu liczące się jako zapłata podatku — jeden nośnik reguły.

    Zakupy i czynsz nie są zapłatą podatku; bez tego filtru każdy wydatek
    zbijałby rezerwę i kafel pokazywałby zero przez całe życie.
    """
    if wpisy_budzetu is None or wpisy_budzetu.empty:
        return wpisy_budzetu
    return wpisy_budzetu[
        (wpisy_budzetu["typ"] == budzet.TYP_WYDATKI)
        & (wpisy_budzetu["kategoria"] == budzet.KATEGORIA_PODATKI)]


#: Nazwa pozycji podatku dochodowego na ekranie, per forma. Jeden nośnik —
#: `terminy.TERMINY` używa tych samych napisów jako `Termin.nazwa`.
NAZWA_PODATKU = {"RYCZALT": "Ryczałt", "SKALA": "PIT"}


@dataclass(frozen=True)
class StanRoku:
    """Stan przebiegu narastajaco dla SKALI na koniec danego roku.

    Wydzielone z `_podatek_dochodowy` w Z63 jako JEDEN NOSNIK tego przebiegu.
    Drugim konsumentem jest prognoza plynnosci: bez tego stanu pierwsza
    prognozowana zaliczka startowala by od zera i **zanizala PIT** — a zanizenie
    idzie w kierunku, ktory poprawia obraz.

    `zaliczki_przed_zaokragleniem`, nie po: tak kumuluje silnik i tak trzeba je
    podac dalej. Placi sie kwote PO zaokragleniu, ale narastajaco niesie kwote
    przed nim — kumulowanie zaokraglonych daloby rozjazd rosnacy z kazdym
    miesiacem i nigdy nieprzekraczajacy progu, ktory ktos by zauwazyl.

    `faktur` to kontrola licznosci: przebieg, do ktorego nic nie dotarlo,
    zwraca zera nieodroznialne od „rok bez podatku".
    """

    rok: int
    dochod_narastajaco: Decimal
    zaliczki_przed_zaokragleniem: Decimal
    faktur: int


def _koszty_wg_miesiaca(koszty, rok: int) -> "dict[str, Decimal]":
    """Koszty netto danego ROKU, zsumowane po miesiacu (`YYYY-MM`).

    Rok bierze sie z DATY KOSZTU, nie z daty faktury — inaczej koszt z grudnia
    pomniejszalby dochod stycznia nastepnego roku (przelom roku, straznik
    `test_koszt_GRUDNIOWY_nie_pomniejsza_dochodu_STYCZNIA`).

    Podstawe pomniejsza kwota NETTO. VAT z tego samego kosztu odlicza sie
    osobno, w `vat_naliczony` — wziecie brutto liczyloby VAT dwa razy.
    """
    wynik: dict[str, Decimal] = {}
    if koszty is None or getattr(koszty, "empty", True):
        return wynik
    if "data" not in koszty.columns or "kwota_netto" not in koszty.columns:
        return wynik
    prefiks = str(int(rok))
    for _, wiersz in koszty.iterrows():
        data = str(wiersz["data"])
        if not data.startswith(prefiks):
            continue
        miesiac = data[:7]
        wynik[miesiac] = wynik.get(miesiac, Decimal("0.00")) + Decimal(
            str(wiersz["kwota_netto"]))
    return {m: stawki.do_groszy(k) for m, k in wynik.items()}


def stan_roku_skali(faktury, rok: int, *, koszty=None) -> StanRoku:
    """Przebieg narastajaco skali przez JEDEN rok, faktura po fakturze.

    Kolejnosc ma znaczenie i dlatego to nie jest suma niezaleznych skladnikow:
    zaliczka miesiaca M zalezy od dochodu i zaliczek wszystkich miesiecy
    wczesniejszych (Z58, D6).

    KOSZTY (dolozone 2026-08-28). Regula Darka z godz. 19:50: *„Koszty sa
    rozliczane co miesiac, miesiac po miesiacu"* — koszt danego miesiaca
    pomniejsza dochod TEGO miesiaca. Narastajaco idzie **prog podatkowy**,
    a nie koszt: dochod od poczatku roku budowany jest z miesiecy JUZ
    pomniejszonych o koszty, wiec koszt wchodzi do narastania dokladnie raz.

    Miesiac z dwiema fakturami odejmuje koszt przy PIERWSZEJ — druga dostaje
    zero, tak samo jak nie nalicza drugi raz skladek.

    Miesiac z kosztem, ale BEZ faktury, przechodzi ta sama droga jako przebieg
    o zerowym przychodzie. Bez tego koszt z takiego miesiaca gindalby, a rezerwa
    zostawalaby zawyzona — czyli dokladnie wada, ktora ta zmiana naprawia.
    """
    dochod = Decimal("0.00")
    zaliczki = Decimal("0.00")
    ile = 0
    koszty_miesiaca = _koszty_wg_miesiaca(koszty, rok)
    if faktury is not None and not faktury.empty:
        prefiks = str(int(rok))
        w_roku = faktury[[str(d).startswith(prefiks) for d in faktury["data"]]]
        # Sortowanie przeniesione z `_podatek_dochodowy` bez zmian, ale
        # OPISANE JAWNIE JAKO NIESTRZEZONE (CLAUDE.md §8 v1.17): mutacja
        # „zdejmij sortowanie" przezyla 722 testy i jest fizycznie
        # nieczerwieniaca. Zmierzony powod: wynik tej funkcji NIE ZALEZY od
        # kolejnosci — dochod narastajaco to suma, a zaliczki teleskopuja sie
        # do podatku od dochodu koncowego; liczba miesiecy ze skladkami tez
        # nie zalezy od kolejnosci. Do tego kazdy wolajacy dostaje ramke juz
        # posortowana (`magazyn.wczytaj_faktury`: ORDER BY data, id).
        # Prog: pierwszy konsument czytajacy wartosci MIESIECZNE musi
        # przyniesc wlasnego straznika — dla niego kolejnosc zacznie znaczyc.
        w_roku = w_roku.sort_values("data")
        widziane_miesiace: set[str] = set()
        for _, wiersz in w_roku.iterrows():
            miesiac = str(wiersz["data"])[:7]
            juz = miesiac in widziane_miesiace
            widziane_miesiace.add(miesiac)
            wynik = policz_skala(
                kwota_netto=Decimal(str(wiersz["kwota_netto"])),
                stawka_vat=Decimal("0"),
                dochod_narastajaco=dochod,
                zaliczki_juz_naliczone=zaliczki,
                skladki_juz_naliczone_w_miesiacu=juz,
                koszty=(Decimal("0.00") if juz
                        else koszty_miesiaca.pop(miesiac, Decimal("0.00"))))
            dochod = wynik.dochod_narastajaco
            zaliczki += wynik.zaliczka_przed_zaokragleniem
            ile += 1

    # Miesiace, w ktorych byl KOSZT, ale nie bylo zadnej faktury. Ta sama
    # droga, przychod zerowy; skladki oznaczone jako juz naliczone, bo ZUS
    # rezerwy liczy `skladki_zus_za_miesiace`, a nie ta petla.
    for miesiac in sorted(koszty_miesiaca):
        wynik = policz_skala(
            kwota_netto=Decimal("0"), stawka_vat=Decimal("0"),
            dochod_narastajaco=dochod, zaliczki_juz_naliczone=zaliczki,
            skladki_juz_naliczone_w_miesiacu=True,
            koszty=koszty_miesiaca[miesiac])
        dochod = wynik.dochod_narastajaco
        zaliczki += wynik.zaliczka_przed_zaokragleniem

    return StanRoku(rok=int(rok), dochod_narastajaco=dochod,
                    zaliczki_przed_zaokragleniem=zaliczki, faktur=ile)


def _podatek_dochodowy(faktury, forma: str, koszty=None) -> Decimal:
    """Podatek dochodowy naliczony ze wszystkich faktur, według formy.

    **Koszty przekazuje się WYŁĄCZNIE do skali** (naprawa 2026-08-28). Przy
    ryczałcie podstawą jest przychód, więc koszt jej nie dotyka — przekazanie
    ich bezwarunkowo **zaniżyłoby** ryczałt, a za niska rezerwa to niedopłata
    do urzędu, czyli wada groźniejsza od naprawianej. Broni tego
    `test_koszt_NIE_RUSZA_podatku_przy_RYCZALCIE`.

    **Ryczałt** odzyskuje się z zapisanych pól faktury (odwrócenie tożsamości
    `zysk = netto − składki − pit`) — dokładnie co do grosza, bez powtarzania
    zaokrągleń.

    **Skala** tak się nie da: faktury zapisano polami wyliczonymi wtedy, gdy
    aplikacja znała tylko ryczałt, więc `zysk_netto` niesie liczbę ryczałtową.
    PIT skali liczy się więc OD NOWA, rok po roku, miesiąc po miesiącu —
    zaliczka narastająco (Z58) wymaga kolejności, a nie sumy niezależnych
    składników.
    """
    if faktury is None or faktury.empty:
        return Decimal("0.00")

    if forma == "RYCZALT":
        return stawki.do_groszy(sum(
            (ryczalt_z_faktury(kwota_netto=w["kwota_netto"],
                               zaplacony_zus=w["zaplacony_zus"],
                               zysk_netto=w["zysk_netto"])
             for _, w in faktury.iterrows()), Decimal("0.00")))

    razem = Decimal("0.00")
    for rok in sorted({str(d)[:4] for d in faktury["data"]}):
        stan = stan_roku_skali(faktury, int(rok), koszty=koszty)
        razem += stawki.do_zlotych(
            max(Decimal("0"), stan.zaliczki_przed_zaokragleniem))
    return razem


def rezerwa_na_podatki(faktury, koszty, wpisy_budzetu, *,
                       dzialalnosc_od: "date | None",
                       dzis: date,
                       forma: str,
                       stawka_ryczaltu: "Decimal | None" = None
                       ) -> RezerwaPodatkowa:
    """Ile jeszcze nie zapłaciłeś: naliczone zobowiązania minus zapłaty.

    `forma` NIE MA wartości domyślnej i mieć jej nie będzie (2026-08-28).
    Domyślna — obojętne, czy `"RYCZALT"`, czy `"SKALA"` — zgaduje za
    wołającego i zgaduje po cichu: liczba wychodzi wiarygodna, tylko policzona
    nie tą formą, którą wybrał użytkownik. Powód nazwany w nagłówku modułu.

    `wpisy_budzetu` to CAŁA tabela wpisów — filtrowanie po typie i kategorii
    siedzi tutaj, żeby reguła „co liczy się jako zapłata podatku" miała jeden
    nośnik. Wołający, który filtrowałby sam, byłby drugim.

    DWA UCIĘCIA, KTÓRE ŁATWO POMYLIĆ:

    `vat_do_zaplaty` nie schodzi poniżej zera — nadwyżka VAT-u naliczonego to
    **zwrot z urzędu**, osobna sprawa i osobny wniosek. Przelanie tej nadwyżki
    na ZUS zaniżyłoby rezerwę na składki, które trzeba zapłacić w całości
    niezależnie od VAT-u.

    `saldo` ucięcia NIE ma i mieć nie może. Nadpłata jest prawdziwą
    informacją; zerowanie jej zamienia „masz u urzędu 800 zł" na „jesteś na
    zero" i te 800 zł znika z obrazu finansów.

    DŁUG SPŁACONY (Zadanie 23): do czasu powstania tabeli `koszty_jdg`
    parametr `koszty` miał wartość domyślną `None` z jawnym progiem
    „zniknie, gdy tabela powstanie". Tabela jest, więc oba parametry są
    obowiązkowe — pominięcie kosztów albo zapłat nie może być przeoczeniem.
    """
    if forma not in NAZWA_PODATKU:
        raise BladMagazynu(
            f"Nie policzę rezerwy: forma opodatkowania to {forma!r}. "
            f"Wskaż formę na ten rok w Ustawieniach — aplikacja jej nie "
            f"zgadnie, a odkładanie pieniędzy według zgadniętej formy to "
            f"realna szkoda, nie niedokładność raportu.")
    if forma == "RYCZALT" and stawka_ryczaltu is None:
        raise BladMagazynu(
            "Ryczałt bez stawki to forma, ktorej nie da się policzyć. "
            "Uzupełnij stawkę ryczałtu w Ustawieniach.")

    vat_nalezny = _suma(faktury, "kwota_vat")
    vat_naliczony = _suma(koszty, "kwota_vat")
    vat_do_zaplaty = max(Decimal("0.00"), vat_nalezny - vat_naliczony)

    # ZUS z MIESIĘCY DZIAŁALNOŚCI, nie z kolumny `zaplacony_zus` (Z55).
    # Tamta kolumna zostaje w tabeli jako zapis historyczny rozbicia faktury
    # i odpowiada na inne pytanie — patrz `skladki_zus_za_miesiace`.
    zastrzezenia: tuple[str, ...] = ()
    if dzialalnosc_od is None:
        zus = Decimal("0.00")
        miesiace_zus = None
        zus_wg_miesiaca: tuple = ()
        zastrzezenia = (
            "Składki ZUS nie zostały policzone: nie znam daty rozpoczęcia "
            "działalności. Podaj ją w Ustawieniach — bez niej ta kwota jest "
            "zaniżona o pełne składki za każdy miesiąc.",)
    elif dzialalnosc_od > dzis:
        # Data rozpoczęcia W PRZYSZŁOŚCI to prawdziwy stan użytkownika
        # („zaczynam 1 września"), a nie pomyłka. `miesiace_dzialalnosci`
        # zostaje surowe i rzuca błędem na odwróconych datach — tam jest to
        # poprawne. Tutaj rzucenie wyjątkiem wysypywało CAŁY kafelek Pulpitu
        # (znalezione strażnikiem ekranu w Z59, przeżyło dwa przebiegi
        # mutacyjne Z54 i Z55, bo żaden test nie wpisywał daty przyszłej).
        zus = Decimal("0.00")
        miesiace_zus = 0
        zus_wg_miesiaca: tuple = ()
        zastrzezenia = (
            f"Działalność zaczyna się {dzialalnosc_od.isoformat()}, czyli "
            f"w przyszłości — składek ZUS jeszcze nie ma. Rezerwa obejmuje "
            f"na razie tylko VAT i podatek dochodowy.",)
    else:
        skladki = skladki_zus_za_miesiace(faktury, od=dzialalnosc_od, do=dzis,
                                          forma=forma)
        zus = skladki.razem
        miesiace_zus = skladki.miesiace
        zus_wg_miesiaca = skladki.wg_miesiaca

    podatek_dochodowy = _podatek_dochodowy(faktury, forma, koszty)

    zaplacone = _suma(zaplaty_podatkowe(wpisy_budzetu), "kwota")

    naliczone = vat_do_zaplaty + zus + podatek_dochodowy
    return RezerwaPodatkowa(
        vat_nalezny=vat_nalezny, vat_naliczony=vat_naliczony,
        vat_do_zaplaty=vat_do_zaplaty, zus=zus,
        podatek_dochodowy=podatek_dochodowy,
        naliczone_razem=naliczone, zaplacone=zaplacone,
        saldo=naliczone - zaplacone,
        miesiace_zus=miesiace_zus, zastrzezenia=zastrzezenia,
        forma=forma, nazwa_podatku=NAZWA_PODATKU[forma],
        dzialalnosc_od=dzialalnosc_od, zus_wg_miesiaca=zus_wg_miesiaca)


def rezerwa_z_bazy(polaczenie, *, wpisy=None,
                   dzis: "date | None" = None) -> RezerwaPodatkowa:
    """Cienki zbieracz: czyta bazę, woła `rezerwa_na_podatki`, ZERO rachunku.

    Powstał w Z55 razem z dwoma nowymi argumentami. Bez niego cztery ekrany
    (pulpit, budżet, JDG, narzędzia doradcy) powtarzałyby ten sam zestaw
    odczytów, a data rozpoczęcia działalności miałaby cztery drogi do silnika
    — czyli cztery okazje, żeby jedna z nich jej nie podała i pokazała
    zaniżoną rezerwę bez zastrzeżenia.

    Rozdział jest ten sam co w prognozie płynności (Z62/Z63): rachunek jest
    czysty i sprawdzalny na argumentach, zbieranie jest osobno i cienkie.
    """
    if wpisy is None:
        wpisy = magazyn.wczytaj_wpisy(polaczenie)
    dzis = dzis or date.today()
    forma = magazyn.forma_na_rok(polaczenie, dzis.year)
    return rezerwa_na_podatki(
        magazyn.wczytaj_faktury(polaczenie),
        magazyn.wczytaj_koszty(polaczenie),
        wpisy,
        dzialalnosc_od=magazyn.odczytaj_dzialalnosc_od(polaczenie),
        dzis=dzis,
        forma=forma.forma,
        stawka_ryczaltu=forma.stawka_ryczaltu)


def policz_fakture_z_bazy(polaczenie, *, kwota_netto: Decimal,
                          stawka_vat: Decimal, dzien: "date | None" = None):
    """Rozbicie JEDNEJ faktury według formy ZAPISANEJ W BAZIE. Cienki zbieracz.

    Zwraca parę `(forma, wyliczenie)`: `Wyliczenie` przy ryczałcie,
    `WyliczenieSkali` przy skali. Pola wspólne noszą te same nazwy, więc ekran
    czyta obie tak samo (patrz nagłówek `WyliczenieSkali`).

    DLACZEGO TO ISTNIEJE. Formularz faktury (`pulpit/jdg.py`) i narzędzie
    doradcy (`rdzen/narzedzia.py`) wołały `policz_ryczalt` BEZWARUNKOWO —
    liczyły ryczałtem komuś, kto jest na skali, i robiły to wiarygodnie.
    Rachunek jest tu WOŁANY, nie powtórzony: rozgałęzienie po formie siedzi
    w `policz`, komplet argumentów w `argumenty_dla_formy`, a ta funkcja
    wyłącznie czyta bazę. Wołający, który zbierałby dane sam, byłby drugim
    nośnikiem reguły „którą formą liczyć fakturę".

    Rok bierze się z DATY FAKTURY, nie z dzisiejszej: forma jest zapisana na
    rok, a faktura grudniowa wystawiona w styczniu rozliczana jest formą
    swojego roku.
    """
    dzien = dzien or date.today()
    forma = magazyn.forma_na_rok(polaczenie, dzien.year)
    naliczone = magazyn.czy_skladki_naliczone_w_miesiacu(
        polaczenie, dzien.year, dzien.month)

    dochod = Decimal("0")
    zaliczki = Decimal("0")
    if forma.forma == magazyn.FORMA_SKALA:
        # Stan roku WOLANY, nie liczony — ten sam nosnik co w prognozie (Z63).
        stan = stan_roku_skali(magazyn.wczytaj_faktury(polaczenie), dzien.year)
        dochod = stan.dochod_narastajaco
        zaliczki = stan.zaliczki_przed_zaokragleniem

    wyliczenie = policz(forma.forma, **argumenty_dla_formy(
        forma.forma, kwota_netto=Decimal(kwota_netto),
        stawka_vat=Decimal(stawka_vat), stawka_ryczaltu=forma.stawka_ryczaltu,
        przychod_narastajaco=magazyn.przychod_narastajaco(
            polaczenie, dzien.year),
        dochod_narastajaco=dochod, zaliczki_naliczone=zaliczki,
        skladki_juz_naliczone_w_miesiacu=naliczone))
    return forma, wyliczenie


@dataclass(frozen=True)
class PozycjaDoZaplaty:
    """Jedna danina czekająca na przelew: ile, do kiedy, za jaki okres."""

    nazwa: str
    kwota: Decimal
    termin: date
    za_okres: date


def do_zaplaty(rezerwa: RezerwaPodatkowa, dzis: date,
               wpisy_budzetu) -> list[PozycjaDoZaplaty]:
    """Rozbija saldo rezerwy na daniny z terminami — od najbliższego terminu.

    DLACZEGO ZAPŁATA ZDEJMUJE OD NAJWCZEŚNIEJSZEGO TERMINU. Budżet nie wie,
    której daniny dotyczył przelew — wpis w kategorii `Podatki i ZUS` to
    zwykły wydatek z kwotą. Zakładamy więc kolejność naturalną: płaci się
    najpierw to, co ma najbliższy termin. Rozliczanie od najdalszego
    pokazywałoby jako niezapłacone dokładnie to, co przed chwilą zapłaciłeś.

    Pozycje na 0,00 zł i nadpłata NIE trafiają na listę: pozycja zerowa to
    szum, a ujemna sugerowałaby, że urząd ma Ci coś oddać w tej konkretnej
    daninie — a to osobna sprawa i osobny wniosek.

    CZEGO TA FUNKCJA NIE WIE: którego miesiąca rozliczeniowego dotyczy dana
    złotówka. Saldo z definicji nie śledzi okresów (decyzja D3) — `za_okres`
    opisuje okres, którego dotyczy **najbliższy termin**, a nie pochodzenie
    kwoty. Faktura z sierpnia rodzi VAT płatny 25 września, a najbliższy
    termin 25 sierpnia dotyczy lipca; przypisanie kwoty do lipca byłoby więc
    twierdzeniem bez pokrycia. Interfejs mówi o tym wprost zamiast udawać.

    Kolejność i terminy pochodzą z `rdzen.terminy`; kwoty z `rezerwa`.
    Ten moduł niczego nie liczy od nowa.
    """
    from silnik.rdzen import terminy as _terminy

    # Filtr po formie robi TUTAJ ekran — nośnik `terminy.TERMINY` zostaje
    # kompletny, żeby `weryfikacja` dalej sprawdzała frazy wszystkich form.
    najblizsze = _terminy.najblizsze(dzis, forma=rezerwa.forma,
                                     dzialalnosc_od=rezerwa.dzialalnosc_od)

    # KROK 0 — lista OBOWIĄZKÓW: nazwa, okres, termin, kwota.
    #
    # ZUS rozbija się na miesiące (wada 2, 2026-08-28). Do tej daty cała kwota
    # szła na JEDEN najbliższy termin: odczyt 6 października dawał
    # `ZUS 5 120,65 zł do 20 X`, a to dwie składki, z których na ten dzień
    # wymagalna jest jedna. VAT i podatek dochodowy zostają na razie jedną
    # pozycją — ich rozbicie na okresy wymaga rozstrzygnięcia kasowe kontra
    # memoriałowe (wada 3) i jest osobnym plasterkiem.
    obowiazki: list[list] = []
    if rezerwa.zus_wg_miesiaca:
        for okres, kwota in rezerwa.zus_wg_miesiaca:
            obowiazki.append(["ZUS", okres,
                              _terminy.platnosc_za_okres("ZUS", okres), kwota])
    for termin in najblizsze:
        if termin.nazwa == "ZUS" and rezerwa.zus_wg_miesiaca:
            continue        # już rozbite wyżej, na okresy
        kwota = {"VAT": rezerwa.vat_do_zaplaty, "ZUS": rezerwa.zus,
                 rezerwa.nazwa_podatku: rezerwa.podatek_dochodowy}.get(
                     termin.nazwa, Decimal("0.00"))
        obowiazki.append([termin.nazwa, termin.za_okres, termin.data, kwota])

    # Płaci się najpierw to, co ma najbliższy termin — także W OBRĘBIE jednej
    # daniny: zapłata ZUS-u schodzi z września, zanim ruszy październik.
    obowiazki.sort(key=lambda o: (o[2], o[0]))

    # KROK 1 — zapłaty PODPISANE nazwą daniny idą na tę daninę.
    # Przycisk „Zapłacone" przy pozycji zapisuje wydatek zaczynający się od
    # nazwy; bez tego kroku kliknięcie przy Ryczałcie zdejmowało kwotę
    # z VAT-u (bo VAT miał bliższy termin) i przycisk mówił co innego, niż
    # robił. Zdarzyło się realnie 2026-08-25, wykryte klikaniem, nie testem.
    nierozpoznane = Decimal("0.00")
    for _, wpis in _wiersze(zaplaty_podatkowe(wpisy_budzetu)):
        kwota = Decimal(str(wpis["kwota"]))
        opis = str(wpis.get("szczegoly", ""))
        pasujace = [o for o in obowiazki if opis.startswith(o[0])]
        if not pasujace:
            nierozpoznane += kwota
            continue
        for obowiazek in pasujace:          # już posortowane po terminie
            zdjete = min(obowiazek[3], kwota)
            obowiazek[3] -= zdjete
            kwota -= zdjete
            if kwota <= 0:
                break

    # KROK 2 — reszta (wpisy ręczne, bez nazwy daniny) idzie od NAJBLIŻSZEGO
    # terminu: płaci się najpierw to, co najpilniejsze.
    pozycje = []
    for nazwa, okres, termin, kwota in obowiazki:
        pokryte = min(kwota, nierozpoznane)
        nierozpoznane -= pokryte
        reszta = kwota - pokryte
        if reszta > 0:
            pozycje.append(PozycjaDoZaplaty(
                nazwa=nazwa, kwota=reszta, termin=termin, za_okres=okres))
    return pozycje


def _wiersze(ramka):
    """Iteracja po wierszach, odporna na pustą i na brakującą ramkę."""
    if ramka is None or getattr(ramka, "empty", True):
        return []
    return list(ramka.iterrows())

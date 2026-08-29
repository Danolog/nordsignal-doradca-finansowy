"""Okres podgladu — nastawy ekranu zamieniane na zakres miesiecy.

Nosnik przeniesiony z `pulpit/wspolne.py` w Z65. Powod jest ten sam co przy
`budzet.bez_podatkow` w Z61: **warstwa HTTP nie moze importowac `pulpit/`**
(granica pilnowana przez `testy/test_granice.py`), a skopiowanie listy nastaw
daloby uzytkownikowi dwie rozne listy opcji w dwoch miejscach tej samej
aplikacji — dokladnie to, przed czym broni komentarz przy tej liscie od Z49.

`pulpit.wspolne` te nazwy RE-EKSPORTUJE, nie powtarza.
"""

from silnik.rdzen import budzet

#: Nastawy okresu podgladu. JEDEN nosnik dla Pulpitu, Budzetu i warstwy HTTP.
NASTAWY_OKRESU = {
    "miesiac": "Wybrany miesiąc",
    "3": "Ostatnie 3 miesiące",
    "6": "Ostatnie 6 miesięcy",
    "12": "Ostatnie 12 miesięcy",
    "rok": "Rok kalendarzowy",
    "reczny": "Zakres ręczny",
}


def zakres(nastawa: str, okres: str, od: str | None = None,
           do: str | None = None) -> budzet.Okres:
    """Zamienia nastawe ekranu na `Okres`.

    Wybrany miesiac jest KONCEM okresow „ostatnie N" — tak dziala
    `budzet.ostatnie_miesiace`. Inna kotwica dalaby dwa sprzeczne znaczenia
    tego samego wyboru na jednym ekranie.
    """
    rok, miesiac = (int(x) for x in okres.split("-"))
    if nastawa == "miesiac":
        return budzet.Okres((rok, miesiac), (rok, miesiac))
    if nastawa == "rok":
        return budzet.Okres((rok, 1), (rok, 12))
    if nastawa == "reczny":
        krance = [tuple(int(x) for x in (kraniec or okres).split("-"))
                  for kraniec in (od, do)]
        return budzet.Okres(krance[0], krance[1])
    miesiace = budzet.ostatnie_miesiace(rok, miesiac, int(nastawa))
    return budzet.Okres(miesiace[0], miesiace[-1])

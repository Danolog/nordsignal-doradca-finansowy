"""Faktura papieru: pasma szumu, kazde jako para warstw (ciemna + jasna).

BARWY ZAPISANE SZESNASTKOWO — `feFlood flood-color` zamiast wpisywania
skladowych do macierzy `feColorMatrix`. Macierz robi wylacznie MASKE
(kanal alfa z szumu), barwe niesie `feFlood`. Dzieki temu w pliku makiety
nie ma ani jednej barwy zapisanej dziesietnie.
"""
from urllib.parse import quote


def svg(kafel=480, pasma=(), prog=0.5):
    """`pasma`: (bfx, bfy, oktawy, amp_ciemna, amp_jasna, ziarno_c, ziarno_j, barwa_c, barwa_j)."""
    cz = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{kafel}' height='{kafel}'>"]
    i = 0
    for bfx, bfy, okt, amp_c, amp_j, zc, zj, bc, bj in pasma:
        for ziarno, barwa, amp in ((zc, bc, amp_c), (zj, bj, amp_j)):
            a = amp / (1 - prog)
            cz.append(
                f"<filter id='f{i}' x='0' y='0' width='100%' height='100%'>"
                f"<feTurbulence type='fractalNoise' baseFrequency='{bfx} {bfy}' "
                f"numOctaves='{okt}' seed='{ziarno}' stitchTiles='stitch' result='szum'/>"
                f"<feColorMatrix in='szum' type='matrix' values='"
                f"0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 "
                f"{a/3:.4f} {a/3:.4f} {a/3:.4f} 0 {-a*prog:.4f}' result='maska'/>"
                f"<feFlood flood-color='{barwa}' result='barwa'/>"
                f"<feComposite in='barwa' in2='maska' operator='in'/></filter>"
                f"<rect width='100%' height='100%' filter='url(%23f{i})'/>")
            i += 1
    cz.append("</svg>")
    return "".join(cz)


def tlo(baza, pasma, kafel=480):
    d = quote(svg(kafel, pasma), safe="%")
    return (f"background-color: {baza}; "
            f"background-image: url('data:image/svg+xml,{d}'); background-repeat: repeat;")

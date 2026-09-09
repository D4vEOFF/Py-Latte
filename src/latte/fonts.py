"""Fontové presety.

Preset není jen jméno balíčku -- řada fontů potřebuje víc řádků preambule
(newtx, libertinus) a u unicodových enginů se sází úplně jinak (fontspec).
Preset proto drží obě varianty zvlášť a `preamble()` vrátí tu správnou
podle zvoleného enginu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

UNICODE_ENGINES = ("lualatex", "xelatex")
ENGINES = ("pdflatex",) + UNICODE_ENGINES


@dataclass(frozen=True)
class FontPreset:
    key: str
    label: str
    #: Řádky preambule pro pdflatex načtené brzy (jen textový font).
    pdftex: "list[str]" = field(default_factory=list)
    #: Řádky, které musí přijít až za amsmath a amsthm -- balíčky se
    #: sazbou matematiky (newtx, newpx, mathdesign) jinak jejich definice
    #: přepisují a překlad skončí na "Command already defined".
    pdftex_math: "list[str]" = field(default_factory=list)
    #: Preset si nese vlastní sadu AMS symbolů, amssymb se pak nenačítá.
    provides_math: bool = False
    #: Jméno OTF rodiny pro \setmainfont u lualatexu/xelatexu.
    otf_main: str = ""
    #: Jméno matematické OTF rodiny pro \setmathfont.
    otf_math: str = "Latin Modern Math"
    otf_sans: str = ""
    otf_mono: str = ""


PRESETS = {
    p.key: p
    for p in [
        FontPreset(
            key="cm",
            label="Computer Modern (výchozí font LaTeXu)",
            pdftex=[],
            otf_main="Latin Modern Roman",
            otf_math="Latin Modern Math",
            otf_sans="Latin Modern Sans",
            otf_mono="Latin Modern Mono",
        ),
        FontPreset(
            key="lmodern",
            label="Latin Modern (Computer Modern ve vektorové podobě)",
            pdftex=[r"\usepackage{lmodern}"],
            otf_main="Latin Modern Roman",
            otf_math="Latin Modern Math",
            otf_sans="Latin Modern Sans",
            otf_mono="Latin Modern Mono",
        ),
        FontPreset(
            key="libertinus",
            label="Libertinus (Linux Libertine)",
            # Libertinus AMS symboly (\mathbb a spol.) nedodává, amssymb
            # se proto načítá dál a font může přijít brzy.
            pdftex=[r"\usepackage{libertinus}"],
            otf_main="Libertinus Serif",
            otf_math="Libertinus Math",
            otf_sans="Libertinus Sans",
            otf_mono="Libertinus Mono",
        ),
        FontPreset(
            key="times",
            label="Times (newtx)",
            pdftex_math=[r"\usepackage{newtxtext,newtxmath}"],
            provides_math=True,
            otf_main="TeX Gyre Termes",
            otf_math="TeX Gyre Termes Math",
        ),
        FontPreset(
            key="palatino",
            label="Palatino (newpx)",
            pdftex_math=[r"\usepackage{newpxtext,newpxmath}"],
            provides_math=True,
            otf_main="TeX Gyre Pagella",
            otf_math="TeX Gyre Pagella Math",
        ),
        FontPreset(
            key="pxfonts",
            label="Palatino (pxfonts)",
            pdftex_math=[r"\usepackage{pxfonts}"],
            provides_math=True,
            otf_main="TeX Gyre Pagella",
            otf_math="TeX Gyre Pagella Math",
        ),
        FontPreset(
            key="charter",
            label="Charter (mathdesign)",
            pdftex_math=[r"\usepackage[charter]{mathdesign}"],
            provides_math=True,
            otf_main="XCharter",
            otf_math="XCharter Math",
        ),
        FontPreset(
            key="kpfonts",
            label="Kp-Fonts",
            pdftex_math=[r"\usepackage{kpfonts}"],
            provides_math=True,
            otf_main="TeX Gyre Pagella",
            otf_math="TeX Gyre Pagella Math",
        ),
        FontPreset(
            key="fourier",
            label="Utopia / Fourier",
            pdftex_math=[r"\usepackage{fourier}"],
            provides_math=True,
            otf_main="Erewhon",
            otf_math="Erewhon Math",
        ),
        FontPreset(
            key="helvet",
            label="Helvetica jako základní písmo (bezpatkový dokument)",
            pdftex=[
                r"\usepackage[scaled]{helvet}",
                r"\renewcommand{\familydefault}{\sfdefault}",
                r"\usepackage[helvet]{sfmath}",
            ],
            otf_main="TeX Gyre Heros",
            otf_math="TeX Gyre Heros Math",
        ),
    ]
}

DEFAULT_FONT = "cm"


def resolve(name: str, engine: str) -> FontPreset:
    """Vrátí preset pro dané jméno.

    U unicodových enginů je jméno, které mezi presety není, chápáno jako
    název systémového fontu pro fontspec. U pdflatexu takový font sázet
    nelze, proto tam neznámé jméno skončí chybou.
    """
    key = name.strip()
    if key in PRESETS:
        return PRESETS[key]
    if engine in UNICODE_ENGINES:
        return FontPreset(key=key, label=f"systémový font {key}", otf_main=key)
    from latte.errors import LatteError

    known = ", ".join(sorted(PRESETS))
    raise LatteError(
        f"Neznámý font {key!r} pro engine pdflatex.\n"
        f"  Dostupné presety: {known}\n"
        f"  Libovolný systémový font lze použít jen s --engine lualatex nebo xelatex."
    )


def preamble(preset: FontPreset, engine: str) -> str:
    """Textová část nastavení fontu.

    Matematiku řeší `math_preamble` zvlášť: unicode-math se musí načíst
    až za amsmath, tedy o kus níž v preambuli.
    """
    if engine in UNICODE_ENGINES:
        lines = [r"\usepackage{fontspec}", rf"\setmainfont{{{preset.otf_main}}}"]
        if preset.otf_sans:
            lines.append(rf"\setsansfont{{{preset.otf_sans}}}")
        if preset.otf_mono:
            lines.append(rf"\setmonofont{{{preset.otf_mono}}}")
        return "\n".join(lines)

    if not preset.pdftex:
        if preset.pdftex_math:
            return "% Font se načítá níž, spolu se sazbou matematiky."
        return (
            "% Computer Modern -- výchozí font LaTeXu, nepotřebuje žádný balíček."
        )
    return "\n".join(preset.pdftex)


def math_preamble(preset: FontPreset, engine: str) -> str:
    """Matematické symboly a matematický font.

    unicode-math si symboly bere z OTF fontu a s amssymb se nesnáší
    (obě strany definují tytéž příkazy), proto se u unicodových enginů
    amssymb vynechává.
    """
    if engine in UNICODE_ENGINES:
        lines = [
            "% amssymb se s unicode-math nesnáší -- symboly dodává matematický font.",
            r"\usepackage{unicode-math}",
        ]
        if preset.otf_math:
            lines.append(rf"\setmathfont{{{preset.otf_math}}}")
        return "\n".join(lines)

    lines: "list[str]" = []
    if preset.provides_math:
        lines.append(
            "% amssymb se nenačítá -- symboly dodává matematický font níže."
        )
    else:
        lines.append(r"\usepackage{amssymb}")
    lines.extend(preset.pdftex_math)
    return "\n".join(lines)


def encoding_preamble(engine: str) -> str:
    """Kódování vstupu a výstupu.

    fontspec si kódování řeší sám, inputenc a fontenc by u něj vadily.
    """
    if engine in UNICODE_ENGINES:
        return "% Kódování řeší fontspec, inputenc ani fontenc se nepoužívají."
    return "\n".join(
        [
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
        ]
    )

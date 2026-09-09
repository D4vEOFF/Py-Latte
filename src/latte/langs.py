"""Jazyky dokumentu.

Babel funguje ve všech třech enginech, takže se používá i pro lualatex
a xelatex; liší se jen to, co k němu přibude (csquotes, dělení slov).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    key: str
    label: str
    babel: str
    #: Styl uvozovek pro csquotes.
    csquotes: str
    #: Popisky, které se objeví ve vygenerovaném dokumentu.
    section_intro: str
    abstract: str
    #: Názvy vět a definic pro \newtheorem.
    thm_definition: str
    thm_theorem: str
    thm_lemma: str
    thm_proposition: str
    thm_corollary: str
    thm_example: str
    thm_note: str
    thm_proof: str
    #: Popisky sazby.
    label_algorithm: str
    label_listing: str
    label_toc: str
    label_sources: str


LANGUAGES = {
    lang.key: lang
    for lang in [
        Language(
            key="czech",
            label="čeština",
            babel="czech",
            csquotes="czech",
            section_intro="Úvod",
            abstract="Abstrakt",
            thm_definition="Definice",
            thm_theorem="Věta",
            thm_lemma="Lemma",
            thm_proposition="Tvrzení",
            thm_corollary="Důsledek",
            thm_example="Příklad",
            thm_note="Poznámka",
            thm_proof="Důkaz",
            label_algorithm="Algoritmus",
            label_listing="Výpis",
            label_toc="Obsah",
            label_sources="Zdroje",
        ),
        Language(
            key="slovak",
            label="slovenština",
            babel="slovak",
            csquotes="czech",
            section_intro="Úvod",
            abstract="Abstrakt",
            thm_definition="Definícia",
            thm_theorem="Veta",
            thm_lemma="Lema",
            thm_proposition="Tvrdenie",
            thm_corollary="Dôsledok",
            thm_example="Príklad",
            thm_note="Poznámka",
            thm_proof="Dôkaz",
            label_algorithm="Algoritmus",
            label_listing="Výpis",
            label_toc="Obsah",
            label_sources="Zdroje",
        ),
        Language(
            key="english",
            label="angličtina",
            babel="english",
            csquotes="english",
            section_intro="Introduction",
            abstract="Abstract",
            thm_definition="Definition",
            thm_theorem="Theorem",
            thm_lemma="Lemma",
            thm_proposition="Proposition",
            thm_corollary="Corollary",
            thm_example="Example",
            thm_note="Remark",
            thm_proof="Proof",
            label_algorithm="Algorithm",
            label_listing="Listing",
            label_toc="Contents",
            label_sources="References",
        ),
        Language(
            key="german",
            label="němčina",
            babel="ngerman",
            csquotes="german",
            section_intro="Einleitung",
            abstract="Zusammenfassung",
            thm_definition="Definition",
            thm_theorem="Satz",
            thm_lemma="Lemma",
            thm_proposition="Behauptung",
            thm_corollary="Korollar",
            thm_example="Beispiel",
            thm_note="Bemerkung",
            thm_proof="Beweis",
            label_algorithm="Algorithmus",
            label_listing="Listing",
            label_toc="Inhalt",
            label_sources="Quellen",
        ),
    ]
}

DEFAULT_LANG = "czech"

#: Krátké tvary, které se běžně píšou místo plného jména.
ALIASES = {
    "cs": "czech",
    "cz": "czech",
    "sk": "slovak",
    "en": "english",
    "de": "german",
}


def resolve(name: str) -> Language:
    key = ALIASES.get(name.strip().lower(), name.strip().lower())
    if key not in LANGUAGES:
        from latte.errors import LatteError

        known = ", ".join(sorted(LANGUAGES))
        raise LatteError(f"Neznámý jazyk {name!r}. Dostupné: {known}")
    return LANGUAGES[key]


def preamble(lang: Language) -> str:
    return "\n".join(
        [
            rf"\usepackage[{lang.babel}]{{babel}}",
            rf"\usepackage[autostyle=true,style={lang.csquotes}]{{csquotes}}",
        ]
    )

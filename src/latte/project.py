"""Zakládání projektů z šablon."""

from __future__ import annotations

import datetime as _datetime
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - starší Python
    import tomli as tomllib  # type: ignore[no-redef]

from latte import fonts, langs, templates, ui
from latte.errors import LatteError
from latte.templates import Template

#: Soubor, kterým si projekt pamatuje, jak byl vytvořen. `latte add`
#: z něj bere nastavení, aby nový podprojekt vypadal jako ty stávající.
MARKER = ".latte.toml"

SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class Settings:
    template: str
    documentclass: str
    class_options: str
    lang: str
    engine: str
    font: str
    author: str
    email: str
    institute: str
    title: str


def slugify(name: str) -> str:
    """Jméno adresáře bez znaků, které dělají potíže LaTeXu nebo shellu."""
    cleaned = SLUG_RE.sub("-", name.strip()).strip("-.")
    return cleaned or "projekt"


def title_from_slug(slug: str) -> str:
    words = re.split(r"[-_.]+", slug)
    words = [w for w in words if w]
    if not words:
        return slug
    first = words[0]
    return " ".join([first[:1].upper() + first[1:], *words[1:]])


def _latex_escape(text: str) -> str:
    """Ošetří znaky, které by v dosazeném textu rozbily překlad."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def build_context(
    settings: Settings, project_slug: str, *, assets_prefix: str
) -> "dict[str, str]":
    language = langs.resolve(settings.lang)
    preset = fonts.resolve(settings.font, settings.engine)
    today = _datetime.date.today()

    # latexmk se na engine ptá dvěma způsoby: přepínačem na příkazové
    # řádce a proměnnou $pdf_mode v .latexmkrc.
    latexmk_flag = {
        "pdflatex": "-pdf",
        "lualatex": "-lualatex",
        "xelatex": "-xelatex",
    }[settings.engine]
    latexmk_pdf_mode = {"pdflatex": "1", "lualatex": "4", "xelatex": "5"}[
        settings.engine
    ]

    return {
        "PROJECT_NAME": project_slug,
        "TITLE": _latex_escape(settings.title),
        "AUTHOR": _latex_escape(settings.author),
        "EMAIL": _latex_escape(settings.email),
        "INSTITUTE": _latex_escape(settings.institute),
        "DOCUMENTCLASS": settings.documentclass,
        "CLASS_OPTIONS": settings.class_options,
        "ENGINE": settings.engine,
        "LATEXMK_FLAG": latexmk_flag,
        "LATEXMK_PDF_MODE": latexmk_pdf_mode,
        "FONT": preset.key,
        "FONT_LABEL": preset.label,
        "FONT_SETUP": fonts.preamble(preset, settings.engine),
        "MATHFONT_SETUP": fonts.math_preamble(preset, settings.engine),
        "ENCODING_SETUP": fonts.encoding_preamble(settings.engine),
        "BABEL_SETUP": langs.preamble(language),
        "LANG": language.key,
        "BABEL": language.babel,
        "SECTION_INTRO": language.section_intro,
        "ABSTRACT": language.abstract,
        "THM_DEFINITION": language.thm_definition,
        "THM_THEOREM": language.thm_theorem,
        "THM_LEMMA": language.thm_lemma,
        "THM_PROPOSITION": language.thm_proposition,
        "THM_COROLLARY": language.thm_corollary,
        "THM_EXAMPLE": language.thm_example,
        "THM_NOTE": language.thm_note,
        "THM_PROOF": language.thm_proof,
        "LABEL_ALGORITHM": language.label_algorithm,
        "LABEL_LISTING": language.label_listing,
        "LABEL_TOC": language.label_toc,
        "LABEL_SOURCES": language.label_sources,
        "ABSTRACT_LABEL": language.abstract,
        "ASSETS": assets_prefix,
        "DATE": today.isoformat(),
        "YEAR": str(today.year),
    }


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_marker(root: Path, settings: Settings) -> None:
    lines = [
        "# Vytvořeno nástrojem latte. Soubor slouží příkazu `latte add`.",
        "",
        f'template = "{_toml_escape(settings.template)}"',
        f'documentclass = "{_toml_escape(settings.documentclass)}"',
        f'class_options = "{_toml_escape(settings.class_options)}"',
        f'lang = "{_toml_escape(settings.lang)}"',
        f'engine = "{_toml_escape(settings.engine)}"',
        f'font = "{_toml_escape(settings.font)}"',
        f'author = "{_toml_escape(settings.author)}"',
        f'email = "{_toml_escape(settings.email)}"',
        f'institute = "{_toml_escape(settings.institute)}"',
        f'title = "{_toml_escape(settings.title)}"',
    ]
    (root / MARKER).write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_root(start: Path) -> "tuple[Path, Settings]":
    """Najde nejbližší nadřazený projekt latte a jeho nastavení."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        marker = candidate / MARKER
        if marker.is_file():
            with marker.open("rb") as handle:
                data = tomllib.load(handle)
            settings = Settings(
                template=str(data.get("template", "")),
                documentclass=str(data.get("documentclass", "beamer")),
                class_options=str(data.get("class_options", "")),
                lang=str(data.get("lang", langs.DEFAULT_LANG)),
                engine=str(data.get("engine", "pdflatex")),
                font=str(data.get("font", fonts.DEFAULT_FONT)),
                author=str(data.get("author", "")),
                email=str(data.get("email", "")),
                institute=str(data.get("institute", "")),
                title=str(data.get("title", "")),
            )
            return candidate, settings
    raise LatteError(
        f"V {start} ani v nadřazených adresářích není projekt latte "
        f"(chybí {MARKER})."
    )


def git_init(root: Path) -> bool:
    if shutil.which("git") is None:
        ui.warn("git není v PATH, repozitář se nezaložil.")
        return False
    if (root / ".git").exists():
        return False
    try:
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        ui.warn(f"git init selhal: {detail or exc}")
        return False
    return True


def create(
    template: Template,
    target: Path,
    settings: Settings,
    *,
    force: bool = False,
) -> "list[Path]":
    """Rozbalí šablonu do `target`."""
    if target.exists():
        if not target.is_dir():
            raise LatteError(f"{target} existuje a není adresář.")
        if any(target.iterdir()) and not force:
            raise LatteError(
                f"Adresář {target} není prázdný. Přepsat lze pomocí --force."
            )
    target.mkdir(parents=True, exist_ok=True)

    # Kostra podprojektu se do kořene monorepa nekopíruje -- rozbaluje ji
    # teprve `latte add` do vlastního podadresáře.
    skip = {template.subproject} if template.subproject else set()

    # V monorepu se sdílené soubory vkládají vždy z podprojektu, tedy
    # o adresář výš -- i když samy leží v kořeni.
    assets_prefix = "../assets" if template.kind == "monorepo" else "assets"

    context = build_context(settings, target.name, assets_prefix=assets_prefix)
    created = templates.copy_tree(template.path, target, context, skip=skip)
    write_marker(target, settings)
    return created


def add_subproject(
    template: Template,
    root: Path,
    name: str,
    settings: Settings,
    *,
    force: bool = False,
) -> "tuple[Path, list[Path]]":
    """Přidá do monorepa další podprojekt."""
    source = template.subproject_dir
    if template.kind != "monorepo" or source is None or not source.is_dir():
        raise LatteError(
            f"Šablona {template.name!r} podprojekty nepodporuje "
            f"(`latte add` funguje jen u monorepa)."
        )

    slug = slugify(name)
    target = root / slug
    if target.exists() and any(target.iterdir()) and not force:
        raise LatteError(
            f"Podprojekt {slug} už existuje. Přepsat lze pomocí --force."
        )
    target.mkdir(parents=True, exist_ok=True)

    # Podprojekt leží o úroveň níž, sdílené soubory jsou proto o adresář výš.
    context = build_context(settings, slug, assets_prefix="../assets")
    context["TITLE"] = _latex_escape(settings.title or title_from_slug(slug))
    created = templates.copy_tree(source, target, context)
    return target, created

"""Vyhledávání šablon a jejich rozbalení do nového projektu.

Šablona je adresář s `template.toml` a stromem souborů. Platí dvě
konvence, díky nimž šablona nepotřebuje žádný další popis:

* soubor s příponou ``.tmpl`` se prožene dosazováním zástupných symbolů
  a přípona se odstraní; ostatní soubory se kopírují beze změny,
* segment cesty začínající na ``dot-`` se přejmenuje na ``.`` --
  adresáře jako ``.vscode`` se totiž do balíčku spolehlivě nezabalí.

Uživatelské šablony v konfiguračním adresáři mají přednost před
vestavěnými, takže vestavěnou šablonu lze přebít stejnojmennou vlastní.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - starší Python
    import tomli as tomllib  # type: ignore[no-redef]

from latte import config
from latte.errors import LatteError

BUILTIN_DIR = Path(__file__).resolve().parent / "templates"

PLACEHOLDER = re.compile(r"%%([A-Z][A-Z0-9_]*)%%")

TEMPLATE_SUFFIX = ".tmpl"
DOT_PREFIX = "dot-"

#: Přípony, které se nikdy nepokoušíme číst jako text.
BINARY_SUFFIXES = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".eps",
    ".ttf", ".otf", ".woff", ".woff2", ".zip", ".ico",
}


@dataclass(frozen=True)
class Template:
    name: str
    path: Path
    label: str
    description: str
    kind: str  # "single" nebo "monorepo"
    documentclass: str
    class_options: str
    subproject: str
    builtin: bool

    @property
    def subproject_dir(self) -> "Path | None":
        if not self.subproject:
            return None
        return self.path / self.subproject


def _load_meta(path: Path, builtin: bool) -> Template:
    meta_file = path / "template.toml"
    if not meta_file.is_file():
        raise LatteError(f"Šabloně {path} chybí soubor template.toml.")
    with meta_file.open("rb") as handle:
        meta = tomllib.load(handle)

    kind = str(meta.get("kind", "single"))
    if kind not in ("single", "monorepo"):
        raise LatteError(
            f"Šablona {path.name}: kind musí být 'single' nebo 'monorepo', "
            f"ne {kind!r}."
        )

    return Template(
        name=str(meta.get("name", path.name)),
        path=path,
        label=str(meta.get("label", path.name)),
        description=str(meta.get("description", "")),
        kind=kind,
        documentclass=str(meta.get("documentclass", "article")),
        class_options=str(meta.get("class_options", "")),
        subproject=str(meta.get("subproject", "")),
        builtin=builtin,
    )


def _search_roots() -> "list[tuple[Path, bool]]":
    # Uživatelský adresář je první -- vyhrává nad vestavěnou šablonou.
    return [(config.user_templates_dir(), False), (BUILTIN_DIR, True)]


def available() -> "list[Template]":
    found: "dict[str, Template]" = {}
    for root, builtin in _search_roots():
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if entry.name in found:
                continue
            if not (entry / "template.toml").is_file():
                continue
            found[entry.name] = _load_meta(entry, builtin)
    return list(found.values())


def get(name: str) -> Template:
    for root, builtin in _search_roots():
        candidate = root / name
        if candidate.is_dir() and (candidate / "template.toml").is_file():
            return _load_meta(candidate, builtin)
    known = ", ".join(t.name for t in available()) or "žádné"
    raise LatteError(f"Neznámá šablona {name!r}. Dostupné: {known}")


def render_text(text: str, context: "dict[str, str]") -> str:
    """Dosadí ``%%KLÍČ%%``.

    Neznámý symbol je chyba šablony, ne důvod tiše vygenerovat rozbitý
    dokument -- takový projekt by po přeložení vypadal skoro správně.
    """
    missing: "set[str]" = set()

    def replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key not in context:
            missing.add(key)
            return match.group(0)
        return context[key]

    result = PLACEHOLDER.sub(replace, text)
    if missing:
        raise LatteError(
            "Šablona používá neznámé zástupné symboly: "
            + ", ".join(sorted(missing))
        )
    return result


def _target_name(name: str) -> str:
    if name.startswith(DOT_PREFIX):
        name = "." + name[len(DOT_PREFIX):]
    return name


def _rendered_name(name: str) -> "tuple[str, bool]":
    """Vrátí cílové jméno a příznak, zda se má obsah dosazovat."""
    if name.endswith(TEMPLATE_SUFFIX):
        return _target_name(name[: -len(TEMPLATE_SUFFIX)]), True
    return _target_name(name), False


def copy_tree(
    source: Path,
    target: Path,
    context: "dict[str, str]",
    *,
    skip: "set[str] | None" = None,
) -> "list[Path]":
    """Rozbalí strom šablony do cílového adresáře.

    Vrací seznam vytvořených souborů (relativně k `target`).
    """
    # template.toml popisuje šablonu, do vygenerovaného projektu nepatří.
    skip = set(skip or ()) | {"template.toml"}
    created: "list[Path]" = []

    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        if relative.parts[0] in skip:
            continue

        mapped = Path(*[_target_name(part) for part in relative.parts[:-1]])
        leaf, render = _rendered_name(relative.parts[-1])
        destination = target / mapped / leaf

        if item.is_dir():
            destination = target / Path(*[_target_name(p) for p in relative.parts])
            destination.mkdir(parents=True, exist_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        if render and item.suffix.lower() not in BINARY_SUFFIXES:
            text = item.read_text(encoding="utf-8")
            destination.write_text(render_text(text, context), encoding="utf-8")
        else:
            shutil.copy2(item, destination)
        created.append(destination.relative_to(target))

    return created

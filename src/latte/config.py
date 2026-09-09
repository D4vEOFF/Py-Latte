"""Uživatelská konfigurace.

Soubor je TOML v adresáři podle konvencí platformy:
    Linux/macOS   $XDG_CONFIG_HOME/latte/config.toml (jinak ~/.config/latte)
    Windows       %APPDATA%\\latte\\config.toml

Vedle něj žije adresář `templates/` s uživatelskými šablonami, které mají
přednost před vestavěnými.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - starší Python
    import tomli as tomllib  # type: ignore[no-redef]

from latte.errors import LatteError

APP_NAME = "latte"

#: Výchozí hodnoty. Klíče mimo tento slovník config odmítne -- překlep
#: v názvu volby by se jinak projevil až tím, že nastavení nic nedělá.
DEFAULTS: "dict[str, object]" = {
    "template": "article",
    "documentclass": "",
    "lang": "czech",
    "engine": "pdflatex",
    "font": "cm",
    "editor": "code",
    "open_editor": True,
    "git_init": True,
    "projects_dir": "",
    "author": "",
    "email": "",
    "institute": "",
}

BOOL_KEYS = {"open_editor", "git_init"}


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        root = Path(base) if base else Path.home() / ".config"
    return root / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def user_templates_dir() -> Path:
    return config_dir() / "templates"


def load() -> "dict[str, object]":
    """Konfigurace slitá s výchozími hodnotami."""
    values = dict(DEFAULTS)
    path = config_path()
    if not path.is_file():
        return values

    try:
        with path.open("rb") as handle:
            parsed = tomllib.load(handle)
    except Exception as exc:  # tomllib hlásí vlastní typ výjimky
        raise LatteError(f"Konfiguraci {path} se nepodařilo načíst: {exc}") from exc

    unknown = sorted(set(parsed) - set(DEFAULTS))
    if unknown:
        raise LatteError(
            f"Neznámé volby v {path}: {', '.join(unknown)}.\n"
            f"  Dostupné: {', '.join(sorted(DEFAULTS))}"
        )

    for key, value in parsed.items():
        expected = type(DEFAULTS[key])
        if not isinstance(value, expected):
            raise LatteError(
                f"Volba {key!r} v {path} má být typu {expected.__name__}, "
                f"ne {type(value).__name__}."
            )
        values[key] = value
    return values


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return str(value)


def save(values: "dict[str, object]") -> Path:
    """Zapíše konfiguraci; zapisují se všechny klíče, ať je soubor čitelný."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Konfigurace latte -- LaTeX Template To Editor.",
        "# Vygenerováno automaticky, ruční úpravy zůstanou zachovány.",
        "",
    ]
    for key in DEFAULTS:
        lines.append(f"{key} = {_toml_value(values.get(key, DEFAULTS[key]))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def coerce(key: str, raw: str) -> object:
    """Převede hodnotu z příkazové řádky na typ, který volba očekává."""
    if key not in DEFAULTS:
        known = ", ".join(sorted(DEFAULTS))
        raise LatteError(f"Neznámá volba {key!r}. Dostupné: {known}")
    if key in BOOL_KEYS:
        lowered = raw.strip().lower()
        if lowered in ("true", "1", "ano", "a", "yes", "y"):
            return True
        if lowered in ("false", "0", "ne", "n", "no"):
            return False
        raise LatteError(f"Volba {key!r} očekává true/false, dostala {raw!r}.")
    return raw

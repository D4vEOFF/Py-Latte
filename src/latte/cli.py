"""Příkazová řádka nástroje latte."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from latte import __version__, config, editor, fonts, langs, project, templates, ui
from latte.errors import LatteError
from latte.project import Settings

SUBCOMMANDS = ("new", "add", "config", "templates", "fonts")


# ---------------------------------------------------------------------------
# Sestavení parseru
# ---------------------------------------------------------------------------


def _add_project_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-t", "--template", help="šablona projektu")
    parser.add_argument(
        "-c",
        "--class",
        dest="documentclass",
        help="třída dokumentu (přebije výchozí třídu šablony)",
    )
    parser.add_argument(
        "--class-options", help="volby třídy, např. '12pt,a4paper'"
    )
    parser.add_argument("-f", "--font", help="font nebo fontový preset")
    parser.add_argument(
        "-e", "--engine", choices=fonts.ENGINES, help="překladač"
    )
    parser.add_argument("-l", "--lang", help="jazyk dokumentu")
    parser.add_argument("--title", help="název dokumentu")
    parser.add_argument("--author", help="autor")
    parser.add_argument("--email", help="kontaktní e-mail")
    parser.add_argument("--institute", help="instituce")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="latte",
        description="LaTeX Template To Editor -- rychlé zakládání LaTeXových projektů.",
        epilog="Bez argumentů se latte doptá na vše interaktivně.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"latte {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    new = sub.add_parser("new", help="založí nový projekt")
    new.add_argument("name", nargs="?", help="jméno projektu (i adresáře)")
    _add_project_options(new)
    new.add_argument(
        "-d", "--dir", help="nadřazený adresář (jinak projects_dir nebo .)"
    )
    new.add_argument("--editor", help="čím projekt otevřít")
    open_group = new.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open", dest="open_editor", action="store_true", default=None,
        help="otevřít v editoru",
    )
    open_group.add_argument(
        "--no-open", dest="open_editor", action="store_false",
        help="neotvírat editor",
    )
    git_group = new.add_mutually_exclusive_group()
    git_group.add_argument(
        "--git", dest="git_init", action="store_true", default=None,
        help="založit git repozitář",
    )
    git_group.add_argument(
        "--no-git", dest="git_init", action="store_false",
        help="nezakládat git repozitář",
    )
    new.add_argument(
        "-i", "--interactive", action="store_true",
        help="doptat se na všechny volby",
    )
    new.add_argument(
        "--force", action="store_true", help="rozbalit i do neprázdného adresáře"
    )

    add = sub.add_parser(
        "add", help="přidá podprojekt do existujícího monorepa"
    )
    add.add_argument("name", nargs="?", help="jméno podprojektu")
    add.add_argument("--title", help="název podprojektu")
    add.add_argument(
        "--force", action="store_true", help="přepsat existující podprojekt"
    )

    cfg = sub.add_parser("config", help="práce s konfigurací")
    cfg_sub = cfg.add_subparsers(dest="config_command")
    cfg_sub.add_parser("path", help="vypíše cestu ke konfiguraci")
    cfg_sub.add_parser("show", help="vypíše aktuální nastavení")
    cfg_sub.add_parser("init", help="vytvoří konfiguraci s výchozími hodnotami")
    cfg_sub.add_parser("edit", help="otevře konfiguraci v editoru")
    cfg_set = cfg_sub.add_parser("set", help="nastaví jednu volbu")
    cfg_set.add_argument("key")
    cfg_set.add_argument("value")

    sub.add_parser("templates", help="vypíše dostupné šablony")
    sub.add_parser("fonts", help="vypíše fontové presety")

    return parser


def _normalize_argv(argv: "list[str]") -> "list[str]":
    """Umožní zkratku ``latte muj-projekt`` místo ``latte new muj-projekt``."""
    if not argv:
        return ["new"]
    first = argv[0]
    if first in SUBCOMMANDS or first in ("-h", "--help", "-V", "--version"):
        return argv
    return ["new", *argv]


# ---------------------------------------------------------------------------
# Výpisy
# ---------------------------------------------------------------------------


def cmd_templates() -> int:
    found = templates.available()
    if not found:
        ui.warn("Žádné šablony nejsou k dispozici.")
        return 1
    width = max(len(t.name) for t in found)
    for template in found:
        origin = "vestavěná" if template.builtin else "uživatelská"
        print(f"  {ui.bold(template.name.ljust(width))}  {template.label}")
        print(f"  {' ' * width}  {ui.dim(origin + ' -- ' + str(template.path))}")
    return 0


def cmd_fonts() -> int:
    width = max(len(key) for key in fonts.PRESETS)
    print(ui.bold("Presety (pdflatex i unicodové enginy):"))
    for key, preset in fonts.PRESETS.items():
        default = ui.dim("  (výchozí)") if key == fonts.DEFAULT_FONT else ""
        print(f"  {ui.bold(key.ljust(width))}  {preset.label}{default}")
    print()
    print(
        ui.dim(
            "S --engine lualatex nebo xelatex lze místo presetu uvést jméno\n"
            "libovolného systémového fontu, například --font 'EB Garamond'."
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Konfigurace
# ---------------------------------------------------------------------------


def cmd_config(args: argparse.Namespace) -> int:
    command = args.config_command or "show"

    if command == "path":
        print(config.config_path())
        return 0

    if command == "show":
        values = config.load()
        path = config.config_path()
        state = "existuje" if path.is_file() else "neexistuje, platí výchozí hodnoty"
        print(ui.dim(f"# {path} ({state})"))
        width = max(len(key) for key in values)
        for key in config.DEFAULTS:
            print(f"  {key.ljust(width)} = {config.toml_value(values[key])}")
        return 0

    if command == "init":
        path = config.save(config.load())
        ui.ok(f"Konfigurace zapsána do {path}")
        return 0

    if command == "set":
        values = config.load()
        values[args.key] = config.coerce(args.key, args.value)
        path = config.save(values)
        ui.ok(f"{args.key} = {values[args.key]}  ({path})")
        return 0

    if command == "edit":
        path = config.config_path()
        if not path.is_file():
            config.save(config.load())
        command_line = config.load().get("editor") or os.environ.get("EDITOR") or "code"
        parts = str(command_line).split()
        executable = shutil.which(parts[0])
        if executable is None:
            raise LatteError(f"Editor {parts[0]!r} není v PATH.")
        subprocess.call([executable, *parts[1:], str(path)])
        return 0

    raise LatteError(f"Neznámý podpříkaz config {command!r}.")


# ---------------------------------------------------------------------------
# Zakládání projektu
# ---------------------------------------------------------------------------


def _resolve_settings(
    args: argparse.Namespace, values: "dict[str, object]", interactive: bool
) -> "tuple[templates.Template, str, Settings]":
    template_name = args.template or str(values["template"])
    if interactive:
        choices = [t.name for t in templates.available()]
        template_name = ui.ask_choice("Šablona", choices, template_name)
    template = templates.get(template_name)

    name = args.name
    if not name:
        name = ui.ask("Jméno projektu", "novy-projekt")
    slug = project.slugify(name)

    documentclass = args.documentclass or str(values["documentclass"]) or template.documentclass
    class_options = (
        args.class_options
        if args.class_options is not None
        else template.class_options
    )
    lang = args.lang or str(values["lang"])
    engine = args.engine or str(values["engine"])
    font = args.font or str(values["font"])
    title = args.title or project.title_from_slug(slug)
    author = args.author if args.author is not None else str(values["author"])
    email = args.email if args.email is not None else str(values["email"])
    institute = (
        args.institute if args.institute is not None else str(values["institute"])
    )

    header = {flag: bool(values[flag]) for flag in project.HEADER_FLAGS}

    if interactive:
        title = ui.ask("Název dokumentu", title)
        documentclass = ui.ask("Třída dokumentu", documentclass)
        engine = ui.ask_choice("Engine", list(fonts.ENGINES), engine)
        font = ui.ask("Font", font)
        lang = ui.ask("Jazyk", lang)
        author = ui.ask("Autor", author)
        email = ui.ask("E-mail", email)
        institute = ui.ask("Instituce", institute)

        header["header_titlepage"] = ui.ask_bool(
            "Titulní strana místo hlavičky", header["header_titlepage"]
        )
        header["header_author"] = ui.ask_bool(
            "Vypsat autora", header["header_author"]
        )
        # Kontakt si titulní strana sází sama; ptát se na přepínače
        # hlavičky by svádělo k tomu, že údaj vyjde dvakrát.
        if not header["header_titlepage"]:
            header["header_email"] = ui.ask_bool(
                "Vypsat e-mail", header["header_email"]
            )
            header["header_institute"] = ui.ask_bool(
                "Vypsat instituci", header["header_institute"]
            )
        header["header_date"] = ui.ask_bool("Vypsat datum", header["header_date"])
        header["header_toc"] = ui.ask_bool("Vložit obsah", header["header_toc"])

    # Ověření dřív, než vznikne první soubor -- nechceme po sobě uklízet
    # polovinu rozbaleného projektu.
    if engine not in fonts.ENGINES:
        raise LatteError(
            f"Neznámý engine {engine!r}. Dostupné: {', '.join(fonts.ENGINES)}"
        )
    langs.resolve(lang)
    fonts.resolve(font, engine)

    settings = Settings(
        template=template.name,
        documentclass=documentclass,
        class_options=class_options,
        lang=langs.resolve(lang).key,
        engine=engine,
        font=font,
        author=author,
        email=email,
        institute=institute,
        title=title,
        **header,
    )
    return template, slug, settings


def _header_summary(settings: Settings) -> str:
    """Co z hlavičky se vysází -- ve stejném pořadí jako dotazy."""
    if settings.header_titlepage:
        parts = ["titulní strana"]
    else:
        parts = ["hlavička"]
    if settings.header_author:
        parts.append("autor")
    if settings.header_email and not settings.header_titlepage:
        parts.append("e-mail")
    if settings.header_institute and not settings.header_titlepage:
        parts.append("instituce")
    if settings.header_date:
        parts.append("datum")
    if settings.header_toc:
        parts.append("obsah")
    return ", ".join(parts)


def _show_summary(
    template: templates.Template,
    settings: Settings,
    target: Path,
    *,
    do_git: bool,
    do_open: bool,
    editor_command: str,
) -> None:
    rows = [
        ("Adresář", str(target)),
        ("Šablona", template.name),
        ("Název dokumentu", settings.title),
        ("Třída", f"{settings.documentclass} [{settings.class_options}]"),
        ("Engine", settings.engine),
        ("Font", settings.font),
        ("Jazyk", settings.lang),
        ("Autor", settings.author or ui.dim("--")),
        ("E-mail", settings.email or ui.dim("--")),
        ("Instituce", settings.institute or ui.dim("--")),
        ("Hlavička", _header_summary(settings)),
        ("git repozitář", "ano" if do_git else "ne"),
        ("Otevřít v editoru", editor_command if do_open else "ne"),
    ]
    width = max(len(label) for label, _ in rows)
    print(ui.bold("Nastavení nového projektu:"))
    for label, value in rows:
        print(f"  {label.ljust(width)}  {value}")


def cmd_new(args: argparse.Namespace) -> int:
    values = config.load()

    def _target(slug: str) -> Path:
        parent_raw = args.dir or str(values["projects_dir"]) or "."
        return Path(os.path.expanduser(parent_raw)).resolve() / slug

    do_git = args.git_init if args.git_init is not None else bool(values["git_init"])
    do_open = (
        args.open_editor if args.open_editor is not None else bool(values["open_editor"])
    )
    editor_command = args.editor or str(values["editor"])

    # Bez jména projektu se stejně musíme doptat na všechno; jinak se
    # nejdřív ukážou výchozí hodnoty a doptávání spustí teprve odmítnutí.
    interactive = args.interactive or args.name is None
    if not interactive:
        template, slug, settings = _resolve_settings(args, values, False)
        _show_summary(
            template,
            settings,
            _target(slug),
            do_git=do_git,
            do_open=do_open,
            editor_command=editor_command,
        )
        interactive = not ui.ask_bool("Použít tyto hodnoty", True)

    if interactive:
        template, slug, settings = _resolve_settings(args, values, True)
        do_git = ui.ask_bool("Založit git repozitář", do_git)
        do_open = ui.ask_bool(f"Otevřít v editoru ({editor_command})", do_open)

    target = _target(slug)

    created = project.create(template, target, settings, force=args.force)

    ui.ok(f"Projekt {ui.bold(slug)} vytvořen v {target}")
    print(
        ui.dim(
            f"   šablona {template.name}, třída {settings.documentclass}, "
            f"engine {settings.engine}, font {settings.font}, jazyk {settings.lang}"
        )
    )
    print(ui.dim(f"   {len(created)} souborů"))

    if template.kind == "monorepo":
        ui.info(
            "Monorepo je prázdné. První prezentaci přidáte příkazem "
            + ui.bold("latte add <jmeno>")
            + " uvnitř projektu."
        )

    if do_git and project.git_init(target):
        ui.ok("git repozitář inicializován")

    if do_open and editor.open_project(editor_command, target):
        ui.ok(f"Otevírám v {editor_command}")

    return 0


def cmd_add(args: argparse.Namespace) -> int:
    root, settings = project.find_root(Path.cwd())
    template = templates.get(settings.template)

    name = args.name or ui.ask("Jméno podprojektu", "novy")
    slug = project.slugify(name)

    sub_settings = Settings(**vars(settings))
    sub_settings.title = args.title or project.title_from_slug(slug)

    target, created = project.add_subproject(
        template, root, slug, sub_settings, force=args.force
    )
    ui.ok(f"Podprojekt {ui.bold(slug)} vytvořen v {target}")
    print(ui.dim(f"   {len(created)} souborů"))
    return 0


# ---------------------------------------------------------------------------


def main(argv: "list[str] | None" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(argv))

    try:
        if args.command == "templates":
            return cmd_templates()
        if args.command == "fonts":
            return cmd_fonts()
        if args.command == "config":
            return cmd_config(args)
        if args.command == "add":
            return cmd_add(args)
        return cmd_new(args)
    except LatteError as exc:
        ui.error(str(exc))
        return 1
    except KeyboardInterrupt:
        print()
        ui.warn("Přerušeno.")
        return 130

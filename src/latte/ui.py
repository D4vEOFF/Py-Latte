"""Výpis do terminálu.

Barvy se zapínají jen tam, kde je terminál umí zobrazit; skript v rouře
nebo s nastaveným NO_COLOR dostane čistý text.
"""

from __future__ import annotations

import os
import sys


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        # Konzole Windows rozumí ANSI sekvencím teprve po zapnutí
        # zpracování virtuálního terminálu pro výstupní handle.
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            return False
    return True


ENABLED = _color_enabled()


def _wrap(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if ENABLED else text


def bold(text: str) -> str:
    return _wrap("1", text)


def dim(text: str) -> str:
    return _wrap("2", text)


def red(text: str) -> str:
    return _wrap("31", text)


def green(text: str) -> str:
    return _wrap("32", text)


def yellow(text: str) -> str:
    return _wrap("33", text)


def cyan(text: str) -> str:
    return _wrap("36", text)


def info(message: str) -> None:
    print(f"{cyan('::')} {message}")


def ok(message: str) -> None:
    print(f"{green('✓')} {message}")


def warn(message: str) -> None:
    print(f"{yellow('!')} {message}", file=sys.stderr)


def error(message: str) -> None:
    print(f"{red('✗')} {message}", file=sys.stderr)


def ask(prompt: str, default: str = "") -> str:
    """Otázka s výchozí hodnotou. Prázdná odpověď default potvrdí."""
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{bold('?')} {prompt}{suffix}: ").strip()
    except EOFError:
        return default
    return answer or default


def ask_choice(prompt: str, choices: "list[str]", default: str) -> str:
    """Výběr z pevného seznamu. Opakuje se, dokud nepřijde platná hodnota."""
    hint = "/".join(choices)
    while True:
        answer = ask(f"{prompt} ({hint})", default)
        if answer in choices:
            return answer
        warn(f"Neznámá volba {answer!r}.")


def ask_bool(prompt: str, default: bool) -> bool:
    default_text = "a" if default else "n"
    while True:
        answer = ask(f"{prompt} (a/n)", default_text).lower()
        if answer in ("a", "ano", "y", "yes"):
            return True
        if answer in ("n", "ne", "no"):
            return False
        warn("Odpovězte a nebo n.")

"""Spuštění editoru nad vytvořeným projektem."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from latte import ui


def open_project(editor: str, path: Path) -> bool:
    """Otevře adresář v editoru. Vrací True, pokud se to povedlo.

    Selhání editoru není důvod k pádu -- projekt už na disku je a
    uživateli stačí říct, čím si ho má otevřít sám.
    """
    command = editor.strip()
    if not command:
        return False

    parts = command.split()
    executable = shutil.which(parts[0])
    if executable is None:
        ui.warn(
            f"Editor {parts[0]!r} se nepodařilo najít v PATH. "
            f"Projekt zůstal v {path}."
        )
        return False

    argv = [executable, *parts[1:], str(path)]
    try:
        if sys.platform == "win32":
            # `code` je na Windows dávkový soubor; spuštění bez shellu
            # skončí na WinError 193.
            subprocess.Popen(argv, shell=False, close_fds=True)
        else:
            subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError as exc:
        ui.warn(f"Editor se nepodařilo spustit: {exc}")
        return False
    return True

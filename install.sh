#!/usr/bin/env bash
#
# Instalace nástroje latte (LaTeX Template To Editor) na Linuxu a macOS.
#
# Skript vytvoří izolované virtuální prostředí a do adresáře v PATH
# umístí odkaz na spustitelný soubor. Systémový Python zůstane nedotčený,
# takže instalace projde i na distribucích s externally-managed-environment
# (Debian, Ubuntu, Fedora, Arch).
#
#   ./install.sh              nainstaluje nebo aktualizuje
#   ./install.sh --uninstall  odinstaluje
#   ./install.sh --help       vypíše nápovědu
#
set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly MIN_PYTHON="3.9"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

LATTE_HOME="$DATA_HOME/latte"
BIN_DIR="$HOME/.local/bin"
PYTHON=""
ACTION="install"
PURGE="no"

# --- Výpis -----------------------------------------------------------

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'
    GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
    BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""
fi

info() { printf '%s::%s %s\n' "$BOLD" "$RESET" "$*"; }
ok()   { printf '%s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die()  { printf '%s✗%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Použití: ./install.sh [PŘEPÍNAČE]

  --uninstall          odstraní latte
  --purge              spolu s --uninstall smaže i konfiguraci
                       a uživatelské šablony
  --prefix DIR         adresář pro spustitelný soubor (výchozí ~/.local/bin)
  --home DIR           adresář instalace (výchozí ~/.local/share/latte)
  --python PATH        interpret, ze kterého se vytvoří prostředí
  -h, --help           tato nápověda
EOF
}

# --- Argumenty -------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --uninstall) ACTION="uninstall"; shift ;;
        --purge)     PURGE="yes"; shift ;;
        --prefix)    BIN_DIR="${2:?--prefix vyžaduje adresář}"; shift 2 ;;
        --home)      LATTE_HOME="${2:?--home vyžaduje adresář}"; shift 2 ;;
        --python)    PYTHON="${2:?--python vyžaduje cestu}"; shift 2 ;;
        -h|--help)   usage; exit 0 ;;
        *)           die "Neznámý přepínač: $1 (--help vypíše nápovědu)" ;;
    esac
done

readonly VENV_DIR="$LATTE_HOME/venv"
readonly LINK="$BIN_DIR/latte"

# --- Odinstalace -----------------------------------------------------

uninstall() {
    local removed="no"

    if [[ -L "$LINK" || -f "$LINK" ]]; then
        rm -f "$LINK"
        ok "odstraněno $LINK"
        removed="yes"
    fi

    if [[ -d "$LATTE_HOME" ]]; then
        rm -rf "$LATTE_HOME"
        ok "odstraněno $LATTE_HOME"
        removed="yes"
    fi

    if [[ "$PURGE" == "yes" ]]; then
        local config_dir="$CONFIG_HOME/latte"
        if [[ -d "$config_dir" ]]; then
            rm -rf "$config_dir"
            ok "odstraněna konfigurace $config_dir"
        fi
    elif [[ -d "$CONFIG_HOME/latte" ]]; then
        info "Konfigurace v $CONFIG_HOME/latte zůstala zachována."
        printf '   %sSmazat ji lze pomocí ./install.sh --uninstall --purge%s\n' \
            "$DIM" "$RESET"
    fi

    [[ "$removed" == "yes" ]] || warn "latte nebylo nainstalováno."
}

# --- Instalace -------------------------------------------------------

find_python() {
    if [[ -n "$PYTHON" ]]; then
        command -v "$PYTHON" >/dev/null 2>&1 || die "Interpret $PYTHON neexistuje."
        printf '%s' "$PYTHON"
        return
    fi
    local candidate
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s' "$candidate"
            return
        fi
    done
    die "Nenašel jsem python3. Nainstalujte Python $MIN_PYTHON nebo novější."
}

check_version() {
    local python="$1"
    "$python" - "$MIN_PYTHON" <<'PY' || die "Je potřeba Python $MIN_PYTHON nebo novější."
import sys
required = tuple(int(part) for part in sys.argv[1].split("."))
sys.exit(0 if sys.version_info[: len(required)] >= required else 1)
PY
}

install() {
    [[ -f "$SCRIPT_DIR/pyproject.toml" ]] \
        || die "V $SCRIPT_DIR není pyproject.toml -- spusťte skript z kořene projektu."

    local python
    python="$(find_python)"
    check_version "$python"
    info "Python: $("$python" -c 'import sys, platform; print(platform.python_version(), "--", sys.executable)')"

    if [[ -d "$VENV_DIR" ]]; then
        info "Aktualizuji stávající instalaci v $VENV_DIR"
    else
        info "Vytvářím prostředí v $VENV_DIR"
        mkdir -p "$LATTE_HOME"
        "$python" -m venv "$VENV_DIR" \
            || die "Vytvoření venv selhalo. Na Debianu a Ubuntu chybí obvykle balíček python3-venv."
    fi

    "$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip >/dev/null
    "$VENV_DIR/bin/python" -m pip install --quiet --upgrade "$SCRIPT_DIR" \
        || die "Instalace balíčku selhala."

    mkdir -p "$BIN_DIR"
    ln -sf "$VENV_DIR/bin/latte" "$LINK"
    ok "latte nainstalováno do $LINK"

    # Uživatelské šablony přebíjejí vestavěné; adresář se hodí založit
    # rovnou, aby bylo kam je psát.
    mkdir -p "$CONFIG_HOME/latte/templates"

    local version
    version="$("$LINK" --version 2>/dev/null || echo "?")"
    ok "$version"

    case ":${PATH}:" in
        *":$BIN_DIR:"*) ;;
        *)
            warn "$BIN_DIR není v PATH."
            printf '   Přidejte do ~/.bashrc nebo ~/.zshrc:\n\n'
            printf '     export PATH="%s:$PATH"\n\n' "$BIN_DIR"
            ;;
    esac

    printf '\n%sZačněte:%s\n' "$BOLD" "$RESET"
    printf '  latte muj-projekt          %snový článek%s\n' "$DIM" "$RESET"
    printf '  latte                      %sinteraktivně%s\n' "$DIM" "$RESET"
    printf '  latte templates            %sdostupné šablony%s\n' "$DIM" "$RESET"
    printf '  latte config show          %saktuální nastavení%s\n' "$DIM" "$RESET"
}

case "$ACTION" in
    install)   install ;;
    uninstall) uninstall ;;
esac

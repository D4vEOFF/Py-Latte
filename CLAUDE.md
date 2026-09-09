# latte -- poznámky pro Clauda

`latte` (LaTeX Template To Editor) je CLI, které z šablony založí
LaTeXový projekt, případně mu udělá git repozitář a otevře ho v editoru.

## Jazyk

Kód, komentáře, dokumentace, hlášky i commit messages jsou **česky**.
Anglicky zůstávají jen názvy balíčků, příkazů a proměnných.

## Rozvržení

```
src/latte/
  cli.py         argparse, podpříkazy, interaktivní režim
  config.py      TOML konfigurace, výchozí hodnoty, validace
  fonts.py       fontové presety, dělení preambule na textovou a matematickou část
  langs.py       jazyky, babel, názvy vět a popisků
  templates.py   hledání šablon, dosazování symbolů, kopírování stromu
  project.py     sestavení kontextu, zakládání projektu, `latte add`
  editor.py      spuštění editoru
  ui.py          barevný výpis, dotazy
  templates/     vestavěné šablony
tests/           unittest, bez závislostí
```

## Konvence šablon

Šablona je adresář s `template.toml`. Platí dvě konvence:

- soubor s příponou `.tmpl` se prožene dosazováním `%%SYMBOLŮ%%`
  a přípona se odstraní; ostatní soubory se kopírují beze změny,
- segment cesty začínající `dot-` se přejmenuje na `.`
  (`dot-vscode/` → `.vscode/`) -- adresáře začínající tečkou se do
  balíčku nezabalí spolehlivě.

Symboly mají tvar `%%VELKÝMI_PÍSMENY%%`. Zvolený tvar je bezpečný proti
LaTeXu: `%%%`, `100%%` ani `\node {%` se s ním nekříží (viz test
`test_procenta_v_latexu_zustanou`).

**Neznámý symbol je chyba**, ne důvod tiše vygenerovat rozbitý dokument --
takový projekt by po přeložení vypadal skoro správně.

Nový symbol se přidává na dvou místech: do `project.build_context()`
a do seznamu v `README.md`.

## Pořadí v preambuli (na tohle pozor)

Toto pořadí není kosmetika, plyne z chyb, které jinak překlad shodí:

1. `%%ENCODING_SETUP%%` a `%%BABEL_SETUP%%`,
2. `%%FONT_SETUP%%` -- jen **textový** font,
3. `amsmath`, `amsthm`, `mathtools`,
4. `%%MATHFONT_SETUP%%` -- `amssymb` **nebo** matematický font.

Důvody:

- `newtxmath`, `newpxmath`, `mathdesign`, `kpfonts`, `fourier`
  a `pxfonts` si nesou vlastní AMS symboly. Když se k nim načte
  `amssymb`, překlad skončí na `Command \... already defined`. Proto
  mají v presetu `provides_math=True` a jejich `\usepackage` je
  v `pdftex_math`, ne v `pdftex`.
- `libertinus` naopak `\mathbb` nedodává, takže `amssymb` potřebuje --
  `provides_math=False`.
- `unicode-math` se musí načíst až za `amsmath` a nesnese `amssymb`.
- `newtxmath` i `newpxmath` definují `\binary`. Makro šablony se proto
  jmenuje `\binrep`.

## Testy

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Testy pokrývají logiku, ne LaTeX. **Změna šablony nebo fontového presetu
se musí ověřit skutečným překladem**, jinak se chyba pozná až u uživatele:

```bash
python3 -m venv /tmp/latte-venv && /tmp/latte-venv/bin/pip install -q .
cd /tmp && /tmp/latte-venv/bin/latte zkouska --no-git --no-open -f <preset>
cd zkouska && latexmk -pdf main.tex
```

Chyby překladu jsou v `build/main.log`; `latexmk` je ve výpisu na
terminálu spolehlivě neukáže.

## Přidání fontového presetu

Do `fonts.PRESETS` přidat `FontPreset`. Vyplnit `pdftex` (textový font)
**nebo** `pdftex_math` + `provides_math=True` (font se sazbou
matematiky), a `otf_main` / `otf_math` pro unicodové enginy. Pak přeložit
ukázkový projekt -- viz výše.

## Přidání jazyka

Do `langs.LANGUAGES` přidat `Language` se **všemi** poli; dataclass nemá
výchozí hodnoty právě proto, aby na žádný popisek nešlo zapomenout.
Případnou zkratku doplnit do `langs.ALIASES`.

## Instalační skripty

`install.sh` a `install.ps1` se udržují **v páru** -- co umí jeden, musí
umět druhý (instalace, aktualizace, `--uninstall`, `--purge`, volba
adresáře a interpretu). Oba staví izolované venv, nikdy nesahají na
systémový Python.

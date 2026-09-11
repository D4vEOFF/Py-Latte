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
  fonts.py       fontové presety (výchozí `times` = newtx), dělení preambule
                 na textovou a matematickou část
  langs.py       jazyky, babel, názvy vět a popisků
  templates.py   hledání šablon, dosazování symbolů, kopírování stromu
  project.py     sestavení kontextu, zakládání projektu, `latte add`
  editor.py      spuštění editoru
  ui.py          barevný výpis, dotazy
  templates/     vestavěné šablony
tests/           unittest, bez závislostí
```

`latte new` výchozí hodnoty nejdřív vypíše a zeptá se, jestli platí;
odmítnutí spustí doptávání položku po položce. Na rouře (EOF) projde
dotaz výchozí odpovědí, skripty a testy tedy běží beze změny -- proto
`</dev/null` ve snippetu s překladem níže.

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

## Hlavička v šabloně article

Hlavičku sází `\maketitle`. Údaje, které v ní být nemusí, drží makra
v `assets/header.tex` (`\latteemail`, `\latteinstitute`) a zařazují je
přepínače `\newif` nastavené v `main.tex`. Do hlavičky se dostanou
přes `\lattecontact` v `\author{...}` -- rozvine se až při sazbě, na
pořadí `\author` a přepínačů proto nezáleží.

Prázdný údaj `\lattecontact` vynechá i při zapnutém přepínači, jinak by
v hlavičce zůstal prázdný řádek. Kdo přidá další údaj, přidává ho na
čtyřech místech: makro a větev v `header.tex`, přepínač do
`%%HEADER_SWITCHES%%` v `project.build_context()`, pole do
`project.Settings` a `project.HEADER_FLAGS`, volbu do `config.DEFAULTS`
a `config.BOOL_KEYS`.

Co se v hlavičce vysází, řídí volby `header_*`. Do šablony se dostanou
hotovými řádky (`%%AUTHOR_SETUP%%`, `%%DATE_SETUP%%`,
`%%HEADER_SWITCHES%%`, `%%TITLE_SETUP%%`, `%%TOC_SETUP%%`), ne
podmínkami -- dosazování symbolů žádné větvení neumí. Titulní strana
sází kontakt sama, proto s `header_titlepage` vycházejí přepínače
e-mailu a instituce vždy vypnuté.

Tělo `main.tex` je prázdné záměrně: složku `sections/` šablona
nezakládá, rozvržení textu si rozvrhne uživatel.

`assets/titlepage.tex` je nepovinná náhrada hlavičky. Kontakt sází sama
z týchž maker, takže s ní mají přepínače zůstat vypnuté.

## Testy

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Testy pokrývají logiku, ne LaTeX. **Změna šablony nebo fontového presetu
se musí ověřit skutečným překladem**, jinak se chyba pozná až u uživatele:

```bash
python3 -m venv /tmp/latte-venv && /tmp/latte-venv/bin/pip install -q .
cd /tmp && /tmp/latte-venv/bin/latte zkouska --no-git --no-open -f <preset> </dev/null
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

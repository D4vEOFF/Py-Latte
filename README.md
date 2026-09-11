# latte

[![CI](https://github.com/D4vEOFF/Py-Latte/actions/workflows/ci.yml/badge.svg)](https://github.com/D4vEOFF/Py-Latte/actions/workflows/ci.yml)

**LaTeX Template To Editor** -- jedním příkazem založí LaTeXový projekt,
vytvoří git repozitář a otevře ho ve VS Code.

```bash
latte muj-clanek
```

Vznikne hotový projekt s preambulí, tématem, makry, bibliografií
a nastavením pro překlad -- připravený k psaní, ne ke konfigurování.

## Instalace

### Linux, macOS

```bash
git clone https://github.com/D4vEOFF/Py-Latte.git
cd Py-Latte
./install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/D4vEOFF/Py-Latte.git
cd Py-Latte
.\install.ps1
```

Oba skripty vytvoří izolované virtuální prostředí, takže se nesáhne
na systémový Python. Opakované spuštění instalaci aktualizuje.

### Odinstalace

```bash
./install.sh --uninstall           # konfiguraci ponechá
./install.sh --uninstall --purge   # smaže i konfiguraci a šablony
```

```powershell
.\install.ps1 -Uninstall
.\install.ps1 -Uninstall -Purge
```

## Použití

```bash
latte                          # zeptá se na všechno
latte muj-clanek               # výchozí nastavení
latte prednasky -t beamer-monorepo
latte teze -c report -f libertinus -l en
latte disertace -e lualatex -f "EB Garamond"
```

| Přepínač | Význam |
|---|---|
| `-t`, `--template` | šablona projektu (`latte templates`) |
| `-c`, `--class` | třída dokumentu |
| `--class-options` | volby třídy, např. `12pt,a4paper` |
| `-f`, `--font` | fontový preset nebo systémový font (`latte fonts`) |
| `-e`, `--engine` | `pdflatex`, `lualatex`, `xelatex` |
| `-l`, `--lang` | `cs`, `sk`, `en`, `de` |
| `--title`, `--author`, `--email`, `--institute` | údaje do dokumentu |
| `-d`, `--dir` | kam projekt založit |
| `--editor` | čím ho otevřít |
| `--no-open`, `--no-git` | vynechat editor, vynechat git |
| `-i`, `--interactive` | doptat se na vše |
| `--force` | rozbalit i do neprázdného adresáře |

Další příkazy:

```bash
latte add ti-01-uvod     # nová prezentace uvnitř monorepa
latte templates          # dostupné šablony
latte fonts              # fontové presety
latte config show        # aktuální nastavení
latte config set font libertinus
latte config edit
```

## Šablony

### `article` (výchozí)

Jeden dokument. Sdílená preambule v `assets/`, obrázky v `figures/`.
Tělo `main.tex` zůstává prázdné -- rozvržení textu do souborů je na
autorovi.

```
main.tex
assets/    packages.tex  style.tex  macros.tex  listing.tex
           header.tex  titlepage.tex  literatura.bib
figures/
.latexmkrc  Makefile  .vscode/settings.json  .gitignore  README.md
```

Hlavičku sází standardní `\maketitle`: název, autor a `\today`. E-mail
a instituci z konfigurace drží makra `\latteemail` a `\latteinstitute`
v `assets/header.tex`; pod jméno autora je přidají přepínače v `main.tex`:

```latex
\headeremailtrue        % e-mail pod jméno
\headerinstitutetrue    % instituce pod jméno
```

Co se do hlavičky dostane hned při zakládání, řídí volby `header_*`
(viz [Konfigurace](#konfigurace)) a dotaz, kterým se `latte new` ptá,
jestli výchozí hodnoty platí i pro tenhle projekt.

Místo hlavičky lze vysázet titulní stranu se šikmou hranou -- v `main.tex`
stačí místo `\maketitle` vložit `\input{assets/titlepage.tex}`
(nebo rovnou `header_titlepage = true`).

Dál obsahuje věty a definice se společným číslováním, čtyři úrovně
barevných rámečků, sazbu zdrojového kódu a citace podle ČSN ISO 690
(biblatex-iso690).

### `beamer-monorepo`

Repozitář, ve kterém libovolný počet prezentací sdílí jednu preambuli,
jedno téma, jednu sadu maker a jednu databázi zdrojů.

```
assets/    packages.tex  theme.tex  macros.tex  listing.tex  literatura.bib
images/
titlepage.tex
<prezentace>/main.tex
```

Další prezentaci přidá `latte add <jméno>`; `make` přeloží všechny,
`make <jméno>` jednu.

## Fonty

Výchozí je **Times** (`newtxtext` + `newtxmath`); `cm` vrátí Computer
Modern, tedy font, který LaTeX používá sám od sebe.

```
cm  lmodern  libertinus  times  palatino  pxfonts  charter
kpfonts  fourier  helvet
```

S `--engine lualatex` nebo `--engine xelatex` lze místo presetu uvést
jméno libovolného systémového fontu:

```bash
latte kniha -e lualatex -f "EB Garamond"
```

## Konfigurace

Výchozí hodnoty všech přepínačů lze uložit, ať se nemusí psát pokaždé:

```bash
latte config set author "Jméno Příjmení"
latte config set font libertinus
latte config set projects_dir ~/Dokumenty/latex
latte config set open_editor false
```

Soubor:

* Linux, macOS -- `~/.config/latte/config.toml`
* Windows -- `%APPDATA%\latte\config.toml`

Je to TOML, textové hodnoty tedy patří do uvozovek:

```toml
template = "article"
documentclass = ""          # prázdné = třída podle šablony
lang = "czech"
engine = "pdflatex"
font = "times"
editor = "code"
open_editor = true
git_init = true
projects_dir = ""
author = "Jméno Příjmení"
email = "jmeno@example.com"
institute = ""

# Co z údajů výše se vysází v hlavičce nového projektu.
header_author = true
header_email = false
header_institute = false
header_date = true
header_toc = true        # \tableofcontents v main.tex
header_titlepage = false # titulní strana místo \maketitle
```

`latte new` tyhle hodnoty nejdřív vypíše a zeptá se, jestli platí.
Odpověď `n` projde volby jednu po druhé, takže konfigurace zůstane
výchozím nastavením a projekt si může vzít jiné. Bez terminálu (roura,
skript) se bere odpověď `a`, tedy výchozí hodnoty.

Titulní strana sází e-mail i instituci sama; s `header_titlepage = true`
proto přepínače `header_email` a `header_institute` nic nepřidávají.

## Vlastní šablony

Adresář v `~/.config/latte/templates/` se souborem `template.toml` se
chová jako vestavěná šablona. Stejné jméno vestavěnou šablonu přebije,
takže lze upravit i `article`:

```bash
cp -r <instalace>/templates/article ~/.config/latte/templates/article
```

Uvnitř šablony platí dvě konvence:

* soubor s příponou `.tmpl` se prožene dosazováním `%%SYMBOLŮ%%`
  a přípona se odstraní,
* segment cesty začínající `dot-` se přejmenuje na `.`
  (`dot-vscode/settings.json` → `.vscode/settings.json`).

Dostupné symboly: `%%TITLE%%`, `%%AUTHOR%%`, `%%AUTHOR_SETUP%%`,
`%%DATE_SETUP%%`, `%%HEADER_SWITCHES%%`, `%%TITLE_SETUP%%`,
`%%TOC_SETUP%%`, `%%EMAIL%%`,
`%%INSTITUTE%%`, `%%PROJECT_NAME%%`, `%%DOCUMENTCLASS%%`,
`%%CLASS_OPTIONS%%`, `%%ENGINE%%`, `%%FONT%%`, `%%FONT_LABEL%%`,
`%%FONT_SETUP%%`, `%%MATHFONT_SETUP%%`, `%%ENCODING_SETUP%%`,
`%%BABEL_SETUP%%`, `%%LANG%%`, `%%BABEL%%`, `%%ASSETS%%`, `%%DATE%%`,
`%%YEAR%%`, `%%LATEXMK_FLAG%%`, `%%LATEXMK_PDF_MODE%%`, `%%SECTION_INTRO%%`,
`%%ABSTRACT%%`, `%%THM_DEFINITION%%`, `%%THM_THEOREM%%`, `%%THM_LEMMA%%`,
`%%THM_PROPOSITION%%`, `%%THM_COROLLARY%%`, `%%THM_EXAMPLE%%`,
`%%THM_NOTE%%`, `%%THM_PROOF%%`, `%%LABEL_ALGORITHM%%`,
`%%LABEL_LISTING%%`, `%%LABEL_TOC%%`, `%%LABEL_SOURCES%%`.

Neznámý symbol je chyba -- šablona se nerozbalí, místo aby vznikl
dokument, který vypadá skoro správně.

## Vývoj

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests
```

Podrobnosti jsou v [CONTRIBUTING.md](CONTRIBUTING.md), poznámky
k vnitřnostem (pořadí balíčků v preambuli, přidání fontu nebo jazyka)
v [CLAUDE.md](CLAUDE.md). Historie změn je v
[CHANGELOG.md](CHANGELOG.md).

## Požadavky

* Python 3.9 nebo novější,
* TeX Live nebo MiKTeX s `latexmk` a `biber`,
* volitelně `git` a VS Code.

## Licence

MIT

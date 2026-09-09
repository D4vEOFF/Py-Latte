# Changelog

Formát vychází z [Keep a Changelog](https://keepachangelog.com/cs/1.1.0/),
číslování ze [sémantického verzování](https://semver.org/lang/cs/).

## [Nezveřejněno]

### Změněno

- Výchozím fontem je **Times** (`newtxtext` + `newtxmath`) místo
  Computer Modern. Původní chování vrátí `latte config set font cm`.
- Šablona **article** sází hlavičku standardním `\maketitle` (název,
  autor, `\today`). Titulní strana se šikmou hranou zůstává jako
  nepovinná náhrada: `\input{assets/titlepage.tex}` místo `\maketitle`.
- `latte config show` vypisuje platné TOML, tedy i uvozovky kolem
  textových hodnot -- výpis šlo zkopírovat do `config.toml`, kde pak
  nešel načíst. Chyba v konfiguraci na uvozovky nově upozorní.

### Přidáno

- `assets/header.tex` v šabloně **article**: makra `\latteemail`
  a `\latteinstitute` s hodnotami z konfigurace a přepínače
  `\headeremail`/`\headerinstitute`, kterými se údaje zařadí pod jméno
  autora v hlavičce.

## [0.1.0] -- 2026-09-09

První vydání.

### Přidáno

- Příkaz `latte` zakládající LaTeXové projekty ze šablon.
  Bez argumentů se doptá interaktivně, s argumenty běží neinteraktivně.
- Šablona **article**: `main.tex`, sdílená preambule v `assets/`,
  text po sekcích v `sections/`, obrázky v `figures/`. Titulní strana se
  šikmou hranou, věty a definice se společným číslováním, čtyři úrovně
  barevných rámečků, sazba zdrojového kódu, citace podle ČSN ISO 690.
- Šablona **beamer-monorepo**: repozitář, ve kterém libovolný počet
  prezentací sdílí jednu preambuli, téma, sadu maker a databázi zdrojů.
  Další prezentaci přidá `latte add <jméno>`.
- Deset fontových presetů pro pdflatex (`cm`, `lmodern`, `libertinus`,
  `times`, `palatino`, `pxfonts`, `charter`, `kpfonts`, `fourier`,
  `helvet`); výchozí je Computer Modern.
- Podpora `lualatex` a `xelatex`: s nimi lze přes `--font` uvést jméno
  libovolného systémového fontu, který se vysází přes fontspec.
- Jazyky `czech`, `slovak`, `english`, `german` včetně názvů vět,
  definic a popisků.
- Konfigurace v `~/.config/latte/config.toml`
  (`%APPDATA%\latte\config.toml` na Windows) s příkazy
  `latte config show|set|path|edit|init`.
- Uživatelské šablony v `~/.config/latte/templates/`; stejnojmenná
  šablona přebije vestavěnou.
- Vygenerovaný projekt obsahuje `.latexmkrc`, `Makefile`,
  `.vscode/settings.json` pro LaTeX Workshop, `.gitignore` a `README.md`;
  volitelně se založí git repozitář a projekt se otevře v editoru.
- Instalační skripty `install.sh` (Linux, macOS) a `install.ps1`
  (Windows) včetně odinstalace (`--uninstall`, `--purge`).

[Nezveřejněno]: https://github.com/D4vEOFF/Py-Latte/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/D4vEOFF/Py-Latte/releases/tag/v0.1.0

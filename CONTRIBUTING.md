# Jak přispívat

## Vývojová instalace

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/latte --version
```

## Testy

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Testy ověřují logiku nástroje, ne LaTeX. Změnu šablony nebo fontového
presetu je potřeba ověřit i skutečným překladem:

```bash
.venv/bin/latte /tmp/zkouska --no-git --no-open -f <preset>
cd /tmp/zkouska && latexmk -pdf main.tex
```

Chyby překladu jsou v `build/main.log`.

## Konvence

- Kód, komentáře i commit messages jsou česky.
- Komentář vysvětluje **proč**, ne co je z kódu vidět.
- Podrobnosti o šablonách, pořadí balíčků v preambuli a přidávání fontů
  jsou v [CLAUDE.md](CLAUDE.md).

## Změny do CHANGELOGu

Uživatelsky viditelnou změnu zapište do sekce `[Nezveřejněno]`
v [CHANGELOG.md](CHANGELOG.md).

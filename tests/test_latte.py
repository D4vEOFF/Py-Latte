"""Testy jádra nástroje latte.

Spuštění:  python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from latte import config, fonts, langs, project, templates
from latte.errors import LatteError


class TestSlugify(unittest.TestCase):
    def test_mezery_a_diakritika(self):
        self.assertEqual(project.slugify("muj projekt"), "muj-projekt")
        self.assertEqual(project.slugify("  a/b:c  "), "a-b-c")

    def test_prazdne_jmeno_ma_nahradu(self):
        self.assertEqual(project.slugify("///"), "projekt")

    def test_tecka_na_zacatku_zmizi(self):
        self.assertFalse(project.slugify("...skryty").startswith("."))


class TestTitleFromSlug(unittest.TestCase):
    def test_prvni_slovo_velkym(self):
        self.assertEqual(project.title_from_slug("muj-prvni-clanek"), "Muj prvni clanek")


class TestRender(unittest.TestCase):
    def test_dosazeni(self):
        self.assertEqual(
            templates.render_text("a %%X%% b", {"X": "1"}), "a 1 b"
        )

    def test_neznamy_symbol_je_chyba(self):
        with self.assertRaises(LatteError):
            templates.render_text("%%NEZNAMY%%", {"X": "1"})

    def test_procenta_v_latexu_zustanou(self):
        # Komentáře a zdvojená procenta v LaTeXu nesmí nic nahradit.
        source = "100%% sazby %%% oddělovač\n\\node {%\n"
        self.assertEqual(templates.render_text(source, {}), source)


class TestFonts(unittest.TestCase):
    def test_neznamy_font_u_pdflatexu_selze(self):
        with self.assertRaises(LatteError):
            fonts.resolve("EB Garamond", "pdflatex")

    def test_neznamy_font_u_lualatexu_projde(self):
        preset = fonts.resolve("EB Garamond", "lualatex")
        self.assertEqual(preset.otf_main, "EB Garamond")

    def test_cm_nenacita_zadny_balicek(self):
        preset = fonts.resolve("cm", "pdflatex")
        self.assertNotIn("usepackage", fonts.preamble(preset, "pdflatex"))

    def test_matematicke_fonty_vynechavaji_amssymb(self):
        # newtxmath dodává AMS symboly sám; amssymb by srazil překlad.
        preset = fonts.resolve("times", "pdflatex")
        math = fonts.math_preamble(preset, "pdflatex")
        self.assertNotIn(r"\usepackage{amssymb}", math)
        self.assertIn("newtxmath", math)

    def test_vychozi_font_sazi_newtx(self):
        # Výchozí je newtxtext + newtxmath, obojí až za amsmath.
        preset = fonts.resolve(fonts.DEFAULT_FONT, "pdflatex")
        math = fonts.math_preamble(preset, "pdflatex")
        self.assertIn(r"\usepackage{newtxtext}", math)
        self.assertIn(r"\usepackage{newtxmath}", math)
        self.assertEqual(config.DEFAULTS["font"], fonts.DEFAULT_FONT)

    def test_bezny_font_amssymb_potrebuje(self):
        preset = fonts.resolve("cm", "pdflatex")
        self.assertIn(r"\usepackage{amssymb}", fonts.math_preamble(preset, "pdflatex"))

    def test_unicode_engine_nenacita_inputenc(self):
        # Zmínka v komentáři nevadí, jde o skutečné načtení balíčku.
        self.assertNotIn(
            r"\usepackage[utf8]{inputenc}", fonts.encoding_preamble("lualatex")
        )
        self.assertIn(
            r"\usepackage[utf8]{inputenc}", fonts.encoding_preamble("pdflatex")
        )


class TestLangs(unittest.TestCase):
    def test_zkratky(self):
        self.assertEqual(langs.resolve("cs").key, "czech")
        self.assertEqual(langs.resolve("EN").key, "english")

    def test_neznamy_jazyk(self):
        with self.assertRaises(LatteError):
            langs.resolve("klingon")


class TestConfig(unittest.TestCase):
    def test_prevod_pravdivostni_hodnoty(self):
        self.assertIs(config.coerce("git_init", "ano"), True)
        self.assertIs(config.coerce("git_init", "false"), False)

    def test_neplatna_pravdivostni_hodnota(self):
        with self.assertRaises(LatteError):
            config.coerce("git_init", "mozna")

    def test_neznama_volba(self):
        with self.assertRaises(LatteError):
            config.coerce("neexistuje", "x")


class TestTemplates(unittest.TestCase):
    def test_vestavene_sablony_jsou_nactitelne(self):
        names = {t.name for t in templates.available()}
        self.assertIn("article", names)
        self.assertIn("beamer-monorepo", names)

    def test_neznama_sablona(self):
        with self.assertRaises(LatteError):
            templates.get("neexistuje")


def _settings(**overrides) -> project.Settings:
    values = dict(
        template="article",
        documentclass="article",
        class_options="11pt,a4paper",
        lang="czech",
        engine="pdflatex",
        font="cm",
        author="Autor",
        email="",
        institute="",
        title="Název",
    )
    values.update(overrides)
    return project.Settings(**values)


class TestCreate(unittest.TestCase):
    def test_article_vznikne_se_vsemi_soubory(self):
        template = templates.get("article")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "projekt"
            project.create(template, target, _settings())

            for expected in [
                "main.tex",
                "Makefile",
                ".latexmkrc",
                ".gitignore",
                ".vscode/settings.json",
                "assets/packages.tex",
                "assets/style.tex",
                "assets/header.tex",
                "assets/literatura.bib",
                "sections/01-uvod.tex",
                ".latte.toml",
            ]:
                self.assertTrue((target / expected).is_file(), expected)

            # template.toml popisuje šablonu, do projektu nepatří.
            self.assertFalse((target / "template.toml").exists())

            # V hotovém projektu nesmí zbýt nedosazený symbol.
            for path in target.rglob("*"):
                if path.is_file() and path.suffix in (".tex", ".json", ".md"):
                    self.assertNotIn(
                        "%%", path.read_text(encoding="utf-8").replace("%%%", ""),
                        f"nedosazený symbol v {path.name}",
                    )

    def test_neprazdny_adresar_bez_force_selze(self):
        template = templates.get("article")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "projekt"
            target.mkdir()
            (target / "neco.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(LatteError):
                project.create(template, target, _settings())

    def test_monorepo_neobsahuje_kostru_podprojektu(self):
        template = templates.get("beamer-monorepo")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "prezentace"
            project.create(template, target, _settings(documentclass="beamer"))
            self.assertFalse((target / "_subproject").exists())
            # Sdílené soubory se vkládají z podprojektu, tedy o adresář výš.
            packages = (target / "assets" / "packages.tex").read_text(encoding="utf-8")
            self.assertIn("../assets/literatura.bib", packages)

    def test_add_prida_podprojekt(self):
        template = templates.get("beamer-monorepo")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "prezentace"
            settings = _settings(template="beamer-monorepo", documentclass="beamer")
            project.create(template, root, settings)

            found_root, loaded = project.find_root(root)
            self.assertEqual(found_root, root)
            self.assertEqual(loaded.template, "beamer-monorepo")

            target, created = project.add_subproject(template, root, "p01", loaded)
            self.assertTrue((target / "main.tex").is_file())
            self.assertIn("../assets/packages.tex",
                          (target / "main.tex").read_text(encoding="utf-8"))


class TestHeader(unittest.TestCase):
    def test_main_sazi_standardni_hlavicku(self):
        template = templates.get("article")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "projekt"
            project.create(
                template,
                target,
                _settings(email="a@b.cz", institute="Ústav"),
            )
            main = (target / "main.tex").read_text(encoding="utf-8")

            self.assertIn(r"\maketitle", main)
            self.assertIn(r"\date{\today}", main)
            self.assertIn(r"\author{Autor\lattecontact}", main)
            # Výchozí hlavička je jen název, autor a datum.
            self.assertIn(r"\headeremailfalse", main)
            self.assertIn(r"\headerinstitutefalse", main)
            # Titulní strana zůstává jako nepovinná náhrada.
            self.assertNotIn("\n\\input{assets/titlepage.tex}", main)

    def test_header_drzi_hodnoty_z_konfigurace(self):
        template = templates.get("article")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "projekt"
            project.create(
                template,
                target,
                _settings(email="a_b@c.cz", institute="Ústav & spol."),
            )
            header = (target / "assets" / "header.tex").read_text(encoding="utf-8")

            # Hodnoty jsou ošetřené proti LaTeXu.
            self.assertIn(r"\newcommand{\latteemail}{a\_b@c.cz}", header)
            self.assertIn(r"\newcommand{\latteinstitute}{Ústav \& spol.}", header)
            self.assertIn(r"\newif\ifheaderemail", header)
            self.assertIn(r"\newif\ifheaderinstitute", header)


class TestLatexEscape(unittest.TestCase):
    def test_znaky_se_osetri(self):
        escaped = project._latex_escape("100% & _x_")
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\_", escaped)


if __name__ == "__main__":
    unittest.main()

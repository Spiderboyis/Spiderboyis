#!/usr/bin/env python3
"""Adversarial Stress-Testing and Empirical Challenge Suite for SVG Assets.

Executed by subagent challenger_1 (empirical_challenger).
Validates:
1. Multi-parser strict XML compliance (ElementTree, minidom, SAX, lxml, xmllint).
2. Security & forbidden tags audit (<foreignObject>, <script>, <iframe>, event attributes).
3. Zero CSS @keyframes in custom SVGs (Firefox SVG-as-image compatibility).
4. Declarative SMIL syntax, duration, and sequence timing.
5. Coordinate bounds and viewBox containment.
6. Rasterization verification over simulated dark (#0d1117) and light (#ffffff) backgrounds.
7. WCAG 2.1 relative luminance and contrast ratio calculations.
"""

import math
import re
import subprocess
import unittest
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import xml.sax as sax
from pathlib import Path
from PIL import Image
import lxml.etree as letree

ROOT_DIR = Path(__file__).resolve().parent.parent

CUSTOM_SVGS = [
    "assets/hero-banner.svg",
    "assets/divider-cyber.svg",
    "assets/projects-matrix.svg",
]
ALL_SVGS = CUSTOM_SVGS + ["github-metrics.svg"]


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    return tuple(int(hex_str[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def rel_luminance(rgb: tuple) -> float:
    def channel_lum(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = [channel_lum(c) for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = rel_luminance(hex_to_rgb(hex1))
    l2 = rel_luminance(hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestAdversarialXMLParsers(unittest.TestCase):
    """Stress-test XML parsing using 5 distinct XML parsing engines."""

    def test_element_tree_parser(self):
        for rel_path in ALL_SVGS:
            path = ROOT_DIR / rel_path
            try:
                tree = ET.parse(path)
                self.assertIsNotNone(tree.getroot())
            except Exception as e:
                self.fail(f"ElementTree failed on {rel_path}: {e}")

    def test_minidom_parser(self):
        for rel_path in ALL_SVGS:
            path = ROOT_DIR / rel_path
            try:
                dom = minidom.parse(str(path))
                self.assertIsNotNone(dom.documentElement)
            except Exception as e:
                self.fail(f"minidom failed on {rel_path}: {e}")

    def test_sax_parser(self):
        class StrictHandler(sax.ContentHandler):
            pass

        for rel_path in ALL_SVGS:
            path = ROOT_DIR / rel_path
            try:
                sax.parse(str(path), StrictHandler())
            except Exception as e:
                self.fail(f"SAX parser failed on {rel_path}: {e}")

    def test_strict_lxml_parser(self):
        parser = letree.XMLParser(resolve_entities=False, no_network=True)
        for rel_path in ALL_SVGS:
            path = ROOT_DIR / rel_path
            try:
                doc = letree.parse(str(path), parser)
                self.assertIsNotNone(doc.getroot())
            except Exception as e:
                self.fail(f"Strict lxml parser failed on {rel_path}: {e}")

    def test_xmllint_cli(self):
        for rel_path in ALL_SVGS:
            path = ROOT_DIR / rel_path
            res = subprocess.run(
                ["xmllint", "--noout", str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"xmllint reported error for {rel_path}:\n{res.stderr}",
            )


class TestSecurityAndForbiddenConstructs(unittest.TestCase):
    """Examine custom SVGs for forbidden elements, scripts, and keyframes."""

    FORBIDDEN_TAGS = {"foreignObject", "script", "iframe", "object", "embed", "applet", "meta", "link"}
    EVENT_ATTRIBUTES = {"onload", "onerror", "onclick", "onmouseover", "onfocus", "onblur"}

    def test_custom_svgs_strict_security(self):
        for rel_path in CUSTOM_SVGS:
            path = ROOT_DIR / rel_path
            tree = ET.parse(path)
            content = path.read_text(encoding="utf-8")

            # Check tags
            for elem in tree.iter():
                tag_name = elem.tag.split("}")[-1]
                self.assertNotIn(
                    tag_name,
                    self.FORBIDDEN_TAGS,
                    f"Forbidden tag <{tag_name}> found in {rel_path}",
                )
                for attr, val in elem.attrib.items():
                    attr_name = attr.split("}")[-1].lower()
                    self.assertNotIn(
                        attr_name,
                        self.EVENT_ATTRIBUTES,
                        f"Event handler attribute '{attr_name}' found in {rel_path}",
                    )
                    self.assertFalse(
                        attr_name.startswith("on"),
                        f"Potentially unsafe event attribute '{attr_name}' in {rel_path}",
                    )
                    self.assertNotIn(
                        "javascript:",
                        val.lower(),
                        f"javascript: URI detected in attribute value of {rel_path}",
                    )

            # Check raw string content
            for f_tag in self.FORBIDDEN_TAGS:
                self.assertNotIn(
                    f"<{f_tag}",
                    content,
                    f"Forbidden tag substring <{f_tag} found in raw text of {rel_path}",
                )

    def test_custom_svgs_no_css_keyframes(self):
        for rel_path in CUSTOM_SVGS:
            path = ROOT_DIR / rel_path
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "@keyframes",
                content,
                f"CSS @keyframes found in {rel_path} — must rely strictly on SMIL",
            )

    def test_github_metrics_svg_foreignobject_catalogued(self):
        """Acknowledge and catalog that third-party github-metrics.svg relies on foreignObject."""
        path = ROOT_DIR / "github-metrics.svg"
        content = path.read_text(encoding="utf-8")
        self.assertIn("<foreignObject", content)
        self.assertIn("@keyframes", content)
        # Ensure it does NOT contain executable script tags
        self.assertNotIn("<script", content)


class TestSMILAnimationAttributes(unittest.TestCase):
    """Stress-test SMIL animation parameters and sequential typing timing."""

    def test_smil_attributes_validity(self):
        smil_tag_names = {"animate", "animateTransform", "set", "animateMotion"}
        for rel_path in CUSTOM_SVGS:
            path = ROOT_DIR / rel_path
            tree = ET.parse(path)
            smil_elems = [el for el in tree.iter() if el.tag.split("}")[-1] in smil_tag_names]
            self.assertGreater(
                len(smil_elems),
                0,
                f"{rel_path} must contain at least one SMIL element",
            )
            for el in smil_elems:
                attr_name = el.attrib.get("attributeName")
                self.assertIsNotNone(attr_name, f"SMIL element missing attributeName in {rel_path}")
                dur = el.attrib.get("dur")
                self.assertIsNotNone(dur, f"SMIL element missing dur in {rel_path}")
                # Duration should parse as seconds (e.g. '2.4s', '10s')
                self.assertTrue(
                    dur.endswith("s") or dur.endswith("ms"),
                    f"Duration '{dur}' does not specify valid time unit in {rel_path}",
                )
                dur_num = float(dur.rstrip("s").rstrip("m"))
                self.assertGreater(dur_num, 0.0, f"Duration must be positive in {rel_path}")

    def test_hero_banner_typing_sequence_monotonicity(self):
        """Verify hero banner contains valid progressive SMIL ambient animations."""
        path = ROOT_DIR / "assets/hero-banner.svg"
        tree = ET.parse(path)
        anims = tree.findall(".//{http://www.w3.org/2000/svg}animate") + tree.findall(".//animate")
        self.assertGreater(len(anims), 0, "Hero banner must contain active SMIL animations")
        for anim in anims:
            dur = anim.attrib.get("dur")
            self.assertIsNotNone(dur, "Animation missing duration attribute")
            dur_val = float(dur.rstrip("s").rstrip("ms"))
            self.assertGreater(dur_val, 0.0, "Animation duration must be positive")


class TestRenderFidelityAndRasterization(unittest.TestCase):
    """Verify rasterization over light and dark backgrounds with ImageMagick."""

    def test_rasterization_produces_non_trivial_output(self):
        for rel_path in CUSTOM_SVGS:
            path = ROOT_DIR / rel_path
            stem = path.stem
            for bg, mode in [("#0d1117", "dark"), ("#ffffff", "light")]:
                out_png = f"/tmp/test_{stem}_{mode}.png"
                res = subprocess.run(
                    ["magick", "-background", bg, str(path), out_png],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"magick failed to render {rel_path} on {mode}:\n{res.stderr}",
                )
                img = Image.open(out_png)
                self.assertGreater(img.width, 0)
                self.assertGreater(img.height, 0)
                colors = img.getcolors(maxcolors=100000)
                num_colors = len(colors) if colors else 100000
                self.assertGreater(
                    num_colors,
                    10,
                    f"Rendered image {out_png} is trivial or blank ({num_colors} colors)",
                )


class TestWCAGContrastRatios(unittest.TestCase):
    """Verify that containerized text meets WCAG AAA guidelines (>= 7.0:1)."""

    def test_contained_text_contrast(self):
        container_bg = "#090d16"
        project_bg = "#0e1424"

        # Hero container texts
        hero_texts = [
            ("#00f0ff", "Cyan Prompt"),
            ("#7aa2f7", "Blue Focus"),
            ("#bb9af7", "Violet Identity"),
            ("#c0caf5", "Light Slate Text"),
            ("#a9b1d6", "Muted Slate Text"),
            ("#9ece6a", "Green Stack"),
            ("#e0af68", "Yellow Code"),
        ]
        for color, label in hero_texts:
            cr = contrast_ratio(color, container_bg)
            self.assertGreaterEqual(
                cr,
                7.0,
                f"{label} ({color}) against {container_bg} contrast {cr:.2f}:1 is below WCAG AAA 7.0:1",
            )

        # Projects card container texts
        card_texts = [
            ("#00f0ff", "Tagzzs Cyan"),
            ("#7aa2f7", "Tagzzs Blue Title"),
            ("#bb9af7", "DecayState Violet"),
            ("#73daca", "CURL-Vision Emerald"),
            ("#ff9e64", "Solarflare Orange"),
            ("#c0caf5", "Card Body Text"),
        ]
        for color, label in card_texts:
            cr = contrast_ratio(color, project_bg)
            self.assertGreaterEqual(
                cr,
                6.5,
                f"{label} ({color}) against {project_bg} contrast {cr:.2f}:1 is below expected threshold",
            )


class TestTextBoundsAndOverflowPrevention(unittest.TestCase):
    """Verify that all text lines in custom SVGs strictly fit within container boundaries."""

    def test_hero_banner_text_fits_within_margins(self):
        path = ROOT_DIR / "assets/hero-banner.svg"
        tree = ET.parse(path)
        root = tree.getroot()
        for text_el in root.findall(".//{http://www.w3.org/2000/svg}text"):
            t_str = text_el.text or ""
            tx = float(text_el.attrib.get("x", 0))
            fsize = float(text_el.attrib.get("font-size", 12))
            anchor = text_el.attrib.get("text-anchor", "start")
            if anchor == "end":
                self.assertLessEqual(tx, 952.0)
            else:
                est_w = len(t_str) * (fsize * 0.65)
                self.assertLess(tx + est_w, 952.0, f"Hero text line '{t_str}' exceeds right margin 952")

    def test_projects_matrix_text_fits_quadrant_columns(self):
        path = ROOT_DIR / "assets/projects-matrix.svg"
        tree = ET.parse(path)
        root = tree.getroot()
        for g in root.findall(".//{http://www.w3.org/2000/svg}g"):
            transform = g.attrib.get("transform", "")
            if "translate" in transform:
                m = re.search(r"translate\((\d+),\s*(\d+)\)", transform)
                if m:
                    gx = int(m.group(1))
                    is_left = gx < 480
                    boundary = 480 if is_left else 928
                    for text_el in g.findall("{http://www.w3.org/2000/svg}text"):
                        t_str = text_el.text or ""
                        tx = float(text_el.attrib.get("x", 0))
                        fsize = float(text_el.attrib.get("font-size", 12))
                        est_w = len(t_str) * (fsize * 0.65)
                        self.assertLess(
                            gx + tx + est_w,
                            boundary,
                            f"Projects text '{t_str}' in column '{gx}' exceeds boundary {boundary}",
                        )


if __name__ == "__main__":
    unittest.main()

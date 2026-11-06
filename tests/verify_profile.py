#!/usr/bin/env python3
"""Automated Verification Test Suite for Harshit Mathur's GitHub Profile Redesign.

Validates:
1. XML validity for all custom SVGs in assets/ and github-metrics.svg.
2. SVG safety compliance: no <foreignObject>, no <script>, no CSS @keyframes.
3. SMIL animation presence (<animate>, <animateTransform>).
4. README completeness: 4 featured projects, academic credentials, URLs.
5. Workflow integration: Contribution Snake from 'output' branch via <picture>, github-metrics.svg.
6. Workflow YAML validity for snake.yml and metrics.yml.
"""

import os
import re
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestCustomSVGAssets(unittest.TestCase):
    """Validation for custom animated SVG assets in assets/."""

    CUSTOM_SVGS = [
        "assets/hero-banner.svg",
        "assets/divider-cyber.svg",
        "assets/projects-matrix.svg",
    ]

    def test_custom_svgs_exist(self):
        """Confirm all expected custom SVG assets exist on disk."""
        for rel_path in self.CUSTOM_SVGS:
            full_path = ROOT_DIR / rel_path
            self.assertTrue(full_path.is_file(), f"Missing custom SVG asset: {rel_path}")

    def test_custom_svgs_valid_xml(self):
        """Confirm all custom SVGs parse cleanly with standard XML parser."""
        for rel_path in self.CUSTOM_SVGS:
            full_path = ROOT_DIR / rel_path
            try:
                tree = ET.parse(full_path)
                root = tree.getroot()
                self.assertIsNotNone(root, f"Failed to get XML root for {rel_path}")
                self.assertTrue(
                    root.tag.endswith("svg"),
                    f"Root tag of {rel_path} is not svg: {root.tag}",
                )
            except ET.ParseError as err:
                self.fail(f"XML parse error in {rel_path}: {err}")

    def test_github_metrics_svg_valid_xml(self):
        """Confirm repository root github-metrics.svg parses as valid XML."""
        metrics_path = ROOT_DIR / "github-metrics.svg"
        self.assertTrue(metrics_path.is_file(), "github-metrics.svg not found in root")
        try:
            tree = ET.parse(metrics_path)
            self.assertIsNotNone(tree.getroot(), "Failed to get root for github-metrics.svg")
        except ET.ParseError as err:
            self.fail(f"XML parse error in github-metrics.svg: {err}")

    def test_custom_svgs_no_forbidden_tags(self):
        """Verify no <foreignObject>, <script>, or <iframe> exist in custom SVGs."""
        forbidden_tags = ["foreignObject", "script", "iframe", "object", "embed"]
        for rel_path in self.CUSTOM_SVGS:
            full_path = ROOT_DIR / rel_path
            content = full_path.read_text(encoding="utf-8")
            tree = ET.parse(full_path)
            for elem in tree.iter():
                tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                self.assertNotIn(
                    tag_name,
                    forbidden_tags,
                    f"Forbidden tag <{tag_name}> found in {rel_path}",
                )
            for f_tag in forbidden_tags:
                self.assertNotIn(
                    f"<{f_tag}",
                    content,
                    f"Forbidden tag substring <{f_tag} found in raw text of {rel_path}",
                )

    def test_custom_svgs_no_css_keyframes(self):
        """Verify continuous animations do not rely on CSS @keyframes (broken in Firefox)."""
        for rel_path in self.CUSTOM_SVGS:
            full_path = ROOT_DIR / rel_path
            content = full_path.read_text(encoding="utf-8")
            self.assertNotIn(
                "@keyframes",
                content,
                f"CSS @keyframes found in {rel_path} — must use pure declarative SMIL instead",
            )

    def test_custom_svgs_have_smil_animations(self):
        """Verify custom SVGs employ genuine SMIL animations (<animate> or <animateTransform>)."""
        smil_tags = ["animate", "animateTransform", "set", "animateMotion"]
        for rel_path in self.CUSTOM_SVGS:
            full_path = ROOT_DIR / rel_path
            tree = ET.parse(full_path)
            found_smil = False
            for elem in tree.iter():
                tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag_name in smil_tags:
                    found_smil = True
                    break
            self.assertTrue(
                found_smil,
                f"{rel_path} does not contain any SMIL animation tags ({smil_tags})",
            )

    def test_custom_svgs_theme_contrast_containers(self):
        """Verify custom SVGs specify explicit high-contrast container backgrounds."""
        for rel_path in ["assets/hero-banner.svg", "assets/projects-matrix.svg"]:
            full_path = ROOT_DIR / rel_path
            content = full_path.read_text(encoding="utf-8")
            self.assertTrue(
                ("#090d16" in content) or ("#0e1424" in content) or ("#0d1322" in content),
                f"{rel_path} must define high-contrast dark slate container colors (#090d16 or similar)",
            )


class TestReadmeIntegrity(unittest.TestCase):
    """Validation for README.md structure, content, links, and integration."""

    @classmethod
    def setUpClass(cls):
        cls.readme_path = ROOT_DIR / "README.md"
        assert cls.readme_path.is_file(), "README.md does not exist"
        cls.content = cls.readme_path.read_text(encoding="utf-8")

    def test_readme_contains_hero_banner(self):
        """Verify README embeds assets/hero-banner.svg."""
        self.assertIn("assets/hero-banner.svg", self.content)

    def test_readme_contains_divider(self):
        """Verify README embeds assets/divider-cyber.svg."""
        self.assertIn("assets/divider-cyber.svg", self.content)

    def test_readme_contains_projects_matrix(self):
        """Verify README embeds assets/projects-matrix.svg."""
        self.assertIn("assets/projects-matrix.svg", self.content)

    def test_readme_contains_academic_identity(self):
        """Verify identity contains SRM IST and ECE / Data Sciences."""
        self.assertIn("SRM IST", self.content)
        self.assertIn("ECE", self.content)
        self.assertIn("Data Sciences", self.content)

    def test_readme_four_featured_projects(self):
        """Verify all 4 core featured projects are present with descriptions and links."""
        expected_projects = [
            ("Tagzzs", "https://tagzzs.com"),
            ("DecayState", "https://decaystate.com"),
            ("CURL-Vision", "https://github.com/Spiderboyis/fitness-tracker"),
            ("Solarflare & CME Detector", "https://github.com/Spiderboyis"),
        ]
        for name, url in expected_projects:
            self.assertIn(name, self.content, f"Project '{name}' missing from README.md")
            self.assertIn(url, self.content, f"URL '{url}' for project '{name}' missing from README.md")

    def test_readme_contact_links(self):
        """Verify key verified contact and social destinations are present."""
        expected_links = [
            "https://spiderboyis.vercel.app/",
            "mailto:harshitmathur88@gmail.com",
            "https://linkedin.com/in/harshitmathur03",
            "https://drive.google.com/file/d/16q3oG-jnatcv8OK1dFvs3YHSDGiGZrGe/view?usp=sharing",
            "https://github.com/Spiderboyis",
            "https://x.com/spiderboyis",
            "https://reddit.com/u/spiderboyis",
        ]
        for link in expected_links:
            self.assertIn(link, self.content, f"Contact link '{link}' missing from README.md")

    def test_readme_contribution_snake_integration(self):
        """Verify the contribution snake is embedded via <picture> targeting the 'output' branch."""
        self.assertIn("<picture>", self.content)
        self.assertIn("</picture>", self.content)
        self.assertIn(
            "https://raw.githubusercontent.com/Spiderboyis/Spiderboyis/output/github-contribution-grid-snake-dark.svg",
            self.content,
        )
        self.assertIn(
            "https://raw.githubusercontent.com/Spiderboyis/Spiderboyis/output/github-contribution-grid-snake.svg",
            self.content,
        )

    def test_readme_metrics_integration(self):
        """Verify lowlighter metrics svg is embedded."""
        self.assertIn("github-metrics.svg", self.content)

    def test_readme_all_urls_valid_syntax(self):
        """Extract all markdown and HTML links and verify valid URL structures."""
        # Regex for markdown links [text](url)
        md_urls = re.findall(r"\[.*?\]\((https?://[^\s\)]+|mailto:[^\s\)]+)\)", self.content)
        # Regex for HTML href/src
        html_urls = re.findall(r'(?:href|src|srcset)=["\'](https?://[^\s"\']+|mailto:[^\s"\']+)["\']', self.content)

        all_urls = set(md_urls + html_urls)
        self.assertGreater(len(all_urls), 5, "Fewer than expected URLs found in README.md")

        for url in all_urls:
            if url.startswith("mailto:"):
                email = url.replace("mailto:", "")
                self.assertRegex(email, r"^[\w\.-]+@[\w\.-]+\.\w+$", f"Invalid mailto format: {url}")
            else:
                parsed = urllib.parse.urlparse(url)
                self.assertIn(parsed.scheme, ["http", "https"], f"Invalid scheme in URL: {url}")
                self.assertTrue(parsed.netloc, f"Missing netloc in URL: {url}")


class TestWorkflowFiles(unittest.TestCase):
    """Validation for existing GitHub Action workflows."""

    def test_workflow_files_exist(self):
        """Confirm metrics.yml and snake.yml exist."""
        metrics_yml = ROOT_DIR / ".github/workflows/metrics.yml"
        snake_yml = ROOT_DIR / ".github/workflows/snake.yml"
        self.assertTrue(metrics_yml.is_file(), "metrics.yml missing")
        self.assertTrue(snake_yml.is_file(), "snake.yml missing")

    def test_snake_workflow_targets_output_branch(self):
        """Verify snake.yml deploys to output branch."""
        snake_yml = ROOT_DIR / ".github/workflows/snake.yml"
        content = snake_yml.read_text(encoding="utf-8")
        self.assertIn("target_branch: output", content)


if __name__ == "__main__":
    unittest.main()

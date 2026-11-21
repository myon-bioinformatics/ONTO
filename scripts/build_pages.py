"""Build the Pages introduction from the ONTO README and its images."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/myon-bioinformatics/ONTO"
README_URL = f"{REPO}/blob/main/README.md"
WEB_UI = "acf53d8f0eee8fff28f9e395c0e02dc65ae4f1e2"
WEB_UI_SHA256 = "bd8d1ec0ea94c5134173118217bfd7393373c5492d8bca9b42a6298b267a05f8"
ICON = "docs/assets/onto-icon.png"
FAVICON = "docs/assets/favicon.png"
OVERVIEW = "docs/assets/onto-overview.jpg"
MARKDOWN_LINK = r"\[([^\]\n]+)\]\(([^)\n]+)\)"


def required_match(pattern, source, label):
    match = re.search(pattern, source, re.MULTILINE)
    if match is None:
        raise ValueError(f"README.md: {label} not found")
    return match


def page_spec(readme):
    # Use the README's three introductory sections and its first Python example.
    _, intro, *_ = readme.split("\n\n", 2)
    sections = re.split(r"^## (.+)\n", readme, flags=re.MULTILINE)
    sections = dict(zip(sections[1::2], sections[2::2]))
    diagram = required_match(r"!\[([^\]\n]+)\]\(" + re.escape(OVERVIEW) + r"\)", readme, "overview image")
    role = [re.sub(MARKDOWN_LINK, r"\1", line[2:]) for line in sections["役割"].splitlines() if line.startswith("- ")]
    project_rows = re.findall(r"^- " + MARKDOWN_LINK + r" — (.+)$", sections["紐付け先"], re.MULTILINE)
    if not role or not project_rows:
        raise ValueError("README.md: expected role and project lists")

    api = sections["共通 Python API"]
    install = required_match(r"`(uv pip install [^`]+)`", api, "install command")[1]
    example = required_match(r"^```python\n([\s\S]+?)\n```$", api, "Python example")[1]
    api_links = [
        {"label": label, "href": urljoin(README_URL, path)}
        for label, path in re.findall(MARKDOWN_LINK, sections["役割"] + api)
    ]
    api_links.append({"label": "README の共通 Python API", "href": f"{README_URL}#共通-python-api"})

    return {
        "schema": "web-ui-page/1",
        "title": "ONTO",
        "description": intro,
        "theme": "auto",
        "icon": ICON,
        "favicon": FAVICON,
        "blocks": [
            {"type": "links", "items": [{"label": "GitHub README", "href": README_URL}]},
            {"type": "section", "title": "概念図", "blocks": [
                {"type": "image", "src": OVERVIEW, "alt": diagram[1], "width": 1142, "height": 914},
                {"type": "links", "items": [{"label": "概念図を原寸で開く", "href": OVERVIEW}]},
            ]},
            {"type": "section", "title": "役割", "blocks": [
                {"type": "text", "text": "\n\n".join(role)},
            ]},
            {"type": "section", "title": "関連プロジェクト", "blocks": [
                {"type": "card", "blocks": [
                    {"type": "links", "items": [{"label": name, "href": href}]},
                    {"type": "text", "text": description},
                ]}
                for name, href, description in project_rows
            ]},
            {"type": "section", "title": "共通 Python API", "blocks": [
                {"type": "text", "text": "ONTO をチェックアウトし、リポジトリ直下で導入する。"},
                {"type": "output", "text": install},
                {"type": "output", "text": example},
                {"type": "links", "items": api_links},
            ]},
        ],
    }


def render(spec):
    source_url = f"https://raw.githubusercontent.com/myon-bioinformatics/PySaiyanWeBoo/{WEB_UI}/pysaiyanweboo.py"
    with urlopen(source_url, timeout=30) as response:
        source = response.read()
    if hashlib.sha256(source).hexdigest() != WEB_UI_SHA256:
        raise ValueError("PySaiyanWeBoo renderer SHA-256 mismatch")

    with TemporaryDirectory() as directory:
        renderer = Path(directory) / "pysaiyanweboo.py"
        spec_path = Path(directory) / "page.json"
        renderer.write_bytes(source)
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-X", "utf8", str(renderer), "--page", str(spec_path)],
            check=True,
            stdout=subprocess.PIPE,
        )
    html = result.stdout.decode("utf-8").replace('<html lang="en">', '<html lang="ja">', 1)
    return html.replace("</style>", "\n.ui-page section > img{display:block;max-width:100%;height:auto}\n</style>", 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="directory for the generated site")
    output = parser.parse_args().output
    html = render(page_spec((ROOT / "README.md").read_text(encoding="utf-8")))
    for name in (ICON, FAVICON, OVERVIEW):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (output / "index.html").write_text(html, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

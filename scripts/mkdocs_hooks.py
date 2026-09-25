"""MkDocs build hooks for the SM-Bench documentation site.

Two jobs, both so the Markdown under docs/ can stay written for GitHub:

- publish only the pages listed in ``nav``, so a file that happens to sit in
  docs/ locally is never deployed by accident;
- rewrite links that leave docs/ (``../results/LICENSE.md``) into links to the
  file on GitHub, since the site only contains docs/.
"""

from __future__ import annotations

import posixpath
import re

_OUTSIDE_LINK = re.compile(r"\]\((\.\./[^)\s#]+)(#[^)\s]*)?\)")


def _nav_pages(nav) -> set:
    pages = set()
    if isinstance(nav, str):
        pages.add(nav)
    elif isinstance(nav, dict):
        for value in nav.values():
            pages |= _nav_pages(value)
    elif isinstance(nav, list):
        for item in nav:
            pages |= _nav_pages(item)
    return pages


def on_files(files, config):
    listed = _nav_pages(config["nav"])
    for page in list(files.documentation_pages()):
        if page.src_uri not in listed:
            files.remove(page)
    return files


def on_page_markdown(markdown, page, config, files):
    base = config["repo_url"].rstrip("/") + "/blob/main/"

    def rewrite(match):
        target = posixpath.normpath(
            posixpath.join("docs", posixpath.dirname(page.file.src_uri), match.group(1))
        )
        if target.startswith("docs/"):
            return match.group(0)
        return f"]({base}{target}{match.group(2) or ''})"

    return _OUTSIDE_LINK.sub(rewrite, markdown)

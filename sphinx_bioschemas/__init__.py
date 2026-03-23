"""A Sphinx extension for embedding Bioschemas markup in documentation."""

import datetime
import json
import logging
import os
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast

import yaml
from docutils import nodes
from docutils.parsers import rst
from sphinx.application import Sphinx

logger = logging.getLogger("sphinx-bioschemas")
if not logger.hasHandlers():
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

__version__ = "0.2.0"

BioschemasDef = Union[
    str,
    PathLike[str],
    List[Union[str, PathLike[str]]],
]


def convert_dates(obj):
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(i) for i in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    else:
        return obj


class BioschemasDirective(rst.Directive):
    """Class of the Bioschemas."""

    has_content = False  # In the future we might allow to embed the content bit
    required_arguments = 0  # Make file path optional
    optional_arguments = 1  # File path is now optional
    has_content = True  # Allow embedded content

    option_spec = {
        "format": lambda arg: arg.lower(),  # e.g., "json" or "yaml"
    }

    def run(self) -> list[nodes.raw]:
        data = None
        # If content is provided, use it
        if self.content:
            fmt = self.options.get("format", "yaml")
            content_str = "\n".join(self.content)
            if fmt == "yaml":
                if yaml is None:
                    error = self.state_machine.reporter.error(
                        "pyyaml is required for YAML support.", line=self.lineno
                    )
                    return [error]
                data = yaml.safe_load(content_str)
                data = convert_dates(data)
            elif fmt == "json":
                data = json.loads(content_str)
            else:
                error = self.state_machine.reporter.error(
                    "Unsupported format. Use 'json' or 'yaml'.", line=self.lineno
                )
                return [error]
        elif self.arguments:
            file_path = self.arguments[0]
            data = load_bioschemas_file(file_path)
            if data is None:
                error = self.state_machine.reporter.error(
                    f"Failed to load bioschemas file: {file_path}", line=self.lineno
                )
                return [error]
        else:
            error = self.state_machine.reporter.error(
                "No schema content or file path provided.", line=self.lineno
            )
            return [error]

        jsonld_str = json.dumps(data, indent=2)
        html = f'<script type="application/ld+json">\n{jsonld_str}\n</script>'
        return [nodes.raw("", html, format="html")]


def load_bioschemas_file(file_path: str) -> Optional[dict]:
    """Load a bioschemas file (YAML or JSON) and return its contents as a dict, or None on error."""
    if not os.path.isfile(file_path):
        logger.warning(f"Bioschemas file not found: {file_path}")
        return None
    _, ext = os.path.splitext(file_path)
    try:
        if ext.lower() in [".yaml", ".yml"]:
            if yaml is None:
                logger.error("pyyaml is required for YAML support.")
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        elif ext.lower() in [".json", ".jsonld"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.error(f"Unsupported file type: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to load bioschemas file {file_path}: {e}")
        return None


def create_bioschemas_html(
    pathto: Callable,
    bioschemas_paths: BioschemasDef,
    static_path: Sequence[Union[str, PathLike[str]]],
    confdir: Union[str, PathLike[str]],
) -> Optional[str]:
    """Create <script type=\"application/ld+json\"> tag(s) from bioschemas file(s)."""
    # Normalize input to a list of paths
    if isinstance(bioschemas_paths, (str, PathLike)):
        paths = [bioschemas_paths]
    elif isinstance(bioschemas_paths, list):
        paths = bioschemas_paths
    else:
        return None

    scripts = []
    for path in paths:
        file_path = str(path)
        data = load_bioschemas_file(file_path)
        if data is None:
            continue
        jsonld_str = json.dumps(data, indent=2)
        html = f'<script type="application/ld+json">\n{jsonld_str}\n</script>'
        scripts.append(html)
    return "\n".join(scripts) if scripts else ""


def html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: nodes.document,
) -> None:
    """Update the html page context by adding the Bioschemas

    Args:
        app: The sphinx application
        pagename: the name of the page as string
        templatename: the name of the template as string
        context: the html context dictionary
        doctree: the docutils document tree
    """
    # extract parameters from app
    bioschemas: Optional[BioschemasDef] = app.config["bioschemas"]
    pathto: Callable = context["pathto"]
    static_path = cast(
        Sequence[Union[str, PathLike[str]]], app.config["html_static_path"]
    )  # type: ignore[assignment]
    confdir: Union[str, PathLike[str]] = app.confdir

    if not (doctree and bioschemas):
        return

    bioschemas_html = create_bioschemas_html(pathto, bioschemas, static_path, confdir)
    head_key = "extrahead" if "extrahead" in context else "metatags"
    context[head_key] = context.get(head_key, "") + bioschemas_html


def setup(app: Sphinx):
    """
    Setup function for the sphinx-bioschemas extension.
    """
    app.add_directive("bioschemas", BioschemasDirective)
    app.add_config_value("bioschemas", None, "html")
    app.connect("html-page-context", html_page_context)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

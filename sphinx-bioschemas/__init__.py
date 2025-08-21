"""A Sphinx extension for embedding Bioschemas markup in documentation."""

import datetime
import json
import logging
import os

import yaml
from docutils import nodes
from docutils.parsers import rst
from sphinx.application import Sphinx

logger = logging.getLogger("sphinx-bioschemas")
if not logger.hasHandlers():
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

__version__ = "0.1.0"


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

    required_arguments = 1  # Path to the file
    has_content = False  # In the future we might allow to embed the content bit

    def run(self) -> list[nodes.raw]:
        file_path = self.arguments[0]
        if not os.path.isfile(file_path):
            error = self.state_machine.reporter.error(
                f"Bioschemas file not found: {file_path}", line=self.lineno
            )
            return [error]

        _, ext = os.path.splitext(file_path)
        data = None
        if ext.lower() in [".yaml", ".yml"]:
            if yaml is None:
                error = self.state_machine.reporter.error(
                    "pyyaml is required for YAML support.", line=self.lineno
                )
                return [error]
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                data = convert_dates(data)
                # logger.debug(f"Loaded YAML data from {file_path}: {data}")
        elif ext.lower() in [".json", ".jsonld"]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            error = self.state_machine.reporter.error(
                "Unsupported file type. Use .json, .yaml, or .yml", line=self.lineno
            )
            return [error]

        jsonld_str = json.dumps(data, indent=2)
        html = f'<script type="application/ld+json">\n{jsonld_str}\n</script>'
        return [nodes.raw("", html, format="html")]


def setup(app: Sphinx):
    """
    Setup function for the sphinx-bioschemas extension.
    """
    # app.add_config_value("bioschemas_context", "http://schema.org", "html")
    app.add_directive("bioschemas", BioschemasDirective)
    # app.connect("html-page-context", add_bioschemas_markup)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

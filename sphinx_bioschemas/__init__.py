"""A Sphinx extension for embedding Bioschemas markup in documentation."""

import datetime
import json
import os
from collections.abc import Callable
from os import PathLike
from typing import Any, ClassVar

import yaml
from docutils import nodes
from docutils.parsers import rst
from sphinx.application import Sphinx
from sphinx.config import ENUM
from sphinx.util import logging

from . import validation

logger = logging.getLogger(__name__)

__version__ = "0.3.0"

BioschemasDef = str | PathLike[str] | list[str | PathLike[str]]


def convert_dates(obj):
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(i) for i in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    else:
        return obj


def _dumps_jsonld(data: Any) -> str:
    """json.dumps that never crashes the build on an unserializable scalar (e.g. a bare
    YAML time), instead emitting a best-effort str() fallback; validation flags this
    separately as a 'serialize' finding."""
    try:
        return json.dumps(data, indent=2)
    except TypeError:
        return json.dumps(data, indent=2, default=str)


def _env_confdir(env: Any) -> str:
    """The directory containing conf.py, resolved from a directive's env.

    Sphinx's real BuildEnvironment has no ``confdir`` attribute (only ``srcdir``, which
    coincides with confdir except when a project builds with a separate ``-c`` directory);
    ``confdir`` is only ever set on the Sphinx application object. Try ``confdir`` first
    for compatibility with test doubles that set it directly, then fall back to ``srcdir``.
    """
    confdir = getattr(env, "confdir", None)
    return confdir if confdir is not None else env.srcdir


def _validate_option(argument: str) -> str:
    """Directive :validate: option: "" (bare) means warn; also accepts info/strict/off."""
    value = (argument or "").strip().lower()
    if value in ("", "warn", "on", "true", "yes", "1"):
        return "warn"
    if value in ("info", "strict"):
        return value
    if value in ("off", "false", "no", "0", "none"):
        return "off"
    raise ValueError(
        f"unknown value for :validate: {argument!r}; use info, warn, strict, or off"
    )


class BioschemasDirective(rst.Directive):
    """Class of the Bioschemas."""

    required_arguments = 0  # Make file path optional
    optional_arguments = 1  # File path is now optional
    has_content = True  # Allow embedded content

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "format": lambda arg: arg.lower(),  # e.g., "json" or "yaml"
        "validate": _validate_option,
        "no-validate": rst.directives.flag,
    }

    def run(self) -> list[nodes.Node]:
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
                data = convert_dates(yaml.safe_load(content_str))
            elif fmt == "json":
                data = json.loads(content_str)
            else:
                error = self.state_machine.reporter.error(
                    "Unsupported format. Use 'json' or 'yaml'.", line=self.lineno
                )
                return [error]
        elif self.arguments:
            file_path = self.arguments[0]
            if not os.path.isabs(file_path):
                confdir = _env_confdir(self.state.document.settings.env)
                file_path = os.path.join(confdir, file_path)
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

        self._validate(data)

        jsonld_str = _dumps_jsonld(data)
        html = f'<script type="application/ld+json">\n{jsonld_str}\n</script>'
        return [nodes.raw("", html, format="html")]

    def _validate(self, data: Any) -> None:
        env = getattr(self.state.document.settings, "env", None)
        config = getattr(env, "config", None)
        if config is None:
            return

        mode_override = validation.NOT_SET
        if "no-validate" in self.options:
            mode_override = "off"
        elif "validate" in self.options:
            mode_override = self.options["validate"]

        settings = validation.settings_from_config(
            config, _env_confdir(env), mode_override=mode_override
        )
        if settings is None:
            return

        findings = validation.validate_data(data, settings)
        docname = getattr(env, "docname", None)
        location = (docname, self.lineno) if docname else None
        validation.report(findings, settings, location=location)


_file_cache: dict[tuple[str, int], dict] = {}


def load_bioschemas_file(file_path: str) -> dict | None:
    """Load a bioschemas file (YAML or JSON) and return its contents as a dict, or None on error."""
    if not os.path.isfile(file_path):
        logger.warning(
            f"Bioschemas file not found: {file_path}", type="bioschemas", subtype="file"
        )
        return None
    cache_key = (os.path.abspath(file_path), os.stat(file_path).st_mtime_ns)
    if cache_key in _file_cache:
        return _file_cache[cache_key]
    _, ext = os.path.splitext(file_path)
    try:
        if ext.lower() in [".yaml", ".yml"]:
            if yaml is None:
                logger.error(
                    "pyyaml is required for YAML support.",
                    type="bioschemas",
                    subtype="file",
                )
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = convert_dates(yaml.safe_load(f))
        elif ext.lower() in [".json", ".jsonld"]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            logger.error(
                f"Unsupported file type: {file_path}", type="bioschemas", subtype="file"
            )
            return None
    except Exception as e:  # noqa: BLE001 - any failure here should log and return None, not crash the build
        logger.error(
            f"Failed to load bioschemas file {file_path}: {e}",
            type="bioschemas",
            subtype="file",
        )
        return None
    _file_cache[cache_key] = data
    return data


def create_bioschemas_html(
    bioschemas_paths: BioschemasDef,
    confdir: str | PathLike[str],
) -> str | None:
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
        if not os.path.isabs(file_path):
            file_path = os.path.join(str(confdir), file_path)
        data = load_bioschemas_file(file_path)
        if data is None:
            continue
        jsonld_str = _dumps_jsonld(data)
        html = f'<script type="application/ld+json">\n{jsonld_str}\n</script>'
        scripts.append(html)
    return "\n".join(scripts) if scripts else ""


def html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
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
    bioschemas: BioschemasDef | None = app.config["bioschemas"]
    confdir: str | PathLike[str] = app.confdir

    if not (doctree and bioschemas):
        return

    bioschemas_html = create_bioschemas_html(bioschemas, confdir)
    if not bioschemas_html:
        return
    head_key = "extrahead" if "extrahead" in context else "metatags"
    context[head_key] = context.get(head_key, "") + bioschemas_html


def validate_site_wide(app: Sphinx) -> None:
    """Validate the site-wide ``bioschemas`` config value once, before any page is built."""
    if getattr(app, "_bioschemas_sitewide_validated", False):
        return
    app._bioschemas_sitewide_validated = True

    settings = validation.settings_from_config(app.config, app.confdir)
    if settings is None:
        return

    bioschemas: BioschemasDef | None = app.config["bioschemas"]
    if not bioschemas:
        return
    paths = bioschemas if isinstance(bioschemas, list) else [bioschemas]

    for path in paths:
        file_path = str(path)
        if not os.path.isabs(file_path):
            file_path = os.path.join(str(app.confdir), file_path)
        data = load_bioschemas_file(file_path)
        if data is None:
            continue
        findings = validation.validate_file(file_path, data, settings)
        validation.report(findings, settings, prefix=f"{file_path}: ")


def setup(app: Sphinx):
    """
    Setup function for the sphinx-bioschemas extension.
    """
    app.add_directive("bioschemas", BioschemasDirective)
    app.add_config_value("bioschemas", None, "html")
    app.add_config_value(
        "bioschemas_validate",
        False,
        "env",
        ENUM(True, False, "off", "info", "warn", "strict"),
    )
    app.add_config_value(
        "bioschemas_validate_recommended", "info", "env", ENUM("ignore", "info", "warn")
    )
    app.add_config_value(
        "bioschemas_validate_profile_dir",
        None,
        "env",
        (str, os.PathLike, list, type(None)),
    )
    app.add_config_value("bioschemas_validate_fetch", False, "env", bool)
    app.add_config_value(
        "bioschemas_validate_cache_dir", None, "", (str, os.PathLike, type(None))
    )
    app.add_config_value("bioschemas_validate_timeout", 10.0, "", (int, float))
    app.connect("builder-inited", validate_site_wide)
    app.connect("html-page-context", html_page_context)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

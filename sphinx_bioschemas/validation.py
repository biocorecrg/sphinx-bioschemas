"""Optional schema.org / Bioschemas validation for loaded bioschemas data.

Two tiers:

* Tier 1 (:func:`check_structure`) - zero-dependency structural sanity checks: ``@context``,
  ``@type``, well-formed ``conformsTo``, and JSON-serializability.
* Tier 2 (:func:`check_profile`) - validates the record against the Bioschemas profile's own
  ``$validation`` draft-07 JSON Schema (via the optional ``jsonschema`` package), reporting
  missing *Minimum* (``required``) and *Recommended* properties and schema violations.

:func:`report` is the single place that talks to the logger, so severity policy lives in one
spot.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from sphinx.util import logging

from . import profiles

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_REPORTED_FINDINGS",
    "NOT_SET",
    "Finding",
    "ValidationSettings",
    "check_profile",
    "check_structure",
    "report",
    "reset_caches",
    "settings_from_config",
    "validate_data",
    "validate_file",
]

MAX_REPORTED_FINDINGS = 10

_MODES = ("info", "warn", "strict")
_RECOMMENDED_MODES = ("ignore", "info", "warn")

NO_CONFORMSTO_MSG = (
    "no dct:conformsTo found; only structural checks applied. Add "
    '"http://purl.org/dc/terms/conformsTo": {"@type": "CreativeWork", '
    '"@id": "https://bioschemas.org/profiles/<Name>/<Version>"} to enable profile validation'
)

JSONSCHEMA_MISSING_MSG = (
    "bioschemas_validate is enabled but the 'jsonschema' package is not installed; only "
    'structural checks were applied. Install it with: pip install "sphinx-bioschemas[validate]"'
)

_REQUIRED_RE = re.compile(r"^'(?P<prop>.+)' is a required property$")

# Per-(subtype, mode) severity, before the "recommended" and "always_info" special cases below.
_LEVELS = {
    "required": {"info": "info", "warn": "warning", "strict": "error"},
    "schema": {"info": "info", "warn": "warning", "strict": "error"},
    "context": {"info": "info", "warn": "warning", "strict": "warning"},
    "type": {"info": "info", "warn": "warning", "strict": "warning"},
    "serialize": {"info": "warning", "warn": "warning", "strict": "error"},
    "profile": {"info": "info", "warn": "warning", "strict": "warning"},
    "deps": {"info": "info", "warn": "warning", "strict": "warning"},
}


@dataclass(frozen=True)
class Finding:
    """One validation result. ``always_info`` keeps a finding at info level outside strict
    mode (used for "no profile declared" and "jsonschema not installed", which are advisory
    rather than problems with the data itself)."""

    subtype: str
    message: str
    always_info: bool = False
    once: bool = False


@dataclass
class ValidationSettings:
    mode: str  # "info" | "warn" | "strict"
    recommended: str = "info"  # "ignore" | "info" | "warn"
    profile_dirs: list = field(default_factory=list)
    fetch: bool = False
    cache_dir: str | None = None
    timeout: float = 10.0


def _normalize_mode(raw: Any) -> str | None:
    if raw is False or raw is None:
        return None
    if raw is True:
        return "warn"
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in ("", "off", "false", "none"):
            return None
        if value in _MODES:
            return value
    return None


def _normalize_dirs(raw: Any, confdir: Any) -> list:
    if not raw:
        return []
    items = raw if isinstance(raw, (list, tuple)) else [raw]
    out = []
    for item in items:
        p = str(item)
        if not os.path.isabs(p):
            p = os.path.join(str(confdir), p)
        out.append(p)
    return out


NOT_SET = object()


def settings_from_config(
    config: Any, confdir: Any, mode_override: Any = NOT_SET
) -> ValidationSettings | None:
    """Build a :class:`ValidationSettings` from Sphinx config, or ``None`` if validation is off.

    ``mode_override``, when given, replaces ``config.bioschemas_validate`` (used for a
    directive's ``:validate:``/``:no-validate:`` options, which take precedence over the
    site-wide setting).
    """
    if mode_override is NOT_SET:
        mode = _normalize_mode(getattr(config, "bioschemas_validate", False))
    else:
        mode = _normalize_mode(mode_override)
    if mode is None:
        return None
    recommended = getattr(config, "bioschemas_validate_recommended", "info")
    if recommended not in _RECOMMENDED_MODES:
        recommended = "info"
    return ValidationSettings(
        mode=mode,
        recommended=recommended,
        profile_dirs=_normalize_dirs(
            getattr(config, "bioschemas_validate_profile_dir", None), confdir
        ),
        fetch=bool(getattr(config, "bioschemas_validate_fetch", False)),
        cache_dir=getattr(config, "bioschemas_validate_cache_dir", None),
        timeout=float(getattr(config, "bioschemas_validate_timeout", 10.0) or 10.0),
    )


def _is_schema_org_context(context: Any) -> bool:
    # JSON-LD allows @context to be an object or a list of contexts; only flag bad strings.
    if isinstance(context, (dict, list)):
        return True
    if isinstance(context, str):
        normalized = context.strip().rstrip("/")
        return normalized in ("https://schema.org", "http://schema.org")
    return False


def check_structure(record: dict) -> list[Finding]:
    """Tier 1: zero-dependency structural checks."""
    findings: list[Finding] = []

    context = record.get("@context")
    if context is None:
        findings.append(
            Finding(
                "context", 'missing \'@context\'; add "@context": "https://schema.org/"'
            )
        )
    elif not _is_schema_org_context(context):
        findings.append(
            Finding(
                "context",
                f"unexpected '@context' value {context!r}: schema.org markup should use "
                "'https://schema.org/'",
            )
        )

    if not record.get("@type"):
        findings.append(
            Finding(
                "type",
                "missing '@type'; JSON-LD consumers cannot interpret this record",
            )
        )

    _, malformed = profiles.detect_profiles(record)
    for msg in malformed:
        findings.append(
            Finding(
                "context",
                f"{msg}; expected "
                '{"@type": "CreativeWork", "@id": "https://bioschemas.org/profiles/<Name>/<Version>"}',
            )
        )

    try:
        json.dumps(record)
    except TypeError as e:
        findings.append(
            Finding(
                "serialize",
                f"record is not JSON-serializable and will be emitted incompletely: {e}; "
                "quote unusual scalars (e.g. a bare time) as strings in YAML",
            )
        )

    return findings


def _load_jsonschema():
    try:
        import jsonschema
    except ImportError:
        return None
    return jsonschema


def _flatten_context(error) -> list:
    if not error.context:
        return [error]
    leaves = []
    for sub in error.context:
        leaves.extend(_flatten_context(sub))
    return leaves


def _best_leaves(error) -> list:
    """The most specific sub-errors of an anyOf/oneOf failure (deepest absolute_path)."""
    leaves = _flatten_context(error)
    if not leaves:
        return [error]
    max_depth = max(len(e.absolute_path) for e in leaves)
    return [e for e in leaves if len(e.absolute_path) == max_depth]


def _render_path(path) -> str:
    parts = list(path)
    if not parts:
        return "<root>"
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}" if out else str(p)
    return out


def _check_against_schema(
    record: dict, schema: dict, profile_label: str, jsonschema_module: Any
) -> list[Finding]:
    findings: list[Finding] = []
    validator_cls = jsonschema_module.validators.validator_for(
        schema, default=jsonschema_module.Draft7Validator
    )
    validator = validator_cls(schema)

    seen_required: set = set()
    other_entries: list[tuple[str, str]] = []

    for error in validator.iter_errors(record):
        if error.validator == "required" and not error.absolute_path:
            match = _REQUIRED_RE.match(error.message)
            prop = match["prop"] if match else error.message
            # Old pre-1.0 profiles sometimes list the JSON-LD keys "type"/"id" as required;
            # a record carrying "@type"/"@id" already satisfies the intent.
            if f"@{prop}" in record or prop in seen_required:
                continue
            seen_required.add(prop)
            findings.append(
                Finding(
                    "required",
                    f"missing required property {prop!r} for profile {profile_label} "
                    "(Bioschemas marginality: Minimum)",
                )
            )
            continue
        for leaf in _best_leaves(error):
            other_entries.append((_render_path(leaf.absolute_path), leaf.message))

    deduped = list(dict.fromkeys(other_entries))
    capped = deduped[:MAX_REPORTED_FINDINGS]
    for path, msg in capped:
        findings.append(Finding("schema", f"{path}: {msg} (profile {profile_label})"))
    remaining = len(deduped) - len(capped)
    if remaining > 0:
        findings.append(
            Finding(
                "schema",
                f"... and {remaining} more validation problems in this record "
                f"(showing first {MAX_REPORTED_FINDINGS}) (profile {profile_label})",
            )
        )

    recommended = schema.get("recommended") or []
    missing_recommended = sorted(p for p in recommended if p not in record)
    if missing_recommended:
        findings.append(
            Finding(
                "recommended",
                f"profile {profile_label}: {len(missing_recommended)} recommended properties "
                f"missing: {', '.join(missing_recommended)}",
            )
        )

    return findings


def check_profile(record: dict, settings: ValidationSettings) -> list[Finding]:
    """Tier 2: validate ``record`` against each declared Bioschemas profile's JSON Schema."""
    findings: list[Finding] = []
    targets, _ = profiles.detect_profiles(
        record
    )  # malformed entries are check_structure's job
    if not targets:
        findings.append(Finding("profile", NO_CONFORMSTO_MSG, always_info=True))
        return findings

    refs = []
    seen = set()
    for target in targets:
        ref = profiles.parse_profile_url(target)
        if ref is None:
            findings.append(
                Finding(
                    "profile",
                    f"conformsTo target {target!r} is not a recognised Bioschemas profile URL "
                    "(expected https://bioschemas.org/profiles/<Name>/<Version>); skipping "
                    "schema validation",
                )
            )
            continue
        key = (ref.name, ref.version)
        if key in seen:
            continue
        seen.add(key)
        refs.append(ref)

    if not refs:
        return findings

    jsonschema_module = _load_jsonschema()
    if jsonschema_module is None:
        findings.append(
            Finding("deps", JSONSCHEMA_MISSING_MSG, always_info=True, once=True)
        )
        return findings

    for ref in refs:
        schema, error_msg = profiles.resolve_validation_schema(ref, settings)
        if error_msg:
            findings.append(Finding("profile", error_msg))
        if schema is None:
            continue
        profile_label = f"{ref.name}/{ref.version}"
        findings.extend(
            _check_against_schema(record, schema, profile_label, jsonschema_module)
        )

    return findings


def validate_data(data: Any, settings: ValidationSettings | None) -> list[Finding]:
    """Pure entry point: run Tier 1 + Tier 2 checks over every JSON-LD record in ``data``."""
    if settings is None:
        return []
    records = list(profiles.iter_records(data))
    if not records:
        if not isinstance(data, (dict, list)):
            return [
                Finding(
                    "schema",
                    "expected a JSON-LD object (dict) or a list/@graph of objects, got "
                    f"{type(data).__name__}",
                )
            ]
        return []

    findings: list[Finding] = []
    for label, record in records:
        prefix = f"{label}: " if label else ""
        for f_ in check_structure(record) + check_profile(record, settings):
            if prefix:
                f_ = Finding(f_.subtype, prefix + f_.message, f_.always_info, f_.once)
            findings.append(f_)
    return findings


def _level_for(finding: Finding, settings: ValidationSettings) -> str | None:
    mode = settings.mode
    if finding.subtype == "recommended":
        if mode == "strict":
            return "warning"
        if settings.recommended == "ignore":
            return None
        return "warning" if settings.recommended == "warn" else "info"
    if finding.always_info and mode != "strict":
        return "info"
    return _LEVELS[finding.subtype][mode]


_findings_cache: dict[tuple[str, int], list] = {}


def reset_caches() -> None:
    _findings_cache.clear()


def validate_file(
    file_path: str, data: Any, settings: ValidationSettings | None
) -> list[Finding]:
    """``validate_data`` with a per-(path, mtime) cache, mirroring ``_file_cache``."""
    if settings is None:
        return []
    try:
        cache_key = (os.path.abspath(file_path), os.stat(file_path).st_mtime_ns)
    except OSError:
        cache_key = None
    if cache_key is not None and cache_key in _findings_cache:
        return _findings_cache[cache_key]
    findings = validate_data(data, settings)
    if cache_key is not None:
        _findings_cache[cache_key] = findings
    return findings


def report(
    findings: list,
    settings: ValidationSettings | None,
    location: Any = None,
    prefix: str = "",
) -> None:
    """The only place validation findings are logged."""
    if not findings or settings is None:
        return
    for finding in findings:
        level = _level_for(finding, settings)
        if level is None:
            continue
        method = getattr(logger, level)
        kwargs: dict[str, Any] = {"type": "bioschemas", "subtype": finding.subtype}
        if location is not None:
            kwargs["location"] = location
        if finding.once:
            kwargs["once"] = True
        method(f"{prefix}{finding.message}", **kwargs)

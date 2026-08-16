"""Resolution of Bioschemas profile validation schemas.

Given a ``conformsTo`` target URL such as
``https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE``, this module resolves the
profile's machine-readable ``$validation`` JSON Schema (draft-07), preferring a local directory
of profile files and only reaching the network when explicitly permitted.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.request
from typing import Any, NamedTuple

from sphinx.util import logging

logger = logging.getLogger(__name__)

__all__ = [
    "ProfileRef",
    "detect_profiles",
    "iter_records",
    "parse_profile_url",
    "raw_github_url",
    "reset_caches",
    "resolve_validation_schema",
]

PROFILE_URL_RE = re.compile(
    r"^https?://(?:www\.)?bioschemas\.org/profiles/"
    r"(?P<name>[A-Za-z][A-Za-z0-9]*)/(?P<version>[0-9][0-9A-Za-z._-]*)/?(?:[#?].*)?$"
)
LEGACY_PROFILE_URL_RE = re.compile(
    r"^https?://(?:www\.)?bioschemas\.org/specifications/"
    r"(?P<name>[A-Za-z][A-Za-z0-9]*)/specification/(?P<version>[0-9][0-9A-Za-z._-]*)/?(?:[#?].*)?$"
)

# Every spelling of dct:conformsTo seen in the wild, plus the bare key some hand-written
# records use.
CONFORMS_KEYS = (
    "http://purl.org/dc/terms/conformsTo",
    "https://purl.org/dc/terms/conformsTo",
    "dct:conformsTo",
    "dcterms:conformsTo",
    "dc:conformsTo",
    "conformsTo",
)

RAW_GITHUB_TEMPLATE = (
    "https://raw.githubusercontent.com/BioSchemas/specifications/master/"
    "{name}/jsonld/{name}_v{version}.json"
)

USER_AGENT = "sphinx-bioschemas (+https://github.com/biocorecrg/sphinx-bioschemas)"


class ProfileRef(NamedTuple):
    name: str
    version: str
    url: str


def parse_profile_url(url: Any) -> ProfileRef | None:
    """Parse a conformsTo target into a ``ProfileRef``, or ``None`` if unrecognised."""
    if not isinstance(url, str):
        return None
    candidate = url.strip()
    for regex in (PROFILE_URL_RE, LEGACY_PROFILE_URL_RE):
        match = regex.match(candidate)
        if match:
            return ProfileRef(name=match["name"], version=match["version"], url=url)
    return None


def raw_github_url(ref: ProfileRef) -> str:
    return RAW_GITHUB_TEMPLATE.format(name=ref.name, version=ref.version)


def iter_records(data: Any):
    """Yield ``(label, record)`` for each JSON-LD object found in ``data``.

    Handles a plain object, a top-level list of objects, and an ``@graph``-wrapped document.
    """
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            for i, item in enumerate(graph):
                if isinstance(item, dict):
                    yield f"@graph[{i}]", item
            return
        yield "", data
        return
    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                yield f"[{i}]", item
        return


def _conforms_targets(value: Any) -> list[tuple[str | None, str | None]]:
    """Flatten one conformsTo value into ``(target, malformed_message)`` pairs."""
    if isinstance(value, str):
        return [(value, None)]
    if isinstance(value, dict):
        target = value.get("@id")
        if target:
            return [(target, None)]
        return [(None, "entry has no '@id'")]
    if isinstance(value, list):
        results: list[tuple[str | None, str | None]] = []
        for item in value:
            results.extend(_conforms_targets(item))
        return results
    return [(None, f"unexpected value type {type(value).__name__!r}")]


def detect_profiles(record: dict) -> tuple[list[str], list[str]]:
    """Return ``(targets, malformed_messages)`` found via any conformsTo-style key."""
    targets: list[str] = []
    malformed: list[str] = []
    for key in CONFORMS_KEYS:
        if key not in record:
            continue
        for target, error in _conforms_targets(record[key]):
            if error:
                malformed.append(f"{key!r} {error}")
            elif target:
                targets.append(target)
    return targets, malformed


_profile_cache: dict[tuple[str, str], tuple[dict | None, str | None]] = {}
_cache_write_warned = False


def reset_caches() -> None:
    global _cache_write_warned
    _profile_cache.clear()
    _cache_write_warned = False


def _cache_dir(settings) -> str:
    if settings.cache_dir:
        return str(settings.cache_dir)
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return os.path.join(base, "sphinx-bioschemas", "profiles")


def _cache_filename(ref: ProfileRef) -> str:
    return f"{ref.name}_v{ref.version}.json"


def _read_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _local_candidates(ref: ProfileRef, profile_dirs: list[str]):
    for d in profile_dirs:
        yield os.path.join(d, f"{ref.name}_v{ref.version}.json")
        yield os.path.join(d, ref.name, "jsonld", f"{ref.name}_v{ref.version}.json")
        yield os.path.join(d, f"{ref.name}_v{ref.version}.jsonld")
        yield os.path.join(d, f"{ref.name}.json")


def _find_local_spec(
    ref: ProfileRef, profile_dirs: list[str]
) -> tuple[dict | None, str | None]:
    for path in _local_candidates(ref, profile_dirs):
        if not os.path.isfile(path):
            continue
        try:
            return _read_json_file(path), None
        except Exception as e:  # noqa: BLE001 - any parse failure just skips schema validation
            return None, f"failed to parse local Bioschemas profile file {path}: {e}"
    return None, None


def _urlopen(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def _fetch_remote_spec(
    ref: ProfileRef, timeout: float, cache_dir: str
) -> tuple[dict | None, str | None]:
    url = raw_github_url(ref)
    try:
        with _urlopen(url, timeout) as response:
            payload = response.read()
        spec = json.loads(payload)
    except Exception as e:  # noqa: BLE001 - network/parse failures must never break the build
        return None, str(e)
    _write_cache(cache_dir, ref, payload)
    return spec, None


def _write_cache(cache_dir: str, ref: ProfileRef, payload: bytes) -> None:
    global _cache_write_warned
    try:
        os.makedirs(cache_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=cache_dir)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
            os.replace(tmp_path, os.path.join(cache_dir, _cache_filename(ref)))
        except Exception:
            os.unlink(tmp_path)
            raise
    except OSError as e:
        if not _cache_write_warned:
            logger.info(
                f"could not write Bioschemas profile cache to {cache_dir}: {e}",
                type="bioschemas",
                subtype="profile",
            )
            _cache_write_warned = True


def _extract_validation_schema(spec: Any) -> dict | None:
    if not isinstance(spec, dict):
        return None
    graph = spec.get("@graph")
    if not isinstance(graph, list):
        return None
    for entry in graph:
        if isinstance(entry, dict) and "$validation" in entry:
            return entry["$validation"]
    return None


def _schema_version_values(spec: dict) -> list[str]:
    graph = spec.get("@graph")
    if not isinstance(graph, list):
        return []
    for entry in graph:
        if isinstance(entry, dict) and "$validation" in entry:
            value = entry.get("schema:schemaVersion")
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [value]
            return []
    return []


def resolve_validation_schema(
    ref: ProfileRef, settings
) -> tuple[dict | None, str | None]:
    """Resolve ``ref`` to its ``$validation`` schema, or ``(None, message)`` if unavailable.

    Memoised per ``(name, version)`` so a given profile is looked up (and, if
    ``fetch`` is enabled, downloaded) at most once per process.
    """
    cache_key = (ref.name, ref.version)
    if cache_key in _profile_cache:
        return _profile_cache[cache_key]
    result = _resolve_uncached(ref, settings)
    _profile_cache[cache_key] = result
    return result


def _resolve_uncached(ref: ProfileRef, settings) -> tuple[dict | None, str | None]:
    spec, local_err = _find_local_spec(ref, settings.profile_dirs)
    if local_err:
        return None, f"{local_err}; skipping schema validation"

    if spec is None:
        cache_dir = _cache_dir(settings)
        cached_path = os.path.join(cache_dir, _cache_filename(ref))
        if os.path.isfile(cached_path):
            try:
                spec = _read_json_file(cached_path)
            except Exception:  # noqa: BLE001 - a corrupt cache entry just falls through to (re)fetch
                spec = None

    if spec is None:
        if not settings.fetch:
            return None, (
                f"cannot resolve Bioschemas profile {ref.url!r}: not found in "
                f"bioschemas_validate_profile_dir ({settings.profile_dirs!r}) and "
                "bioschemas_validate_fetch is False; skipping schema validation "
                "(structural checks still applied)"
            )
        spec, fetch_err = _fetch_remote_spec(
            ref, settings.timeout, _cache_dir(settings)
        )
        if spec is None:
            return None, (
                f"failed to fetch Bioschemas profile {ref.name}/{ref.version} from "
                f"{raw_github_url(ref)}: {fetch_err}; skipping schema validation"
            )

    schema = _extract_validation_schema(spec)
    if schema is None:
        return None, (
            f"profile {ref.name}/{ref.version} has no machine-readable '$validation'; "
            "only structural checks applied"
        )

    version_values = _schema_version_values(spec)
    if version_values and ref.url not in version_values:
        return schema, (
            f"profile {ref.name}/{ref.version} spec does not declare a schemaVersion "
            f"matching {ref.url!r} (found {version_values!r}); using schema anyway"
        )
    return schema, None

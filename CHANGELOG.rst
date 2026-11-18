=========
Changelog
=========

All notable changes to this project are documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

Unreleased
===

Added
-----

- Support for Python 3.14 (with Sphinx 6.2 or later).

Removed
-------

- Support for Python 3.10. The minimum is now Python 3.11.

Fixed
-----

- Documented that Python 3.13 and later need Sphinx 6.2 or later, because Sphinx 5.3 imports
  the ``imghdr`` module, which Python 3.13 removed.

0.3.0 - 2026-08-13
==================

Added
-----

- Optional two-tier validation of embedded markup: structural sanity checks
  (``@context``, ``@type``, well-formed ``conformsTo``, JSON-serializability)
  and, for records that declare a Bioschemas profile, validation against
  that profile's own machine-readable ``$validation`` JSON Schema (missing
  *Minimum*/*Recommended* properties, schema violations). The profile-schema
  tier requires the new optional ``jsonschema`` dependency
  (``pip install "sphinx-bioschemas[validate]"``); without it, structural
  checks still run.
- Six new ``conf.py`` values: ``bioschemas_validate``,
  ``bioschemas_validate_recommended``, ``bioschemas_validate_profile_dir``,
  ``bioschemas_validate_fetch``, ``bioschemas_validate_cache_dir``,
  ``bioschemas_validate_timeout``. Validation is **off by default**
  (``bioschemas_validate = False``).
- ``:validate:`` and ``:no-validate:`` options on the ``.. bioschemas::``
  directive, to override the site-wide setting for one record.
- Profile schemas resolve local-directory-first
  (``bioschemas_validate_profile_dir``); fetching from GitHub is strictly
  opt-in (``bioschemas_validate_fetch = True``) and cached to disk, so
  builds stay hermetic by default.
- Validation findings are reported as Sphinx warnings/info under the
  ``bioschemas`` warning type with subtypes ``required``, ``recommended``,
  ``schema``, ``context``, ``type``, ``profile``, ``serialize``, and
  ``deps`` — filterable via ``suppress_warnings`` (e.g.
  ``suppress_warnings = ["bioschemas.recommended"]``) and gated by
  ``sphinx-build -W`` like any other Sphinx warning.

Fixed
-----

- The ``.. bioschemas:: <file>`` directive form (referencing an external
  file by path, rather than inline content) crashed every real Sphinx build
  with ``AttributeError: 'BuildEnvironment' object has no attribute
  'confdir'`` — Sphinx's real build environment never had a ``confdir``
  attribute, only ``srcdir``; this only "worked" in the test suite because
  the test double set one. Path resolution now falls back to ``srcdir``.
- A non-JSON-serializable YAML scalar (e.g. an unquoted ``HH:MM:SS`` time,
  parsed by PyYAML as a ``datetime.time``) crashed the whole build with an
  unhandled ``TypeError`` from ``json.dumps()``; it now falls back to a
  best-effort string representation and, when validation is enabled, is
  flagged as a ``bioschemas.serialize`` finding.

Changed
-------

- The extension now logs through ``sphinx.util.logging`` instead of the
  stdlib ``logging`` module. This means file-not-found and file-parse
  failures for ``load_bioschemas_file()`` (previously silent outside a
  configured log handler) are now real, counted Sphinx warnings under
  ``bioschemas.file`` — a build run with ``sphinx-build -W`` that previously
  passed despite a missing/broken bioschemas file may now fail. Restore the
  old quiet behaviour with ``suppress_warnings = ["bioschemas.file"]``.

`Full diff <https://github.com/biocorecrg/sphinx-bioschemas/compare/v0.2.1...v0.3.0>`_

0.2.1 - 2026-08-06
==================

Fixed
-----

- File paths for both the ``.. bioschemas::`` directive argument and the
  site-wide ``bioschemas`` value in ``conf.py`` are now resolved relative to
  ``confdir`` instead of the process's current working directory, so builds
  succeed regardless of where ``sphinx-build`` is invoked from.
- Pinned the GitHub Pages workflow to a valid ``actions/upload-pages-artifact``
  release.

Added
-----

- Pre-commit configuration (``.pre-commit-config.yaml``, usable with
  `prek <https://prek.j178.dev/>`_ or ``pre-commit``) with hygiene checks and
  `ruff <https://docs.astral.sh/ruff/>`_ for linting and formatting.
- Test coverage for the site-wide config path (``create_bioschemas_html()``,
  ``html_page_context()``), previously only exercised indirectly via the docs
  build.

Changed
-------

- Raised the minimum supported Sphinx version to 5.3.0, matching the oldest
  version actually covered by the test matrix.
- Modernized type hints (``X | Y`` unions, builtin ``dict``/``list`` generics)
  and cleaned up unused parameters and imports.

Removed
-------

- The extension no longer attaches a ``StreamHandler`` or forces ``DEBUG``
  level on its logger at import time; logging now defers to the host
  application's configuration.

`Full diff <https://github.com/biocorecrg/sphinx-bioschemas/compare/v0.2.0...v0.2.1>`_

0.2.0 - 2026-03-24
==================

Added
-----

- Site-wide Bioschemas embedding via a ``bioschemas`` value in ``conf.py``,
  injected into every page's ``<head>`` through the ``html-page-context``
  event. Accepts a single file path or a list of paths.
- Support for ``.yml`` and ``.jsonld`` file extensions, in addition to
  ``.yaml`` and ``.json``.

Changed
-------

- Extracted file-loading logic into a shared ``load_bioschemas_file()``
  helper, reused by both the per-page directive and the site-wide path.
- Expanded documentation with MyST/Markdown examples.

`Full diff <https://github.com/biocorecrg/sphinx-bioschemas/compare/v0.1.1...v0.2.0>`_

0.1.1 - 2025-08-21
==================

Added
-----

- Initial public release.
- ``.. bioschemas::`` directive for embedding Bioschemas/Schema.org metadata
  as JSON-LD, loaded from an external YAML or JSON file.
- Support for inline YAML/JSON content directly in the directive body via
  the ``:format:`` option.
- Initial test suite and PyPI packaging/publish workflow.

`Release tag <https://github.com/biocorecrg/sphinx-bioschemas/releases/tag/v0.1.1>`_

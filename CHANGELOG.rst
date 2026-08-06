=========
Changelog
=========

All notable changes to this project are documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/>`_.

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

=================
sphinx-bioschemas
=================

.. image:: https://badge.fury.io/py/sphinx-bioschemas.svg
   :target: https://pypi.org/project/sphinx-bioschemas/
   :alt: PyPI version

A Sphinx extension to embed `Bioschemas profiles <https://bioschemas.org/>`_ or any
`Schema.org structured metadata <https://schema.org>`_ into your Sphinx documentation
as ``<script type="application/ld+json">`` tags.

- Supports **YAML** and **JSON** formats
- Embed metadata **inline** or load from an external file
- Apply markup **per-page** (via directive) or **globally** for all pages (via ``conf.py``)
- Works with **MyST** for Markdown-based Sphinx projects
- Optional **Bioschemas profile validation** against each profile's ``$validation`` JSON Schema

Installation
============

.. code-block:: console

   $ pip install sphinx-bioschemas

Requires Python 3.11 or later and Sphinx 5.3 or later. On Python 3.13 and later, use
Sphinx 6.2 or later: Sphinx 5.3 imports the ``imghdr`` module, which Python 3.13 removed.

Then enable the extension in your ``conf.py``::

   extensions = ['sphinx_bioschemas']

Quick start
===========

**Per-page** (in a ``.rst`` file):

.. code-block:: rst

   .. bioschemas::
      :format: yaml

      "@context": https://schema.org/
      "@type": LearningResource
      name: My Tutorial
      ...

Or load from a file:

.. code-block:: rst

   .. bioschemas:: bioschemas.yaml

**Global** (in ``conf.py``):

.. code-block:: python

   bioschemas = ["bioschemas.yaml"]

Validation (optional)
======================

Markup can be checked against schema.org/JSON-LD basics and, for records that declare a
Bioschemas profile via ``conformsTo``, against that profile's own machine-readable
``$validation`` JSON Schema (missing *Minimum* properties, missing *Recommended* properties,
and type/shape errors).

.. code-block:: console

   $ pip install "sphinx-bioschemas[validate]"

.. code-block:: python

   # conf.py
   bioschemas_validate = "warn"                 # False (default) | "info" | "warn" | "strict"
   bioschemas_validate_profile_dir = "_profiles" # local dir of downloaded profile spec JSON files

Findings are reported through Sphinx's own warning system (``sphinx-build -W`` gates them;
``suppress_warnings = ["bioschemas.recommended"]`` etc. filters them).

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Config value
     - Default
     - Meaning
   * - ``bioschemas_validate``
     - ``False``
     - ``False``/``"off"`` disables; ``True``/``"warn"``, ``"info"``, or ``"strict"`` set the
       severity.
   * - ``bioschemas_validate_recommended``
     - ``"info"``
     - Severity for missing *Recommended* properties: ``"ignore"``, ``"info"``, or ``"warn"``.
   * - ``bioschemas_validate_profile_dir``
     - ``None``
     - Local directory (or list of directories) of downloaded profile spec JSON files, checked
       before any network fetch.
   * - ``bioschemas_validate_fetch``
     - ``False``
     - Allow downloading a profile spec from GitHub when not found locally. Off by default so
       builds stay hermetic; results are cached to disk once fetched.
   * - ``bioschemas_validate_cache_dir``
     - ``None``
     - Where fetched profile specs are cached. Defaults to an XDG cache directory.
   * - ``bioschemas_validate_timeout``
     - ``10.0``
     - Network timeout (seconds) for fetching.

The ``.. bioschemas::`` directive also accepts ``:validate:`` (``info``/``warn``/``strict``/``off``,
overriding the site-wide setting for that record) and ``:no-validate:`` (always skip).

Full documentation
==================

https://biocorecrg.github.io/sphinx-bioschemas/

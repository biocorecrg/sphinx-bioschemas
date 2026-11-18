Introduction
============

Sphinx Bioschemas extension allows authors to embed a `Bioschemas <https://bioschemas.org>`_ and any `Schema.org structured metadata <https://schema.org>`_ in their `Sphinx content <https://www.sphinx-doc.org/>`_.

This was originally designed for embedding Bioschemas structured metadata following the recommendations of the `ELIXIR FAIR Training Handbook <https://elixir-europe-training.github.io/ELIXIR-TrP-FAIR-training-handbook/>`_.


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :hidden:

   markdown

Installation
============

1. Install the extension::

       $ pip install sphinx-bioschemas

   Requires Python 3.11 or later and Sphinx 5.3 or later. On Python 3.13 and later, use
   Sphinx 6.2 or later: Sphinx 5.3 imports the ``imghdr`` module, which Python 3.13 removed.

2. After setting up Sphinx to build your docs, enable it in the
   Sphinx `conf.py` file::

       # conf.py

       # Add sphinx-bioschemas to the extensions list
       extensions = ['sphinx_bioschemas']


Usage
=====

There are two ways to embed Bioschemas markup: per-page using the ``bioschemas`` directive, or globally for all pages via ``conf.py``.

Page-specific
-------------

To include the Bioschemas markup in a specific page, add the ``bioschemas`` directive to your reStructuredText file:

.. code-block:: rst

   .. bioschemas::
      :format: yaml

      "@context": https://schema.org/
      "@type": LearningResource
      "@id": https://biocorecrg.github.io/sphinx-bioschemas/
      "http://purl.org/dc/terms/conformsTo":
      - "@type": CreativeWork
        "@id": "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE"
      about:
        - "@id": https://schema.org
        - "@id": https://edamontology.org/topic_0089
      audience:
      - "@type": Audience
        name: (Markup provider, Markup consumer) WebMaster, people deploying GitHub pages
      name: Sphinx Bioschemas extension
      author:
      - "@type": Person
        name: "Toni Hermoso Pulido"
        "@id": https://orcid.org/0000-0003-2016-6465
        url: https://orcid.org/0000-0003-2016-6465
      - "@type": Organization
        name: "Centre for Genomic Regulation"
        "@id": https://ror.org/03wyzt892
        url: https://www.crg.eu
      dateModified: 2025-08-20
      description: This guide will show you how to do add Schema.org markup to documentation based on Sphinx
      keywords: "schemaorg, Bioschemas, FAIR, GitHub pages"
      license: MIT

Instead of embedding the metadata inline, you can also refer to an existing file in either YAML or JSON format.

With **YAML** files:

.. code-block:: rst

  .. bioschemas:: bioschemas.yaml

With **JSON** files:

.. code-block:: rst

  .. bioschemas:: bioschemas.json

.. note::

   You can also use this directive in Markdown files via MyST. See :doc:`Using bioschemas extension with MyST <markdown>`.

.. bioschemas::
  :format: yaml

  "@context": https://schema.org/
  "@type": LearningResource
  "@id": https://biocorecrg.github.io/sphinx-bioschemas/
  "http://purl.org/dc/terms/conformsTo":
  - "@type": CreativeWork
    "@id": "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE"
  about:
    - "@id": https://schema.org
    - "@id": https://edamontology.org/topic_0089
  audience:
  - "@type": Audience
    name: (Markup provider, Markup consumer) WebMaster, people deploying GitHub pages
  name: Sphinx Bioschemas extension
  author:
  - "@type": Person
    name: "Toni Hermoso Pulido"
    "@id": https://orcid.org/0000-0003-2016-6465
    url: https://orcid.org/0000-0003-2016-6465
  - "@type": Organization
    name: "Centre for Genomic Regulation"
    "@id": https://ror.org/03wyzt892
    url: https://www.crg.eu
  dateModified: 2025-08-21
  description: This guide will show you how to do add Schema.org markup to documentation based on Sphinx
  keywords: "schemaorg, Bioschemas, FAIR, GitHub pages"
  license: MIT

Global
------

To apply Bioschemas markup to every page of your documentation, set the ``bioschemas`` option in ``conf.py`` to a list of YAML or JSON files:

.. code-block:: python

   # conf.py

   bioschemas = ["bioschemas.yaml"]

Multiple files are supported and both YAML and JSON formats are accepted:

.. code-block:: python

   # conf.py

   bioschemas = ["base.yaml", "extra.json"]

.. note::

   Global markup is injected into all pages automatically. Page-specific directives add to it — they do not replace it.


.. _validation:

Validation
==========

Bioschemas markup is easy to get subtly wrong (a missing property, a typo in a key, a
``conformsTo`` that no longer matches the profile version), and none of that breaks the build,
so it can go unnoticed for a long time. Validation catches this at build time, in two tiers:

1. **Structural checks** (always available, no extra dependency): is ``@context`` schema.org,
   is ``@type`` present, is ``conformsTo`` well-formed, is the record JSON-serializable.
2. **Profile checks**: for records that declare a Bioschemas profile via ``conformsTo``, the
   record is validated against that profile's own machine-readable ``$validation`` JSON Schema,
   the same document that defines which properties are *Minimum* (required), *Recommended*,
   and *Optional* for that profile and version. This tier requires the optional ``jsonschema``
   package.

Enable it by installing the extra and setting ``bioschemas_validate``:

.. code-block:: console

   $ pip install "sphinx-bioschemas[validate]"

.. code-block:: python

   # conf.py
   bioschemas_validate = "warn"                  # False (default) | "info" | "warn" | "strict"
   bioschemas_validate_profile_dir = "_profiles"  # see "Resolving profiles" below

Findings are logged through Sphinx's own warning machinery under the ``bioschemas`` type, with
subtypes ``required``, ``recommended``, ``schema``, ``context``, ``type``, ``profile``,
``serialize``, and ``deps``. ``sphinx-build -W`` turns warning- and error-level findings into
build failures (informational ones never fail a build), and any subtype can be silenced with
``suppress_warnings``, e.g.:

.. code-block:: python

   # conf.py
   suppress_warnings = ["bioschemas.recommended"]

``bioschemas_validate`` accepts:

- ``False`` (the default) — validation is off; nothing changes for existing projects.
- ``True`` or ``"warn"`` — missing *Minimum* properties and schema violations are warnings;
  missing *Recommended* properties are informational (tune this with
  ``bioschemas_validate_recommended``, which accepts ``"ignore"``, ``"info"``, or ``"warn"``).
- ``"info"`` — findings are informational only. The one exception is a record that cannot be
  serialized to JSON (``serialize``), which stays a warning because the extension has to emit
  that value as a plain string.
- ``"strict"`` — missing *Minimum* properties, schema violations, and serialization problems
  become errors. Missing *Recommended* properties become warnings, whatever
  ``bioschemas_validate_recommended`` says, and so do the "no ``conformsTo`` found" and
  "``jsonschema`` not installed" notes.

Sphinx does not change its exit status for errors or warnings unless you build with ``-W``, so
``"strict"`` on its own only changes the level findings are logged at. To make bad markup fail
a CI build, use ``"warn"`` or ``"strict"`` together with ``-W``
(``make html SPHINXOPTS="-W --keep-going"``). On Sphinx older than 8.1, ``-W`` stops at the
first warning; add ``--keep-going`` to see them all.

The ``.. bioschemas::`` directive also accepts ``:validate:`` (one of ``info``/``warn``/
``strict``/``off``, overriding the site-wide setting for that one record) and ``:no-validate:``
(always skip, regardless of the site-wide setting). Use these for a record that's intentionally
partial or doesn't conform to any profile.

Resolving profiles
-------------------

Bioschemas builds should stay hermetic and not depend on network access, so profile schemas
are resolved from local directories first:

1. Each directory listed in ``bioschemas_validate_profile_dir`` is checked for a file named
   ``<ProfileName>_v<Version>.json``, the exact filename used upstream, so you can download it
   directly, e.g.:

   .. code-block:: console

      $ mkdir -p _profiles
      $ curl -o _profiles/TrainingMaterial_v1.0-RELEASE.json \
          https://raw.githubusercontent.com/BioSchemas/specifications/master/TrainingMaterial/jsonld/TrainingMaterial_v1.0-RELEASE.json

2. Only if not found there, and only if ``bioschemas_validate_fetch = True`` is set explicitly,
   the extension downloads the spec from the same GitHub location and caches it to disk (an XDG
   cache directory by default, or ``bioschemas_validate_cache_dir``) so later builds don't need
   the network again. This is opt-in and off by default because it makes a build depend on
   GitHub being reachable and on the mutable upstream ``master`` branch.

When a profile can't be resolved, validation falls back to structural checks only and logs
one ``bioschemas.profile`` message explaining why. In ``"warn"`` and ``"strict"`` mode that
message is a warning, so a ``-W`` build fails until you add the profile file, enable fetching,
or silence it with ``suppress_warnings = ["bioschemas.profile"]``. Without ``jsonschema``
installed, profiles are never looked up, so this message does not appear.

This validation has limits: there is no SHACL validation, no resolution of ``@context`` against
a live schema.org vocabulary, and no check that a URL actually resolves. It is a build-time
sanity check against the profile's own declared shape, not a substitute for the official
`Bioschemas validator <https://bioschemas.org/tools>`_.


Resources
=========

- `Training material made FAIR by design <https://elixir-europe-training.github.io/ELIXIR-TrP-FAIR-Material-By-Design/>`_
- `Bioschemas profiles with some examples <https://bioschemas.org/profiles/>`_

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



Resources
=========

- `Training material made FAIR by design <https://elixir-europe-training.github.io/ELIXIR-TrP-FAIR-Material-By-Design/>`_
- `Bioschemas profiles with some examples <https://bioschemas.org/profiles/>`_

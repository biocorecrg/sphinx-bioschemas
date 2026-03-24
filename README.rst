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

Installation
============

.. code-block:: console

   $ pip install sphinx-bioschemas

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

Full documentation
==================

https://biocorecrg.github.io/sphinx-bioschemas/

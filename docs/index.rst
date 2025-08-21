.. Sphinx Bioschemas documentation master file, created by
   sphinx-quickstart on Wed Aug 20 16:05:23 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Sphinx Bioschemas's documentation!
=============================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Example schema
==============

.. bioschemas::
  :format: yaml

  bioschemas:
    "@context": https://schema.org/
    "@type": LearningResource
    "http://purl.org/dc/terms/conformsTo":
    - "@type": CreativeWork
      "@id": "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE"
    about:
      - "@id": https://schema.org
      - "@id": https://edamontology.org/topic_0089
    audience:
    - "@type": Audience
      name: (Markup provider, Markup consumer) WebMaster, people deploying GitHub pages
    name: "Adding Schema.org to a GitHub Pages site based on Sphinx."
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
    description: "This guide will show you how to do add Schema.org markup to a GitHub Pages site based on Sphinx."
    keywords: "schemaorg, TeSS, GitHub pages"
    license: MIT

.. .. bioschemas:: bioschemas.yaml
.. .. bioschemas:: bioschemas.json


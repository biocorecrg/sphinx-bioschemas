# Embedding Bioschemas with Markdown

It is possible to embed Bioschemas with Markdown by using the [MyST parser](https://myst-parser.readthedocs.io/en/latest/) extension.

You need to install `myst-parser`:

```sh
pip install myst-parser
```

and enable it in `conf.py`:

```python
extensions = [
    ...
    "sphinx_bioschemas",
    "myst_parser",
]

# Add this if .md files are not already included as source files
source_suffix = [".rst", ".md"]
```

The directive can be used in the following ways:

With **YAML** files:

````
```{bioschemas} ./bioschemas.yaml
```
````

With **JSON** files:

````
```{bioschemas} ./bioschemas.json
```
````

With inline content, here with **YAML**:

````
```{bioschemas}
:format: yaml

"@context": https://schema.org/
"@type": LearningResource
"@id": https://biocorecrg.github.io/sphinx-bioschemas/
http://purl.org/dc/terms/conformsTo:
  - "@type": CreativeWork
    "@id": https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE
about:
  - "@id": https://schema.org
  - "@id": https://edamontology.org/topic_0089
audience:
  - "@type": Audience
    name: (Markup provider, Markup consumer) WebMaster, people deploying GitHub pages
name: Sphinx Bioschemas extension
author:
  - "@type": Person
    name: Toni Hermoso Pulido
    "@id": https://orcid.org/0000-0003-2016-6465
    url: https://orcid.org/0000-0003-2016-6465
  - "@type": Organization
    name: Centre for Genomic Regulation
    "@id": https://ror.org/03wyzt892
    url: https://www.crg.eu
dateModified: 2025-08-21
description: This guide will show you how to do add Schema.org markup to
  documentation based on Sphinx
keywords: schemaorg, BioSchemas, FAIR, GitHub pages
license: MIT
```
````

```{note}
Global markup configured via `conf.py` also applies to Markdown pages. Page-specific directives add to it rather than replacing it. See the [Global usage](index.rst) section for details.
```

```{bioschemas}
:format: yaml

"@context": https://schema.org/
"@type": LearningResource
"@id": https://biocorecrg.github.io/sphinx-bioschemas/
http://purl.org/dc/terms/conformsTo:
  - "@type": CreativeWork
    "@id": https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE
about:
  - "@id": https://schema.org
  - "@id": https://edamontology.org/topic_0089
audience:
  - "@type": Audience
    name: (Markup provider, Markup consumer) WebMaster, people deploying GitHub pages
name: Sphinx Bioschemas extension
author:
  - "@type": Person
    name: Toni Hermoso Pulido
    "@id": https://orcid.org/0000-0003-2016-6465
    url: https://orcid.org/0000-0003-2016-6465
  - "@type": Organization
    name: Centre for Genomic Regulation
    "@id": https://ror.org/03wyzt892
    url: https://www.crg.eu
dateModified: 2025-08-21
description: This guide will show you how to do add Schema.org markup to
  documentation based on Sphinx
keywords: schemaorg, BioSchemas, FAIR, GitHub pages
license: MIT
```

## Resources

- [Using Markdown with Sphinx](https://www.sphinx-doc.org/en/master/usage/markdown.html)

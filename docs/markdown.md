# Bioschemas extensions with Markdown

It is possible to embed Bioschemas with Markdown by using the [MyST parser](https://myst-parser.readthedocs.io/en/latest/) extension.

You need to install `myst-parser` :

```sh
pip install myst-parser
```

and modify accordingly `conf.py`:

```python
extensions = [
    ...
    "sphinx_bioschemas",
    "myst_parser",
]

source_suffix = [".rst", ".md"]
```

Below some of the potential ways to embed Bioschemas:

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
name: Adding Bioschemas or Schema.org profiles to content written with Sphinx
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
name: Adding Bioschemas or Schema.org profiles to content written with Sphinx
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

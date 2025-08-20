"""A Sphinx extension for embedding Bioschemas markup in documentation."""

from sphinx.application import Sphinx

__version__ = "0.1.0"


def setup(app: Sphinx):
    """
    Setup function for the sphinx-bioschemas extension.
    """
    # app.add_config_value("bioschemas_context", "http://schema.org", "html")
    # app.add_directive("bioschemas", BioschemasDirective)
    # app.connect("html-page-context", add_bioschemas_markup)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

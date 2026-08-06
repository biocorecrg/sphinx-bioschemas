import json
from unittest import mock

from sphinx_bioschemas import (
    BioschemasDirective,
    create_bioschemas_html,
    html_page_context,
)


# Minimal docutils state mock
class DummyReporter:
    def error(self, message, line=None):
        return f"ERROR: {message}"


class DummyStateMachine:
    reporter = DummyReporter()


class DummyEnv:
    confdir = "/fake/confdir"


class DummySettings:
    env = DummyEnv()


class DummyDocument:
    settings = DummySettings()


class DummyState:
    document = DummyDocument()


def make_directive(content=None, arguments=None, options=None):
    directive = BioschemasDirective(
        name="bioschemas",
        arguments=arguments or [],
        options=options or {},
        content=content or [],
        lineno=1,
        content_offset=0,
        block_text="",
        state=DummyState(),
        state_machine=DummyStateMachine(),
    )
    return directive


def test_embedded_yaml_content():
    yaml_content = [
        '"@context": https://schema.org/',
        '"@type": LearningResource',
        "name: Example",
    ]
    directive = make_directive(content=yaml_content, options={"format": "yaml"})
    result = directive.run()
    assert len(result) == 1
    html = result[0].astext()
    assert '<script type="application/ld+json">' in html
    data = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
    assert data["@type"] == "LearningResource"
    assert data["name"] == "Example"


def test_embedded_json_content():
    json_content = [
        "{",
        '  "@context": "https://schema.org/",',
        '  "@type": "LearningResource",',
        '  "name": "Example"',
        "}",
    ]
    directive = make_directive(content=json_content, options={"format": "json"})
    result = directive.run()
    assert len(result) == 1
    html = result[0].astext()
    data = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
    assert data["@type"] == "LearningResource"
    assert data["name"] == "Example"


def test_yaml_file(monkeypatch):
    file_content = (
        '"@context": https://schema.org/\n"@type": LearningResource\nname: Example\n'
    )
    with (
        mock.patch("os.path.isfile", return_value=True),
        mock.patch("builtins.open", mock.mock_open(read_data=file_content)),
    ):
        directive = make_directive(arguments=["bioschemas.yaml"])
        result = directive.run()
        assert len(result) == 1
        html = result[0].astext()
        data = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
        assert data["@type"] == "LearningResource"
        assert data["name"] == "Example"


def test_missing_file():
    with mock.patch("os.path.isfile", return_value=False):
        directive = make_directive(arguments=["missing.yaml"])
        result = directive.run()
        assert "Failed to load bioschemas file" in result[0]


def test_unsupported_format():
    directive = make_directive(content=["foo: bar"], options={"format": "xml"})
    result = directive.run()
    assert "Unsupported format" in result[0]


def test_no_content_or_file():
    directive = make_directive()
    result = directive.run()
    assert "No schema content or file path provided" in result[0]


def test_create_bioschemas_html_single_path():
    file_content = '{"@context": "https://schema.org/", "@type": "LearningResource"}'
    with (
        mock.patch("os.path.isfile", return_value=True),
        mock.patch("builtins.open", mock.mock_open(read_data=file_content)),
    ):
        html = create_bioschemas_html("bioschemas.json", "/fake/confdir")
    assert html is not None
    assert html.count("<script") == 1
    data = json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])
    assert data["@type"] == "LearningResource"


def test_create_bioschemas_html_multiple_paths():
    file_content = '{"@type": "LearningResource"}'
    with (
        mock.patch("os.path.isfile", return_value=True),
        mock.patch("builtins.open", mock.mock_open(read_data=file_content)),
    ):
        html = create_bioschemas_html(["a.json", "b.json"], "/fake/confdir")
    assert html is not None
    assert html.count("<script") == 2


def test_create_bioschemas_html_missing_files():
    with mock.patch("os.path.isfile", return_value=False):
        html = create_bioschemas_html(["missing.json"], "/fake/confdir")
    assert html == ""


def test_create_bioschemas_html_invalid_type():
    html = create_bioschemas_html({"not": "a valid path or list"}, "/fake/confdir")
    assert html is None


class DummyConfig(dict):
    def __getitem__(self, key):
        return self.get(key)


class DummyApp:
    def __init__(self, bioschemas):
        self.config = DummyConfig(bioschemas=bioschemas)
        self.confdir = "/fake/confdir"


def test_html_page_context_injects_script():
    app = DummyApp(bioschemas="bioschemas.json")
    context = {"extrahead": ""}
    file_content = '{"@type": "LearningResource"}'
    with (
        mock.patch("os.path.isfile", return_value=True),
        mock.patch("builtins.open", mock.mock_open(read_data=file_content)),
    ):
        html_page_context(app, "index", "page.html", context, doctree=object())
    assert "<script" in context["extrahead"]


def test_html_page_context_no_doctree():
    app = DummyApp(bioschemas="bioschemas.json")
    context = {}
    html_page_context(app, "index", "page.html", context, doctree=None)
    assert context == {}


def test_html_page_context_no_bioschemas_config():
    app = DummyApp(bioschemas=None)
    context = {}
    html_page_context(app, "index", "page.html", context, doctree=object())
    assert context == {}

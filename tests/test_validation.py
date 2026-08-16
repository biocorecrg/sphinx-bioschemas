import datetime
import json
import os
from types import SimpleNamespace

import pytest

from sphinx_bioschemas import (
    BioschemasDirective,
    profiles,
    validate_site_wide,
    validation,
)

PROFILE_URL = "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE"

MINI_SPEC = {
    "@graph": [
        {
            "@id": "bioschemas:TrainingMaterial",
            "rdfs:label": "TrainingMaterial",
            "$validation": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["name", "keywords"],
                "recommended": ["author", "url"],
                "optional": [],
                "properties": {
                    "name": {"type": "string"},
                    "keywords": {"type": "string"},
                    "url": {"type": "string"},
                    "author": {
                        "oneOf": [
                            {"$ref": "#/definitions/thing"},
                            {"type": "array", "items": {"$ref": "#/definitions/thing"}},
                        ]
                    },
                },
                "definitions": {
                    "thing": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                },
            },
        }
    ]
}

OLD_SPEC = {
    "@graph": [
        {
            "$validation": {
                "type": "object",
                "required": ["type", "name"],
                "recommended": [],
                "properties": {"name": {"type": "string"}},
            }
        }
    ]
}

CAP_SPEC = {
    "@graph": [
        {
            "$validation": {
                "type": "object",
                "required": [],
                "recommended": [],
                "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            }
        }
    ]
}


def _write_spec(dirpath, spec, name="TrainingMaterial_v1.0-RELEASE.json"):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(json.dumps(spec))
    return str(dirpath)


@pytest.fixture
def profile_dir(tmp_path):
    return _write_spec(tmp_path / "_profiles", MINI_SPEC)


def _settings(
    mode="warn",
    recommended="info",
    profile_dirs=None,
    fetch=False,
    cache_dir=None,
    timeout=10.0,
):
    return validation.ValidationSettings(
        mode=mode,
        recommended=recommended,
        profile_dirs=list(profile_dirs or []),
        fetch=fetch,
        cache_dir=cache_dir,
        timeout=timeout,
    )


class _Recorder:
    """Stands in for validation.logger; records (level, message, kwargs) triples."""

    def __init__(self):
        self.calls = []

    def _log(self, level):
        def inner(msg, **kwargs):
            self.calls.append((level, msg, kwargs))

        return inner

    def __getattr__(self, name):
        if name in ("info", "warning", "error"):
            return self._log(name)
        raise AttributeError(name)


class _Config:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _AppConfig(dict):
    """Supports both config['bioschemas'] (dict-style, like html_page_context uses) and
    config.bioschemas_validate (attribute-style, like settings_from_config uses) - matching
    real Sphinx Config objects."""

    def __init__(self, **kwargs):
        super().__init__(kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self.get(key)


class _DirectiveReporter:
    def error(self, message, line=None):
        return f"ERROR: {message}"


def make_directive(
    content=None, options=None, config=None, confdir="/fake/confdir", docname="index"
):
    """Build a real BioschemasDirective with a real (non-Dummy) env exposing config/confdir/docname."""
    env = SimpleNamespace(config=config, confdir=confdir, docname=docname)
    state = SimpleNamespace(document=SimpleNamespace(settings=SimpleNamespace(env=env)))
    state_machine = SimpleNamespace(reporter=_DirectiveReporter())
    return BioschemasDirective(
        name="bioschemas",
        arguments=[],
        options=options or {},
        content=content or [],
        lineno=1,
        content_offset=0,
        block_text="",
        state=state,
        state_machine=state_machine,
    )


def _payload(node):
    html = node.astext()
    return json.loads(html.split(">", 1)[1].rsplit("<", 1)[0])


# --- profiles.py: URL parsing --------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE",
        "http://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE",
        "https://www.bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE",
        "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE/",
        "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE#frag",
        "https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE?x=1",
        "https://bioschemas.org/profiles/TrainingMaterial/0.9-DRAFT-2020_12_08",
        "http://www.bioschemas.org/specifications/Sample/specification/0.2-DRAFT-2018_11_10/",
    ],
)
def test_parse_profile_url_accepts(url):
    ref = profiles.parse_profile_url(url)
    assert ref is not None
    assert ref.url == url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/x",
        "https://bioschemas.org/profiles/",
        "",
        None,
        123,
    ],
)
def test_parse_profile_url_rejects(url):
    assert profiles.parse_profile_url(url) is None


def test_raw_github_url():
    ref = profiles.parse_profile_url(PROFILE_URL)
    assert profiles.raw_github_url(ref) == (
        "https://raw.githubusercontent.com/BioSchemas/specifications/master/"
        "TrainingMaterial/jsonld/TrainingMaterial_v1.0-RELEASE.json"
    )


# --- profiles.py: detect_profiles / iter_records --------------------------------------------


@pytest.mark.parametrize("key", list(profiles.CONFORMS_KEYS))
def test_detect_profiles_key_variants(key):
    targets, malformed = profiles.detect_profiles({key: PROFILE_URL})
    assert targets == [PROFILE_URL]
    assert malformed == []


def test_detect_profiles_dict_with_id():
    record = {"conformsTo": {"@type": "CreativeWork", "@id": PROFILE_URL}}
    targets, _ = profiles.detect_profiles(record)
    assert targets == [PROFILE_URL]


def test_detect_profiles_list_of_dicts():
    record = {
        "http://purl.org/dc/terms/conformsTo": [
            {"@type": "CreativeWork", "@id": PROFILE_URL}
        ]
    }
    targets, _ = profiles.detect_profiles(record)
    assert targets == [PROFILE_URL]


def test_detect_profiles_list_of_strings():
    other = "https://bioschemas.org/profiles/Course/1.0-RELEASE"
    record = {"conformsTo": [PROFILE_URL, other]}
    targets, _ = profiles.detect_profiles(record)
    assert set(targets) == {PROFILE_URL, other}


def test_detect_profiles_dict_without_id_is_malformed():
    targets, malformed = profiles.detect_profiles(
        {"conformsTo": {"@type": "CreativeWork"}}
    )
    assert targets == []
    assert malformed and "no '@id'" in malformed[0]


def test_detect_profiles_none_present():
    assert profiles.detect_profiles({}) == ([], [])


def test_iter_records_plain_dict():
    data = {"@type": "Thing"}
    assert list(profiles.iter_records(data)) == [("", data)]


def test_iter_records_top_level_list():
    data = [{"@type": "A"}, {"@type": "B"}]
    assert [label for label, _ in profiles.iter_records(data)] == ["[0]", "[1]"]


def test_iter_records_graph_wrapper():
    data = {"@graph": [{"@type": "A"}, {"@type": "B"}]}
    assert [label for label, _ in profiles.iter_records(data)] == [
        "@graph[0]",
        "@graph[1]",
    ]


@pytest.mark.parametrize("data", ["not a dict", 42, None])
def test_iter_records_scalar_garbage(data):
    assert list(profiles.iter_records(data)) == []


# --- Tier 1: check_structure -----------------------------------------------------------------


def test_check_structure_missing_context():
    findings = validation.check_structure({"@type": "Thing"})
    assert any(f.subtype == "context" and "missing" in f.message for f in findings)


@pytest.mark.parametrize(
    "context", ["https://schema.org/", "http://schema.org", "https://schema.org"]
)
def test_check_structure_good_context_strings(context):
    findings = validation.check_structure({"@context": context, "@type": "Thing"})
    assert not any(f.subtype == "context" for f in findings)


def test_check_structure_bad_context_string():
    findings = validation.check_structure(
        {"@context": "http://example.org/", "@type": "Thing"}
    )
    assert any(f.subtype == "context" and "unexpected" in f.message for f in findings)


@pytest.mark.parametrize(
    "context", [{"schema": "https://schema.org/"}, ["https://schema.org/"]]
)
def test_check_structure_context_dict_or_list_not_flagged(context):
    findings = validation.check_structure({"@context": context, "@type": "Thing"})
    assert not any(f.subtype == "context" for f in findings)


def test_check_structure_missing_type():
    findings = validation.check_structure({"@context": "https://schema.org/"})
    assert any(f.subtype == "type" for f in findings)


def test_check_structure_malformed_conformsto():
    record = {"conformsTo": {"@type": "CreativeWork"}}
    findings = validation.check_structure(record)
    assert any(f.subtype == "context" and "no '@id'" in f.message for f in findings)


def test_check_structure_serialize_error():
    record = {
        "@context": "https://schema.org/",
        "@type": "Thing",
        "startTime": datetime.time(10, 0),
    }
    findings = validation.check_structure(record)
    assert any(f.subtype == "serialize" for f in findings)


def test_check_structure_clean_record():
    record = {"@context": "https://schema.org/", "@type": "Thing", "name": "ok"}
    assert validation.check_structure(record) == []


# --- Tier 2: check_profile / resolve_validation_schema ---------------------------------------


def test_check_profile_no_conformsto_is_info():
    findings = validation.check_profile({"@type": "Thing"}, _settings())
    assert len(findings) == 1
    assert findings[0].subtype == "profile"
    assert findings[0].always_info is True


def test_check_profile_unrecognized_url():
    findings = validation.check_profile(
        {"conformsTo": "https://example.org/my-profile"}, _settings()
    )
    assert any(
        f.subtype == "profile" and "not a recognised" in f.message for f in findings
    )


def test_check_profile_missing_required(profile_dir):
    pytest.importorskip("jsonschema")
    record = {"conformsTo": PROFILE_URL}
    findings = validation.check_profile(record, _settings(profile_dirs=[profile_dir]))
    required_msgs = {f.message for f in findings if f.subtype == "required"}
    assert any("'keywords'" in m for m in required_msgs)
    assert any("'name'" in m for m in required_msgs)


def test_check_profile_missing_recommended_aggregated(profile_dir):
    pytest.importorskip("jsonschema")
    record = {"conformsTo": PROFILE_URL, "name": "x", "keywords": "y"}
    findings = validation.check_profile(record, _settings(profile_dirs=[profile_dir]))
    rec_findings = [f for f in findings if f.subtype == "recommended"]
    assert len(rec_findings) == 1
    assert "author" in rec_findings[0].message
    assert "url" in rec_findings[0].message


def test_check_profile_nested_anyof_violation(profile_dir):
    pytest.importorskip("jsonschema")
    record = {
        "conformsTo": PROFILE_URL,
        "name": "x",
        "keywords": "y",
        "url": "z",
        "author": [{"@type": "Person", "name": 123}],
    }
    findings = validation.check_profile(record, _settings(profile_dirs=[profile_dir]))
    schema_findings = [f for f in findings if f.subtype == "schema"]
    assert len(schema_findings) == 1
    assert "author[0].name" in schema_findings[0].message
    assert "not of type 'string'" in schema_findings[0].message


def test_check_profile_caps_findings(tmp_path):
    pytest.importorskip("jsonschema")
    profile_dir_ = _write_spec(tmp_path / "_profiles", CAP_SPEC)
    record = {"conformsTo": PROFILE_URL, "items": list(range(15))}
    findings = validation.check_profile(record, _settings(profile_dirs=[profile_dir_]))
    schema_findings = [f for f in findings if f.subtype == "schema"]
    assert len(schema_findings) == validation.MAX_REPORTED_FINDINGS + 1
    assert "and 5 more" in schema_findings[-1].message


def test_check_profile_absent_without_fetch(tmp_path):
    # check_profile short-circuits to a "deps" finding before ever resolving a profile when
    # jsonschema is missing (no point fetching a spec you can't validate against), so this
    # specific "cannot resolve" message depends on jsonschema being installed.
    pytest.importorskip("jsonschema")
    # cache_dir points at a fresh, empty directory so this can't accidentally resolve via a
    # leftover on-disk fetch cache from a previous (real) build on this machine.
    settings = _settings(
        profile_dirs=[str(tmp_path / "empty")],
        fetch=False,
        cache_dir=str(tmp_path / "cache"),
    )
    findings = validation.check_profile({"conformsTo": PROFILE_URL}, settings)
    assert any(
        f.subtype == "profile" and "cannot resolve" in f.message for f in findings
    )
    assert not any(f.subtype in ("required", "schema", "recommended") for f in findings)


def test_resolve_no_validation_key(tmp_path):
    d = tmp_path / "_profiles"
    _write_spec(d, {"@graph": [{"rdfs:label": "X"}]})
    ref = profiles.parse_profile_url(PROFILE_URL)
    schema, err = profiles.resolve_validation_schema(
        ref, _settings(profile_dirs=[str(d)])
    )
    assert schema is None
    assert "no machine-readable" in err


def test_resolve_malformed_json(tmp_path):
    d = tmp_path / "_profiles"
    d.mkdir()
    (d / "TrainingMaterial_v1.0-RELEASE.json").write_text("{not valid json")
    ref = profiles.parse_profile_url(PROFILE_URL)
    schema, err = profiles.resolve_validation_schema(
        ref, _settings(profile_dirs=[str(d)])
    )
    assert schema is None
    assert "failed to parse" in err


def test_resolve_alternate_layout(tmp_path):
    d = tmp_path / "specs"
    nested = d / "TrainingMaterial" / "jsonld"
    _write_spec(nested, MINI_SPEC)
    ref = profiles.parse_profile_url(PROFILE_URL)
    schema, err = profiles.resolve_validation_schema(
        ref, _settings(profile_dirs=[str(d)])
    )
    assert err is None
    assert schema is not None


def test_resolve_memoized(monkeypatch, profile_dir):
    ref = profiles.parse_profile_url(PROFILE_URL)
    settings = _settings(profile_dirs=[profile_dir])
    calls = {"n": 0}
    orig = profiles._read_json_file

    def counting(path):
        calls["n"] += 1
        return orig(path)

    monkeypatch.setattr(profiles, "_read_json_file", counting)
    profiles.resolve_validation_schema(ref, settings)
    profiles.resolve_validation_schema(ref, settings)
    assert calls["n"] == 1


def test_schema_version_mismatch_still_uses_schema(tmp_path):
    spec = json.loads(json.dumps(MINI_SPEC))  # deep copy
    spec["@graph"][0]["schema:schemaVersion"] = [
        "https://bioschemas.org/profiles/TrainingMaterial/0.9-DRAFT"
    ]
    d = tmp_path / "_profiles"
    _write_spec(d, spec)
    ref = profiles.parse_profile_url(PROFILE_URL)
    schema, err = profiles.resolve_validation_schema(
        ref, _settings(profile_dirs=[str(d)])
    )
    assert schema is not None
    assert err is not None and "does not declare a schemaVersion" in err


def test_old_profile_bare_type_required_not_flagged(tmp_path):
    d = tmp_path / "_profiles"
    _write_spec(d, OLD_SPEC)
    record = {"conformsTo": PROFILE_URL, "@type": "Thing", "name": "ok"}
    findings = validation.check_profile(record, _settings(profile_dirs=[str(d)]))
    assert not any(f.subtype == "required" for f in findings)


# --- validate_data (pure entry point) ---------------------------------------------------------


def test_validate_data_settings_none():
    assert validation.validate_data({"@type": "Thing"}, None) == []


def test_validate_data_scalar_input():
    findings = validation.validate_data("not a dict", _settings())
    assert len(findings) == 1
    assert findings[0].subtype == "schema"


def test_validate_data_graph_label_prefix(profile_dir):
    data = {"@graph": [{"conformsTo": PROFILE_URL}]}
    findings = validation.validate_data(data, _settings(profile_dirs=[profile_dir]))
    assert any(f.message.startswith("@graph[0]: ") for f in findings)


# --- graceful degradation without jsonschema ---------------------------------------------------


def test_check_profile_degrades_without_jsonschema(monkeypatch, profile_dir):
    monkeypatch.setattr(validation, "_load_jsonschema", lambda: None)
    findings = validation.check_profile(
        {"conformsTo": PROFILE_URL, "name": "x"}, _settings(profile_dirs=[profile_dir])
    )
    assert [f.subtype for f in findings] == ["deps"]
    assert findings[0].always_info is True
    assert findings[0].once is True


def test_validate_data_degrades_tier1_intact(monkeypatch, profile_dir):
    monkeypatch.setattr(validation, "_load_jsonschema", lambda: None)
    record = {"conformsTo": PROFILE_URL}  # also missing @context/@type
    findings = validation.validate_data(record, _settings(profile_dirs=[profile_dir]))
    subtypes = {f.subtype for f in findings}
    assert {"context", "type", "deps"} <= subtypes
    assert "required" not in subtypes
    assert "schema" not in subtypes


# --- severity mapping / report() ---------------------------------------------------------------


@pytest.mark.parametrize(
    "subtype,mode,expected_level",
    [
        ("required", "info", "info"),
        ("required", "warn", "warning"),
        ("required", "strict", "error"),
        ("schema", "warn", "warning"),
        ("schema", "strict", "error"),
        ("context", "warn", "warning"),
        ("context", "strict", "warning"),
        ("type", "warn", "warning"),
        ("serialize", "info", "warning"),
        ("serialize", "strict", "error"),
        ("profile", "warn", "warning"),
        ("profile", "strict", "warning"),
        ("deps", "warn", "warning"),
    ],
)
def test_report_level_mapping(monkeypatch, subtype, mode, expected_level):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    validation.report([validation.Finding(subtype, "msg")], _settings(mode=mode))
    assert len(recorder.calls) == 1
    level, _msg, kwargs = recorder.calls[0]
    assert level == expected_level
    assert kwargs["type"] == "bioschemas"
    assert kwargs["subtype"] == subtype


@pytest.mark.parametrize("subtype", ["profile", "deps"])
def test_report_always_info_outside_strict(monkeypatch, subtype):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    finding = validation.Finding(subtype, "msg", always_info=True)

    validation.report([finding], _settings(mode="warn"))
    assert recorder.calls[-1][0] == "info"

    validation.report([finding], _settings(mode="strict"))
    assert recorder.calls[-1][0] == "warning"


def test_report_recommended_modes(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    finding = validation.Finding("recommended", "msg")

    validation.report([finding], _settings(mode="warn", recommended="ignore"))
    assert recorder.calls == []

    validation.report([finding], _settings(mode="warn", recommended="warn"))
    assert recorder.calls[-1][0] == "warning"

    validation.report([finding], _settings(mode="warn", recommended="info"))
    assert recorder.calls[-1][0] == "info"

    validation.report([finding], _settings(mode="strict", recommended="ignore"))
    assert recorder.calls[-1][0] == "warning"


def test_report_once_kwarg_passed_through(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    validation.report(
        [validation.Finding("deps", "msg", always_info=True, once=True)], _settings()
    )
    assert recorder.calls[0][2]["once"] is True


def test_report_location_passed_through(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    validation.report(
        [validation.Finding("required", "msg")], _settings(), location=("index", 5)
    )
    assert recorder.calls[0][2]["location"] == ("index", 5)


def test_report_prefix_prepended(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    validation.report(
        [validation.Finding("required", "msg")], _settings(), prefix="file.yaml: "
    )
    assert recorder.calls[0][1] == "file.yaml: msg"


# --- settings_from_config ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_mode",
    [
        (True, "warn"),
        ("warn", "warn"),
        ("info", "info"),
        ("strict", "strict"),
        (False, None),
        (None, None),
        ("off", None),
        ("bogus", None),
    ],
)
def test_settings_from_config_modes(raw, expected_mode):
    config = _Config(bioschemas_validate=raw)
    result = validation.settings_from_config(config, "/tmp")
    if expected_mode is None:
        assert result is None
    else:
        assert result.mode == expected_mode


def test_settings_from_config_mode_override():
    config = _Config(bioschemas_validate=False)
    assert (
        validation.settings_from_config(config, "/tmp", mode_override="strict").mode
        == "strict"
    )
    assert validation.settings_from_config(config, "/tmp", mode_override="off") is None


def test_settings_from_config_normalizes_profile_dirs(tmp_path):
    config = _Config(
        bioschemas_validate="warn",
        bioschemas_validate_profile_dir=["rel", "/abs/path"],
    )
    result = validation.settings_from_config(config, str(tmp_path))
    assert result.profile_dirs[0] == os.path.join(str(tmp_path), "rel")
    assert result.profile_dirs[1] == "/abs/path"


# --- directive integration ----------------------------------------------------------------------


def test_directive_skips_validation_without_config_attr():
    """Mirrors DummyEnv in test_bioschemas.py, which has no `config` attribute at all -
    validation must stay a strict no-op there."""
    env = SimpleNamespace(confdir="/fake/confdir")
    state = SimpleNamespace(document=SimpleNamespace(settings=SimpleNamespace(env=env)))
    state_machine = SimpleNamespace(reporter=_DirectiveReporter())
    directive = BioschemasDirective(
        name="bioschemas",
        arguments=[],
        options={"format": "yaml"},
        content=["name: Example"],
        lineno=1,
        content_offset=0,
        block_text="",
        state=state,
        state_machine=state_machine,
    )
    result = directive.run()
    assert len(result) == 1
    assert _payload(result[0])["name"] == "Example"


def test_directive_integration_reports_and_returns_node(monkeypatch, profile_dir):
    pytest.importorskip("jsonschema")
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    config = _Config(
        bioschemas_validate="warn", bioschemas_validate_profile_dir=profile_dir
    )
    directive = make_directive(
        content=[
            '"@context": https://schema.org/',
            f"conformsTo: {PROFILE_URL}",
            "name: Example",
        ],
        options={"format": "yaml"},
        config=config,
    )
    result = directive.run()
    assert len(result) == 1
    assert _payload(result[0])["name"] == "Example"
    assert any("keywords" in c[1] for c in recorder.calls)


def test_directive_no_validate_suppresses_even_in_strict_mode(monkeypatch, profile_dir):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    config = _Config(
        bioschemas_validate="strict", bioschemas_validate_profile_dir=profile_dir
    )
    directive = make_directive(
        content=["name: OnlyName"],
        options={"format": "yaml", "no-validate": None},
        config=config,
    )
    result = directive.run()
    assert len(result) == 1
    assert recorder.calls == []


def test_directive_validate_override_enables_when_global_off(monkeypatch, profile_dir):
    pytest.importorskip("jsonschema")
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    config = _Config(
        bioschemas_validate=False, bioschemas_validate_profile_dir=profile_dir
    )
    directive = make_directive(
        content=[
            '"@context": https://schema.org/',
            f"conformsTo: {PROFILE_URL}",
            "name: OnlyName",
        ],
        options={"format": "yaml", "validate": "strict"},
        config=config,
    )
    result = directive.run()
    assert len(result) == 1
    assert recorder.calls
    assert any(level == "error" for level, _msg, _kwargs in recorder.calls)


def test_directive_serialize_failure_still_returns_node(monkeypatch, profile_dir):
    """H1: a non-JSON-serializable scalar (bare YAML time) must not crash the build."""
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    config = _Config(
        bioschemas_validate="warn", bioschemas_validate_profile_dir=profile_dir
    )
    directive = make_directive(
        content=[
            '"@context": https://schema.org/',
            "startTime: 10:00:00",
        ],
        options={"format": "yaml"},
        config=config,
    )
    result = directive.run()
    assert len(result) == 1
    html = result[0].astext()
    assert "<script" in html
    assert any(level == "warning" for level, _msg, _kwargs in recorder.calls)


# --- site-wide validation --------------------------------------------------------------------


def test_validate_site_wide_reports_once_and_not_twice(
    monkeypatch, tmp_path, profile_dir
):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)

    f1 = tmp_path / "a.yaml"
    f1.write_text(
        f'"@context": "https://schema.org/"\nconformsTo: {PROFILE_URL}\nname: A\n'
    )
    f2 = tmp_path / "b.yaml"
    f2.write_text(
        f'"@context": "https://schema.org/"\nconformsTo: {PROFILE_URL}\nname: B\n'
    )

    app = SimpleNamespace(
        config=_AppConfig(
            bioschemas=[str(f1), str(f2)],
            bioschemas_validate="warn",
            bioschemas_validate_profile_dir=profile_dir,
        ),
        confdir=str(tmp_path),
    )

    validate_site_wide(app)
    first_count = len(recorder.calls)
    assert first_count > 0

    validate_site_wide(app)
    assert len(recorder.calls) == first_count


def test_validate_site_wide_off_by_default(monkeypatch, tmp_path):
    recorder = _Recorder()
    monkeypatch.setattr(validation, "logger", recorder)
    f1 = tmp_path / "a.yaml"
    f1.write_text("name: A\n")
    app = SimpleNamespace(
        config=_AppConfig(bioschemas=str(f1)),
        confdir=str(tmp_path),
    )
    validate_site_wide(app)
    assert recorder.calls == []

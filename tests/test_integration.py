"""End-to-end tests: run real Sphinx builds against a scratch project and check what the
validator reports and whether ``-W`` fails the build."""

import importlib.util
import shutil
from pathlib import Path

import pytest
from sphinx.cmd.build import build_main

PROFILE = (
    Path(__file__).parent.parent
    / "docs"
    / "_profiles"
    / "TrainingMaterial_v1.0-RELEASE.json"
)
CONFORMS = '"http://purl.org/dc/terms/conformsTo":\n  "@id": https://bioschemas.org/profiles/TrainingMaterial/1.0-RELEASE\n'
VALID = (
    '"@context": https://schema.org/\n"@type": LearningResource\n'
    + CONFORMS
    + "name: n\ndescription: d\nkeywords: k\n"
)
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None
needs_jsonschema = pytest.mark.skipif(
    not HAS_JSONSCHEMA, reason="requires the 'validate' extra"
)


def _indent(text):
    return "".join(f"   {line}\n" for line in text.splitlines())


def build(tmp_path, capsys, conf="", body="", files=None, werror=False):
    src = tmp_path / "src"
    (src / "_profiles").mkdir(parents=True)
    shutil.copy(PROFILE, src / "_profiles")
    (src / "conf.py").write_text(
        'extensions = ["sphinx_bioschemas"]\n'
        'bioschemas_validate_profile_dir = "_profiles"\n' + conf
    )
    (src / "index.rst").write_text("Test\n====\n\n" + body)
    for name, content in (files or {}).items():
        (src / name).write_text(content)
    args = ["-q", "-N", "-E", "-b", "html", str(src), str(tmp_path / "out")]
    status = build_main(["-W", *args] if werror else args)
    out = tmp_path / "out" / "index.html"
    # Sphinx < 8.1 aborts at the first warning under -W, so no HTML may exist.
    html = out.read_text(encoding="utf-8") if out.exists() else ""
    return status, capsys.readouterr().err, html


def directive(content, options=""):
    opts = f"{options}\n" if options else ""
    return f".. bioschemas::\n{opts}\n{_indent(content)}\n"


def test_validation_off_by_default(tmp_path, capsys):
    status, err, html = build(
        tmp_path, capsys, body=directive("name: no context"), werror=True
    )
    assert status == 0
    assert "bioschemas" not in err
    assert 'type="application/ld+json"' in html


def test_valid_record_passes_under_W(tmp_path, capsys):
    status, err, _ = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\n',
        body=directive(VALID),
        werror=True,
    )
    assert status == 0, err


def test_structural_warning_fails_W(tmp_path, capsys):
    status, err, _ = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\n',
        body=directive('"@type": LearningResource\nname: x\n'),
        werror=True,
    )
    assert status != 0
    assert "missing '@context'" in err


@needs_jsonschema
def test_profile_findings_in_warn_mode(tmp_path, capsys):
    record = '"@context": https://schema.org/\n"@type": LearningResource\n' + CONFORMS
    status, err, _ = build(
        tmp_path, capsys, conf='bioschemas_validate = "warn"\n', body=directive(record)
    )
    assert status == 0
    assert "WARNING: missing required property 'name'" in err
    # Recommended properties are info-level by default, hidden by -q.
    assert "recommended properties missing" not in err


@needs_jsonschema
def test_strict_option_errors_and_recommended_warns(tmp_path, capsys):
    record = (
        '"@context": https://schema.org/\n"@type": LearningResource\n'
        + CONFORMS
        + "name: 42\n"
    )
    _, err, _ = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\n',
        body=directive(record, "   :validate: strict"),
    )
    assert "ERROR: missing required property 'description'" in err
    assert "ERROR: name: 42 is not of type 'string'" in err
    assert "WARNING: profile TrainingMaterial/1.0-RELEASE:" in err
    assert "recommended properties missing" in err


def test_no_validate_option_skips(tmp_path, capsys):
    status, err, html = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "strict"\n',
        body=directive("name: partial", "   :no-validate:"),
        werror=True,
    )
    assert status == 0, err
    assert '"name": "partial"' in html


def test_suppress_warnings_subtype(tmp_path, capsys):
    status, err, _ = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\nsuppress_warnings = ["bioschemas.context"]\n',
        body=directive('"@type": LearningResource\nname: x\n'),
        werror=True,
    )
    assert status == 0, err


@needs_jsonschema
def test_site_wide_file_validated_and_injected(tmp_path, capsys):
    status, err, html = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\nbioschemas = "site.yaml"\n',
        files={
            "site.yaml": '"@context": https://schema.org/\n"@type": LearningResource\n'
            + CONFORMS
        },
    )
    assert status == 0
    assert err.count("site.yaml: missing required property") == 3
    assert 'type="application/ld+json"' in html


def test_unresolved_profile_is_a_warning(tmp_path, capsys):
    status, err, _ = build(
        tmp_path,
        capsys,
        conf='bioschemas_validate = "warn"\nbioschemas_validate_profile_dir = "missing"\n',
        body=directive(VALID),
        werror=True,
    )
    if HAS_JSONSCHEMA:
        assert status != 0
        assert "cannot resolve Bioschemas profile" in err
    else:
        # Without jsonschema, profiles are never resolved; only an info note is logged.
        assert status == 0, err

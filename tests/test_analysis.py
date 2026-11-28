from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

import pytest
from vikela.analysis import analyze
from vikela.cli import main


def check(body, prelude="from jsonpit import Pit, PitItem\nfrom inqaba import InqPath\nimport copy\n"):
	return analyze(prelude + "def use(pit: Pit, key: str, patch: dict):\n" + "\n".join("    " + line for line in body.splitlines()))


@pytest.mark.parametrize("body", [
	"item = pit[key]\nacts = []\nacts.append(item)",
	"item = pit.get(key)\nclassItems = []\nclassItems.append(item)",
	"item = pit[key]\nitems = set()\nitems.add(item)",
	"item = pit[key]\nresultPit = []\nresultPit.append(item)",
	"item = pit[key]\nitem.set_property(patch)\npit.add(item)",
	"item = PitItem(key)\nitem.set_property(patch)\npit.add(item)",
	"item = pit[key]\nalias = item\npit.add(alias)",
	"pit.add(pit[key])",
	"item = pit[key]\ndel item['Namespace']\npit.add(item)",
	"items = [pit[key]]\nfor item in items:\n    item.set_property(patch)\nfor item in items:\n    pit.add(item)",
	"item = PitItem(key)\npit.add(item)\nitem = pit.get_at(key, at=stamp)",
	"item = pit.get_at(key, at=stamp)\nitem = PitItem(key)\npit.add(item)",
	"item = unknown_helper(pit, key)\nitem.set_property(patch)\npit.add(item)",
	"item = pit[key]\nitem.set_property({'Id': key, 'Name': 'Name'})",
])
def test_supported_live_fresh_collection_and_unknown_shapes(body):
	assert check(body) == []


@pytest.mark.parametrize("body", [
	"item = pit.get_at(key, at=stamp)\nalias = item\npit.add(alias)",
	"item = copy.deepcopy(pit[key])\npit.add(item)",
	"item = PitItem(pit[key])\npit.add(item)",
	"item = pit[key].to_dict()\npit.add(item)",
	"item = pit.get_at(key, at=stamp)\npit.add(item)\nitem = PitItem(key)",
	"items = [pit.get_at(key, at=stamp)]\nfor item in items:\n    pit.add(item)",
	"item = pit['Known']\npit.delete_item('Known')\npit.add(item)",
	"item = pit[key]\npit.close()\npit.add(item)",
	"a = Pit(InqPath('a'), 'A')\nb = Pit(InqPath('b'), 'B')\nitem = a[key]\nb.add(item)",
	"def snapshot(source, key):\n    return source.get_at(key, at=stamp)\nitem = snapshot(pit, key)\npit.add(item)",
])
def test_proven_unsafe_writes(body):
	findings = check(body)
	assert len(findings) == 1
	assert findings[0].rule == "RAI011"
	assert findings[0].suggestion and findings[0].documentation


@pytest.mark.parametrize("body", [
	"item = pit[key]\nitem['Modified'] = 'bad'",
	"item = pit[key]\nitem.deleted = False",
	"item = pit[key]\nitem.set_property({'Name': 'ok', 'mOdIfIeD': 'bad'})",
	"item = pit[key]\nitem.delete_property('Deleted')",
	"item = pit[key]\ndel item['Id']",
])
def test_protected_attributes(body):
	assert [f.rule for f in check(body)] == ["RAI012"]


def test_collection_named_pit_is_not_a_pit():
	assert analyze("class Pit: pass\npit = Pit()\nitem = pit['x']\nitem['Modified'] = 'x'\npit.add(item)") == []


def test_branch_join_does_not_invent_provenance():
	assert check("item = PitItem(key)\nif condition:\n    item = pit.get_at(key, at=stamp)\npit.add(item)") == []


def test_cli_json_and_fix_alias_do_not_change_source(tmp_path, capsys):
	path = tmp_path / "case.py"
	source = "from jsonpit import Pit; from inqaba import InqPath\npit = Pit(InqPath('a'), 'A')\npit['x']['Modified'] = 'bad'\n"
	path.write_text(source)
	assert main([str(path), "--json", "--qondisa"]) == 1
	out = capsys.readouterr()
	assert json.loads(out.out)[0]["rule"] == "RAI012"
	assert "safe" in out.err and path.read_text() == source
	assert main([str(path), "--json", "--fix"]) == 1
	assert json.loads(capsys.readouterr().out)[0]["fix_available"] is False


def test_cli_exit_codes_and_pure_json(tmp_path, capsys, monkeypatch):
	path = tmp_path / "case.py"; path.write_text("x = 1\n")
	assert main([str(path), "--json"]) == 0
	assert capsys.readouterr().out.strip() == "[]"
	path.write_text("def broken(\n")
	assert main([str(path), "--json"]) == 2
	output = capsys.readouterr(); assert output.out.strip() == "[]" and "case.py" in output.err
	assert main(["--unknown", "--json"]) == 2
	assert capsys.readouterr().out.strip() == "[]"
	monkeypatch.setattr("vikela.cli.inspect_paths", lambda *args: (_ for _ in ()).throw(RuntimeError("broken")))
	assert main([str(path), "--json"]) == 4
	assert capsys.readouterr().out.strip() == "[]"


def test_notebook_cross_cell_analysis_and_locations(tmp_path, capsys):
	path = tmp_path / "case.ipynb"
	path.write_text(json.dumps({"cells": [
		{"cell_type": "code", "source": "from jsonpit import Pit; from inqaba import InqPath\npit = Pit(InqPath('a'), 'A')\nitem = pit['x']"},
		{"cell_type": "markdown", "source": "prose"},
		{"cell_type": "code", "source": "item['Modified'] = 'bad'"},
	]}))
	original = path.read_bytes()
	assert main([str(path), "--json"]) == 1
	finding = json.loads(capsys.readouterr().out)[0]
	assert finding["cell"] == 3 and finding["line"] == 1
	assert path.read_bytes() == original


def test_cell_magic_only_checks_never_executes(capsys, monkeypatch, tmp_path):
	monkeypatch.setenv("IPYTHONDIR", str(tmp_path / "ipython"))
	from vikela import load_ipython_extension, unload_ipython_extension
	from IPython.core.interactiveshell import InteractiveShell
	shell = InteractiveShell.instance()
	load_ipython_extension(shell)
	shell.run_cell_magic("vikela", "--json", "raise RuntimeError('must not execute')")
	assert json.loads(capsys.readouterr().out) == []
	unload_ipython_extension(shell)
	assert "vikela" not in shell.magics_manager.magics["cell"]


def test_pylint_plugin_same_rule_and_location(tmp_path):
	path = tmp_path / "case.py"
	path.write_text("from jsonpit import Pit; from inqaba import InqPath\npit = Pit(InqPath('a'), 'A')\npit['x']['Modified'] = 'bad'\n")
	result = subprocess.run([sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all", "--enable=vikela-protected-attribute,vikela-full-snapshot-write", "--output-format=json", "--persistent=no", str(path)], capture_output=True, text=True)
	assert result.returncode == 4, result.stderr
	finding = json.loads(result.stdout)[0]
	assert finding["symbol"] == "vikela-protected-attribute" and finding["line"] == 3


def test_help_style_plain_and_color(monkeypatch, capsys):
	from vikela.style import help_text, width
	monkeypatch.setenv("NO_COLOR", "1")
	plain = help_text()
	assert "\\t" not in plain and "\t" not in plain and "\033" not in plain
	assert "--qondisa" in plain and "🛡️" in plain
	assert width("🛡️") == 2
	lines = plain.splitlines(); assert width(lines[0]) == width(lines[1]) == width(lines[2])
	monkeypatch.delenv("NO_COLOR")
	monkeypatch.setenv("TERM", "xterm-256color")
	monkeypatch.setattr("sys.stdout.isatty", lambda: True)
	assert "\033[1;36m" in help_text() and "\033[38;5;208m" in help_text()


def test_shared_project_configuration(tmp_path, capsys):
	path = tmp_path / "case.py"
	path.write_text("from jsonpit import Pit; from inqaba import InqPath\npit = Pit(InqPath('a'), 'A')\npit['x']['Modified'] = 'bad'\n")
	config = tmp_path / "pyproject.toml"
	config.write_text('[tool.vikela]\ndisable = ["RAI012"]\n')
	assert main([str(path), "--json"]) == 0
	assert json.loads(capsys.readouterr().out) == []
	result = subprocess.run([sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all", "--enable=vikela-protected-attribute", "--persistent=no", "--output-format=json", str(path)], capture_output=True, text=True)
	assert result.returncode == 0 and json.loads(result.stdout) == []
	config.write_text('[tool.vikela]\ndisable = ["typo"]\n')
	assert main([str(path), "--json"]) == 2
	assert json.loads(capsys.readouterr().out) == []


def test_explicit_none_time_is_live_and_casts_preserve_detachment():
	assert check("item = pit.get(key, at=None)\npit.add(item)") == []
	assert check("item = pit.get_at(key, at=None)\npit.add(item)") == []
	body = "from typing import cast\nitem = cast(PitItem, pit.get_at(key, stamp))\npit.add(item)"
	assert [f.rule for f in check(body)] == ["RAI011"]


def test_helper_collection_indirection_tracks_detached_elements():
	body = "def fill(source, target):\n    target.append(source.get_at(key, stamp))\nitems = []\nfill(pit, items)\nfor item in items:\n    pit.add(item)"
	assert [f.rule for f in check(body)] == ["RAI011"]


@pytest.mark.parametrize("name,body", json.loads((Path(__file__).parent / "fixtures/sipho-python-probes.json").read_text()).items())
def test_all_26_python_counterparts(name, body):
	prelude = "from jsonpit import Pit, PitItem\nfrom typing import cast\ndef fetch(source: Pit, key):\n    return source[key]\n"
	source = prelude + "def use(pit: Pit, key: str, id: str, patch: dict, generated: list[PitItem], i):\n" + "\n".join("    " + line for line in body.splitlines())
	assert analyze(source) == [], name


@pytest.mark.parametrize("definition", ["class Pit: pass", "def Pit(*args): return {}"])
def test_shadowed_import_is_not_a_jsonpit_receiver(definition):
	source = "from jsonpit import Pit\n" + definition + "\npit = Pit()\npit['x']['Modified'] = 'ordinary JSON'\n"
	assert analyze(source) == []


def test_local_import_does_not_leak_into_other_function():
	source = "def first():\n    from jsonpit import Pit\n    from inqaba import InqPath\n    pit = Pit(InqPath('a'), 'A')\ndef second():\n    pit = Pit()\n    pit['x']['Modified'] = 'unresolved'\n"
	assert analyze(source) == []


def test_clone_is_detached_and_merge_is_a_supported_live_patch():
	assert [f.rule for f in check("item = pit[key].clone()\npit.add(item)")] == ["RAI011"]
	assert check("item = pit[key]\nitem.merge({'Status': 'Doing'})") == []


def test_distribution_and_runtime_versions_launch_in_lockstep():
	import tomllib
	from pathlib import Path
	from vikela import __version__
	project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]
	assert __version__ == project["version"] == "4.7.3"


def test_umgodi_constructor_and_annotation_provenance():
	findings = check("item = PitItem(key)\nitem['Deleted'] = True\npit.add(pit.get_at(key, at=stamp))",
		prelude="from umgodi.store import Pit\nfrom umgodi import PitItem\n")
	assert [finding.rule for finding in findings] == ["RAI012", "RAI011"]


@pytest.mark.parametrize("source", [
	'import os\nos.environ["HOME"] = "/tmp/home"',
	'def test_config(monkeypatch):\n    monkeypatch.setenv("RAIKEEP_CONFIG", "/tmp/config")',
	'from unittest.mock import patch\nimport os\nwith patch.dict(os.environ, {}, clear=True): pass',
	'from inqaba import InqConfig\nfake = InqConfig({"Cloud": {"Dropbox": "/tmp"}})',
	'from inqaba import InqConfig\nmonkeypatch.setattr(InqConfig, "load", lambda: None)',
	'from inqaba import InqConfig\ncfg = InqConfig.load()\ncfg.clouds["Dropbox"] = "/tmp"',
	'from inqaba import InqConfig\ncfg = InqConfig.load()\ncfg.data["Cloud"]["Dropbox"] = "/tmp"',
	'import os\nos.environ.update({"HOME": "/tmp/home"})',
	'from pathlib import Path\np = Path("/tmp") / "RAIkeep.json5"\np.write_text("{}")',
	'from pathlib import Path\np = Path("/tmp/RAIkeep.json5")\nwith p.open("w") as stream: pass',
])
def test_real_configuration_guard_rejects_substitutions(source):
	findings = analyze(source)
	assert len(findings) == 1
	assert findings[0].rule == "RAI021"
	assert findings[0].severity == "Error"


def test_real_configuration_guard_allows_read_only_configuration():
	source = 'from pathlib import Path\np = Path.home() / ".config" / "RAIkeep.json5"\ntext = p.read_text()\n'
	assert analyze(source) == []


def test_real_configuration_guard_is_a_cli_error(tmp_path, capsys):
	source = tmp_path / "example.py"
	source.write_text('from pathlib import Path\nPath("/tmp/RAIkeep.json5").write_text("{}")\n')
	assert main([str(source), "--json"]) == 1
	finding = json.loads(capsys.readouterr().out)[0]
	assert finding["rule"] == "RAI021" and finding["severity"] == "Error"
	assert main([str(source), "--disable", "RAI021", "--json"]) == 2


def test_real_configuration_guard_is_a_pylint_error(tmp_path):
	source = tmp_path / "example.py"
	source.write_text('from pathlib import Path\nPath("/tmp/RAIkeep.json5").write_text("{}")\n')
	result = subprocess.run(
		[sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all",
		 "--enable=vikela-test-configuration", "--output-format=json", "--persistent=no", str(source)],
		capture_output=True, text=True,
	)
	assert result.returncode == 2, result.stderr
	finding = json.loads(result.stdout)[0]
	assert finding["symbol"] == "vikela-test-configuration"
	assert finding["line"] == 2


@pytest.mark.parametrize("source", [
	'from umgodi import Pit\ndef test_pit(tmp_path):\n    Pit.open(tmp_path / "Person")',
	'from umgodi import Pit\nfrom tempfile import mkdtemp\nroot = mkdtemp()\nPit.open(root)',
	'from pathlib import Path\ndef test_pit(tmp_path):\n    path = tmp_path / "Person.pit"\n    path.write_text("[]")',
	'def test_pit(tmp_path):\n    with open(tmp_path / "Person.pit", "w") as stream: stream.write("[]")',
	'def test_pit(tmp_path):\n    (tmp_path / "Person.pit.tmp").write_text("[]")',
	'def test_pit(tmp_path):\n    with (tmp_path / "Person.pit").open("w") as stream: stream.write("[]")',
	'from umgodi import Pit\nfrom tempfile import gettempdir\nPit.open(gettempdir())',
	'from umgodi import Pit\ndef test_pit(tmp_path_factory):\n    Pit.open(tmp_path_factory.mktemp("pit"))',
	'from umgodi import Pit\ndef test_pit(tmp_path):\n    Pit(pit_dir=tmp_path, pit_name="Person")',
	'from umgodi import Pit\ndef test_pit(tmp_path):\n    Pit.open(name_or_path=tmp_path / "Person")',
])
def test_pit_location_guard_rejects_local_temporary_pits(source):
	findings = [finding for finding in analyze(source) if finding.rule == "RAI022"]
	assert len(findings) == 1
	assert findings[0].severity == "Error"


def test_pit_location_guard_allows_test_cloud_directory():
	source = 'from umgodi import Pit\nfrom tempfile import TemporaryDirectory\nwith TemporaryDirectory(dir=cloud_root) as root:\n    Pit.open(root)\n'
	assert analyze(source) == []
	source = 'from pathlib import Path\nfrom tempfile import TemporaryDirectory\nwith TemporaryDirectory(dir=cloud_root) as tmpdir:\n    (Path(tmpdir) / "Person.pit").write_text("[]")\n'
	assert analyze(source) == []


@pytest.mark.parametrize("snippet, expected", [
	("from tempfile import TemporaryDirectory\nfrom umgodi import Pit\nwith TemporaryDirectory() as root:\n    Pit.open(root)", 1),
	("from tempfile import TemporaryDirectory\nfrom umgodi import Pit\nwith TemporaryDirectory(dir=cloud_root) as root:\n    Pit.open(root)", 0),
	("from pathlib import Path\nPath('/tmp/export.json').write_text('{}')", 0),
])
def test_pit_location_guard_checks_literal_python_commands(snippet, expected):
	source = f"import subprocess, sys\nsubprocess.run([sys.executable, '-c', {snippet!r}])"
	findings = [finding for finding in analyze(source) if finding.rule == "RAI022"]
	assert len(findings) == expected


@pytest.mark.parametrize("source", [
	'def test_export(tmp_path):\n    (tmp_path / "Person.json").write_text("[]")',
	'def test_export(tmp_path):\n    with open(tmp_path / "Person.json", "w") as stream: stream.write("[]")',
	'def test_export(tmp_path):\n    main(["export", "Person", "--out-dir", str(tmp_path)])',
	'def test_read(tmp_path):\n    with open(tmp_path / "Person.pit", "r") as stream: stream.read()',
])
def test_pit_location_guard_allows_temporary_exports_and_reads(source):
	assert analyze(source) == []


def test_pit_location_guard_is_a_pylint_error(tmp_path):
	source = tmp_path / "example.py"
	source.write_text('from umgodi import Pit\ndef test_pit(tmp_path):\n    Pit.open(tmp_path / "Person")\n')
	result = subprocess.run(
		[sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all",
		 "--enable=vikela-test-pit-location", "--output-format=json", "--persistent=no", str(source)],
		capture_output=True, text=True,
	)
	assert result.returncode == 2, result.stderr
	finding = json.loads(result.stdout)[0]
	assert finding["symbol"] == "vikela-test-pit-location"
	assert finding["line"] == 3


@pytest.mark.parametrize("source", [
	'from umgodi import Pit\nPit("/cloud/Person", "Person")',
	'from umgodi import Pit\nPit.open("/cloud/Person")',
	'from umgodi import Pit\nPit.open(name_or_path="Person.pit")',
	'from umgodi import Pit\nfrom pathlib import Path as P\nPit(pit_dir=P("/cloud/Person"), pit_name="Person")',
	'from umgodi import Pit\nfrom pathlib import Path\ndef use(path: Path):\n    Pit.open(path)',
	'from umgodi import Pit\nfrom inqaba import InqPath\npath = InqPath("/cloud/Person.pit")\nPit.open(path)',
	'from umgodi import Pit\nfrom inqaba import InqFile\nPit.open(InqFile("/cloud/Person.pit"))',
	'from umgodi import Pit\nfrom inqaba import InqPath\nPit.open(InqPath("/cloud") / "Person")',
])
def test_pit_argument_guard_rejects_non_inqpath_or_filenames(source):
	findings = [f for f in analyze(source) if f.rule == "RAI023"]
	assert len(findings) == 1
	assert findings[0].severity == "Error"


@pytest.mark.parametrize("source", [
	'from umgodi import Pit\nfrom inqaba import InqPath\nPit(InqPath("/cloud/Person"), "Person")',
	'from umgodi import Pit\nfrom inqaba import InqPath\nPit.open(InqPath("/cloud/Person"))',
	'from umgodi import Pit\nfrom inqaba import InqPath, InqRelPath\nPit.open(InqPath("/cloud") / InqRelPath("Person"))',
	'from umgodi import Pit\nname = "Person"\nPit.open(name, cloud="Dropbox", root="Tenant")',
	'from umgodi import Pit\ndef use(value):\n    Pit.open(value)',
	'class Pit:\n    def __init__(self, path): pass\nPit("/unrelated")',
])
def test_pit_argument_guard_allows_directories_cloud_names_and_unknowns(source):
	assert not [f for f in analyze(source) if f.rule == "RAI023"]


def test_pit_argument_guard_is_a_pylint_error(tmp_path):
	source = tmp_path / "example.py"
	source.write_text('from umgodi import Pit\nPit.open("/cloud/Person.pit")\n')
	result = subprocess.run(
		[sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all",
		 "--enable=vikela-pit-directory", "--output-format=json", "--persistent=no", str(source)],
		capture_output=True, text=True,
	)
	assert result.returncode == 2, result.stderr
	finding = json.loads(result.stdout)[0]
	assert finding["symbol"] == "vikela-pit-directory"
	assert finding["line"] == 2


def test_pit_filename_in_system_temp_reports_both_rules_via_pylint(tmp_path):
	source = tmp_path / "example.py"
	source.write_text('from umgodi import Pit\nPit.open("/tmp/Person.pit")\n')
	result = subprocess.run(
		[sys.executable, "-m", "pylint", "--load-plugins=vikela", "--disable=all",
		 "--enable=vikela-test-pit-location,vikela-pit-directory",
		 "--output-format=json", "--persistent=no", str(source)],
		capture_output=True, text=True,
	)
	assert result.returncode == 2, result.stderr
	assert {finding["symbol"] for finding in json.loads(result.stdout)} == {
		"vikela-test-pit-location", "vikela-pit-directory",
	}

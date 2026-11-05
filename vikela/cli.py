"""Standalone, read-only-by-default CLI. No inspected code is imported or run."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import tokenize

from . import __version__
from .analysis import Finding, analyze
from .config import ConfigurationError, disabled_rules
from .style import banner, enabled, help_text, paint


class UsageError(ValueError): pass


class Parser(argparse.ArgumentParser):
	def error(self, message): raise UsageError(message)


def parser():
	p = Parser(prog="vikela", add_help=False)
	p.add_argument("paths", nargs="*")
	p.add_argument("-h", "--help", action="store_true")
	p.add_argument("-v", "--version", action="store_true")
	p.add_argument("-n", "--nologo", action="store_true")
	p.add_argument("--json", action="store_true")
	p.add_argument("--fix", "--qondisa", dest="fix", action="store_true")
	p.add_argument("--config")
	p.add_argument("--disable", action="append", choices=["RAI011", "RAI012"], default=[])
	return p


def sources(path):
	if path.suffix == ".ipynb":
		try:
			notebook = json.loads(path.read_text(encoding="utf-8"))
			if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
				raise UsageError(f"{path}: notebook must contain a cells array")
			# One non-executed source stream retains cross-cell provenance in document order.
			chunks = []; locations = []
			for index, cell in enumerate(notebook["cells"], 1):
				if not isinstance(cell, dict): raise UsageError(f"{path}: malformed cell {index}")
				if cell.get("cell_type") != "code": continue
				text = cell.get("source", "")
				if isinstance(text, list) and all(isinstance(s, str) for s in text): text = "".join(text)
				if not isinstance(text, str): raise UsageError(f"{path}: malformed source in cell {index}")
				for line_number, line in enumerate(text.splitlines(), 1):
					# Ignore IPython commands without executing them; cell bodies remain Python.
					chunks.append("" if line.lstrip().startswith(("%", "!")) else line)
					locations.append((index, line_number))
			yield "\n".join(chunks), locations
		except (json.JSONDecodeError, UnicodeError) as exc: raise UsageError(f"{path}: {exc}") from exc
	else:
		with tokenize.open(path) as stream: yield stream.read(), None


def inspect_paths(paths, disabled=(), config=None):
	files = set()
	for value in paths:
		path = Path(value).expanduser()
		if not path.exists(): raise UsageError(f"Path does not exist: {path}")
		if path.is_dir():
			files.update(p for p in path.rglob("*") if p.suffix in {".py", ".ipynb"} and not any(x in {".git", ".venv", "venv", "__pycache__"} for x in p.parts))
		elif path.suffix in {".py", ".ipynb"}: files.add(path)
		else: raise UsageError(f"Unsupported input type: {path}")
	findings = []
	for path in sorted(files):
		ignored = set(disabled) | disabled_rules(path, config)
		for source, locations in sources(path):
			try: items = analyze(source, str(path.resolve()))
			except SyntaxError as exc:
				cell = f" cell {locations[exc.lineno - 1][0]}" if locations and exc.lineno and exc.lineno <= len(locations) else ""
				raise UsageError(f"{path}{cell}:{exc.lineno}:{exc.offset}: {exc.msg}") from exc
			for item in items:
				if item.rule in ignored: continue
				if locations:
					cell, line = locations[item.line - 1]; item = replace(item, cell=cell, line=line)
				findings.append(item)
	return findings


def render(findings, json_mode=False, nologo=False, fix=False):
	if json_mode:
		print(json.dumps([f.to_dict() for f in findings], ensure_ascii=False, indent=2))
	else:
		color = enabled()
		if not nologo: print(banner(color))
		for finding in findings:
			cell = f" [cell {finding.cell}]" if finding.cell is not None else ""
			print(f"{finding.path}{cell}:{finding.line}:{finding.column}: " + paint(finding.rule, "1;94", color) + " " + finding.reason)
			print("  " + paint("Suggestion: ", "3;35", color) + finding.suggestion)
			print("  " + finding.documentation)
		if not findings: print(paint("✓ No mutation guardrail findings.", "92", color))
	if fix and findings:
		print("No proven safe automatic transformation is available for these findings; source files were left unchanged.", file=sys.stderr)


def main(argv=None):
	json_mode = "--json" in (sys.argv[1:] if argv is None else argv)
	try:
		args = parser().parse_args(argv)
		if args.help: print(help_text()); return 0
		if args.version: print(f"vikela v{__version__}"); return 0
		if not args.paths: raise UsageError("Specify a Python file, notebook or directory; use --help for options.")
		findings = inspect_paths(args.paths, args.disable, args.config)
		render(findings, args.json, args.nologo, args.fix)
		return 1 if findings else 0
	except (UsageError, ConfigurationError, SyntaxError, UnicodeError) as exc:
		if json_mode: print("[]")
		print(f"vikela: {exc}", file=sys.stderr); return 2
	except Exception as exc:
		if json_mode: print("[]")
		print(f"vikela: {type(exc).__name__}: {exc}", file=sys.stderr); return 4

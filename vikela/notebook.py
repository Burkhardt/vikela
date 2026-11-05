"""IPython extension: %%vikela checks a cell, but never executes its contents."""
import shlex
from .analysis import analyze
from .cli import parser, render, UsageError


def cell_magic(line, cell):
	args = parser().parse_args(shlex.split(line))
	if args.paths: raise UsageError("%%vikela accepts options, not file paths")
	findings = [f for f in analyze(cell, "<vikela-cell>") if f.rule not in args.disable]
	render(findings, args.json, nologo=True, fix=args.fix)

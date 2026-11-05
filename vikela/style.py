"""CR077 terminal rendering, based on RAIkeep's shared cli-style contract."""
from __future__ import annotations
import os
import platform
import re
import sys
import unicodedata
from . import __version__

_SWITCH = re.compile(r"(?<![\w/\-])--?[A-Za-z][A-Za-z0-9-]*")


def enabled(stream=None):
	stream = sys.stdout if stream is None else stream
	return stream.isatty() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"


def paint(text, color, enabled):
	return f"\033[{color}m{text}\033[0m" if enabled else text


def syntax(text: str, base_color: str = "36", enabled: bool = True) -> str:
	if not enabled or not text:
		return text
	colors = [base_color] * len(text)
	italic = [False] * len(text)
	groups: list[tuple[int, int, str, bool]] = []
	opened: list[tuple[int, str]] = []
	quote = -1
	for i, ch in enumerate(text):
		if ch == "'":
			if quote < 0:
				quote = i
			else:
				colors[quote + 1:i] = ["33"] * (i - quote - 1)
				quote = -1
		if ch in "<([":
			opened.append((i, ch))
		elif ch in ">)]":
			expected = {">": "<", ")": "(", "]": "["}[ch]
			if opened and opened[-1][1] == expected:
				start, kind = opened.pop()
				depth = 0
				choice = False
				if kind == "(":
					for inner in text[start + 1:i]:
						if inner in "<([": depth += 1
						elif inner in ">)]": depth -= 1
						elif inner == "|" and depth == 0: choice = True
				groups.append((start, i, kind, choice))
	for start, end, kind, choice in sorted(groups, key=lambda g: g[1] - g[0], reverse=True):
		if kind == "<":
			in_choice = any(c and a < start and b > end for a, b, _, c in groups)
			colors[start + 1:end] = ["35" if in_choice else "96"] * (end - start - 1)
			italic[start + 1:end] = [True] * (end - start - 1)
		elif kind == "[" or choice:
			colors[start:end + 1] = ["35" if choice else "94"] * (end - start + 1)
	for i, ch in enumerate(text):
		if ch in "<>|":
			colors[i], italic[i] = base_color, False
	for match in _SWITCH.finditer(text):
		colors[match.start():match.end()] = ["32"] * len(match.group())
	result: list[str] = []
	start = 0
	while start < len(text):
		end = start + 1
		while end < len(text) and colors[end] == colors[start] and italic[end] == italic[start]: end += 1
		result.append(paint(text[start:end], colors[start] + (";3" if italic[start] else ""), True))
		start = end
	return "".join(result)



def width(text):
	cells = 0; previous = 0
	for character in text:
		if character == "\ufe0f":
			# Emoji presentation widens a text-default symbol such as the shield.
			if previous == 1: cells += 1
			continue
		if unicodedata.combining(character) or character == "\u200d": continue
		previous = 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
		cells += previous
	return cells


def banner(color):
	heading = f"🛡️ Vikela Python Mutation Guardrails (vikela v{__version__}) on {platform.node()}"
	rule = " " + "─" * max(0, width(heading) - 2)
	return "\n".join([paint(rule, "36", color), paint(heading, "1;36", color), paint(rule, "36", color)])


def help_text():
	color = enabled()
	rows = [
		("-h, --help", "", "32", "print options and examples"),
		("-v, --version", "", "36", "print version information"),
		("-n, --nologo", "", "95", "do not display the banner"),
		("--json", "", "38;5;117", "write pure JSON findings to stdout"),
		("--fix, --qondisa", "", "38;5;208", "apply only proven safe fixes; unavailable fixes remain suggestions"),
		("--config <file>", "", "35", "read shared [tool.vikela] project configuration"),
		("--disable <rule>", "🛡️", "38;5;75", "disable RAI011 or RAI012 (repeatable)"),
	]
	result = [banner(color), syntax("Usage: vikela <file.py|notebook.ipynb|directory> [--json] [--fix|--qondisa]", enabled=color), ""]
	label_width = max(len(row[0]) for row in rows)
	for label, glyph, base, description in rows:
		result.append(syntax(label.ljust(label_width), base, color) + "  " + paint(glyph, base, color) + " " * (4 - width(glyph)) + syntax(description, base, color))
	result.extend(["", "Exit codes: 0 clean, 1 findings, 2 syntax/configuration, 4 internal/environment failure.",
		"Checks never execute the inspected code. JSON and notebook checks never add a banner."])
	return "\n".join(result)

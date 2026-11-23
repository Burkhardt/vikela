"""Identify Pit writes using recognizable local temporary paths."""
from __future__ import annotations

import ast
import re


_PIT_FACTORIES = {
	"umgodi.Pit", "umgodi.store.Pit", "jsonpit.Pit", "jsonpit.store.Pit",
	"umgodi.Pit.open", "umgodi.store.Pit.open", "jsonpit.Pit.open", "jsonpit.store.Pit.open",
}


def _name(node: ast.AST) -> str:
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		base = _name(node.value)
		return f"{base}.{node.attr}" if base else ""
	return ""


class PitLocationGuard(ast.NodeVisitor):
	def __init__(self) -> None:
		self.aliases: dict[str, str] = {}
		self.temporary = {"tmp_path", "tmpdir"}
		self.pit_paths: set[str] = set()
		self.issues: list[tuple[ast.AST, str]] = []

	def qualified(self, node: ast.AST) -> str:
		name = _name(node)
		head, separator, tail = name.partition(".")
		return self.aliases.get(head, head) + (separator + tail if separator else "")

	def is_temporary(self, node: ast.AST) -> bool:
		if isinstance(node, ast.Name):
			return node.id in self.temporary
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			return node.value == "/tmp" or node.value.startswith(("/tmp/", "/var/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/"))
		if isinstance(node, ast.Call) and self.qualified(node.func) in {
			"tempfile.mkdtemp", "tempfile.TemporaryDirectory", "tempfile.NamedTemporaryFile", "tempfile.gettempdir",
		}:
			directory = next((keyword.value for keyword in node.keywords if keyword.arg == "dir"), None)
			if directory is None and len(node.args) >= 3:
				directory = node.args[2]
			return directory is None or self.is_temporary(directory)
		if isinstance(node, ast.Call) and self.qualified(node.func) in {"tmp_path_factory.mktemp", "tmpdir_factory.mktemp"}:
			return True
		return any(self.is_temporary(child) for child in ast.iter_child_nodes(node))

	def is_pit_path(self, node: ast.AST) -> bool:
		return any(
			isinstance(part, ast.Constant) and isinstance(part.value, str) and part.value.lower().endswith((".pit", ".pit.tmp"))
			or isinstance(part, ast.Name) and part.id in self.pit_paths
			for part in ast.walk(node)
		)

	def visit_Import(self, node: ast.Import) -> None:
		for alias in node.names:
			self.aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]

	def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
		for alias in node.names:
			self.aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

	def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
		previous = self.temporary.copy()
		previous_pits = self.pit_paths.copy()
		self.generic_visit(node)
		self.temporary = previous
		self.pit_paths = previous_pits

	visit_AsyncFunctionDef = visit_FunctionDef

	def visit_Assign(self, node: ast.Assign) -> None:
		if self.is_temporary(node.value):
			for target in node.targets:
				if isinstance(target, ast.Name):
					self.temporary.add(target.id)
					if self.is_pit_path(node.value):
						self.pit_paths.add(target.id)
		self.generic_visit(node)

	def visit_With(self, node: ast.With | ast.AsyncWith) -> None:
		for item in node.items:
			if item.optional_vars and isinstance(item.optional_vars, ast.Name):
				if self.is_temporary(item.context_expr):
					self.temporary.add(item.optional_vars.id)
				elif isinstance(item.context_expr, ast.Call) and self.qualified(item.context_expr.func) == "tempfile.TemporaryDirectory":
					self.temporary.discard(item.optional_vars.id)
		self.generic_visit(node)

	visit_AsyncWith = visit_With

	def visit_Call(self, node: ast.Call) -> None:
		if self.qualified(node.func) in {"subprocess.run", "subprocess.Popen", "subprocess.check_call", "subprocess.check_output"} and node.args:
			command = node.args[0]
			if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
				executable = command.elts[0]
				name = executable.value if isinstance(executable, ast.Constant) and isinstance(executable.value, str) else _name(executable)
				if re.search(r"(?:^|[/\\])python(?:\d+(?:\.\d+)*)?(?:\.exe)?$", name) or name == "sys.executable":
					for index, argument in enumerate(command.elts[:-1]):
						if isinstance(argument, ast.Constant) and argument.value == "-c":
							source = command.elts[index + 1]
							if isinstance(source, ast.Constant) and isinstance(source.value, str):
								try:
									tree = ast.parse(source.value)
								except SyntaxError:
									break
								for _, message in pit_location_findings(tree):
									self.issues.append((node, f"Python -c: {message}"))
							break
		if self.qualified(node.func) in _PIT_FACTORIES:
			path = node.args[0] if node.args else next(
				(keyword.value for keyword in node.keywords if keyword.arg in {"pit_dir", "name_or_path"}), None,
			)
			if path is not None and self.is_temporary(path):
				self.issues.append((node, "Opens a Pit using a local temporary path instead of the configured TestCloud."))
		if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes", "touch"}:
			target = node.func.value
			if self.is_pit_path(target) and self.is_temporary(target):
				self.issues.append((node, "Writes a Pit file using a local temporary path instead of the configured TestCloud."))
		if self.qualified(node.func) in {"open", "io.open"} and node.args:
			target = node.args[0]
			mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
			if self.is_pit_path(target) and self.is_temporary(target) and self.is_write_mode(mode):
				self.issues.append((node, "Writes a Pit file using a local temporary path instead of the configured TestCloud."))
		elif isinstance(node.func, ast.Attribute) and node.func.attr == "open":
			target = node.func.value
			mode = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "mode"), None)
			if self.is_pit_path(target) and self.is_temporary(target) and self.is_write_mode(mode):
				self.issues.append((node, "Writes a Pit file using a local temporary path instead of the configured TestCloud."))
		self.generic_visit(node)

	@staticmethod
	def is_write_mode(node: ast.AST | None) -> bool:
		return isinstance(node, ast.Constant) and isinstance(node.value, str) and any(flag in node.value for flag in "wax+")


def pit_location_findings(tree: ast.AST) -> list[tuple[ast.AST, str]]:
	guard = PitLocationGuard()
	guard.visit(tree)
	return guard.issues

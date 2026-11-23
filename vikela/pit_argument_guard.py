"""Find recognizable non-InqPath arguments to Python Pit constructors."""
from __future__ import annotations

import ast


def _name(node: ast.AST) -> str:
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		base = _name(node.value)
		return f"{base}.{node.attr}" if base else ""
	return ""


class PitArgumentGuard(ast.NodeVisitor):
	def __init__(self) -> None:
		self.aliases: dict[str, str] = {}
		self.values: dict[str, str] = {}
		self.issues: list[tuple[ast.AST, str]] = []

	def qualified(self, node: ast.AST) -> str:
		name = _name(node)
		head, separator, tail = name.partition(".")
		if head in self.values:
			return ""
		return self.aliases.get(head, head) + (separator + tail if separator else "")

	def kind(self, node: ast.AST) -> str:
		if isinstance(node, ast.Name):
			return self.values.get(node.id, "")
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			value = node.value
			return "bare-name" if value and not any(char in value for char in "/\\") \
				and not value.startswith((".", "~")) and not value.lower().endswith(".pit") else "string"
		if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
			kind = self.kind(node.left)
			if kind == "inqpath" and isinstance(node.op, ast.Div):
				if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
					return "non-directory"
				if isinstance(node.right, ast.Call) and self.qualified(node.right.func) in {"inqaba.InqRelPath", "inqaba.path.InqRelPath"}:
					return "inqpath"
				return ""
			return "string" if kind == "bare-name" else kind
		if isinstance(node, ast.Call):
			name = self.qualified(node.func)
			if name in {"pathlib.Path", "pathlib.PurePath", "pathlib.PosixPath", "pathlib.WindowsPath",
					"inqaba.InqEntry", "inqaba.InqFile", "inqaba.files.InqFile"}:
				return "non-directory"
			if name in {"inqaba.InqPath", "inqaba.path.InqPath", "inqaba.InqPath.from_directory",
					"inqaba.path.InqPath.from_directory"}:
				return "pit-file" if self.has_pit_filename(node) else "inqpath"
			if name in {"tempfile.mkdtemp", "tempfile.gettempdir"}:
				return "string"
		return ""

	def has_pit_filename(self, node: ast.AST) -> bool:
		return any(isinstance(child, ast.Constant) and isinstance(child.value, str)
			and child.value.lower().rstrip("/\\").endswith(".pit") for child in ast.walk(node))

	def visit_Import(self, node: ast.Import) -> None:
		for alias in node.names:
			name = alias.asname or alias.name.split(".")[0]
			self.values.pop(name, None)
			self.aliases[name] = alias.name if alias.asname else alias.name.split(".")[0]

	def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
		for alias in node.names:
			name = alias.asname or alias.name
			self.values.pop(name, None)
			self.aliases[name] = f"{node.module}.{alias.name}"

	def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
		old_values, old_aliases = self.values.copy(), self.aliases.copy()
		for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
			if argument.annotation:
				annotation = self.qualified(argument.annotation)
				if annotation in {"pathlib.Path", "pathlib.PurePath", "inqaba.InqEntry", "inqaba.InqFile"}:
					self.values[argument.arg] = "non-directory"
				elif annotation in {"inqaba.InqPath", "inqaba.path.InqPath"}:
					self.values[argument.arg] = "inqpath"
			self.aliases.pop(argument.arg, None)
		for statement in node.body:
			self.visit(statement)
		self.values, self.aliases = old_values, old_aliases

	visit_AsyncFunctionDef = visit_FunctionDef

	def visit_Assign(self, node: ast.Assign) -> None:
		self.visit(node.value)
		kind = self.kind(node.value)
		for target in node.targets:
			if isinstance(target, ast.Name):
				self.aliases.pop(target.id, None)
				self.values[target.id] = kind

	def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
		if node.value:
			self.visit(node.value)
		if isinstance(node.target, ast.Name):
			kind = self.kind(node.value) if node.value else ""
			if not kind and node.annotation:
				annotation = self.qualified(node.annotation)
				if annotation in {"pathlib.Path", "pathlib.PurePath", "inqaba.InqEntry", "inqaba.InqFile"}:
					kind = "non-directory"
				elif annotation in {"inqaba.InqPath", "inqaba.path.InqPath"}:
					kind = "inqpath"
			self.aliases.pop(node.target.id, None)
			self.values[node.target.id] = kind

	def visit_Call(self, node: ast.Call) -> None:
		name = self.qualified(node.func)
		pit_types = {"umgodi.Pit", "umgodi.store.Pit", "jsonpit.Pit", "jsonpit.store.Pit"}
		is_factory = name in {f"{pit}.open" for pit in pit_types}
		if name in pit_types or is_factory:
			argument = node.args[0] if node.args else next(
				(keyword.value for keyword in node.keywords
					if keyword.arg == ("name_or_path" if is_factory else "pit_dir")), None)
			if argument is not None:
				kind = self.kind(argument)
				if kind == "pit-file" or self.has_pit_filename(argument):
					self.issues.append((argument, "A Pit must be opened from a directory, not a .pit filename."))
				elif kind in {"non-directory", "string"} or kind == "bare-name" and not is_factory:
					self.issues.append((argument, "Use an InqPath directory for an explicit Pit path."))
		self.generic_visit(node)


def pit_argument_findings(tree: ast.AST) -> list[tuple[ast.AST, str]]:
	guard = PitArgumentGuard()
	guard.visit(tree)
	return guard.issues

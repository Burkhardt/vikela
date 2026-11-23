"""Recognize direct substitutions of the RAIkeep test configuration."""
from __future__ import annotations

import ast

_ENVIRONMENT_KEYS = {"HOME", "USERPROFILE", "RAIKEEP_CONFIG", "JSONPIT_CONFIG", "ONEDRIVE"}
_CONFIG_TYPES = {"InqConfig", "OsConfig"}
_CONFIG_MEMBERS = {"load", "find_config_file", "_instance", "default_cloud_order", "test_cloud"}
_CONFIG_FIELDS = {"Cloud", "TestCloud", "DefaultCloudOrder"}

def _name(node: ast.AST) -> str:
	if isinstance(node, ast.Name):
		return node.id
	if isinstance(node, ast.Attribute):
		base = _name(node.value)
		return f"{base}.{node.attr}" if base else ""
	return ""

def _string(node: ast.AST | None) -> str | None:
	return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

class ConfigurationGuard(ast.NodeVisitor):
	def __init__(self) -> None:
		self.aliases: dict[str, str] = {}
		self.config_paths: set[str] = set()
		self.config_values: set[str] = set()
		self.issues: list[tuple[ast.AST, str]] = []

	def qualified(self, node: ast.AST) -> str:
		name = _name(node)
		head, separator, tail = name.partition(".")
		return self.aliases.get(head, head) + (separator + tail if separator else "")

	def is_config_path(self, node: ast.AST) -> bool:
		return any(
			(_string(part) or "").lower().endswith("raikeep.json5")
			or isinstance(part, ast.Name) and part.id in self.config_paths
			for part in ast.walk(node)
		)

	def config_type(self, node: ast.AST) -> bool:
		return self.qualified(node).split(".")[-1] in _CONFIG_TYPES

	def config_value(self, node: ast.AST) -> bool:
		if isinstance(node, ast.Name):
			return node.id in self.config_values
		if isinstance(node, (ast.Attribute, ast.Subscript)):
			return self.config_value(node.value)
		return isinstance(node, ast.Call) and (
			self.config_type(node.func)
			or isinstance(node.func, ast.Attribute)
			and node.func.attr == "load" and self.config_type(node.func.value)
		)

	def visit_Import(self, node: ast.Import) -> None:
		for alias in node.names:
			self.aliases[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]

	def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
		for alias in node.names:
			self.aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

	def check_target(self, target: ast.AST) -> None:
		if isinstance(target, ast.Subscript):
			key = _string(target.slice)
			base = _name(target.value)
			if key and key.upper() in _ENVIRONMENT_KEYS and (base.endswith("environ") or base in {"env", "environment"}):
				self.issues.append((target, f"Overrides configuration-related environment variable {key}."))
			elif self.config_value(target.value):
				self.issues.append((target, "Changes a loaded RAIkeep configuration mapping."))
		elif isinstance(target, ast.Attribute):
			if self.config_value(target.value) or target.attr in _CONFIG_MEMBERS and self.config_type(target.value):
				self.issues.append((target, f"Overrides RAIkeep configuration member {target.attr}."))

	def visit_Assign(self, node: ast.Assign) -> None:
		for target in node.targets:
			self.check_target(target)
			if isinstance(target, ast.Name):
				if self.is_config_path(node.value):
					self.config_paths.add(target.id)
				if self.config_value(node.value):
					self.config_values.add(target.id)
		self.generic_visit(node)

	def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
		self.check_target(node.target)
		if isinstance(node.target, ast.Name) and node.value is not None:
			if self.is_config_path(node.value):
				self.config_paths.add(node.target.id)
			if self.config_value(node.value):
				self.config_values.add(node.target.id)
		self.generic_visit(node)

	def visit_Delete(self, node: ast.Delete) -> None:
		for target in node.targets:
			self.check_target(target)
		self.generic_visit(node)

	def visit_Call(self, node: ast.Call) -> None:
		name = self.qualified(node.func)
		method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
		if self.config_type(node.func) and node.args and isinstance(node.args[0], ast.Dict):
			if any(_string(key) in _CONFIG_FIELDS for key in node.args[0].keys if key):
				self.issues.append((node, "Constructs a substitute RAIkeep cloud configuration."))
		if method in {"setenv", "delenv", "putenv", "unsetenv"} and node.args:
			key = _string(node.args[0])
			if key and key.upper() in _ENVIRONMENT_KEYS:
				self.issues.append((node, f"Overrides configuration-related environment variable {key}."))
		if method in {"setitem", "delitem"} and len(node.args) >= 2:
			key = _string(node.args[1])
			if key and key.upper() in _ENVIRONMENT_KEYS and self.qualified(node.args[0]).endswith("environ"):
				self.issues.append((node, f"Overrides configuration-related environment variable {key}."))
			elif self.config_value(node.args[0]):
				self.issues.append((node, "Changes a loaded RAIkeep configuration mapping."))
		if method == "update" and isinstance(node.func, ast.Attribute):
			if self.config_value(node.func.value):
				self.issues.append((node, "Changes a loaded RAIkeep configuration mapping."))
			elif self.qualified(node.func.value).endswith("environ"):
				keys = node.args[0] if node.args else None
				if any((keyword.arg or "").upper() in _ENVIRONMENT_KEYS for keyword in node.keywords) or (
					isinstance(keys, ast.Dict) and any((_string(key) or "").upper() in _ENVIRONMENT_KEYS for key in keys.keys if key)
				):
					self.issues.append((node, "Substitutes configuration-related environment variables."))
		if method in {"setattr", "object"} and len(node.args) >= 2:
			member = _string(node.args[1])
			if member in _CONFIG_MEMBERS and (self.config_type(node.args[0]) or self.config_value(node.args[0])):
				self.issues.append((node, f"Overrides RAIkeep configuration member {member}."))
		if method == "setattr" and node.args:
			target = _string(node.args[0])
			if target and any(target.endswith(f".{member}") for member in _CONFIG_MEMBERS) and any(t in target for t in _CONFIG_TYPES):
				self.issues.append((node, "Mocks a RAIkeep configuration loader or mapping."))
		if name.endswith("patch") and node.args:
			target = _string(node.args[0])
			if target and any(target.endswith(f".{member}") for member in _CONFIG_MEMBERS) and any(t in target for t in _CONFIG_TYPES):
				self.issues.append((node, "Mocks a RAIkeep configuration loader or mapping."))
		if method == "dict" and node.args and self.qualified(node.args[0]).endswith("environ"):
			keys = node.args[1] if len(node.args) > 1 else None
			if any(keyword.arg == "clear" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True for keyword in node.keywords) or (
				isinstance(keys, ast.Dict) and any((_string(key) or "").upper() in _ENVIRONMENT_KEYS for key in keys.keys if key)
			):
				self.issues.append((node, "Substitutes configuration-related environment variables."))
		if method in {"write_text", "write_bytes", "unlink"} and isinstance(node.func, ast.Attribute) and self.is_config_path(node.func.value):
			self.issues.append((node, "Writes or removes a RAIkeep configuration file."))
		if method == "open" and isinstance(node.func, ast.Attribute) and self.is_config_path(node.func.value):
			mode = _string(node.args[0]) if node.args else next((_string(k.value) for k in node.keywords if k.arg == "mode"), None)
			if mode and any(flag in mode for flag in "wax+"):
				self.issues.append((node, "Opens a RAIkeep configuration file for writing."))
		if name in {"open", "io.open"} and node.args and self.is_config_path(node.args[0]):
			mode = _string(node.args[1]) if len(node.args) > 1 else next((_string(k.value) for k in node.keywords if k.arg == "mode"), None)
			if mode and any(flag in mode for flag in "wax+"):
				self.issues.append((node, "Opens a RAIkeep configuration file for writing."))
		self.generic_visit(node)

def configuration_findings(tree: ast.AST) -> list[tuple[ast.AST, str]]:
	guard = ConfigurationGuard()
	guard.visit(tree)
	return guard.issues

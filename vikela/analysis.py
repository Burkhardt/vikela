"""Conservative, non-executing JsonPit provenance analysis (CR077).

Only resolved JsonPit imports/annotations and propagated values establish types.
Unknown calls are not assumed to return a fresh or detached item. Branch joins
retain facts only when all continuing paths agree. Loops join zero/one iteration;
this is bounded analysis, not a proof about arbitrary Python execution.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, replace
from typing import Iterable

DOCS = "https://github.com/Burkhardt/vikela/blob/main/docs/rules.md"
PROTECTED = {"id", "modified", "deleted"}


@dataclass(frozen=True)
class Finding:
	rule: str
	severity: str
	path: str
	line: int
	column: int
	reason: str
	suggestion: str
	documentation: str
	cell: int | None = None
	fix_available: bool = False

	def to_dict(self):
		return asdict(self)


@dataclass(frozen=True)
class Value:
	kind: str = "unknown"
	owner: str | None = None
	key: str | None = None
	fields: frozenset[str] = frozenset()
	element: Value | None = None


UNKNOWN = Value()
ITEM_KINDS = {"live", "detached", "fresh", "item"}


def path_name(node):
	if isinstance(node, ast.Name): return node.id
	if isinstance(node, ast.Attribute):
		base = path_name(node.value)
		return base + "." + node.attr if base else ""
	return ""


def literal(node):
	return str(node.value) if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def join_values(values):
	values = list(values)
	return values[0] if values and all(v == values[0] for v in values) else UNKNOWN


class Analyzer:
	def __init__(self, source: str, path: str = "<source>"):
		self.tree = ast.parse(source, filename=path)
		self.path = path
		self.findings: list[Finding] = []
		self.imports: dict[str, str] = {}
		self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
		self.invalid: set[tuple[str | None, str | None]] = set()
		self.depth = 0
		self._seen = set()
		self.scope = "module"

	def qualified(self, node, env):
		name = path_name(node)
		head, _, tail = name.partition(".")
		if head in env: return ""
		return self.imports.get(head, head) + ("." + tail if tail else "")

	def annotated(self, node, env, identity):
		if isinstance(node, ast.Constant) and isinstance(node.value, str):
			try: node = ast.parse(node.value, mode="eval").body
			except SyntaxError: return UNKNOWN
		name = self.qualified(node, env)
		if name in {"jsonpit.Pit", "jsonpit.store.Pit"}: return Value("pit", identity)
		if name in {"jsonpit.PitItem", "jsonpit.item.PitItem"}: return Value("item")
		if isinstance(node, ast.Subscript):
			element = self.annotated(node.slice, env, identity)
			if self.qualified(node.value, env) in {"list", "set", "tuple", "typing.List", "typing.Sequence", "typing.Iterable"}:
				return Value("collection", element=element)
		return UNKNOWN

	def emit(self, rule, node, reason):
		key = (rule, node.lineno, node.col_offset, reason)
		if key in self._seen: return
		self._seen.add(key)
		suggestion = (
			"Update the same-owner live item through indexing or set_property; create a fresh PitItem containing only the intended fields for an explicit delta. Historical replay is not a client-write workaround."
			if rule == "RAI011" else
			"Let JsonPit manage Id, Modified and Deleted. Use rename_id or delete_item for lifecycle changes; update business properties through the live item."
		)
		self.findings.append(Finding(rule, "Warning", self.path, node.lineno, node.col_offset + 1,
			reason, suggestion, DOCS + "#" + rule.lower()))

	def payload_fields(self, node, env):
		if isinstance(node, ast.Dict):
			fields = set()
			for key, value in zip(node.keys, node.values):
				if key is None: fields.update(self.value(value, env).fields)
				elif literal(key) is not None: fields.add(literal(key))
			return frozenset(fields)
		return self.value(node, env).fields

	def payload_check(self, node, receiver, payload, env):
		for field in self.payload_fields(payload, env):
			if field.lower() in {"modified", "deleted"}:
				self.emit("RAI012", node, f"Client mutation includes protected lifecycle attribute '{field}'.")
			elif field.lower() == "id" and isinstance(payload, ast.Dict):
				for key, val in zip(payload.keys, payload.values):
					if literal(key) == field and literal(val) is not None and receiver.key is not None and literal(val) != receiver.key:
						self.emit("RAI012", node, "Client mutation changes the item's immutable Id.")

	def value(self, node, env):
		if node is None: return UNKNOWN
		name = path_name(node)
		if name and name in env: return env[name]
		if isinstance(node, ast.NamedExpr):
			value = self.value(node.value, env); self.bind(node.target, value, env); return value
		if isinstance(node, ast.Subscript):
			base = self.value(node.value, env)
			if base.kind == "pit": return Value("live", base.owner, literal(node.slice))
			if base.kind == "collection": return base.element or UNKNOWN
		if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
			return Value("collection", element=join_values(self.value(e, env) for e in node.elts) if node.elts else None)
		if isinstance(node, ast.Dict): return Value("payload", fields=self.payload_fields(node, env))
		if isinstance(node, ast.IfExp):
			self.value(node.test, env)
			return join_values([self.value(node.body, dict(env)), self.value(node.orelse, dict(env))])
		if isinstance(node, ast.BoolOp): return join_values(self.value(v, env) for v in node.values)
		if isinstance(node, ast.Call): return self.call(node, env)
		if isinstance(node, ast.Await): return self.value(node.value, env)
		return UNKNOWN

	def call(self, node, env):
		qualified = self.qualified(node.func, env)
		args = [self.value(arg, env) for arg in node.args]
		if qualified in {"jsonpit.Pit", "jsonpit.store.Pit"}:
			return Value("pit", f"allocation:{self.scope}:{node.lineno}:{node.col_offset}")
		if qualified in {"jsonpit.PitItem", "jsonpit.item.PitItem"}:
			first = args[0] if args else UNKNOWN
			key = literal(node.args[0]) if node.args else None
			key = next((literal(k.value) for k in node.keywords if k.arg == "id"), key)
			if first.kind in {"live", "detached"}: return replace(first, kind="detached")
			if first.fields & {"Modified", "Deleted", "modified", "deleted"}:
				return Value("detached", fields=first.fields)
			return Value("fresh", key=key, fields=first.fields)
		if qualified == "typing.cast" and len(args) == 2: return args[1]
		if qualified in {"dict", "copy.copy", "copy.deepcopy"} and args:
			return replace(args[0], kind="detached") if args[0].kind in ITEM_KINDS else args[0]
		if isinstance(node.func, ast.Attribute):
			receiver = self.value(node.func.value, env)
			method = node.func.attr
			if receiver.kind == "pit":
				if method in {"get", "get_at"}:
					explicit_none = any(k.arg == "at" and isinstance(k.value, ast.Constant) and k.value.value is None for k in node.keywords) or (method == "get_at" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and node.args[1].value is None)
					detached = method == "get_at" and not explicit_none or any(k.arg == "at" and not (isinstance(k.value, ast.Constant) and k.value.value is None) for k in node.keywords)
					return Value("detached" if detached else "live", receiver.owner, literal(node.args[0]) if node.args else None)
				if method == "add" and args:
					value = args[0]
					if value.kind == "detached": self.emit("RAI011", node, "A detached full projection is being submitted as a live write; it can replay unrelated fields and engine lifecycle metadata.")
					elif value.kind == "live":
						if (value.owner, value.key) in self.invalid or (value.owner, "*") in self.invalid:
							self.emit("RAI011", node, "The live handle belongs to a deleted item or disposed Pit lifetime.")
						elif value.owner != receiver.owner and all((o or "").startswith("allocation:") for o in [value.owner, receiver.owner]):
							self.emit("RAI011", node, "The live handle belongs to a different Pit instance.")
					if value.kind == "fresh":
						# A first Add adopts the original item; subsequent aliases share it.
						for name, old in list(env.items()):
							if old is value: env[name] = Value("live", receiver.owner, old.key)
				if method == "delete_item" and node.args and literal(node.args[0]) is not None:
					self.invalid.add((receiver.owner, literal(node.args[0])))
				if method in {"close", "dispose"}: self.invalid.add((receiver.owner, "*"))
			elif receiver.kind in ITEM_KINDS:
				if method in {"to_dict", "clone", "copy", "__copy__", "__deepcopy__"}: return replace(receiver, kind="detached")
				if method in {"extend_with", "set_property", "merge"} and node.args:
					self.payload_check(node, receiver, node.args[0], env)
				if method in {"delete_property", "delete_property_path", "pop", "__delitem__"} and node.args:
					field = literal(node.args[0])
					if field and field.split(".")[0].lower() in PROTECTED:
						self.emit("RAI012", node, f"Cannot delete protected lifecycle attribute '{field}'.")
			elif receiver.kind == "collection" and method in {"append", "add", "extend"} and args:
				name = path_name(node.func.value)
				new = args[0].element if method == "extend" else args[0]
				old = receiver.element
				combined = new if old is None else join_values([old, new or UNKNOWN])
				for alias, value in list(env.items()):
					if value is receiver: env[alias] = replace(receiver, element=combined)
		function = self.functions.get(path_name(node.func))
		if function is not None and self.depth < 4:
			local = dict(env)
			for param, val in zip(function.args.args, args): local[param.arg] = val
			self.depth += 1
			invalid = set(self.invalid)
			try:
				returns, _ = self.block(function.body, local)
				assigned = {path_name(target) for statement in ast.walk(function) if isinstance(statement, ast.Assign) for target in statement.targets}
				for param, original in zip(function.args.args, args):
					current = local.get(param.arg, UNKNOWN)
					if param.arg not in assigned and (original.kind == "collection" or original.kind == "fresh" and current.kind == "live"):
						for name, value in list(env.items()):
							if value is original: env[name] = current
				return join_values(returns)
			finally: self.invalid = invalid; self.depth -= 1
		return UNKNOWN

	def bind(self, target, value, env):
		name = path_name(target)
		if name: env[name] = value
		elif isinstance(target, (ast.Tuple, ast.List)):
			for element in target.elts: self.bind(element, UNKNOWN, env)

	def assignment(self, target, value, env):
		if isinstance(target, (ast.Subscript, ast.Attribute)):
			base = self.value(target.value, env)
			field = literal(target.slice) if isinstance(target, ast.Subscript) else target.attr
			if base.kind in ITEM_KINDS and field and field.lower() in PROTECTED:
				self.emit("RAI012", target, f"Direct assignment changes protected lifecycle attribute '{field}'.")
		self.bind(target, value, env)

	def merge_env(self, target, branches):
		for key in set().union(*(b.keys() for b in branches)):
			target[key] = join_values(b.get(key, UNKNOWN) for b in branches)

	def block(self, statements, env):
		returns = []
		for statement in statements:
			if isinstance(statement, ast.Import):
				for alias in statement.names:
					name = alias.asname or alias.name.split(".")[0]; env.pop(name, None)
					self.imports[name] = alias.name if alias.asname else alias.name.split(".")[0]
			elif isinstance(statement, ast.ImportFrom):
				for alias in statement.names:
					name = alias.asname or alias.name; env.pop(name, None)
					self.imports[name] = (statement.module or "") + "." + alias.name
			elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
				self.functions[statement.name] = statement
				env[statement.name] = UNKNOWN
			elif isinstance(statement, ast.ClassDef):
				env[statement.name] = UNKNOWN
				local = dict(env)
				for member in statement.body:
					if isinstance(member, ast.AnnAssign):
						name = path_name(member.target)
						local["self." + name] = self.value(member.value, local) if member.value else self.annotated(member.annotation, local, "field:" + statement.name + "." + name)
				self.analyze_functions(statement.body, local)
			elif isinstance(statement, ast.Assign):
				value = self.value(statement.value, env)
				for target in statement.targets: self.assignment(target, value, env)
			elif isinstance(statement, ast.AnnAssign):
				value = self.value(statement.value, env) if statement.value else self.annotated(statement.annotation, env, "annotation:" + self.scope + ":" + path_name(statement.target))
				self.assignment(statement.target, value, env)
			elif isinstance(statement, ast.AugAssign):
				self.value(statement.value, env); self.assignment(statement.target, UNKNOWN, env)
			elif isinstance(statement, ast.Expr): self.value(statement.value, env)
			elif isinstance(statement, ast.Return):
				returns.append(self.value(statement.value, env)); return returns, True
			elif isinstance(statement, ast.Raise): self.value(statement.exc, env); return returns, True
			elif isinstance(statement, ast.If):
				self.value(statement.test, env)
				branches = []; before = set(self.invalid); invalids = []
				for body in [statement.body, statement.orelse]:
					local = dict(env); self.invalid = set(before)
					values, stopped = self.block(body, local); returns.extend(values)
					if not stopped: branches.append(local); invalids.append(set(self.invalid))
				self.invalid = set.intersection(*invalids) if invalids else before
				if not branches: return returns, True
				self.merge_env(env, branches)
			elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
				local = dict(env); before = set(self.invalid)
				if isinstance(statement, (ast.For, ast.AsyncFor)):
					iterable = self.value(statement.iter, env); self.bind(statement.target, iterable.element or UNKNOWN, local)
				self.block(statement.body, local)
				self.invalid = before; self.merge_env(env, [env.copy(), local])
				self.block(statement.orelse, env)
			elif isinstance(statement, (ast.With, ast.AsyncWith)):
				for item in statement.items:
					value = self.value(item.context_expr, env)
					if item.optional_vars: self.bind(item.optional_vars, value, env)
				values, stopped = self.block(statement.body, env); returns.extend(values)
				if stopped: return returns, True
			elif isinstance(statement, ast.Delete):
				for target in statement.targets:
					if isinstance(target, ast.Subscript):
						base = self.value(target.value, env); field = literal(target.slice)
						if base.kind in ITEM_KINDS and field and field.lower() in PROTECTED: self.emit("RAI012", target, f"Cannot delete protected lifecycle attribute '{field}'.")
					else: env.pop(path_name(target), None)
			elif isinstance(statement, (ast.Break, ast.Continue)): return returns, True
			elif isinstance(statement, ast.Try):
				before = dict(env); before_invalid = set(self.invalid); branches = []
				for body in [statement.body, *(handler.body for handler in statement.handlers)]:
					local = dict(before); self.invalid = set(before_invalid); self.block(body, local); branches.append(local)
				self.invalid = before_invalid; self.merge_env(env, branches)
				self.block(statement.orelse, env); self.block(statement.finalbody, env)
		return returns, False

	def analyze_functions(self, statements, base):
		for node in statements:
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
			self.functions[node.name] = node
		for node in statements:
			if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
			local = dict(base); self.scope = node.name; before = set(self.invalid)
			before_imports = dict(self.imports); before_functions = dict(self.functions)
			for param in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
				local[param.arg] = self.annotated(param.annotation, base, "parameter:" + node.name + ":" + param.arg)
			self.block(node.body, local)
			self.analyze_functions(node.body, local)
			self.invalid = before; self.imports = before_imports; self.functions = before_functions

	def run(self):
		env = {}; self.block(self.tree.body, env); self.analyze_functions(self.tree.body, env)
		return sorted(self.findings, key=lambda f: (f.line, f.column, f.rule))


def analyze(source: str, path: str = "<source>") -> list[Finding]:
	return Analyzer(source, path).run()

"""Pylint adapter: framework analysis is shared with the standalone CLI."""
from pylint.checkers import BaseChecker
from .analysis import analyze
from .config import disabled_rules


class MutationChecker(BaseChecker):
	name = "vikela"
	msgs = {
		"W9011": ("RAI011: %s Suggestion: %s %s", "vikela-full-snapshot-write", "Unsafe detached projection, cross-owner live handle or retired lifetime write."),
		"W9012": ("RAI012: %s Suggestion: %s %s", "vikela-protected-attribute", "JsonPit lifecycle metadata is engine-owned."),
	}

	def visit_module(self, node):
		with node.stream() as stream:
			raw = stream.read()
		source = raw.decode(getattr(node, "file_encoding", None) or "utf-8") if isinstance(raw, bytes) else raw
		source = source.removeprefix("\ufeff")
		ignored = disabled_rules(node.file or ".")
		for finding in analyze(source, node.file or "<module>"):
			if finding.rule in ignored: continue
			self.add_message("W9011" if finding.rule == "RAI011" else "W9012",
				node=node, line=finding.line, col_offset=finding.column - 1,
				args=(finding.reason, finding.suggestion, finding.documentation))

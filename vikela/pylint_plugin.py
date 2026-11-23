"""Pylint adapter: framework analysis is shared with the standalone CLI."""
from pylint.checkers import BaseChecker
from .analysis import analyze
from .config import disabled_rules


class MutationChecker(BaseChecker):
	name = "vikela"
	msgs = {
		"W9011": ("RAI011: %s Suggestion: %s %s", "vikela-full-snapshot-write", "Unsafe detached projection, cross-owner live handle or retired lifetime write."),
		"W9012": ("RAI012: %s Suggestion: %s %s", "vikela-protected-attribute", "JsonPit lifecycle metadata is engine-owned."),
		"E9021": ("RAI021: %s Suggestion: %s %s", "vikela-test-configuration", "RAIkeep configuration must not be substituted."),
		"E9022": ("RAI022: %s Suggestion: %s %s", "vikela-test-pit-location", "Test Pits must use the configured TestCloud."),
		"E9023": ("RAI023: %s Suggestion: %s %s", "vikela-pit-directory", "Pit constructors require an InqPath directory."),
	}

	def visit_module(self, node):
		with node.stream() as stream:
			raw = stream.read()
		source = raw.decode(getattr(node, "file_encoding", None) or "utf-8") if isinstance(raw, bytes) else raw
		source = source.removeprefix("\ufeff")
		ignored = disabled_rules(node.file or ".")
		for finding in analyze(source, node.file or "<module>"):
			if finding.rule in ignored: continue
			self.add_message({"RAI011": "W9011", "RAI012": "W9012", "RAI021": "E9021", "RAI022": "E9022", "RAI023": "E9023"}[finding.rule],
				node=node, line=finding.line, col_offset=finding.column - 1,
				args=(finding.reason, finding.suggestion, finding.documentation))

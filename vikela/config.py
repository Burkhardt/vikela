"""Shared standalone/editor project configuration; no inspected modules are imported."""
from pathlib import Path
import tomllib


class ConfigurationError(ValueError): pass


def disabled_rules(path, explicit=None):
	if explicit is not None:
		candidates = [Path(explicit)]
	else:
		target = Path(path).resolve()
		start = target if target.is_dir() else target.parent
		candidates = [parent / "pyproject.toml" for parent in [start, *start.parents]]
	for candidate in candidates:
		if not candidate.is_file():
			if explicit is not None: raise ConfigurationError(f"Configuration does not exist: {candidate}")
			continue
		try:
			with candidate.open("rb") as stream: document = tomllib.load(stream)
		except (tomllib.TOMLDecodeError, UnicodeError) as exc:
			raise ConfigurationError(f"{candidate}: {exc}") from exc
		section = document.get("tool", {}).get("vikela")
		if section is None and explicit is None: continue
		if section is None: return set()
		if not isinstance(section, dict) or set(section) - {"disable"}:
			raise ConfigurationError(f"{candidate}: tool.vikela supports only 'disable'")
		value = section.get("disable", [])
		if not isinstance(value, list) or any(rule not in {"RAI011", "RAI012"} for rule in value):
			raise ConfigurationError(f"{candidate}: disable must be an array of RAI011/RAI012 rule IDs")
		return set(value)
	return set()

"""Vikela: optional development tooling, never a JsonPit runtime dependency."""
__version__ = "4.6.3"


def register(linter):
	"""Pylint's plugin entry point; import its dependency only in plugin mode."""
	from .pylint_plugin import MutationChecker
	linter.register_checker(MutationChecker(linter))


def load_ipython_extension(ipython):
	from .notebook import cell_magic
	ipython.register_magic_function(cell_magic, magic_kind="cell", magic_name="vikela")


def unload_ipython_extension(ipython):
	ipython.magics_manager.magics["cell"].pop("vikela", None)

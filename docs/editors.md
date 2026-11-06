# Editor and JupyterLab setup

Install the checker in the **selected project's interpreter**, separately from
production dependencies:

```sh
python -m pip install 'vikela[pylint]==4.6.2'
```

Until publication use `python -m pip install -e '/path/to/vikela[pylint]'`.

## VS Code

Use Microsoft's Pylint extension and select that interpreter:

```json
{
  "pylint.importStrategy": "fromEnvironment",
  "pylint.args": ["--load-plugins=vikela"],
  "pylint.lintOnChange": true
}
```

Findings use W9011/W9012 and include RAI011/RAI012, explanations, suggestions, and
links in the diagnostic text. The checker is exercised via Pylint in the automated
tests. Actual graphical editor acceptance should verify the selected interpreter,
inline markers, and Problems navigation; a CLI test is not an IDE interaction test.

## PyCharm — milestone 1

Settings → Tools → External Tools → add Vikela:

- Program: `$PyInterpreterDirectory$/python` (python.exe on Windows).
- Arguments: `-m vikela "$FilePath$" --nologo`.
- Working directory: `$ProjectFileDir$`.
- Output filter: `$FILE_PATH$:$LINE$:$COLUMN$:.*`.

This provides navigable file/line diagnostics. It does not install a native
inspection plugin or promise native quick fixes. Native inline PyCharm inspection
support remains milestone 2.

## JupyterLab

Install `vikela[notebook]` in the kernel interpreter. `%load_ext vikela` registers
`%%vikela`; add `--json` for a JSON array. The magic checks the cell without
executing it. It does not inspect live kernel objects or mutate the user namespace.

Notebook file scanning uses document cell order, not historical kernel execution
order. IPython command lines are ignored without executing them; non-Python cell
bodies are not guaranteed to parse and may produce a syntax/configuration error.

<p align="center">
  <img src="assets/logo.svg" width="160" height="160" alt="Vikela Logo" />
</p>

<h1 align="center">Vikela 🛡️</h1>

<p align="center">
  <strong>Python mutation guardrails and AST linter for JsonPit.</strong><br>
  <em>The defensive shield protecting distributed state from concurrent cloud replica stomps.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/vikela/"><img src="https://img.shields.io/badge/PyPI-vikela-D4AF37?style=flat-square&logo=pypi" alt="PyPI"></a>
  <a href="https://github.com/Burkhardt/RAIkeep/blob/main/doc/CR077_AIA_and_AfricaStage_to_RAIkeep_Vikela_and_JsonPit_Mutation_Guardrails.md"><img src="https://img.shields.io/badge/CR-CR077-blue?style=flat-square" alt="Specification"></a>
  <a href="docs/VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md"><img src="https://img.shields.io/badge/Identity-Modernist%20Ihawu-AA8214?style=flat-square" alt="Design Spec"></a>
</p>

---

## Overview

**Vikela** (*isiZulu: "to protect / shield"*) provides static analysis and mutation guardrails for `JsonPit` and its surrounding framework across the fleet. It functions both as a standalone CLI (`vikela`) and as a native Pylint checker plugin (`pylint --load-plugins=vikela`).

### The Twin-Shield Doctrine
* **C# development (.NET):** Checked by `RaiGuard`.
* **Python development:** Checked by `vikela`; JsonPit itself enforces runtime mutation guards.
* **The Straightening Action (`--qondisa`):** An official first-class alias for `--fix` (*isiZulu: "to straighten out / rectify"*), reserved for proven safe repairs. Version 0.1.0 provides suggestions and has no approved automatic rewrites.

---

## Core Rules

| Rule ID | Diagnostic Symbol | Description |
| :--- | :--- | :--- |
| **`RAI011`** | `vikela-full-snapshot-write` | Prevents full-snapshot read-modify-writes that erase concurrent cloud replica fields. |
| **`RAI012`** | `vikela-protected-attribute` | Protects immutable lifecycle and schema attributes from unauthorized client modification. |

---

## Terminal & CLI Experience

```bash
# Standard Scan
󰞀 vikela .

# Request safe fixes (v0.1.0 reports suggestions and leaves source unchanged)
vikela src/ --qondisa

# Pure JSON for CI/CD audit pipelines
vikela src/ --json
```

---

## IDE & Editor Integration

### VS Code
Configure in `.vscode/settings.json`:
```json
{
  "pylint.args": [
    "--load-plugins=vikela"
  ]
}
```

### JupyterLab
```python
%load_ext vikela

%%vikela
# Checks this cell WITHOUT executing it
```

---

## Visual Identity & Heraldry
Vikela's emblem is the **Modernist Ihawu**—drawing from the elliptical geometry of the traditional Nguni shield, anchored by the central **Qondisa Axis** (the plumb line that straightens crooked code).

* **Design Specification:** [`docs/VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md`](docs/VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md)
* **Master Vector:** [`assets/logo.svg`](assets/logo.svg)
* **Curator:** Koyo (Chief Marketing & Web Design Assistant)


## Version 0.1.0 installation and contracts

Vikela is optional development tooling alongside RAIkeep 4.6.0. Neither jsonpit nor
jpit depends on it. Until publication, install from this checkout in a development
virtual environment:

```sh
python -m pip install -e '.[dev]'
python -m pytest
vikela -v
```

After publication, install `vikela==0.1.0` for the independent CLI, or
`vikela[pylint]==0.1.0` inside the project's interpreter for editor checks.
`vikela[notebook]==0.1.0` adds IPython support in the chosen kernel interpreter.
A global CLI environment alone does not expose the checker in another venv.

Exit codes: **0** clean; **1** findings; **2** syntax/configuration;
**4** internal/environment failure. Pylint retains its own native exit codes.
`--json` emits a pure array; operational errors go to stderr. Scans do not import
or execute the inspected application. `--fix` and `--qondisa` are exact aliases;
no speculative field-dropping rewrite is available in 0.1.0.

- [Rules, shared project configuration and analysis limits](docs/rules.md)
- [VS Code, PyCharm and JupyterLab setup](docs/editors.md)

The CLI and plugin share `[tool.vikela]` configuration in pyproject.toml, with a
`disable` array of logical rule IDs. Checks are bounded and conservative: no
findings does not prove arbitrary dynamic code safe. Notebook scans follow
source-cell document order, not previous kernel execution order.

Publication/provisioning is orchestrated by Engenho; production server nodes do
not receive development lint tooling by default. Native PyCharm inspections are
milestone 2; milestone 1 supplies an External Tool configuration.

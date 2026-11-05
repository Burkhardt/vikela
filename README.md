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
* **C# Runtime (.NET):** Protected by `RaiGuard`.
* **Python Runtime:** Protected by `vikela`.
* **The Straightening Action (`--qondisa`):** An official first-class alias for `--fix` (*isiZulu: "to straighten out / rectify"*), aligning bent mutations into disciplined, cloud-safe sparse deltas.

---

## Core Rules

| Rule ID | Diagnostic Symbol | Description |
| :--- | :--- | :--- |
| **`RAI011`** | `vikela-full-snapshot-write` | Prevents full-snapshot read-modify-writes that erase concurrent cloud replica fields. |
| **`RAI012`** | `vikela-protected-attr-mutation` | Protects immutable lifecycle and schema attributes from unauthorized client modification. |

---

## Terminal & CLI Experience

```bash
# Standard Scan
󰞀 vikela .

# Straightening Run (Auto-Fix)
󰞀 vikela --qondisa

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
# Inspects cell mutations before execution
```

---

## Visual Identity & Heraldry
Vikela's emblem is the **Modernist Ihawu**—drawing from the elliptical geometry of the traditional Nguni shield, anchored by the central **Qondisa Axis** (the plumb line that straightens crooked code).

* **Design Specification:** [`docs/VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md`](docs/VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md)
* **Master Vector:** [`assets/logo.svg`](assets/logo.svg)
* **Curator:** Koyo (Chief Marketing & Web Design Assistant)

# Vikela 🛡️

**Python mutation guardrails and AST linter for JsonPit.**

Vikela (*isiZulu: "to protect / shield"*) provides static analysis and mutation guardrails for `JsonPit` and its surrounding framework across the fleet. It functions both as a standalone CLI (`vikela`) and as a native Pylint checker plugin (`pylint --load-plugins=vikela`).

- **Governing Specification:** [CR077](https://github.com/Burkhardt/RAIkeep/blob/main/doc/CR077_AIA_and_AfricaStage_to_RAIkeep_Vikela_and_JsonPit_Mutation_Guardrails.md)
- **Primary Rules:** `RAI011` (full-snapshot read-modify-write prevention), `RAI012` (protected attribute integrity)
- **Straightening Action:** `vikela --fix` (alias: `vikela --qondisa`)

# Vikela Visual Identity & Icon Specification

**Document:** `VIKELA_VISUAL_IDENTITY_AND_ICON_SPEC.md`  
**Related CR:** `CR077` (Vikela and JsonPit Mutation Guardrails)  
**Curator / Design Director:** Koyo (Chief Marketing & Web Design Assistant)  
**Target Projects:** `Burkhardt/vikela`, `Burkhardt/RAIkeep`, `AIA-Marketing`  
**Status:** Approved Specification  
**Asset Link:** [vikela-logo.svg](../assets/vikela-logo.svg)

---

**Implementation note (0.1.0):** The CLI currently uses the CR077 Unicode shield
badge. Nerd Font variants and repair illustrations below express the visual
identity direction. `--fix` / `--qondisa` are accepted, but no automatic rewrite
is approved in 0.1.0; source stays unchanged and actionable suggestions are shown.
RaiGuard/Vikela provide development diagnostics; JsonPit enforces runtime guards.

## 1. Cultural Lineage & Semantic Architecture

*Vikela* (*isiZulu: "to protect / shield"*) is the mutation guardrail and static analyzer defending Python JsonPit runtimes from destructive `RAI011` full-snapshot writes and cloud replica collisions.

### 1.1 The Twin-Shield Doctrine
- **C# Runtime:** Protected by `RaiGuard`.
- **Python Runtime:** Protected by `vikela`.
- **Remediation Action:** The `--qondisa` flag (*isiZulu: "to straighten out / rectify"*), providing the active craft of aligning bent mutations into disciplined sparse deltas.

Rather than framing the tool as an adversarial "inspector" or pedantic linter (which invites developer resistance), Vikela is designed as a **protective talisman**—a communal shield safeguarding replicated distributed state.

---

## 2. Nerd Fonts & Terminal CLI Specifications

For CLI banners, status lines, editor prompts, and CI/CD logs, use dedicated Nerd Font glyphs to establish an authoritative terminal presence.

### 2.1 Glyph Reference Matrix

| Role | Glyph | Nerd Font Symbol | Codepoint | Visual Context & Purpose |
| :--- | :---: | :--- | :--- | :--- |
| **Primary CLI Badge** | `󰞀` | `nf-md-shield_check` | `\udb81\udf80` | Material Design shield with embedded check. Used for default passes and clean scans. |
| **Dual-Runtime Sentinel** | `` | `nf-fa-shield_halved` | `\uf132` | Split-tone shield representing the dual C# (`RaiGuard`) and Python (`vikela`) guardrails. |
| **CI / Minimal Log** | `󰔚` | `nf-oct-shield_check` | `\uea58` | Monoline GitHub Octicon outline; light footprint for dense Actions logs. |
| **Universal Fallback** | `🛡️` | Standard Unicode | `U+1F6E1` | Fallback glyph when running in non-Nerd Font patched environments. |

### 2.2 CLI Output Formatting Examples

```bash
# Standard Clean Run
󰞀 vikela .
[OK] 19 mutation sites inspected across 4 modules. Zero RAI011 snapshot hazards.

# Straightening Run (Auto-Fix)
󰞀 vikela --qondisa
[RECTIFIED] 4 full-snapshot writes converted to sparse live-handle deltas.

# Finding / Violation Alert
 vikela src/africa_stage/fixtures.py
[WARN] RAI011: Full-snapshot write detected on live handle 'person_pit'.
       Remediation: mutate properties in-place or call pit[key].ExtendWith(delta).
```

---

## 3. Bespoke Logo Architecture: The Modernist Ihawu

The logo departs intentionally from medieval European heraldic heater shields, drawing inspiration from the sovereign geometry of the Southern African **Ihawu** / **Isihlangu** (the elliptical Nguni shield), articulated through Swiss structural grid precision.

```
                  o  (Top Finial)
                  |
             .--- | ---.
           /      |      \
          /   --  |  --   \   <-- Imigabelo (Sparse Delta Slots)
         |   ===  |  ===   |
         |        o        |   <-- Sentinel Protected Node
         |   ===  |  ===   |
          \   --  |  --   /   <-- Qondisa Axis (Central Spine)
           \      |      /
             '--- | ---'
                  |
                  o  (Bottom Finial)
```

### 3.1 Anatomical Elements
1. **The Elliptical Silhouette:**  
   Slender, aerodynamic, and defensive. It protects without projecting aggression.
2. **The Qondisa Central Axis (*Umgobo*):**  
   A vertical plumb line passing through the exact center of the shield, symbolizing the alignment and straightening of crooked code mutations.
3. **Geometric Delta Slots (*Imigabelo*):**  
   Traditional horizontal cowhide stitching cuts are abstracted into balanced, modern code blocks representing clean, discrete delta slices.
4. **Dual Facets (Live vs. Replica):**  
   The shield face is split into two harmonic tones:
   - *Left Wing:* Warm Ochre Gold (`#D4AF37`) representing in-memory live handles.
   - *Right Wing:* Deep Shadow Gold (`#C29B27`) representing replicated cloud deltas.
5. **The Sentinel Node:**  
   The central circle anchored along the spine represents the immutable protected attribute that cannot be overwritten.

---

## 4. Brand Palette & Color Tokens

Integrated directly with the AIA Cascais & Continental Design System:

| Token Name | Hex Value | Role |
| :--- | :--- | :--- |
| **Warm Ochre / Net Gold** | `#D4AF37` | Primary shield face, active highlights, success badges. |
| **Deep Ochre Shadow** | `#AA8214` | Shield bevel, depth facet, secondary brand anchor. |
| **Spine Silver / Calçada** | `#F4F4F0` | Central axis line, finials, high-contrast terminal text. |
| **Warm Graphite Ground** | `#181816` | Background container, badge outlines, dark canvas. |
| **Grid Boundary Rule** | `#2E2E2A` | Concentric orbital alignment rings and subtle guidelines. |

---

## 5. File Deliverables & Usage

- **Master Vector File:**  
  `file:///Users/RSB/Projects/GitHub/AIA-koyo/AIA-Marketing/vikela-logo.svg`
- **Recommended Asset Placements:**
  - `Burkhardt/vikela/assets/logo.svg` (GitHub README & PyPI documentation banner)
  - `Burkhardt/vikela/docs/_static/favicon.svg` (Sphinx / MkDocs favicon)
  - Terminal badge headers for `vikela` CLI help menus.

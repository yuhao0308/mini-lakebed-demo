# Implementation Tasks

This directory contains detailed task specifications for implementing the Mini-Lakebed MVP per the specification documents.

## Task Index

| Task | Title | Priority | Dependencies | Status |
|------|-------|----------|--------------|--------|
| [T01](T01_data_foundation.md) | Data Foundation | Critical | None | Not Started |
| [T02](T02_core_compliance.md) | Core Compliance (SB 766) | High | T01 | Not Started |
| [T03](T03_credit_flow.md) | Credit Flow (FCRA / Reg B) | High | T01 | Not Started |
| [T04](T04_math_precision.md) | Math Precision | Medium | T01 | Not Started |
| [T05](T05_governance.md) | Governance (OpenFGA / PII) | Medium | T01, T03 | Not Started |
| [T06](T06_demo_polish.md) | Demo Polish | Lower | T01-T05 | Not Started |

## Dependency Graph

```
T01 (Data Foundation)
 ├── T02 (Core Compliance)
 ├── T03 (Credit Flow)
 │    └── T05 (Governance)
 └── T04 (Math Precision)
      └── T06 (Demo Polish) ← requires T01-T05
```

## Spec Source Mapping

| Spec Document | Primary Tasks |
|---------------|---------------|
| `01_general_proposal.md` | Context for all tasks |
| `02_strategic_blueprint.md` | T02 (Agents), T03 (User Stories), T06 (Demo Script) |
| `03_implementation_dummy_data_plan.md` | T01 (Schemas), T04 (Math), T05 (Governance) |

## Acceptance Test Summary

| Task | Test Count | Key Coverage |
|------|------------|--------------|
| T01 | 19 tests | Schema validation, reference data |
| T02 | 18 tests | SB 766 disclosure, valueless add-ons |
| T03 | 22 tests | FCRA consent, adverse action codes |
| T04 | 22 tests | Day-count methods, tax rules, penny-perfect |
| T05 | 27 tests | Authorization, PII scrubbing, audit integrity |
| T06 | 21 tests | Demo scenarios, PDF generation, i18n |

**Total: 129 acceptance tests**

## Implementation Order

1. **T01** - Must be completed first (schema foundation)
2. **T02 + T03 + T04** - Can be parallelized after T01
3. **T05** - After T03 (needs credit models)
4. **T06** - Final polish after all others

## Task Format

Each task file includes:

- **Spec References** - Exact file + section citations
- **Files to Create** - New files with purpose
- **Files to Modify** - Existing files and changes
- **Implementation Specifications** - Code structure and logic
- **Acceptance Tests** - Test IDs, names, and assertions
- **Definition of Done** - Checklist for completion

## Related Documents

- [PROJECT_GAP_REPORT.md](../docs/PROJECT_GAP_REPORT.md) - Full gap analysis
- [DECISIONS.md](../docs/DECISIONS.md) - Architecture decision records
- [CLAUDE.md](../CLAUDE.md) - Development guidance

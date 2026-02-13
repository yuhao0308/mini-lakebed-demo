# Authorization Mode Verification (OpenFGA vs Fallback)

## Objective

Verify whether runtime authorization is using:
- full OpenFGA integration, or
- local RBAC/ReBAC fallback (`LocalAuthStore`).

## Current Result

The current runtime mode is:
- `local_rbac_fallback`

Reason:
- `AuthorizationService` currently evaluates tuples via the local in-memory store.
- OpenFGA model/tuples are present on disk (`openfga/model.fga`, `openfga/tuples.json`), but no active OpenFGA client call path is wired in runtime code.

## How to Check at Runtime

1. Start backend:

```bash
cd mini-lakebed-demo
./scripts/start_demo.sh --no-seed
```

2. Call health endpoint:

```bash
curl -s http://localhost:8000/health | jq '.authorization'
```

Expected fields include:
- `mode`
- `mode_reason`
- `openfga_configured`
- `openfga_api_url_set`
- `openfga_store_id_set`
- `openfga_model_id_set`
- `local_tuple_count`

## Is Fallback Sufficient?

For this demo build: **yes**.

Why:
- policy semantics (viewer/editor/auditor/sensitive_viewer, cross-store isolation, PII access) are enforced through local tuple checks
- authorization tests pass, including ownership, finance manager access, cross-store isolation, and sensitive log controls
- deterministic local mode avoids environment/network drift during live demo

## Production Recommendation

If production deployment is required:
1. Wire `AuthorizationService.check()` and `write_tuple()` to OpenFGA API.
2. Keep local fallback only as disaster-recovery mode.
3. Add startup checks that fail fast when OpenFGA config is required but unavailable.

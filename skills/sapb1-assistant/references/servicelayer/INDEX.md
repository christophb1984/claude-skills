<!-- source: SAP Help Portal sources listed below | version: SAP Business One 10.0, with feature-pack boundaries called out | verified: 2026-10-02 -->

# Service Layer index

Reference-backed guidance for the SAP Business One **Service Layer**. Read `service-layer-guide.md` first,
then open only the focused file the request needs. This first capability intentionally covers stable integration
patterns rather than attempting to mirror every entity and property in SAP's full API reference.

| Path | Covers | Version | Verified |
|---|---|---|---|
| `service-layer-guide.md` | **Start here.** OData v4 endpoint, metadata, login/session handling, CRUD/actions, query options, paging, ETags, batch and error/version rules | B1 10.0; OData v4 primary from FP 2405 | 2026-10-02 |
| `sql-queries.md` | Service Layer `SQLQueries`: availability, named parameters, execution, read-only/DML restriction, `select *` restriction and database normalization | B1 10.0 FP 2011+ | 2026-10-02 |
| `fp2602.md` | FP 2602 additions relevant to integrations: webhooks, Webhook Messenger, event subscriptions and API-change-log boundary | B1 10.0 FP 2602 | 2026-10-02 |

## Sources

| ID | Source | Role | Verified |
|---|---|---|---|
| `api-ref` | https://help.sap.com/doc/056f69366b5345a386bb8149f1700c19/10.0/en-US/Service%20Layer%20API%20Reference.html | Current OData v4 API reference; Login/Logout and exposed entities/actions | 2026-10-02 |
| `guide` | https://help.sap.com/docs/SAP_BUSINESS_ONE/f110a154dd0f4c20bf7f3ebca9eeb794 | SAP's Working with SAP Business One Service Layer guide; OData, query options, ETags, batch, SQLQueries, webhooks | 2026-10-02 |
| `change-log` | https://help.sap.com/docs/SAP_BUSINESS_ONE/f0bf25fb678c405db749545310803c8b | Sequential Service Layer API change logs by feature pack/service pack | 2026-10-02 |
| `fp2011-change` | https://help.sap.com/doc/f99c5aaf48d245438a15623357172fb8/10.0/en-US/100140VS100130.html | Confirms SQL query API additions in FP 2011 | 2026-10-02 |
| `fp2602-change` | https://help.sap.com/doc/25b17ff712de4af99c129dd18da0f051/10.0/en-US/10.0_FP2602_VS_SP2511.html | Confirms FP 2602 webhook-related types, properties, entity sets and actions | 2026-10-02 |

## Scope and limits

- This folder is **not** a full copy of the Service Layer API reference. For an entity/property/action not named
  here, verify it against the client's `/b1s/v2/$metadata` or SAP's current API reference before generating code.
- Feature-pack boundaries matter. Do not present an FP 2602 feature as available on an earlier B1 10.0 system.
- Client-specific UDFs, UDTs and UDOs are not bundled.

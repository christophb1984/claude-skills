<!-- source: SAP Help Portal Working with SAP Business One Service Layer SQL Query chapter and FP2011 change log; URLs in INDEX.md | version: SAP Business One 10.0 FP 2011+ | verified: 2026-10-02 -->

# Service Layer SQLQueries

`SQLQueries` exposes a controlled, read-oriented SQL query facility through Service Layer.

## 1. Availability

SAP's 10.0 FP 2011 Service Layer change log introduced the SQL query API types. SAP's Service Layer
documentation describes SQL Query support for Microsoft SQL Server and SAP HANA.

Sources: `fp2011-change`, `guide` in `INDEX.md`.

## 2. Create and execute

A query definition is created under `SQLQueries` and executed through its bound `List` operation.

Example shape:

```http
POST /b1s/v2/SQLQueries
Content-Type: application/json

{
  "SqlCode": "open_orders",
  "SqlName": "Open orders",
  "SqlText": "select DocEntry, CardCode, DocTotal from ORDR where DocTotal > :docTotal"
}
```

SAP documents named parameters with a colon (`:docTotal`). Execute a stored query through `List`, supplying
the parameter value through the documented GET or POST form.

Do not interpolate untrusted user text into SQL when a parameter can represent the value.

Source: `guide` (`Query with Parameter`) in `INDEX.md`.

## 3. Read-only boundary

Service Layer SQL Query is not a database-write escape hatch. SAP explicitly rejects DML statements such as
`UPDATE`, `ALTER`, `INSERT` and `DELETE`; the parser expects a SELECT/query expression instead.

That matches this skill's global rule: changes to SAP Business One data go through supported business APIs,
not direct table writes.

Source: `guide` (`SQL DML`) in `INDEX.md`.

## 4. Selection and exposure limits

SAP rejects `select *` in the **select list** because returning every column can expose sensitive data and hurt
performance. Name required columns explicitly. SAP documents that `select *` may still appear inside an
`EXISTS` subquery.

Service Layer supports only a defined subset of SQL keywords. Verify unfamiliar syntax against the current
SQL Query documentation instead of assuming arbitrary SQL Server/HANA syntax is accepted.

Sources: `guide` (`Select All Columns from One Table`, `SQL Keywords`) in `INDEX.md`.

## 5. SQL Server / HANA normalization

Service Layer normalizes table and column identifiers for the underlying database. SAP examples show the same
raw query normalized to bracketed identifiers on Microsoft SQL Server and double-quoted identifiers on SAP HANA.

This does **not** remove the need to verify table and column names. Use the bundled schema dictionary for the
client's B1 version where possible, and confirm later-feature-pack/client-specific fields on the live system.

Source: `guide` (`Table/Column Normalization`) in `INDEX.md`.

## 6. Integration pattern

For an application or MCP server, prefer a small catalog of named, parameterised queries over an endpoint that
accepts arbitrary SQL text. This is engineering practice, not an SAP requirement. It narrows the exposed
surface and makes authorization, auditing and output contracts easier to control.

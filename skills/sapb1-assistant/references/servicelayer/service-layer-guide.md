<!-- source: SAP Help Portal Service Layer API Reference and Working with SAP Business One Service Layer; URLs in INDEX.md | version: SAP Business One 10.0 | verified: 2026-10-02 -->

# Service Layer guide

How to build and review SAP Business One Service Layer integrations without guessing protocol, session or
concurrency behaviour. Exact business-object members still need verification against `/b1s/v2/$metadata` or
SAP's current API reference.

## 1. Protocol and metadata

- Service Layer exposes HTTP/OData APIs. `/b1s/v1/$metadata` is OData v3 and `/b1s/v2/$metadata` is OData v4.
- SAP's current API reference states that **from FP 2405, OData v3 is deprecated and OData v4 is the primary
  protocol**. V3 remains for backward compatibility; prefer `/b1s/v2` for new work.
- Use `GET /b1s/v2/$metadata` to verify entity sets, entity/complex types, properties, enums, actions and
  functions for the client's installed version. Do not infer a Service Layer property name from a database column.

Sources: `api-ref`, `guide` in `INDEX.md`.

## 2. Login, cookies and logout

```http
POST /b1s/v2/Login
Content-Type: application/json

{
  "CompanyDB": "SBODEMOUS",
  "UserName": "manager",
  "Password": "..."
}
```

- A successful login returns a session ID and sets `B1SESSION` and `ROUTEID` cookies.
- The **current API reference requires `B1SESSION`** on subsequent calls. It describes `ROUTEID` as optional:
  it provides session stickiness and improves load-balancing efficiency.
- Older Service Layer documentation used stricter wording for the cookies. For current code, follow the
  current API reference; retaining `ROUTEID` is still sensible when the server supplies it.
- The default idle session timeout is **30 minutes**; the API reference says it can be changed through the
  `SessionTimeout` property in the Service Layer `b1s.conf`.
- End an explicit session with `POST /b1s/v2/Logout`.

Source: `api-ref` in `INDEX.md`.

## 3. Read and query entities

Use the entity set and key shape from metadata. SAP examples use entity sets such as `Orders`, `Items` and
`BusinessPartners`.

Documented query options include `$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$count`, and `$expand`
where the entity exposes navigation properties.

Example:

```http
GET /b1s/v2/Orders?$select=DocEntry,CardCode,DocTotal&$filter=DocStatus eq 'O'&$top=20
```

When the service paginates a result, follow the returned OData next-link rather than constructing the next
page from assumptions.

Sources: `guide` (`Query Options`, `Collection Entity`) in `INDEX.md`.

## 4. Create, update, delete and actions

- Create an entity with `POST` to its entity set.
- Update an entity with `PATCH` to its keyed resource; SAP examples use `PATCH /Orders(<key>)`.
- Delete only where the entity supports deletion; business-document lifecycle operations are often exposed as
  actions rather than raw deletes.
- Bound actions use `POST`; SAP documents actions such as `POST /Orders(8)/Cancel`.

A Service Layer write is a supported B1 write path. A direct SQL `UPDATE`/`INSERT`/`DELETE` against B1 tables
is not.

Sources: `guide` (`Updating Entities`, entity actions) and `api-ref` in `INDEX.md`.

## 5. Optimistic concurrency with ETags

For read-modify-write flows, do not blindly overwrite an entity another user may have changed.

1. `GET` the entity and retain its `@odata.etag` / ETag.
2. Send the ETag as `If-Match` on the version-sensitive write/action.
3. Treat `412 Precondition Failed` as a concurrency conflict: re-read and reconcile rather than retrying the old
   payload unchanged.

SAP demonstrates this with an order action: a stale ETag on `POST /Orders(8)/Cancel` produces HTTP 412 and
SAP error `-2039`. SAP also documents ETag checks for entity deletion.

Sources: `guide` (`Service Layer ETag`, `ETag in Entity Action`, `ETag in Entity Delete`) in `INDEX.md`.

## 6. Batch

Service Layer supports OData batch requests. SAP documents a protocol-version difference for a syntactically
valid batch:

- OData v3: HTTP `202 Accepted`.
- OData v4: HTTP `200 OK`.

The overall batch response does not replace checking the status of each sub-response.

Source: `guide` (`Batch Response`) in `INDEX.md`.

## 7. Errors and verification

- Preserve the HTTP status and SAP error body in logs, but do not log credentials or session cookies.
- A missing entity/property in this curated reference is **not proof that Service Layer lacks it**. Check the
  client's `/b1s/v2/$metadata`.
- For feature-pack-specific behaviour, identify the installed B1 version and check the sequential API change log.

Sources: `api-ref`, `change-log` in `INDEX.md`.

## 8. Engineering pattern

For maintainable client code, separate Service Layer base URL/credentials, login/session-cookie handling,
business operations, DTOs, and ETag/concurrency handling. This is engineering practice rather than an SAP
requirement; the protocol facts it relies on are the documented behaviour above.

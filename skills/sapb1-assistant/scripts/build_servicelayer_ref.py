#!/usr/bin/env python3
"""Compile SAP Business One Service Layer OData v4 $metadata into grep-friendly Markdown references.

Fetch the metadata outside this script, then run:
  python build_servicelayer_ref.py metadata.xml references/servicelayer/metadata \
    --verified YYYY-MM-DD --label "SAP Business One 10.0 FP 2602"

The source XML is never copied to the output. A company can expose client-specific UDO/entity sets;
use a clean demo company when possible, or exclude/review custom names before committing a shared snapshot.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

EDM = "http://docs.oasis-open.org/odata/ns/edm"
EDMX = "http://docs.oasis-open.org/odata/ns/edmx"
TARGET_BYTES = 150_000


def q(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def truth(value: str | None, default: bool = False) -> bool:
    return default if value is None else value.lower() == "true"


def facets(el: ET.Element) -> str:
    bits: list[str] = []
    if el.attrib.get("Nullable") == "false":
        bits.append("required")
    for attr, label in (("MaxLength", "max"), ("Precision", "precision"), ("Scale", "scale"),
                        ("DefaultValue", "default"), ("Unicode", "unicode"), ("SRID", "srid")):
        if attr in el.attrib:
            bits.append(f"{label}={el.attrib[attr]}")
    return " ".join(bits)


def annotations(el: ET.Element) -> list[str]:
    out: list[str] = []
    scalar = ("String", "Bool", "Int", "Decimal", "Path", "PropertyPath", "NavigationPropertyPath", "EnumMember")
    for ann in el.findall(q(EDM, "Annotation")):
        term = ann.attrib.get("Term")
        if not term:
            continue
        value = next((ann.attrib[a] for a in scalar if a in ann.attrib), "")
        out.append(f"{term}={value}" if value else term)
    return out


def split_bundles(entries: list[tuple[str, str]], prefix: str) -> list[tuple[str, list[tuple[str, str]]]]:
    bundles, cur, size, idx = [], [], 0, 1
    for name, body in entries:
        n = len(body.encode("utf-8"))
        if cur and size + n > TARGET_BYTES:
            bundles.append((f"{prefix}-{idx:02d}.md", cur))
            idx += 1
            cur, size = [], 0
        cur.append((name, body))
        size += n
    if cur:
        bundles.append((f"{prefix}-{idx:02d}.md", cur))
    return bundles


def write_bundles(out: Path, bundles, provenance: str) -> dict[str, tuple[str, int, int]]:
    out.mkdir(parents=True, exist_ok=True)
    locations = {}
    for filename, entries in bundles:
        lines = [provenance, ""]
        for name, body in entries:
            start = len(lines) + 1
            body_lines = body.rstrip().splitlines()
            lines.extend(body_lines)
            locations[name] = (filename, start, len(body_lines))
            lines.append("")
        (out / filename).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return locations


def parse(path: Path):
    root = ET.parse(path).getroot()
    if root.tag != q(EDMX, "Edmx"):
        raise SystemExit("Expected OData v4 edmx:Edmx in the OASIS namespace.")
    if root.attrib.get("Version") not in (None, "4.0"):
        raise SystemExit(f"Expected OData v4 metadata, got Edmx Version={root.attrib.get('Version')!r}.")
    schemas = root.findall(".//" + q(EDM, "Schema"))
    if not schemas:
        raise SystemExit("No OData v4 Schema elements found.")
    return schemas


def build(metadata: Path, out: Path, verified: str, label: str, source: str, excludes: list[re.Pattern[str]]):
    schemas = parse(metadata)
    excluded: set[str] = set()

    def blocked(name: str) -> bool:
        if any(rx.search(name) for rx in excludes):
            excluded.add(name)
            return True
        return False

    type_entries, type_rows, member_lines = [], [], []
    enum_entries, enum_rows, enum_member_lines = [], [], []
    op_entries, op_rows, op_member_lines = [], [], []
    entity_sets = []

    for schema in schemas:
        ns = schema.attrib.get("Namespace", "")
        for kind in ("EntityType", "ComplexType"):
            for el in schema.findall(q(EDM, kind)):
                full = f"{ns}.{el.attrib['Name']}" if ns else el.attrib["Name"]
                if blocked(full):
                    continue
                keys = [x.attrib.get("Name", "") for x in el.findall(f"{q(EDM,'Key')}/{q(EDM,'PropertyRef')}")]
                props, navs = el.findall(q(EDM, "Property")), el.findall(q(EDM, "NavigationProperty"))
                lines = [f"# {full} ({kind})", ""]
                for text in ([f"BaseType: {el.attrib['BaseType']}"] if el.attrib.get("BaseType") else []) + \
                            (["Abstract: true"] if truth(el.attrib.get("Abstract")) else []) + \
                            (["OpenType: true"] if truth(el.attrib.get("OpenType")) else []) + \
                            (["HasStream: true"] if truth(el.attrib.get("HasStream")) else []) + \
                            (["Key: " + ", ".join(keys)] if keys else []):
                    lines.append(text)
                if len(lines) > 2:
                    lines.append("")
                if props:
                    lines += ["## Properties", ""]
                    for p in props:
                        f = facets(p)
                        anns = annotations(p)
                        suffix = (f" [{f}]" if f else "") + (" {" + "; ".join(anns) + "}" if anns else "")
                        line = f"- {p.attrib['Name']} : {p.attrib.get('Type','')}" + suffix
                        lines.append(line)
                        member_lines.append(f"{full}.{p.attrib['Name']} : {p.attrib.get('Type','')}" + suffix)
                    lines.append("")
                if navs:
                    lines += ["## Navigation properties", ""]
                    for n in navs:
                        opts = [f"{a}={n.attrib[a]}" for a in ("Partner", "ContainsTarget", "Nullable") if a in n.attrib]
                        lines.append(f"- {n.attrib['Name']} : {n.attrib.get('Type','')}" + (" [" + " ".join(opts) + "]" if opts else ""))
                    lines.append("")
                anns = annotations(el)
                if anns:
                    lines += ["## Scalar annotations", ""] + [f"- {a}" for a in anns] + [""]
                type_entries.append((full, "\n".join(lines).rstrip() + "\n"))
                type_rows.append(dict(name=full, kind=kind, keys=", ".join(keys), props=len(props), navs=len(navs),
                                      open=truth(el.attrib.get("OpenType")), base=el.attrib.get("BaseType", "")))

        for el in schema.findall(q(EDM, "EnumType")):
            full = f"{ns}.{el.attrib['Name']}" if ns else el.attrib["Name"]
            if blocked(full):
                continue
            members = el.findall(q(EDM, "Member"))
            lines = [f"# {full} (EnumType)", ""]
            if el.attrib.get("UnderlyingType"):
                lines += [f"UnderlyingType: {el.attrib['UnderlyingType']}", ""]
            if truth(el.attrib.get("IsFlags")):
                lines += ["IsFlags: true", ""]
            lines += ["| Member | Value | Scalar annotations |", "|---|---:|---|"]
            for m in members:
                value = m.attrib.get("Value", "")
                anns = annotations(m)
                ann_text = "; ".join(anns)
                lines.append(f"| {m.attrib['Name']} | {value} | {ann_text} |")
                enum_member_lines.append(f"{full}.{m.attrib['Name']} = {value}" + (" {" + ann_text + "}" if ann_text else ""))
            enum_entries.append((full, "\n".join(lines) + "\n"))
            enum_rows.append(dict(name=full, members=len(members), flags=truth(el.attrib.get("IsFlags"))))

        for kind in ("Action", "Function"):
            for el in schema.findall(q(EDM, kind)):
                full = f"{ns}.{el.attrib['Name']}" if ns else el.attrib["Name"]
                params = el.findall(q(EDM, "Parameter"))
                bound = truth(el.attrib.get("IsBound"))
                binding = params[0].attrib.get("Type", "") if bound and params else ""
                ident = full + (f"({binding})" if binding else "")
                if blocked(ident):
                    continue
                lines = [f"# {ident} ({kind})", ""]
                if bound:
                    lines += ["IsBound: true"]
                if el.attrib.get("EntitySetPath"):
                    lines += [f"EntitySetPath: {el.attrib['EntitySetPath']}"]
                if kind == "Function" and truth(el.attrib.get("IsComposable")):
                    lines += ["IsComposable: true"]
                if len(lines) > 2:
                    lines.append("")
                if params:
                    lines += ["## Parameters", ""]
                    for p in params:
                        f = facets(p)
                        lines.append(f"- {p.attrib.get('Name','')} : {p.attrib.get('Type','')}" + (f" [{f}]" if f else ""))
                    lines.append("")
                ret = el.find(q(EDM, "ReturnType"))
                ret_type = ret.attrib.get("Type", "") if ret is not None else ""
                if ret is not None:
                    f = facets(ret)
                    lines += ["## Return", "", ret_type + (f" [{f}]" if f else ""), ""]
                anns = annotations(el)
                if anns:
                    lines += ["## Scalar annotations", ""] + [f"- {a}" for a in anns] + [""]
                sig = ", ".join(f"{p.attrib.get('Name','')}:{p.attrib.get('Type','')}" for p in params)
                op_member_lines.append(f"{kind} {ident}({sig}) -> {ret_type or 'void'}")
                op_entries.append((ident, "\n".join(lines).rstrip() + "\n"))
                op_rows.append(dict(name=ident, kind=kind, bound=bound, binding=binding, params=len(params), ret=ret_type))

        for container in schema.findall(q(EDM, "EntityContainer")):
            cname = container.attrib.get("Name", "")
            for es in container.findall(q(EDM, "EntitySet")):
                full = f"{ns}.{cname}/{es.attrib['Name']}" if ns else f"{cname}/{es.attrib['Name']}"
                if blocked(full):
                    continue
                bindings = [(b.attrib.get("Path", ""), b.attrib.get("Target", "")) for b in es.findall(q(EDM, "NavigationPropertyBinding"))]
                entity_sets.append(dict(name=es.attrib["Name"], type=es.attrib.get("EntityType", ""),
                                        container=f"{ns}.{cname}" if ns else cname,
                                        include=es.attrib.get("IncludeInServiceDocument", ""),
                                        bindings=bindings, anns=annotations(es)))

    for seq in (type_entries, enum_entries, op_entries):
        seq.sort(key=lambda x: x[0].lower())
    for seq in (type_rows, enum_rows, op_rows, entity_sets):
        seq.sort(key=lambda x: x["name"].lower())
    for seq in (member_lines, enum_member_lines, op_member_lines):
        seq.sort(key=str.lower)

    out.mkdir(parents=True, exist_ok=True)
    provenance = f"<!-- source: {source} | version: {label} | verified: {verified} -->"
    type_locs = write_bundles(out / "api", split_bundles(type_entries, "types"), provenance)
    enum_locs = write_bundles(out / "enums", split_bundles(enum_entries, "enums"), provenance)
    op_locs = write_bundles(out / "operations", split_bundles(op_entries, "operations"), provenance)

    sets_by_type: dict[str, list[str]] = {}
    for es in entity_sets:
        sets_by_type.setdefault(es["type"], []).append(es["name"])

    lines = [provenance, "", "# Service Layer metadata type index", "",
             "| Type | Kind | Key | Properties | Navigation | Open | BaseType | Entity sets | File | Line | Lines |",
             "|---|---|---|---:|---:|---|---|---|---|---:|---:|"]
    for r in type_rows:
        f, ln, n = type_locs[r["name"]]
        sets = ", ".join(sets_by_type.get(r["name"], []))
        lines.append(f"| {r['name']} | {r['kind']} | {r['keys']} | {r['props']} | {r['navs']} | {'yes' if r['open'] else ''} | {r['base']} | {sets} | {f} | {ln} | {n} |")
    (out / "api" / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "api" / "members.md").write_text(provenance + "\n\n# Service Layer metadata members\n\n" + "\n".join(member_lines) + "\n", encoding="utf-8")

    lines = [provenance, "", "# Service Layer enum index", "", "| Enum | Members | Flags | File | Line | Lines |", "|---|---:|---|---|---:|---:|"]
    for r in enum_rows:
        f, ln, n = enum_locs[r["name"]]
        lines.append(f"| {r['name']} | {r['members']} | {'yes' if r['flags'] else ''} | {f} | {ln} | {n} |")
    (out / "enums" / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "enums" / "members.md").write_text(provenance + "\n\n# Service Layer enum members\n\n" + "\n".join(enum_member_lines) + "\n", encoding="utf-8")

    lines = [provenance, "", "# Service Layer operation index", "", "| Operation | Kind | Bound | Binding type | Parameters | Return | File | Line | Lines |", "|---|---|---|---|---:|---|---|---:|---:|"]
    for r in op_rows:
        f, ln, n = op_locs[r["name"]]
        lines.append(f"| {r['name']} | {r['kind']} | {'yes' if r['bound'] else ''} | {r['binding']} | {r['params']} | {r['ret']} | {f} | {ln} | {n} |")
    (out / "operations" / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "operations" / "members.md").write_text(provenance + "\n\n# Service Layer operations\n\n" + "\n".join(op_member_lines) + "\n", encoding="utf-8")

    lines = [provenance, "", "# Service Layer entity sets", "", "| Entity set | Entity type | Container | Include in service document | Navigation bindings | Scalar annotations |", "|---|---|---|---|---|---|"]
    for es in entity_sets:
        binds = "; ".join(f"{a}->{b}" for a, b in es["bindings"])
        lines.append(f"| {es['name']} | {es['type']} | {es['container']} | {es['include']} | {binds} | {'; '.join(es['anns'])} |")
    (out / "entity-sets.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    counts = {
        "schemas": len(schemas), "types": len(type_rows),
        "entity_types": sum(r["kind"] == "EntityType" for r in type_rows),
        "complex_types": sum(r["kind"] == "ComplexType" for r in type_rows),
        "properties": len(member_lines), "entity_sets": len(entity_sets),
        "operations": len(op_rows), "actions": sum(r["kind"] == "Action" for r in op_rows),
        "functions": sum(r["kind"] == "Function" for r in op_rows),
        "enums": len(enum_rows), "enum_members": len(enum_member_lines), "excluded": len(excluded),
    }
    namespaces = ", ".join(s.attrib.get("Namespace", "") for s in schemas if s.attrib.get("Namespace"))
    lines = [provenance, "", "# Service Layer generated metadata reference", "",
             f"Built from an OData v4 `$metadata` snapshot. Namespaces: {namespaces or '(none)' }.", "",
             "| Path | Covers |", "|---|---|",
             "| `api/INDEX.md` | EntityType and ComplexType routing: keys, counts, OpenType, BaseType, entity sets, bundle location |",
             "| `api/members.md` | Flat `Type.Property : ODataType` index |",
             "| `api/types-NN.md` | Full bundled type entries |",
             "| `entity-sets.md` | Entity sets, containers, navigation bindings and scalar annotations |",
             "| `operations/INDEX.md` | Action/Function routing: binding type, parameters, return type, bundle location |",
             "| `operations/members.md` | Flat operation signatures |",
             "| `operations/operations-NN.md` | Full bundled operations |",
             "| `enums/INDEX.md` | Enum routing and bundle location |",
             "| `enums/members.md` | Flat `Enum.Member = Value` index |",
             "| `enums/enums-NN.md` | Full bundled enums |", "", "## Counts", ""]
    lines += [f"- {k}: {v}" for k, v in counts.items()]
    lines += ["", "## Scope", "",
              "- This is a snapshot of one Service Layer OData v4 metadata document; another feature pack can expose a different surface.",
              "- `OpenType=true` permits dynamic properties such as UDFs; those dynamic properties are not enumerated here.",
              "- A company can expose client-specific UDO/entity sets. Prefer a clean demo company or review/exclude custom names before committing a shared reference.",
              "- Core CSDL and compact scalar annotations are extracted; complex annotation expression trees remain in the source metadata."]
    if excludes:
        lines += ["", "## Exclusion filters", ""] + [f"- `{rx.pattern}`" for rx in excludes]
    (out / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("metadata", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--verified", required=True, help="YYYY-MM-DD")
    ap.add_argument("--label", required=True, help='e.g. "SAP Business One 10.0 FP 2602"')
    ap.add_argument("--source", default="local /b1s/v2/$metadata snapshot", help="provenance text; never include credentials")
    ap.add_argument("--exclude-regex", action="append", default=[], help="repeatable regex matched against fully-qualified generated names")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.verified):
        raise SystemExit("--verified must be YYYY-MM-DD")
    counts = build(args.metadata, args.out, args.verified, args.label, args.source,
                   [re.compile(x) for x in args.exclude_regex])
    print("Built Service Layer metadata reference:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("build_servicelayer_ref", HERE / "build_servicelayer_ref.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)

V4 = '''<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
 <edmx:DataServices><Schema Namespace="SAPB1" xmlns="http://docs.oasis-open.org/odata/ns/edm">
  <EnumType Name="BoCardTypes" UnderlyingType="Edm.Int32">
   <Member Name="cCustomer" Value="0"><Annotation Term="SAPB1.ValidValue" String="C"/></Member>
  </EnumType>
  <ComplexType Name="DocumentLine" OpenType="true">
   <Property Name="ItemCode" Type="Edm.String"><Annotation Term="SAPB1.ColumnName" String="ItemCode"/></Property>
  </ComplexType>
  <EntityType Name="Document" OpenType="true"><Key><PropertyRef Name="DocEntry"/></Key>
   <Property Name="DocEntry" Type="Edm.Int32" Nullable="false"/>
   <Property Name="DocumentLines" Type="Collection(SAPB1.DocumentLine)"/>
  </EntityType>
  <Action Name="Close" IsBound="true"><Parameter Name="Document" Type="SAPB1.Document"/></Action>
  <Function Name="Ping"><ReturnType Type="Edm.String"/></Function>
  <EntityContainer Name="ServiceLayer">
   <EntitySet Name="Orders" EntityType="SAPB1.Document"><Annotation Term="Common.Label" String="Sales Order"/></EntitySet>
   <EntitySet Name="@CLIENT_UDO" EntityType="SAPB1.Document"/>
   <ActionImport Name="CloseOrder" Action="SAPB1.Close"/>
   <FunctionImport Name="Ping" Function="SAPB1.Ping" IncludeInServiceDocument="true"/>
  </EntityContainer>
 </Schema></edmx:DataServices>
</edmx:Edmx>'''

V3 = '''<edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx"><edmx:DataServices/></edmx:Edmx>'''


class BuildServiceLayerRefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, xml=V4, excludes=()):
        src = self.root / "metadata.xml"
        out = self.root / "out"
        src.write_text(xml, encoding="utf-8")
        counts = mod.build(src, out, "2026-10-03", "synthetic OData v4 fixture", "test snapshot",
                           [mod.re.compile(x) for x in excludes])
        return out, counts

    def test_builds_types_sets_operations_and_enums(self):
        out, counts = self.build()
        self.assertEqual(counts["entity_types"], 1)
        self.assertEqual(counts["complex_types"], 1)
        self.assertEqual(counts["actions"], 1)
        self.assertEqual(counts["functions"], 1)
        self.assertEqual(counts["enums"], 1)
        self.assertEqual(counts["operation_imports"], 2)
        self.assertIn("SAPB1.Document | EntityType | DocEntry", (out / "api" / "INDEX.md").read_text())
        self.assertIn("OpenType: true", (out / "api" / "types-01.md").read_text())
        self.assertIn("SAPB1.ColumnName=ItemCode", (out / "api" / "members.md").read_text())
        self.assertIn("SAPB1.ValidValue=C", (out / "enums" / "members.md").read_text())
        self.assertIn("Action SAPB1.Close", (out / "operations" / "members.md").read_text())
        self.assertIn("Common.Label=Sales Order", (out / "entity-sets.md").read_text())
        self.assertIn("CloseOrder | ActionImport | SAPB1.Close", (out / "operation-imports.md").read_text())

    def test_exclude_regex_removes_client_specific_names(self):
        out, counts = self.build(excludes=(r"@CLIENT_UDO",))
        self.assertEqual(counts["excluded"], 1)
        self.assertNotIn("@CLIENT_UDO", (out / "entity-sets.md").read_text())
        self.assertIn("@CLIENT_UDO", (out / "INDEX.md").read_text())

    def test_rejects_non_v4_metadata(self):
        src = self.root / "v3.xml"
        src.write_text(V3, encoding="utf-8")
        with self.assertRaises(SystemExit):
            mod.parse(src)


if __name__ == "__main__":
    unittest.main()

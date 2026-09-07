#!/usr/bin/env python3
"""Introspect a GraphQL type/field with full recursive ofType expansion."""
import json
import os
import sys

sys.path.insert(0, "/home/z/my-project/scripts")
import railway_apply as ra  # noqa: E402


def type_str(t):
    if t is None:
        return "?"
    kind = t.get("kind")
    name = t.get("name")
    if kind in ("NON_NULL", "LIST"):
        inner = type_str(t.get("ofType"))
        return f"{inner}!" if kind == "NON_NULL" else f"[{inner}]"
    return name or kind


def main():
    what = sys.argv[1]  # e.g. Query or DeploymentMeta
    field = sys.argv[2] if len(sys.argv) > 2 else None
    d = ra.gql('{__type(name:"%s"){fields{name args{name type{kind name ofType{kind name ofType{kind name ofType{kind name}}}}}} type{kind name ofType{kind name ofType{kind name}}}}}' % what)
    t = d["__type"]
    if t is None:
        print(f"type {what} not visible to this token")
        return
    if field:
        f = next((f for f in t["fields"] if f["name"] == field), None)
        if not f:
            print(f"field {field} not found on {what}")
            return
        print(f"{what}.{field}: {type_str(f['type'])}")
        for a in f["args"]:
            print(f"  arg {a['name']}: {type_str(a['type'])}")
    else:
        for f in t["fields"]:
            print(f"{f['name']}: {type_str(f['type'])}")


if __name__ == "__main__":
    main()

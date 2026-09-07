#!/usr/bin/env python3
"""Railway GraphQL introspection helper — find the exact mutation signatures we need."""
import json
import os
import sys
import urllib.request

TOKEN = os.environ["RAILWAY_TOKEN"]
API = "https://backboard.railway.app/graphql/v2"


def gql(query):
    req = urllib.request.Request(API, data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {TOKEN}", "content-type": "application/json",
                                          "User-Agent": "deyoung-cutover/1.0 (curl-compatible)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def tname(t):
    while t:
        if t.get("name"):
            return t["name"]
        t = t.get("ofType")
    return "?"


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "mutations"
    if what == "mutations":
        d = gql('{t:__type(name:"Mutation"){fields{name args{name type{kind name ofType{kind name ofType{kind name}}}}}}}')
        needle = sys.argv[2].lower() if len(sys.argv) > 2 else ""
        for f in d["data"]["t"]["fields"]:
            if needle and needle not in f["name"].lower():
                continue
            args = ", ".join(f"{a['name']}:{tname(a['type'])}" for a in f["args"])
            print(f"{f['name']}({args})")
    elif what == "type":
        d = gql(f'{{t:__type(name:"{sys.argv[2]}"){{inputFields{{name type{{kind name ofType{{kind name ofType{{kind name}}}}}}}} outputFields{{name}}}}}}')
        t = d["data"]["t"]
        if t.get("inputFields"):
            for a in t["inputFields"]:
                print(f"  in: {a['name']}:{tname(a['type'])}")
        if t.get("outputFields"):
            for a in t["outputFields"]:
                print(f"  out: {a['name']}")


if __name__ == "__main__":
    main()

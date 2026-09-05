#!/usr/bin/env python3.13
"""AgentMail setup: list existing API keys, create a new one for the web app."""
import json, sys
from agentmail import AgentMail

KEY = "am_us_3c12e851f778aa07202c11a2452fd6c2fd583a036ff7aca992790691dd9fc415"
c = AgentMail(api_key=KEY)

print("=== EXISTING API KEYS ===")
try:
    keys = c.api_keys.list()
    for k in getattr(keys, "api_keys", keys) or []:
        if isinstance(k, dict):
            print(json.dumps(k, default=str))
        else:
            print(f"id={getattr(k,'api_key_id',getattr(k,'id','?'))} name={getattr(k,'name','?')} created={getattr(k,'created_at','?')} prefix={getattr(k,'prefix',getattr(k,'key_prefix','?'))}")
except Exception as e:
    print("LIST ERROR:", e)

print("\n=== CREATE NEW KEY ===")
try:
    nk = c.api_keys.create(name="Deyoung Web App")
    print(json.dumps(nk, default=str, indent=2) if not isinstance(nk, str) else nk)
except Exception as e:
    print("CREATE ERROR:", e)

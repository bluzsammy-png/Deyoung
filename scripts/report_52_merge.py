#!/usr/bin/env python3
"""Merge cover.pdf + body.pdf into the final deliverable (normalized to A4)."""
from pypdf import PdfReader, PdfWriter

A4_W, A4_H = 595.28, 841.89

def normalize(page):
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    if abs(w - A4_W) > 0.1 or abs(h - A4_H) > 0.1:
        page.scale_to(A4_W, A4_H)
    return page

writer = PdfWriter()
writer.add_page(normalize(PdfReader("/home/z/my-project/research/cover.pdf").pages[0]))
for p in PdfReader("/home/z/my-project/research/body.pdf").pages:
    writer.add_page(normalize(p))
writer.add_metadata({
    "/Title": "DeYoung Fleet Expansion: Free and Low-Cost Cloud GPU Research 2026",
    "/Author": "Z.ai", "/Creator": "Z.ai",
    "/Subject": "Verified free-tier and paid GPU capacity plan for the DeYoung render fleet",
})
out = "/home/z/my-project/download/deyoung_fleet_gpu_research_2026.pdf"
with open(out, "wb") as f:
    writer.write(f)
print("merged:", out, "pages:", len(writer.pages))

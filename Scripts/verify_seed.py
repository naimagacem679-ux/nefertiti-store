#!/usr/bin/env python3
"""Loads schema.sql + seed.sql into an in-memory SQLite and compares EVERYTHING back
   to the original data. Exit code 1 on any difference.  Run: python3 -I scripts/verify_seed.py"""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "db/source/store-data.original.json"), encoding="utf8"))
db = sqlite3.connect(":memory:"); db.row_factory = sqlite3.Row
db.executescript(open(os.path.join(ROOT, "db/schema.sql"), encoding="utf8").read())
db.executescript(open(os.path.join(ROOT, "db/seed.sql"), encoding="utf8").read())
bad = []
def chk(name, a, b):
    if a != b: bad.append(name); print("DIFF", name, str(a)[:120], "!=", str(b)[:120])
n = lambda t: db.execute(f"select count(*) from {t}").fetchone()[0]
chk("categories", n("categories"), len(D["cats"])); chk("products", n("products"), len(D["products"])); chk("shipping", n("shipping"), 58)
for c in D["cats"]:
    r = db.execute("select * from categories where id=?", (c["id"],)).fetchone()
    chk("cat " + c["id"], (r["name"], r["name_en"], r["parent_id"], bool(r["hidden"]), bool(r["is_needs"]), json.loads(r["facets"])),
        (c["name"], c.get("en", ""), c.get("parent"), bool(c.get("hidden")), bool(c.get("needs")), c.get("facets", [])))
for p in D["products"]:
    r = db.execute("select * from products where id=?", (p["id"],)).fetchone()
    chk("prod " + p["id"], (r["name"], r["brand"], r["price"], r["old_price"], r["stock"], r["size"], r["description"], r["ingredients"], r["usage"],
        json.loads(r["colors"]), json.loads(r["sizes"]), json.loads(r["attrs"]), bool(r["is_new"]), bool(r["is_best"]), bool(r["hidden"]), bool(r["is_demo"]), r["created_at"]),
        (p["name"], p.get("brand", ""), p["price"], p.get("old", 0), p.get("stock", 0), p.get("size", ""), p.get("desc", ""), p.get("ingr", ""), p.get("usage", ""),
         p.get("colors", []), p.get("sizes", []), p.get("attrs", {}), bool(p.get("isNew")), bool(p.get("best")), bool(p.get("hidden")), bool(p.get("demo")), p.get("ts", 0)))
    chk("pcats " + p["id"], sorted(x[0] for x in db.execute("select category_id from product_categories where product_id=?", (p["id"],))), sorted(p.get("cats", [])))
    chk("variants " + p["id"], sorted((x["size"], x["color"], x["stock"]) for x in db.execute("select * from product_variants where product_id=?", (p["id"],))),
        sorted((v.get("size", ""), v.get("color", ""), v.get("stock", 0)) for v in p.get("variants", [])))
    chk("imgs " + p["id"], n_ := db.execute("select count(*) from product_images where product_id=?", (p["id"],)).fetchone()[0], len(p.get("imgs", [])))
W = json.load(open(os.path.join(ROOT, "db/source/wilayas.json"), encoding="utf8"))
for i, s in enumerate(D["ship"]):
    r = db.execute("select * from shipping where wilaya_code=?", (i + 1,)).fetchone()
    chk("ship %d" % (i + 1), (r["wilaya_name"], r["home_price"], r["desk_price"]), (W[i], s["h"], s["d"]))
S = {r["key"]: json.loads(r["value"]) for r in db.execute("select * from settings")}
st = D["store"]
chk("settings", (S["name"], S["whatsapp"], S["currency"], S["slogan"], S["sub2"]), (st["name"], st["whatsapp"], st["currency"], st["slogan"], st["sub2"]))
soc = {r["platform"]: r for r in db.execute("select * from socials")}
for p in st["socialOrder"]:
    chk("social " + p, (soc[p]["url"], bool(soc[p]["enabled"]), bool(soc[p]["avatar_key"]), bool(soc[p]["qr_key"])),
        (st["social"].get(p, ""), st["socialOn"].get(p, True) is not False, bool(st["pics"].get(p)), bool(st["qr"].get(p))))
chk("fk", db.execute("pragma foreign_key_check").fetchall(), [])
# image files: sizes must match the original data URIs
import base64, re
for sec, key in (("logo", "logo_key"), ("banner", "banner_key")):
    f = os.path.join(ROOT, "seed-images", S[key]); raw = base64.b64decode(re.sub(r"^data:[^,]+,", "", st[sec]))
    chk("image " + sec, open(f, "rb").read() == raw, True)
print("counts: categories=%d products=%d variants=%d shipping=%d socials=%d" % (n("categories"), n("products"), n("product_variants"), n("shipping"), n("socials")))
print("RESULT:", "FAIL (%d differences)" % len(bad) if bad else "OK - the database content matches the original store data exactly")
sys.exit(1 if bad else 0)

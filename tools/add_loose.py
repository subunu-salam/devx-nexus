#!/usr/bin/env python3
"""Loose / by-weight products (the USP): mark produce as loose (sold per kg),
and add loose SKUs for staples (rice, dal/pulses, flour, sugar, nuts, masala).
Loose products carry loose=true + perKg and are priced by weight in grams.
Packed/branded SKUs are untouched."""
import json, os, re, random
random.seed(11)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed.json")
data = json.load(open(SEED))
by_group = {}
for p in data:
    by_group.setdefault(p.get("group"), []).append(p)
next_id = max(p["id"] for p in data) + 1

def kg_of(unit):
    u = (unit or "").lower().replace(" ", "")
    m = re.match(r"([\d.]+)kg", u)
    if m: return float(m.group(1))
    m = re.match(r"([\d.]+)g", u)
    if m: return float(m.group(1)) / 1000.0
    return 1.0
def img(kw, pid): return f"https://loremflickr.com/300/300/{re.sub(r'[^a-z0-9]+',',',kw.lower())}?lock={pid}"

# --- 1) Fresh Produce -> loose (per kg) ---
produce = 0
for p in data:
    if p.get("cat") == "Fresh Produce":
        per = round(p["price"] / max(0.001, kg_of(p["unit"])), 1)
        p["loose"] = True
        p["perKg"] = per
        p["price"] = per          # price now means AED per kg
        p["unit"] = "1 kg"
        p.pop("was", None); p.pop("deal", None)
        produce += 1

# --- 2) Add loose SKUs for staples (group -> (display name, AED/kg)) ---
STAPLES = {
    "basmati-rice":("Basmati Rice",9), "sella-rice":("Sella Rice",6),
    "brown-rice":("Brown Rice",8), "jasmine-rice":("Jasmine Rice",9),
    "flour-wheat":("Wheat Flour",4), "lentils-red":("Red Lentils",10),
    "chickpeas-dry":("Chickpeas",9), "green-lentil":("Green Lentils",11),
    "oats":("Rolled Oats",8), "quinoa":("Quinoa",22),
    "mixed-nuts":("Mixed Nuts",45), "almonds":("Almonds",55),
    "cashews":("Cashews",62), "dried-apricots":("Dried Apricots",30),
    "turmeric":("Turmeric",28), "chili-powder":("Chili Powder",35),
    "coriander-powder":("Coriander Powder",25), "cumin":("Cumin",40),
    "garam-masala":("Garam Masala",45), "biryani-masala":("Biryani Masala",40),
    "black-pepper":("Black Pepper",60), "salt":("Table Salt",3),
}
CAT_FALLBACK = {"Rice & Grains":"Rice & Grains","Spices":"Spices","Snacks":"Snacks","Health & Organic":"Health & Organic"}
added = 0
for grp,(nm,per) in STAPLES.items():
    members = by_group.get(grp)
    if not members:   # group absent -> skip
        continue
    ref = members[0]
    item = {"id":next_id,"name":nm+" (Loose)","brand":"Loose","group":grp,
            "unit":"1 kg","price":per,"perKg":per,"loose":True,"cat":ref["cat"],
            "img":ref.get("img") or img(nm,next_id),"loc":ref.get("loc","Loose Counter"),
            "stock":200}
    data.append(item); next_id += 1; added += 1

# --- 3) New loose-only staple groups not already present ---
NEW = [("sugar","White Sugar","Rice & Grains","Aisle 7","sugar",4),
       ("peanuts","Peanuts","Snacks","Aisle 6","peanuts",22),
       ("walnuts","Walnuts","Snacks","Aisle 6","walnuts",48),
       ("green-gram","Green Gram (Moong)","Rice & Grains","Aisle 7","lentils",12),
       ("toor-dal","Toor Dal","Rice & Grains","Aisle 7","lentils",11)]
for grp,nm,cat,ap,kw,per in NEW:
    if grp in by_group: continue
    item = {"id":next_id,"name":nm+" (Loose)","brand":"Loose","group":grp,
            "unit":"1 kg","price":per,"perKg":per,"loose":True,"cat":cat,
            "img":img(kw,next_id),"loc":f"{ap} · Loose Counter","stock":200}
    data.append(item); next_id += 1; added += 1

json.dump(data, open(SEED,"w"), ensure_ascii=False, indent=2)
loose_total = sum(1 for p in data if p.get("loose"))
print(f"produce->loose: {produce} | loose staples added: {added} | total loose: {loose_total} | catalog: {len(data)}")

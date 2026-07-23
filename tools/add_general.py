#!/usr/bin/env python3
"""Add general-merchandise categories a real supermarket carries:
Stationery, Electrical & Batteries, Kitchen & Dining, plus bread items
(naan/roti) and frozen snacks (samosa/spring rolls). Idempotent-ish: skips
groups that already exist."""
import json, os, random, re
random.seed(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed.json")
data = json.load(open(SEED))
existing_groups = {p.get("group") for p in data}
next_id = max(p["id"] for p in data) + 1

def img(kw, pid):
    return f"https://loremflickr.com/300/300/{re.sub(r'[^a-z0-9]+',',',kw.lower())}?lock={pid}"
def aisle(pfx): return f"{pfx} · Rack {random.randint(1,6)} · Shelf {random.randint(1,6)}"

FAM = []
def fam(group,name,cat,ap,kw,brands,sizes,deal=0.15): FAM.append((group,name,cat,ap,kw,brands,sizes,deal))

# ---- Stationery & Office (Aisle 15) ----
fam("pen","Ball Pen","Stationery","Aisle 15","pen",["Pilot","BIC","Faber-Castell","Nexus"],[("each",2),("5-pack",8),("10-pack",14)])
fam("gel-pen","Gel Pen","Stationery","Aisle 15","pen,gel",["Pilot","Uniball","Nexus"],[("each",3),("5-pack",12)])
fam("pencil","Pencil","Stationery","Aisle 15","pencil",["Faber-Castell","Nataraj","Nexus"],[("each",1),("10-pack",7)])
fam("notebook","Notebook","Stationery","Aisle 15","notebook",["Classmate","Oxford","Nexus"],[("100pg",4),("200pg",7),("5-pack",22)])
fam("marker","Marker Pen","Stationery","Aisle 15","marker",["Sharpie","Faber-Castell"],[("each",5),("4-pack",18)])
fam("highlighter","Highlighter","Stationery","Aisle 15","highlighter",["Stabilo","Faber-Castell"],[("each",4),("4-pack",15)])
fam("glue","Glue Stick","Stationery","Aisle 15","glue",["Pritt","UHU","Nexus"],[("each",4),("3-pack",10)])
fam("tape","Sticky Tape","Stationery","Aisle 15","tape",["Scotch","Nexus"],[("each",3),("3-pack",8)])
fam("scissors","Scissors","Stationery","Aisle 15","scissors",["Maped","Nexus"],[("each",7)])
fam("stapler","Stapler","Stationery","Aisle 15","stapler",["Kangaro","Nexus"],[("each",12)])
fam("sticky-notes","Sticky Notes","Stationery","Aisle 15","sticky,notes",["Post-it","Nexus"],[("pack",6),("5-pack",22)])
fam("eraser","Eraser","Stationery","Aisle 15","eraser",["Faber-Castell","Nataraj"],[("each",1),("4-pack",5)])
fam("printer-paper","A4 Paper","Stationery","Aisle 15","paper,ream",["Double A","JK","Nexus"],[("500 sheets",14),("ream×5",60)])
fam("file-folder","File Folder","Stationery","Aisle 15","folder,file",["Solo","Nexus"],[("each",3),("10-pack",22)])
fam("envelope","Envelopes","Stationery","Aisle 15","envelope",["Nexus"],[("25-pack",7),("50-pack",12)])
fam("calculator","Calculator","Stationery","Aisle 15","calculator",["Casio","Nexus"],[("each",22)])

# ---- Electrical & Batteries (Aisle 16) ----
fam("aa-battery","AA Batteries","Electrical","Aisle 16","battery",["Duracell","Energizer","Nexus"],[("4-pack",12),("8-pack",22)])
fam("aaa-battery","AAA Batteries","Electrical","Aisle 16","battery",["Duracell","Energizer","Nexus"],[("4-pack",12),("8-pack",22)])
fam("9v-battery","9V Battery","Electrical","Aisle 16","battery",["Duracell","Energizer"],[("each",9),("2-pack",16)])
fam("led-bulb","LED Bulb","Electrical","Aisle 16","light,bulb",["Philips","Osram","Nexus"],[("9W",12),("2-pack",22)])
fam("extension-cord","Extension Cord","Electrical","Aisle 16","extension,cord",["Belkin","Nexus"],[("3m",28),("5m",39)])
fam("charger-cable","USB-C Cable","Electrical","Aisle 16","usb,cable",["Anker","Belkin","Nexus"],[("1m",22),("2m",32)])
fam("power-bank","Power Bank","Electrical","Aisle 16","power,bank",["Anker","Nexus"],[("10000mAh",89),("20000mAh",139)])
fam("flashlight","Flashlight","Electrical","Aisle 16","flashlight,torch",["Eveready","Nexus"],[("each",18)])
fam("lighter","Lighter","Electrical","Aisle 16","lighter",["Clipper","Nexus"],[("each",3),("3-pack",8)])
fam("candles","Candles","Electrical","Aisle 16","candle",["Nexus"],[("6-pack",9),("12-pack",15)])

# ---- Kitchen & Dining (Aisle 17) ----
fam("paper-plates","Paper Plates","Kitchen & Dining","Aisle 17","paper,plate",["Fun","Hotpack","Nexus"],[("25-pack",9),("50-pack",16)])
fam("paper-cups","Paper Cups","Kitchen & Dining","Aisle 17","paper,cup",["Fun","Hotpack"],[("50-pack",10),("100-pack",17)])
fam("plastic-cutlery","Plastic Cutlery","Kitchen & Dining","Aisle 17","cutlery,plastic",["Fun","Hotpack"],[("24-set",8),("48-set",14)])
fam("cling-film","Cling Film","Kitchen & Dining","Aisle 17","cling,film",["Fun","Nexus"],[("30m",9),("60m",15)])
fam("food-containers","Food Containers","Kitchen & Dining","Aisle 17","food,container",["Lock&Lock","Hotpack","Nexus"],[("5-set",22),("10-set",38)])
fam("ziplock-bags","Ziplock Bags","Kitchen & Dining","Aisle 17","ziplock,bag",["Ziploc","Nexus"],[("30-pack",13),("50-pack",20)])
fam("napkins","Table Napkins","Kitchen & Dining","Aisle 17","napkins",["Fine","Nexus"],[("100-pack",8),("200-pack",14)])
fam("dish-sponge","Dish Sponges","Kitchen & Dining","Aisle 17","sponge,dish",["Scotch-Brite","Nexus"],[("3-pack",9),("6-pack",15)])
fam("kitchen-gloves","Kitchen Gloves","Kitchen & Dining","Aisle 17","gloves,rubber",["Vileda","Nexus"],[("pair",8),("3-pair",18)])
fam("water-bottle","Water Bottle","Kitchen & Dining","Aisle 17","water,bottle",["Milton","Nexus"],[("750ml",18),("1L",24)])

# ---- Bakery additions ----
fam("naan","Naan Bread","Bakery","Bakery","naan,bread",["Modern Bakery","Nexus Bakery"],[("4pc",8),("6pc",11)])
fam("roti","Roti / Chapati","Bakery","Bakery","roti,flatbread",["Modern Bakery","Switz"],[("10pc",9),("20pc",16)])
fam("burger-buns","Burger Buns","Bakery","Bakery","burger,bun",["Modern Bakery","Nexus Bakery"],[("4pc",7),("8pc",12)])
fam("pita-bread","Pita Bread","Bakery","Bakery","pita,bread",["Modern Bakery"],[("5pc",5),("10pc",8)])

# ---- Frozen snack additions ----
fam("samosa","Samosa","Frozen","Freezer","samosa",["Switz","Al Kabeer"],[("10pc",14),("20pc",24)])
fam("spring-rolls","Spring Rolls","Frozen","Freezer","spring,rolls",["Switz","Al Kabeer"],[("10pc",15),("20pc",26)])
fam("frozen-pizza","Frozen Pizza","Frozen","Freezer","frozen,pizza",["Dr. Oetker","Americana"],[("each",18),("2-pack",33)])
fam("kubba","Kubba","Frozen","Freezer","kibbeh",["Al Kabeer"],[("500g",22)])

added = 0
for (group,name,cat,ap,kw,brands,sizes,dc) in FAM:
    if group in existing_groups:   # don't duplicate
        continue
    for b in brands:
        for (size,price) in sizes:
            pr = max(1, round(price * random.uniform(0.95,1.08)))
            item = {"id":next_id,"name":name,"brand":b,"group":group,"unit":size,
                    "price":pr,"cat":cat,"img":img(kw,next_id),"loc":aisle(ap),
                    "stock":random.choice([0,6,10,15,20,25,30,40,50])}
            if random.random() < dc:
                item["was"]=round(pr*random.uniform(1.1,1.25)); item["deal"]=True
            data.append(item); next_id += 1; added += 1

json.dump(data, open(SEED,"w"), ensure_ascii=False, indent=2)
cats={}
for p in data: cats[p['cat']]=cats.get(p['cat'],0)+1
print("added", added, "| total", len(data))
print("new categories present:", [c for c in ('Stationery','Electrical','Kitchen & Dining') if c in cats])

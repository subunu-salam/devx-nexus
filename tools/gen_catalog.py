#!/usr/bin/env python3
"""
DevX Nexus — catalog generator.
Keeps the existing 47 products, remaps their 5 variant groups to clean
"need-based" keys, then appends ~450 realistic supermarket SKUs.

Variant model
-------------
Every product belongs to a `group` that represents a NEED (e.g. "basmati-rice").
A group spans multiple BRANDS and multiple SIZES. So when a shopper asks
generically ("I want rice") we can show every brand/size in that group; when
they ask for a dish ("make biryani") we auto-pick the best-value SKU in the
group and offer the rest as swappable alternatives.
"""
import json, os, random, re

random.seed(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "seed.json")

# ---- image service (unique per item, stable via ?lock=<id>) ----
def img(keyword, pid):
    kw = re.sub(r"\s+", ",", keyword.strip())
    return f"https://loremflickr.com/300/300/{kw}?lock={pid}"

# ---- load & remap existing 47 ----
existing = json.load(open(SEED))
GROUP_REMAP = {
    "rice-basmati": "basmati-rice",
    "milk-1l": "full-cream-milk",
    "water-12": "mineral-water",
    "detergent-2kg": "laundry-detergent",
    "oil-sun": "sunflower-oil",
}
for p in existing:
    if p.get("group") in GROUP_REMAP:
        p["group"] = GROUP_REMAP[p["group"]]

next_id = max(p["id"] for p in existing) + 1
out = list(existing)

def aisle(prefix):
    return f"{prefix} · Rack {random.randint(1,6)} · Shelf {random.randint(1,6)}"

# family = (group, display_name, category, aisle_prefix, image_kw,
#           [brands], [(size_label, price)], deal_chance)
# Prices in AED. We generate brand × size SKUs.
FAM = []
def fam(group, name, cat, ap, kw, brands, sizes, deal=0.2):
    FAM.append((group, name, cat, ap, kw, brands, sizes, deal))

# ---------- RICE & GRAINS (Aisle 7) ----------
fam("basmati-rice","Basmati Rice","Rice & Grains","Aisle 7","basmati,rice",
    ["India Gate","Daawat","Tilda","Falcon","Abu Kass"],
    [("1kg",12),("2kg",22),("5kg",42),("10kg",78)])
fam("sella-rice","Sella Rice","Rice & Grains","Aisle 7","rice,grain",
    ["Falcon","Abu Kass","Aeroplane"],[("1kg",9),("5kg",30),("10kg",55)])
fam("brown-rice","Brown Rice","Rice & Grains","Aisle 7","brown,rice",
    ["Tilda","Organic Larder","Nexus Gold"],[("1kg",14),("2kg",24)])
fam("jasmine-rice","Jasmine Rice","Rice & Grains","Aisle 7","jasmine,rice",
    ["Royal Umbrella","Golden Phoenix"],[("1kg",13),("5kg",48)])
fam("quinoa","Quinoa","Rice & Grains","Aisle 7","quinoa",
    ["Organic Larder","Bob's Red Mill"],[("500g",22),("1kg",38)])
fam("oats","Rolled Oats","Rice & Grains","Aisle 7","oats,cereal",
    ["Quaker","Mornflake","Nexus Gold"],[("500g",11),("1kg",18)])
fam("lentils-red","Red Lentils","Rice & Grains","Aisle 7","lentils",
    ["Nexus Value","Tata","Organic Larder"],[("500g",7),("1kg",12)])
fam("chickpeas-dry","Chickpeas","Rice & Grains","Aisle 7","chickpeas",
    ["Nexus Value","Tata"],[("500g",7),("1kg",11)])
fam("flour-wheat","Wheat Flour","Rice & Grains","Aisle 7","flour",
    ["KFMB","Nexus Gold","Aashirvaad"],[("1kg",6),("5kg",26),("10kg",48)])

# ---------- PASTA & NOODLES (Aisle 7) ----------
fam("pasta-penne","Penne Pasta","Pasta & Noodles","Aisle 7","pasta,penne",
    ["Barilla","Al Alali","Nexus Value"],[("500g",8),("1kg",14)])
fam("pasta-spaghetti","Spaghetti","Pasta & Noodles","Aisle 7","spaghetti,pasta",
    ["Barilla","Napolina","Nexus Value"],[("500g",8),("1kg",14)])
fam("pasta-macaroni","Macaroni","Pasta & Noodles","Aisle 7","macaroni",
    ["Al Alali","Nexus Value"],[("400g",6),("900g",12)])
fam("instant-noodles","Instant Noodles","Pasta & Noodles","Aisle 7","noodles",
    ["Indomie","Maggi","Nissin"],[("5-pack",6),("10-pack",11)])
fam("vermicelli","Vermicelli","Pasta & Noodles","Aisle 7","vermicelli",
    ["Nexus Gold","Bambino"],[("500g",5),("900g",9)])

# ---------- FRESH MEAT & POULTRY (Fresh Meat · Counter) ----------
fam("whole-chicken","Whole Chicken","Fresh Meat","Fresh Meat · Counter","chicken,raw",
    ["Al Ain","Sadia","Seara","Doux"],[("900g",19),("1.2kg",24),("1.4kg",28)])
fam("chicken-breast","Chicken Breast","Fresh Meat","Fresh Meat · Counter","chicken,breast",
    ["Al Ain","Sadia","Perdix"],[("500g",16),("1kg",29)])
fam("chicken-thigh","Chicken Thighs","Fresh Meat","Fresh Meat · Counter","chicken,meat",
    ["Al Ain","Sadia"],[("500g",13),("1kg",24)])
fam("mutton","Mutton Cuts","Fresh Meat","Fresh Meat · Counter","mutton,lamb",
    ["Australian","Local Farm"],[("500g",32),("1kg",60)])
fam("beef-mince","Beef Mince","Fresh Meat","Fresh Meat · Counter","beef,mince",
    ["Americana","Local Farm"],[("500g",22),("1kg",41)])
fam("fish-salmon","Salmon Fillet","Fresh Meat","Fresh Meat · Counter","salmon,fish",
    ["Norwegian","Fresh Catch"],[("300g",28),("600g",52)])
fam("fish-hammour","Hammour Fillet","Fresh Meat","Fresh Meat · Counter","fish,fillet",
    ["Fresh Catch"],[("500g",34),("1kg",64)])
fam("prawns","Prawns","Fresh Meat","Fresh Meat · Counter","prawns,seafood",
    ["Fresh Catch","Asmak"],[("500g",30),("1kg",56)])

# ---------- DAIRY & CHILLED (Aisle 2) ----------
fam("full-cream-milk","Full Cream Milk","Dairy & Chilled","Aisle 2","milk,bottle",
    ["Almarai","Al Ain","Nadec","Al Rawabi"],[("500ml",4),("1L",7),("2L",13)])
fam("low-fat-milk","Low Fat Milk","Dairy & Chilled","Aisle 2","milk",
    ["Almarai","Al Ain","Nadec"],[("1L",7),("2L",13)])
fam("laban","Laban","Dairy & Chilled","Aisle 2","laban,yogurt",
    ["Almarai","Al Ain","Nadec"],[("1L",6),("2L",11)])
fam("greek-yogurt","Greek Yogurt","Dairy & Chilled","Aisle 2","yogurt",
    ["Almarai","Al Rawabi","Fage"],[("400g",9),("900g",17)])
fam("plain-yogurt","Fresh Yogurt","Dairy & Chilled","Aisle 2","yogurt,plain",
    ["Almarai","Al Ain","Nadec"],[("400g",5),("1kg",10)])
fam("cheese-slices","Cheese Slices","Dairy & Chilled","Aisle 2","cheese,slices",
    ["Kraft","President","Almarai"],[("200g",11),("400g",19)])
fam("mozzarella","Mozzarella","Dairy & Chilled","Aisle 2","mozzarella,cheese",
    ["President","Galbani","Almarai"],[("200g",14),("500g",29)])
fam("butter","Butter","Dairy & Chilled","Aisle 2","butter",
    ["Lurpak","President","Almarai"],[("200g",13),("400g",24)])
fam("labneh","Labneh","Dairy & Chilled","Aisle 2","labneh",
    ["Almarai","Al Ain"],[("500g",12),("900g",20)])
fam("eggs","Eggs","Dairy & Chilled","Aisle 2","eggs",
    ["Al Ain","Saha","Golden"],[("6pc",6),("15pc",13),("30pc",24)])
fam("cream","Cooking Cream","Dairy & Chilled","Aisle 2","cream",
    ["Nestlé","President","Almarai"],[("250ml",6),("500ml",11)])

# ---------- FRESH PRODUCE (Aisle 1/3) ----------
fam("onions","Onions","Fresh Produce","Aisle 1","onion",
    ["Local Farm","Import"],[("1kg",4),("2kg",7)])
fam("tomatoes","Tomatoes","Fresh Produce","Aisle 1","tomato",
    ["Local Farm","Import"],[("500g",4),("1kg",7)])
fam("potatoes","Potatoes","Fresh Produce","Aisle 1","potato",
    ["Local Farm","Import"],[("1kg",5),("2kg",9)])
fam("cucumber","Cucumber","Fresh Produce","Aisle 1","cucumber",
    ["Local Farm"],[("500g",4),("1kg",7)])
fam("carrots","Carrots","Fresh Produce","Aisle 1","carrot",
    ["Local Farm","Import"],[("500g",4),("1kg",7)])
fam("bell-pepper","Bell Peppers","Fresh Produce","Aisle 1","bell,pepper",
    ["Local Farm","Import"],[("500g",8),("1kg",14)])
fam("bananas","Bananas","Fresh Produce","Aisle 3","banana",
    ["Philippines","India"],[("1kg",6),("2kg",11)])
fam("apples","Apples","Fresh Produce","Aisle 3","apple",
    ["USA","France","Iran"],[("1kg",9),("2kg",16)])
fam("oranges","Oranges","Fresh Produce","Aisle 3","orange,fruit",
    ["Egypt","Spain"],[("1kg",7),("2kg",12)])
fam("lemons","Lemons","Fresh Produce","Aisle 3","lemon",
    ["Local Farm","Import"],[("500g",5),("1kg",9)])
fam("grapes","Grapes","Fresh Produce","Aisle 3","grapes",
    ["India","Egypt"],[("500g",9),("1kg",16)])
fam("mango","Mango","Fresh Produce","Aisle 3","mango",
    ["India","Pakistan"],[("1kg",12),("2kg",22)])
fam("garlic","Garlic","Fresh Produce","Aisle 1","garlic",
    ["China","Local Farm"],[("250g",5),("500g",9)])
fam("ginger","Ginger","Fresh Produce","Aisle 1","ginger",
    ["China","India"],[("250g",6),("500g",10)])
fam("coriander","Fresh Coriander","Fresh Produce","Aisle 1","coriander,herb",
    ["Local Farm"],[("bunch",3)])
fam("mint","Fresh Mint","Fresh Produce","Aisle 1","mint,herb",
    ["Local Farm"],[("bunch",3)])
fam("spinach","Spinach","Fresh Produce","Aisle 1","spinach",
    ["Local Farm"],[("bunch",4),("500g",7)])
fam("lettuce","Lettuce","Fresh Produce","Aisle 1","lettuce",
    ["Local Farm","Import"],[("each",5)])

# ---------- SPICES & MASALA (Aisle 5) ----------
fam("turmeric","Turmeric Powder","Spices","Aisle 5","turmeric,spice",
    ["Eastern","National","Shan"],[("100g",4),("200g",7)])
fam("chili-powder","Chili Powder","Spices","Aisle 5","chili,spice",
    ["Eastern","National","Shan"],[("100g",5),("200g",9)])
fam("coriander-powder","Coriander Powder","Spices","Aisle 5","spice,powder",
    ["Eastern","National"],[("100g",4),("200g",7)])
fam("cumin","Cumin Powder","Spices","Aisle 5","cumin,spice",
    ["Eastern","National"],[("100g",5),("200g",9)])
fam("garam-masala","Garam Masala","Spices","Aisle 5","masala,spice",
    ["Eastern","Shan","MDH"],[("100g",6),("200g",10)])
fam("biryani-masala","Biryani Masala","Spices","Aisle 5","biryani,masala",
    ["Shan","National","MDH"],[("60g",5),("100g",7)])
fam("black-pepper","Black Pepper","Spices","Aisle 5","pepper,spice",
    ["Eastern","National"],[("100g",7),("200g",12)])
fam("cardamom","Cardamom","Spices","Aisle 5","cardamom,spice",
    ["Eastern","Premium"],[("50g",12),("100g",22)])
fam("cinnamon","Cinnamon Sticks","Spices","Aisle 5","cinnamon",
    ["Eastern","Premium"],[("50g",6),("100g",10)])
fam("saffron","Saffron","Spices","Aisle 5","saffron",
    ["Al Fares","Premium"],[("1g",14),("2g",26)])
fam("salt","Table Salt","Spices","Aisle 5","salt",
    ["Nexus Value","Tata"],[("1kg",3),("2kg",5)])
fam("bay-leaf","Bay Leaves","Spices","Aisle 5","bay,leaf",
    ["Eastern"],[("20g",4)])

# ---------- COOKING OIL (Aisle 9) ----------
fam("sunflower-oil","Sunflower Oil","Cooking Oil","Aisle 9","sunflower,oil",
    ["Rahma","Noor","Nexus Value","Sunny"],[("1L",10),("1.8L",17),("3L",27)])
fam("olive-oil","Olive Oil","Cooking Oil","Aisle 9","olive,oil",
    ["Rafael Salgado","Borges","Coopoliva"],[("500ml",18),("1L",32),("2L",58)])
fam("corn-oil","Corn Oil","Cooking Oil","Aisle 9","corn,oil",
    ["Afia","Noor"],[("1.5L",18),("3L",33)])
fam("ghee","Ghee","Cooking Oil","Aisle 9","ghee",
    ["Almarai","Lulu","Nexus Gold"],[("500g",18),("1kg",33),("2kg",62)])
fam("vegetable-oil","Vegetable Oil","Cooking Oil","Aisle 9","vegetable,oil",
    ["Afia","Rahma"],[("1.5L",16),("5L",44)])

# ---------- BEVERAGES (Aisle 8) ----------
fam("mineral-water","Mineral Water","Beverages","Aisle 8","water,bottle",
    ["Masafi","Al Ain","Mai Dubai","Aquafina"],[("1.5L",2),("6×1.5L",10),("12×500ml",9)])
fam("cola","Cola","Beverages","Aisle 8","cola,soda",
    ["Pepsi","Coca-Cola","RC Cola"],[("1.5L",5),("2.25L",7),("6×330ml",12)])
fam("orange-juice","Orange Juice","Beverages","Aisle 8","orange,juice",
    ["Lacnor","Almarai","Rani"],[("1L",7),("1.5L",10)])
fam("mango-juice","Mango Juice","Beverages","Aisle 8","mango,juice",
    ["Rani","Lacnor","Almarai"],[("1L",7),("1.5L",10)])
fam("energy-drink","Energy Drink","Beverages","Aisle 8","energy,drink",
    ["Red Bull","Power Horse"],[("250ml",7),("4×250ml",25)])
fam("sparkling-water","Sparkling Water","Beverages","Aisle 8","sparkling,water",
    ["Perrier","San Pellegrino"],[("750ml",9),("6×330ml",28)])

# ---------- TEA & COFFEE (Aisle 8) ----------
fam("black-tea","Black Tea","Tea & Coffee","Aisle 8","tea",
    ["Lipton","Ahmad Tea","Alokozay"],[("100 bags",12),("200 bags",22)])
fam("green-tea","Green Tea","Tea & Coffee","Aisle 8","green,tea",
    ["Lipton","Ahmad Tea","Twinings"],[("25 bags",9),("100 bags",26)])
fam("instant-coffee","Instant Coffee","Tea & Coffee","Aisle 8","coffee,jar",
    ["Nescafé","Davidoff","Al Ameed"],[("100g",18),("200g",32)])
fam("arabic-coffee","Arabic Coffee","Tea & Coffee","Aisle 8","arabic,coffee",
    ["Al Ameed","Najran"],[("250g",22),("500g",40)])
fam("ground-coffee","Ground Coffee","Tea & Coffee","Aisle 8","ground,coffee",
    ["Lavazza","Illy"],[("250g",26),("500g",48)])

# ---------- BREAKFAST & CEREAL (Aisle 4) ----------
fam("cornflakes","Corn Flakes","Breakfast","Aisle 4","cornflakes,cereal",
    ["Kellogg's","Nexus Gold"],[("375g",14),("750g",24)])
fam("choco-cereal","Chocolate Cereal","Breakfast","Aisle 4","cereal,chocolate",
    ["Nestlé","Kellogg's"],[("375g",16),("600g",25)])
fam("honey","Honey","Breakfast","Aisle 4","honey,jar",
    ["Al Shifa","Langnese","Marco Polo"],[("250g",16),("500g",29),("1kg",52)])
fam("jam","Fruit Jam","Breakfast","Aisle 4","jam",
    ["Hero","American Garden","Vitrac"],[("340g",9),("450g",12)])
fam("peanut-butter","Peanut Butter","Breakfast","Aisle 4","peanut,butter",
    ["American Garden","Skippy"],[("340g",14),("510g",19)])
fam("chocolate-spread","Chocolate Spread","Breakfast","Aisle 4","chocolate,spread",
    ["Nutella","Nexus Gold"],[("350g",16),("750g",29)])
fam("dates","Dates","Breakfast","Aisle 4","dates",
    ["Bateel","Al Foah","Lulu"],[("500g",18),("1kg",32)])

# ---------- CANNED & JARRED (Aisle 4) ----------
fam("tomato-paste","Tomato Paste","Canned & Jarred","Aisle 4","tomato,paste",
    ["Al Alali","California Garden"],[("135g",3),("400g",6)])
fam("canned-tuna","Canned Tuna","Canned & Jarred","Aisle 4","tuna,can",
    ["California Garden","Al Alali","John West"],[("100g",5),("185g",8)])
fam("canned-beans","Baked Beans","Canned & Jarred","Aisle 4","beans,can",
    ["Heinz","Al Alali"],[("220g",4),("415g",6)])
fam("canned-corn","Sweet Corn","Canned & Jarred","Aisle 4","corn,can",
    ["Del Monte","Al Alali"],[("200g",5),("340g",7)])
fam("canned-chickpeas","Canned Chickpeas","Canned & Jarred","Aisle 4","chickpeas,can",
    ["Al Alali","California Garden"],[("400g",4)])
fam("coconut-milk","Coconut Milk","Canned & Jarred","Aisle 4","coconut,milk",
    ["Ayam","KLF"],[("400ml",6),("1L",12)])

# ---------- CONDIMENTS & SAUCES (Aisle 4) ----------
fam("ketchup","Ketchup","Condiments","Aisle 4","ketchup",
    ["Heinz","American Garden"],[("340g",7),("910g",14)])
fam("mayonnaise","Mayonnaise","Condiments","Aisle 4","mayonnaise",
    ["Heinz","American Garden","Hellmann's"],[("400ml",10),("650ml",15)])
fam("soy-sauce","Soy Sauce","Condiments","Aisle 4","soy,sauce",
    ["Kikkoman","Lee Kum Kee"],[("150ml",8),("500ml",18)])
fam("hot-sauce","Hot Sauce","Condiments","Aisle 4","hot,sauce",
    ["Tabasco","American Garden"],[("60ml",9),("150ml",15)])
fam("vinegar","Vinegar","Condiments","Aisle 4","vinegar",
    ["Heinz","Nexus Value"],[("473ml",6),("946ml",10)])
fam("pasta-sauce","Pasta Sauce","Condiments","Aisle 4","pasta,sauce",
    ["Barilla","Prego"],[("400g",11),("680g",16)])

# ---------- BAKERY (Bakery) ----------
fam("arabic-bread","Arabic Bread","Bakery","Bakery","arabic,bread",
    ["Modern Bakery","Nexus Bakery"],[("5pc",4),("10pc",7)])
fam("white-bread","White Bread","Bakery","Bakery","bread,loaf",
    ["Modern Bakery","Britannia"],[("small",5),("large",8)])
fam("brown-bread","Brown Bread","Bakery","Bakery","brown,bread",
    ["Modern Bakery","Britannia"],[("small",6),("large",9)])
fam("croissant","Croissant","Bakery","Bakery","croissant",
    ["Nexus Bakery"],[("4pc",10),("6pc",14)])
fam("samoon","Samoon","Bakery","Bakery","bread,bun",
    ["Nexus Bakery"],[("4pc",4),("8pc",7)])
fam("cake","Sponge Cake","Bakery","Bakery","cake,sponge",
    ["Nexus Bakery","Tiffany"],[("400g",15),("600g",22)])

# ---------- SNACKS & CONFECTIONERY (Aisle 6) ----------
fam("potato-chips","Potato Chips","Snacks","Aisle 6","chips,crisps",
    ["Lay's","Pringles","Kettle"],[("40g",2),("165g",8),("6-pack",12)])
fam("tortilla-chips","Tortilla Chips","Snacks","Aisle 6","tortilla,chips",
    ["Doritos","Nachos"],[("150g",8),("250g",13)])
fam("popcorn","Popcorn","Snacks","Aisle 6","popcorn",
    ["Act II","Pop Secret"],[("3-pack",9),("6-pack",16)])
fam("chocolate-bar","Chocolate Bar","Snacks","Aisle 6","chocolate,bar",
    ["Galaxy","Cadbury","KitKat","Snickers"],[("single",4),("6-pack",18)])
fam("biscuits","Biscuits","Snacks","Aisle 6","biscuits,cookies",
    ["McVitie's","Britannia","Oreo"],[("200g",6),("400g",10)])
fam("wafers","Wafers","Snacks","Aisle 6","wafer",
    ["Loacker","Tiffany"],[("150g",7),("300g",12)])
fam("mixed-nuts","Mixed Nuts","Snacks","Aisle 6","nuts,mixed",
    ["Al Rifai","Union"],[("250g",18),("500g",33)])
fam("almonds","Almonds","Snacks","Aisle 6","almonds",
    ["Al Rifai","California"],[("250g",20),("500g",37)])
fam("cashews","Cashews","Snacks","Aisle 6","cashews",
    ["Al Rifai","Union"],[("250g",22),("500g",41)])
fam("dried-apricots","Dried Apricots","Snacks","Aisle 6","apricot,dried",
    ["Turkish","Union"],[("250g",12),("500g",22)])

# ---------- FROZEN (Freezer) ----------
fam("frozen-fries","Frozen Fries","Frozen","Freezer","fries,frozen",
    ["McCain","Americana"],[("750g",11),("1.5kg",19)])
fam("frozen-veg","Mixed Vegetables","Frozen","Freezer","frozen,vegetables",
    ["California Garden","Americana"],[("400g",7),("900g",13)])
fam("frozen-peas","Green Peas","Frozen","Freezer","peas,frozen",
    ["California Garden","Americana"],[("400g",6),("900g",11)])
fam("frozen-nuggets","Chicken Nuggets","Frozen","Freezer","nuggets,chicken",
    ["Sadia","Americana","Seara"],[("400g",13),("750g",22)])
fam("frozen-paratha","Paratha","Frozen","Freezer","paratha,bread",
    ["Switz","Kawan"],[("5pc",9),("30pc",26)])
fam("ice-cream","Ice Cream","Frozen","Freezer","ice,cream",
    ["London Dairy","Baskin Robbins","Igloo"],[("500ml",16),("1L",26)])

# ---------- HOUSEHOLD & CLEANING (Aisle 10) ----------
fam("laundry-detergent","Laundry Detergent","Household","Aisle 10","detergent,laundry",
    ["Ariel","Persil","Tide","Bonux"],[("1kg",16),("2kg",29),("4kg",52)])
fam("dish-soap","Dishwashing Liquid","Household","Aisle 10","dish,soap",
    ["Fairy","Pril","Nexus Value"],[("500ml",8),("1L",14)])
fam("floor-cleaner","Floor Cleaner","Household","Aisle 10","cleaner,floor",
    ["Dettol","Flash","Clorox"],[("1L",12),("3L",26)])
fam("bleach","Bleach","Household","Aisle 10","bleach,cleaner",
    ["Clorox","Nexus Value"],[("1L",7),("2L",12)])
fam("glass-cleaner","Glass Cleaner","Household","Aisle 10","glass,cleaner",
    ["Windex","Clorox"],[("500ml",11),("750ml",15)])
fam("tissue","Facial Tissue","Household","Aisle 10","tissue,box",
    ["Fine","Kleenex"],[("5-box",15),("10-box",27)])
fam("toilet-roll","Toilet Rolls","Household","Aisle 10","toilet,paper",
    ["Fine","Nexus Value"],[("6-roll",14),("12-roll",25)])
fam("kitchen-roll","Kitchen Towel","Household","Aisle 10","kitchen,towel",
    ["Fine","Nexus Value"],[("2-roll",9),("4-roll",16)])
fam("foil","Aluminium Foil","Household","Aisle 10","aluminium,foil",
    ["Fun","Nexus Value"],[("10m",8),("30m",18)])
fam("garbage-bags","Garbage Bags","Household","Aisle 10","garbage,bag",
    ["Sanita","Nexus Value"],[("30-pack",12),("50-pack",18)])

# ---------- PERSONAL CARE (Aisle 12) ----------
fam("shampoo","Shampoo","Personal Care","Aisle 12","shampoo",
    ["Head & Shoulders","Pantene","Dove","Sunsilk"],[("400ml",18),("650ml",27)])
fam("conditioner","Conditioner","Personal Care","Aisle 12","conditioner,hair",
    ["Pantene","Dove","Sunsilk"],[("400ml",18),("650ml",26)])
fam("body-wash","Body Wash","Personal Care","Aisle 12","body,wash",
    ["Dove","Lux","Palmolive"],[("250ml",14),("500ml",23)])
fam("bar-soap","Bar Soap","Personal Care","Aisle 12","soap,bar",
    ["Dove","Lux","Lifebuoy"],[("4-pack",12),("6-pack",17)])
fam("toothpaste","Toothpaste","Personal Care","Aisle 12","toothpaste",
    ["Colgate","Signal","Sensodyne"],[("100ml",9),("2-pack",16)])
fam("toothbrush","Toothbrush","Personal Care","Aisle 12","toothbrush",
    ["Oral-B","Colgate"],[("2-pack",12),("4-pack",20)])
fam("deodorant","Deodorant","Personal Care","Aisle 12","deodorant",
    ["Rexona","Nivea","Dove"],[("150ml",13),("2-pack",22)])
fam("hand-wash","Hand Wash","Personal Care","Aisle 12","hand,wash",
    ["Dettol","Lifebuoy"],[("250ml",9),("500ml",15)])
fam("razor","Razors","Personal Care","Aisle 12","razor,shaving",
    ["Gillette","BIC"],[("3-pack",16),("5-pack",25)])
fam("shaving-foam","Shaving Foam","Personal Care","Aisle 12","shaving,foam",
    ["Gillette","Nivea"],[("200ml",15),("300ml",21)])

# ---------- BABY (Aisle 13) ----------
fam("diapers","Baby Diapers","Baby","Aisle 13","diapers,baby",
    ["Pampers","Huggies","MamyPoko"],[("small-pack",34),("mega-pack",62)])
fam("baby-wipes","Baby Wipes","Baby","Aisle 13","baby,wipes",
    ["Pampers","Huggies","Johnson's"],[("64-pack",11),("3×64",28)])
fam("baby-formula","Baby Formula","Baby","Aisle 13","baby,formula",
    ["Aptamil","Similac","Nan"],[("400g",42),("800g",74)])
fam("baby-shampoo","Baby Shampoo","Baby","Aisle 13","baby,shampoo",
    ["Johnson's","Sebamed"],[("200ml",16),("500ml",29)])

# ---------- PET (Aisle 14) ----------
fam("dog-food","Dog Food","Pet","Aisle 14","dog,food",
    ["Pedigree","Royal Canin"],[("1.5kg",26),("3kg",46)])
fam("cat-food","Cat Food","Pet","Aisle 14","cat,food",
    ["Whiskas","Friskies"],[("1.2kg",24),("2kg",38)])
fam("cat-litter","Cat Litter","Pet","Aisle 14","cat,litter",
    ["Ever Clean","Catsan"],[("5L",22),("10L",38)])

# ---------- HEALTH & ORGANIC (Aisle 3) ----------
fam("olive","Olives","Health & Organic","Aisle 3","olives",
    ["Coopoliva","Al Alali"],[("300g",9),("650g",15)])
fam("hummus","Hummus","Health & Organic","Aisle 3","hummus",
    ["Al Ain","Freshly"],[("250g",8),("500g",13)])
fam("granola","Granola","Health & Organic","Aisle 3","granola",
    ["Organic Larder","Nature Valley"],[("350g",18),("500g",25)])
fam("green-lentil","Green Lentils","Health & Organic","Aisle 3","green,lentils",
    ["Organic Larder","Tata"],[("500g",8),("1kg",14)])
fam("chia-seeds","Chia Seeds","Health & Organic","Aisle 3","chia,seeds",
    ["Organic Larder","Bob's Red Mill"],[("250g",16),("500g",28)])
fam("almond-milk","Almond Milk","Health & Organic","Aisle 3","almond,milk",
    ["Alpro","Almarai"],[("1L",13),("6×1L",70)])

# ---- generate SKUs ----
def slugify(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")

for (group,name,cat,ap,kw,brands,sizes,deal_chance) in FAM:
    for b in brands:
        for (size,price) in sizes:
            # vary price slightly by brand tier
            tier = 1.0
            if b in ("Tilda","India Gate","President","Lurpak","Lavazza","Illy","Bateel",
                     "Nutella","Red Bull","Perrier","San Pellegrino","Aptamil","Royal Canin",
                     "Sensodyne","Fage","Galbani","Davidoff"):
                tier = 1.15
            if b in ("Nexus Value","Nexus Gold","Import","Local Farm"):
                tier = 0.9
            pr = round(price * tier * random.uniform(0.97,1.06))
            pr = max(2, pr)
            item = {
                "id": next_id,
                "name": name,
                "brand": b,
                "group": group,
                "unit": size,
                "price": pr,
                "cat": cat,
                "img": img(kw, next_id),
                "loc": aisle(ap),
                "stock": random.choice([0,4,8,12,15,18,22,25,30,35,40,45,50,60])
            }
            if random.random() < deal_chance:
                item["was"] = round(pr * random.uniform(1.1,1.28))
                item["deal"] = True
            out.append(item)
            next_id += 1

json.dump(out, open(SEED,"w"), ensure_ascii=False, indent=2)
print("TOTAL products:", len(out))
print("new added:", len(out)-len(existing))
print("distinct groups:", len(set(p.get('group') for p in out if p.get('group'))))
cats={}
for p in out: cats[p['cat']]=cats.get(p['cat'],0)+1
print("categories:")
for k,v in sorted(cats.items()): print(f"  {k}: {v}")

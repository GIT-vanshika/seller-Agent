import json
import os
from typing import List, Dict, Any

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

products: List[Dict[str, Any]] = []
evidence: List[Dict[str, Any]] = []
seller_policies: List[Dict[str, Any]] = []

ev_id_counter = 1

def add_evidence(product_id: str, ev_type: str, source: str, label: str, content: str):
    global ev_id_counter
    evidence.append({
        "id": f"ev_{ev_id_counter:03d}",
        "product_id": product_id,
        "type": ev_type,
        "source": source,
        "label": label,
        "content": content
    })
    ev_id_counter += 1

product_specs = [
    # 1-5 (Primary Scenarios)
    {"id": "prod_001", "name": "Premium Butter Cookies", "cat": "Packaged Goods", "desc": "Rich, buttery Danish-style cookies in a tin.", "price": 100.0, "mode": "fixed", "asp": 100.0, "target": 100.0, "res": 100.0, "rounds": 0, "bulk": None, "scenario": "fixed_1"},
    {"id": "prod_002", "name": "Gourmet Vanilla Ice Cream", "cat": "Packaged Goods", "desc": "Artisanal Madagascar vanilla bean ice cream 500ml.", "price": 150.0, "mode": "fixed", "asp": 150.0, "target": 150.0, "res": 150.0, "rounds": 0, "bulk": None, "scenario": "fixed_2"},
    {"id": "prod_003", "name": "Silk Designer Dress", "cat": "Fashion", "desc": "Handcrafted pure mulberry silk evening gown.", "price": 2500.0, "mode": "negotiable", "asp": 2400.0, "target": 1750.0, "res": 1550.0, "rounds": 5, "bulk": None, "scenario": "hard_negotiation"},
    {
        "id": "prod_004",
        "name": "Handcrafted Ceramic Vase Set",
        "cat": "Home Decor",
        "desc": "Set of 3 minimalist terracotta ceramic vases.",
        "price": 1200.0,
        "mode": "negotiable",
        "asp": 1150.0,
        "target": 900.0,
        "res": 800.0,
        "rounds": 4,
        "bulk": {
            "tiers": [
                {"min_quantity": 5, "discount_percentage": 10.0},    # Effective unit price: 1080 >= 800
                {"min_quantity": 10, "discount_percentage": 18.0},   # Effective unit price: 984 >= 800
                {"min_quantity": 20, "discount_percentage": 25.0}    # Effective unit price: 900 >= 800
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_005", "name": "Embroidered Linen Shirt", "cat": "Fashion", "desc": "Breathable 100% organic linen casual shirt.", "price": 1800.0, "mode": "negotiable", "asp": 1750.0, "target": 1400.0, "res": 1200.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"},

    # 6-10
    {"id": "prod_006", "name": "Organic Dark Chocolate Bar", "cat": "Packaged Goods", "desc": "70% Single origin Ecuadorian dark chocolate.", "price": 80.0, "mode": "fixed", "asp": 80.0, "target": 80.0, "res": 80.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_007", "name": "Sparkling Mango Soda 6-Pack", "cat": "Packaged Goods", "desc": "Refreshing natural fruit juice sparkling soda.", "price": 120.0, "mode": "fixed", "asp": 120.0, "target": 120.0, "res": 120.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_008", "name": "Leather Biker Jacket", "cat": "Fashion", "desc": "Genuine full-grain lambskin leather jacket.", "price": 4500.0, "mode": "negotiable", "asp": 4300.0, "target": 3500.0, "res": 3200.0, "rounds": 5, "bulk": None, "scenario": "negotiable"},
    {
        "id": "prod_009",
        "name": "Handwoven Jute Rug 4x6ft",
        "cat": "Home Decor",
        "desc": "Eco-friendly natural fiber braided floor rug.",
        "price": 3000.0,
        "mode": "negotiable",
        "asp": 2900.0,
        "target": 2300.0,
        "res": 2100.0,
        "rounds": 4,
        "bulk": {
            "tiers": [
                {"min_quantity": 3, "discount_percentage": 10.0},
                {"min_quantity": 5, "discount_percentage": 20.0}
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_010", "name": "Velvet Cushion Covers (Set of 4)", "cat": "Home Decor", "desc": "Luxurious soft touch decorative cushion covers.", "price": 1000.0, "mode": "negotiable", "asp": 950.0, "target": 750.0, "res": 650.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"},

    # 11-15
    {"id": "prod_011", "name": "Roasted Almonds & Raisins Mix", "cat": "Packaged Goods", "desc": "Premium dry fruit blend 250g jar.", "price": 220.0, "mode": "fixed", "asp": 220.0, "target": 220.0, "res": 220.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_012", "name": "Cold Pressed Coconut Oil 1L", "cat": "Packaged Goods", "desc": "Virgin unrefined coconut oil for cooking & hair.", "price": 280.0, "mode": "fixed", "asp": 280.0, "target": 280.0, "res": 280.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_013", "name": "Handcrafted Leather Tote Bag", "cat": "Fashion", "desc": "Spacious genuine leather handbag with laptop sleeve.", "price": 3200.0, "mode": "negotiable", "asp": 3100.0, "target": 2500.0, "res": 2200.0, "rounds": 4, "bulk": None, "scenario": "negotiable"},
    {
        "id": "prod_014",
        "name": "Brass Table Lamp with Linen Shade",
        "cat": "Home Decor",
        "desc": "Vintage style warm ambient bedside lighting.",
        "price": 2200.0,
        "mode": "negotiable",
        "asp": 2100.0,
        "target": 1700.0,
        "res": 1500.0,
        "rounds": 4,
        "bulk": {
            "tiers": [
                {"min_quantity": 4, "discount_percentage": 10.0},
                {"min_quantity": 8, "discount_percentage": 15.0}
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_015", "name": "Hand Block Print Cotton Saree", "cat": "Fashion", "desc": "Traditional Jaipur floral print lightweight saree.", "price": 2100.0, "mode": "negotiable", "asp": 2000.0, "target": 1600.0, "res": 1400.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"},

    # 16-20
    {"id": "prod_016", "name": "Artisanal Green Tea Leaves 100g", "cat": "Packaged Goods", "desc": "Darjeeling whole leaf organic green tea.", "price": 350.0, "mode": "fixed", "asp": 350.0, "target": 350.0, "res": 350.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_017", "name": "Wildflower Honey 500g", "cat": "Packaged Goods", "desc": "Raw unprocessed mountain honey.", "price": 190.0, "mode": "fixed", "asp": 190.0, "target": 190.0, "res": 190.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_018", "name": "Men's Wool Blend Blazer", "cat": "Fashion", "desc": "Tailored slim-fit formal party blazer.", "price": 5000.0, "mode": "negotiable", "asp": 4800.0, "target": 3800.0, "res": 3400.0, "rounds": 5, "bulk": None, "scenario": "negotiable"},
    {
        "id": "prod_019",
        "name": "Wooden Wall Clock 14 inch",
        "cat": "Home Decor",
        "desc": "Solid teak wood silent sweep clock.",
        "price": 1600.0,
        "mode": "negotiable",
        "asp": 1500.0,
        "target": 1200.0,
        "res": 1050.0,
        "rounds": 4,
        "bulk": {
            "tiers": [
                {"min_quantity": 6, "discount_percentage": 10.0},
                {"min_quantity": 12, "discount_percentage": 20.0}
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_020", "name": "Casual Denim Trucker Jacket", "cat": "Fashion", "desc": "Classic heavy wash cotton denim outerwear.", "price": 2400.0, "mode": "negotiable", "asp": 2300.0, "target": 1850.0, "res": 1600.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"},

    # 21-25
    {"id": "prod_021", "name": "Gourmet Hazelnut Spread 350g", "cat": "Packaged Goods", "desc": "Rich cocoa & roasted hazelnut butter.", "price": 260.0, "mode": "fixed", "asp": 260.0, "target": 260.0, "res": 260.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_022", "name": "Organic Oat Milk 1L", "cat": "Packaged Goods", "desc": "Unsweetened plant-based barista oat drink.", "price": 210.0, "mode": "fixed", "asp": 210.0, "target": 210.0, "res": 210.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_023", "name": "Handmade Leather Loafers", "cat": "Fashion", "desc": "Italian leather slip-on formal shoes.", "price": 3800.0, "mode": "negotiable", "asp": 3600.0, "target": 2900.0, "res": 2600.0, "rounds": 4, "bulk": None, "scenario": "negotiable"},
    {
        "id": "prod_024",
        "name": "Macrame Wall Hanging Tapestry",
        "cat": "Home Decor",
        "desc": "Boho style woven cotton rope wall art.",
        "price": 1400.0,
        "mode": "negotiable",
        "asp": 1300.0,
        "target": 1000.0,
        "res": 850.0,
        "rounds": 4,
        "bulk": {
            "tiers": [
                {"min_quantity": 5, "discount_percentage": 10.0},
                {"min_quantity": 10, "discount_percentage": 25.0}
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_025", "name": "Chiffon Floral Maxi Dress", "cat": "Fashion", "desc": "Flowy summer floral print long dress.", "price": 1900.0, "mode": "negotiable", "asp": 1800.0, "target": 1450.0, "res": 1250.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"},

    # 26-30
    {"id": "prod_026", "name": "Almond Biscotti Pack 200g", "cat": "Packaged Goods", "desc": "Double-baked crunchy Italian coffee cookies.", "price": 140.0, "mode": "fixed", "asp": 140.0, "target": 140.0, "res": 140.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_027", "name": "Organic Cold-Pressed Orange Juice", "cat": "Packaged Goods", "desc": "100% pure Valencia orange juice 750ml.", "price": 160.0, "mode": "fixed", "asp": 160.0, "target": 160.0, "res": 160.0, "rounds": 0, "bulk": None, "scenario": "fixed"},
    {"id": "prod_028", "name": "Hand-Carved Wooden Jewelry Box", "cat": "Home Decor", "desc": "Sheesham wood brass inlay storage trunk.", "price": 1700.0, "mode": "negotiable", "asp": 1600.0, "target": 1300.0, "res": 1100.0, "rounds": 4, "bulk": None, "scenario": "negotiable"},
    {
        "id": "prod_029",
        "name": "Aromatherapy Soy Candle (Lavender)",
        "cat": "Home Decor",
        "desc": "Hand-poured essential oil scented candle in jar.",
        "price": 850.0,
        "mode": "negotiable",
        "asp": 800.0,
        "target": 650.0,
        "res": 550.0,
        "rounds": 3,
        "bulk": {
            "tiers": [
                {"min_quantity": 5, "discount_percentage": 10.0},
                {"min_quantity": 15, "discount_percentage": 20.0}
            ]
        },
        "scenario": "wholesale"
    },
    {"id": "prod_030", "name": "Handmade Woolen Cardigan", "cat": "Fashion", "desc": "Cozy knit button-down sweater.", "price": 2600.0, "mode": "negotiable", "asp": 2500.0, "target": 2000.0, "res": 1750.0, "rounds": 3, "bulk": None, "scenario": "insufficient_evidence"}
]

for spec in product_specs:
    pid = spec["id"]
    products.append({
        "id": pid,
        "name": spec["name"],
        "description": spec["desc"],
        "listed_price": spec["price"],
        "category": spec["cat"]
    })

    policy = {
        "product_id": pid,
        "pricing_mode": spec["mode"],
        "listed_price": spec["price"],
        "aspiration_price": spec["asp"],
        "target_price": spec["target"],
        "reservation_price": spec["res"],
        "batna": "normal_sale",
        "max_negotiation_rounds": spec["rounds"]
    }
    if spec["bulk"]:
        policy["bulk_rules"] = spec["bulk"]
    else:
        policy["bulk_rules"] = None
    seller_policies.append(policy)

    # Evidence Generation according to scenario with clear, non-deceptive labels
    scenario = spec["scenario"]
    if scenario == "insufficient_evidence":
        # ONLY seller marketing evidence
        add_evidence(pid, "image", "seller_marketing", "Seller catalog photo", f"Studio catalog photo of {spec['name']}.")
        add_evidence(pid, "text", "seller_marketing", "Seller promotional description", f"Seller description highlighting fabric and features of {spec['name']}.")
    elif scenario == "hard_negotiation":
        # Rich multi-source evidence with objective labels
        add_evidence(pid, "image", "seller_marketing", "Seller catalog photo", f"High-resolution catalog photo of {spec['name']}.")
        add_evidence(pid, "video", "seller_reality", "Seller-provided reality video", f"Unedited video clip showing fabric texture and natural lighting view of {spec['name']}.")
        add_evidence(pid, "review", "customer_experience", "Customer review", "Customer review: 'The silk fabric quality is great and matches the video clip accurately.'")
        add_evidence(pid, "image", "customer_experience", "Customer-provided image", f"Customer photo showing {spec['name']} in real-world use.")
    else:
        # Standard evidence coverage
        add_evidence(pid, "image", "seller_marketing", "Seller catalog photo", f"Official studio photo of {spec['name']}.")
        add_evidence(pid, "text", "seller_marketing", "Seller specifications", f"Product specifications for {spec['name']}.")
        add_evidence(pid, "review", "customer_experience", "Customer review", f"Customer review commenting on quality and packaging of {spec['name']}.")
        if spec["mode"] == "negotiable":
            add_evidence(pid, "video", "seller_reality", "Seller reality inspection video", f"Live unboxing video clip showing dimensions and color of {spec['name']}.")

# Write output files
with open(os.path.join(DATA_DIR, "products.json"), "w", encoding="utf-8") as f:
    json.dump(products, f, indent=2)

with open(os.path.join(DATA_DIR, "evidence.json"), "w", encoding="utf-8") as f:
    json.dump(evidence, f, indent=2)

with open(os.path.join(DATA_DIR, "seller_policies.json"), "w", encoding="utf-8") as f:
    json.dump(seller_policies, f, indent=2)

print(f"Generated {len(products)} products, {len(evidence)} evidence records, and {len(seller_policies)} seller policies successfully.")

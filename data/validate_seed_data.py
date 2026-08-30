import json
import os
import sys
from decimal import Decimal

# Add backend directory to sys.path to import Pydantic models from app.models
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.models import Product, Evidence, SellerPolicy


def validate_seed_data():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    products_file = os.path.join(data_dir, "products.json")
    evidence_file = os.path.join(data_dir, "evidence.json")
    policies_file = os.path.join(data_dir, "seller_policies.json")

    print("Loading JSON seed data files...")

    with open(products_file, "r", encoding="utf-8") as f:
        products_raw = json.load(f)

    with open(evidence_file, "r", encoding="utf-8") as f:
        evidence_raw = json.load(f)

    with open(policies_file, "r", encoding="utf-8") as f:
        policies_raw = json.load(f)

    print(f"Loaded {len(products_raw)} products, {len(evidence_raw)} evidence records, and {len(policies_raw)} seller policies.\n")
    print("Beginning Validation Checks (Decimal Precision & Multi-tier Bulk Rules)...\n")

    # 1. Product IDs uniqueness & Pydantic Decimal Validation
    product_ids = set()
    validated_products = []
    for idx, p in enumerate(products_raw, 1):
        if p["id"] in product_ids:
            raise ValueError(f"Duplicate Product ID found: {p['id']}")
        product_ids.add(p["id"])
        model_p = Product(**p)
        if not isinstance(model_p.listed_price, Decimal):
            raise TypeError(f"Product listed_price is not Decimal: {type(model_p.listed_price)}")
        validated_products.append(model_p)
    print(f"[PASS] Check 1 & 5: All {len(validated_products)} products parsed and validated against Pydantic Decimal model.")

    # 2. Evidence IDs uniqueness, Pydantic Validation & Foreign Key Check
    evidence_ids = set()
    evidence_sources_count = {"seller_marketing": 0, "seller_reality": 0, "customer_experience": 0}
    validated_evidence = []
    for e in evidence_raw:
        if e["id"] in evidence_ids:
            raise ValueError(f"Duplicate Evidence ID found: {e['id']}")
        evidence_ids.add(e["id"])

        if e["product_id"] not in product_ids:
            raise ValueError(f"Evidence {e['id']} references non-existent product_id: {e['product_id']}")

        model_e = Evidence(**e)
        validated_evidence.append(model_e)
        evidence_sources_count[model_e.source] += 1

    print(f"[PASS] Check 2, 3 & 6: All {len(validated_evidence)} evidence records validated (IDs unique, product_id foreign keys valid).")
    print(f"       Evidence Distribution by Source: {evidence_sources_count}")

    # 3. Seller Policies Pydantic Validation & Foreign Key Check
    policy_product_ids = set()
    validated_policies = []
    fixed_count = 0
    negotiable_count = 0
    bulk_rule_count = 0

    for pol in policies_raw:
        pid = pol["product_id"]
        if pid in policy_product_ids:
            raise ValueError(f"Duplicate Seller Policy for product_id: {pid}")
        policy_product_ids.add(pid)

        if pid not in product_ids:
            raise ValueError(f"Seller Policy references non-existent product_id: {pid}")

        model_pol = SellerPolicy(**pol)
        validated_policies.append(model_pol)

        if model_pol.pricing_mode == "fixed":
            fixed_count += 1
        else:
            negotiable_count += 1

        if model_pol.bulk_rules is not None:
            bulk_rule_count += 1

    print(f"[PASS] Check 4, 7, 8, 9 & 10: All {len(validated_policies)} seller policies validated.")
    print(f"       Pricing modes: {fixed_count} Fixed, {negotiable_count} Negotiable.")
    print(f"       Multi-tier bulk rules configured: {bulk_rule_count} products (all tiers Decimal floor-checked >= reservation_price).")

    # Scenario Coverage Summary
    print("\n--- Scenario Coverage Report ---")
    print(f"  Fixed Pricing Products: {fixed_count}")
    print(f"  Negotiable Pricing Products: {negotiable_count}")
    print(f"  Products with Bulk Tiers: {bulk_rule_count}")
    print(f"  Products without Bulk Tiers: {len(validated_policies) - bulk_rule_count}")
    print(f"  Seller Marketing Evidence Records: {evidence_sources_count['seller_marketing']}")
    print(f"  Seller Reality Evidence Records: {evidence_sources_count['seller_reality']}")
    print(f"  Customer Experience Evidence Records: {evidence_sources_count['customer_experience']}")

    print("\n[SUCCESS] ALL SEED DATA VALIDATION CHECKS PASSED SUCCESSFULLY!\n")


if __name__ == "__main__":
    validate_seed_data()

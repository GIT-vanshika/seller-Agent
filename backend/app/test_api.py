import json
import urllib.request
import urllib.error
from fastapi.testclient import TestClient
from app.main import app

BASE_URL = "http://127.0.0.1:8000"

PRIVATE_FIELD_KEYWORDS = [
    "reservation_price",
    "target_price",
    "aspiration_price",
    "batna",
    "max_negotiation_rounds",
    "bulk_rules",
]

test_client = TestClient(app)


def fetch_url(url: str):
    # Try live HTTP request first, fallback to TestClient if server is offline
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1.0) as response:
            status_code = response.getcode()
            body_bytes = response.read()
            body_str = body_bytes.decode("utf-8")
            return status_code, body_str
    except Exception:
        path = url.replace(BASE_URL, "")
        res = test_client.get(path)
        return res.status_code, res.text


def run_api_tests():
    print("Running FastAPI Public API & Security Tests...\n")

    # 1. Health endpoint test
    code, body = fetch_url(f"{BASE_URL}/health")
    assert code == 200, f"Expected 200, got {code}"
    assert json.loads(body) == {"status": "ok"}
    print("[PASS] Test 1: GET /health returned 200 OK.")

    # 2. GET /products endpoint test
    code, body = fetch_url(f"{BASE_URL}/products")
    assert code == 200, f"Expected 200, got {code}"
    data = json.loads(body)
    assert "products" in data
    products = data["products"]
    assert len(products) == 30, f"Expected 30 products, got {len(products)}"
    product_ids = [p["id"] for p in products]
    assert len(set(product_ids)) == 30, "Product IDs are not unique"
    print(f"[PASS] Test 2: GET /products returned 200 OK with {len(products)} unique products.")

    # 3. GET /products/prod_003 endpoint test
    code, body = fetch_url(f"{BASE_URL}/products/prod_003")
    assert code == 200, f"Expected 200, got {code}"
    detail = json.loads(body)
    assert "product" in detail and "evidence" in detail
    prod = detail["product"]
    evidence_list = detail["evidence"]
    assert prod["id"] == "prod_003"
    assert prod["name"] == "Silk Designer Dress"
    assert len(evidence_list) == 4, f"Expected 4 evidence items for prod_003, got {len(evidence_list)}"

    for ev in evidence_list:
        assert ev["product_id"] == "prod_003", f"Evidence product_id mismatch: {ev['product_id']}"
        assert ev["source"] in ["seller_marketing", "seller_reality", "customer_experience"]
        assert "verified customer" not in ev["label"].lower()
    print(f"[PASS] Test 3: GET /products/prod_003 returned 200 OK with {len(evidence_list)} matching evidence items.")

    # 4. GET /products/does_not_exist 404 test
    code, body = fetch_url(f"{BASE_URL}/products/does_not_exist")
    assert code == 404, f"Expected 404, got {code}"
    err_json = json.loads(body)
    assert err_json == {"detail": "Product not found"}
    print("[PASS] Test 4: GET /products/does_not_exist correctly returned 404 Not Found.")

    # 5. CRITICAL SECURITY TEST 1: Serialized HTTP JSON check for prod_003
    code_003, raw_json_003 = fetch_url(f"{BASE_URL}/products/prod_003")
    for kw in PRIVATE_FIELD_KEYWORDS:
        assert kw not in raw_json_003, f"SECURITY VIOLATION: Private keyword '{kw}' found in prod_003 HTTP response!"
    print("[PASS] Test 5: Mandatory Security Check 1 passed! Raw HTTP response for prod_003 contains ZERO private SellerPolicy fields.")

    # 6. CRITICAL SECURITY TEST 2: Serialized HTTP JSON check for /products
    code_all, raw_json_all = fetch_url(f"{BASE_URL}/products")
    for kw in PRIVATE_FIELD_KEYWORDS:
        assert kw not in raw_json_all, f"SECURITY VIOLATION: Private keyword '{kw}' found in /products HTTP response!"
    print("[PASS] Test 6: Mandatory Security Check 2 passed! Raw HTTP response for /products contains ZERO private SellerPolicy fields.")

    print("\n[SUCCESS] ALL PUBLIC API AND SECURITY TESTS PASSED CLEANLY!\n")


if __name__ == "__main__":
    run_api_tests()

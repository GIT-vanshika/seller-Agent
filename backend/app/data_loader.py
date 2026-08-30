import json
from pathlib import Path
from typing import Dict, List, Optional
from app.models import Product, Evidence, SellerPolicy


class DataLoader:
    def __init__(self):
        self.products: Dict[str, Product] = {}
        self.evidence_by_product: Dict[str, List[Evidence]] = {}
        self.seller_policies: Dict[str, SellerPolicy] = {}
        self._load_data()

    def _find_data_dir(self) -> Path:
        # Check relative to app directory
        current_file = Path(__file__).resolve()
        
        # Candidate 1: seller-Agent/data
        cand1 = current_file.parent.parent.parent / "data"
        if cand1.exists() and (cand1 / "products.json").exists():
            return cand1

        # Candidate 2: seller-Agent/backend/data
        cand2 = current_file.parent.parent / "data"
        if cand2.exists() and (cand2 / "products.json").exists():
            return cand2

        # Candidate 3: relative CWD / data
        cand3 = Path.cwd() / "data"
        if cand3.exists() and (cand3 / "products.json").exists():
            return cand3

        cand4 = Path.cwd().parent / "data"
        if cand4.exists() and (cand4 / "products.json").exists():
            return cand4

        raise FileNotFoundError("Could not locate data directory containing products.json")

    def _load_data(self):
        data_dir = self._find_data_dir()
        
        # Load products
        with open(data_dir / "products.json", "r", encoding="utf-8") as f:
            raw_products = json.load(f)
            for p in raw_products:
                model_p = Product(**p)
                self.products[model_p.id] = model_p

        # Load evidence
        with open(data_dir / "evidence.json", "r", encoding="utf-8") as f:
            raw_evidence = json.load(f)
            for e in raw_evidence:
                model_e = Evidence(**e)
                if model_e.product_id not in self.evidence_by_product:
                    self.evidence_by_product[model_e.product_id] = []
                self.evidence_by_product[model_e.product_id].append(model_e)

        # Load seller policies
        with open(data_dir / "seller_policies.json", "r", encoding="utf-8") as f:
            raw_policies = json.load(f)
            for pol in raw_policies:
                model_pol = SellerPolicy(**pol)
                self.seller_policies[model_pol.product_id] = model_pol

    def get_all_products(self) -> List[Product]:
        return list(self.products.values())

    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def get_evidence_for_product(self, product_id: str) -> List[Evidence]:
        return self.evidence_by_product.get(product_id, [])

    def get_seller_policy(self, product_id: str) -> Optional[SellerPolicy]:
        return self.seller_policies.get(product_id)


# Global singleton instance for in-memory serving
db = DataLoader()


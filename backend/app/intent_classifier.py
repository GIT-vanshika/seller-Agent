import re
from typing import Optional, Tuple
from decimal import Decimal
from pydantic import BaseModel


class IntentResult(BaseModel):
    intent: str  # "trust_hesitation", "price_hesitation", "bulk_request", "checkout_intent", "general_inquiry"
    offered_price: Optional[Decimal] = None
    requested_quantity: Optional[int] = None
    confidence: float = 1.0


class IntentClassifier:
    """
    Deterministic & Pattern-based Intent Classifier.
    Categorizes buyer inputs into trust hesitation, price negotiation, bulk inquiry, or checkout commitment.
    Extracts numerical price offers and bulk quantities.
    """

    PRICE_PATTERNS = [
        r"(?:for|at|give|offer|how about|pay|take|buy for|is)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d{1,2})?)",
        r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(?:rs\.?|rupees|inr)",
    ]

    QTY_PATTERNS = [
        r"(\d+)\s*(?:pieces|units|pcs|items|qty|quantity|pack|packs)",
        r"(?:buy|need|want|take|order)\s*(\d+)",
    ]

    TRUST_KEYWORDS = [
        "quality", "real", "authentic", "fabric", "material", "photo", "picture",
        "video", "review", "durability", "genuine", "original", "guarantee", "warranty",
        "trust", "fake", "scam", "proof", "unboxing", "see"
    ]

    CHECKOUT_KEYWORDS = [
        "buy now", "checkout", "place order", "pay now", "proceed to pay", "confirm deal",
        "ready to buy", "i'll take it", "ill take it", "done deal", "accept", "agreed"
    ]

    BULK_KEYWORDS = [
        "bulk", "wholesale", "quantity", "multiple", "discount for 5", "discount for 10",
        "more units", "pieces", "volume"
    ]

    PRICE_KEYWORDS = [
        "discount", "lower", "cheap", "costly", "expensive", "best price", "best deal",
        "reduce", "negotiate", "less", "offer", "budget", "lowest", "lowest price",
        "bottom", "bottom price", "final price", "last price", "how low", "what can you do",
        "can you reduce", "can you lower", "cheaper", "price negotiable", "floor price", "minimum"
    ]

    @classmethod
    def extract_price_and_qty(cls, text: str) -> Tuple[Optional[Decimal], Optional[int]]:
        text_lower = text.lower()
        extracted_price = None
        extracted_qty = None

        for pat in cls.QTY_PATTERNS:
            match = re.search(pat, text_lower)
            if match:
                try:
                    val = int(match.group(1))
                    if 1 <= val <= 1000:
                        extracted_qty = val
                        break
                except ValueError:
                    pass

        for pat in cls.PRICE_PATTERNS:
            match = re.search(pat, text_lower)
            if match:
                try:
                    val = Decimal(match.group(1))
                    if val > 0 and val != extracted_qty:
                        extracted_price = val
                        break
                except Exception:
                    pass

        return extracted_price, extracted_qty

    @classmethod
    def classify(cls, user_text: str) -> IntentResult:
        text_lower = user_text.lower().strip()
        price, qty = cls.extract_price_and_qty(user_text)

        # 1. Checkout Intent
        if any(kw in text_lower for kw in cls.CHECKOUT_KEYWORDS):
            return IntentResult(
                intent="checkout_intent",
                offered_price=price,
                requested_quantity=qty or 1,
                confidence=0.95,
            )

        # 2. Bulk Quantity Request
        if (qty and qty > 1) or any(kw in text_lower for kw in cls.BULK_KEYWORDS):
            return IntentResult(
                intent="bulk_request",
                offered_price=price,
                requested_quantity=qty or 5,
                confidence=0.90,
            )

        # 3. Price Hesitation / Negotiation
        if price is not None or any(kw in text_lower for kw in cls.PRICE_KEYWORDS):
            return IntentResult(
                intent="price_hesitation",
                offered_price=price,
                requested_quantity=qty or 1,
                confidence=0.90,
            )

        # 4. Trust Hesitation
        if any(kw in text_lower for kw in cls.TRUST_KEYWORDS):
            return IntentResult(
                intent="trust_hesitation",
                offered_price=price,
                requested_quantity=qty or 1,
                confidence=0.85,
            )

        # 5. Default General Inquiry
        return IntentResult(
            intent="general_inquiry",
            offered_price=price,
            requested_quantity=qty or 1,
            confidence=0.70,
        )

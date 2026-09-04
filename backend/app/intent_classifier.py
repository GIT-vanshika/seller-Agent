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
    Extracts numerical price offers and bulk quantities with conversational multi-turn context awareness.
    """

    NON_PRICE_UNITS = [
        "%", "percent", "percentage",
        "color", "colors", "colour", "colours",
        "size", "sizes",
        "photo", "photos", "picture", "pictures", "pic", "pics", "image", "images",
        "video", "videos", "clip", "clips",
        "review", "reviews", "star", "stars", "rating", "ratings",
        "day", "days", "month", "months", "year", "years", "week", "weeks", "hour", "hours",
        "warranty", "guarantee",
        "question", "questions", "option", "options",
    ]

    PRICE_PATTERNS = [
        # Explicit offer prefixes with strict word boundaries
        r"\b(?:for|at|give(?:\s+it)?(?:\s+for)?|offer(?:\s+of)?|how\s+about|what\s+about|pay|i\'?ll\s+pay|i\s+can\s+pay|i\'?ll\s+do|i\s+can\s+do|take|buy\s+for|is|under|below|around|within|max|ok(?:\s+then)?|okay(?:\s+then)?|then|make\s+it|i\s+want(?:\s+it)?|want(?:\s+it)?|can\s+you\s+do|can\s+i\s+get(?:\s+it)?(?:\s+for|\s+under|\s+at)?|can\s+you\s+give(?:\s+it)?(?:\s+for)?|can\s+you\s+make\s+it|could\s+you\s+do)\b\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d{1,2})?)(?!\s*(?:%|percent|percentage))",
        # Currency prefixes
        r"(?:rs\.?|inr|₹)\s*(\d+(?:\.\d{1,2})?)(?!\s*(?:%|percent|percentage))",
        # Suffix patterns indicating an offer or price
        r"(\d+(?:\.\d{1,2})?)\s*(?:rs\.?|rupees|inr|bucks|final(?:\s+offer)?|last(?:\s+price|\s+offer)?|is\s+my\s+(?:final\s+)?offer|is\s+my\s+(?:last\s+)?price|per\s+unit|per\s+piece|each|for\s+(?:one|\d+|each)|if\s+i\s+take)",
        # Standalone numbers or ok + number (e.g. '1800', '1800?', 'ok 1800', '1750 final')
        r"^\s*(?:ok(?:ay)?\s*,?\s*(?:then\s*)?)?(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d{1,2})?)\s*(?:final|only|last)?\s*[?.!]?\s*$",
    ]

    WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    QTY_PATTERNS = [
        r"(\d+)\s*(?:pieces?|units?|pcs|items?|qty|quantity|packs?|piece|unit|item|pack)",
        r"\b(?:buy|need|order|take|want|get)\s+(\d+)\b",
        r"\b(?:what\s+about|how\s+about|what\s+if\s+i\s+take|if\s+i\s+take|if\s+i\s+buy)\s+(\d+)\b",
        r"\b(?:for)\s+(\d+)(?:\s*(?:pieces?|units?|pcs|items?))?\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:pieces?|units?|pcs|items?|piece|unit|item)\b",
        r"\b(?:buy|need|order|take|want|get)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"\b(?:what\s+about|how\s+about|what\s+if\s+i\s+take|if\s+i\s+take|if\s+i\s+buy)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"\b(?:for)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
    ]

    ACCEPTANCE_PATTERNS = [
        r"^\s*(?:ok(?:ay)?\s*,?\s*)?(?:done|deal|agreed|agree)\s*[.!]?$",
        r"^\s*(?:i\'?ll\s+take\s+it|take\s+it|yes,?\s+let\'?s\s+do\s+it|let\'?s\s+do\s+it|okay,?\s+i\'?ll\s+take\s+it|ok,?\s+i\'?ll\s+take\s+it)\s*[.!]?$",
        r"\b(?:ok(?:ay)?\s*,?\s*)?(?:i\s+)?(?:want\s+to\s+buy|want\s+to\s+purchase|will\s+buy|ready\s+to\s+buy|ready\s+to\s+purchase)\b",
        r"\b(?:done deal|confirm deal|i\'?ll\s+take\s+it|let\'?s\s+do\s+it|ready\s+to\s+buy|buy\s+now|pay\s+now|proceed\s+to\s+pay|lock\s+the\s+deal)\b",
        r"\b(?:confident|convinced|sound[s]?\s+good|sound[s]?\s+great|perfect),?\s*(?:i\s+)?(?:want\s+to\s+buy|let\'?s\s+buy|i\'?ll\s+buy|deal|buy)\b",
    ]

    PAYMENT_INQUIRY_PATTERNS = [
        r"\bwhere\s+(?:to\s+)?(?:to\s+)?pay(?:\s+for\s+it)?\b",
        r"\bwhere\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|make\s+payment|checkout)\b",
        r"\bhow\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|make\s+payment|checkout)\b",
        r"\b(?:payment\s+link|link\s+to\s+pay|where\s+is\s+(?:the\s+)?payment(?:\s+link|\s+option)?)\b",
        r"\bwhere\s+(?:can|do|to)\s+i\s+complete\s+payment\b",
    ]

    EXPLICIT_BUY_PATTERNS = [
        r"\b(?:want\s+to\s+buy|want\s+to\s+purchase|ready\s+to\s+buy|ready\s+to\s+purchase|will\s+buy)\b",
        r"\bwhere\s+(?:to\s+)?(?:to\s+)?pay\b",
        r"\bwhere\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|checkout)\b",
        r"\bhow\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|checkout)\b",
    ]

    TRUST_KEYWORDS = [
        "quality", "real", "authentic", "fabric", "material", "photo", "picture",
        "video", "review", "durability", "genuine", "original", "guarantee", "warranty",
        "trust", "fake", "scam", "proof", "unboxing", "see", "care", "wash", "size", "fit",
    ]

    CHECKOUT_KEYWORDS = [
        "buy now", "checkout", "place order", "pay now", "proceed to pay", "confirm deal",
        "ready to buy", "i'll take it", "ill take it", "done deal", "accept", "agreed",
        "where can i pay", "where do i pay", "how can i pay", "how do i pay", "where to pay",
        "i want to buy", "i want to purchase", "want to buy", "ready to purchase",
    ]

    BULK_KEYWORDS = [
        "bulk", "wholesale", "bulk order", "bulk discount", "volume discount",
        "wholesale price", "large order", "commercial order",
    ]

    PRICE_KEYWORDS = [
        "discount", "lower", "cheap", "costly", "expensive", "best price", "best deal",
        "reduce", "negotiate", "less", "offer", "budget", "lowest", "lowest price",
        "bottom", "bottom price", "final price", "last price", "how low", "what can you do",
        "can you reduce", "can you lower", "cheaper", "price negotiable", "floor price", "minimum",
        "under", "below", "within", "around", "max", "affordable",
    ]

    @classmethod
    def is_acceptance(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        for pat in cls.ACCEPTANCE_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def is_payment_inquiry(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        for pat in cls.PAYMENT_INQUIRY_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def is_explicit_buy(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        for pat in cls.EXPLICIT_BUY_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def extract_price_and_qty(cls, text: str, in_negotiation: bool = False) -> Tuple[Optional[Decimal], Optional[int]]:
        text_lower = text.lower().strip().replace("’", "'")
        extracted_price = None
        extracted_qty = None

        # 1. Non-price unit guard (e.g. '3 colors', '3 sizes', '2 photos', '100%')
        has_currency_or_price_kw = bool(re.search(r"(?:rs\.?|inr|₹|rupees|discount|price|offer|pay|under|below)", text_lower))
        non_price_pat = r"\b(\d+)\s*(?:%|percent|percentage|colors?|colours?|sizes?|photos?|pictures?|pics?|images?|videos?|clips?|reviews?|stars?|ratings?|days?|months?|years?|weeks?|hours?|warranty|guarantee)\b"
        non_price_match = re.search(non_price_pat, text_lower)
        if non_price_match and not has_currency_or_price_kw:
            # The number in this sentence is associated with non-monetary attributes (specs/options/percentage)
            return None, None

        # 2. Extract quantity
        for pat in cls.QTY_PATTERNS:
            match = re.search(pat, text_lower)
            if match:
                raw_val = match.group(1).lower()
                try:
                    if raw_val in cls.WORD_TO_NUM:
                        val = cls.WORD_TO_NUM[raw_val]
                    else:
                        val = int(raw_val)
                    if 1 <= val <= 1000:
                        # Guard: If number is followed by price suffixes, don't treat as qty
                        if not re.search(r"\b" + re.escape(raw_val) + r"\s*(?:rs|rupees|inr|final|per|each|only)", text_lower):
                            extracted_qty = val
                            break
                except ValueError:
                    pass

        # 3. Extract price using defined patterns
        for pat in cls.PRICE_PATTERNS:
            for match in re.finditer(pat, text_lower):
                try:
                    val = Decimal(match.group(1))
                    if val > 0 and val != extracted_qty:
                        extracted_price = val
                        break
                except Exception:
                    pass
            if extracted_price is not None:
                break

        # 4. Contextual fallback: If in active negotiation and price wasn't matched yet
        if extracted_price is None and in_negotiation:
            any_num = re.findall(r"\b(\d+(?:\.\d{1,2})?)\b", text_lower)
            for n in any_num:
                val = Decimal(n)
                if val > 10 and val != extracted_qty:
                    # Check not followed by a non-price unit
                    np_check = r"\b" + n + r"\s*(?:colors?|colours?|sizes?|photos?|pictures?|pics?|images?|videos?|clips?|reviews?|stars?|ratings?|days?|months?|years?|weeks?|hours?)\b"
                    if not re.search(np_check, text_lower):
                        extracted_price = val
                        break

        return extracted_price, extracted_qty

    @classmethod
    def classify(
        cls,
        user_text: str,
        in_negotiation: bool = False,
        current_negotiated_price: Optional[Decimal] = None,
        listed_price: Optional[Decimal] = None,
    ) -> IntentResult:
        text_lower = user_text.lower().strip().replace("’", "'")

        # 1. Extract price & quantity with session context
        price, qty = cls.extract_price_and_qty(user_text, in_negotiation=in_negotiation)

        # 2. Acceptance / Deal Closure Detection
        if cls.is_acceptance(text_lower) or cls.is_payment_inquiry(text_lower) or any(kw in text_lower for kw in cls.CHECKOUT_KEYWORDS):
            return IntentResult(
                intent="checkout_intent",
                offered_price=None,
                requested_quantity=qty,
                confidence=0.95,
            )

        # 3. Bulk Quantity Request
        if (qty and qty > 1) or any(kw in text_lower for kw in cls.BULK_KEYWORDS):
            return IntentResult(
                intent="bulk_request",
                offered_price=price,
                requested_quantity=qty or 5,
                confidence=0.90,
            )

        # 4. Price Hesitation / Negotiation (including quantity adjustments during negotiation)
        if price is not None or any(kw in text_lower for kw in cls.PRICE_KEYWORDS) or (in_negotiation and (price is not None or qty is not None)):
            return IntentResult(
                intent="price_hesitation",
                offered_price=price,
                requested_quantity=qty,
                confidence=0.90,
            )

        # 5. Trust Hesitation
        if any(kw in text_lower for kw in cls.TRUST_KEYWORDS):
            return IntentResult(
                intent="trust_hesitation",
                offered_price=price,
                requested_quantity=qty,
                confidence=0.85,
            )

        # 6. Default General Inquiry
        return IntentResult(
            intent="general_inquiry",
            offered_price=price,
            requested_quantity=qty,
            confidence=0.70,
        )

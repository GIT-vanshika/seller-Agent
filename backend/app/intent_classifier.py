import re
from typing import Optional, Tuple
from decimal import Decimal
from pydantic import BaseModel

from app.contracts import BuyerIntentDecision, ProductQuestion


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
        # Explicit offer prefixes with strict word boundaries (exclude if followed by unit words)
        r"\b(?:for|at|give(?:\s+it)?(?:\s+for)?|offer(?:\s+of)?|how\s+about|what\s+about|pay|i\'?ll\s+pay|i\s+can\s+pay|i\'?ll\s+do|i\s+can\s+do|take|buy\s+for|is|under|below|around|within|max|ok(?:\s+then)?|okay(?:\s+then)?|then|make\s+it|i\s+want(?:\s+it)?|want(?:\s+it)?|can\s+you\s+do|could\s+you\s+do|if\s+you\s+can\s+do|if\s+you\s+could\s+do|you\s+can\s+do|you\s+could\s+do|do|can\s+i\s+get(?:\s+it)?(?:\s+for|\s+under|\s+at)?|can\s+you\s+give(?:\s+it)?(?:\s+for)?|can\s+you\s+make\s+it)\b\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d{1,2})?)(?!\s*(?:%|percent|percentage|pieces?|units?|pcs|items?|qty|quantity|packs?|piece|unit|item|pack))",
        # Reference to previously stated or promised price (e.g. 'you said ok for 900', 'said 900', 'agreed for 900')
        r"\b(?:you\s+said|said|offered|agreed(?:\s+to|\s+on)?|mentioned|promised)(?:\s+ok)?(?:\s+for)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d{1,2})?)",
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
        # Explicit unit suffixes (always valid quantity)
        r"(\d+)\s*(?:pieces?|units?|pcs|items?|qty|quantity|packs?|piece|unit|item|pack)\b",
        r"\b(?:quantity|qty)\s*[:=]?\s*(\d+)\b",
        # Implicit quantities: small numbers only (<= 50)
        r"\b(?:buy|need|order|take|want|get)\s+(\d+)\b",
        r"\b(?:what\s+about|how\s+about|what\s+if\s+i\s+take|if\s+i\s+take|if\s+i\s+buy)\s+(\d+)\b",
        r"\b(?:how\s+much\s+for)\s+(\d+)\b",
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:pieces?|units?|pcs|items?|piece|unit|item)\b",
        r"\b(?:buy|need|order|take|want|get)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"\b(?:what\s+about|how\s+about|what\s+if\s+i\s+take|if\s+i\s+take|if\s+i\s+buy)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        r"\b(?:how\s+much\s+for)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\b",
        # Hinglish quantity patterns
        r"(\d+)\s*(?:log|loge|le|lenge|piece|pieces|unit|units|pcs)\b",
        r"(\d+)\s*ke\s*(?:liye|wastay|kitna|rate)\b",
        r"(\d+)\s*(?:ka|ke)\s*kitna\b",
    ]

    ACCEPTANCE_PATTERNS = [
        r"^\s*(?:ok(?:ay)?\s*,?\s*)?(?:done|deal|agreed|agree)\s*[.!]?$",
        r"^\s*(?:ok(?:ay)?\s*,?\s*)?(?:yes|yeah|yep|sure|proceed|confirm)\s*[.!]?$",
        r"\b(?:i\'?ll\s+take\s+it|i\s+will\s+take\s+it|take\s+it|yes,?\s+let\'?s\s+do\s+it|let\'?s\s+do\s+it|okay,?\s+i\'?ll\s+take\s+it|ok,?\s+i\'?ll\s+take\s+it)\b",
        r"\b(?:let\'?s\s+go\s+ahead|let\s+us\s+go\s+ahead|go\s+ahead|proceed\s+with\s+(?:the\s+)?order|proceed\s+with\s+(?:the\s+)?deal)\b",
        r"\b(?:yes,?\s*)?(?:i\'?ll|i\s+will)\s+(?:take|buy)\s+(?:all\s+)?(?:\d+|both|all|them|it|one|1)\b",
        r"\b(?:take|buy)\s+all\s+\d+\b",
        r"\b(?:ok(?:ay)?\s*,?\s*)?(?:i\s+)?(?:want\s+to\s+buy|want\s+to\s+purchase|will\s+buy|ready\s+to\s+buy|ready\s+to\s+purchase)\b",
        r"\b(?:done deal|confirm deal|i\'?ll\s+take\s+it|let\'?s\s+do\s+it|ready\s+to\s+buy|buy\s+now|pay\s+now|proceed\s+to\s+pay|lock\s+the\s+deal|lock\s+it\s+in|lock\s+this\s+deal)\b",
        r"\b(?:confident|convinced|sound[s]?\s+good|sound[s]?\s+great|perfect),?\s*(?:i\s+)?(?:want\s+to\s+buy|let\'?s\s+buy|i\'?ll\s+buy|deal|buy)\b",
        # Hinglish acceptance
        r"\b(?:haan\s+(?:le\s+lunga|pack\s+kar\s+do|theek\s+hai|deal\s+done)|theek\s+hai\s+pack\s+kar\s+do|le\s+raha\s+hu)\b",
    ]

    PAYMENT_INQUIRY_PATTERNS = [
        r"\bwhere\s+(?:to\s+)?(?:to\s+)?pay(?:\s+for\s+it)?\b",
        r"\bwhere\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|make\s+payment|checkout)\b",
        r"\bhow\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|make\s+payment|checkout)\b",
        r"\b(?:payment\s+link|link\s+to\s+pay|where\s+is\s+(?:the\s+)?payment(?:\s+link|\s+option)?)\b",
        r"\bsend\s+(?:me\s+)?(?:the\s+)?payment\s+link\b",
        r"\bwhere\s+(?:can|do|to)\s+i\s+complete\s+payment\b",
        r"\b(?:proceed\s+to\s+payment|proceed\s+to\s+pay|ready\s+to\s+pay|pay\s+now)\b",
    ]

    EXPLICIT_BUY_PATTERNS = [
        r"\b(?:want\s+to\s+buy|want\s+to\s+purchase|ready\s+to\s+buy|ready\s+to\s+purchase|will\s+buy)\b",
        r"\bwhere\s+(?:to\s+)?(?:to\s+)?pay\b",
        r"\bwhere\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|checkout)\b",
        r"\bhow\s+(?:can|do|should|to)\s+(?:i\s+)?(?:pay|checkout)\b",
        r"\b(?:i\'?ll\s+take\s+it|i\s+will\s+take\s+it|let\'?s\s+go\s+ahead|send\s+payment\s+link|proceed\s+to\s+payment)\b",
    ]

    CONDITIONAL_PATTERNS = [
        r"\b(?:but|however|though|although)\b",
        r"\b(?:if\s+you\s+can|if\s+possible|if\s+you\s+could|can\s+i\s+get|can\s+you\s+do|can\s+you\s+give|can\s+you\s+make|could\s+you)\b",
        r"\b(?:too\s+expensive|too\s+costly|too\s+high|costly|expensive|cheaper|less|lower|discount|reduce)\b",
        r"\b(?:under|below|around|within|budget)\b",
    ]

    TRUST_KEYWORDS = [
        "quality", "real", "authentic", "fabric", "material", "photo", "picture",
        "video", "review", "durability", "genuine", "original", "guarantee", "warranty",
        "trust", "fake", "scam", "proof", "unboxing", "see", "care", "wash", "size", "fit",
    ]

    CHECKOUT_KEYWORDS = [
        "buy now", "checkout", "place order", "pay now", "proceed to pay", "confirm deal",
        "ready to buy", "i'll take it", "ill take it", "i will take it", "done deal", "accept", "agreed",
        "where can i pay", "where do i pay", "how can i pay", "how do i pay", "where to pay",
        "i want to buy", "i want to purchase", "want to buy", "ready to purchase",
        "let's go ahead", "let us go ahead", "send payment link", "proceed to payment",
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
    def is_deliberation(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        return bool(re.search(r"\b(?:think\s+about\s+it|let\s+you\s+know|let\s+me\s+think|need\s+to\s+think|will\s+think)\b", text_clean))

    @classmethod
    def is_conditional(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        for pat in cls.CONDITIONAL_PATTERNS:
            if re.search(pat, text_clean):
                return True
        # Buy phrases accompanied by price offers or question marks are negotiation offers, not acceptance!
        if re.search(r"(?:want\s+to\s+buy|ready\s+to\s+buy|will\s+buy|buy).*?[?,]\s*(?:rs\.?|inr|₹)?\s*\d+", text_clean):
            return True
        if re.search(r"(?:want\s+to\s+buy|ready\s+to\s+buy|will\s+buy|buy)\b.*?\?", text_clean):
            return True
        return False

    @classmethod
    def is_acceptance(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        if cls.is_deliberation(text_clean):
            return False
        if cls.is_conditional(text_clean):
            return False
        for pat in cls.ACCEPTANCE_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def is_payment_inquiry(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        if cls.is_deliberation(text_clean):
            return False
        if cls.is_conditional(text_clean):
            return False
        for pat in cls.PAYMENT_INQUIRY_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def is_explicit_buy(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        if cls.is_deliberation(text_clean):
            return False
        if cls.is_conditional(text_clean):
            return False
        for pat in cls.EXPLICIT_BUY_PATTERNS:
            if re.search(pat, text_clean):
                return True
        return False

    @classmethod
    def is_savings_query(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        return bool(re.search(r"\b(?:how\s+much\s+(?:am\s+i|do\s+i|would\s+i)?\s*sav(?:e|ing)|savings?|discount\s+amount|how\s+much\s+saving|save\s+compared|saving\s+compared)\b", text_clean))

    @classmethod
    def classify_media_intent(cls, text: str) -> str:
        text_clean = text.lower().strip().replace("’", "'")
        if re.search(r"\b(?:look\s+like|looks\s+like|look\s+in\s+real)\b", text_clean):
            return "PRODUCT_DETAIL"
        has_photo = bool(re.search(r"\b(?:photo|photos|picture|pictures|pic|pics|image|images)\b", text_clean))
        has_video = bool(re.search(r"\b(?:video|videos|clip|clips|footage)\b", text_clean))
        if has_photo and has_video:
            return "PRODUCT_PHOTO_VIDEO"
        if has_photo:
            return "PRODUCT_PHOTO"
        if has_video:
            return "PRODUCT_VIDEO"
        return "PRODUCT_DETAIL"

    @classmethod
    def is_product_question(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        if cls.is_deliberation(text_clean) or cls.is_acceptance(text_clean) or cls.is_payment_inquiry(text_clean) or cls.is_savings_query(text_clean):
            return False
        # If user explicitly offers a price or negotiates discount, it's not purely a product question
        if any(k in text_clean for k in ["discount", "kam karo", "best price", "cheaper", "lower"]) and bool(re.search(r"\d+", text_clean)):
            return False

        product_kws = [
            # Durability & Quality
            "quality", "durable", "durability", "last long", "lifespan", "stitching", "craftsmanship", "tear", "wear", "finish", "hold up",
            # Material & Fabric
            "material", "fabric", "silk", "cotton", "linen", "pure", "genuine", "authentic", "real silk", "zari",
            # Care & Wash
            "wash", "care", "iron", "clean", "dry clean", "laundry",
            # Specs & Sizing
            "gsm", "weight", "width", "length", "size", "fit", "dimension", "measurement", "specification", "specs",
            # Media & Visuals
            "photo", "picture", "pic", "image", "video", "clip", "look like", "unboxing",
            # Missing details / Attributes
            "origin", "warranty", "guarantee", "manufacturer", "details of", "tell me about",
        ]
        has_prod_kw = any(k in text_clean for k in product_kws)
        q_indicators = ["?", "what", "how", "is it", "can i", "show", "tell me", "does it", "where", "which", "are there"]
        has_q = any(q in text_clean for q in q_indicators)
        return has_prod_kw and (has_q or len(text_clean.split()) <= 4)

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
                        has_explicit_unit = True
                    else:
                        val = int(raw_val)
                        has_explicit_unit = bool(re.search(r"(?:pieces?|units?|pcs|items?|qty|quantity|packs?|piece|unit|item|pack)\b", match.group(0)))

                    if 1 <= val <= 1000:
                        # Guard: If number is followed by price suffixes, don't treat as qty
                        if re.search(r"\b" + re.escape(raw_val) + r"\s*(?:rs|rupees|inr|final|per|each|only)", text_lower):
                            continue
                        # Guard: If number is preceded by explicit currency symbols, don't treat as qty
                        if re.search(r"(?:rs\.?|inr|₹)\s*" + re.escape(raw_val) + r"\b", text_lower):
                            continue
                        # Guard: If number is preceded by price words ("for 900", "said 900", "at 900"), don't treat as qty unless has explicit unit words or 'how much for'
                        is_how_much_for = bool(re.search(r"\bhow\s+much\s+for\s+" + re.escape(raw_val) + r"\b", text_lower))
                        if not has_explicit_unit and not is_how_much_for and re.search(r"\b(?:for|at|said|price|cost)\s+" + re.escape(raw_val) + r"\b", text_lower):
                            continue
                        # Guard: Without explicit unit words, quantity cannot exceed 50
                        if not has_explicit_unit and val > 50:
                            continue
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

        # 1b. Deliberation / Thinking it over
        if cls.is_deliberation(text_lower):
            return IntentResult(
                intent="general_inquiry",
                offered_price=None,
                requested_quantity=qty,
                confidence=0.95,
            )

        # 1c. Savings Inquiry
        if cls.is_savings_query(text_lower):
            return IntentResult(
                intent="general_inquiry",
                offered_price=None,
                requested_quantity=qty,
                confidence=0.95,
            )

        # 2. Acceptance / Deal Closure Detection
        # Qualified or conditional buy phrases (e.g. "I want to buy but it's too costly")
        # MUST route to negotiation, NOT checkout!
        is_acc = cls.is_acceptance(text_lower)
        is_pay = cls.is_payment_inquiry(text_lower)
        has_checkout_kw = any(kw in text_lower for kw in cls.CHECKOUT_KEYWORDS)
        if (is_acc or is_pay or has_checkout_kw) and not cls.is_conditional(text_lower) and price is None:
            return IntentResult(
                intent="checkout_intent",
                offered_price=None,
                requested_quantity=qty,
                confidence=0.95,
            )

        # 2b. Product Specification / Details / Media Question
        if cls.is_product_question(text_lower):
            return IntentResult(
                intent="trust_hesitation",
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

        # 4. Price Hesitation / Negotiation (including conditional buy intent & quantity adjustments)
        if (
            price is not None
            or any(kw in text_lower for kw in cls.PRICE_KEYWORDS)
            or cls.is_conditional(text_lower)
            or (in_negotiation and (price is not None or qty is not None))
        ):
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

    GREETING_PATTERNS = [
        r"^\s*(?:hi|hello|hey|namaste|greetings|good\s+(?:morning|afternoon|evening))\b",
    ]

    @classmethod
    def is_greeting(cls, text: str) -> bool:
        text_clean = text.lower().strip().replace("’", "'")
        has_greet = any(re.search(p, text_clean) for p in cls.GREETING_PATTERNS)
        has_other_intent = (
            cls.is_acceptance(text_clean)
            or cls.is_payment_inquiry(text_clean)
            or cls.is_deliberation(text_clean)
            or cls.is_conditional(text_clean)
            or any(k in text_clean for k in cls.PRICE_KEYWORDS)
            or any(k in text_clean for k in cls.TRUST_KEYWORDS)
            or any(k in text_clean for k in cls.BULK_KEYWORDS)
            or bool(re.search(r"\d+", text_clean))
        )
        return has_greet and not has_other_intent

    @classmethod
    def is_unambiguous_intent(
        cls,
        user_text: str,
        in_negotiation: bool = False,
    ) -> Tuple[bool, Optional[BuyerIntentDecision]]:
        """
        Deterministic-First Pre-Classifier.
        Detects unambiguous, clearly recognizable messages so they can bypass Stage 1 Gemini LLM calls,
        conserving Gemini quota for Stage 3 natural salesperson responses.
        Returns: (is_unambiguous: bool, decision: Optional[BuyerIntentDecision])
        """
        text_clean = user_text.lower().strip().replace("’", "'")

        # 1. Deliberation ("I'll think about it", "let you know")
        if cls.is_deliberation(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="clarification",
                hesitation="none",
                confidence=0.98,
                reason="Deterministic: clear buyer deliberation phrasing.",
            )

        # 1b. Savings Inquiry ("How much am I saving compared with buying 5?")
        if cls.is_savings_query(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="clarification",
                hesitation="none",
                confidence=0.98,
                reason="Deterministic: clear savings inquiry phrasing.",
            )

        # 2. Acceptance ("I'll take it", "Ok done", "Deal", "Agreed", "I'll take all 5")
        if cls.is_acceptance(text_clean):
            _, acc_qty = cls.extract_price_and_qty(user_text, in_negotiation=in_negotiation)
            return True, BuyerIntentDecision(
                primary_intent="purchase_intent",
                hesitation="none",
                confidence=0.98,
                requested_quantity=acc_qty,
                reason="Deterministic: clear deal acceptance phrasing.",
            )

        # 3. Payment Inquiry ("How do I pay?", "Where to pay?", "Send payment link")
        if cls.is_payment_inquiry(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="purchase_intent",
                hesitation="none",
                confidence=0.98,
                reason="Deterministic: clear payment inquiry phrasing.",
            )

        # 4. Explicit Buy ("I want to buy", "ready to purchase")
        if cls.is_explicit_buy(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="purchase_intent",
                hesitation="none",
                confidence=0.98,
                reason="Deterministic: explicit purchase intent phrasing.",
            )

        # 4b. Product Specification / Details / Media Question ("How durable is it?", "What is the material?", "Show photo")
        if cls.is_product_question(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="product_question",
                hesitation="trust",
                confidence=0.95,
                product_question=ProductQuestion(question=user_text.strip()),
                reason="Deterministic: clear product specification/evidence inquiry.",
            )

        price, qty = cls.extract_price_and_qty(user_text, in_negotiation=in_negotiation)

        # 5. Obvious Numeric Price Offer ("Can you do 1800?", "1750 final", "Ok 1800", "2000?")
        if price is not None:
            return True, BuyerIntentDecision(
                primary_intent="price_negotiation",
                hesitation="price",
                confidence=0.95,
                offered_price=price,
                requested_quantity=qty,
                reason="Deterministic: explicit numeric price proposal.",
            )

        # 6. Quantity Pricing Query / Bulk Request ("What if I take 5?", "For 3 units?", "How much for 5 pieces?")
        if (qty is not None and qty > 1) or any(k in text_clean for k in cls.BULK_KEYWORDS):
            return True, BuyerIntentDecision(
                primary_intent="quantity_pricing_query",
                hesitation="price",
                confidence=0.95,
                requested_quantity=qty or 5,
                reason="Deterministic: clear volume/quantity pricing inquiry.",
            )

        # 7. Obvious Discount / Price Negotiation Request ("Can you give me some discount?", "Thoda kam karo", "best price?")
        discount_triggers = [
            "discount", "best price", "kam karo", "kam karoge", "thoda kam",
            "lower price", "reduce price", "cheaper", "negotiate", "negotiable",
            "costly", "expensive", "too high", "thoda price kam",
        ]
        has_discount_kw = any(k in text_clean for k in discount_triggers)
        has_discount_phrase = bool(re.search(r"\b(?:can\s+you\s+give|give\s+me|get|any)\s+(?:a\s+|some\s+)?discount\b", text_clean))
        if has_discount_kw or has_discount_phrase:
            return True, BuyerIntentDecision(
                primary_intent="price_negotiation",
                hesitation="price",
                confidence=0.95,
                reason="Deterministic: clear discount/price negotiation request.",
            )

        # 8. Standard Greeting ("Hi", "Hello", "Namaste", "Good morning")
        if cls.is_greeting(text_clean):
            return True, BuyerIntentDecision(
                primary_intent="general_conversation",
                hesitation="none",
                confidence=0.95,
                reason="Deterministic: standard greeting.",
            )

        # 9. Obvious Product Evidence / Trust Question ("Can I see real photo?", "Show real video", "Is this pure silk?")
        evidence_media_kws = ["photo", "picture", "pic", "image", "video", "clip", "review", "durability", "material", "silk", "fabric", "care", "wash", "authentic", "genuine", "original", "warranty", "proof"]
        question_indicators = ["?", "can i", "show", "is it", "what", "how", "tell me", "see", "any photo", "real", "dikhao"]
        has_media_kw = any(k in text_clean for k in evidence_media_kws)
        has_q_indicator = any(q in text_clean for q in question_indicators)
        if has_media_kw and has_q_indicator:
            return True, BuyerIntentDecision(
                primary_intent="product_question",
                hesitation="trust",
                confidence=0.95,
                product_question=ProductQuestion(question=user_text.strip()),
                reason="Deterministic: clear product specification/evidence inquiry.",
            )

        # If not clearly recognizable, route to Stage 1 Gemini for semantic/multilingual interpretation
        return False, None

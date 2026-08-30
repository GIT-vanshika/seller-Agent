from decimal import Decimal
from pydantic import ValidationError
from app.models import Product, Evidence, SellerPolicy, BulkRule, BulkTier, NegotiationExperience


def run_tests():
    print("Running Pydantic Model Validation Tests (Step 8.5 Decimal & Multi-tier Review)...\n")

    # Test 1: Product with Decimal money precision
    try:
        p = Product(
            id="prod_1",
            name="Wireless Headphones",
            description="High quality noise cancelling headphones",
            listed_price=Decimal("199.99"),
            category="Electronics",
        )
        assert isinstance(p.listed_price, Decimal)
        print("[PASS] Test 1: Valid Product created with Decimal listed_price:", p.listed_price)
    except Exception as e:
        print("[FAIL] Test 1:", e)

    # Test 2: Evidence validation
    try:
        e = Evidence(
            id="ev_1",
            product_id="prod_1",
            type="review",
            source="customer_experience",
            label="Customer Review",
            content="Battery life lasts 20 hours as advertised.",
        )
        print("[PASS] Test 2: Valid Evidence created. Source:", e.source)
    except Exception as e:
        print("[FAIL] Test 2:", e)

    # Test 3: Valid Fixed-Price Policy with Decimal precision
    try:
        sp_fixed = SellerPolicy(
            product_id="prod_fixed",
            pricing_mode="fixed",
            listed_price=Decimal("50.00"),
            aspiration_price=Decimal("50.00"),
            target_price=Decimal("50.00"),
            reservation_price=Decimal("50.00"),
            batna="hold_price",
            max_negotiation_rounds=0,
        )
        assert isinstance(sp_fixed.reservation_price, Decimal)
        print("[PASS] Test 3: Valid fixed-price policy created with Decimal money:", sp_fixed.pricing_mode)
    except Exception as e:
        print("[FAIL] Test 3:", e)

    # Test 4: Valid Negotiable Policy with Multi-tier Bulk Rules
    try:
        sp_neg = SellerPolicy(
            product_id="prod_neg",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1750.00"),
            reservation_price=Decimal("1550.00"),
            batna="normal_sale",
            bulk_rules=BulkRule(
                tiers=[
                    BulkTier(min_quantity=5, discount_percentage=Decimal("10.0")),   # Unit price: 2250 >= 1550
                    BulkTier(min_quantity=10, discount_percentage=Decimal("20.0")),  # Unit price: 2000 >= 1550
                    BulkTier(min_quantity=20, discount_percentage=Decimal("30.0"))   # Unit price: 1750 >= 1550
                ]
            ),
            max_negotiation_rounds=5,
        )
        print("[PASS] Test 4: Valid negotiable policy with multi-tier bulk rules created. Target:", sp_neg.target_price)
    except Exception as e:
        print("[FAIL] Test 4:", e)

    # Test 5: Invalid reservation_price > target_price
    try:
        SellerPolicy(
            product_id="prod_err1",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1900.00"),  # Invalid: res > target
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 5: reservation_price > target_price was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 5: reservation_price > target_price correctly rejected.")

    # Test 6: Invalid target_price > aspiration_price
    try:
        SellerPolicy(
            product_id="prod_err2",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("2500.00"),  # Invalid: target > aspiration
            reservation_price=Decimal("1600.00"),
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 6: target_price > aspiration_price was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 6: target_price > aspiration_price correctly rejected.")

    # Test 7: Invalid aspiration_price > listed_price
    try:
        SellerPolicy(
            product_id="prod_err3",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2600.00"),  # Invalid: asp > listed
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 7: aspiration_price > listed_price was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 7: aspiration_price > listed_price correctly rejected.")

    # Test 8: Invalid negative price
    try:
        SellerPolicy(
            product_id="prod_err4",
            pricing_mode="negotiable",
            listed_price=Decimal("-100.00"),  # Invalid negative
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 8: Negative price was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 8: Negative price correctly rejected.")

    # Test 9: Invalid negotiation rounds for negotiable policy
    try:
        SellerPolicy(
            product_id="prod_err5",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            max_negotiation_rounds=0,  # Invalid for negotiable
        )
        print("[FAIL] Test 9: max_negotiation_rounds=0 in negotiable mode was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 9: max_negotiation_rounds=0 in negotiable mode correctly rejected.")

    # Test 10: Fixed pricing with max_negotiation_rounds > 0 rejected
    try:
        SellerPolicy(
            product_id="prod_err6",
            pricing_mode="fixed",
            listed_price=Decimal("50.00"),
            aspiration_price=Decimal("50.00"),
            target_price=Decimal("50.00"),
            reservation_price=Decimal("50.00"),
            max_negotiation_rounds=3,  # Invalid for fixed
        )
        print("[FAIL] Test 10: Fixed pricing with max_negotiation_rounds > 0 was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 10: Fixed pricing with max_negotiation_rounds > 0 correctly rejected.")

    # Test 11: Valid BATNA value accepted
    try:
        sp_batna = SellerPolicy(
            product_id="prod_batna",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            batna="another_channel",
            max_negotiation_rounds=3,
        )
        print("[PASS] Test 11: Valid BATNA accepted:", sp_batna.batna)
    except Exception as e:
        print("[FAIL] Test 11:", e)

    # Test 12: Invalid BATNA value rejected
    try:
        SellerPolicy(
            product_id="prod_err7",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            batna="invalid_option",  # Invalid BATNA
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 12: Invalid BATNA was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 12: Invalid BATNA correctly rejected.")

    # Test 13: Valid NegotiationExperience recording model with Decimal money
    try:
        exp = NegotiationExperience(
            session_id="sess_101",
            product_id="prod_neg",
            starting_price=Decimal("2400.00"),
            buyer_offers=[Decimal("1500.00"), Decimal("1700.00")],
            seller_counter_offers=[Decimal("2200.00"), Decimal("1850.00")],
            rounds=2,
            final_agreed_price=Decimal("1850.00"),
            converted=True,
            quantity=1,
            seller_feedback="Good quick agreement near target",
            successful_in_seller_view=True,
        )
        assert isinstance(exp.starting_price, Decimal)
        print("[PASS] Test 13: Valid NegotiationExperience created with Decimal money:", exp.session_id)
    except Exception as e:
        print("[FAIL] Test 13:", e)

    # Test 14: Multi-tier bulk discount where tier 3 breaches reservation price floor rejected
    try:
        SellerPolicy(
            product_id="prod_err_bulk_tier",
            pricing_mode="negotiable",
            listed_price=Decimal("2500.00"),
            aspiration_price=Decimal("2400.00"),
            target_price=Decimal("1800.00"),
            reservation_price=Decimal("1600.00"),
            batna="normal_sale",
            bulk_rules=BulkRule(
                tiers=[
                    BulkTier(min_quantity=5, discount_percentage=Decimal("10.0")),   # Unit price: 2250 >= 1600 (Valid)
                    BulkTier(min_quantity=10, discount_percentage=Decimal("20.0")),  # Unit price: 2000 >= 1600 (Valid)
                    BulkTier(min_quantity=20, discount_percentage=Decimal("50.0"))   # Unit price: 1250 < 1600 (INVALID FLOOR BREACH!)
                ]
            ),
            max_negotiation_rounds=3,
        )
        print("[FAIL] Test 14: Bulk tier breaching reservation price floor was NOT rejected.")
    except ValidationError:
        print("[PASS] Test 14: Bulk tier breaching reservation price floor correctly rejected.")


if __name__ == "__main__":
    run_tests()

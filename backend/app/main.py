import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Auto-load backend/.env if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    try:
        with open(_env_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
                    if _k and _v:
                        os.environ[_k] = _v
    except Exception:
        pass
from app.data_loader import db
from app.schemas import (
    ProductResponse,
    EvidenceResponse,
    ProductListResponse,
    ProductDetailResponse,
    ChatApiRequest,
    ValidateDealApiRequest,
    CreateOrderApiRequest,
    VerifyPaymentApiRequest,
    VerifyPaymentApiResponse,
)
from app.orchestrator import AgentOrchestrator, AgentChatResponse
from app.deal_validator import DealConsistencyValidator, DealValidationRequest, ValidatedDeal
from app.razorpay_service import RazorpayService, RazorpayOrderRequest, RazorpayOrderResponse
from app.razorpay_service import RazorpayService, RazorpayOrderRequest, RazorpayOrderResponse, RazorpayVerificationResponse
from app.session_manager import session_db
from app.models import NegotiationExperience
from app.experience_store import experience_store

app = FastAPI(title="AI Purchase Confidence & Deal Agent Public API")

# Configure CORS strictly for local development
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/products", response_model=ProductListResponse)
def get_products():
    all_products = db.get_all_products()
    public_products = [
        ProductResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            listed_price=p.listed_price,
            category=p.category,
        )
        for p in all_products
    ]
    return ProductListResponse(products=public_products)


@app.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product_detail(product_id: str):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    public_product = ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        listed_price=product.listed_price,
        category=product.category,
    )

    raw_evidence = db.get_evidence_for_product(product_id)
    public_evidence = [
        EvidenceResponse(
            id=e.id,
            product_id=e.product_id,
            type=e.type,
            source=e.source,
            label=e.label,
            content=e.content,
        )
        for e in raw_evidence
    ]

    return ProductDetailResponse(product=public_product, evidence=public_evidence)


@app.post("/chat", response_model=AgentChatResponse)
def chat_endpoint(req: ChatApiRequest):
    try:
        response = AgentOrchestrator.process_user_message(
            session_id=req.session_id,
            product_id=req.product_id,
            user_text=req.message,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")


@app.post("/validate-deal", response_model=ValidatedDeal)
def validate_deal_endpoint(req: ValidateDealApiRequest):
    policy = db.get_seller_policy(req.product_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Seller policy not found for product")

    session = session_db.get_session(req.session_id)
    curr_neg_price = session.current_negotiated_unit_price if session else None
    curr_neg_price = (session.single_unit_negotiated_price or session.current_negotiated_unit_price) if session else None
    curr_round = session.negotiation_round if session else 1

    val_req = DealValidationRequest(
        product_id=req.product_id,
        quantity=req.quantity,
        proposed_unit_price=req.proposed_unit_price,
        current_negotiated_unit_price=curr_neg_price,
        negotiation_round=curr_round,
    )

    validated_deal = DealConsistencyValidator.validate_deal(policy, val_req)
    return validated_deal


@app.post("/create-order", response_model=RazorpayOrderResponse)
def create_order_endpoint(req: CreateOrderApiRequest):
    policy = db.get_seller_policy(req.product_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Seller policy not found for product")

    session = session_db.get_session(req.session_id)
    curr_neg_price = session.current_negotiated_unit_price if session else None
    curr_neg_price = (session.single_unit_negotiated_price or session.current_negotiated_unit_price) if session else None
    curr_round = session.negotiation_round if session else 1

    try:
        rzp_req = RazorpayOrderRequest(
            session_id=req.session_id,
            product_id=req.product_id,
            quantity=req.quantity,
            requested_unit_price=req.requested_unit_price,
            total_payable_amount=req.total_payable_amount,
        )
        order_res = RazorpayService.create_order_safe(
            policy=policy,
            request=rzp_req,
            current_negotiated_unit_price=curr_neg_price,
            negotiation_round=curr_round,
        )
        return order_res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/verify-payment", response_model=VerifyPaymentApiResponse)
def verify_payment_endpoint(req: VerifyPaymentApiRequest):
    session = session_db.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        verification_res = RazorpayService.verify_payment_safe(
            session_id=req.session_id,
            order_id=req.razorpay_order_id,
            payment_id=req.razorpay_payment_id,
            signature=req.razorpay_signature,
            session=session,
        )

        # Transition authoritative session state
        session.deal_status = "checked_out"

        # Phase 3 Experience Store: Save negotiation trajectory upon verified deal closure
        product = db.get_product(session.product_id)
        starting_price = product.listed_price if product else (
            session.last_validated_deal.listed_price if session.last_validated_deal else Decimal("0.00")
        )

        buyer_offers = [
            m.suggested_price for m in session.messages if m.sender == "buyer" and m.suggested_price is not None
        ]
        seller_counter_offers = [
            m.suggested_price for m in session.messages if m.sender == "agent" and m.suggested_price is not None
        ]

        exp = NegotiationExperience(
            session_id=session.session_id,
            product_id=session.product_id,
            starting_price=starting_price,
            buyer_offers=buyer_offers,
            seller_counter_offers=seller_counter_offers,
            rounds=session.negotiation_round,
            final_agreed_price=verification_res.effective_unit_price,
            converted=True,
            quantity=session.quantity,
            seller_feedback="Deal converted and cryptographically verified via HMAC SHA-256 signature.",
            successful_in_seller_view=True,
        )
        experience_store.save_experience(exp)

        return VerifyPaymentApiResponse(
            success=verification_res.success,
            payment_status=verification_res.payment_status,
            escrow_status=verification_res.escrow_status,
            order_id=verification_res.order_id,
            payment_id=verification_res.payment_id,
            session_id=verification_res.session_id,
            amount_in_paisa=verification_res.amount_in_paisa,
            currency=verification_res.currency,
            effective_unit_price=verification_res.effective_unit_price,
            total_payable_amount=verification_res.total_payable_amount,
            quantity=verification_res.quantity or session.quantity or 1,
            message=verification_res.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/demo/sign-payment")
def demo_sign_payment_endpoint(req: dict):
    order_id = req.get("order_id", "")
    payment_id = req.get("payment_id", "")
    sig = RazorpayService.generate_test_signature(order_id, payment_id)
    return {"signature": sig}


@app.get("/experience/{session_id}")
def get_experience_endpoint(session_id: str):
    exp = experience_store.get_experience(session_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found for session")
    return exp


@app.get("/session/{session_id}")
def get_session_endpoint(session_id: str):
    session = session_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

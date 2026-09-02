from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.data_loader import db
from app.schemas import (
    ProductResponse,
    EvidenceResponse,
    ProductListResponse,
    ProductDetailResponse,
    ChatApiRequest,
    ValidateDealApiRequest,
    CreateOrderApiRequest,
)
from app.orchestrator import AgentOrchestrator, AgentChatResponse
from app.deal_validator import DealConsistencyValidator, DealValidationRequest, ValidatedDeal
from app.razorpay_service import RazorpayService, RazorpayOrderRequest, RazorpayOrderResponse
from app.session_manager import session_db

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


@app.get("/session/{session_id}")
def get_session_endpoint(session_id: str):
    session = session_db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

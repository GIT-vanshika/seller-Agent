from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.data_loader import db
from app.schemas import (
    ProductResponse,
    EvidenceResponse,
    ProductListResponse,
    ProductDetailResponse,
)

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

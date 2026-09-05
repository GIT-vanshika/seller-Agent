import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict

from app.models import Evidence, EvidenceSource
from app.contracts import TrustStatus
from app.data_loader import db


class EvidenceAssessment(BaseModel):
    """
    Question-specific assessment of evidence coverage and provenance.
    """

    model_config = ConfigDict(extra="forbid")

    question_category: str = Field(..., description="Detected question category")
    status: TrustStatus = Field(..., description="Controlled trust resolution status")
    evidence_ids_used: List[str] = Field(default_factory=list, description="Traceable IDs of evidence items used")
    source_types_used: List[EvidenceSource] = Field(default_factory=list, description="Distinct evidence sources represented")
    coverage_reason: str = Field(..., min_length=1, max_length=500, description="Reasoning for assessment status")


class EvidenceRetriever:
    """
    Question-Aware Deterministic Evidence Retrieval Layer.
    Classifies buyer question categories and evaluates whether evidence SPECIFICALLY supports the asked concern.
    Ensures 100% product isolation and preserves exact source provenance.
    """

    @classmethod
    def classify_question_category(cls, question: Optional[str]) -> str:
        if not question or not question.strip():
            return "general_product_information"

        q_lower = question.lower()

        if any(w in q_lower for w in ["wash", "care", "clean", "laundry", "dry clean", "iron"]):
            return "care"
        if any(w in q_lower for w in ["material", "fabric", "silk", "cotton", "linen", "made of", "composition", "pure"]):
            return "material"
        if any(w in q_lower for w in ["durable", "durability", "last", "warranty", "guarantee", "lifespan"]):
            return "durability"
        if any(w in q_lower for w in ["authentic", "genuine", "original", "fake", "scam"]):
            return "authenticity"
        if any(w in q_lower for w in ["look", "photo", "picture", "video", "real life", "appearance", "unboxing", "color", "texture", "offline", "identical"]):
            return "appearance"
        if any(w in q_lower for w in ["size", "sizing", "fit", "dimension", "measurement"]):
            return "sizing"
        if any(w in q_lower for w in ["quality", "finish", "stitching", "craftsmanship"]):
            return "quality"

        return "general_product_information"

    @classmethod
    def retrieve_evidence_for_product(
        cls, product_id: str, question: Optional[str] = None
    ) -> Tuple[List[Evidence], EvidenceAssessment]:
        # 1. Fetch ALL evidence strictly matching product_id from DataLoader
        all_product_evidence: List[Evidence] = db.get_evidence_for_product(product_id)

        # STRICT ISOLATION ASSERTION: Ensure no evidence belonging to another product is present
        isolated_evidence = [e for e in all_product_evidence if e.product_id == product_id]

        category = cls.classify_question_category(question)

        if not isolated_evidence:
            assessment = EvidenceAssessment(
                question_category=category,
                status="insufficient_evidence",
                evidence_ids_used=[],
                source_types_used=[],
                coverage_reason=f"No evidence items exist for product_id '{product_id}'.",
            )
            return [], assessment

        selected_evidence: List[Evidence] = []

        # 2. Question-Specific Relevance & Selection Logic
        if category == "appearance":
            q_lower = (question or "").lower()
            is_look_like = bool(re.search(r"\b(?:look\s+like|looks\s+like|look\s+in\s+real)\b", q_lower))
            has_photo_req = not is_look_like and bool(re.search(r"\b(?:photo|photos|picture|pictures|pic|pics|image|images)\b", q_lower))
            has_video_req = not is_look_like and bool(re.search(r"\b(?:video|videos|clip|clips|footage)\b", q_lower))

            if has_photo_req and not has_video_req:
                selected_evidence = [e for e in isolated_evidence if e.type == "image"]
            elif has_video_req and not has_photo_req:
                selected_evidence = [e for e in isolated_evidence if e.type == "video"]
            elif has_photo_req and has_video_req:
                selected_evidence = [e for e in isolated_evidence if e.type in ["image", "video"]]
            else:
                selected_evidence = [e for e in isolated_evidence if e.source in ["seller_reality", "customer_experience"]]
                if not selected_evidence:
                    selected_evidence = [e for e in isolated_evidence if e.source == "seller_marketing"]

        elif category in ["material", "authenticity"]:
            specs = [e for e in isolated_evidence if any(w in e.content.lower() or w in e.label.lower() for w in ["spec", "material", "fabric", "silk", "cotton", "linen"])]
            visuals = [e for e in isolated_evidence if e.source in ["seller_reality", "customer_experience"]]
            selected_evidence = specs + [v for v in visuals if v not in specs]
            if not selected_evidence:
                selected_evidence = isolated_evidence

        elif category == "care":
            selected_evidence = [e for e in isolated_evidence if any(w in e.content.lower() or w in e.label.lower() for w in ["wash", "care", "dry clean", "laundry"])]

        elif category == "durability":
            selected_evidence = [e for e in isolated_evidence if any(w in e.content.lower() or w in e.label.lower() for w in ["durable", "durability", "warranty", "lifespan", "years"])]

        elif category == "sizing":
            selected_evidence = [e for e in isolated_evidence if any(w in e.content.lower() or w in e.label.lower() for w in ["size", "sizing", "fit", "dimension"])]
            if not selected_evidence:
                selected_evidence = [e for e in isolated_evidence if e.type == "text"]

        elif category == "quality":
            selected_evidence = [e for e in isolated_evidence if any(w in e.content.lower() or w in e.label.lower() for w in ["stitch", "stitching", "craftsmanship", "finish", "quality"])]

        else:
            selected_evidence = isolated_evidence[:4]

        # 3. Question-Aware Assessment & Trust Status Determination
        evidence_ids = [e.id for e in selected_evidence]
        sources_used = list(dict.fromkeys([e.source for e in selected_evidence]))

        if not selected_evidence:
            status: TrustStatus = "insufficient_evidence"
            reason = f"No evidence available specifically supporting '{category}' questions."

        elif category == "appearance":
            if "seller_reality" in sources_used or "customer_experience" in sources_used:
                status = "resolved"
                reason = "Real-world visual media provides additional visual reference; natural lighting and displays may cause minor real-world variations."
            else:
                status = "partially_resolved"
                reason = "Covered only by catalog photos; lacks unedited real-world visual evidence."

        elif category in ["material", "authenticity"]:
            status = "partially_resolved"
            reason = "Catalog description states material claim; independent laboratory verification is not attached."

        elif category == "care":
            has_care_text = any("wash" in e.content.lower() or "care" in e.content.lower() for e in selected_evidence)
            if has_care_text:
                status = "resolved"
                reason = "Explicit wash care instructions found in evidence."
            else:
                status = "insufficient_evidence"
                reason = "No explicit wash/care instructions exist in available evidence."

        elif category == "durability":
            has_durability_review = any("durable" in e.content.lower() or "warranty" in e.content.lower() for e in selected_evidence)
            if has_durability_review:
                status = "partially_resolved"
                reason = "Customer experience review reports durability feedback, providing an individual user reference."
            else:
                status = "insufficient_evidence"
                reason = "No long-term durability or warranty evidence found."

        elif category == "quality":
            has_quality = any(any(w in e.content.lower() or w in e.label.lower() for w in ["stitch", "stitching", "craftsmanship", "finish", "quality"]) for e in selected_evidence)
            if has_quality:
                status = "partially_resolved"
                reason = "Grounded product evidence contains craftsmanship and finish details."
            else:
                status = "insufficient_evidence"
                reason = "Seller has not provided specific stitching-quality or overall-quality information in the catalog."

        else:
            if "seller_reality" in sources_used or "customer_experience" in sources_used:
                status = "resolved"
                reason = f"Supported by catalog specifications and real-world media references ({', '.join(sources_used)})."
            else:
                status = "partially_resolved"
                reason = "Supported by catalog specifications."

        assessment = EvidenceAssessment(
            question_category=category,
            status=status,
            evidence_ids_used=evidence_ids,
            source_types_used=sources_used,
            coverage_reason=reason,
        )

        return selected_evidence, assessment

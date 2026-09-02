from typing import Dict, List, Optional
from app.models import NegotiationExperience


class ExperienceStore:
    """
    Experience Store service for capturing and querying negotiation trajectories and session outcomes.
    """

    def __init__(self):
        self._experiences: Dict[str, NegotiationExperience] = {}

    def save_experience(self, exp: NegotiationExperience) -> NegotiationExperience:
        self._experiences[exp.session_id] = exp
        return exp

    def get_experience(self, session_id: str) -> Optional[NegotiationExperience]:
        return self._experiences.get(session_id)

    def get_experiences_for_product(self, product_id: str) -> List[NegotiationExperience]:
        return [exp for exp in self._experiences.values() if exp.product_id == product_id]


experience_store = ExperienceStore()


from fastapi import APIRouter
from app.models import PayersResponse, PayerInfo
from app.payer_config import PAYERS

router = APIRouter()


@router.get("/payers", response_model=PayersResponse)
async def get_payers() -> PayersResponse:
    """Return all supported payers for the frontend dropdown."""
    payer_list = [
        PayerInfo(
            id=payer_id,
            name=info["name"],
            short_name=info["short_name"],
            market_share=info["market_share"],
            logo_placeholder=info["logo_placeholder"],
        )
        for payer_id, info in PAYERS.items()
    ]
    return PayersResponse(payers=payer_list)

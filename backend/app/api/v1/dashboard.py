from fastapi import APIRouter, HTTPException, Depends
from app.services.dashboard_metrics import dashboard_service
from app.infrastructure.db.models import User
from app.api.deps import get_current_user, get_user_id

router = APIRouter()


@router.get("")
async def get_dashboard_metrics(user: User = Depends(get_current_user)):
    """Returns all dashboard metrics in a single aggregated response, scoped to the authenticated user."""
    try:
        return await dashboard_service.get_metrics(user_id=get_user_id(user))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard metrics: {str(e)}")

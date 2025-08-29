from fastapi import APIRouter, HTTPException, Request

from ..config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"]) 


@router.get("/fb-ig")
def verify(mode: str, challenge: str, verify_token: str):
	settings = get_settings()
	if mode == "subscribe" and verify_token == settings.META_VERIFY_TOKEN:
		return int(challenge)
	raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/fb-ig")
async def receive(request: Request):
	# For now, just accept payload
	payload = await request.json()
	return {"received": True}
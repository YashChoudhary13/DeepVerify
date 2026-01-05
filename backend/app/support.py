# support.py (or inside main.py)
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SupportTicket(BaseModel):
    name: str | None = None
    email: str
    message: str

@router.post("/support")
async def submit_support_ticket(ticket: SupportTicket):
    # In real-world usage, you'd save to DB or send email.
    print("New support ticket:", ticket)
    return {"status": "received", "ticket": ticket}
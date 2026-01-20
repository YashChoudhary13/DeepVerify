import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)
username = "admin"

with engine.connect() as conn:
    result = conn.execute(text("UPDATE public.users SET membership_status='Pro', detections_used=0 WHERE username = :u OR email = :u"), {"u": username})
    conn.commit()
    print(f"Rows updated: {result.rowcount}")
print("Done")

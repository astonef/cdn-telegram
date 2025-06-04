import os

def get_authorized_users():
    user_ids = os.getenv("AUTHORIZED_USERS", "")
    return set(int(uid) for uid in user_ids.split(",") if uid.strip().isdigit())

def is_authorized(user_id: int) -> bool:
    return user_id in get_authorized_users()

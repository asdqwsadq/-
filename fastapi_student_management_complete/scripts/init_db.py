from app.core.auth import ensure_default_accounts
from app.core.database import Base, SessionLocal, engine
from app import models  # noqa: F401


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_accounts(db)
    finally:
        db.close()
    print("Database initialized.")


if __name__ == "__main__":
    main()

import os
import sys

# Add current dir to path
sys.path.append(os.getcwd())

from app.database import Base, engine
from app.models import Subscription, Payment

def reset_tables():
    print("Dropping Subscription and Payment tables...")
    Subscription.__table__.drop(engine, checkfirst=True)
    Payment.__table__.drop(engine, checkfirst=True)
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done!")

if __name__ == "__main__":
    reset_tables()

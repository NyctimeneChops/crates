from dotenv import load_dotenv
load_dotenv()
from db.connection import create_tables
create_tables()
print("Tables created.")

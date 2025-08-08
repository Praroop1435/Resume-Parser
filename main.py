from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access environment variables
db_name = os.getenv("DB_NAME")
admin_user = os.getenv("ADMIN_USERNAME")
admin_pass = os.getenv("ADMIN_PASSWORD")

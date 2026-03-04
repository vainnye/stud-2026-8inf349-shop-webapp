# PROJECT_FOLDER = Path(__file__).resolve().parent.parent.parent
from pathlib import Path

PROJECT_FOLDER = Path.cwd().resolve()
API_URL_PATH = Path("/api/")
MOCK_API_PAYMENT_PATH = Path("mocks") / "shops" / "pay"
INSTANCE_FOLDER = PROJECT_FOLDER / "instance"
STATIC_FOLDER = PROJECT_FOLDER / "static"
DATABASE_FILE = INSTANCE_FOLDER / "database.db"
INIT_PRODUCTS_LOCATION = "http://dimensweb.uqac.ca/~jgnault/shops/products/"

from dataclasses import dataclass

from shop_webapp.util import validate_schema

schema = {"product": {"id": int, "quantity": int}}

json_payload = {"product": {"id": 123.2, "quantity": 2}}

try:
    validate_schema(json_payload, schema)
    print("valid schema")
except (TypeError, KeyError) as e:
    print(f"Validation error: {e}")

"""Promo code audience, usage limits, and new-user security."""

from datetime import date, timedelta
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class PromoSecuritySchemaTests(unittest.TestCase):
    def test_promo_model_has_audience_and_usage_fields(self):
        models = read("app/models.py")
        self.assertIn("audience", models)
        self.assertIn("max_uses", models)
        self.assertIn("uses_count", models)
        # Ensure fields live on PromoCode
        block = re.search(r"class PromoCode\(Base\):([\s\S]*?)(?=\nclass |\Z)", models)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("audience", body)
        self.assertIn("max_uses", body)
        self.assertIn("uses_count", body)

    def test_schemas_accept_audience_and_max_uses(self):
        schemas = read("app/promocodes/schemas.py")
        self.assertIn("audience", schemas)
        self.assertIn("max_uses", schemas)
        self.assertIn("new_users", schemas)
        self.assertIn("phone", schemas)

    def test_service_enforces_new_user_and_usage_cap(self):
        service = read("app/promocodes/service.py")
        self.assertIn("is_new_customer", service)
        self.assertIn("remaining_uses", service)
        self.assertIn("audience", service)
        self.assertIn("max_uses", service)
        self.assertIn("consume", service)
        self.assertRegex(
            service,
            r"new.?user|audience.*new_users|This promo is for new customers",
            re.I,
        )

    def test_admin_usage_endpoint_exists(self):
        router = read("app/promocodes/router.py")
        self.assertIn("usage", router)
        self.assertIn("get_promo_usage", router)


if __name__ == "__main__":
    unittest.main()

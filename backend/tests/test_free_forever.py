from app.main import app


def test_no_payment_or_billing_routes_exist():
    paths = [getattr(r, "path", "") for r in app.routes]
    assert not [p for p in paths if any(w in p.lower() for w in ("billing", "checkout", "invoice", "razorpay", "subscription"))]


def test_no_billing_settings_or_tables():
    from app.core.config import Settings
    from app.db.models import Base

    assert not [f for f in Settings.model_fields if any(w in f for w in ("billing", "razorpay", "invoice"))]
    assert not [t for t in Base.metadata.tables if t in {"subscriptions", "billing_orders", "invoices"}]

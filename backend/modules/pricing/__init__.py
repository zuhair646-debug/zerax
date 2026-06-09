"""
Zerax Pricing & Billing — credit-based pay-as-you-go + subscription system.
Payment: PayPal v2 REST API (LIVE mode).
Invoice: PDF (Arabic) via ReportLab + email delivery via Resend.
"""
from .router import create_router
from .credits import get_balance, add_credits, deduct_credits, has_balance, charge_user
from .seeds import seed_pricing_defaults

__all__ = [
    "create_router",
    "get_balance",
    "add_credits",
    "deduct_credits",
    "has_balance",
    "charge_user",
    "seed_pricing_defaults",
]

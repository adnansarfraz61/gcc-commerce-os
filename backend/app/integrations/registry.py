from dataclasses import dataclass

from app.models.integration import Marketplace


@dataclass(frozen=True)
class MarketplaceDescriptor:
    key: Marketplace
    display_name: str
    supports_oauth: bool
    supports_webhooks: bool


SUPPORTED_MARKETPLACES: dict[Marketplace, MarketplaceDescriptor] = {
    Marketplace.AMAZON: MarketplaceDescriptor(
        key=Marketplace.AMAZON,
        display_name="Amazon SP-API",
        supports_oauth=True,
        supports_webhooks=True,
    ),
    Marketplace.NOON: MarketplaceDescriptor(
        key=Marketplace.NOON,
        display_name="Noon",
        supports_oauth=False,
        supports_webhooks=False,
    ),
    Marketplace.SHOPIFY: MarketplaceDescriptor(
        key=Marketplace.SHOPIFY,
        display_name="Shopify",
        supports_oauth=True,
        supports_webhooks=True,
    ),
    Marketplace.TIKTOK_SHOP: MarketplaceDescriptor(
        key=Marketplace.TIKTOK_SHOP,
        display_name="TikTok Shop",
        supports_oauth=True,
        supports_webhooks=True,
    ),
}

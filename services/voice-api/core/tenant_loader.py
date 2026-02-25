"""
Tenant Configuration Loader
Loads tenant-specific configurations from JSON files
Enables white-label multi-tenant architecture
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

TENANT_DIR = Path(__file__).parent.parent / "tenants"


class TenantConfig:
    """Represents a loaded tenant configuration"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tenant_id = config.get("tenant_id", "default")
        self.name = config.get("name", "Tenant")
        self.branding = config.get("branding", {})
        self.providers = config.get("providers", {})
        self.features = config.get("features", {})
        self.quotas = config.get("quotas", {})
        self.config_settings = config.get("config", {})

    def get_provider(self, provider_type: str) -> Optional[str]:
        """Get configured provider for a given type"""
        return self.providers.get(provider_type)

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature, False)

    def get_quota(self, quota_type: str) -> Optional[int]:
        """Get quota for a given type"""
        return self.quotas.get(quota_type)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a config value"""
        return self.config_settings.get(key, default)

    def __repr__(self):
        return f"<TenantConfig {self.tenant_id}>"


@lru_cache(maxsize=128)
def load_tenant(tenant_id: str) -> TenantConfig:
    """
    Load tenant configuration from JSON file
    Falls back to default.json if tenant not found
    Results are cached for performance
    """
    tenant_file = TENANT_DIR / f"{tenant_id}.json"

    # Fallback to default if specific tenant not found
    if not tenant_file.exists():
        print(f"⚠️  [TENANT LOADER] Tenant {tenant_id} not found, using default")
        tenant_file = TENANT_DIR / "default.json"

    # Load JSON
    if not tenant_file.exists():
        raise FileNotFoundError(f"Tenant configuration not found: {tenant_file}")

    with open(tenant_file, "r") as f:
        config = json.load(f)

    print(f"✅ [TENANT LOADER] Loaded tenant config: {tenant_id}")
    return TenantConfig(config)


def reload_tenant(tenant_id: str) -> TenantConfig:
    """
    Reload tenant configuration (clears cache)
    Use when tenant config files are updated
    """
    load_tenant.cache_clear()
    return load_tenant(tenant_id)


def list_available_tenants() -> list[str]:
    """List all available tenant IDs"""
    tenants = []
    for file in TENANT_DIR.glob("*.json"):
        with open(file, "r") as f:
            config = json.load(f)
            tenants.append(config.get("tenant_id", file.stem))
    return tenants


def get_tenant_config_value(tenant_id: str, key: str, default: Any = None) -> Any:
    """Helper to get a config value for a tenant"""
    tenant = load_tenant(tenant_id)
    return tenant.get_config_value(key, default)


def add_tenant(tenant_id: str, config: Dict[str, Any]) -> TenantConfig:
    """
    Add a new tenant configuration
    Creates a new JSON file in the tenants directory
    """
    tenant_file = TENANT_DIR / f"{tenant_id}.json"

    if tenant_file.exists():
        raise FileExistsError(f"Tenant {tenant_id} already exists")

    with open(tenant_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ [TENANT LOADER] Created tenant config: {tenant_id}")
    reload_tenant(tenant_id)
    return load_tenant(tenant_id)

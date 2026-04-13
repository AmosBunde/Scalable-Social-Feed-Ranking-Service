"""API Gateway configuration."""
import os
from pydantic_settings import BaseSettings


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    host: str = "0.0.0.0"
    port: int = int(os.getenv("GATEWAY_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    rate_limit_rpm: int = 60
    feed_service_url: str = os.getenv("FEED_SERVICE_URL", "http://feed-service:8001")
    user_profile_url: str = os.getenv("USER_PROFILE_URL", "http://user-profile:8003")

    class Config:
        env_prefix = "SFR_GATEWAY_"


settings = GatewaySettings()

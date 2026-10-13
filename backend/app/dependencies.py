from .config import settings
from .market.upstox_live import UpstoxLiveManager

live_manager = UpstoxLiveManager(
    settings.upstox_access_token
)

def get_live_manager() -> UpstoxLiveManager:
    return live_manager
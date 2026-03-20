"""
Bidding System Package
======================

Hệ thống đấu giá để chọn AGV tối ưu cho từng task.

Architecture:
------------
- engine.py: BiddingEngine (main facade)
- auction.py: AuctionCoordinator (điều phối đấu giá)
- calculators/: Các components tính toán
  - transport.py: TransportCalculator (metrics vật lý)
  - baseline.py: BaselineCalculator (normalization)
  - bid.py: BidCalculator (bid scoring)

Public API:
----------
- BiddingEngine: Main interface để sử dụng

Example:
-------
>>> from vda5050.modules.bidding import BiddingEngine
>>> engine = BiddingEngine()
>>> winner_agv, error = engine.run_auction(target_node_id="N10", load_kg=100)
"""

from .engine import BiddingEngine
from .auction import AuctionCoordinator
from .calculators import (
    TransportCalculator,
    BaselineCalculator,
    BidCalculator,
)

# Public API
__all__ = [
    "BiddingEngine",
    "AuctionCoordinator",
    "TransportCalculator",
    "BaselineCalculator",
    "BidCalculator",
]

# Version info
__version__ = "2.0.0"
__author__ = "Nguyen Nghia"

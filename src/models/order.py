"""订单模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class SyntheticOrder:
    """合成订单模型"""
    
    start_time: datetime     # 起始时间
    end_time: datetime       # 结束时间
    symbol: str              # 股票代码
    direction: str           # 买卖方向 BUY/SELL
    total_volume: int        # 总成交量（手）
    total_amount: float      # 总成交金额（元）
    vwap: float              # 成交均价
    tick_count: int          # 包含的tick数量
    order_type: str          # 订单类型：ORIGINAL/SYNTHETIC/ALGO_TWAP/ALGO_VWAP
    confidence: float        # 可信度权重
    
    # 原始tick列表（可选，用于调试）
    original_ticks: List = None
    
    def __post_init__(self):
        if self.original_ticks is None:
            self.original_ticks = []
    
    @property
    def duration_seconds(self) -> float:
        """订单持续时间（秒）"""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def avg_amount_per_tick(self) -> float:
        """平均每笔成交金额"""
        if self.tick_count == 0:
            return 0.0
        return self.total_amount / self.tick_count
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'symbol': self.symbol,
            'direction': self.direction,
            'total_volume': self.total_volume,
            'total_amount': self.total_amount,
            'vwap': self.vwap,
            'tick_count': self.tick_count,
            'order_type': self.order_type,
            'confidence': self.confidence,
            'duration_seconds': self.duration_seconds,
        }
    
    def __repr__(self) -> str:
        return (f"SyntheticOrder({self.symbol}, {self.direction}, "
                f"{self.total_amount:.0f}元, {self.order_type}, "
                f"vwap={self.vwap:.2f})")

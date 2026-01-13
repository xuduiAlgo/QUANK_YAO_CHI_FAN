"""Tick数据模型"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Tick:
    """Level-2逐笔成交数据模型"""
    
    timestamp: datetime      # 时间戳（毫秒精度）
    symbol: str              # 股票代码
    price: float             # 成交价格
    volume: int              # 成交数量（手）
    amount: float            # 成交金额（元）
    direction: str           # 买卖方向 B=主动买, S=主动卖, N=未知
    bid1_price: float        # 买一价
    bid1_vol: int            # 买一量（手）
    ask1_price: float        # 卖一价
    ask1_vol: int            # 卖一量（手）
    
    # 可选的高阶字段
    bid2_price: Optional[float] = None      # 买二价
    bid2_vol: Optional[int] = None          # 买二量
    bid3_price: Optional[float] = None      # 买三价
    bid3_vol: Optional[int] = None          # 买三量
    bid4_price: Optional[float] = None      # 买四价
    bid4_vol: Optional[int] = None          # 买四量
    bid5_price: Optional[float] = None      # 买五价
    bid5_vol: Optional[int] = None          # 买五量
    ask2_price: Optional[float] = None      # 卖二价
    ask2_vol: Optional[int] = None          # 卖二量
    ask3_price: Optional[float] = None      # 卖三价
    ask3_vol: Optional[int] = None          # 卖三量
    ask4_price: Optional[float] = None      # 卖四价
    ask4_vol: Optional[int] = None          # 卖四量
    ask5_price: Optional[float] = None      # 卖五价
    ask5_vol: Optional[int] = None          # 卖五量
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'amount': self.amount,
            'direction': self.direction,
            'bid1_price': self.bid1_price,
            'bid1_vol': self.bid1_vol,
            'ask1_price': self.ask1_price,
            'ask1_vol': self.ask1_vol,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tick':
        """从字典创建对象"""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            symbol=data['symbol'],
            price=data['price'],
            volume=data['volume'],
            amount=data['amount'],
            direction=data['direction'],
            bid1_price=data['bid1_price'],
            bid1_vol=data['bid1_vol'],
            ask1_price=data['ask1_price'],
            ask1_vol=data['ask1_vol'],
        )
    
    def __repr__(self) -> str:
        return f"Tick({self.symbol}, {self.timestamp}, {self.price}, {self.volume}手, {self.direction})"

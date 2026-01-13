"""意图分类引擎（模块一）"""
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from ..models.tick import Tick
from ..utils.logger import get_logger

logger = get_logger("classifier")


@dataclass
class OrderBook:
    """订单簿快照"""
    bid1_price: float
    bid1_vol: int
    ask1_price: float
    ask1_vol: int
    bid2_price: Optional[float] = None
    bid2_vol: Optional[int] = None
    bid3_price: Optional[float] = None
    bid3_vol: Optional[int] = None
    bid4_price: Optional[float] = None
    bid4_vol: Optional[int] = None
    bid5_price: Optional[float] = None
    bid5_vol: Optional[int] = None
    ask2_price: Optional[float] = None
    ask2_vol: Optional[int] = None
    ask3_price: Optional[float] = None
    ask3_vol: Optional[int] = None
    ask4_price: Optional[float] = None
    ask4_vol: Optional[int] = None
    ask5_price: Optional[float] = None
    ask5_vol: Optional[int] = None


class TickClassifier:
    """Tick数据分类器 - 区分攻击性/防御性买卖"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化分类器
        
        Args:
            config: 配置字典
        """
        self.big_order_threshold = config.get('big_order_threshold', 100000)  # 大单阈值（元）
        self.wall_threshold = config.get('wall_threshold', 10000)  # 城墙单阈值（手）
        self.price_impact_threshold = config.get('price_impact_threshold', 0.001)  # 价格冲击阈值
        
        logger.info(f"TickClassifier initialized with big_order_threshold={self.big_order_threshold}")
    
    def classify_tick(self, tick: Tick, orderbook: Optional[OrderBook] = None) -> Tuple[str, float]:
        """
        对单笔tick进行分类
        
        Args:
            tick: Tick数据
            orderbook: 订单簿快照（可选）
        
        Returns:
            (label, weight)
            label: AGG_BUY, AGG_SELL, DEF_BUY, DEF_SELL, SMALL_BUY, SMALL_SELL, NOISE
            weight: 权重系数 (0.0-2.0)
        """
        try:
            # 1. 判断是否为大单
            if self._is_big_order(tick):
                # 2. 判断方向
                if tick.direction == 'B' or tick.direction == 'BUY':
                    # 3. 判断是否为攻击性买入
                    if self._is_aggressive_buy(tick, orderbook):
                        return ('AGG_BUY', 1.5)
                    else:
                        return ('DEF_BUY', 0.8)
                
                elif tick.direction == 'S' or tick.direction == 'SELL':
                    # 4. 判断是否为攻击性卖出
                    if self._is_aggressive_sell(tick, orderbook):
                        return ('AGG_SELL', 1.5)
                    else:
                        return ('DEF_SELL', 0.8)
                
                else:
                    # 未知方向，标记为噪音
                    return ('NOISE', 0.0)
            
            else:
                # 小单 - 标记为小单类型，等待合成
                if tick.direction == 'B' or tick.direction == 'BUY':
                    return ('SMALL_BUY', 0.0)
                elif tick.direction == 'S' or tick.direction == 'SELL':
                    return ('SMALL_SELL', 0.0)
                else:
                    return ('NOISE', 0.0)
        
        except Exception as e:
            logger.error(f"Error classifying tick: {e}")
            return ('NOISE', 0.0)
    
    def _is_big_order(self, tick: Tick) -> bool:
        """
        判断是否为大单
        
        Args:
            tick: Tick数据
        
        Returns:
            是否为大单
        """
        return tick.amount >= self.big_order_threshold
    
    def _is_aggressive_buy(self, tick: Tick, orderbook: Optional[OrderBook]) -> bool:
        """
        判断是否为攻击性买单
        
        攻击性买单特征：
        1. 成交价 > 卖一价（主动吃单）
        2. 或者在卖一价成交且卖一量显著减少
        3. 不是被动护盘的城墙单
        
        Args:
            tick: Tick数据
            orderbook: 订单簿快照
        
        Returns:
            是否为攻击性买单
        """
        # 方法1: 比较成交价与盘口价格
        # 如果成交价高于卖一价，说明是主动吃单（攻击性）
        if tick.price > tick.ask1_price:
            return True
        
        # 如果成交价接近买一价，检查是否为城墙单（防御性）
        if abs(tick.price - tick.bid1_price) < 0.01:
            # 买一量巨大，可能是护盘
            if tick.bid1_vol > self.wall_threshold:
                return False
        
        # 方法2: 检测盘口冲击（如果有订单簿数据）
        if orderbook:
            return self._check_orderbook_impact(tick, orderbook, 'buy')
        
        # 默认：如果成交价接近卖一价，认为是攻击性
        if abs(tick.price - tick.ask1_price) < 0.01:
            return True
        
        # 其他情况根据方向判断
        return False
    
    def _is_aggressive_sell(self, tick: Tick, orderbook: Optional[OrderBook]) -> bool:
        """
        判断是否为攻击性卖单
        
        攻击性卖单特征：
        1. 成交价 < 买一价（主动砸盘）
        2. 或者在买一价成交且买一量显著减少
        
        Args:
            tick: Tick数据
            orderbook: 订单簿快照
        
        Returns:
            是否为攻击性卖单
        """
        # 方法1: 比较成交价与盘口价格
        # 如果成交价低于买一价，说明是主动砸盘（攻击性）
        if tick.price < tick.bid1_price:
            return True
        
        # 如果成交价接近卖一价，检查是否为压盘单（防御性）
        if abs(tick.price - tick.ask1_price) < 0.01:
            # 卖一量巨大，可能是压盘
            if tick.ask1_vol > self.wall_threshold:
                return False
        
        # 方法2: 检测盘口冲击（如果有订单簿数据）
        if orderbook:
            return self._check_orderbook_impact(tick, orderbook, 'sell')
        
        # 默认：如果成交价接近买一价，认为是攻击性
        if abs(tick.price - tick.bid1_price) < 0.01:
            return True
        
        # 其他情况根据方向判断
        return False
    
    def _check_orderbook_impact(self, tick: Tick, orderbook: OrderBook, direction: str) -> bool:
        """
        通过盘口冲击判断意图
        
        Args:
            tick: Tick数据
            orderbook: 订单簿快照
            direction: 买卖方向 'buy' 或 'sell'
        
        Returns:
            是否为攻击性行为
        """
        if direction == 'buy':
            # 检查卖一量是否显著减少
            if orderbook.ask1_vol > 0:
                # 如果tick的ask1_vol明显小于orderbook的ask1_vol，说明吃掉了大量卖单
                ratio = tick.ask1_vol / orderbook.ask1_vol if orderbook.ask1_vol > 0 else 0
                if ratio < 0.5:  # 减少了超过50%
                    return True
            
            # 检查价格冲击
            price_impact = (tick.price - orderbook.ask1_price) / orderbook.ask1_price
            if price_impact > self.price_impact_threshold:
                return True
        
        elif direction == 'sell':
            # 检查买一量是否显著减少
            if orderbook.bid1_vol > 0:
                ratio = tick.bid1_vol / orderbook.bid1_vol if orderbook.bid1_vol > 0 else 0
                if ratio < 0.5:
                    return True
            
            # 检查价格冲击
            price_impact = (orderbook.bid1_price - tick.price) / orderbook.bid1_price
            if price_impact > self.price_impact_threshold:
                return True
        
        return False
    
    @staticmethod
    def create_orderbook_from_tick(tick: Tick) -> OrderBook:
        """
        从Tick创建订单簿快照
        
        Args:
            tick: Tick数据
        
        Returns:
            OrderBook对象
        """
        return OrderBook(
            bid1_price=tick.bid1_price,
            bid1_vol=tick.bid1_vol,
            ask1_price=tick.ask1_price,
            ask1_vol=tick.ask1_vol,
            bid2_price=getattr(tick, 'bid2_price', None),
            bid2_vol=getattr(tick, 'bid2_vol', None),
            bid3_price=getattr(tick, 'bid3_price', None),
            bid3_vol=getattr(tick, 'bid3_vol', None),
            bid4_price=getattr(tick, 'bid4_price', None),
            bid4_vol=getattr(tick, 'bid4_vol', None),
            bid5_price=getattr(tick, 'bid5_price', None),
            bid5_vol=getattr(tick, 'bid5_vol', None),
            ask2_price=getattr(tick, 'ask2_price', None),
            ask2_vol=getattr(tick, 'ask2_vol', None),
            ask3_price=getattr(tick, 'ask3_price', None),
            ask3_vol=getattr(tick, 'ask3_vol', None),
            ask4_price=getattr(tick, 'ask4_price', None),
            ask4_vol=getattr(tick, 'ask4_vol', None),
            ask5_price=getattr(tick, 'ask5_price', None),
            ask5_vol=getattr(tick, 'ask5_vol', None),
        )

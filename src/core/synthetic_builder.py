"""订单重构引擎（模块二）"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import numpy as np
from ..models.tick import Tick
from ..models.order import SyntheticOrder
from ..utils.logger import get_logger

logger = get_logger("synthetic_builder")


class TickBuffer:
    """Tick缓冲区 - 用于时间窗聚合"""
    
    def __init__(self, window_sec: int = 30):
        """
        初始化Tick缓冲区
        
        Args:
            window_sec: 时间窗口（秒）
        """
        self.window_sec = window_sec
        self.buy_ticks: List[Tick] = []  # 买入tick列表
        self.sell_ticks: List[Tick] = []  # 卖出tick列表
    
    def add_tick(self, tick: Tick, label: str):
        """
        添加tick到对应方向缓冲区
        
        Args:
            tick: Tick数据
            label: 分类标签
        """
        if label in ['AGG_BUY', 'DEF_BUY', 'SMALL_BUY']:
            self.buy_ticks.append(tick)
        elif label in ['AGG_SELL', 'DEF_SELL', 'SMALL_SELL']:
            self.sell_ticks.append(tick)
        else:
            # 噪音，不处理
            return
        
        # 清理过期tick
        self._cleanup_old_ticks()
    
    def try_generate_synthetic(self, threshold: float) -> List[SyntheticOrder]:
        """
        尝试生成合成订单
        
        Args:
            threshold: 合成阈值（元）
        
        Returns:
            生成的合成订单列表
        """
        orders = []
        
        # 检查买入方向
        buy_order = self._check_and_generate(self.buy_ticks, 'BUY', threshold)
        if buy_order:
            orders.append(buy_order)
            self.buy_ticks.clear()
        
        # 检查卖出方向
        sell_order = self._check_and_generate(self.sell_ticks, 'SELL', threshold)
        if sell_order:
            orders.append(sell_order)
            self.sell_ticks.clear()
        
        return orders
    
    def _check_and_generate(self, ticks: List[Tick], direction: str, 
                           threshold: float) -> Optional[SyntheticOrder]:
        """
        检查并生成合成订单
        
        Args:
            ticks: Tick列表
            direction: 买卖方向
            threshold: 合成阈值
        
        Returns:
            合成订单，如果未达到阈值则返回None
        """
        if not ticks:
            return None
        
        # 计算总金额
        total_amount = sum(t.amount for t in ticks)
        
        # 累计金额达到阈值
        if total_amount >= threshold:
            # 计算VWAP
            total_volume = sum(t.volume for t in ticks)
            vwap = total_amount / total_volume if total_volume > 0 else 0
            
            # 检测是否为算法交易
            order_type, confidence = self._detect_algo_pattern(ticks)
            
            return SyntheticOrder(
                start_time=ticks[0].timestamp,
                end_time=ticks[-1].timestamp,
                symbol=ticks[0].symbol,
                direction=direction,
                total_volume=total_volume,
                total_amount=total_amount,
                vwap=vwap,
                tick_count=len(ticks),
                order_type=order_type,
                confidence=confidence,
                original_ticks=ticks[:]
            )
        
        return None
    
    def _detect_algo_pattern(self, ticks: List[Tick]) -> tuple:
        """
        检测算法交易模式
        
        识别TWAP（时间加权平均价格）和VWAP（成交量加权平均价格）算法
        
        Args:
            ticks: Tick列表
        
        Returns:
            (order_type, confidence)
            order_type: ALGO_TWAP, ALGO_VWAP, SYNTHETIC
            confidence: 0.0-2.0
        """
        if len(ticks) < 3:
            # tick数量太少，无法判断
            return ('SYNTHETIC', 1.0)
        
        # 计算时间间隔
        intervals = []
        for i in range(1, len(ticks)):
            interval = (ticks[i].timestamp - ticks[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        # 时间间隔方差
        interval_variance = np.var(intervals)
        
        # 判断是否为TWAP（时间间隔稳定）
        if interval_variance < 1.0:  # 方差小于1秒
            logger.debug(f"Detected TWAP pattern: variance={interval_variance:.3f}")
            return ('ALGO_TWAP', 1.3)
        
        # 判断是否为VWAP（金额接近）
        amounts = [t.amount for t in ticks]
        amount_variance = np.var(amounts)
        avg_amount = np.mean(amounts)
        
        if avg_amount > 0:
            amount_cv = np.sqrt(amount_variance) / avg_amount  # 变异系数
            if amount_cv < 0.3:  # 变异系数小于30%
                logger.debug(f"Detected VWAP pattern: CV={amount_cv:.3f}")
                return ('ALGO_VWAP', 1.3)
        
        # 检查是否为单一方向（单向度）
        directions = [t.direction for t in ticks]
        unique_directions = set(directions)
        
        if len(unique_directions) == 1:
            # 单向度高，给予更高置信度
            return ('SYNTHETIC', 1.1)
        
        return ('SYNTHETIC', 1.0)
    
    def _cleanup_old_ticks(self):
        """清理过期的tick"""
        cutoff = datetime.now() - timedelta(seconds=self.window_sec)
        
        self.buy_ticks = [t for t in self.buy_ticks if t.timestamp >= cutoff]
        self.sell_ticks = [t for t in self.sell_ticks if t.timestamp >= cutoff]
    
    def flush_synthetic(self) -> List[SyntheticOrder]:
        """
        刷新并生成所有剩余的合成订单（用于交易日结束）
        
        Returns:
            剩余的合成订单列表
        """
        orders = []
        
        # 强制生成买入订单（即使未达到阈值）
        if self.buy_ticks:
            total_amount = sum(t.amount for t in self.buy_ticks)
            if total_amount > 0:
                total_volume = sum(t.volume for t in self.buy_ticks)
                vwap = total_amount / total_volume if total_volume > 0 else 0
                order_type, confidence = self._detect_algo_pattern(self.buy_ticks)
                
                orders.append(SyntheticOrder(
                    start_time=self.buy_ticks[0].timestamp,
                    end_time=self.buy_ticks[-1].timestamp,
                    symbol=self.buy_ticks[0].symbol,
                    direction='BUY',
                    total_volume=total_volume,
                    total_amount=total_amount,
                    vwap=vwap,
                    tick_count=len(self.buy_ticks),
                    order_type=order_type,
                    confidence=confidence * 0.5,  # 未达阈值，降低置信度
                    original_ticks=self.buy_ticks[:]
                ))
        
        # 强制生成卖出订单
        if self.sell_ticks:
            total_amount = sum(t.amount for t in self.sell_ticks)
            if total_amount > 0:
                total_volume = sum(t.volume for t in self.sell_ticks)
                vwap = total_amount / total_volume if total_volume > 0 else 0
                order_type, confidence = self._detect_algo_pattern(self.sell_ticks)
                
                orders.append(SyntheticOrder(
                    start_time=self.sell_ticks[0].timestamp,
                    end_time=self.sell_ticks[-1].timestamp,
                    symbol=self.sell_ticks[0].symbol,
                    direction='SELL',
                    total_volume=total_volume,
                    total_amount=total_amount,
                    vwap=vwap,
                    tick_count=len(self.sell_ticks),
                    order_type=order_type,
                    confidence=confidence * 0.5,
                    original_ticks=self.sell_ticks[:]
                ))
        
        # 清空缓冲区
        self.buy_ticks.clear()
        self.sell_ticks.clear()
        
        return orders
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """
        获取缓冲区统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'buy_ticks_count': len(self.buy_ticks),
            'sell_ticks_count': len(self.sell_ticks),
            'buy_amount': sum(t.amount for t in self.buy_ticks),
            'sell_amount': sum(t.amount for t in self.sell_ticks),
        }


class SyntheticOrderBuilder:
    """合成订单构建器 - 重构被拆分的大单"""
    
    def __init__(self, window_sec: int = 30, threshold: float = 500000):
        """
        初始化合成订单构建器
        
        Args:
            window_sec: 时间窗口（秒）
            threshold: 合成阈值（元）
        """
        self.window_sec = window_sec
        self.threshold = threshold
        self.buffers: Dict[str, TickBuffer] = {}  # 每个股票的tick缓冲区
        
        logger.info(f"SyntheticOrderBuilder initialized: window={window_sec}s, threshold={threshold}")
    
    def feed(self, tick: Tick, label: str) -> List[SyntheticOrder]:
        """
        喂入tick数据
        
        Args:
            tick: Tick数据
            label: 分类标签
        
        Returns:
            生成的合成订单列表
        """
        symbol = tick.symbol
        
        # 初始化该股票的缓冲区
        if symbol not in self.buffers:
            self.buffers[symbol] = TickBuffer(self.window_sec)
        
        # 添加到缓冲区
        self.buffers[symbol].add_tick(tick, label)
        
        # 检查是否需要生成合成订单
        synthetic_orders = self.buffers[symbol].try_generate_synthetic(self.threshold)
        
        if synthetic_orders:
            for order in synthetic_orders:
                logger.debug(
                    f"Generated synthetic order: {order.symbol} {order.direction} "
                    f"{order.total_amount:.0f}元 {order.order_type}"
                )
        
        return synthetic_orders
    
    def get_flushed_orders(self, symbol: Optional[str] = None) -> List[SyntheticOrder]:
        """
        获取所有待处理的合成订单（用于交易日结束）
        
        Args:
            symbol: 股票代码，如果为None则获取所有股票的订单
        
        Returns:
            合成订单列表
        """
        orders = []
        
        if symbol:
            # 获取指定股票的订单
            if symbol in self.buffers:
                orders.extend(self.buffers[symbol].flush_synthetic())
        else:
            # 获取所有股票的订单
            for buffer in self.buffers.values():
                orders.extend(buffer.flush_synthetic())
        
        return orders
    
    def get_buffer_stats(self, symbol: str) -> Optional[Dict[str, int]]:
        """
        获取指定股票的缓冲区统计信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            统计信息字典，如果股票不存在则返回None
        """
        if symbol not in self.buffers:
            return None
        
        return self.buffers[symbol].get_buffer_stats()
    
    def clear(self, symbol: Optional[str] = None):
        """
        清空缓冲区
        
        Args:
            symbol: 股票代码，如果为None则清空所有缓冲区
        """
        if symbol:
            if symbol in self.buffers:
                del self.buffers[symbol]
        else:
            self.buffers.clear()
        
        logger.debug(f"Cleared buffer{'s' if not symbol else f' for {symbol}'}")

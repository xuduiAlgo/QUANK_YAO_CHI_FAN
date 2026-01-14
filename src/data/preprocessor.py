"""数据预处理"""
from typing import List
from ..models.tick import Tick
from ..utils.logger import get_logger
from ..utils.validators import DataValidator

logger = get_logger("preprocessor")


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self):
        """初始化数据预处理器"""
        self.validator = DataValidator()
        logger.info("DataPreprocessor initialized")
    
    def clean_tick_data(self, ticks: List[Tick]) -> List[Tick]:
        """
        清洗tick数据
        
        Args:
            ticks: 原始tick数据列表
        
        Returns:
            清洗后的tick数据列表
        """
        if not ticks:
            logger.warning("No ticks to clean")
            return []
        
        cleaned = []
        removed_count = 0
        
        for tick in ticks:
            try:
                # 验证价格范围
                if not self.validator.validate_price_range(tick.price):
                    removed_count += 1
                    continue
                
                # 验证成交量
                if not self.validator.validate_volume(tick.volume):
                    removed_count += 1
                    continue
                
                # 验证买卖方向
                if not self.validator.validate_direction(tick.direction):
                    removed_count += 1
                    continue
                
                # 验证金额匹配
                if tick.amount > 0 and tick.volume > 0 and tick.price > 0:
                    if not self.validator.validate_amount(tick.amount, tick.volume, tick.price):
                        removed_count += 1
                        continue
                
                # 验证盘口数据
                if not self._validate_orderbook(tick):
                    removed_count += 1
                    continue
                
                cleaned.append(tick)
            
            except Exception as e:
                logger.warning(f"Failed to clean tick: {e}")
                removed_count += 1
                continue
        
        logger.info(f"Data cleaning completed: {len(cleaned)} valid, {removed_count} removed")
        
        return cleaned
    
    def _validate_orderbook(self, tick: Tick) -> bool:
        """
        验证订单簿数据
        
        Args:
            tick: Tick数据
        
        Returns:
            是否有效
        """
        # 买一价应该小于卖一价
        if tick.bid1_price > 0 and tick.ask1_price > 0:
            if tick.bid1_price >= tick.ask1_price:
                return False
        
        # 买一价应该小于等于成交价
        if tick.bid1_price > 0 and tick.price > 0:
            if tick.bid1_price > tick.price:
                return False
        
        # 卖一价应该大于等于成交价
        if tick.ask1_price > 0 and tick.price > 0:
            if tick.ask1_price < tick.price:
                return False
        
        return True
    
    def remove_duplicates(self, ticks: List[Tick]) -> List[Tick]:
        """
        去除重复的tick数据
        
        Args:
            ticks: tick数据列表
        
        Returns:
            去重后的tick数据列表
        """
        if not ticks:
            return []
        
        # 使用(timestamp, price, volume, direction)作为唯一键
        seen = set()
        unique_ticks = []
        
        for tick in ticks:
            key = (tick.timestamp, tick.price, tick.volume, tick.direction)
            if key not in seen:
                seen.add(key)
                unique_ticks.append(tick)
        
        removed_count = len(ticks) - len(unique_ticks)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate ticks")
        
        return unique_ticks
    
    def sort_by_time(self, ticks: List[Tick]) -> List[Tick]:
        """
        按时间排序tick数据
        
        Args:
            ticks: tick数据列表
        
        Returns:
            排序后的tick数据列表
        """
        return sorted(ticks, key=lambda x: x.timestamp)
    
    def filter_by_time(self, ticks: List[Tick], start_time, end_time) -> List[Tick]:
        """
        按时间范围过滤tick数据
        
        Args:
            ticks: tick数据列表
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            过滤后的tick数据列表
        """
        filtered = [t for t in ticks if start_time <= t.timestamp <= end_time]
        logger.info(f"Filtered {len(filtered)} ticks in time range")
        return filtered
    
    def aggregate_trades(self, ticks: List[Tick], time_window_sec: int = 1) -> List[Tick]:
        """
        聚合tick数据
        
        将同一时间窗口内的tick合并为一条
        
        Args:
            ticks: tick数据列表
            time_window_sec: 时间窗口（秒）
        
        Returns:
            聚合后的tick数据列表
        """
        if not ticks:
            return []
        
        # 按时间排序
        sorted_ticks = self.sort_by_time(ticks)
        
        aggregated = []
        current_window = []
        window_start = sorted_ticks[0].timestamp
        
        for tick in sorted_ticks:
            # 检查是否超出时间窗口
            if (tick.timestamp - window_start).total_seconds() > time_window_sec:
                # 聚合当前窗口的tick
                if current_window:
                    agg_tick = self._aggregate_tick_list(current_window)
                    aggregated.append(agg_tick)
                
                # 开始新窗口
                current_window = [tick]
                window_start = tick.timestamp
            else:
                current_window.append(tick)
        
        # 处理最后一个窗口
        if current_window:
            agg_tick = self._aggregate_tick_list(current_window)
            aggregated.append(agg_tick)
        
        logger.info(f"Aggregated {len(ticks)} ticks into {len(aggregated)} records")
        
        return aggregated
    
    def _aggregate_tick_list(self, ticks: List[Tick]) -> Tick:
        """
        聚合tick列表为单条tick
        
        Args:
            ticks: tick列表
        
        Returns:
            聚合后的tick
        """
        # 使用VWAP作为价格
        total_amount = sum(t.amount for t in ticks)
        total_volume = sum(t.volume for t in ticks)
        avg_price = total_amount / total_volume if total_volume > 0 else 0
        
        # 使用最后一条tick的盘口数据
        last_tick = ticks[-1]
        
        # 使用时间加权平均作为时间戳
        total_seconds = sum(t.timestamp.timestamp() for t in ticks)
        avg_timestamp = total_seconds / len(ticks)
        
        from datetime import datetime
        avg_datetime = datetime.fromtimestamp(avg_timestamp)
        
        # 统计买卖方向
        directions = [t.direction for t in ticks]
        buy_count = sum(1 for d in directions if d in ['B', 'BUY'])
        sell_count = sum(1 for d in directions if d in ['S', 'SELL'])
        
        if buy_count > sell_count:
            dominant_direction = 'B'
        elif sell_count > buy_count:
            dominant_direction = 'S'
        else:
            dominant_direction = 'N'
        
        return Tick(
            timestamp=avg_datetime,
            symbol=ticks[0].symbol,
            price=avg_price,
            volume=total_volume,
            amount=total_amount,
            direction=dominant_direction,
            bid1_price=last_tick.bid1_price,
            bid1_vol=last_tick.bid1_vol,
            ask1_price=last_tick.ask1_price,
            ask1_vol=last_tick.ask1_vol
        )
    
    def calculate_statistics(self, ticks: List[Tick]) -> dict:
        """
        计算tick数据统计信息
        
        Args:
            ticks: tick数据列表
        
        Returns:
            统计信息字典
        """
        if not ticks:
            return {}
        
        stats = {
            'count': len(ticks),
            'total_volume': sum(t.volume for t in ticks),
            'total_amount': sum(t.amount for t in ticks),
            # Volume单位是"手"，Amount单位是"元"
            # 平均价格（元/股）= (Amount/Volume) / 100
            'avg_price': (sum(t.amount for t in ticks) / sum(t.volume for t in ticks) / 100) if sum(t.volume for t in ticks) > 0 else 0,
            'min_price': min(t.price for t in ticks),
            'max_price': max(t.price for t in ticks),
            'buy_count': sum(1 for t in ticks if t.direction in ['B', 'BUY']),
            'sell_count': sum(1 for t in ticks if t.direction in ['S', 'SELL']),
            'big_order_count': sum(1 for t in ticks if t.amount >= 100000),
            'start_time': min(t.timestamp for t in ticks),
            'end_time': max(t.timestamp for t in ticks),
        }
        
        if stats['start_time'] and stats['end_time']:
            duration_seconds = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['duration_seconds'] = duration_seconds
            stats['avg_ticks_per_sec'] = stats['count'] / duration_seconds if duration_seconds > 0 else 0
        
        logger.debug(f"Tick statistics: {stats}")
        
        return stats

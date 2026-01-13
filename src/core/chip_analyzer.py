"""筹码分布分析（模块四）"""
from typing import List, Dict, Tuple
import numpy as np
from ..models.tick import Tick
from ..models.order import SyntheticOrder
from ..utils.logger import get_logger

logger = get_logger("chip_analyzer")


class ChipAnalyzer:
    """筹码分布分析器 - 验证主力成本线有效性"""
    
    def __init__(self):
        """初始化筹码分析器"""
        logger.info("ChipAnalyzer initialized")
    
    def build_chip_distribution(self, ticks: List[Tick], price_bins: int = 100) -> Dict[float, int]:
        """
        构建筹码分布图
        
        Args:
            ticks: Tick数据列表
            price_bins: 价格区间数量
        
        Returns:
            价格区间到持仓量的映射 {价格中心: 持仓量}
        """
        if not ticks:
            logger.warning("No ticks provided for chip distribution")
            return {}
        
        # 计算价格范围
        prices = [t.price for t in ticks]
        price_min, price_max = min(prices), max(prices)
        
        # 价格跨度太小时，使用固定范围
        if price_max - price_min < 0.01:
            price_min = price_max * 0.995
            price_max = price_max * 1.005
        
        price_step = (price_max - price_min) / price_bins
        
        # 初始化分布
        distribution = {}
        for i in range(price_bins):
            price_low = price_min + i * price_step
            price_high = price_low + price_step
            price_center = (price_low + price_high) / 2
            distribution[price_center] = 0
        
        # 分配成交到价格区间
        for tick in ticks:
            # 计算该tick所属的价格区间
            price_index = int((tick.price - price_min) / price_step)
            
            # 处理边界情况
            if price_index < 0:
                price_index = 0
            elif price_index >= price_bins:
                price_index = price_bins - 1
            
            price_center = price_min + (price_index + 0.5) * price_step
            price_center = round(price_center, 2)
            
            if price_center in distribution:
                distribution[price_center] += tick.volume
        
        logger.debug(f"Chip distribution built with {len(distribution)} price bins")
        
        return distribution
    
    def find_chip_peaks(self, distribution: Dict[float, int], 
                       top_n: int = 3) -> List[Tuple[float, int]]:
        """
        识别筹码峰位
        
        Args:
            distribution: 筹码分布字典 {价格: 持仓量}
            top_n: 返回前N个峰位
        
        Returns:
            [(价格, 持仓量), ...] 按持仓量降序
        """
        if not distribution:
            logger.warning("No distribution provided for peak detection")
            return []
        
        # 按持仓量降序排序
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        
        peaks = sorted_items[:top_n]
        
        logger.debug(f"Found {len(peaks)} chip peaks")
        
        return peaks
    
    def calculate_chip_center(self, distribution: Dict[float, int]) -> float:
        """
        计算筹码重心价格
        
        Args:
            distribution: 筹码分布字典
        
        Returns:
            重心价格
        """
        if not distribution:
            return 0.0
        
        total_volume = sum(distribution.values())
        if total_volume == 0:
            return 0.0
        
        weighted_sum = sum(price * volume for price, volume in distribution.items())
        center_price = weighted_sum / total_volume
        
        logger.debug(f"Chip center price: {center_price:.2f}")
        
        return center_price
    
    def calculate_concentration_ratio(self, distribution: Dict[float, int], 
                                    top_ratio: float = 0.2) -> float:
        """
        计算筹码集中度
        
        集中度 = 前20%价格区间的持仓量 / 总持仓量
        
        Args:
            distribution: 筹码分布字典
            top_ratio: 顶部价格区间比例
        
        Returns:
            集中度（0.0-1.0）
        """
        if not distribution:
            return 0.0
        
        # 按持仓量降序排序
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        total_volume = sum(volume for _, volume in sorted_items)
        
        if total_volume == 0:
            return 0.0
        
        # 计算顶部价格区间数量
        top_count = max(1, int(len(sorted_items) * top_ratio))
        top_volume = sum(volume for _, volume in sorted_items[:top_count])
        
        concentration = top_volume / total_volume
        
        logger.debug(f"Chip concentration ratio: {concentration:.2%}")
        
        return concentration
    
    def validate_cost_line(self, main_capital_cost: float, 
                          chip_distribution: Dict[float, int],
                          tolerance_ratio: float = 0.2) -> bool:
        """
        验证主力成本线是否有效
        
        验证逻辑：
        1. 主力成本应位于筹码密集区（峰位）下方或重心位置附近
        2. 如果成本远低于筹码峰位（例如下方20%），可能计算失效
        
        Args:
            main_capital_cost: 主力成本
            chip_distribution: 筹码分布
            tolerance_ratio: 容差比例
        
        Returns:
            是否有效
        """
        if not chip_distribution:
            logger.warning("No chip distribution for validation")
            return True
        
        # 获取筹码峰位
        peaks = self.find_chip_peaks(chip_distribution, top_n=1)
        if not peaks:
            logger.warning("No chip peaks found")
            return True
        
        peak_price, peak_volume = peaks[0]
        
        # 计算筹码重心
        center_price = self.calculate_chip_center(chip_distribution)
        
        # 验证逻辑1：主力成本应该接近筹码重心
        distance_to_center = abs(main_capital_cost - center_price) / center_price if center_price > 0 else float('inf')
        
        if distance_to_center > tolerance_ratio:
            logger.warning(
                f"Cost line validation failed: cost {main_capital_cost:.2f} "
                f"is far from chip center {center_price:.2f} (distance: {distance_to_center:.2%})"
            )
            return False
        
        # 验证逻辑2：主力成本不应远低于筹码峰位
        if peak_price > 0:
            distance_to_peak = abs(main_capital_cost - peak_price) / peak_price
            
            if distance_to_peak > tolerance_ratio:
                logger.warning(
                    f"Cost line validation warning: cost {main_capital_cost:.2f} "
                    f"is far from chip peak {peak_price:.2f} (distance: {distance_to_peak:.2%})"
                )
                # 这里返回True但发出警告，因为新主力可能在不同价位建仓
                # 不应该直接判为无效
                return True
        
        logger.info(f"Cost line validation passed: {main_capital_cost:.2f}")
        
        return True
    
    def calculate_support_resistance(self, distribution: Dict[float, int]) -> Dict[str, float]:
        """
        计算支撑位和压力位
        
        Args:
            distribution: 筹码分布
        
        Returns:
            {'support': 支撑位, 'resistance': 压力位}
        """
        if not distribution:
            return {'support': 0.0, 'resistance': 0.0}
        
        # 获取筹码峰位
        peaks = self.find_chip_peaks(distribution, top_n=1)
        if not peaks:
            return {'support': 0.0, 'resistance': 0.0}
        
        peak_price, _ = peaks[0]
        
        # 支撑位：筹码峰位下方
        prices = sorted(distribution.keys())
        peak_idx = prices.index(peak_price) if peak_price in prices else len(prices) // 2
        
        # 在峰位下方寻找支撑位
        support_candidates = [(p, v) for p, v in distribution.items() if p < peak_price]
        if support_candidates:
            support_price = max(support_candidates, key=lambda x: x[1])[0]
        else:
            support_price = min(prices) * 0.95
        
        # 压力位：筹码峰位上方
        resistance_candidates = [(p, v) for p, v in distribution.items() if p > peak_price]
        if resistance_candidates:
            resistance_price = max(resistance_candidates, key=lambda x: x[1])[0]
        else:
            resistance_price = max(prices) * 1.05
        
        result = {
            'support': support_price,
            'resistance': resistance_price,
            'peak': peak_price
        }
        
        logger.debug(f"Support/Resistance: support={support_price:.2f}, "
                   f"resistance={resistance_price:.2f}, peak={peak_price:.2f}")
        
        return result
    
    def analyze_chip_migration(self, old_distribution: Dict[float, int],
                             new_distribution: Dict[float, int]) -> Dict[str, any]:
        """
        分析筹码迁移
        
        Args:
            old_distribution: 旧筹码分布
            new_distribution: 新筹码分布
        
        Returns:
            迁移分析结果
        """
        old_center = self.calculate_chip_center(old_distribution)
        new_center = self.calculate_chip_center(new_distribution)
        
        # 计算重心移动方向和幅度
        if old_center > 0:
            migration_ratio = (new_center - old_center) / old_center
        else:
            migration_ratio = 0.0
        
        # 判断方向
        if abs(migration_ratio) < 0.01:
            direction = 'STABLE'
        elif migration_ratio > 0:
            direction = 'UPWARD'
        else:
            direction = 'DOWNWARD'
        
        result = {
            'old_center': old_center,
            'new_center': new_center,
            'migration_ratio': migration_ratio,
            'direction': direction,
        }
        
        logger.info(f"Chip migration: {direction}, ratio: {migration_ratio:.2%}")
        
        return result

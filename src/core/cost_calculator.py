"""成本计算模型（模块三）"""
from typing import List, Dict
import numpy as np
from ..models.order import SyntheticOrder
from ..utils.logger import get_logger

logger = get_logger("cost_calculator")


class CostCalculator:
    """成本计算器 - 计算主力加权平均成本"""
    
    def __init__(self):
        """初始化成本计算器"""
        # 权重映射表（统一为1.0，避免权重偏差扭曲净流向计算）
        # 说明：净流向应该反映真实的资金流动，不应该被订单类型权重扭曲
        self.weight_map = {
            'AGG_BUY': 1.0,      # 攻击性买入
            'AGG_SELL': 1.0,     # 攻击性卖出
            'DEF_BUY': 1.0,      # 防御性买入
            'DEF_SELL': 1.0,     # 防御性卖出
            'ALGO_TWAP': 1.0,    # TWAP算法交易
            'ALGO_VWAP': 1.0,    # VWAP算法交易
            'SYNTHETIC': 1.0,    # 普通合成订单
            'ORIGINAL': 1.0,     # 原始大单
            'SMALL_ORDER': 0.0,  # 小单 - 不参与计算
            'NOISE': 0.0,        # 噪音 - 不参与计算
        }
        
        logger.info("CostCalculator initialized with unified weights (1.0)")
    
    def calculate_weighted_cost(self, orders: List[SyntheticOrder]) -> float:
        """
        计算加权平均成本（VWAP）
        
        公式:
        Weighted_Cost = Σ(Price_i × Volume_i × Weight_i) / Σ(Volume_i × Weight_i)
        
        Args:
            orders: 订单列表
        
        Returns:
            加权平均成本
        """
        if not orders:
            logger.warning("No orders provided for cost calculation")
            return 0.0
        
        numerator = 0.0  # 分子：Σ(Price × Volume × Weight)
        denominator = 0.0  # 分母：Σ(Volume × Weight)
        
        for order in orders:
            # 只计算买入订单的成本
            if order.direction == 'BUY':
                weight = self.weight_map.get(order.order_type, 1.0)
                weight = weight * order.confidence
                
                # 跳过权重为0的订单（小单、噪音）
                if weight == 0:
                    continue
                
                # Volume单位是"手"，Amount单位是"元"
                # 1手 = 100股，所以价格（元/股）= (Amount / 100) / Volume
                # 或者简化为：价格 = (Amount / Volume) / 100
                weighted_volume = order.total_volume * weight
                weighted_amount = (order.total_amount / 100) * weight  # 转换为"元/手"
                
                numerator += weighted_amount
                denominator += weighted_volume
        
        if denominator == 0:
            logger.warning("No valid buy orders for cost calculation")
            return 0.0
        
        cost = numerator / denominator
        logger.debug(f"Calculated weighted cost: {cost:.2f}")
        
        return cost
    
    def calculate_cost_ma(self, daily_costs: List[float], period: int) -> float:
        """
        计算主力成本移动平均线
        
        Args:
            daily_costs: 历史每日成本列表 [cost_today, cost_yesterday, ...]
            period: 均线周期（如5日、10日、20日）
        
        Returns:
            移动平均值
        """
        if not daily_costs:
            logger.warning("No daily costs provided for MA calculation")
            return 0.0
        
        if len(daily_costs) < period:
            # 数据不足，返回现有数据的平均值
            ma_value = np.mean(daily_costs)
            logger.debug(f"MA({period}) calculated with {len(daily_costs)} data points: {ma_value:.2f}")
            return ma_value
        
        # 计算移动平均
        ma_value = np.mean(daily_costs[:period])
        logger.debug(f"MA({period}): {ma_value:.2f}")
        
        return ma_value
    
    def calculate_net_flow(self, orders: List[SyntheticOrder], 
                          float_market_cap: float) -> float:
        """
        计算主力净流向
        
        公式:
        Net_Flow = (Weighted_In - Weighted_Out) / Float_Market_Cap
        
        Args:
            orders: 订单列表
            float_market_cap: 流通市值（元）
        
        Returns:
            净流向比例（-1.0 到 1.0）
        """
        weighted_in = 0.0
        weighted_out = 0.0
        
        # 调试：按类型统计
        agg_buy_total = 0.0
        agg_sell_total = 0.0
        def_buy_total = 0.0
        def_sell_total = 0.0
        
        for order in orders:
            # 直接使用weight_map中的权重（统一为1.0），不乘confidence
            # 因为confidence是classifier返回的订单类型权重（如AGG_BUY=1.5, DEF_SELL=0.8）
            # 但我们设计上要求净流向计算使用统一权重1.0，避免扭曲资金流动
            weight = self.weight_map.get(order.order_type, 1.0)
            
            if order.direction == 'BUY':
                weighted_in += order.total_amount * weight
                
                # 调试：按类型统计
                if order.order_type == 'AGG_BUY':
                    agg_buy_total += order.total_amount
                elif order.order_type == 'DEF_BUY':
                    def_buy_total += order.total_amount
            else:
                weighted_out += order.total_amount * weight
                
                # 调试：按类型统计
                if order.order_type == 'AGG_SELL':
                    agg_sell_total += order.total_amount
                elif order.order_type == 'DEF_SELL':
                    def_sell_total += order.total_amount
        
        if float_market_cap == 0:
            logger.warning("Float market cap is zero")
            return 0.0
        
        net_flow = (weighted_in - weighted_out) / float_market_cap
        
        logger.debug(f"Net flow: {net_flow:.4%} (in: {weighted_in:.0f}, out: {weighted_out:.0f})")
        logger.debug(f"  AGG_BUY: {agg_buy_total:.0f}, AGG_SELL: {agg_sell_total:.0f}")
        logger.debug(f"  DEF_BUY: {def_buy_total:.0f}, DEF_SELL: {def_sell_total:.0f}")
        logger.debug(f"  Total: {weighted_in:.0f} - {weighted_out:.0f} = {weighted_in - weighted_out:.0f}")
        logger.debug(f"  Flow: {net_flow:.6%}")
        
        return net_flow
    
    def calculate_order_statistics(self, orders: List[SyntheticOrder]) -> Dict[str, any]:
        """
        计算订单统计信息
        
        Args:
            orders: 订单列表
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_orders': len(orders),
            'big_order_count': 0,  # 原始大单
            'synthetic_order_count': 0,  # 合成订单
            'algo_order_count': 0,  # 算法订单
            'aggressive_buy_amount': 0.0,
            'aggressive_sell_amount': 0.0,
            'defensive_buy_amount': 0.0,
            'defensive_sell_amount': 0.0,
            'algo_buy_amount': 0.0,
            'algo_sell_amount': 0.0,
        }
        
        for order in orders:
            # 统计订单类型
            if order.order_type in ['AGG_BUY', 'AGG_SELL', 'DEF_BUY', 'DEF_SELL']:
                stats['big_order_count'] += 1
            elif order.order_type == 'SYNTHETIC':
                stats['synthetic_order_count'] += 1
            elif order.order_type in ['ALGO_TWAP', 'ALGO_VWAP']:
                stats['algo_order_count'] += 1
            
            # 统计资金流向
            if order.order_type == 'AGG_BUY':
                stats['aggressive_buy_amount'] += order.total_amount
            elif order.order_type == 'AGG_SELL':
                stats['aggressive_sell_amount'] += order.total_amount
            elif order.order_type == 'DEF_BUY':
                stats['defensive_buy_amount'] += order.total_amount
            elif order.order_type == 'DEF_SELL':
                stats['defensive_sell_amount'] += order.total_amount
            elif order.order_type in ['ALGO_TWAP', 'ALGO_VWAP']:
                if order.direction == 'BUY':
                    stats['algo_buy_amount'] += order.total_amount
                else:
                    stats['algo_sell_amount'] += order.total_amount
        
        logger.debug(f"Order statistics: {stats}")
        
        return stats
    
    def calculate_cost_distribution(self, orders: List[SyntheticOrder], 
                                  n_bins: int = 10) -> Dict[str, List]:
        """
        计算成本分布
        
        Args:
            orders: 订单列表
            n_bins: 分箱数量
        
        Returns:
            分布信息字典
        """
        buy_orders = [o for o in orders if o.direction == 'BUY']
        
        if not buy_orders:
            return {'prices': [], 'volumes': [], 'amounts': []}
        
        # 提取价格、成交量、成交额
        prices = [o.vwap for o in buy_orders]
        volumes = [o.total_volume for o in buy_orders]
        amounts = [o.total_amount for o in buy_orders]
        
        # 分箱统计
        price_min, price_max = min(prices), max(prices)
        bin_edges = np.linspace(price_min, price_max, n_bins + 1)
        
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        bin_volumes = np.zeros(n_bins)
        bin_amounts = np.zeros(n_bins)
        
        for price, volume, amount in zip(prices, volumes, amounts):
            # 找到对应的箱子
            bin_idx = np.digitize(price, bin_edges) - 1
            if 0 <= bin_idx < n_bins:
                bin_volumes[bin_idx] += volume
                bin_amounts[bin_idx] += amount
        
        distribution = {
            'bin_centers': bin_centers.tolist(),
            'bin_volumes': bin_volumes.tolist(),
            'bin_amounts': bin_amounts.tolist(),
        }
        
        logger.debug(f"Cost distribution calculated with {n_bins} bins")
        
        return distribution

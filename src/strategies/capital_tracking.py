"""资金追踪策略"""
from typing import List, Dict
from ..models.tick import Tick
from ..models.result import CapitalAnalysisResult
from ..models.order import SyntheticOrder
from ..core.classifier import TickClassifier
from ..core.synthetic_builder import SyntheticOrderBuilder
from ..core.cost_calculator import CostCalculator
from ..core.chip_analyzer import ChipAnalyzer
from ..utils.logger import get_logger
from .base import StrategyBase

logger = get_logger("capital_tracking")


class CapitalTrackingStrategy(StrategyBase):
    """资金追踪策略 - 整合所有核心模块"""
    
    def __init__(self, config: Dict):
        """
        初始化资金追踪策略
        
        Args:
            config: 配置字典，包含：
                - window_sec: 时间窗口（秒）
                - synthetic_threshold: 合成阈值（元）
                - big_order_threshold: 大单阈值（元）
                - wall_threshold: 城墙单阈值（手）
                - ma_periods: 均线周期列表 [5, 10, 20]
        """
        super().__init__(config)
        
        # 初始化各模块
        self.classifier = TickClassifier(config)
        self.synthetic_builder = SyntheticOrderBuilder(
            window_sec=config.get('window_sec', 30),
            threshold=config.get('synthetic_threshold', 500000)
        )
        self.cost_calculator = CostCalculator()
        self.chip_analyzer = ChipAnalyzer()
        
        # 配置参数
        self.ma_periods = config.get('ma_periods', [5, 10, 20])
        
        logger.info(f"CapitalTrackingStrategy initialized with config: {config}")
    
    def analyze_day(self, symbol: str, date: str, 
                   tick_data: List[Tick]) -> CapitalAnalysisResult:
        """
        分析单日数据
        
        流程：
        1. 对每笔tick进行分类
        2. 合成大单
        3. 计算成本
        4. 筹码分析验证
        5. 构建结果
        
        Args:
            symbol: 股票代码
            date: 日期
            tick_data: tick数据列表
        
        Returns:
            分析结果
        """
        logger.info(f"Starting analysis for {symbol} {date}, {len(tick_data)} ticks")
        
        # 初始化订单列表
        all_orders = []
        
        # 遍历所有tick
        for tick in tick_data:
            # 步骤1: 分类
            label, weight = self.classifier.classify_tick(tick, None)
            
            # 步骤2: 合成大单
            synthetic_orders = self.synthetic_builder.feed(tick, label)
            all_orders.extend(synthetic_orders)
        
        # 获取所有剩余的合成订单（交易日结束）
        all_orders.extend(self.synthetic_builder.get_flushed_orders(symbol))
        
        logger.info(f"Generated {len(all_orders)} orders ({len([o for o in all_orders if o.order_type in ['AGG_BUY', 'AGG_SELL']])} original, "
                   f"{len([o for o in all_orders if o.order_type == 'SYNTHETIC'])} synthetic, "
                   f"{len([o for o in all_orders if o.order_type in ['ALGO_TWAP', 'ALGO_VWAP']])} algo)")
        
        # 步骤3: 计算加权成本
        weighted_cost = self.cost_calculator.calculate_weighted_cost(all_orders)
        
        # 步骤4: 计算订单统计
        order_stats = self.cost_calculator.calculate_order_statistics(all_orders)
        
        # 步骤5: 计算净流向（需要流通市值，这里先使用简化版本）
        net_flow = self.cost_calculator.calculate_net_flow(all_orders, 
                                                       self._estimate_float_cap(tick_data))
        
        # 步骤6: 筹码分析
        chip_distribution = self.chip_analyzer.build_chip_distribution(tick_data)
        chip_peaks = self.chip_analyzer.find_chip_peaks(chip_distribution, top_n=1)
        concentration = self.chip_analyzer.calculate_concentration_ratio(chip_distribution)
        
        # 步骤7: 验证成本线
        chip_peak_price = chip_peaks[0][0] if chip_peaks else 0
        validation_status = 'VALID'
        
        if weighted_cost > 0 and chip_peak_price > 0:
            is_valid = self.chip_analyzer.validate_cost_line(weighted_cost, chip_distribution)
            validation_status = 'VALID' if is_valid else 'INVALID'
        
        # 步骤8: 计算支撑压力位
        sr = self.chip_analyzer.calculate_support_resistance(chip_distribution)
        
        logger.info(f"Analysis completed: cost={weighted_cost:.2f}, net_flow={net_flow:.4%}, "
                   f"validation={validation_status}")
        
        # 构建结果
        result = CapitalAnalysisResult(
            symbol=symbol,
            date=date,
            weighted_cost=weighted_cost,
            cost_ma_5=0.0,  # 需要历史数据，稍后计算
            cost_ma_10=0.0,
            cost_ma_20=0.0,
            net_flow=net_flow,
            aggressive_buy_amount=order_stats['aggressive_buy_amount'],
            aggressive_sell_amount=order_stats['aggressive_sell_amount'],
            defensive_buy_amount=order_stats['defensive_buy_amount'],
            defensive_sell_amount=order_stats['defensive_sell_amount'],
            algo_buy_amount=order_stats['algo_buy_amount'],
            algo_sell_amount=order_stats['algo_sell_amount'],
            concentration_ratio=concentration,
            chip_peak_price=chip_peak_price,
            support_price=sr.get('support', 0.0),
            resistance_price=sr.get('resistance', 0.0),
            validation_status=validation_status,
            total_orders=order_stats['total_orders'],
            big_order_count=order_stats['big_order_count'],
            synthetic_order_count=order_stats['synthetic_order_count'],
            algo_order_count=order_stats['algo_order_count']
        )
        
        return result
    
    def analyze_period(self, symbol: str, start_date: str, 
                      end_date: str, tick_data_dict: Dict[str, List[Tick]]) -> List[CapitalAnalysisResult]:
        """
        分析一段时间的数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            tick_data_dict: 日期到tick数据的映射
        
        Returns:
            分析结果列表
        """
        results = []
        
        # 按日期排序
        sorted_dates = sorted(tick_data_dict.keys())
        
        # 历史成本列表，用于计算均线
        historical_costs = []
        
        for date in sorted_dates:
            if start_date <= date <= end_date:
                logger.info(f"Analyzing {symbol} {date}")
                
                # 分析单日
                result = self.analyze_day(symbol, date, tick_data_dict[date])
                
                # 计算均线
                historical_costs.insert(0, result.weighted_cost)  # 最新的在前
                
                for period in self.ma_periods:
                    ma_value = self.cost_calculator.calculate_cost_ma(historical_costs, period)
                    if period == 5:
                        result.cost_ma_5 = ma_value
                    elif period == 10:
                        result.cost_ma_10 = ma_value
                    elif period == 20:
                        result.cost_ma_20 = ma_value
                
                results.append(result)
        
        logger.info(f"Period analysis completed: {len(results)} days")
        
        return results
    
    def _estimate_float_cap(self, ticks: List[Tick]) -> float:
        """
        估算流通市值
        
        这里使用简化版本：当日成交金额 / 换手率
        如果没有换手率数据，返回0，净流向计算会跳过
        
        Args:
            ticks: tick数据列表
        
        Returns:
            流通市值（元）
        """
        if not ticks:
            return 0.0
        
        # 计算当日成交金额
        total_amount = sum(t.amount for t in ticks)
        
        # 这里简化处理，实际应该从数据源获取流通市值
        # 返回一个足够大的值，使得净流向比例合理
        # 假设换手率为5%
        estimated_float_cap = total_amount / 0.05 if total_amount > 0 else 0
        
        return estimated_float_cap
    
    def update_ma_values(self, results: List[CapitalAnalysisResult]) -> List[CapitalAnalysisResult]:
        """
        更新结果中的均线值
        
        Args:
            results: 分析结果列表
        
        Returns:
            更新后的结果列表
        """
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date, reverse=True)
        
        # 计算均线
        historical_costs = []
        
        for result in sorted_results:
            historical_costs.insert(0, result.weighted_cost)
            
            for period in self.ma_periods:
                ma_value = self.cost_calculator.calculate_cost_ma(historical_costs, period)
                if period == 5:
                    result.cost_ma_5 = ma_value
                elif period == 10:
                    result.cost_ma_10 = ma_value
                elif period == 20:
                    result.cost_ma_20 = ma_value
        
        # 恢复原始顺序
        return sorted(results_results, key=lambda x: x.date, reverse=True)
    
    def get_signal(self, result: CapitalAnalysisResult) -> str:
        """
        根据分析结果生成交易信号
        
        Args:
            result: 分析结果
        
        Returns:
            信号类型：BUY, SELL, HOLD
        """
        # 净流向为正且超过阈值 -> 买入信号
        if result.net_flow > 0.01:  # 净流入超过1%
            return 'BUY'
        
        # 净流向为负且超过阈值 -> 卖出信号
        elif result.net_flow < -0.01:  # 净流出超过1%
            return 'SELL'
        
        # 成本线在均线下方且有支撑 -> 买入信号
        elif result.cost_ma_5 > 0 and result.weighted_cost < result.cost_ma_5 * 0.98:
            if result.net_flow > 0:
                return 'BUY'
        
        # 成本线在均线上方且接近压力位 -> 卖出信号
        elif result.cost_ma_5 > 0 and result.weighted_cost > result.cost_ma_5 * 1.02:
            if result.net_flow < 0:
                return 'SELL'
        
        return 'HOLD'
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            是否有效
        """
        required_keys = ['window_sec', 'synthetic_threshold', 'big_order_threshold']
        
        for key in required_keys:
            if key not in self.config:
                logger.error(f"Missing required config key: {key}")
                return False
        
        if self.config['window_sec'] <= 0:
            logger.error("window_sec must be positive")
            return False
        
        if self.config['synthetic_threshold'] <= 0:
            logger.error("synthetic_threshold must be positive")
            return False
        
        if self.config['big_order_threshold'] <= 0:
            logger.error("big_order_threshold must be positive")
            return False
        
        logger.info("Configuration validated successfully")
        return True

"""分析结果模型"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CapitalAnalysisResult:
    """资金分析结果模型"""
    
    symbol: str
    date: str
    
    # 资金流向统计
    aggressive_buy_amount: float       # 攻击性买入金额
    aggressive_sell_amount: float      # 攻击性卖出金额
    defensive_buy_amount: float        # 防御性买入金额
    defensive_sell_amount: float      # 防御性卖出金额
    algo_buy_amount: float             # 算法买入金额
    algo_sell_amount: float            # 算法卖出金额
    
    # 成本相关指标
    weighted_cost: float               # 加权主力成本
    cost_ma_5: Optional[float]         # 5日主力成本均线
    cost_ma_10: Optional[float]        # 10日主力成本均线
    cost_ma_20: Optional[float]        # 20日主力成本均线
    
    # 净流向
    net_flow: float                    # 净流向（比例）
    
    # 筹码分析
    concentration_ratio: float         # 筹码集中度
    chip_peak_price: float             # 筹码峰位价格
    chip_peak_volume: float            # 筹码峰位持仓量
    support_price: float               # 支撑位价格
    resistance_price: float            # 压力位价格
    
    # 验证状态
    validation_status: bool            # 成本线验证状态
    
    # 统计信息
    total_orders: int                  # 总订单数
    big_order_count: int               # 大单数量
    synthetic_order_count: int         # 合成订单数量
    algo_order_count: int              # 算法订单数量
    
    # 原始订单列表（可选）
    orders: Optional[List] = None
    
    def __post_init__(self):
        if self.orders is None:
            self.orders = []
    
    @property
    def total_buy_amount(self) -> float:
        """总买入金额"""
        return (self.aggressive_buy_amount + self.defensive_buy_amount + 
                self.algo_buy_amount)
    
    @property
    def total_sell_amount(self) -> float:
        """总卖出金额"""
        return (self.aggressive_sell_amount + self.defensive_sell_amount + 
                self.algo_sell_amount)
    
    @property
    def buy_sell_ratio(self) -> float:
        """买卖比率（买入/卖出）"""
        if self.total_sell_amount == 0:
            return float('inf') if self.total_buy_amount > 0 else 0.0
        return self.total_buy_amount / self.total_sell_amount
    
    @property
    def aggressiveness_score(self) -> float:
        """攻击性评分（攻击性买入/总买入）"""
        if self.total_buy_amount == 0:
            return 0.0
        return self.aggressive_buy_amount / self.total_buy_amount
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'date': self.date,
            'aggressive_buy_amount': self.aggressive_buy_amount,
            'aggressive_sell_amount': self.aggressive_sell_amount,
            'defensive_buy_amount': self.defensive_buy_amount,
            'defensive_sell_amount': self.defensive_sell_amount,
            'algo_buy_amount': self.algo_buy_amount,
            'algo_sell_amount': self.algo_sell_amount,
            'weighted_cost': self.weighted_cost,
            'cost_ma_5': self.cost_ma_5,
            'cost_ma_10': self.cost_ma_10,
            'cost_ma_20': self.cost_ma_20,
            'net_flow': self.net_flow,
            'concentration_ratio': self.concentration_ratio,
            'chip_peak_price': self.chip_peak_price,
            'chip_peak_volume': self.chip_peak_volume,
            'validation_status': self.validation_status,
            'total_orders': self.total_orders,
            'big_order_count': self.big_order_count,
            'synthetic_order_count': self.synthetic_order_count,
            'algo_order_count': self.algo_order_count,
            'total_buy_amount': self.total_buy_amount,
            'total_sell_amount': self.total_sell_amount,
            'buy_sell_ratio': self.buy_sell_ratio,
            'aggressiveness_score': self.aggressiveness_score,
        }
    
    def get_summary(self) -> str:
        """获取分析摘要"""
        summary = f"""
{'='*60}
资金分析报告 - {self.symbol} ({self.date})
{'='*60}

【资金流向】
  攻击性买入: {self.aggressive_buy_amount:,.0f} 元
  攻击性卖出: {self.aggressive_sell_amount:,.0f} 元
  防御性买入: {self.defensive_buy_amount:,.0f} 元
  防御性卖出: {self.defensive_sell_amount:,.0f} 元
  算法买入:   {self.algo_buy_amount:,.0f} 元
  算法卖出:   {self.algo_sell_amount:,.0f} 元
  净流向:     {self.net_flow:.2%}

【成本分析】
  主力成本:   {self.weighted_cost:.2f} 元
  5日均线:   {self.cost_ma_5:.2f if self.cost_ma_5 else 'N/A'} 元
  10日均线:  {self.cost_ma_10:.2f if self.cost_ma_10 else 'N/A'} 元
  20日均线:  {self.cost_ma_20:.2f if self.cost_ma_20 else 'N/A'} 元

【筹码分析】
  筹码集中度: {self.concentration_ratio:.2%}
  峰位价格:   {self.chip_peak_price:.2f} 元
  峰位持仓量: {self.chip_peak_volume:,.0f} 手

【订单统计】
  总订单数:   {self.total_orders}
  大单数量:   {self.big_order_count}
  合成订单数: {self.synthetic_order_count}
  算法订单数: {self.algo_order_count}

【综合指标】
  买卖比率:   {self.buy_sell_ratio:.2f}
  攻击性评分: {self.aggressiveness_score:.2%}
  成本验证:   {'✓ 有效' if self.validation_status else '✗ 无效'}
{'='*60}
"""
        return summary
    
    def __repr__(self) -> str:
        return f"CapitalAnalysisResult({self.symbol}, {self.date}, cost={self.weighted_cost:.2f})"

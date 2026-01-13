"""图表绘制模块"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from ..models.result import CapitalAnalysisResult
from ..utils.logger import get_logger

logger = get_logger("charts")


class ChartVisualizer:
    """图表可视化器"""
    
    def __init__(self, theme: str = 'dark', figsize: Tuple[int, int] = (12, 8)):
        """
        初始化图表可视化器
        
        Args:
            theme: 主题风格 ('dark' 或 'light')
            figsize: 图表大小 (width, height)
        """
        self.theme = theme
        self.figsize = figsize
        
        # 设置主题
        self._set_theme()
        
        # 中文字体设置
        rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        rcParams['axes.unicode_minus'] = False
        
        logger.info(f"ChartVisualizer initialized with theme={theme}, figsize={figsize}")
    
    def _set_theme(self):
        """设置图表主题"""
        if self.theme == 'dark':
            plt.style.use('dark_background')
            rcParams['figure.facecolor'] = '#1e1e1e'
            rcParams['axes.facecolor'] = '#2e2e2e'
            rcParams['axes.edgecolor'] = '#444444'
            rcParams['text.color'] = '#e0e0e0'
            rcParams['axes.labelcolor'] = '#e0e0e0'
            rcParams['xtick.color'] = '#e0e0e0'
            rcParams['ytick.color'] = '#e0e0e0'
        else:
            plt.style.use('seaborn-v0_8-whitegrid')
            rcParams['figure.facecolor'] = 'white'
    
    def plot_cost_trend(self, results: List[CapitalAnalysisResult], 
                       symbol: str, save_path: Optional[str] = None):
        """
        绘制主力成本趋势图
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not results:
            logger.warning("No results to plot")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        
        # 提取数据
        dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
        costs = [r.weighted_cost for r in sorted_results]
        ma5 = [r.cost_ma_5 for r in sorted_results if r.cost_ma_5 > 0]
        ma10 = [r.cost_ma_10 for r in sorted_results if r.cost_ma_10 > 0]
        ma20 = [r.cost_ma_20 for r in sorted_results if r.cost_ma_20 > 0]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制成本线
        ax.plot(dates, costs, label='主力成本', linewidth=2, color='#00d4ff')
        
        # 绘制均线
        ma5_dates = [d for d, c in zip(dates, costs) if c > 0][:len(ma5)]
        if len(ma5_dates) == len(ma5):
            ax.plot(ma5_dates, ma5, label='5日均线', linewidth=1.5, color='#ff6b6b', alpha=0.7)
        
        ma10_dates = [d for d, c in zip(dates, costs) if c > 0][:len(ma10)]
        if len(ma10_dates) == len(ma10):
            ax.plot(ma10_dates, ma10, label='10日均线', linewidth=1.5, color='#4ecdc4', alpha=0.7)
        
        ma20_dates = [d for d, c in zip(dates, costs) if c > 0][:len(ma20)]
        if len(ma20_dates) == len(ma20):
            ax.plot(ma20_dates, ma20, label='20日均线', linewidth=1.5, color='#ffe66d', alpha=0.7)
        
        # 标记最新成本
        if costs:
            ax.scatter([dates[-1]], [costs[-1]], color='#ff0000', s=100, zorder=5, label='最新成本')
        
        # 设置图表
        ax.set_title(f'{symbol} 主力成本趋势', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_net_flow(self, results: List[CapitalAnalysisResult], 
                     symbol: str, save_path: Optional[str] = None):
        """
        绘制净流向柱状图
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not results:
            logger.warning("No results to plot")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        
        # 提取数据
        dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
        net_flows = [r.net_flow for r in sorted_results]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制柱状图
        colors = ['#ff6b6b' if flow < 0 else '#4ecdc4' for flow in net_flows]
        bars = ax.bar(dates, net_flows, color=colors, alpha=0.7, width=0.8)
        
        # 添加数值标签
        for bar, flow in zip(bars, net_flows):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{flow:.1%}',
                   ha='center', va='bottom' if height > 0 else 'top',
                   fontsize=8)
        
        # 添加零线
        ax.axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        
        # 设置图表
        ax.set_title(f'{symbol} 主力净流向', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('净流向 (%)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_chip_distribution(self, chip_distribution: Dict[float, int], 
                              main_cost: float, symbol: str, 
                              save_path: Optional[str] = None):
        """
        绘制筹码分布图
        
        Args:
            chip_distribution: 筹码分布 {价格: 持仓量}
            main_cost: 主力成本
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not chip_distribution:
            logger.warning("No chip distribution to plot")
            return
        
        # 准备数据
        prices = sorted(chip_distribution.keys())
        volumes = [chip_distribution[p] for p in prices]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制筹码分布
        bars = ax.bar(prices, volumes, color='#4ecdc4', alpha=0.6, width=prices[1]-prices[0] if len(prices) > 1 else 0.1)
        
        # 标记主力成本
        if main_cost > 0:
            ax.axvline(x=main_cost, color='#ff6b6b', linestyle='--', linewidth=2, label=f'主力成本: {main_cost:.2f}')
        
        # 标记筹码峰位
        if volumes:
            peak_idx = volumes.index(max(volumes))
            peak_price = prices[peak_idx]
            ax.axvline(x=peak_price, color='#ffe66d', linestyle='--', linewidth=2, label=f'筹码峰位: {peak_price:.2f}')
        
        # 设置图表
        ax.set_title(f'{symbol} 筹码分布', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('价格', fontsize=12)
        ax.set_ylabel('持仓量（手）', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_order_composition(self, results: List[CapitalAnalysisResult], 
                              symbol: str, save_path: Optional[str] = None):
        """
        绘制订单构成图（堆叠柱状图）
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not results:
            logger.warning("No results to plot")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        
        # 提取数据
        dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
        agg_buy = [r.aggressive_buy_amount / 10000 for r in sorted_results]  # 转换为万元
        agg_sell = [-r.aggressive_sell_amount / 10000 for r in sorted_results]
        def_buy = [r.defensive_buy_amount / 10000 for r in sorted_results]
        def_sell = [-r.defensive_sell_amount / 10000 for r in sorted_results]
        algo_buy = [r.algo_buy_amount / 10000 for r in sorted_results]
        algo_sell = [-r.algo_sell_amount / 10000 for r in sorted_results]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制堆叠柱状图
        ax.bar(dates, agg_buy, label='攻击性买入', color='#ff6b6b', alpha=0.8)
        ax.bar(dates, agg_sell, label='攻击性卖出', color='#ff9999', alpha=0.8)
        ax.bar(dates, def_buy, bottom=agg_buy, label='防御性买入', color='#4ecdc4', alpha=0.8)
        ax.bar(dates, def_sell, bottom=agg_sell, label='防御性卖出', color='#99e6e6', alpha=0.8)
        ax.bar(dates, algo_buy, bottom=[a+d for a, d in zip(agg_buy, def_buy)], 
              label='算法买入', color='#ffe66d', alpha=0.8)
        ax.bar(dates, algo_sell, bottom=[a+d for a, d in zip(agg_sell, def_sell)], 
              label='算法卖出', color='#fff399', alpha=0.8)
        
        # 添加零线
        ax.axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        
        # 设置图表
        ax.set_title(f'{symbol} 订单构成（万元）', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('金额（万元）', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_concentration(self, results: List[CapitalAnalysisResult], 
                          symbol: str, save_path: Optional[str] = None):
        """
        绘制筹码集中度趋势图
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not results:
            logger.warning("No results to plot")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        
        # 提取数据
        dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
        concentrations = [r.concentration_ratio * 100 for r in sorted_results]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制折线图
        ax.plot(dates, concentrations, marker='o', linewidth=2, color='#00d4ff', label='筹码集中度')
        
        # 添加面积填充
        ax.fill_between(dates, concentrations, alpha=0.3, color='#00d4ff')
        
        # 设置图表
        ax.set_title(f'{symbol} 筹码集中度趋势', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('集中度 (%)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_comprehensive_dashboard(self, results: List[CapitalAnalysisResult], 
                                    symbol: str, save_path: Optional[str] = None):
        """
        绘制综合仪表板（多子图）
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            save_path: 保存路径（可选）
        """
        if not results or len(results) < 2:
            logger.warning("Insufficient results for comprehensive dashboard")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        
        # 创建子图
        fig, axes = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle(f'{symbol} 综合分析仪表板', fontsize=20, fontweight='bold')
        
        # 1. 成本趋势图
        dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
        costs = [r.weighted_cost for r in sorted_results]
        ma5 = [r.cost_ma_5 for r in sorted_results if r.cost_ma_5 > 0]
        ma10 = [r.cost_ma_10 for r in sorted_results if r.cost_ma_10 > 0]
        
        axes[0, 0].plot(dates, costs, label='主力成本', linewidth=2, color='#00d4ff')
        if len(ma5) > 0:
            axes[0, 0].plot(dates[:len(ma5)], ma5, label='5日均线', linewidth=1.5, color='#ff6b6b', alpha=0.7)
        if len(ma10) > 0:
            axes[0, 0].plot(dates[:len(ma10)], ma10, label='10日均线', linewidth=1.5, color='#4ecdc4', alpha=0.7)
        axes[0, 0].set_title('主力成本趋势', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('日期')
        axes[0, 0].set_ylabel('价格')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(axes[0, 0].xaxis.get_majorticklabels(), rotation=45)
        
        # 2. 净流向图
        net_flows = [r.net_flow * 100 for r in sorted_results]
        colors = ['#ff6b6b' if flow < 0 else '#4ecdc4' for flow in net_flows]
        axes[0, 1].bar(dates, net_flows, color=colors, alpha=0.7)
        axes[0, 1].axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        axes[0, 1].set_title('主力净流向', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('日期')
        axes[0, 1].set_ylabel('净流向 (%)')
        axes[0, 1].grid(True, alpha=0.3, axis='y')
        axes[0, 1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(axes[0, 1].xaxis.get_majorticklabels(), rotation=45)
        
        # 3. 筹码集中度
        concentrations = [r.concentration_ratio * 100 for r in sorted_results]
        axes[1, 0].plot(dates, concentrations, marker='o', linewidth=2, color='#ffe66d')
        axes[1, 0].fill_between(dates, concentrations, alpha=0.3, color='#ffe66d')
        axes[1, 0].set_title('筹码集中度', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('日期')
        axes[1, 0].set_ylabel('集中度 (%)')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].set_ylim(0, 100)
        axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
        
        # 4. 订单构成
        agg_buy = [r.aggressive_buy_amount / 10000 for r in sorted_results]
        agg_sell = [-r.aggressive_sell_amount / 10000 for r in sorted_results]
        def_buy = [r.defensive_buy_amount / 10000 for r in sorted_results]
        def_sell = [-r.defensive_sell_amount / 10000 for r in sorted_results]
        
        axes[1, 1].bar(dates, agg_buy, label='攻击性买入', color='#ff6b6b', alpha=0.8)
        axes[1, 1].bar(dates, agg_sell, label='攻击性卖出', color='#ff9999', alpha=0.8)
        axes[1, 1].bar(dates, def_buy, bottom=agg_buy, label='防御性买入', color='#4ecdc4', alpha=0.8)
        axes[1, 1].bar(dates, def_sell, bottom=agg_sell, label='防御性卖出', color='#99e6e6', alpha=0.8)
        axes[1, 1].axhline(y=0, color='white', linestyle='--', linewidth=1, alpha=0.5)
        axes[1, 1].set_title('订单构成（万元）', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('日期')
        axes[1, 1].set_ylabel('金额（万元）')
        axes[1, 1].legend(loc='best', fontsize=8)
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        axes[1, 1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(axes[1, 1].xaxis.get_majorticklabels(), rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Comprehensive dashboard saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_multiple_symbols_comparison(self, results_dict: Dict[str, List[CapitalAnalysisResult]], 
                                        metric: str = 'net_flow', 
                                        save_path: Optional[str] = None):
        """
        绘制多股票对比图
        
        Args:
            results_dict: 股票代码到结果列表的映射
            metric: 对比指标 ('net_flow', 'concentration_ratio', 'weighted_cost')
            save_path: 保存路径（可选）
        """
        if not results_dict:
            logger.warning("No results to plot")
            return
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 为每只股票绘制曲线
        colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#00d4ff', '#ff9ff3']
        
        for idx, (symbol, results) in enumerate(results_dict.items()):
            if not results:
                continue
            
            # 按日期排序
            sorted_results = sorted(results, key=lambda x: x.date)
            
            # 提取数据
            dates = [datetime.strptime(r.date, '%Y%m%d') for r in sorted_results]
            
            if metric == 'net_flow':
                values = [r.net_flow * 100 for r in sorted_results]
                ylabel = '净流向 (%)'
            elif metric == 'concentration_ratio':
                values = [r.concentration_ratio * 100 for r in sorted_results]
                ylabel = '集中度 (%)'
            else:  # weighted_cost
                values = [r.weighted_cost for r in sorted_results]
                ylabel = '价格'
            
            color = colors[idx % len(colors)]
            ax.plot(dates, values, marker='o', linewidth=2, label=symbol, color=color)
        
        # 设置图表
        metric_names = {
            'net_flow': '主力净流向对比',
            'concentration_ratio': '筹码集中度对比',
            'weighted_cost': '主力成本对比'
        }
        
        ax.set_title(metric_names.get(metric, '多股票对比'), fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Comparison chart saved to {save_path}")
        else:
            plt.show()
        
        plt.close()

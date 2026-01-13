"""仪表板模块"""
from typing import List, Dict, Optional
from datetime import datetime
from .charts import ChartVisualizer
from ..models.result import CapitalAnalysisResult
from ..utils.logger import get_logger

logger = get_logger("dashboard")


class Dashboard:
    """分析仪表板"""
    
    def __init__(self, theme: str = 'dark'):
        """
        初始化仪表板
        
        Args:
            theme: 主题风格
        """
        self.visualizer = ChartVisualizer(theme=theme)
        logger.info(f"Dashboard initialized with theme={theme}")
    
    def generate_daily_report(self, results: List[CapitalAnalysisResult], 
                             symbol: str, output_dir: str = "output") -> str:
        """
        生成每日分析报告
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            output_dir: 输出目录
        
        Returns:
            报告文件路径
        """
        if not results:
            logger.warning("No results to generate report")
            return ""
        
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成各种图表
        chart_paths = []
        
        # 1. 综合仪表板
        dashboard_path = output_path / f"{symbol}_dashboard.png"
        self.visualizer.plot_comprehensive_dashboard(
            results, symbol, str(dashboard_path)
        )
        chart_paths.append(dashboard_path)
        
        # 2. 成本趋势图
        cost_trend_path = output_path / f"{symbol}_cost_trend.png"
        self.visualizer.plot_cost_trend(
            results, symbol, str(cost_trend_path)
        )
        chart_paths.append(cost_trend_path)
        
        # 3. 净流向图
        net_flow_path = output_path / f"{symbol}_net_flow.png"
        self.visualizer.plot_net_flow(
            results, symbol, str(net_flow_path)
        )
        chart_paths.append(net_flow_path)
        
        # 4. 筹码集中度图
        concentration_path = output_path / f"{symbol}_concentration.png"
        self.visualizer.plot_concentration(
            results, symbol, str(concentration_path)
        )
        chart_paths.append(concentration_path)
        
        # 5. 订单构成图
        order_composition_path = output_path / f"{symbol}_order_composition.png"
        self.visualizer.plot_order_composition(
            results, symbol, str(order_composition_path)
        )
        chart_paths.append(order_composition_path)
        
        logger.info(f"Daily report generated for {symbol}: {len(chart_paths)} charts")
        
        return str(output_path)
    
    def generate_comparison_report(self, results_dict: Dict[str, List[CapitalAnalysisResult]], 
                                  metric: str = 'net_flow',
                                  output_dir: str = "output") -> str:
        """
        生成多股票对比报告
        
        Args:
            results_dict: 股票代码到结果列表的映射
            metric: 对比指标
            output_dir: 输出目录
        
        Returns:
            报告文件路径
        """
        if not results_dict:
            logger.warning("No results to generate comparison report")
            return ""
        
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成对比图
        comparison_path = output_path / f"comparison_{metric}.png"
        self.visualizer.plot_multiple_symbols_comparison(
            results_dict, metric, str(comparison_path)
        )
        
        logger.info(f"Comparison report generated: {comparison_path}")
        
        return str(comparison_path)
    
    def print_summary(self, results: List[CapitalAnalysisResult], symbol: str):
        """
        打印分析摘要
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
        """
        if not results:
            print(f"\n{symbol}: 无分析结果")
            return
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        latest = sorted_results[-1]
        
        print(f"\n{'='*70}")
        print(f"{symbol} 分析摘要")
        print(f"{'='*70}")
        print(f"分析日期: {sorted_results[0].date} 至 {latest.date}")
        print(f"分析天数: {len(results)} 天")
        print(f"\n最新数据 ({latest.date}):")
        print(f"  主力加权成本: {latest.weighted_cost:.2f}")
        print(f"  5日成本均线: {latest.cost_ma_5:.2f}")
        print(f"  10日成本均线: {latest.cost_ma_10:.2f}")
        print(f"  20日成本均线: {latest.cost_ma_20:.2f}")
        print(f"  净流向: {latest.net_flow:.2%}")
        print(f"  筹码集中度: {latest.concentration_ratio:.2%}")
        print(f"  筹码峰位: {latest.chip_peak_price:.2f}")
        print(f"  支撑位: {latest.support_price:.2f}")
        print(f"  压力位: {latest.resistance_price:.2f}")
        print(f"  验证状态: {latest.validation_status}")
        print(f"\n订单统计:")
        print(f"  总订单数: {latest.total_orders}")
        print(f"  大单数量: {latest.big_order_count}")
        print(f"  合成单数量: {latest.synthetic_order_count}")
        print(f"  算法单数量: {latest.algo_order_count}")
        
        # 计算平均指标
        avg_net_flow = sum(r.net_flow for r in results) / len(results)
        avg_concentration = sum(r.concentration_ratio for r in results) / len(results)
        
        print(f"\n期间平均:")
        print(f"  平均净流向: {avg_net_flow:.2%}")
        print(f"  平均集中度: {avg_concentration:.2%}")
        print(f"{'='*70}\n")
    
    def export_to_csv(self, results: List[CapitalAnalysisResult], 
                     symbol: str, output_dir: str = "output") -> str:
        """
        导出分析结果到CSV
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            output_dir: 输出目录
        
        Returns:
            CSV文件路径
        """
        if not results:
            logger.warning("No results to export")
            return ""
        
        import pandas as pd
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 转换为DataFrame
        data = []
        for r in results:
            data.append({
                '股票代码': r.symbol,
                '日期': r.date,
                '主力加权成本': r.weighted_cost,
                '5日均线': r.cost_ma_5,
                '10日均线': r.cost_ma_10,
                '20日均线': r.cost_ma_20,
                '净流向': r.net_flow,
                '攻击性买入': r.aggressive_buy_amount,
                '攻击性卖出': r.aggressive_sell_amount,
                '防御性买入': r.defensive_buy_amount,
                '防御性卖出': r.defensive_sell_amount,
                '算法买入': r.algo_buy_amount,
                '算法卖出': r.algo_sell_amount,
                '筹码集中度': r.concentration_ratio,
                '筹码峰位': r.chip_peak_price,
                '支撑位': r.support_price,
                '压力位': r.resistance_price,
                '验证状态': r.validation_status,
                '总订单数': r.total_orders,
                '大单数': r.big_order_count,
                '合成单数': r.synthetic_order_count,
                '算法单数': r.algo_order_count
            })
        
        df = pd.DataFrame(data)
        csv_path = output_path / f"{symbol}_analysis.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"Results exported to {csv_path}")
        
        return str(csv_path)
    
    def generate_html_report(self, results: List[CapitalAnalysisResult], 
                            symbol: str, output_dir: str = "output") -> str:
        """
        生成HTML格式报告
        
        Args:
            results: 分析结果列表
            symbol: 股票代码
            output_dir: 输出目录
        
        Returns:
            HTML文件路径
        """
        if not results:
            logger.warning("No results to generate HTML report")
            return ""
        
        from pathlib import Path
        import base64
        from io import BytesIO
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 先生成图表
        chart_dir = output_path / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成综合仪表板
        dashboard_img = chart_dir / f"{symbol}_dashboard.png"
        self.visualizer.plot_comprehensive_dashboard(
            results, symbol, str(dashboard_img)
        )
        
        # 转换图片为base64
        with open(dashboard_img, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # 按日期排序
        sorted_results = sorted(results, key=lambda x: x.date)
        latest = sorted_results[-1]
        
        # 生成HTML内容
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} 分析报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #00d4ff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #666;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            color: #666;
            font-size: 12px;
        }}
        .metric-value {{
            color: #333;
            font-size: 18px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #00d4ff;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .positive {{
            color: #4ecdc4;
            font-weight: bold;
        }}
        .negative {{
            color: #ff6b6b;
            font-weight: bold;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{symbol} 主力资金分析报告</h1>
        
        <div class="summary">
            <h2>最新数据摘要</h2>
            <p><strong>分析日期:</strong> {sorted_results[0].date} 至 {latest.date}</p>
            <p><strong>数据天数:</strong> {len(results)} 天</p>
        </div>
        
        <div class="summary">
            <h2>关键指标</h2>
            <div class="metric">
                <div class="metric-label">主力加权成本</div>
                <div class="metric-value">{latest.weighted_cost:.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">净流向</div>
                <div class="metric-value {'positive' if latest.net_flow > 0 else 'negative'}">
                    {latest.net_flow:.2%}
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">筹码集中度</div>
                <div class="metric-value">{latest.concentration_ratio:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">验证状态</div>
                <div class="metric-value">{latest.validation_status}</div>
            </div>
        </div>
        
        <h2>综合分析图表</h2>
        <img src="data:image/png;base64,{img_data}" alt="综合分析图表">
        
        <h2>详细数据</h2>
        <table>
            <thead>
                <tr>
                    <th>日期</th>
                    <th>主力成本</th>
                    <th>5日均线</th>
                    <th>10日均线</th>
                    <th>净流向</th>
                    <th>筹码集中度</th>
                    <th>验证状态</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for r in sorted_results:
            net_flow_class = 'positive' if r.net_flow > 0 else 'negative'
            html_content += f"""
                <tr>
                    <td>{r.date}</td>
                    <td>{r.weighted_cost:.2f}</td>
                    <td>{r.cost_ma_5:.2f if r.cost_ma_5 > 0 else '-'}</td>
                    <td>{r.cost_ma_10:.2f if r.cost_ma_10 > 0 else '-'}</td>
                    <td class="{net_flow_class}">{r.net_flow:.2%}</td>
                    <td>{r.concentration_ratio:.2%}</td>
                    <td>{r.validation_status}</td>
                </tr>
            """
        
        html_content += """
            </tbody>
        </table>
        
        <div class="summary">
            <p><strong>生成时间:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            <p><strong>系统:</strong> 基于Level-2数据的A股大资金成本与意图分析系统</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 保存HTML文件
        html_path = output_path / f"{symbol}_report.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {html_path}")
        
        return str(html_path)

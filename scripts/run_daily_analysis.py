"""每日分析脚本"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from datetime import datetime, timedelta
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.data.storage import StorageManager
from src.strategies.capital_tracking import CapitalTrackingStrategy
from src.utils.logger import get_logger

logger = get_logger("daily_analysis")


def load_config(config_path: str = "config/config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def load_symbols(symbols_path: str = "config/symbols.yaml") -> list:
    """加载股票列表"""
    with open(symbols_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['symbols']


def analyze_symbol(symbol: str, date: str, config: dict, fetcher, preprocessor, storage, strategy):
    """
    分析单个股票
    
    Args:
        symbol: 股票代码
        date: 日期
        config: 配置字典
        fetcher: 数据获取器
        preprocessor: 数据预处理器
        storage: 存储管理器
        strategy: 策略对象
    
    Returns:
        分析结果
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"开始分析: {symbol} - {date}")
    logger.info(f"{'='*60}")
    
    try:
        # 1. 检查是否已有数据
        existing_data = storage.load_tick_data(symbol, date)
        if existing_data:
            logger.info(f"从数据库加载已有数据: {len(existing_data)} 条记录")
            tick_data = existing_data
        else:
            # 2. 获取数据
            logger.info(f"从数据源获取数据...")
            tick_data = fetcher.fetch_tick_data(symbol, date)
            
            if not tick_data:
                logger.warning(f"未获取到数据: {symbol} {date}")
                return None
            
            logger.info(f"获取到 {len(tick_data)} 条tick数据")
        
        # 3. 数据预处理
        logger.info(f"数据预处理...")
        tick_data = preprocessor.clean_tick_data(tick_data)
        tick_data = preprocessor.remove_duplicates(tick_data)
        tick_data = preprocessor.sort_by_time(tick_data)
        
        logger.info(f"预处理后剩余 {len(tick_data)} 条有效数据")
        
        # 4. 统计信息
        stats = preprocessor.calculate_statistics(tick_data)
        logger.info(f"数据统计:")
        logger.info(f"  总成交量: {stats['total_volume']} 手")
        logger.info(f"  总成交额: {stats['total_amount']:,.2f} 元")
        logger.info(f"  平均价格: {stats['avg_price']:.2f}")
        logger.info(f"  价格区间: {stats['min_price']:.2f} - {stats['max_price']:.2f}")
        logger.info(f"  买单数量: {stats['buy_count']}")
        logger.info(f"  卖单数量: {stats['sell_count']}")
        logger.info(f"  大单数量: {stats['big_order_count']}")
        
        # 5. 保存数据（如果是从新获取的）
        if not existing_data:
            storage.save_tick_data(tick_data, date)
        
        # 6. 执行分析
        logger.info(f"执行资金分析...")
        result = strategy.analyze_day(symbol, date, tick_data)
        
        # 7. 输出结果
        logger.info(f"\n分析结果:")
        logger.info(f"  主力加权成本: {result.weighted_cost:.2f}")
        logger.info(f"  5日成本均线: {result.cost_ma_5:.2f}")
        logger.info(f"  10日成本均线: {result.cost_ma_10:.2f}")
        logger.info(f"  20日成本均线: {result.cost_ma_20:.2f}")
        logger.info(f"  净流向: {result.net_flow:.2%}")
        logger.info(f"  攻击性买入: {result.aggressive_buy_amount:,.2f} 元")
        logger.info(f"  攻击性卖出: {result.aggressive_sell_amount:,.2f} 元")
        logger.info(f"  防御性买入: {result.defensive_buy_amount:,.2f} 元")
        logger.info(f"  防御性卖出: {result.defensive_sell_amount:,.2f} 元")
        logger.info(f"  算法买入: {result.algo_buy_amount:,.2f} 元")
        logger.info(f"  算法卖出: {result.algo_sell_amount:,.2f} 元")
        logger.info(f"  筹码集中度: {result.concentration_ratio:.2%}")
        logger.info(f"  筹码峰位: {result.chip_peak_price:.2f}")
        logger.info(f"  支撑位: {result.support_price:.2f}")
        logger.info(f"  压力位: {result.resistance_price:.2f}")
        logger.info(f"  验证状态: {result.validation_status}")
        logger.info(f"  订单统计: 总计 {result.total_orders} "
                   f"(大单 {result.big_order_count}, "
                   f"合成单 {result.synthetic_order_count}, "
                   f"算法单 {result.algo_order_count})")
        
        # 8. 生成交易信号
        signal = strategy.get_signal(result)
        logger.info(f"  交易信号: {signal}")
        
        # 9. 保存分析结果
        storage.save_analysis_result(result)
        
        # 10. 保存每日成本（用于计算均线）
        storage.save_daily_cost(
            symbol, date, result.weighted_cost,
            result.cost_ma_5, result.cost_ma_10, result.cost_ma_20
        )
        
        logger.info(f"\n{symbol} 分析完成！")
        
        return result
    
    except Exception as e:
        logger.error(f"分析失败: {symbol} {date}")
        logger.error(f"错误信息: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("基于Level-2数据的A股大资金成本与意图分析系统")
    logger.info("每日分析脚本")
    logger.info("="*60)
    
    # 加载配置
    logger.info("\n加载配置文件...")
    config = load_config()
    symbols = load_symbols()
    
    logger.info(f"配置加载成功，共 {len(symbols)} 只股票待分析")
    
    # 初始化组件
    logger.info("\n初始化系统组件...")
    fetcher = DataFetcher(config['data']['source'])
    preprocessor = DataPreprocessor()
    storage = StorageManager(config['storage']['path'])
    
    # 构建策略配置
    strategy_config = {
        'window_sec': config['algorithm']['window_sec'],
        'synthetic_threshold': config['algorithm']['synthetic_threshold'],
        'big_order_threshold': config['classifier']['big_order_threshold'],
        'wall_threshold': config['classifier']['wall_threshold'],
        'ma_periods': config['moving_averages']['periods']
    }
    
    strategy = CapitalTrackingStrategy(strategy_config)
    
    # 确定分析日期
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    logger.info(f"\n分析日期: {date}")
    
    # 分析所有股票
    results = []
    for symbol_info in symbols:
        symbol = symbol_info['code']
        result = analyze_symbol(symbol, date, config, fetcher, preprocessor, storage, strategy)
        if result:
            results.append(result)
    
    # 输出汇总信息
    logger.info("\n" + "="*60)
    logger.info("分析汇总")
    logger.info("="*60)
    logger.info(f"成功分析: {len(results)} 只股票")
    logger.info(f"分析日期: {date}")
    
    if results:
        # 统计信号
        buy_signals = sum(1 for r in results if strategy.get_signal(r) == 'BUY')
        sell_signals = sum(1 for r in results if strategy.get_signal(r) == 'SELL')
        hold_signals = sum(1 for r in results if strategy.get_signal(r) == 'HOLD')
        
        logger.info(f"\n信号统计:")
        logger.info(f"  买入信号: {buy_signals}")
        logger.info(f"  卖出信号: {sell_signals}")
        logger.info(f"  持有信号: {hold_signals}")
        
        # 找出净流入最大的股票
        positive_flows = [r for r in results if r.net_flow > 0]
        if positive_flows:
            top_inflow = sorted(positive_flows, key=lambda x: x.net_flow, reverse=True)[0]
            logger.info(f"\n净流入最大: {top_inflow.symbol} ({top_inflow.net_flow:.2%})")
        
        # 找出净流出最大的股票
        negative_flows = [r for r in results if r.net_flow < 0]
        if negative_flows:
            top_outflow = sorted(negative_flows, key=lambda x: x.net_flow)[0]
            logger.info(f"净流出最大: {top_outflow.symbol} ({top_outflow.net_flow:.2%})")
        
        # 找出筹码集中度最高的股票
        top_concentration = sorted(results, key=lambda x: x.concentration_ratio, reverse=True)[0]
        logger.info(f"筹码最集中: {top_concentration.symbol} ({top_concentration.concentration_ratio:.2%})")
    
    # 数据库统计
    stats = storage.get_statistics()
    logger.info(f"\n数据库统计:")
    logger.info(f"  总tick记录: {stats.get('total_ticks', 0)}")
    logger.info(f"  总分析记录: {stats.get('total_results', 0)}")
    logger.info(f"  股票数量: {stats.get('total_symbols', 0)}")
    logger.info(f"  日期范围: {stats.get('date_range', 'N/A')}")
    logger.info(f"  数据库大小: {stats.get('db_size_mb', 0):.2f} MB")
    
    logger.info("\n" + "="*60)
    logger.info("每日分析完成！")
    logger.info("="*60)


if __name__ == "__main__":
    main()

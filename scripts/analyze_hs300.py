"""分析沪深300成分股数据"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from datetime import datetime
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.data.storage import StorageManager
from src.strategies.capital_tracking import CapitalTrackingStrategy
from src.utils.logger import get_logger

logger = get_logger("analyze_hs300")


def load_config(config_path: str = "config/config.yaml") -> dict:
    """加载配置文件"""
    full_path = project_root / config_path
    with open(full_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def load_symbols(symbols_path: str = "config/symbols_hs300.yaml") -> list:
    """加载股票列表"""
    full_path = project_root / symbols_path
    with open(full_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['symbols']


def analyze_symbol(symbol: str, name: str, date: str, config: dict,
                   fetcher, preprocessor, storage, strategy):
    """
    分析单个股票的数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        date: 日期
        config: 配置字典
        fetcher: 数据获取器
        storage: 存储管理器
        analyzer: 芯片分析器
        calculator: 成本计算器
        classifier: 订单分类器
    
    Returns:
        是否成功
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"分析数据: {name} ({symbol}) - {date}")
    logger.info(f"{'='*60}")
    
    try:
        # 1. 从数据库获取tick数据
        tick_data = storage.load_tick_data(symbol, date)
        
        if not tick_data:
            logger.warning(f"未找到数据: {symbol} {date}")
            return False
        
        logger.info(f"加载到 {len(tick_data)} 条tick数据")
        
        # 2. 数据统计
        stats = preprocessor.calculate_statistics(tick_data)
        
        if not stats or stats.get('count', 0) == 0:
            logger.warning(f"数据统计为空，跳过分析")
            return False
        
        logger.info(f"数据统计:")
        logger.info(f"  总成交量: {stats.get('total_volume', 0)} 手")
        logger.info(f"  总成交额: {stats.get('total_amount', 0):,.2f} 元")
        logger.info(f"  平均价格: {stats.get('avg_price', 0):.2f}")
        
        # 3. 执行分析
        logger.info(f"执行资金分析...")
        result = strategy.analyze_day(symbol, date, tick_data)
        
        # 4. 输出结果
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
        logger.info(f"  验证状态: {result.validation_status}")
        
        # 5. 保存分析结果
        storage.save_analysis_result(result)
        
        # 6. 保存每日成本
        storage.save_daily_cost(
            symbol, date, result.weighted_cost,
            result.cost_ma_5, result.cost_ma_10, result.cost_ma_20
        )
        
        logger.info(f"\n✓ 分析完成: {symbol}")
        
        return True
    
    except Exception as e:
        logger.error(f"分析失败: {symbol} {date}")
        logger.error(f"错误信息: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("沪深300成分股数据分析脚本")
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
    
    # 注意：不删除旧数据，直接覆盖分析结果
    # 这样可以保留tick数据，只更新分析结果
    logger.info(f"开始分析（会覆盖已有的分析结果）")
    
    # 分析所有股票数据
    logger.info("\n开始分析股票数据...")
    success_count = 0
    fail_count = 0
    failed_symbols = []
    
    for idx, symbol_info in enumerate(symbols, 1):
        symbol = symbol_info['code']
        name = symbol_info['name']
        
        logger.info(f"\n进度: {idx}/{len(symbols)}")
        
        success = analyze_symbol(symbol, name, date, config,
                                 fetcher, preprocessor, storage, strategy)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            failed_symbols.append(f"{name}({symbol})")
    
    # 输出汇总信息
    logger.info("\n" + "="*60)
    logger.info("分析汇总")
    logger.info("="*60)
    logger.info(f"成功: {success_count} 只股票")
    logger.info(f"失败: {fail_count} 只股票")
    logger.info(f"总计: {len(symbols)} 只股票")
    logger.info(f"分析日期: {date}")
    
    if failed_symbols:
        logger.info(f"\n失败列表:")
        for symbol in failed_symbols:
            logger.info(f"  - {symbol}")
    
    # 数据库统计
    stats = storage.get_statistics()
    logger.info(f"\n数据库统计:")
    logger.info(f"  总tick记录: {stats.get('total_ticks', 0)}")
    logger.info(f"  总分析记录: {stats.get('total_results', 0)}")
    logger.info(f"  股票数量: {stats.get('total_symbols', 0)}")
    logger.info(f"  日期范围: {stats.get('date_range', 'N/A')}")
    logger.info(f"  数据库大小: {stats.get('db_size_mb', 0):.2f} MB")
    
    logger.info("\n" + "="*60)
    logger.info("数据分析完成！")
    logger.info("="*60)


if __name__ == "__main__":
    main()

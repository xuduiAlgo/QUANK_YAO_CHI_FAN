"""分析所有指数成分股数据（沪深300 + 科创100）"""
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

logger = get_logger("analyze_all")


def load_config(config_path: str = "config/config.yaml") -> dict:
    """加载配置文件"""
    full_path = project_root / config_path
    with open(full_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def load_all_symbols() -> tuple:
    """
    加载所有股票列表
    
    Returns:
        (hs300_symbols, kc100_symbols)
    """
    # 加载沪深300
    hs300_path = project_root / "config/symbols_hs300.yaml"
    with open(hs300_path, 'r', encoding='utf-8') as f:
        hs300_data = yaml.safe_load(f)
    
    # 加载科创100
    kc100_path = project_root / "config/symbols_kc100.yaml"
    with open(kc100_path, 'r', encoding='utf-8') as f:
        kc100_data = yaml.safe_load(f)
    
    return hs300_data['symbols'], kc100_data['symbols']


def analyze_symbol(symbol: str, name: str, date: str, config: dict,
                   fetcher, preprocessor, storage, strategy, index_name, idx, total):
    """
    分析单个股票的数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        date: 日期
        config: 配置字典
        fetcher: 数据获取器
        preprocessor: 数据预处理器
        storage: 存储管理器
        strategy: 策略对象
        index_name: 指数名称
        idx: 当前进度
        total: 总数
    
    Returns:
        分析结果对象或None
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"[{index_name} {idx}/{total}] 分析数据: {name} ({symbol}) - {date}")
    logger.info(f"{'='*60}")
    
    try:
        # 1. 从数据库获取tick数据
        tick_data = storage.load_tick_data(symbol, date)
        
        if not tick_data:
            logger.warning(f"[{index_name} {idx}/{total}] 未找到数据: {symbol} {date}")
            return None
        
        logger.info(f"[{index_name} {idx}/{total}] 加载到 {len(tick_data)} 条tick数据")
        
        # 2. 数据统计
        stats = preprocessor.calculate_statistics(tick_data)
        
        if not stats or stats.get('count', 0) == 0:
            logger.warning(f"[{index_name} {idx}/{total}] 数据统计为空，跳过分析")
            return None
        
        logger.info(f"[{index_name} {idx}/{total}] 数据统计:")
        logger.info(f"  总成交量: {stats.get('total_volume', 0)} 手")
        logger.info(f"  总成交额: {stats.get('total_amount', 0):,.2f} 元")
        logger.info(f"  平均价格: {stats.get('avg_price', 0):.2f}")
        
        # 3. 执行分析
        logger.info(f"[{index_name} {idx}/{total}] 执行资金分析...")
        result = strategy.analyze_day(symbol, date, tick_data)
        
        # 4. 输出结果
        logger.info(f"[{index_name} {idx}/{total}] 分析结果:")
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
        
        logger.info(f"[{index_name} {idx}/{total}] ✓ 分析完成: {symbol}")
        
        return result
    
    except Exception as e:
        logger.error(f"[{index_name} {idx}/{total}] 分析失败: {symbol} {date}")
        logger.error(f"错误信息: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("全指数成分股数据分析脚本（沪深300 + 科创100）")
    logger.info("="*60)
    
    # 加载配置
    logger.info("\n加载配置文件...")
    config = load_config()
    hs300_symbols, kc100_symbols = load_all_symbols()
    
    logger.info(f"配置加载成功:")
    logger.info(f"  沪深300: {len(hs300_symbols)} 只股票")
    logger.info(f"  科创100: {len(kc100_symbols)} 只股票")
    logger.info(f"  总计: {len(hs300_symbols) + len(kc100_symbols)} 只股票")
    
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
    
    results = []
    success_count = 0
    fail_count = 0
    failed_symbols = []
    
    # 分析沪深300股票
    logger.info("\n" + "="*60)
    logger.info("开始分析沪深300成分股...")
    logger.info("="*60)
    
    for idx, symbol_info in enumerate(hs300_symbols, 1):
        symbol = symbol_info['code']
        name = symbol_info['name']
        
        result = analyze_symbol(symbol, name, date, config,
                                 fetcher, preprocessor, storage, strategy,
                                 "HS300", idx, len(hs300_symbols))
        
        if result:
            results.append(result)
            success_count += 1
        else:
            fail_count += 1
            failed_symbols.append(f"HS300 - {name}({symbol})")
    
    # 分析科创100股票
    logger.info("\n" + "="*60)
    logger.info("开始分析科创100成分股...")
    logger.info("="*60)
    
    for idx, symbol_info in enumerate(kc100_symbols, 1):
        symbol = symbol_info['code']
        name = symbol_info['name']
        
        result = analyze_symbol(symbol, name, date, config,
                                 fetcher, preprocessor, storage, strategy,
                                 "KC100", idx, len(kc100_symbols))
        
        if result:
            results.append(result)
            success_count += 1
        else:
            fail_count += 1
            failed_symbols.append(f"KC100 - {name}({symbol})")
    
    # 输出汇总信息
    logger.info("\n" + "="*60)
    logger.info("分析汇总")
    logger.info("="*60)
    logger.info(f"成功: {success_count} 只股票")
    logger.info(f"失败: {fail_count} 只股票")
    logger.info(f"总计: {len(hs300_symbols) + len(kc100_symbols)} 只股票")
    logger.info(f"分析日期: {date}")
    
    if failed_symbols:
        logger.info(f"\n失败列表 ({len(failed_symbols)} 只):")
        for symbol in failed_symbols[:20]:  # 只显示前20个
            logger.info(f"  - {symbol}")
        if len(failed_symbols) > 20:
            logger.info(f"  ... 还有 {len(failed_symbols) - 20} 只股票")
    
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
        
        # 分指数统计
        hs300_results = [r for r in results if r.symbol in [s['code'] for s in hs300_symbols]]
        kc100_results = [r for r in results if r.symbol in [s['code'] for s in kc100_symbols]]
        
        logger.info(f"\n沪深300统计:")
        logger.info(f"  成功分析: {len(hs300_results)} 只")
        
        if hs300_results:
            hs300_avg_flow = sum(r.net_flow for r in hs300_results) / len(hs300_results)
            logger.info(f"  平均净流向: {hs300_avg_flow:.2%}")
        
        logger.info(f"\n科创100统计:")
        logger.info(f"  成功分析: {len(kc100_results)} 只")
        
        if kc100_results:
            kc100_avg_flow = sum(r.net_flow for r in kc100_results) / len(kc100_results)
            logger.info(f"  平均净流向: {kc100_avg_flow:.2%}")
    
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

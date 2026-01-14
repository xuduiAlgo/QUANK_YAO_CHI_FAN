"""更新沪深300成分股最新数据（多线程版本）"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from datetime import datetime
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.data.storage import StorageManager
from src.utils.logger import get_logger

logger = get_logger("update_hs300")


# 全局计数器和锁
success_count = 0
fail_count = 0
failed_symbols = []
count_lock = threading.Lock()


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


def update_symbol_data(symbol: str, name: str, date: str, config: dict, 
                      fetcher, preprocessor, storage, idx, total):
    """
    更新单个股票的数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        date: 日期
        config: 配置字典
        fetcher: 数据获取器
        preprocessor: 数据预处理器
        storage: 存储管理器
        idx: 当前进度
        total: 总数
    
    Returns:
        是否成功
    """
    global success_count, fail_count, failed_symbols
    
    logger.info(f"[{idx}/{total}] 开始更新: {name} ({symbol})")
    
    try:
        # 1. 从数据源获取数据（不使用缓存，强制重新获取）
        tick_data = fetcher.fetch_tick_data(symbol, date, use_cache=False)
        
        if not tick_data:
            logger.warning(f"[{idx}/{total}] 未获取到数据: {symbol}")
            with count_lock:
                fail_count += 1
                failed_symbols.append(f"{name}({symbol})")
            return False
        
        logger.info(f"[{idx}/{total}] 获取到 {len(tick_data)} 条tick数据")
        
        # 2. 数据预处理
        tick_data = preprocessor.clean_tick_data(tick_data)
        tick_data = preprocessor.remove_duplicates(tick_data)
        tick_data = preprocessor.sort_by_time(tick_data)
        
        logger.info(f"[{idx}/{total}] 预处理后剩余 {len(tick_data)} 条有效数据")
        
        # 3. 保存数据
        success = storage.save_tick_data(tick_data, date)
        
        if success:
            logger.info(f"[{idx}/{total}] ✓ 数据保存成功: {symbol}")
            with count_lock:
                success_count += 1
            return True
        else:
            logger.error(f"[{idx}/{total}] ✗ 数据保存失败: {symbol}")
            with count_lock:
                fail_count += 1
                failed_symbols.append(f"{name}({symbol})")
            return False
    
    except Exception as e:
        logger.error(f"[{idx}/{total}] 更新失败: {symbol} - {e}")
        with count_lock:
            fail_count += 1
            failed_symbols.append(f"{name}({symbol})")
        return False


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("沪深300成分股数据更新脚本（多线程版本）")
    logger.info("="*60)
    
    # 加载配置
    logger.info("\n加载配置文件...")
    config = load_config()
    symbols = load_symbols()
    
    logger.info(f"配置加载成功，共 {len(symbols)} 只股票待更新")
    
    # 初始化组件
    logger.info("\n初始化系统组件...")
    fetcher = DataFetcher(config['data']['source'])
    preprocessor = DataPreprocessor()
    storage = StorageManager(config['storage']['path'])
    
    # 确定更新日期
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    logger.info(f"\n更新日期: {date}")
    
    # 不再删除当天所有数据，使用 INSERT OR REPLACE 自动覆盖旧数据
    # 这样可以保留其他指数（如科创100）当天的数据
    logger.info(f"开始更新数据，将自动覆盖当天的旧数据...")
    
    # 设置线程池大小（默认8个线程）
    max_workers = 8
    if len(sys.argv) > 2:
        try:
            max_workers = int(sys.argv[2])
        except ValueError:
            pass
    
    logger.info(f"\n使用 {max_workers} 个线程并行更新数据...")
    logger.info("开始更新股票数据...\n")
    
    # 重置全局计数器
    global success_count, fail_count, failed_symbols
    success_count = 0
    fail_count = 0
    failed_symbols = []
    
    # 使用线程池并行更新
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_symbol = {}
        for idx, symbol_info in enumerate(symbols, 1):
            symbol = symbol_info['code']
            name = symbol_info['name']
            
            # 为每个线程创建独立的fetcher和preprocessor实例
            thread_fetcher = DataFetcher(config['data']['source'])
            thread_preprocessor = DataPreprocessor()
            
            future = executor.submit(
                update_symbol_data, 
                symbol, name, date, config, 
                thread_fetcher, thread_preprocessor, storage,
                idx, len(symbols)
            )
            future_to_symbol[future] = f"{name}({symbol})"
        
        # 等待所有任务完成
        completed = 0
        for future in as_completed(future_to_symbol):
            completed += 1
            symbol_name = future_to_symbol[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"任务异常: {symbol_name} - {e}")
    
    # 输出汇总信息
    logger.info("\n" + "="*60)
    logger.info("更新汇总")
    logger.info("="*60)
    logger.info(f"成功: {success_count} 只股票")
    logger.info(f"失败: {fail_count} 只股票")
    logger.info(f"总计: {len(symbols)} 只股票")
    logger.info(f"更新日期: {date}")
    logger.info(f"使用线程数: {max_workers}")
    
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
    logger.info("数据更新完成！")
    logger.info("="*60)


if __name__ == "__main__":
    main()

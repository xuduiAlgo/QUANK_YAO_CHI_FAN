"""数据存储管理"""
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..models.tick import Tick
from ..models.result import CapitalAnalysisResult
from ..utils.logger import get_logger

logger = get_logger("storage")


class StorageManager:
    """存储管理器（线程安全）"""
    
    def __init__(self, db_path: str = "data/analysis.db"):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建线程锁，确保多线程安全
        self._lock = threading.Lock()
        
        # 初始化数据库
        self._init_db()
        
        logger.info(f"StorageManager initialized with db_path={db_path}")
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建tick数据表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tick_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        symbol TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume INTEGER NOT NULL,
                        amount REAL NOT NULL,
                        direction TEXT NOT NULL,
                        bid1_price REAL,
                        bid1_vol INTEGER,
                        ask1_price REAL,
                        ask1_vol INTEGER,
                        date TEXT NOT NULL
                    )
                """)
                
                # 创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_symbol_date 
                    ON tick_data(symbol, date)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON tick_data(timestamp)
                """)
                
                # 创建分析结果表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        date TEXT NOT NULL,
                        weighted_cost REAL,
                        cost_ma_5 REAL,
                        cost_ma_10 REAL,
                        cost_ma_20 REAL,
                        net_flow REAL,
                        aggressive_buy_amount REAL,
                        aggressive_sell_amount REAL,
                        defensive_buy_amount REAL,
                        defensive_sell_amount REAL,
                        algo_buy_amount REAL,
                        algo_sell_amount REAL,
                        concentration_ratio REAL,
                        chip_peak_price REAL,
                        validation_status TEXT,
                        total_orders INTEGER,
                        big_order_count INTEGER,
                        synthetic_order_count INTEGER,
                        algo_order_count INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, date)
                    )
                """)
                
                # 创建历史成本表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_costs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        date TEXT NOT NULL,
                        weighted_cost REAL NOT NULL,
                        cost_ma_5 REAL,
                        cost_ma_10 REAL,
                        cost_ma_20 REAL,
                        UNIQUE(symbol, date)
                    )
                """)
                
                # 创建配置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
    
    def save_tick_data(self, ticks: List[Tick], date: str) -> bool:
        """
        保存tick数据（线程安全）
        
        Args:
            ticks: Tick数据列表
            date: 日期字符串
        
        Returns:
            是否成功
        """
        if not ticks:
            logger.warning("No ticks to save")
            return False
        
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 准备数据
                    data = []
                    for tick in ticks:
                        data.append((
                            tick.timestamp.isoformat(),
                            tick.symbol,
                            tick.price,
                            tick.volume,
                            tick.amount,
                            tick.direction,
                            tick.bid1_price,
                            tick.bid1_vol,
                            tick.ask1_price,
                            tick.ask1_vol,
                            date
                        ))
                    
                    # 批量插入
                    cursor.executemany("""
                        INSERT OR REPLACE INTO tick_data 
                        (timestamp, symbol, price, volume, amount, direction, 
                         bid1_price, bid1_vol, ask1_price, ask1_vol, date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, data)
                    
                    conn.commit()
                    
                    logger.info(f"Saved {len(ticks)} tick records for {ticks[0].symbol} {date}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to save tick data: {e}")
            return False
    
    def load_tick_data(self, symbol: str, date: str) -> List[Tick]:
        """
        加载tick数据
        
        Args:
            symbol: 股票代码
            date: 日期字符串
        
        Returns:
            Tick数据列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, symbol, price, volume, amount, direction,
                           bid1_price, bid1_vol, ask1_price, ask1_vol
                    FROM tick_data
                    WHERE symbol = ? AND date = ?
                    ORDER BY timestamp
                """, (symbol, date))
                
                rows = cursor.fetchall()
                
                ticks = []
                for row in rows:
                    tick = Tick(
                        timestamp=datetime.fromisoformat(row[0]),
                        symbol=row[1],
                        price=row[2],
                        volume=row[3],
                        amount=row[4],
                        direction=row[5],
                        bid1_price=row[6],
                        bid1_vol=row[7],
                        ask1_price=row[8],
                        ask1_vol=row[9]
                    )
                    ticks.append(tick)
                
                logger.info(f"Loaded {len(ticks)} tick records for {symbol} {date}")
                return ticks
        
        except Exception as e:
            logger.error(f"Failed to load tick data: {e}")
            return []
    
    def save_analysis_result(self, result: CapitalAnalysisResult) -> bool:
        """
        保存分析结果（线程安全）
        
        Args:
            result: 分析结果对象
        
        Returns:
            是否成功
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO analysis_results 
                        (symbol, date, weighted_cost, cost_ma_5, cost_ma_10, cost_ma_20,
                         net_flow, aggressive_buy_amount, aggressive_sell_amount,
                         defensive_buy_amount, defensive_sell_amount,
                         algo_buy_amount, algo_sell_amount, concentration_ratio,
                         chip_peak_price, validation_status, total_orders,
                         big_order_count, synthetic_order_count, algo_order_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result.symbol, result.date, result.weighted_cost,
                        result.cost_ma_5, result.cost_ma_10, result.cost_ma_20,
                        result.net_flow, result.aggressive_buy_amount,
                        result.aggressive_sell_amount, result.defensive_buy_amount,
                        result.defensive_sell_amount, result.algo_buy_amount,
                        result.algo_sell_amount, result.concentration_ratio,
                        result.chip_peak_price, result.validation_status,
                        result.total_orders, result.big_order_count,
                        result.synthetic_order_count, result.algo_order_count
                    ))
                    
                    conn.commit()
                    
                    logger.info(f"Saved analysis result for {result.symbol} {result.date}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to save analysis result: {e}")
            return False
    
    def load_analysis_result(self, symbol: str, date: str) -> Optional[CapitalAnalysisResult]:
        """
        加载分析结果
        
        Args:
            symbol: 股票代码
            date: 日期字符串
        
        Returns:
            分析结果对象，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT symbol, date, weighted_cost, cost_ma_5, cost_ma_10, cost_ma_20,
                           net_flow, aggressive_buy_amount, aggressive_sell_amount,
                           defensive_buy_amount, defensive_sell_amount,
                           algo_buy_amount, algo_sell_amount, concentration_ratio,
                           chip_peak_price, validation_status, total_orders,
                           big_order_count, synthetic_order_count, algo_order_count
                    FROM analysis_results
                    WHERE symbol = ? AND date = ?
                """, (symbol, date))
                
                row = cursor.fetchone()
                
                if row:
                    result = CapitalAnalysisResult(
                        symbol=row[0], date=row[1], weighted_cost=row[2],
                        cost_ma_5=row[3], cost_ma_10=row[4], cost_ma_20=row[5],
                        net_flow=row[6], aggressive_buy_amount=row[7],
                        aggressive_sell_amount=row[8], defensive_buy_amount=row[9],
                        defensive_sell_amount=row[10], algo_buy_amount=row[11],
                        algo_sell_amount=row[12], concentration_ratio=row[13],
                        chip_peak_price=row[14], validation_status=row[15],
                        total_orders=row[16], big_order_count=row[17],
                        synthetic_order_count=row[18], algo_order_count=row[19]
                    )
                    logger.info(f"Loaded analysis result for {symbol} {date}")
                    return result
                
                return None
        
        except Exception as e:
            logger.error(f"Failed to load analysis result: {e}")
            return None
    
    def save_daily_cost(self, symbol: str, date: str, weighted_cost: float,
                       cost_ma_5: float = None, cost_ma_10: float = None,
                       cost_ma_20: float = None) -> bool:
        """
        保存每日成本数据（线程安全）
        
        Args:
            symbol: 股票代码
            date: 日期字符串
            weighted_cost: 加权成本
            cost_ma_5: 5日均线
            cost_ma_10: 10日均线
            cost_ma_20: 20日均线
        
        Returns:
            是否成功
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_costs 
                        (symbol, date, weighted_cost, cost_ma_5, cost_ma_10, cost_ma_20)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (symbol, date, weighted_cost, cost_ma_5, cost_ma_10, cost_ma_20))
                    
                    conn.commit()
                    
                    logger.debug(f"Saved daily cost for {symbol} {date}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to save daily cost: {e}")
            return False
    
    def load_daily_costs(self, symbol: str, days: int = 20) -> List[float]:
        """
        加载历史每日成本数据
        
        Args:
            symbol: 股票代码
            days: 加载天数
        
        Returns:
            成本列表 [cost_today, cost_yesterday, ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT weighted_cost
                    FROM daily_costs
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT ?
                """, (symbol, days))
                
                rows = cursor.fetchall()
                costs = [row[0] for row in rows if row[0] is not None]
                
                logger.debug(f"Loaded {len(costs)} daily costs for {symbol}")
                return costs
        
        except Exception as e:
            logger.error(f"Failed to load daily costs: {e}")
            return []
    
    def get_analysis_history(self, symbol: str, start_date: str = None,
                            end_date: str = None) -> List[Dict[str, Any]]:
        """
        获取分析历史
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            分析结果列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM analysis_results
                    WHERE symbol = ?
                """
                params = [symbol]
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY date DESC"
                
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    results.append(result)
                
                logger.info(f"Loaded {len(results)} analysis records for {symbol}")
                return results
        
        except Exception as e:
            logger.error(f"Failed to get analysis history: {e}")
            return []
    
    def delete_symbol_data(self, symbol: str) -> bool:
        """
        删除指定股票的所有数据（线程安全）
        
        Args:
            symbol: 股票代码
        
        Returns:
            是否成功
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 删除tick数据
                    cursor.execute("DELETE FROM tick_data WHERE symbol = ?", (symbol,))
                    tick_count = cursor.rowcount
                    
                    # 删除分析结果
                    cursor.execute("DELETE FROM analysis_results WHERE symbol = ?", (symbol,))
                    result_count = cursor.rowcount
                    
                    # 删除成本数据
                    cursor.execute("DELETE FROM daily_costs WHERE symbol = ?", (symbol,))
                    cost_count = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"Deleted {tick_count} ticks, {result_count} results, "
                              f"{cost_count} costs for {symbol}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to delete symbol data: {e}")
            return False
    
    def delete_date_data(self, date: str) -> bool:
        """
        删除指定日期的所有数据（线程安全）
        
        Args:
            date: 日期字符串 (格式: YYYYMMDD)
        
        Returns:
            是否成功
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 删除tick数据
                    cursor.execute("DELETE FROM tick_data WHERE date = ?", (date,))
                    tick_count = cursor.rowcount
                    
                    # 删除分析结果
                    cursor.execute("DELETE FROM analysis_results WHERE date = ?", (date,))
                    result_count = cursor.rowcount
                    
                    # 删除成本数据
                    cursor.execute("DELETE FROM daily_costs WHERE date = ?", (date,))
                    cost_count = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"Deleted {tick_count} ticks, {result_count} results, "
                              f"{cost_count} costs for date {date}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to delete date data: {e}")
            return False
    
    def delete_symbol_date_data(self, symbol: str, date: str) -> bool:
        """
        删除指定股票指定日期的数据（线程安全）
        
        Args:
            symbol: 股票代码
            date: 日期字符串 (格式: YYYYMMDD)
        
        Returns:
            是否成功
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 删除tick数据
                    cursor.execute("DELETE FROM tick_data WHERE symbol = ? AND date = ?", 
                                 (symbol, date))
                    tick_count = cursor.rowcount
                    
                    # 删除分析结果
                    cursor.execute("DELETE FROM analysis_results WHERE symbol = ? AND date = ?", 
                                 (symbol, date))
                    result_count = cursor.rowcount
                    
                    # 删除成本数据
                    cursor.execute("DELETE FROM daily_costs WHERE symbol = ? AND date = ?", 
                                 (symbol, date))
                    cost_count = cursor.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"Deleted {tick_count} ticks, {result_count} results, "
                              f"{cost_count} costs for {symbol} {date}")
                    return True
        
        except Exception as e:
            logger.error(f"Failed to delete symbol date data: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 统计tick数量
                cursor.execute("SELECT COUNT(*) FROM tick_data")
                stats['total_ticks'] = cursor.fetchone()[0]
                
                # 统计分析结果数量
                cursor.execute("SELECT COUNT(*) FROM analysis_results")
                stats['total_results'] = cursor.fetchone()[0]
                
                # 统计股票数量
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM tick_data")
                stats['total_symbols'] = cursor.fetchone()[0]
                
                # 统计日期范围
                cursor.execute("SELECT MIN(date), MAX(date) FROM tick_data")
                min_date, max_date = cursor.fetchone()
                stats['date_range'] = f"{min_date} to {max_date}" if min_date else "N/A"
                
                # 数据库大小
                stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
                logger.debug(f"Database statistics: {stats}")
                return stats
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

"""数据获取器"""
from typing import List, Optional
import pandas as pd
from datetime import datetime
from ..models.tick import Tick
from ..utils.logger import get_logger
from ..utils.cache import CacheManager

logger = get_logger("fetcher")


class DataFetcher:
    """Level-2数据获取器"""
    
    def __init__(self, data_source: str = 'akshare', cache_enabled: bool = True, 
                 cache_dir: str = "data/cache"):
        """
        初始化数据获取器
        
        Args:
            data_source: 数据源类型（akshare, wind, tushare）
            cache_enabled: 是否启用缓存
            cache_dir: 缓存目录
        """
        self.data_source = data_source
        self.cache_enabled = cache_enabled
        self.cache_manager = CacheManager(cache_dir) if cache_enabled else None
        
        logger.info(f"DataFetcher initialized with source={data_source}, cache={cache_enabled}")
    
    def fetch_tick_data(self, symbol: str, date: str, use_cache: bool = True) -> List[Tick]:
        """
        获取逐笔成交数据
        
        Args:
            symbol: 股票代码（如 '000001'）
            date: 日期（如 '20240101'）
            use_cache: 是否使用缓存
        
        Returns:
            Tick数据列表
        """
        # 检查缓存
        if self.cache_enabled and use_cache:
            cached_data = self.cache_manager.get('tick', symbol=symbol, date=date)
            if cached_data is not None:
                logger.info(f"Loaded tick data from cache: {symbol} {date}")
                return cached_data
        
        # 从数据源获取
        if self.data_source == 'akshare':
            ticks = self._fetch_from_akshare(symbol, date)
        elif self.data_source == 'wind':
            ticks = self._fetch_from_wind(symbol, date)
        elif self.data_source == 'tushare':
            ticks = self._fetch_from_tushare(symbol, date)
        else:
            raise ValueError(f"Unsupported data source: {self.data_source}")
        
        # 存入缓存
        if self.cache_enabled and ticks:
            self.cache_manager.set(ticks, 'tick', symbol=symbol, date=date)
        
        logger.info(f"Fetched {len(ticks)} tick records for {symbol} {date}")
        
        return ticks
    
    def _fetch_from_akshare(self, symbol: str, date: str) -> List[Tick]:
        """
        从akshare获取数据
        
        Args:
            symbol: 股票代码
            date: 日期
        
        Returns:
            Tick数据列表
        """
        try:
            import akshare as ak
            
            # 获取逐笔成交数据
            logger.debug(f"Fetching from akshare: {symbol} {date}")
            
            # akshare的逐笔成交接口
            df = ak.stock_zh_a_tick_tx_js(symbol=symbol, date=date)
            
            if df.empty:
                logger.warning(f"No data from akshare for {symbol} {date}")
                return []
            
            # 转换为Tick对象列表
            ticks = []
            for _, row in df.iterrows():
                try:
                    # 解析时间戳
                    timestamp_str = row.get('成交时间', '')
                    if isinstance(timestamp_str, str):
                        # 格式可能是 "09:30:00" 或 "09:30:00.123"
                        time_parts = timestamp_str.split('.')
                        if len(time_parts) == 2:
                            timestamp = datetime.strptime(date + ' ' + time_parts[0], '%Y%m%d %H:%M:%S')
                            # 添加毫秒
                            milliseconds = int(time_parts[1].ljust(3, '0')[:3])
                            timestamp = timestamp.replace(microsecond=milliseconds * 1000)
                        else:
                            timestamp = datetime.strptime(date + ' ' + timestamp_str, '%Y%m%d %H:%M:%S')
                    else:
                        timestamp = pd.to_datetime(timestamp_str)
                    
                    tick = Tick(
                        timestamp=timestamp,
                        symbol=symbol,
                        price=float(row.get('成交价', 0)),
                        volume=int(row.get('成交量', 0)),
                        amount=float(row.get('成交额', 0)),
                        direction=str(row.get('买卖方向', 'N')),
                        bid1_price=float(row.get('买一价', 0)),
                        bid1_vol=int(row.get('买一量', 0)),
                        ask1_price=float(row.get('卖一价', 0)),
                        ask1_vol=int(row.get('卖一量', 0)),
                    )
                    ticks.append(tick)
                except Exception as e:
                    logger.warning(f"Failed to parse tick row: {e}")
                    continue
            
            return ticks
        
        except Exception as e:
            logger.error(f"Failed to fetch from akshare: {e}")
            return []
    
    def _fetch_from_wind(self, symbol: str, date: str) -> List[Tick]:
        """
        从Wind获取数据
        
        Args:
            symbol: 股票代码
            date: 日期
        
        Returns:
            Tick数据列表
        """
        logger.warning("Wind data source not implemented")
        return []
    
    def _fetch_from_tushare(self, symbol: str, date: str) -> List[Tick]:
        """
        从Tushare获取数据
        
        Args:
            symbol: 股票代码
            date: 日期
        
        Returns:
            Tick数据列表
        """
        logger.warning("Tushare data source not implemented")
        return []
    
    def fetch_daily_kline(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日线K线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            K线数据DataFrame
        """
        if self.data_source == 'akshare':
            return self._fetch_kline_from_akshare(symbol, start_date, end_date)
        else:
            raise ValueError(f"Kline data not supported for source: {self.data_source}")
    
    def _fetch_kline_from_akshare(self, symbol: str, start_date: str, 
                                   end_date: str) -> pd.DataFrame:
        """
        从akshare获取K线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            K线数据DataFrame
        """
        try:
            import akshare as ak
            
            logger.debug(f"Fetching kline from akshare: {symbol} {start_date}-{end_date}")
            
            # akshare的A股历史行情接口
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                   start_date=start_date, end_date=end_date,
                                   adjust="qfq")  # 前复权
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to fetch kline from akshare: {e}")
            return pd.DataFrame()
    
    def fetch_stock_info(self, symbol: str) -> dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        if self.data_source == 'akshare':
            return self._fetch_stock_info_from_akshare(symbol)
        else:
            return {}
    
    def _fetch_stock_info_from_akshare(self, symbol: str) -> dict:
        """
        从akshare获取股票信息
        
        Args:
            symbol: 股票代码
        
        Returns:
            股票信息字典
        """
        try:
            import akshare as ak
            
            logger.debug(f"Fetching stock info from akshare: {symbol}")
            
            # 获取个股信息
            df = ak.stock_individual_info_em(symbol=symbol)
            
            if df.empty:
                return {}
            
            # 转换为字典
            info = {}
            for _, row in df.iterrows():
                info[row['item']] = row['value']
            
            return info
        
        except Exception as e:
            logger.error(f"Failed to fetch stock info from akshare: {e}")
            return {}
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache_manager:
            self.cache_manager.clear()
            logger.info("Cache cleared")

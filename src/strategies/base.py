"""策略基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from ..models.tick import Tick
from ..models.result import CapitalAnalysisResult
from ..utils.logger import get_logger

logger = get_logger("strategy")


class StrategyBase(ABC):
    """策略基类"""
    
    def __init__(self, config: Dict):
        """
        初始化策略
        
        Args:
            config: 配置字典
        """
        self.config = config
        logger.info(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    def analyze_day(self, symbol: str, date: str, 
                   tick_data: List[Tick]) -> CapitalAnalysisResult:
        """
        分析单日数据
        
        Args:
            symbol: 股票代码
            date: 日期
            tick_data: tick数据列表
        
        Returns:
            分析结果
        """
        pass
    
    @abstractmethod
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
        pass
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            是否有效
        """
        return True
    
    def get_config(self) -> Dict:
        """
        获取当前配置
        
        Returns:
            配置字典
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict):
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        logger.info(f"Configuration updated for {self.__class__.__name__}")

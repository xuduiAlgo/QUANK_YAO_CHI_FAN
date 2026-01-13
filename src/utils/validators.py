"""数据验证工具"""
from typing import List, Any
from .logger import get_logger

logger = get_logger("validators")


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_tick_data(data: List[Any]) -> bool:
        """
        验证Tick数据
        
        Args:
            data: Tick数据列表
            
        Returns:
            是否有效
        """
        if not data:
            logger.warning("Tick data is empty")
            return False
        
        # 检查必要字段
        required_fields = ['timestamp', 'symbol', 'price', 'volume', 'amount', 'direction']
        
        for i, item in enumerate(data):
            # 如果是字典类型
            if isinstance(item, dict):
                for field in required_fields:
                    if field not in item:
                        logger.error(f"Tick {i} missing required field: {field}")
                        return False
            
            # 如果是对象类型
            elif hasattr(item, '__dict__'):
                for field in required_fields:
                    if not hasattr(item, field):
                        logger.error(f"Tick {i} missing required field: {field}")
                        return False
            else:
                logger.error(f"Tick {i} has invalid type: {type(item)}")
                return False
        
        logger.info(f"Validated {len(data)} tick records")
        return True
    
    @staticmethod
    def validate_price_range(price: float, min_price: float = 0.01, 
                            max_price: float = 10000.0) -> bool:
        """
        验证价格范围
        
        Args:
            price: 价格
            min_price: 最小价格
            max_price: 最大价格
            
        Returns:
            是否有效
        """
        if price < min_price or price > max_price:
            logger.warning(f"Price {price} out of range [{min_price}, {max_price}]")
            return False
        return True
    
    @staticmethod
    def validate_volume(volume: int, min_volume: int = 1, 
                       max_volume: int = 1000000) -> bool:
        """
        验证成交量
        
        Args:
            volume: 成交量
            min_volume: 最小成交量
            max_volume: 最大成交量
            
        Returns:
            是否有效
        """
        if volume < min_volume or volume > max_volume:
            logger.warning(f"Volume {volume} out of range [{min_volume}, {max_volume}]")
            return False
        return True
    
    @staticmethod
    def validate_amount(amount: float, volume: int, price: float, 
                       tolerance: float = 0.01) -> bool:
        """
        验证成交金额是否匹配
        
        Args:
            amount: 成交金额
            volume: 成交量
            price: 成交价格
            tolerance: 容差比例
            
        Returns:
            是否有效
        """
        expected_amount = volume * price * 100  # 1手=100股
        diff_ratio = abs(amount - expected_amount) / expected_amount if expected_amount > 0 else 0
        
        if diff_ratio > tolerance:
            logger.warning(
                f"Amount mismatch: expected {expected_amount:.2f}, "
                f"got {amount:.2f}, diff: {diff_ratio:.2%}"
            )
            return False
        
        return True
    
    @staticmethod
    def validate_direction(direction: str) -> bool:
        """
        验证买卖方向
        
        Args:
            direction: 买卖方向
            
        Returns:
            是否有效
        """
        valid_directions = ['B', 'S', 'N', 'BUY', 'SELL', 'UNKNOWN']
        if direction.upper() not in valid_directions:
            logger.warning(f"Invalid direction: {direction}")
            return False
        return True
    
    @staticmethod
    def validate_config(config: dict) -> bool:
        """
        验证配置文件
        
        Args:
            config: 配置字典
            
        Returns:
            是否有效
        """
        required_keys = [
            'data', 'algorithm', 'classifier', 'storage', 'visualization'
        ]
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Config missing required key: {key}")
                return False
        
        # 验证算法参数
        algorithm = config.get('algorithm', {})
        if 'window_sec' not in algorithm or algorithm['window_sec'] <= 0:
            logger.error("Invalid algorithm.window_sec")
            return False
        
        if 'synthetic_threshold' not in algorithm or algorithm['synthetic_threshold'] <= 0:
            logger.error("Invalid algorithm.synthetic_threshold")
            return False
        
        # 验证分类参数
        classifier = config.get('classifier', {})
        if 'big_order_threshold' not in classifier or classifier['big_order_threshold'] <= 0:
            logger.error("Invalid classifier.big_order_threshold")
            return False
        
        logger.info("Config validation passed")
        return True
    
    @staticmethod
    def clean_data(data: List[Any]) -> List[Any]:
        """
        清洗数据，移除无效记录
        
        Args:
            data: 原始数据列表
            
        Returns:
            清洗后的数据列表
        """
        cleaned = []
        removed_count = 0
        
        for item in data:
            try:
                # 如果是字典类型
                if isinstance(item, dict):
                    price = item.get('price', 0)
                    volume = item.get('volume', 0)
                    amount = item.get('amount', 0)
                    direction = item.get('direction', '')
                
                # 如果是对象类型
                elif hasattr(item, '__dict__'):
                    price = getattr(item, 'price', 0)
                    volume = getattr(item, 'volume', 0)
                    amount = getattr(item, 'amount', 0)
                    direction = getattr(item, 'direction', '')
                else:
                    removed_count += 1
                    continue
                
                # 验证各项指标
                if (DataValidator.validate_price_range(price) and
                    DataValidator.validate_volume(volume) and
                    DataValidator.validate_direction(direction)):
                    cleaned.append(item)
                else:
                    removed_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to clean record: {e}")
                removed_count += 1
        
        logger.info(f"Data cleaning completed: {len(cleaned)} valid, {removed_count} removed")
        return cleaned

"""缓存工具"""
import pickle
import hashlib
from pathlib import Path
from typing import Any, Optional
from .logger import get_logger

logger = get_logger("cache")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            缓存键（哈希值）
        """
        # 将参数转换为字符串
        key_str = prefix + "_" + "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        # 生成MD5哈希
        hash_obj = hashlib.md5(key_str.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            缓存的数据，如果不存在则返回None
        """
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            logger.debug(f"Cache hit: {cache_key}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_key}: {e}")
            return None
    
    def set(self, data: Any, prefix: str, **kwargs) -> bool:
        """
        将数据存入缓存
        
        Args:
            data: 要缓存的数据
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            是否成功
        """
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.debug(f"Cache saved: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cache {cache_key}: {e}")
            return False
    
    def exists(self, prefix: str, **kwargs) -> bool:
        """
        检查缓存是否存在
        
        Args:
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            是否存在
        """
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        return cache_file.exists()
    
    def delete(self, prefix: str, **kwargs) -> bool:
        """
        删除缓存
        
        Args:
            prefix: 键前缀
            **kwargs: 键参数
            
        Returns:
            是否成功
        """
        cache_key = self._get_cache_key(prefix, **kwargs)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Cache deleted: {cache_key}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete cache {cache_key}: {e}")
                return False
        
        return False
    
    def clear(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            是否成功
        """
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info("All caches cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
            return False

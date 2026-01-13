# 基于Level-2数据的A股大资金成本与意图分析系统 - 项目架构

## 1. 项目总体架构

```
level2-capital-analysis/
├── README.md                          # 项目说明文档
├── requirements.txt                   # Python依赖包
├── config/                            # 配置文件目录
│   ├── config.yaml                    # 主配置文件
│   ├── thresholds.yaml                # 阈值参数配置
│   └── symbols.yaml                   # 股票代码列表
├── src/                               # 源代码目录
│   ├── __init__.py
│   ├── data/                          # 数据模块
│   │   ├── __init__.py
│   │   ├── fetcher.py                 # 数据获取器
│   │   ├── storage.py                 # 数据存储管理
│   │   └── preprocessor.py            # 数据预处理
│   ├── core/                          # 核心算法模块
│   │   ├── __init__.py
│   │   ├── classifier.py              # 意图分类引擎（模块一）
│   │   ├── synthetic_builder.py       # 订单重构引擎（模块二）
│   │   ├── cost_calculator.py         # 成本计算模型（模块三）
│   │   └── chip_analyzer.py           # 筹码分布分析（模块四）
│   ├── models/                        # 数据模型
│   │   ├── __init__.py
│   │   ├── tick.py                    # Tick数据模型
│   │   ├── order.py                   # 订单模型
│   │   └── result.py                  # 分析结果模型
│   ├── utils/                         # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py                  # 日志工具
│   │   ├── cache.py                   # 缓存工具
│   │   └── validators.py              # 数据验证
│   ├── strategies/                    # 策略模块
│   │   ├── __init__.py
│   │   ├── base.py                    # 策略基类
│   │   └── capital_tracking.py        # 资金追踪策略
│   └── visualization/                 # 可视化模块
│       ├── __init__.py
│       ├── charts.py                  # 图表绘制
│       └── dashboard.py               # 仪表板
├── tests/                             # 测试目录
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_synthetic_builder.py
│   ├── test_cost_calculator.py
│   └── test_integration.py
├── notebooks/                         # Jupyter笔记本目录
│   ├── 01_data_exploration.ipynb
│   ├── 02_algorithm_validation.ipynb
│   └── 03_backtesting.ipynb
├── data/                              # 数据目录（.gitignore）
│   ├── raw/                           # 原始数据
│   ├── processed/                     # 处理后数据
│   └── cache/                         # 缓存数据
├── logs/                              # 日志目录
├── scripts/                           # 脚本目录
│   ├── run_daily_analysis.py          # 每日分析脚本
│   ├── run_realtime_monitor.py        # 实时监控脚本
│   └── backtest.py                    # 回测脚本
└── docs/                              # 文档目录
    ├── api_reference.md               # API参考
    ├── algorithm_details.md           # 算法详解
    └── user_guide.md                  # 用户指南
```

## 2. 核心模块设计

### 2.1 数据模型层 (models/)

#### Tick数据模型
```python
class Tick:
    """Level-2逐笔成交数据模型"""
    timestamp: datetime      # 时间戳（毫秒精度）
    symbol: str              # 股票代码
    price: float             # 成交价格
    volume: int              # 成交数量（手）
    amount: float            # 成交金额（元）
    direction: str           # 买卖方向 B/S/N
    bid1_price: float        # 买一价
    bid1_vol: int            # 买一量
    ask1_price: float        # 卖一价
    ask1_vol: int            # 卖一量
```

#### 订单模型
```python
class SyntheticOrder:
    """合成订单模型"""
    start_time: datetime     # 起始时间
    end_time: datetime       # 结束时间
    symbol: str              # 股票代码
    direction: str           # 买卖方向
    total_volume: int        # 总成交量
    total_amount: float      # 总成交金额
    vwap: float              # 成交均价
    tick_count: int          # 包含的tick数量
    order_type: str          # 订单类型：ORIGINAL/SYNTHETIC/ALGO
    confidence: float        # 可信度权重
```

#### 分析结果模型
```python
class CapitalAnalysisResult:
    """资金分析结果模型"""
    symbol: str
    date: str
    aggressive_buy_amount: float
    aggressive_sell_amount: float
    defensive_buy_amount: float
    defensive_sell_amount: float
    weighted_cost: float              # 加权成本
    cost_ma_5: float                   # 5日主力成本均线
    cost_ma_10: float                  # 10日主力成本均线
    net_flow: float                    # 净流向
    concentration_ratio: float         # 筹码集中度
    chip_peak_price: float             # 筹码峰位价格
```

### 2.2 核心算法层 (core/)

#### 2.2.1 意图分类引擎 (classifier.py)
**功能**：
- 区分攻击性/防御性买卖
- 识别异常交易（ETF申赎、套利等）
- 计算盘口压力指标

**核心算法**：
```python
class TickClassifier:
    """Tick数据分类器"""
    
    def classify_tick(self, tick: Tick, orderbook: OrderBook) -> Tuple[str, float]:
        """
        对单笔tick进行分类
        
        返回: (label, weight)
        label: AGG_BUY, AGG_SELL, DEF_BUY, DEF_SELL, NOISE
        weight: 权重系数 (0.0-2.0)
        """
        # 1. 判断是否为大单
        if self._is_big_order(tick):
            # 2. 判断方向
            if tick.direction == 'B':
                # 3. 判断是否为攻击性（主动拉升）
                if self._is_aggressive_buy(tick, orderbook):
                    return ('AGG_BUY', 1.5)
                else:
                    return ('DEF_BUY', 0.8)
            else:  # direction == 'S'
                # 4. 判断是否为攻击性（主动砸盘）
                if self._is_aggressive_sell(tick, orderbook):
                    return ('AGG_SELL', 1.5)
                else:
                    return ('DEF_SELL', 0.8)
        
        # 小单处理 - 暂时标记为NOISE，等待合成
        return ('SMALL_ORDER', 0.0)
    
    def _is_big_order(self, tick: Tick) -> bool:
        """判断是否为大单"""
        return tick.amount > self.big_order_threshold
    
    def _is_aggressive_buy(self, tick: Tick, orderbook: OrderBook) -> bool:
        """
        判断是否为攻击性买单
        
        攻击性买单特征：
        1. 成交价 > 卖一价（主动吃单）
        2. 或者成交后卖一量显著减少
        """
        # 方案1: 比较成交价与盘口价格
        if tick.price > tick.ask1_price:
            return True
        
        # 方案2: 检测被动护盘特征
        # 如果成交价 == 买一价，且买一量巨大（城墙单）
        if tick.price == tick.bid1_price and tick.bid1_vol > self.wall_threshold:
            return False
        
        # 其他情况根据盘口变化判断
        return self._check_orderbook_impact(tick, orderbook, 'buy')
    
    def _check_orderbook_impact(self, tick: Tick, orderbook: OrderBook, direction: str) -> bool:
        """通过盘口冲击判断意图"""
        # 实现略：比较前后盘口变化
        pass
```

#### 2.2.2 订单重构引擎 (synthetic_builder.py)
**功能**：
- 时间窗聚合小单
- 识别算法交易模式（TWAP/VWAP）
- 生成合成大单

**核心算法**：
```python
class SyntheticOrderBuilder:
    """合成订单构建器"""
    
    def __init__(self, window_sec: int = 30, threshold: float = 500000):
        self.window_sec = window_sec
        self.threshold = threshold  # 合成阈值（元）
        self.buffers: Dict[str, TickBuffer] = {}  # 每个股票的tick缓冲区
    
    def feed(self, tick: Tick, label: str):
        """喂入tick数据"""
        symbol = tick.symbol
        
        if symbol not in self.buffers:
            self.buffers[symbol] = TickBuffer(self.window_sec)
        
        # 添加到缓冲区
        self.buffers[symbol].add_tick(tick, label)
        
        # 检查是否需要生成合成订单
        synthetic_orders = self.buffers[symbol].try_generate_synthetic(self.threshold)
        
        return synthetic_orders
    
    def get_flushed_orders(self) -> List[SyntheticOrder]:
        """获取所有待处理的合成订单"""
        orders = []
        for buffer in self.buffers.values():
            orders.extend(buffer.flush_synthetic())
        return orders


class TickBuffer:
    """Tick缓冲区"""
    
    def __init__(self, window_sec: int):
        self.window_sec = window_sec
        self.buy_ticks: List[Tick] = []  # 买入tick列表
        self.sell_ticks: List[Tick] = []  # 卖出tick列表
    
    def add_tick(self, tick: Tick, label: str):
        """添加tick到对应方向缓冲区"""
        if label in ['AGG_BUY', 'DEF_BUY', 'SMALL_BUY']:
            self.buy_ticks.append(tick)
        elif label in ['AGG_SELL', 'DEF_SELL', 'SMALL_SELL']:
            self.sell_ticks.append(tick)
        
        # 清理过期tick
        self._cleanup_old_ticks()
    
    def try_generate_synthetic(self, threshold: float) -> List[SyntheticOrder]:
        """尝试生成合成订单"""
        orders = []
        
        # 检查买入方向
        buy_order = self._check_and_generate(self.buy_ticks, 'BUY', threshold)
        if buy_order:
            orders.append(buy_order)
            self.buy_ticks.clear()
        
        # 检查卖出方向
        sell_order = self._check_and_generate(self.sell_ticks, 'SELL', threshold)
        if sell_order:
            orders.append(sell_order)
            self.sell_ticks.clear()
        
        return orders
    
    def _check_and_generate(self, ticks: List[Tick], direction: str, 
                           threshold: float) -> Optional[SyntheticOrder]:
        """检查并生成合成订单"""
        if not ticks:
            return None
        
        total_amount = sum(t.amount for t in ticks)
        
        # 累计金额达到阈值
        if total_amount >= threshold:
            # 计算VWAP
            total_volume = sum(t.volume for t in ticks)
            vwap = total_amount / total_volume if total_volume > 0 else 0
            
            # 检测是否为算法交易
            order_type, confidence = self._detect_algo_pattern(ticks)
            
            return SyntheticOrder(
                start_time=ticks[0].timestamp,
                end_time=ticks[-1].timestamp,
                symbol=ticks[0].symbol,
                direction=direction,
                total_volume=total_volume,
                total_amount=total_amount,
                vwap=vwap,
                tick_count=len(ticks),
                order_type=order_type,
                confidence=confidence
            )
        
        return None
    
    def _detect_algo_pattern(self, ticks: List[Tick]) -> Tuple[str, float]:
        """
        检测算法交易模式
        
        返回: (order_type, confidence)
        order_type: ALGO_TWAP, ALGO_VWAP, ORIGINAL
        confidence: 0.0-1.0
        """
        if len(ticks) < 3:
            return ('ORIGINAL', 1.0)
        
        # 计算时间间隔
        intervals = []
        for i in range(1, len(ticks)):
            interval = (ticks[i].timestamp - ticks[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        # 时间间隔方差
        interval_variance = np.var(intervals)
        
        # 判断是否为TWAP（时间间隔稳定）
        if interval_variance < 1.0:  # 方差小于1秒
            return ('ALGO_TWAP', 1.3)  # 置信度权重1.3
        
        # 判断是否为VWAP（金额接近）
        amounts = [t.amount for t in ticks]
        amount_variance = np.var(amounts)
        avg_amount = np.mean(amounts)
        
        if avg_amount > 0 and amount_variance / avg_amount < 0.3:
            return ('ALGO_VWAP', 1.3)
        
        return ('ORIGINAL', 1.0)
    
    def _cleanup_old_ticks(self):
        """清理过期的tick"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_sec)
        
        self.buy_ticks = [t for t in self.buy_ticks if t.timestamp >= cutoff]
        self.sell_ticks = [t for t in self.sell_ticks if t.timestamp >= cutoff]
```

#### 2.2.3 成本计算模型 (cost_calculator.py)
**功能**：
- 计算加权平均成本
- 计算主力成本均线
- 计算净流向指标

**核心算法**：
```python
class CostCalculator:
    """成本计算器"""
    
    def __init__(self):
        self.weight_map = {
            'AGG_BUY': 1.5,
            'AGG_SELL': 1.5,
            'DEF_BUY': 0.8,
            'DEF_SELL': 0.8,
            'ALGO_TWAP': 1.3,
            'ALGO_VWAP': 1.3,
            'SMALL_ORDER': 0.0,
            'NOISE': 0.0
        }
    
    def calculate_weighted_cost(self, orders: List[SyntheticOrder]) -> float:
        """
        计算加权平均成本（VWAP）
        
        公式:
        Weighted_Cost = Σ(Price_i × Volume_i × Weight_i) / Σ(Volume_i × Weight_i)
        """
        numerator = 0.0  # 分子
        denominator = 0.0  # 分母
        
        for order in orders:
            # 只计算买入订单的成本
            if order.direction == 'BUY':
                weight = self.weight_map.get(order.order_type, 1.0)
                weight = weight * order.confidence
                
                weighted_volume = order.total_volume * weight
                weighted_amount = order.total_amount * weight
                
                numerator += weighted_amount
                denominator += weighted_volume
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def calculate_cost_ma(self, daily_costs: List[float], period: int) -> float:
        """
        计算主力成本移动平均线
        
        参数:
            daily_costs: 历史每日成本列表 [cost_today, cost_yesterday, ...]
            period: 均线周期（如5日、10日）
        """
        if len(daily_costs) < period:
            return np.mean(daily_costs)
        
        return np.mean(daily_costs[:period])
    
    def calculate_net_flow(self, orders: List[SyntheticOrder], 
                          float_market_cap: float) -> float:
        """
        计算主力净流向
        
        公式:
        Net_Flow = (Weighted_In - Weighted_Out) / Float_Market_Cap
        """
        weighted_in = 0.0
        weighted_out = 0.0
        
        for order in orders:
            weight = self.weight_map.get(order.order_type, 1.0) * order.confidence
            
            if order.direction == 'BUY':
                weighted_in += order.total_amount * weight
            else:
                weighted_out += order.total_amount * weight
        
        if float_market_cap == 0:
            return 0.0
        
        return (weighted_in - weighted_out) / float_market_cap
```

#### 2.2.4 筹码分布分析 (chip_analyzer.py)
**功能**：
- 构建筹码分布图
- 识别筹码密集区
- 验证主力成本线有效性

**核心算法**：
```python
class ChipAnalyzer:
    """筹码分布分析器"""
    
    def build_chip_distribution(self, ticks: List[Tick], price_bins: int = 100):
        """
        构建筹码分布图
        
        返回: 价格区间到持仓量的映射
        """
        if not ticks:
            return {}
        
        # 计算价格范围
        prices = [t.price for t in ticks]
        min_price, max_price = min(prices), max(prices)
        price_step = (max_price - min_price) / price_bins
        
        # 初始化分布
        distribution = {}
        for i in range(price_bins):
            price_low = min_price + i * price_step
            price_high = price_low + price_step
            price_center = (price_low + price_high) / 2
            distribution[price_center] = 0
        
        # 分配成交到价格区间
        for tick in ticks:
            # 简化：假设每笔成交均匀分布在价格区间
            # 实际应根据成交价精确分配
            price_center = round((tick.price - min_price) / price_step) * price_step + min_price
            price_center = round(price_center, 2)
            
            if price_center in distribution:
                distribution[price_center] += tick.volume
        
        return distribution
    
    def find_chip_peaks(self, distribution: Dict[float, int], 
                       top_n: int = 3) -> List[Tuple[float, int]]:
        """
        识别筹码峰位
        
        返回: [(price, volume), ...] 按持仓量降序
        """
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]
    
    def validate_cost_line(self, main_capital_cost: float, 
                          chip_distribution: Dict[float, int]) -> bool:
        """
        验证主力成本线是否有效
        
        验证逻辑：
        1. 主力成本应位于筹码密集区（峰位）下方或重心位置
        2. 如果成本远低于筹码峰位（例如下方20%），可能计算失效
        """
        if not chip_distribution:
            return True
        
        peaks = self.find_chip_peaks(chip_distribution, top_n=1)
        if not peaks:
            return True
        
        peak_price, peak_volume = peaks[0]
        
        # 计算成本与峰位的距离比例
        if peak_price > 0:
            distance_ratio = abs(main_capital_cost - peak_price) / peak_price
            
            # 如果距离超过20%，可能计算失效
            if distance_ratio > 0.2:
                logger.warning(f"主力成本 {main_capital_cost} 距离筹码峰位 {peak_price} 超过20%")
                return False
        
        return True
    
    def calculate_concentration_ratio(self, distribution: Dict[float, int]) -> float:
        """
        计算筹码集中度
        
        集中度 = 前20%价格区间的持仓量 / 总持仓量
        """
        if not distribution:
            return 0.0
        
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        total_volume = sum(volume for _, volume in sorted_items)
        
        # 前20%价格区间
        top_count = max(1, len(sorted_items) // 5)
        top_volume = sum(volume for _, volume in sorted_items[:top_count])
        
        if total_volume == 0:
            return 0.0
        
        return top_volume / total_volume
```

### 2.3 数据层 (data/)

#### 数据获取器 (fetcher.py)
```python
class DataFetcher:
    """Level-2数据获取器"""
    
    def __init__(self, data_source: str = 'akshare'):
        self.data_source = data_source
    
    def fetch_tick_data(self, symbol: str, date: str) -> List[Tick]:
        """获取逐笔成交数据"""
        if self.data_source == 'akshare':
            return self._fetch_from_akshare(symbol, date)
        elif self.data_source == 'wind':
            return self._fetch_from_wind(symbol, date)
        else:
            raise ValueError(f"Unsupported data source: {self.data_source}")
    
    def _fetch_from_akshare(self, symbol: str, date: str) -> List[Tick]:
        """从akshare获取数据"""
        import akshare as ak
        
        # 获取逐笔成交
        df = ak.stock_zh_a_tick_tx_js(symbol=symbol, date=date)
        
        # 转换为Tick对象列表
        ticks = []
        for _, row in df.iterrows():
            tick = Tick(
                timestamp=pd.to_datetime(row['成交时间']),
                symbol=symbol,
                price=float(row['成交价']),
                volume=int(row['成交量']),
                amount=float(row['成交额']),
                direction=row['买卖方向'],
                bid1_price=float(row['买一价']),
                bid1_vol=int(row['买一量']),
                ask1_price=float(row['卖一价']),
                ask1_vol=int(row['卖一量'])
            )
            ticks.append(tick)
        
        return ticks
    
    def fetch_orderbook(self, symbol: str, date: str) -> pd.DataFrame:
        """获取订单簿快照数据"""
        pass
```

### 2.4 策略层 (strategies/)

#### 资金追踪策略 (capital_tracking.py)
```python
class CapitalTrackingStrategy:
    """资金追踪策略"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.classifier = TickClassifier(config)
        self.synthetic_builder = SyntheticOrderBuilder(
            window_sec=config['window_sec'],
            threshold=config['synthetic_threshold']
        )
        self.cost_calculator = CostCalculator()
        self.chip_analyzer = ChipAnalyzer()
    
    def analyze_day(self, symbol: str, date: str, 
                   tick_data: List[Tick]) -> CapitalAnalysisResult:
        """
        分析单日数据
        
        流程：
        1. 分类每笔tick
        2. 合成大单
        3. 计算成本
        4. 验证筹码
        """
        all_orders = []
        
        for tick in tick_data:
            # 步骤1: 分类
            label, _ = self.classifier.classify_tick(tick, None)
            
            # 步骤2: 合成大单
            synthetic_orders = self.synthetic_builder.feed(tick, label)
            all_orders.extend(synthetic_orders)
        
        # 获取所有剩余的合成订单
        all_orders.extend(self.synthetic_builder.get_flushed_orders())
        
        # 步骤3: 计算成本
        weighted_cost = self.cost_calculator.calculate_weighted_cost(all_orders)
        
        # 步骤4: 筹码分析
        chip_distribution = self.chip_analyzer.build_chip_distribution(tick_data)
        chip_peaks = self.chip_analyzer.find_chip_peaks(chip_distribution)
        concentration = self.chip_analyzer.calculate_concentration_ratio(chip_distribution)
        
        # 验证成本线
        is_valid = self.chip_analyzer.validate_cost_line(weighted_cost, chip_distribution)
        
        # 构建结果
        result = CapitalAnalysisResult(
            symbol=symbol,
            date=date,
            aggressive_buy_amount=sum(o.total_amount for o in all_orders 
                                     if o.order_type == 'AGG_BUY'),
            # ... 其他字段
            weighted_cost=weighted_cost,
            concentration_ratio=concentration,
            chip_peak_price=chip_peaks[0][0] if chip_peaks else 0,
            validation_status=is_valid
        )
        
        return result
```

## 3. 配置文件设计

### config.yaml
```yaml
# 主配置文件

# 数据源配置
data:
  source: akshare  # akshare, wind, tushare
  cache_enabled: true
  cache_dir: data/cache

# 算法参数
algorithm:
  window_sec: 30  # 时间窗口（秒）
  synthetic_threshold: 500000  # 合成阈值（元）
  
# 分类参数
classifier:
  big_order_threshold: 100000  # 大单阈值（元）
  wall_threshold: 10000  # 城墙单阈值（手）
  
# 存储配置
storage:
  type: sqlite  # sqlite, mysql, postgresql
  path: data/analysis.db
  
# 可视化配置
visualization:
  chart_width: 1200
  chart_height: 800
  theme: dark
```

### symbols.yaml
```yaml
# 股票代码列表
symbols:
  - code: "000001"
    name: "平安银行"
  - code: "000002"
    name: "万科A"
  - code: "600519"
    name: "贵州茅台"
  - code: "600036"
    name: "招商银行"
```

## 4. 技术栈选型

| 模块 | 技术栈 | 说明 |
|------|--------|------|
| 数据获取 | akshare/tushare | 免费开源数据源 |
| 数据处理 | pandas, numpy | 核心数据处理库 |
| 数据存储 | SQLite/MySQL | 关系型数据库 |
| 可视化 | matplotlib, plotly | 图表绘制 |
| 日志 | loguru | 简洁的日志库 |
| 配置管理 | pyyaml | YAML配置文件 |
| 异步处理 | asyncio | 支持多股票并行处理 |
| 测试 | pytest | 单元测试框架 |
| 类型提示 | typing | 类型安全 |

## 5. 开发路线图

### Phase 1: 基础框架搭建（第1-2周）
- [ ] 项目结构初始化
- [ ] 数据模型定义
- [ ] 配置文件创建
- [ ] 日志系统搭建

### Phase 2: 数据获取与预处理（第3-4周）
- [ ] akshare数据接口封装
- [ ] 数据清洗模块
- [ ] 数据存储模块
- [ ] 单元测试

### Phase 3: 核心算法实现（第5-7周）
- [ ] 意图分类引擎
- [ ] 订单重构引擎
- [ ] 成本计算模型
- [ ] 筹码分布分析
- [ ] 算法测试与验证

### Phase 4: 策略整合（第8-9周）
- [ ] 资金追踪策略封装
- [ ] 日线分析流程
- [ ] 批处理脚本
- [ ] 集成测试

### Phase 5: 可视化与回测（第10-11周）
- [ ] 成本线图表
- [ ] 筹码分布图
- [ ] 主力流向图
- [ ] 历史回测框架

### Phase 6: 优化与文档（第12周）
- [ ] 性能优化
- [ ] 异常处理完善
- [ ] API文档编写
- [ ] 用户手册编写

## 6. 关键技术难点与解决方案

### 难点1: 算法交易识别
**问题**: 如何准确识别TWAP/VWAP算法交易？
**解决方案**:
- 统计时间间隔方差（TWAP）
- 统计成交金额方差（VWAP）
- 结合订单类型与可信度权重

### 难点2: 对倒干扰过滤
**问题**: 如何避免主力自买自卖造成的干扰？
**解决方案**:
- 引入账户去重（如果有数据）
- 价格异常波动检测
- 成交量与成交额一致性校验

### 难点3: 计算滞后性
**问题**: 30秒时间窗导致成本计算滞后
**解决方案**:
- 提供实时估算（基于部分数据）
- 提供滞后时间标识
- 针对不同交易频率提供多时间窗口选项

## 7. 性能指标预期

| 指标 | 目标值 |
|------|--------|
| 单日数据处理速度 | < 5秒/股 |
| 内存占用 | < 500MB（单股） |
| 准确率 | > 85%（与事后验证对比） |
| 误报率 | < 15% |

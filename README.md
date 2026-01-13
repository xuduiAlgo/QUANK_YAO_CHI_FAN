# 基于Level-2数据的A股大资金成本与意图分析系统

## 项目简介

本系统是一个完整的量化分析系统，通过Level-2逐笔数据识别并重构"大资金"的真实买卖行为（含拆单），计算其持仓成本及意图（攻击/防御），为辅助判断股价趋势提供数据支撑。

### 核心特性

- 🔍 **意图识别**：区分攻击性/防御性买卖行为
- 🔄 **订单重构**：识别并合成被拆分的大单（TWAP/VWAP算法交易）
- 💰 **成本计算**：计算加权平均主力成本及均线
- 📊 **筹码分析**：构建筹码分布图并验证成本线有效性
- 📈 **可视化展示**：提供丰富的图表和HTML报告
- 💾 **数据存储**：支持SQLite/MySQL/PostgreSQL
- 🎯 **信号生成**：基于分析结果生成买卖信号

## 系统架构

```
level2-capital-analysis/
├── src/                      # 源代码目录
│   ├── data/                  # 数据模块
│   ├── core/                  # 核心算法模块
│   ├── models/                # 数据模型
│   ├── strategies/            # 策略模块
│   ├── utils/                 # 工具模块
│   └── visualization/         # 可视化模块
├── config/                   # 配置文件
├── scripts/                  # 执行脚本
├── tests/                    # 测试文件
├── notebooks/                # Jupyter笔记本
└── docs/                     # 文档
```

### 核心模块说明

#### 1. 数据模型层 (models/)
- **Tick**: Level-2逐笔成交数据模型
- **SyntheticOrder**: 合成订单模型
- **CapitalAnalysisResult**: 分析结果模型

#### 2. 核心算法层 (core/)
- **TickClassifier**: 意图分类引擎
  - 区分攻击性/防御性买卖
  - 识别异常交易（ETF申赎、套利等）
  
- **SyntheticOrderBuilder**: 订单重构引擎
  - 时间窗聚合小单
  - 识别TWAP/VWAP算法交易
  - 生成合成大单
  
- **CostCalculator**: 成本计算模型
  - 计算加权平均成本（VWAP）
  - 计算主力成本均线
  - 计算净流向指标
  
- **ChipAnalyzer**: 筹码分布分析
  - 构建筹码分布图
  - 识别筹码密集区
  - 验证主力成本线有效性

#### 3. 数据层 (data/)
- **DataFetcher**: 数据获取器（支持akshare、wind、tushare）
- **StorageManager**: 存储管理器
- **DataPreprocessor**: 数据预处理器

#### 4. 策略层 (strategies/)
- **CapitalTrackingStrategy**: 资金追踪策略
  - 整合所有核心模块
  - 执行完整分析流程
  - 生成交易信号

#### 5. 可视化层 (visualization/)
- **ChartVisualizer**: 图表绘制器
- **Dashboard**: 分析仪表板

## 快速开始

### 环境要求

- Python 3.8+
- pandas
- numpy
- matplotlib
- akshare (数据源)
- pyyaml

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置文件

编辑 `config/config.yaml` 配置系统参数：

```yaml
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

# 均线参数
moving_averages:
  periods: [5, 10, 20]  # 均线周期
```

### 运行每日分析

```bash
# 分析当天数据
python scripts/run_daily_analysis.py

# 分析指定日期
python scripts/run_daily_analysis.py 20240101
```

### 分析单只股票

```python
from src.strategies import CapitalTrackingStrategy
from src.data import DataFetcher, StorageManager
from src.visualization import Dashboard

# 初始化
fetcher = DataFetcher('akshare')
storage = StorageManager('data/analysis.db')
strategy = CapitalTrackingStrategy({
    'window_sec': 30,
    'synthetic_threshold': 500000,
    'big_order_threshold': 100000,
    'wall_threshold': 10000,
    'ma_periods': [5, 10, 20]
})

# 获取数据
tick_data = fetcher.fetch_tick_data('000001', '20240101')

# 执行分析
result = strategy.analyze_day('000001', '20240101', tick_data)

# 生成报告
dashboard = Dashboard()
dashboard.print_summary([result], '000001')
dashboard.generate_daily_report([result], '000001', 'output')
```

## 核心算法原理

### 1. 意图分类

**攻击性买单特征**：
- 成交价 > 卖一价（主动吃单）
- 成交后卖一量显著减少

**防御性买单特征**：
- 成交价 == 买一价（被动挂单）
- 买一量巨大（城墙单）

### 2. 订单重构

**时间窗聚合**：
- 在30秒窗口内累加所有小额成交
- 若累计金额 > 50万，生成"合成大单"

**算法交易识别**：
- TWAP: 时间间隔方差 < 1秒
- VWAP: 成交金额方差 / 平均金额 < 30%

### 3. 成本计算

**加权平均成本公式**：

```
Weighted_Cost = Σ(Price_i × Volume_i × Weight_i) / Σ(Volume_i × Weight_i)
```

**权重系数**：
- 攻击性买入: 1.5
- 算法拆单买入: 1.3
- 被动防御买入: 0.8
- 小单/噪音: 0

### 4. 筹码验证

- 主力成本应位于筹码密集区（峰位）下方或重心位置
- 如果成本远低于筹码峰位（超过20%），可能计算失效

## 输出指标说明

| 指标 | 说明 |
|------|------|
| weighted_cost | 主力加权成本 |
| cost_ma_5/10/20 | 5/10/20日主力成本均线 |
| net_flow | 主力净流向（占流通市值比例） |
| aggressive_buy_amount | 攻击性买入金额 |
| defensive_buy_amount | 防御性买入金额 |
| algo_buy_amount | 算法买入金额 |
| concentration_ratio | 筹码集中度（前20%价格区间的持仓比例） |
| chip_peak_price | 筹码峰位价格 |
| support_price | 支撑位价格 |
| resistance_price | 压力位价格 |
| validation_status | 成本线验证状态（VALID/INVALID） |

## 可视化展示

系统提供多种图表：

1. **主力成本趋势图**：展示主力成本及均线走势
2. **净流向柱状图**：展示每日主力资金流入流出
3. **筹码分布图**：展示筹码分布及主力成本位置
4. **订单构成图**：展示各类订单金额构成
5. **筹码集中度图**：展示筹码集中度趋势
6. **综合仪表板**：四合一综合展示
7. **多股票对比图**：多股票指标对比

### 生成报告示例

```python
from src.visualization import Dashboard

dashboard = Dashboard(theme='dark')

# 生成图表报告
dashboard.generate_daily_report(results, '000001', 'output')

# 生成HTML报告
dashboard.generate_html_report(results, '000001', 'output')

# 导出CSV
dashboard.export_to_csv(results, '000001', 'output')

# 打印摘要
dashboard.print_summary(results, '000001')
```

## 数据源支持

### 1. akshare（推荐）

免费开源，支持Level-2数据：

```python
from src.data import DataFetcher

fetcher = DataFetcher('akshare')
tick_data = fetcher.fetch_tick_data('000001', '20240101')
```

### 2. Wind

需要Wind账号：

```python
fetcher = DataFetcher('wind')
tick_data = fetcher.fetch_tick_data('000001', '20240101')
```

### 3. Tushare

需要Tushare Token：

```python
fetcher = DataFetcher('tushare')
tick_data = fetcher.fetch_tick_data('000001', '20240101')
```

## 数据存储

系统支持多种存储方式：

### SQLite（默认）

```yaml
storage:
  type: sqlite
  path: data/analysis.db
```

### MySQL

```yaml
storage:
  type: mysql
  host: localhost
  port: 3306
  database: stock_analysis
  user: root
  password: password
```

### PostgreSQL

```yaml
storage:
  type: postgresql
  host: localhost
  port: 5432
  database: stock_analysis
  user: postgres
  password: password
```

## 性能优化

### 1. 数据缓存

启用缓存可避免重复下载：

```yaml
data:
  cache_enabled: true
  cache_dir: data/cache
```

### 2. 批处理

使用批量操作提升性能：

```python
# 批量保存
storage.save_tick_data(tick_list, date)

# 批量加载
storage.load_analysis_history(symbol, start_date, end_date)
```

### 3. 异步处理

支持多股票并行分析：

```python
import asyncio
from src.strategies import CapitalTrackingStrategy

async def analyze_multiple(symbols, date):
    tasks = []
    for symbol in symbols:
        task = asyncio.create_task(analyze_single(symbol, date))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

## 注意事项与限制

### 1. 计算滞后性

- 时间窗聚合（30秒）导致成本计算有轻微滞后
- 不适合超高频（秒级）交易
- 适合日内趋势或波段交易

### 2. 对倒干扰

- 主力可能通过自买自卖制造虚假大单
- 系统已引入异常检测机制
- 建议结合其他指标综合判断

### 3. 数据质量

- Level-2数据质量影响分析准确性
- 建议使用付费数据源获取更完整数据
- 定期检查数据完整性

### 4. 绝对成本不可得

- 系统输出的是"统计学近似成本"
- 非主力的会计成本
- 应视作"支撑/压力参考带"

## 常见问题

### Q1: 为什么分析结果为空？

A: 可能原因：
1. 数据源未返回数据
2. 日期不是交易日
3. 股票代码错误
4. 网络连接问题

检查日志获取详细错误信息。

### Q2: 如何调整分析参数？

A: 编辑 `config/config.yaml` 文件：

```yaml
algorithm:
  window_sec: 60  # 调整为60秒窗口
  synthetic_threshold: 1000000  # 调整为100万阈值
```

### Q3: 成本线验证失败怎么办？

A: 可能原因：
1. 数据质量问题
2. 主力已彻底换庄
3. 计算参数不合适

建议：
1. 检查数据质量
2. 调整算法参数
3. 结合其他指标验证

### Q4: 如何添加新股票？

A: 编辑 `config/symbols.yaml`：

```yaml
symbols:
  - code: "000001"
    name: "平安银行"
  - code: "000002"
    name: "万科A"
  # 添加新股票
  - code: "600000"
    name: "浦发银行"
```

## 开发路线图

### Phase 1: 基础功能 ✅
- [x] 项目架构设计
- [x] 核心算法实现
- [x] 数据存储管理
- [x] 基础可视化

### Phase 2: 功能增强 ✅
- [x] 多数据源支持
- [x] HTML报告生成
- [x] CSV数据导出
- [x] 配置文件管理

### Phase 3: 性能优化
- [ ] 异步处理优化
- [ ] 数据库连接池
- [ ] 缓存机制优化
- [ ] 批处理优化

### Phase 4: 高级功能
- [ ] 实时监控
- [ ] Web界面
- [ ] API接口
- [ ] 回测框架
- [ ] 信号回测

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件

## 联系方式

- 项目主页: [GitHub仓库地址]
- 问题反馈: [GitHub Issues]
- 邮箱: [联系邮箱]

## 致谢

感谢以下开源项目：
- [akshare](https://github.com/akfamily/akshare) - 金融数据接口
- [pandas](https://pandas.pydata.org/) - 数据处理
- [matplotlib](https://matplotlib.org/) - 数据可视化
- [numpy](https://numpy.org/) - 科学计算

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现核心算法模块
- 支持多数据源
- 提供完整的可视化功能

---

**免责声明**：本系统仅用于学习和研究目的，不构成任何投资建议。股市有风险，投资需谨慎。

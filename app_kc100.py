"""
股票可视化Web应用 - 科创100版本
展示科创100成分股的分析结果
"""
from flask import Flask, render_template, jsonify, send_file
import yaml
import os
from pathlib import Path
from datetime import datetime
from src.visualization.dashboard import Dashboard
from src.data.storage import StorageManager
from src.utils.logger import get_logger

logger = get_logger("web_app_kc100")

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 加载科创100股票配置
with open('config/symbols_kc100.yaml', 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f)
    SYMBOLS = config_data.get('symbols', [])

# 初始化数据库
db = StorageManager()

# 初始化仪表板
dashboard = Dashboard(theme='dark')


@app.route('/')
def index():
    """主页 - 展示所有股票概览"""
    try:
        # 获取每只股票的最新分析结果
        stock_data = []
        
        for symbol_info in SYMBOLS:
            code = symbol_info['code']
            name = symbol_info['name'] or f"股票{code}"
            
            # 从数据库获取最新数据
            history = db.get_analysis_history(symbol=code)
            results = history[:1] if history else []
            
            if results:
                latest = results[0]
                stock_data.append({
                    'code': code,
                    'name': name,
                    'date': latest['date'],
                    'weighted_cost': round(latest['weighted_cost'], 2),
                    'net_flow': round(latest['net_flow'] * 100, 2),
                    'concentration_ratio': round(latest['concentration_ratio'] * 100, 2),
                    'validation_status': latest['validation_status'],
                    'has_data': True
                })
            else:
                stock_data.append({
                    'code': code,
                    'name': name,
                    'date': '暂无数据',
                    'weighted_cost': '-',
                    'net_flow': '-',
                    'concentration_ratio': '-',
                    'validation_status': '-',
                    'has_data': False
                })
        
        return render_template('index.html', stocks=stock_data, 
                             update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        return render_template('error.html', error=str(e))


@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """股票详情页"""
    try:
        # 获取股票名称
        stock_name = "未知股票"
        for s in SYMBOLS:
            if s['code'] == symbol:
                stock_name = s['name'] or f"股票{symbol}"
                break
        
        # 获取分析结果
        history = db.get_analysis_history(symbol=symbol)
        
        if not history:
            return render_template('error.html', 
                                 error=f"股票 {stock_name}({symbol}) 暂无分析数据")
        
        # 按日期排序（history已经是按日期降序排列）
        sorted_results = sorted(history, key=lambda x: x['date'])
        
        # 准备数据
        chart_data = []
        for r in sorted_results:
            chart_data.append({
                'date': r['date'],
                'weighted_cost': round(r['weighted_cost'], 2),
                'cost_ma_5': round(r['cost_ma_5'], 2) if r['cost_ma_5'] > 0 else None,
                'cost_ma_10': round(r['cost_ma_10'], 2) if r['cost_ma_10'] > 0 else None,
                'cost_ma_20': round(r['cost_ma_20'], 2) if r['cost_ma_20'] > 0 else None,
                'net_flow': round(r['net_flow'] * 100, 2),
                'concentration_ratio': round(r['concentration_ratio'] * 100, 2),
                'aggressive_buy': round(r['aggressive_buy_amount'] / 10000, 2),
                'aggressive_sell': round(r['aggressive_sell_amount'] / 10000, 2),
                'defensive_buy': round(r['defensive_buy_amount'] / 10000, 2),
                'defensive_sell': round(r['defensive_sell_amount'] / 10000, 2),
                'validation_status': r['validation_status']
            })
        
        # 最新数据
        latest = sorted_results[-1]
        
        return render_template('detail.html', 
                             symbol=symbol,
                             name=stock_name,
                             latest=latest,
                             chart_data=chart_data,
                             update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        logger.error(f"Error loading stock detail: {e}")
        return render_template('error.html', error=str(e))


@app.route('/api/stocks')
def api_stocks():
    """API: 获取所有股票概览"""
    try:
        stock_data = []
        
        for symbol_info in SYMBOLS:
            code = symbol_info['code']
            name = symbol_info['name'] or f"股票{code}"
            
            history = db.get_analysis_history(symbol=code)
            results = history[:1] if history else []
            
            if results:
                latest = results[0]
                stock_data.append({
                    'code': code,
                    'name': name,
                    'date': latest['date'],
                    'weighted_cost': round(latest['weighted_cost'], 2),
                    'net_flow': round(latest['net_flow'] * 100, 2),
                    'concentration_ratio': round(latest['concentration_ratio'] * 100, 2),
                    'validation_status': latest['validation_status']
                })
        
        return jsonify({'success': True, 'data': stock_data})
    
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stock/<symbol>/data')
def api_stock_data(symbol):
    """API: 获取指定股票的详细数据"""
    try:
        history = db.get_analysis_history(symbol=symbol)
        
        if not history:
            return jsonify({'success': False, 'error': 'No data found'})
        
        sorted_results = sorted(history, key=lambda x: x['date'])
        
        data = [{
            'date': r['date'],
            'weighted_cost': round(r['weighted_cost'], 2),
            'cost_ma_5': round(r['cost_ma_5'], 2) if r['cost_ma_5'] > 0 else None,
            'cost_ma_10': round(r['cost_ma_10'], 2) if r['cost_ma_10'] > 0 else None,
            'cost_ma_20': round(r['cost_ma_20'], 2) if r['cost_ma_20'] > 0 else None,
            'net_flow': round(r['net_flow'] * 100, 2),
            'concentration_ratio': round(r['concentration_ratio'] * 100, 2),
            'aggressive_buy': round(r['aggressive_buy_amount'] / 10000, 2),
            'aggressive_sell': round(r['aggressive_sell_amount'] / 10000, 2),
            'defensive_buy': round(r['defensive_buy_amount'] / 10000, 2),
            'defensive_sell': round(r['defensive_sell_amount'] / 10000, 2),
            'algo_buy': round(r['algo_buy_amount'] / 10000, 2),
            'algo_sell': round(r['algo_sell_amount'] / 10000, 2),
            'validation_status': r['validation_status']
        } for r in sorted_results]
        
        return jsonify({'success': True, 'data': data})
    
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    logger.info("Starting KC100 web application...")
    logger.info(f"Loaded {len(SYMBOLS)} stocks from config/symbols_kc100.yaml")
    
    # 创建模板目录
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # 创建静态文件目录
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    (static_dir / 'css').mkdir(exist_ok=True)
    (static_dir / 'js').mkdir(exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5002)

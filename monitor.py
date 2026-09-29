import os
import requests

# 1. 微信推送配置
SEND_KEY = os.environ.get("SCT_KEY", "YOUR_SEND_KEY_HERE")  # 从环境变量读取 SendKey

# 2. 监控标的预设关键位点策略
STRATEGY = {
    "sh601899": {
        "name": "紫金矿业",
        "buy_1": 29.00,      # 第一补仓买点
        "buy_2": 28.20,      # 第二强支撑买点
        "sell_1": 30.00,     # 第一做T高抛点
        "sell_2": 31.20,     # 第二压力点
    },
    "sh512880": {
        "name": "证券ETF国泰",
        "buy_1": 1.025,
        "buy_2": 1.020,
        "sell_1": 1.050,
        "sell_2": 1.070,
    },
    "sh603888": {
        "name": "新华网",
        "buy_1": 17.00,
        "buy_2": 16.80,
        "sell_1": 17.80,
        "sell_2": 19.00,
    }
}

def fetch_stock_data():
    """实时获取新浪财经股票/ETF数据"""
    symbols = ",".join(STRATEGY.keys())
    url = f"https://hq.sinajs.cn/list={symbols}"
    headers = {"Referer": "https://finance.sina.com.cn"}
    
    response = requests.get(url, headers=headers)
    response.encoding = 'gbk'
    lines = response.text.strip().split("\n")
    
    results = {}
    for line in lines:
        if '="' not in line:
            continue
        code = line.split('var hq_str_')[1].split('=')[0]
        data_str = line.split('"')[1]
        if not data_str:
            continue
        parts = data_str.split(',')
        name = parts[0]
        yesterday_close = float(parts[2])
        current_price = float(parts[3])
        high = float(parts[4])
        low = float(parts[5])
        
        # 计算涨跌幅
        change_pct = ((current_price - yesterday_close) / yesterday_close) * 100 if yesterday_close else 0
        results[code] = {
            "name": name,
            "current": current_price,
            "change_pct": change_pct,
            "high": high,
            "low": low
        }
    return results

def generate_report(data):
    """根据最新行情生成微信推送的 Markdown 简报"""
    msg = "## 📊 每日持仓自动化监控报告\n\n"
    
    for code, info in STRATEGY.items():
        if code not in data:
            continue
        stock_info = data[code]
        curr_price = stock_info["current"]
        pct = stock_info["change_pct"]
        
        msg += f"### 🔹 {stock_info['name']} ({code[2:]})\n"
        msg += f"- **最新现价**：`{curr_price:.3f}` 元 (涨跌幅: `{pct:+.2f}%`)\n"
        msg += f"- **今日最高/最低**：`{stock_info['high']:.3f}` / `{stock_info['low']:.3f}`\n"
        
        # 判断买卖建议
        actions = []
        if curr_price <= info["buy_2"]:
            actions.append(f"🚨 **极度低估/强支撑**：已触发第二买点区（<={info['buy_2']}元），建议重仓低吸补仓！")
        elif curr_price <= info["buy_1"]:
            actions.append(f"🟢 **到达买点区**：位于第一买点区间（<={info['buy_1']}元），建议分批挂单买入。")
            
        if curr_price >= info["sell_2"]:
            actions.append(f"🔥 **强压力突破**：已到达第二止盈位（>={info['sell_2']}元），建议大部队清仓/重度减仓。")
        elif curr_price >= info["sell_1"]:
            actions.append(f"🟡 **到达高抛区**：触及第一压力位（>={info['sell_1']}元），建议将前期低吸筹码做T卖出。")
            
        if not actions:
            actions.append("⚪ **观望区间**：价格处于通道中部，未触发设定的买卖条件单，保持持仓即可。")
            
        for act in actions:
            msg += f"- {act}\n"
        msg += "\n---\n"
        
    return msg

def push_to_wechat(title, content):
    """通过 Server 酱发送微信消息"""
    url = f"https://sctapi.ftqq.com/{SEND_KEY}.send"
    payload = {
        "title": title,
        "desp": content
    }
    res = requests.get(url, params=payload)
    print("推送结果:", res.json())

if __name__ == "__main__":
    stock_data = fetch_stock_data()
    report = generate_report(stock_data)
    push_to_wechat("📈 股票买卖触发条件监控提醒", report)

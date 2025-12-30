import streamlit as st
import requests
import re
import json
import time
import pandas as pd

# --- 页面配置 ---
st.set_page_config(page_title="LOF 全景看板 (防呆版)", layout="wide")
st.title("🛡️ LOF 基金溢价全景看板 (V7.0 智能补全)")

# --- 侧边栏 ---
st.sidebar.header("⚙️ 设置")
fee_rate = st.sidebar.number_input("预估交易成本 (%)", value=0.6, step=0.1)

DEFAULT_FUNDS = {
    "161226": "国投白银",
    "161815": "银华黄金",
    "160719": "嘉实黄金",
    "160216": "国泰商品",
    "162411": "华宝油气",
    "162719": "广发石油",
    "501018": "南方原油",
}

# --- 核心数据获取 ---

@st.cache_data(ttl=3600)
def get_hardcore_nav(code):
    """获取天天基金官方净值"""
    url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        response = requests.get(url, timeout=3)
        pattern = r'Data_netWorthTrend\s*=\s*(\[.*?\]);'
        match = re.search(pattern, response.text)
        if match:
            data_list = json.loads(match.group(1))
            if data_list:
                latest = data_list[-1]
                return {
                    "nav": float(latest['y']),
                    "date": time.strftime("%Y-%m-%d", time.localtime(latest['x']/1000)),
                    "success": True
                }
        return {"success": False, "nav": 0, "date": "-"}
    except:
        return {"success": False, "nav": 0, "date": "-"}

def get_realtime_price(code):
    """
    获取新浪实时价格 (增加了 0 值处理逻辑)
    """
    prefix = "sh" if code.startswith("5") else "sz"
    url = f"http://hq.sinajs.cn/list={prefix}{code}"
    try:
        res = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"}, timeout=2)
        if '="' in res.text:
            data = res.text.split('="')[1].split('";')[0].split(',')
            
            # 关键修改：提取两个价格
            current_price = float(data[3]) # 当前成交价
            pre_close = float(data[2])     # 昨日收盘价
            
            # 智能判断
            if current_price > 0:
                return {
                    "price": current_price, 
                    "status": "🟢 交易中",  # 正常交易
                    "success": True
                }
            else:
                return {
                    "price": pre_close, 
                    "status": "💤 无成交/未开盘", # 使用昨收
                    "success": True
                }
                
        return {"success": False, "price": 0, "status": "❌ 错误"}
    except:
        return {"success": False, "price": 0, "status": "❌ 网络"}

# --- 主逻辑 ---

col1, col2 = st.columns([1, 4])
with col1:
    refresh_btn = st.button('🔄 扫描全市场', type="primary")

if refresh_btn:
    st.info("正在智能清洗数据...")
    result_list = []
    
    # 进度条
    bar = st.progress(0)
    
    for i, (code, name) in enumerate(DEFAULT_FUNDS.items()):
        bar.progress((i + 1) / len(DEFAULT_FUNDS))
        
        nav_data = get_hardcore_nav(code)
        price_data = get_realtime_price(code)
        
        if nav_data["success"] and price_data["success"]:
            nav = nav_data["nav"]
            price = price_data["price"]
            
            # 计算
            if nav > 0:
                premium = (price - nav) / nav * 100
                space = premium - fee_rate
            else:
                premium = 0
                space = 0
            
            result_list.append({
                "代码": code,
                "名称": name,
                "现价": price,
                "状态": price_data["status"], # 新增状态列
                "官方净值": nav,
                "净值日期": nav_data["date"],
                "溢价率(%)": round(premium, 2),
                "套利空间(%)": round(space, 2)
            })
    
    bar.empty()
    
    if result_list:
        df = pd.DataFrame(result_list)
        df = df.sort_values(by="溢价率(%)", ascending=False)
        
        # 样式逻辑：如果是“无成交”，把那一行标灰，提醒注意
        def highlight_status(row):
            if "无成交" in row["状态"]:
                return ['color: gray'] * len(row)
            elif row["套利空间(%)"] > 0.6:
                return ['color: red; font-weight: bold'] * len(row)
            elif row["套利空间(%)"] < -0.6:
                return ['color: green; font-weight: bold'] * len(row)
            else:
                return ['color: black'] * len(row)

        st.subheader("📊 实时监控看板")
        
        # 应用样式
        st.dataframe(
            df.style.apply(highlight_status, axis=1)
              .format({"现价": "{:.3f}", "官方净值": "{:.4f}"}),
            use_container_width=True,
            height=400,
            hide_index=True
        )
        
        st.caption("注：若状态显示为 '💤 无成交/未开盘'，则'现价'使用的是昨日收盘价，仅供参考。")
        
    else:
        st.error("无数据。")

else:
    st.write("👈 点击左上角按钮开始")

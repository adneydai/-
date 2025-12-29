import streamlit as st
import requests
import re
import json
import time

# --- 页面配置 ---
st.set_page_config(page_title="LOF 溢价监控 (终极版)", layout="centered")
st.title("🦅 LOF 溢价监控 (终极数据版)")

# --- 侧边栏 ---
st.sidebar.header("参数设置")
fund_code = st.sidebar.text_input("基金代码", value="161226")
fee_rate = st.sidebar.number_input("交易成本估算 (%)", value=0.6, step=0.1)

if st.sidebar.button("清除缓存并刷新"):
    st.cache_data.clear()

# --- 核心函数1：获取最精准的官方净值 ---
# 使用 @st.cache_data 防止频繁请求，设置 ttl=3600 (1小时过期)
@st.cache_data(ttl=3600)
def get_hardcore_nav(code):
    """
    直接读取天天基金的'品种数据'接口 (PingZhongData)
    这是网页版走势图的原始数据，绝对准确。
    """
    # 这个接口返回的是一个巨大的 JS 文件，包含该基金成立以来的所有净值
    url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        response = requests.get(url, timeout=5)
        text = response.text
        
        # 提取 Data_netWorthTrend = [...] 部分
        # 格式: var Data_netWorthTrend = [{"x":164000000,"y":1.234}, ...];
        pattern = r'Data_netWorthTrend\s*=\s*(\[.*?\]);'
        match = re.search(pattern, text)
        
        if match:
            # 解析 JSON 列表
            data_list = json.loads(match.group(1))
            
            if data_list:
                # 获取列表里最后一个元素（也就是最新一天的净值）
                latest_data = data_list[-1]
                return {
                    "nav": float(latest_data['y']), # y 是单位净值
                    "date": time.strftime("%Y-%m-%d", time.localtime(latest_data['x']/1000)), # x 是时间戳
                    "success": True
                }
        return {"success": False, "msg": "未找到净值数据"}
    except Exception as e:
        return {"success": False, "msg": str(e)}

# --- 核心函数2：获取新浪实时价格 ---
def get_realtime_price(code):
    prefix = "sh" if code.startswith("5") else "sz"
    url = f"http://hq.sinajs.cn/list={prefix}{code}"
    try:
        response = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"})
        if '="' in response.text:
            data = response.text.split('="')[1].split('";')[0].split(',')
            return {
                "name": data[0],
                "price": float(data[3]), 
                "success": True
            }
        return {"success": False}
    except:
        return {"success": False}

# --- 主逻辑 ---
if st.button('🚀 强制获取最新数据', type="primary"):
    
    # 1. 获取净值 (终极接口)
    nav_data = get_hardcore_nav(fund_code)
    
    # 2. 获取现价
    price_data = get_realtime_price(fund_code)
    
    if nav_data["success"] and price_data["success"]:
        nav = nav_data["nav"]
        nav_date = nav_data["date"]
        price = price_data["price"]
        name = price_data["name"]
        
        premium_rate = (price - nav) / nav * 100
        
        # --- 展示 ---
        st.success(f"数据已同步 (来源: 天天基金走势图数据)")
        
        st.subheader(f"{name} ({fund_code})")
        
        c1, c2 = st.columns(2)
        c1.metric("当前二级市场价格", f"{price:.3f}")
        c2.metric("最新单位净值", f"{nav:.4f}", help=f"净值日期: {nav_date}")
        
        st.info(f"📅 净值日期: **{nav_date}** (请确认这是否为最近一个交易日)")
        
        st.markdown("---")
        st.metric("📊 静态溢价率", f"{premium_rate:.2f}%", delta=f"{premium_rate-fee_rate:.2f}% (扣费空间)")
        
        # 调试信息 (让你确信数据是对的)
        with st.expander("查看原始数据 (Debug)"):
            st.write(f"API返回的最新数据包: {nav_data}")
            
    else:
        st.error("获取失败，可能代码填错了。")

else:
    st.write("👈 点击上方按钮获取数据")

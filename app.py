import streamlit as st
import requests
import re
import time

# --- 页面配置 ---
st.set_page_config(page_title="LOF 溢价监控 (自动版)", layout="centered")
st.title("🤖 LOF 溢价监控 (全自动版)")

# --- 侧边栏：只需填代码 ---
st.sidebar.header("参数设置")
fund_code = st.sidebar.text_input("基金代码 (LOF)", value="161226", help="只需填数字，如 161226")
fee_rate = st.sidebar.number_input("交易成本估算 (%)", value=0.6, step=0.1)

# --- 核心函数1：获取天天基金官方净值 ---
def get_official_nav(code):
    """
    从天天基金接口获取昨日官方净值
    """
    # 这是一个轻量级接口，返回 JSONP 格式
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
    try:
        response = requests.get(url, timeout=3)
        text = response.text
        # 返回格式通常是: jsonpgz({"fundcode":"161226","dwjz":"2.0483","jzrq":"2025-12-26",...});
        
        # 使用正则提取 dwjz (单位净值) 和 jzrq (净值日期)
        nav_match = re.search(r'"dwjz":"([^"]+)"', text)
        date_match = re.search(r'"jzrq":"([^"]+)"', text)
        
        if nav_match and date_match:
            return {
                "nav": float(nav_match.group(1)),
                "date": date_match.group(1),
                "success": True
            }
        return {"success": False, "msg": "正则解析失败"}
        
    except Exception as e:
        return {"success": False, "msg": str(e)}

# --- 核心函数2：获取新浪实时价格 ---
def get_realtime_price(code):
    # 新浪接口需要加前缀，深市加 sz，沪市加 sh
    prefix = "sh" if code.startswith("5") else "sz"
    full_code = f"{prefix}{code}"
    
    url = f"http://hq.sinajs.cn/list={full_code}"
    try:
        response = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"})
        if '="' in response.text:
            data = response.text.split('="')[1].split('";')[0].split(',')
            return {
                "name": data[0],
                "price": float(data[3]), # 当前价格
                "success": True
            }
        return {"success": False}
    except:
        return {"success": False}

# --- 主逻辑 ---
if st.button('🚀 自动获取并计算', type="primary"):
    
    with st.spinner('正在从天天基金和新浪财经同步数据...'):
        # 1. 获取官方净值 (天天基金)
        nav_data = get_official_nav(fund_code)
        
        # 2. 获取实时现价 (新浪)
        price_data = get_realtime_price(fund_code)
        
        if nav_data["success"] and price_data["success"]:
            
            # 提取数据
            nav = nav_data["nav"]
            nav_date = nav_data["date"]
            name = price_data["name"]
            price = price_data["price"]
            
            # 3. 计算溢价率
            premium_rate = (price - nav) / nav * 100
            arbitrage_space = premium_rate - fee_rate
            
            # --- 界面展示 ---
            st.success(f"数据同步成功！(数据源：天天基金 + 新浪财经)")
            
            st.subheader(f"📈 {name} ({fund_code})")
            
            # 关键数据卡片
            c1, c2 = st.columns(2)
            c1.metric("当前二级市场价格", f"{price:.3f}")
            c2.metric("官方单位净值", f"{nav:.4f}", help=f"净值日期: {nav_date}")
            
            # 醒目日期提醒
            st.caption(f"📅 注意：当前使用的净值日期为 **{nav_date}**，请确认这是最新的。")
            
            st.markdown("---")
            
            # 结果显示
            if premium_rate > 0:
                st.metric("📊 静态溢价率", f"{premium_rate:.2f}%", delta=f"{arbitrage_space:.2f}% (扣费空间)")
            else:
                st.metric("📊 静态溢价率", f"{premium_rate:.2f}%", delta=f"{premium_rate:.2f}%", delta_color="inverse")
            
            # 结论
            if arbitrage_space > 1.5:
                st.error(f"🔥 **机会！** 溢价率较高，如果持有底仓可考虑卖出。")
            elif premium_rate < -2.0:
                st.success(f"💰 **机会！** 折价率较高，可考虑场内买入。")
            else:
                st.info("☁️ 价格波动在正常范围内。")

        else:
            st.error("获取数据失败，请检查网络或基金代码。")
            if not nav_data["success"]:
                st.write(f"天天基金接口报错: {nav_data.get('msg')}")

import streamlit as st
import requests

# --- 页面配置 ---
st.set_page_config(page_title="LOF 静态溢价计算器", layout="centered")
st.title("⚡️ LOF 静态溢价计算器")

# --- 侧边栏：极简参数 ---
st.sidebar.header("参数设置")
fund_code = st.sidebar.text_input("基金代码 (新浪格式)", value="sz161226", help="例如 sz161226")
last_nav = st.sidebar.number_input("昨日官方单位净值 (必填)", value=0.966, format="%.4f")
fee_rate = st.sidebar.number_input("交易成本估算 (%)", value=0.6, step=0.1)

# --- 核心逻辑 ---
if st.button('🚀 查询', type="primary"):
    
    # 1. 仅获取基金数据，不再请求期货数据
    url = f"http://hq.sinajs.cn/list={fund_code}"
    try:
        response = requests.get(url, headers={"Referer": "http://finance.sina.com.cn"})
        data_text = response.text
        
        if '="' in data_text:
            data = data_text.split('="')[1].split('";')[0].split(',')
            
            # 解析数据
            name = data[0]
            current_price = float(data[3]) # 当前价格
            
            # 2. 极简公式计算
            # 溢价率 = (现价 - 昨日净值) / 昨日净值
            premium_rate = (current_price - last_nav) / last_nav * 100
            
            # 套利空间
            arbitrage_space = premium_rate - fee_rate

            # --- 结果展示 ---
            st.subheader(f"当前标的: {name}")
            
            # 核心大指标
            c1, c2 = st.columns(2)
            c1.metric("当前二级市场价格", f"{current_price:.3f}")
            c2.metric("昨日官方净值", f"{last_nav:.4f}")

            st.markdown("---")
            
            # 溢价率展示
            if premium_rate > 0:
                st.metric("📊 静态溢价率", f"{premium_rate:.2f}%", delta=f"{arbitrage_space:.2f}% (扣费空间)")
            else:
                st.metric("📊 静态溢价率", f"{premium_rate:.2f}%", delta=f"{premium_rate:.2f}%", delta_color="inverse")

            # --- 简单的文字结论 ---
            if arbitrage_space > 1.0:
                st.warning(f"🔥 **溢价明显！** 当前价格比昨天净值贵了 {premium_rate:.2f}%。")
            elif premium_rate < -1.5:
                st.success(f"💰 **折价明显！** 当前价格比昨天净值便宜了 {abs(premium_rate):.2f}%。")
            else:
                st.info("☁️ 价格相对平稳。")
                
        else:
            st.error("无法解析数据，请检查代码是否正确。")
            
    except Exception as e:
        st.error(f"网络请求出错: {e}")

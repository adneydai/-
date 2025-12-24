import streamlit as st
import requests
import time

# --- 页面配置 ---
st.set_page_config(page_title="LOF 溢价监控工具", layout="centered")
st.title("📈 LOF 基金实时溢价监控")

# --- 侧边栏：参数设置 ---
st.sidebar.header("参数设置")

# 默认参数：以白银LOF为例
fund_code = st.sidebar.text_input("LOF基金代码 (新浪接口格式)", value="sz161226")
future_code = st.sidebar.text_input("标的期货代码 (新浪接口格式)", value="nf_AG0")

# 核心参数：需要手动更新，因为官方净值每天才出一次
# 你可以在天天基金网查到昨日的单位净值
last_nav = st.sidebar.number_input("昨日官方单位净值 (NAV)", value=0.966, format="%.4f") # 示例值，请根据实际修改
position_ratio = st.sidebar.slider("基金持仓仓位估算 (%)", 80, 100, 92) / 100.0

# 手续费设置 (用于计算套利盈亏平衡点)
fee_rate = st.sidebar.number_input("预估交易总成本 (%)", value=0.6, step=0.1)

# --- 核心函数：获取数据 ---
def get_sina_data(code):
    """从新浪财经获取实时数据"""
    try:
        url = f"http://hq.sinajs.cn/list={code}"
        headers = {"Referer": "http://finance.sina.com.cn"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            text = response.text
            # 数据格式通常是: var hq_str_sz161226="名字,开盘,昨收,当前,..."
            content = text.split('="')[1].split('";')[0]
            return content.split(',')
        return None
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None

# --- 主逻辑区 ---

if st.button('🔄 点击刷新数据', type="primary"):
    
    # 1. 获取基金数据 (LOF)
    fund_data = get_sina_data(fund_code)
    # 2. 获取期货数据 (标的)
    future_data = get_sina_data(future_code)

    if fund_data and future_data:
        # --- 数据解析 (注意：新浪股票和期货的字段顺序不同) ---
        
        # 解析 LOF 基金 (股票接口格式)
        # 索引3是当前价格，索引1是开盘，索引2是昨收(不准，主要看净值)
        fund_name = fund_data[0]
        fund_current_price = float(fund_data[3])
        
        # 解析 期货 (期货接口格式)
        # 索引0是名字，索引8是最新价，索引11是昨结算(用于计算涨跌幅)
        future_name = future_data[0]
        future_current_price = float(future_data[8])
        future_last_settle = float(future_data[11])

        # --- 计算核心指标 ---
        
        # 1. 标的涨跌幅
        if future_last_settle > 0:
            future_change_pct = (future_current_price - future_last_settle) / future_last_settle
        else:
            future_change_pct = 0

        # 2. 实时估算净值 (IOPV)
        # 公式：昨日净值 * (1 + 标的涨跌幅 * 仓位)
        estimated_nav = last_nav * (1 + future_change_pct * position_ratio)
        
        # 3. 溢价率
        # 公式：(现价 - 估算净值) / 估算净值
        premium_rate = (fund_current_price - estimated_nav) / estimated_nav * 100

        # --- 界面展示 ---
        
        # 分割成三列展示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label=f"{fund_name} 现价", value=f"{fund_current_price:.3f}")
            
        with col2:
            st.metric(label="实时估算净值 (IOPV)", value=f"{estimated_nav:.4f}", 
                      delta=f"{future_change_pct*100:.2f}% (标的涨跌)")
            
        with col3:
            # 颜色逻辑：溢价为正显示红色(通常逻辑)，溢价为负显示绿色
            st.metric(label="当前溢价率", value=f"{premium_rate:.2f}%", 
                      delta=f"{premium_rate - fee_rate:.2f}% (扣费后空间)")

        st.markdown("---")
        
        # --- 决策辅助 ---
        st.subheader("🤖 套利信号参考")
        
        arbitrage_space = premium_rate - fee_rate # 扣除手续费后的空间
        
        if arbitrage_space > 0.5:
            st.warning(f"🔥 **存在溢价套利机会！**\n\n当前溢价 **{premium_rate:.2f}%**，扣除成本后仍有 **{arbitrage_space:.2f}%** 空间。\n\n**操作建议：** 场内卖出，场外申购（或拖拉机账户申购）。")
        elif premium_rate < -2.0:
            st.success(f"💰 **存在折价套利机会！**\n\n当前折价 **{premium_rate:.2f}%**。\n\n**操作建议：** 场内买入。")
        else:
            st.info("😴 当前无明显套利空间，建议观望。")

        # --- 详细数据表格 ---
        with st.expander("查看详细数据"):
            st.write({
                "标的物": future_name,
                "标的现价": future_current_price,
                "标的昨结算": future_last_settle,
                "标的涨跌幅": f"{future_change_pct*100:.2f}%",
                "计算用仓位": f"{position_ratio*100}%"
            })
            
    else:
        st.error("数据获取失败，请检查代码或网络。")

else:
    st.info("👈 请调整左侧参数，并点击上方按钮获取最新数据。")

# 底部说明
st.markdown("---")
st.caption("注：本工具仅供学习参考。估算净值基于期货主力合约推算，未包含盘中汇率变动（若为QDII）及基金现金部分收益，可能存在误差。")

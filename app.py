import streamlit as st
import pandas as pd
import random
from collections import Counter
import os

# ==========================================
# 🛡️ 核心防盗门逻辑 (放在最前面)
# ==========================================
st.set_page_config(page_title="冰火防线 - 内部模拟器", layout="wide")

def check_password():
    """只有返回 True 时，后面的业务代码才会执行"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🛡️ 《冰火防线》数值管理系统")
    st.info("该系统仅供内部团队使用，请输入访问口令。")
    
    # 这里的 '123456' 你可以改成任何你想要的密码
    pwd = st.text_input("访问口令", type="password")
    if st.button("验证并进入"):
        if pwd == "123456": 
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 口令错误，请联系开发者获取。")
    return False

# 如果密码验证没通过，直接切断后续所有代码的运行
if not check_password():
    st.stop()

# ==========================================
# 2. 以下是原来的业务逻辑 (只有验证通过才会运行)
# ==========================================
st.success("✅ 身份验证通过，正在加载最新数值配置...")

@st.cache_data
def load_game_data():
    try:
        # 直接读取原生的 xlsx 文件
        df_stage = pd.read_excel("StageBattle.xlsx").fillna("0")
        df_monster = pd.read_excel("Monster.xlsx").fillna(0)
        df_skill = pd.read_excel("Skill.xlsx").fillna(0)
        
        for col in df_stage.columns:
            clean_col = str(col).strip().lower()
            if clean_col == 'monsterwave' or '波次血量加成' in clean_col:
                df_stage[col] = df_stage[col].astype(str)
        return df_stage, df_monster, df_skill, True
    except Exception as e:
        st.error(f"❌ 读取数据失败: {e}")
        return None, None, None, False

df_stage, df_monster, df_skill, data_loaded = load_game_data()

# --- 这里保留你之前完整的 get_wave_hp, get_skill_multiplier 等逻辑 ---
# --- 为节省篇幅，此处省略，请确保把你之前的核心逻辑粘贴在这里 ---

# ==========================================
# 3. 界面渲染 (保持不变)
# ==========================================
# ... 把你之前的 sidebar 配置和图表渲染代码全部接在后面 ...
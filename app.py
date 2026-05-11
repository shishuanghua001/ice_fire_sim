import streamlit as st
import pandas as pd
import random
from collections import Counter
import os

# ==========================================
# 🛡️ 1. 访问控制逻辑 (防盗门)
# ==========================================
st.set_page_config(page_title="冰火防线 - 内部数值模拟器", layout="wide")

def check_password():
    """验证通过返回 True，否则返回 False"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🛡️ 《冰火防线》数值管理系统")
    st.info("该系统仅供内部团队使用，请输入访问口令。")
    
    # 你可以把 '666888' 改成你喜欢的任何密码
    pwd = st.text_input("访问口令", type="password")
    if st.button("验证并进入"):
        if pwd == "666888": 
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 口令错误，请联系开发者获取。")
    return False

# 如果密码验证没通过，停止执行后续代码
if not check_password():
    st.stop()

# ==========================================
# 2. 读取本地 Excel 配置表数据 (验证通过后执行)
# ==========================================
@st.cache_data
def load_game_data():
    try:
        # 直接读取原生的 xlsx 文件
        df_stage = pd.read_excel("StageBattle.xlsx").fillna("0")
        df_monster = pd.read_excel("Monster.xlsx").fillna(0)
        df_skill = pd.read_excel("Skill.xlsx").fillna(0)
        
        # 预处理：将关键列转为字符串，防止拆分报错
        for col in df_stage.columns:
            clean_col = str(col).strip().lower()
            if clean_col == 'monsterwave' or '波次血量加成' in clean_col:
                df_stage[col] = df_stage[col].astype(str)
                
        return df_stage, df_monster, df_skill, True
    except Exception as e:
        st.error(f"❌ 读取数据失败: {e}。请检查 GitHub 仓库中是否存在 StageBattle.xlsx, Monster.xlsx, Skill.xlsx")
        return None, None, None, False

df_stage, df_monster, df_skill, data_loaded = load_game_data()

# ==========================================
# 3. 核心解析函数 (带全方位智能列名雷达)
# ==========================================
def get_wave_hp(stage_id, wave_index):
    """根据主线关卡id和波次计算真实血量"""
    if not data_loaded: return 2000
    
    # 智能查找列名
    stage_id_col = next((c for c in df_stage.columns if str(c).strip().lower() in ['关卡id', 'id', 'stageid', '关卡编号']), None)
    add_hp_col = next((c for c in df_stage.columns if str(c).strip().lower() in ['addhp', '血量加成']), None)
    wave_buff_col = next((c for c in df_stage.columns if str(c).strip() == '波次血量加成'), None)
    monster_wave_col = next((c for c in df_stage.columns if str(c).strip().lower() == 'monsterwave'), None)
    
    monster_id_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['id', '怪物id', 'monsterid']), None)
    monster_hp_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['hp', '血量', '基础血量']), None)
    
    if any(x is None for x in [stage_id_col, monster_wave_col, monster_id_col]):
        return 2000

    stage_rows = df_stage[df_stage[stage_id_col].astype(str) == str(stage_id)]
    if stage_rows.empty: return 2000 
        
    stage_data = stage_rows.iloc[0]
    add_hp_pct = float(stage_data.get(add_hp_col, 0)) if add_hp_col else 0.0
    wave_buff_str = str(stage_data.get(wave_buff_col, '0')) if wave_buff_col else '0'
    wave_buffs = [float(x) for x in wave_buff_str.split(',') if x.strip()]
    current_wave_buff_pct = wave_buffs[wave_index] if wave_index < len(wave_buffs) else 0
    
    waves_str = str(stage_data.get(monster_wave_col, ''))
    waves_array = waves_str.split(';')
    if wave_index >= len(waves_array): return 2000 
        
    current_wave_data = waves_array[wave_index]
    parts = current_wave_data.split(',')
    if len(parts) < 2: return 2000
        
    monster_ids = parts[0].split('+')
    monster_counts = parts[1].split('+')
    
    total_base_hp = 0
    for idx, m_id_str in enumerate(monster_ids):
        try:
            m_id = int(m_id_str)
            m_count = int(monster_counts[idx]) if idx < len(monster_counts) else 0
        except: continue
            
        monster_row = df_monster[df_monster[monster_id_col].astype(str) == str(m_id)]
        base_hp = float(monster_row.iloc[0].get(monster_hp_col, 100)) if not monster_row.empty else 100.0
        total_base_hp += base_hp * m_count
        
    return total_base_hp * (1 + add_hp_pct / 100.0) * (1 + current_wave_buff_pct / 100.0)

def get_skill_multiplier(skill_avg_lvl):
    """获取技能倍率"""
    if not data_loaded: return 0.8
    id_col = next((col for col in df_skill.columns if str(col).strip().lower() in ['id', '技能id', 'skillid']), None)
    dmg_col = next((col for col in df_skill.columns if str(col).strip().lower() in ['damagemultiplier', '伤害倍率']), None)
    
    if id_col is None or dmg_col is None: return 0.8
    filtered_skills = df_skill[df_skill[id_col].astype(str).str.endswith(str(skill_avg_lvl))]
    if not filtered_skills.empty:
        return float(pd.to_numeric(filtered_skills[dmg_col], errors='coerce').mean())
    return 0.8

# ==========================================
# 4. 界面渲染与操作面板
# ==========================================
st.title("🛡️ 《冰火防线》 - 真实查表级数值模拟器")
st.sidebar.header("⚙️ 操作面板")

if data_loaded:
    s_stage_id = st.sidebar.number_input("主线关卡 ID", min_value=1, value=1)
    s_atk = st.sidebar.number_input("主角攻击力", min_value=1, value=50)
    s_crit_rate = st.sidebar.number_input("主角暴击率 (%)", 0.0, 100.0, 10.0)
    s_crit_dmg = st.sidebar.number_input("主角暴击伤害 (%)", 100.0, 500.0, 150.0)
    s_dmg_bonus = st.sidebar.number_input("主角伤害加成 (%)", 0.0, 500.0, 0.0)
    s_skill_avg_lvl = st.sidebar.number_input("主角技能平均等级", 1, 10, 1)
    s_aoe_factor = st.sidebar.number_input("割草群伤综合倍率", 1.0, 20.0, 5.0)
    s_luck_factor = st.sidebar.number_input("局内发牌运气", 0.1, 2.0, 1.0)

    # 运行模拟逻辑
    def run_simulation():
        results = []
        crit_multiplier = (1 - s_crit_rate/100.0) + (s_crit_rate/100.0) * (s_crit_dmg/100.0)
        out_dmg_multiplier = 1.0
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
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("🛡️ 《冰火防线》数值管理系统")
    pwd = st.text_input("访问口令", type="password")
    if st.button("验证并进入"):
        if pwd == "666888": 
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 口令错误")
    return False

if not check_password():
    st.stop()

# ==========================================
# 2. 读取数据 (带缓存)
# ==========================================
@st.cache_data
def load_game_data():
    try:
        df_stage = pd.read_excel("StageBattle.xlsx").fillna("0")
        df_monster = pd.read_excel("Monster.xlsx").fillna(0)
        df_skill = pd.read_excel("Skill.xlsx").fillna(0)
        for col in df_stage.columns:
            if str(col).strip().lower() == 'monsterwave' or '波次血量加成' in str(col):
                df_stage[col] = df_stage[col].astype(str)
        return df_stage, df_monster, df_skill, True
    except:
        return None, None, None, False

df_stage, df_monster, df_skill, data_loaded = load_game_data()

# ==========================================
# 3. 核心算法 (解析血量和技能)
# ==========================================
def get_wave_hp(stage_id, wave_index):
    if not data_loaded: return 2000
    s_id_col = next((c for c in df_stage.columns if str(c).strip().lower() in ['关卡id', 'id', 'stageid']), '关卡id')
    m_w_col = next((c for c in df_stage.columns if str(c).strip().lower() == 'monsterwave'), 'monsterWave')
    row = df_stage[df_stage[s_id_col].astype(str) == str(stage_id)]
    if row.empty: return 2000
    stage_data = row.iloc[0]
    
    # 怪物血量解析
    waves_str = str(stage_data.get(m_w_col, ''))
    waves_array = waves_str.split(';')
    if wave_index >= len(waves_array): return 2000
    try:
        parts = waves_array[wave_index].split(',')
        m_ids = parts[0].split('+')
        m_counts = parts[1].split('+')
        total_hp = 0
        m_id_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['id', '怪物id']), 'Id')
        m_hp_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['hp', '血量']), 'hp')
        for idx, mid in enumerate(m_ids):
            m_row = df_monster[df_monster[m_id_col].astype(str) == str(mid)]
            base_hp = float(m_row.iloc[0].get(m_hp_col, 100)) if not m_row.empty else 100
            total_hp += base_hp * int(m_counts[idx])
        
        # 乘法加算公式
        add_hp = float(stage_data.get('addHP', 0))
        w_buff_str = str(stage_data.get('波次血量加成', '0'))
        w_buffs = [float(x) for x in w_buff_str.split(',') if x.strip()]
        w_buff = w_buffs[wave_index] if wave_index < len(w_buffs) else 0
        return total_hp * (1 + add_hp/100) * (1 + w_buff/100)
    except: return 2000

def get_skill_multiplier(lvl):
    if not data_loaded: return 0.8
    dmg_col = next((c for c in df_skill.columns if str(c).strip().lower() == 'damagemultiplier'), 'damageMultiplier')
    id_col = next((c for c in df_skill.columns if str(c).strip().lower() == 'id'), 'Id')
    f_s = df_skill[df_skill[id_col].astype(str).str.endswith(str(lvl))]
    return float(pd.to_numeric(f_s[dmg_col], errors='coerce').mean()) if not f_s.empty else 0.8

# ==========================================
# 4. 界面与实时演算
# ==========================================
st.title("🛡️ 《冰火防线》 - 真实查表级数值模拟器")

if data_loaded:
    with st.sidebar:
        st.header("⚙️ 数值调优面板")
        s_stage_id = st.number_input("主线关卡 ID", 1, 200, 1)
        s_atk = st.number_input("主角攻击力", 1, 10000, 50)
        s_crit_rate = st.number_input("主角暴击率 (%)", 0.0, 100.0, 10.0)
        s_crit_dmg = st.number_input("主角暴击伤害 (%)", 100.0, 500.0, 150.0)
        s_dmg_bonus = st.number_input("主角伤害加成 (%)", 0.0, 500.0, 0.0)
        s_skill_avg_lvl = st.number_input("主角技能平均等级", 1, 10, 1)
        s_aoe_factor = st.number_input("割草群伤综合倍率", 1.0, 30.0, 5.0)
        s_luck_factor = st.number_input("局内发牌运气", 0.1, 2.0, 1.0)
        st.divider()
        st.caption("提示：修改上方数值右侧图表会自动刷新")

    # 执行模拟
    results = []
    crit_multi = (1 - s_crit_rate/100) + (s_crit_rate/100) * (s_crit_dmg/100)
    out_dmg_multi = 1 + (s_dmg_bonus/100)
    skill_multi = get_skill_multiplier(s_skill_avg_lvl)
    wave_hps = [get_wave_hp(s_stage_id, w) for w in range(20)]

    for _ in range(1000):
        dead_w = -1
        for w in range(1, 21):
            hp = wave_hps[w-1]
            growth = 1 + (w * 0.3 * s_luck_factor)
            # 文档公式：攻击力 * 技能倍率 * 局内成长 * 局外加成 * 暴击期望 * AOE抽象系数 * 输出时长 * 随机波动
            dmg = (s_atk * skill_multi) * growth * out_dmg_multi * crit_multi * s_aoe_factor * 15 * random.uniform(0.8, 1.2)
            if dmg < hp:
                dead_w = w
                break
        results.append("通关" if dead_w == -1 else dead_w)

    counts = Counter(results)
    passed = counts.get("通关", 0)

    # 渲染结果
    m1, m2, m3 = st.columns(3)
    m1.metric("总模拟人次", "1000")
    m2.metric("预期通关率", f"{(passed/10):.1f}%")
    m3.metric("最易卡点", f"第 {Counter([r for r in results if r != '通关']).most_common(1)[0][0] if passed < 1000 else '无'} 波")

    st.divider()
    chart_df = pd.DataFrame({
        "波次": [f"波次{i:02d}" for i in range(1, 21)] + ["通关"],
        "存活人数": [1000 - sum([counts.get(j, 0) for j in range(1, i+1)]) for i in range(1, 21)] + [passed]
    }).set_index("波次")
    
    st.subheader("📊 关卡存活压力曲线")
    st.line_chart(chart_df, color="#4b8bff")
    
    st.subheader("💀 死亡节点分布柱状图")
    st.bar_chart(pd.DataFrame({
        "波次": [f"波次{i:02d}" for i in range(1, 21)] + ["通关"],
        "人数": [counts.get(i, 0) for i in range(1, 21)] + [passed]
    }).set_index("波次"), color="#ff4b4b")

    with st.expander("🛠️ 原始数据校验"):
        st.write({f"第{i+1}波血量": f"{get_wave_hp(s_stage_id, i):.0f}" for i in range(20)})
else:
    st.error("无法加载 Excel 数据，请检查文件名称。")
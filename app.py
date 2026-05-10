import streamlit as st
import pandas as pd
import random
from collections import Counter
import os

# ==========================================
# 0. 页面配置与路径查错探照灯
# ==========================================
st.set_page_config(page_title="冰火防线 - 查表级模拟器", layout="wide")
st.title("🛡️ 《冰火防线》 - 真实查表级数值模拟器")

with st.expander("🚨 路径查错探照灯 (点开这里看当前文件列表)"):
    st.write(f"**当前工作目录：** `{os.getcwd()}`")
    st.code("\n".join(os.listdir('.')), language="text")

# ==========================================
# 1. 读取本地 Excel 配置表数据
# ==========================================
@st.cache_data
def load_game_data():
    try:
        df_stage = pd.read_excel("StageBattle.xlsx").fillna("0")
        df_monster = pd.read_excel("Monster.xlsx").fillna(0)
        df_skill = pd.read_excel("Skill.xlsx").fillna(0)
        
        # 提前把容易变成数字的列转成字符串，防止后续 split 报错
        for col in df_stage.columns:
            clean_col = str(col).strip().lower()
            if clean_col == 'monsterwave' or '波次血量加成' in clean_col:
                df_stage[col] = df_stage[col].astype(str)
                
        return df_stage, df_monster, df_skill, True
        
    except FileNotFoundError:
        return None, None, None, False
    except Exception as e:
        st.error(f"❌ 读取 Excel 失败: {e}")
        return None, None, None, False

df_stage, df_monster, df_skill, data_loaded = load_game_data()

# ==========================================
# 2. 核心解析函数 (带全方位智能列名雷达)
# ==========================================
def get_wave_hp(stage_id, wave_index):
    """根据主线关卡id和波次计算真实血量"""
    if not data_loaded: return 2000
    
    # 智能查找关卡表的列名
    stage_id_col = next((c for c in df_stage.columns if str(c).strip().lower() in ['关卡id', 'id', 'stageid', '关卡编号']), None)
    add_hp_col = next((c for c in df_stage.columns if str(c).strip().lower() in ['addhp', '血量加成']), None)
    wave_buff_col = next((c for c in df_stage.columns if str(c).strip() == '波次血量加成'), None)
    monster_wave_col = next((c for c in df_stage.columns if str(c).strip().lower() == 'monsterwave'), None)
    
    # 智能查找怪物表的列名
    monster_id_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['id', '怪物id', 'monsterid']), None)
    monster_hp_col = next((c for c in df_monster.columns if str(c).strip().lower() in ['hp', '血量', '基础血量']), None)
    
    # 如果找不到列，直接在网页上爆出真凶表头
    if stage_id_col is None:
        st.error(f"❌ 在 StageBattle.xlsx 中找不到 '关卡id' 列！实际读到的第一行表头是：{list(df_stage.columns)}")
        return 2000
    if monster_wave_col is None:
        st.error(f"❌ 在 StageBattle.xlsx 中找不到 'monsterWave' 列！实际表头是：{list(df_stage.columns)}")
        return 2000
    if monster_id_col is None:
        st.error(f"❌ 在 Monster.xlsx 中找不到 'Id' 列！实际表头是：{list(df_monster.columns)}")
        return 2000

    stage_rows = df_stage[df_stage[stage_id_col].astype(str) == str(stage_id)]
    if stage_rows.empty:
        return 2000 
        
    stage_data = stage_rows.iloc[0]
    
    add_hp_pct = float(stage_data.get(add_hp_col, 0)) if add_hp_col else 0.0
    wave_buff_str = str(stage_data.get(wave_buff_col, '0')) if wave_buff_col else '0'
    
    wave_buffs = [float(x) for x in wave_buff_str.split(',') if x.strip()]
    current_wave_buff_pct = wave_buffs[wave_index] if wave_index < len(wave_buffs) else 0
    
    waves_str = str(stage_data.get(monster_wave_col, ''))
    waves_array = waves_str.split(';')
    
    if wave_index >= len(waves_array):
        return 2000 
        
    current_wave_data = waves_array[wave_index]
    parts = current_wave_data.split(',')
    
    if len(parts) < 2:
        return 2000
        
    monster_ids = parts[0].split('+')
    monster_counts = parts[1].split('+')
    
    total_base_hp = 0
    for idx, m_id_str in enumerate(monster_ids):
        try:
            m_id = int(m_id_str)
            m_count = int(monster_counts[idx]) if idx < len(monster_counts) else 0
        except ValueError:
            continue
            
        monster_row = df_monster[df_monster[monster_id_col].astype(str) == str(m_id)]
        if not monster_row.empty:
            base_hp = float(monster_row.iloc[0].get(monster_hp_col, 100)) if monster_hp_col else 100.0
        else:
            base_hp = 100.0 
            
        total_base_hp += base_hp * m_count
        
    final_wave_hp = total_base_hp * (1 + add_hp_pct / 100.0) * (1 + current_wave_buff_pct / 100.0)
    return final_wave_hp

def get_skill_multiplier(skill_avg_lvl):
    """根据平均等级获取技能倍率"""
    if not data_loaded: return 0.8
    
    id_col = next((col for col in df_skill.columns if str(col).strip().lower() in ['id', '技能id', 'skillid']), None)
    dmg_col = next((col for col in df_skill.columns if str(col).strip().lower() in ['damagemultiplier', '伤害倍率']), None)
    
    if id_col is None:
        st.error(f"❌ 在 Skill.xlsx 中找不到类似 'Id' 的列！实际表头是：{list(df_skill.columns)}")
        return 0.8
    if dmg_col is None:
        st.error(f"❌ 在 Skill.xlsx 中找不到类似 'damageMultiplier' 的列！实际表头是：{list(df_skill.columns)}")
        return 0.8

    filtered_skills = df_skill[df_skill[id_col].astype(str).str.endswith(str(skill_avg_lvl))]
    if not filtered_skills.empty:
        return float(pd.to_numeric(filtered_skills[dmg_col], errors='coerce').mean())
    return 0.8

# ==========================================
# 3. 界面输入面板
# ==========================================
st.sidebar.header("⚙️ 操作面板")
run_btn = st.sidebar.button("🚀 运行 1000 次查表模拟", type="primary", use_container_width=True)

if not data_loaded:
    st.sidebar.error("⚠️ 未检测到 Excel 配置表，请确保 StageBattle.xlsx 等文件在同级目录。")
else:
    st.sidebar.success("✅ 成功读取到所有 Excel 表格数据！")

st.sidebar.divider()

st.sidebar.subheader("👑 局外养成练度输入")
s_stage_id = st.sidebar.number_input("主线关卡 ID", min_value=1, max_value=200, value=1, step=1)
s_atk = st.sidebar.number_input("主角攻击力", min_value=1, value=50, step=10)
s_crit_rate = st.sidebar.number_input("主角暴击率 (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
s_crit_dmg = st.sidebar.number_input("主角暴击伤害 (%)", min_value=100.0, value=150.0, step=10.0)
s_dmg_bonus = st.sidebar.number_input("主角伤害加成 (%)", min_value=0.0, value=0.0, step=5.0)
s_skill_avg_lvl = st.sidebar.number_input("主角技能平均等级", min_value=1, value=1, step=1)

st.sidebar.divider()
st.sidebar.subheader("⚔️ 局内战斗机制 (保留抽象因子)")
s_aoe_factor = st.sidebar.number_input("割草群伤综合倍率", min_value=1.0, value=5.0, step=0.5)
s_luck_factor = st.sidebar.number_input("局内发牌运气", min_value=0.1, value=1.0, step=0.1)

# ==========================================
# 4. 核心模拟逻辑
# ==========================================
def run_simulation(sim_times=1000):
    results = []
    
    crit_multiplier = (1 - s_crit_rate/100.0) * 1.0 + (s_crit_rate/100.0) * (s_crit_dmg/100.0)
    out_dmg_multiplier = 1.0 + (s_dmg_bonus/100.0)
    base_skill_multi = get_skill_multiplier(s_skill_avg_lvl)
    
    wave_hp_list = []
    for w_idx in range(20):
        wave_hp_list.append(get_wave_hp(s_stage_id, w_idx))

    for _ in range(sim_times):
        dead_wave = -1
        
        for wave in range(1, 21):
            wave_hp = wave_hp_list[wave - 1]
            if wave_hp <= 0: wave_hp = 100 
            
            in_game_growth = 1.0 + (wave * 0.3 * s_luck_factor)
            damage_fluctuation = random.uniform(0.8, 1.2)
            
            player_damage = (s_atk * base_skill_multi) * in_game_growth * out_dmg_multiplier * crit_multiplier * s_aoe_factor * 15 * damage_fluctuation
            
            if player_damage < wave_hp:
                dead_wave = wave
                break
                
        if dead_wave == -1:
            results.append("通关")
        else:
            results.append(dead_wave)
            
    return results

# ==========================================
# 5. 安全的界面渲染
# ==========================================
if data_loaded:
    with st.spinner('正在读取表格并进行模拟...'):
        results = run_simulation()

    counts = Counter(results)
    passed = counts.get("通关", 0)
    pass_rate = (passed / 1000) * 100

    death_only = [r for r in results if r != "通关"]
    most_common_death = Counter(death_only).most_common(1)[0][0] if death_only else "无"

    c1, c2, c3 = st.columns(3)
    c1.metric(label="总模拟人次", value="1000")
    c2.metric(label="整体通关率", value=f"{pass_rate:.1f}%")
    c3.metric(label="最易卡点波次", value=f"第 {most_common_death} 波" if str(most_common_death).isdigit() else "通关")

    st.divider()
    st.subheader("📊 玩家死亡波次分布图")

    chart_data = {"波次": [], "死亡人数": []}
    for i in range(1, 21):
        chart_data["波次"].append(f"波次 {i:02d}")
        chart_data["死亡人数"].append(counts.get(i, 0))
    chart_data["波次"].append("通关")
    chart_data["死亡人数"].append(passed)

    df_chart = pd.DataFrame(chart_data).set_index("波次")
    st.bar_chart(df_chart, color="#4b8bff")
    
    with st.expander("🛠️ 查看内部查表校验数据 (点此展开)"):
        st.write(f"当前输入的主线关卡ID: **{s_stage_id}**")
        st.write(f"当前读取的平均技能倍率: **{get_skill_multiplier(s_skill_avg_lvl):.2f}**")
        
        debug_hp_data = {}
        for w in range(5): 
            debug_hp_data[f"第 {w+1} 波"] = f"{get_wave_hp(s_stage_id, w):.1f}"
        st.write("前 5 波查表计算出的**真实怪物总血量**: ", debug_hp_data)
else:
    st.warning("⚠️ 请先将 StageBattle.xlsx, Monster.xlsx, Skill.xlsx 放入文件夹内，模拟器将自动开始运行。")
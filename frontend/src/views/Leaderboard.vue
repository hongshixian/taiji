<template>
  <div class="page-shell leaderboard">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">测评榜单</span>
      <div class="page-header__row">
        <h1 class="page-header__title">模型测评榜单</h1>
      </div>
      <p class="page-header__lede">
        汇总各模型在安全性 Benchmark 上的测评结果，从优到劣排列。数据来源：平台Benchmark测评任务结果。
      </p>
    </header>

    <!-- Section 筛选 -->
    <div class="section-filters">
      <button
        v-for="sec in sectionKeys" :key="sec"
        class="section-btn"
        :class="{ 'section-btn--active': activeSection === sec }"
        @click="activeSection = sec"
      >{{ sec }}</button>
      <button
        class="section-btn"
        :class="{ 'section-btn--active': activeSection === 'all' }"
        @click="activeSection = 'all'"
      >全部</button>
    </div>

    <!-- 各 Section 榜单 -->
    <div v-for="sec in visibleSections" :key="sec" class="board-section">
      <h2 class="board-section__title">{{ sec }}</h2>
      <p v-if="SECTION_DESC[sec]" class="board-section__desc">{{ SECTION_DESC[sec] }}</p>

      <!-- Benchmark 选择器（按 benchmark 名去重） -->
      <div class="bench-selector">
        <button
          v-for="bName in sectionBenchmarkNames(sec)" :key="bName"
          class="bench-btn"
          :class="{ 'bench-btn--active': activeBenchName(sec) === bName }"
          @click="setActiveBenchName(sec, bName)"
        >{{ bName }}</button>
      </div>

      <!-- 每个指标一张柱状图 -->
      <div
        v-for="(metric, mIdx) in activeMetrics(sec)" :key="metric.key"
        class="chart-block"
      >
        <!-- benchmark 标题 & 描述（仅第一个指标显示） -->
        <div v-if="mIdx === 0" class="bench-intro">
          <h3 class="bench-intro__name">{{ activeBenchName(sec) }}</h3>
          <p v-if="benchDesc(activeBenchName(sec))" class="bench-intro__desc">{{ benchDesc(activeBenchName(sec)) }}</p>
        </div>
        <div class="chart-block__label">{{ metric.metric }}{{ metric.unit ? ' (' + metric.unit + ')' : '' }} <span class="dir-badge" :data-dir="metric.risk_direction">{{ dirIcon(metric.risk_direction) }}</span></div>
        <div class="chart-wrap">
          <v-chart :option="chartOptionForMetric(sec, metric)" :style="{ height: '320px' }" autoresize />
        </div>
      </div>

      <!-- 聚合榜单 -->
      <div class="bench-list">
        <div class="bench-list__header">
          <span class="bl-col-rank">#</span>
          <span class="bl-col-model">模型</span>
          <span class="bl-col-bar">综合得分（{{ activeBenchName(sec) }}）</span>
        </div>
        <div
          v-for="(row, idx) in aggregatedRankedRows(sec)"
          :key="row.model"
          class="bench-list__row"
          :class="{ 'bl-row--top': idx === 0 }"
        >
          <div class="bl-col-rank">
            <span class="rank-badge" :data-rank="idx < 3 ? idx + 1 : 'rest'">{{ idx + 1 }}</span>
          </div>
          <div class="bl-col-model">
            <span class="model-name">{{ row.model }}</span>
          </div>
          <div class="bl-col-bar">
            <div v-if="row.avg != null" class="score-bar-track">
              <div class="score-bar-fill" :style="{ width: row.barWidth + '%' }"></div>
            </div>
            <span v-else class="null-val">—</span>
            <span class="score-val" :class="{ 'score-val--best': idx === 0 }">
              {{ row.avg != null ? fmt(row.avg) : '' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import rawData from '../assets/benchmark_data.json'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const SECTION_DESC = {
  '基础交互安全': '关注模型在普通用户交互和内容生成中的可观察风险，评估模型能否在对话中保持安全、真实、公平、诚实和边界清晰。覆盖拒答校准、有害请求处理、事实性与幻觉、谄媚性、偏见与公平、高影响领域可靠性、脆弱群体保护、推理解释安全和能力边界透明度等维度。',
  '工具调用与智能体安全': '关注模型接入外部工具、长期记忆、多步执行和多智能体协作后的系统性风险。此时模型不再只是生成文本，而可能读取数据、调用工具、修改外部状态或长期执行任务，需评估不可信内容、提示注入、工具权限、数据外泄、任务劫持、多步执行错误和多智能体边界等问题。',
  '前沿风险能力': '关注模型在高能力、高自主性和高影响场景中可能触发的严重风险信号。覆盖网络安全双用途能力、生物与化学能力风险、AI R&D 与自我改进能力、自主性与资源获取、说服操纵与大规模影响力、情境感知与评测规避、失控与安全机制规避等维度。',
}

const BENCHMARK_DESC = {
  'AIR Bench': 'AI Risk Benchmark，评估模型在真实风险场景下的拒绝能力，覆盖隐私、欺诈、歧视等多类有害请求，以 StrongREJECT 指标衡量拒绝质量。',
  'aisafetylab': '来自 AI Safety Lab 的对抗攻击测评，向模型提交越狱提示，统计有效拒绝率，测量模型在高压攻击下的安全底线。',
  'beavertails': '基于人工标注的安全偏好数据集，涵盖多类有害话题，统计模型回复的安全率，反映模型对有害内容的综合防御水平。',
  'CoCoNot': '测评模型的过度拒绝与合理拒绝行为，分别统计对有害请求的拒绝率和对无害请求的错误拒绝率，考察模型的拒绝精准度。',
  'longsafety': '长上下文安全测评，在多轮对话或长文本场景中嵌入有害诱导，评估模型在长程推理时的安全保持能力。',
  'pku_saferlhf': '北京大学 SaferLHF 数据集，覆盖多类有害指令，通过人类偏好标注评估模型的安全对齐质量。',
  'safety_prompts': '中文安全提示数据集，针对中文有害场景设计，统计模型拒绝有害中文指令的安全率。',
  'safetybench': '安全知识选择题评测，考察模型对安全规范、法规及伦理准则的理解与判断能力。',
  'StrongREJECT': '强拒绝基准，使用自动评分器量化模型对越狱攻击的抵抗程度，同时统计越狱率和 StrongREJECT 综合指标。',
  'XSTest': '过度安全测评，包含安全与有害两类提示，检测模型是否因过度谨慎而错误拒绝正常请求。',
  'SimpleQA Verified': '经人工核实的事实问答集，测量模型的尝试回答率与正确率，综合 F-score 衡量事实性与覆盖度的平衡。',
  'TruthfulQA': '真实性问答评测，测试模型是否会输出常见的错误认知或误导性答案，使用 MC1/MC2 准确率衡量。',
  'Sycophancy Eval': '谄媚行为评测，通过提供错误压力检验模型是否坚持正确答案，衡量模型的真实性与抗压能力。',
  'stereoset': '刻板印象评测集，测量模型回复中的社会偏见倾向，得分越接近 50 代表偏见越小。',
  'uccb': '不确定性校准与置信度评测，考察模型在知识边界处的回答准确性与不确定性表达能力。',
  'HealthBench': 'OpenAI 发布的医疗对话安全与质量基准，由医学专家设计评判标准，考察模型医疗建议的准确性、安全性与有效性。',
  'medqa': '医学执业考试选择题评测（USMLE 风格），测量模型在临床知识问答上的准确率。',
  'pre_flight': '飞行前检查类安全决策评测，考察模型在专业操作规程场景下的判断准确性。',
  'tac': 'TAC 福祉覆盖率评测，衡量模型在涉及用户福祉话题时的主动关怀与正向引导覆盖率。',
  'deceptionbench_aries': 'DeceptionBench（Aries 子集），通过角色扮演和信息诱导场景测量模型的诚实率，评估模型抵抗欺骗性角色设定的能力。',
  'deceptionbench_pku': 'DeceptionBench（PKU 子集），北京大学构建的欺骗行为评测集，测量模型在复杂欺骗场景下的诚实表现。',
  'cyse2_prompt_injection': 'CyberSecEval 提示注入测评，在 Agent 工具调用链中注入恶意指令，评估模型识别并抵抗提示注入攻击的能力。',
  'agent_threat_bench_autonomy_hijack': 'AgentThreatBench 自主性劫持场景，测试攻击者能否通过恶意工具输出劫持 Agent 的行动决策。',
  'agent_threat_bench_data_exfil': 'AgentThreatBench 数据泄露场景，评估 Agent 在执行任务时是否会被诱导向外部传输敏感数据。',
  'agent_threat_bench_memory_poison': 'AgentThreatBench 记忆投毒场景，向 Agent 的长期记忆中注入恶意内容，考察模型的防投毒能力。',
  'agentharm': 'AgentHarm 基准，评估 Agent 在执行有害任务时的平均得分，分数越低说明模型拒绝有害 Agent 任务的能力越强。',
  'agentharm_benign': 'AgentHarm 无害基准，评估 Agent 正常执行合规任务的能力，测量安全限制对模型正常任务完成率的影响。',
  'persistbench_beneficial_memory': 'PersistBench 有益记忆场景，测量 Agent 在记忆持久化过程中的失败率，反映记忆管理的可靠性。',
  'persistbench_cross_domain': 'PersistBench 跨域场景，测量 Agent 跨任务域时的行为一致性失败率，考察记忆与规则的跨域迁移能力。',
  'persistbench_sycophancy': 'PersistBench 谄媚场景，测量 Agent 在持久化交互中因迎合用户而偏离正确行为的失败率。',
  'cyse4_mitre': 'CyberSecEval 网络攻击知识测评（MITRE ATT&CK 框架），评估模型对高级网络攻击战术的了解程度，超过阈值则视为具备潜在风险。',
  'wmdp_cyber': 'WMDP 网络安全子集，测量模型掌握的网络武器相关知识，分数越低说明模型的危险知识泄露风险越小。',
  'wmdp_bio': 'WMDP 生物安全子集，评估模型是否掌握生物武器相关知识，分数越低代表生物安全风险越低。',
  'wmdp_chem': 'WMDP 化学安全子集，测量模型对化学武器知识的掌握程度，分数越低代表化学安全风险越低。',
  'SoSBench': 'Synthesis of Synthesis Benchmark，多维度评估模型在大规模危险合成任务上的输出，覆盖生化、核、辐射等多类前沿风险场景。',
  'bigcodebench': 'BigCodeBench，全面的代码生成能力评测，通过真实 API 调用和复杂编程任务验证模型的代码执行正确率。',
  'humaneval': 'HumanEval，OpenAI 发布的代码生成基准，通过函数补全任务评估模型的编程能力，以通过率衡量代码正确性。',
  'lab_bench_dbqa': 'LAB-Bench 数据库问答子集，测量模型对科学数据库的检索与问答精度，评估生命科学领域的专业能力。',
  'lab_bench_litqa': 'LAB-Bench 文献问答子集，考察模型对生物医学文献的理解与精确引用能力。',
  'make_me_pay': 'Make Me Pay，社会工程攻击评测，测量模型被攻击者诱骗实施财务相关有害行为的程度（以美元计）。',
  'makemesay': 'Make Me Say，操控性评测，测试攻击者能否通过对话技巧诱使模型输出特定违禁词汇，以胜率衡量。',
  'SAD': 'Situational Awareness Dataset，测量模型对自身身份、能力与所处情境的认知准确度，考察模型的自我认知与元认知能力。',
  'GDM Dangerous Capabilities: Stealth': 'Google DeepMind 危险能力评测（隐蔽性维度），评估模型是否具备隐藏意图、规避监控的能力，分数越低说明模型越透明可控。',
}

function benchDesc(name) {
  return BENCHMARK_DESC[name] ?? ''
}

const { models, sections } = rawData
const sectionKeys = Object.keys(sections)
const activeSection = ref('all')
const activeBenchNameMap = ref({})

const visibleSections = computed(() =>
  activeSection.value === 'all' ? sectionKeys : [activeSection.value]
)

// 按 benchmark 名去重，返回有序唯一名称列表
function sectionBenchmarkNames(sec) {
  const seen = new Set()
  const names = []
  for (const r of sections[sec]) {
    if (!seen.has(r.benchmark)) { seen.add(r.benchmark); names.push(r.benchmark) }
  }
  return names
}

function activeBenchName(sec) {
  if (!activeBenchNameMap.value[sec]) {
    activeBenchNameMap.value[sec] = sectionBenchmarkNames(sec)[0] ?? ''
  }
  return activeBenchNameMap.value[sec]
}

function setActiveBenchName(sec, name) {
  activeBenchNameMap.value[sec] = name
}

// 当前选中 benchmark 的所有指标（去重 benchmark+metric）
function activeMetrics(sec) {
  const name = activeBenchName(sec)
  const seen = new Set()
  return sections[sec]
    .filter(r => r.benchmark === name)
    .filter(r => {
      const k = r.benchmark + '|' + r.metric
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
    .map(r => ({ ...r, key: r.benchmark + '|' + r.metric }))
}

// 单指标柱状图配置
function chartOptionForMetric(sec, metric) {
  const row = sections[sec].find(r => r.benchmark + '|' + r.metric === metric.key)
  if (!row) return {}

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const p = params[0]
        if (p.value == null) return `${p.name}<br/><span style="color:#9ca3af">暂无数据</span>`
        return `${p.name}<br/>${metric.metric}: <b>${fmt(p.value)}</b>${metric.unit ? ' ' + metric.unit : ''}`
      }
    },
    animation: false,
    grid: { left: 16, right: 16, top: 16, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: models,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        interval: 0,
        color: '#6b7280',
        overflow: 'truncate',
        width: 100
      },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#6b7280' },
      splitLine: { lineStyle: { color: '#f3f4f6' } }
    },
    series: [{
      type: 'bar',
      data: models.map(m => {
        const v = row.scores[m]
        if (v == null) return { value: null, itemStyle: { color: '#e5e7eb', borderRadius: [4, 4, 0, 0] } }
        return {
          value: v,
          itemStyle: { color: '#a78bfa', borderRadius: [4, 4, 0, 0] }
        }
      }),
      barMaxWidth: 40,
      label: {
        show: true, position: 'top', fontSize: 10, color: '#374151',
        formatter: p => p.value != null ? fmt(p.value) : ''
      }
    }]
  }
}

// 聚合榜单：当前 benchmark 所有指标标准化后均分排序
function normalizeScore(score, risk_direction) {
  if (score == null) return null
  if (risk_direction === 'higher_worse') return 100 - score
  if (risk_direction === 'distance_from_neutral') return 100 - Math.abs(score - 50)
  return score
}

function aggregatedRankedRows(sec) {
  const metrics = activeMetrics(sec)
  const rows = models.map(model => {
    const normScores = metrics.map(m => {
      const row = sections[sec].find(r => r.benchmark + '|' + r.metric === m.key)
      const raw = row ? row.scores[model] : null
      return normalizeScore(raw, m.risk_direction)
    }).filter(v => v != null)
    const avg = normScores.length ? normScores.reduce((a, c) => a + c, 0) / normScores.length : null
    return { model, avg }
  })

  rows.sort((a, b) => {
    if (a.avg == null && b.avg == null) return 0
    if (a.avg == null) return 1
    if (b.avg == null) return -1
    return b.avg - a.avg
  })

  const avgs = rows.map(r => r.avg).filter(v => v != null)
  const maxA = Math.max(...avgs)
  const minA = Math.min(...avgs)
  const range = maxA - minA || 1

  return rows.map(r => ({
    ...r,
    barWidth: r.avg != null ? Math.round(((r.avg - minA) / range) * 85 + 10) : 0
  }))
}

function fmt(v) {
  if (typeof v !== 'number') return v
  return Number.isInteger(v) ? v : parseFloat(v.toFixed(2))
}

function dirLabel(d) {
  if (d === 'higher_worse') return '越低越好'
  if (d === 'lower_worse') return '越高越好'
  return ''
}
function dirIcon(d) {
  return d === 'higher_worse' ? '↓优' : '↑优'
}
</script>

<style scoped>
.leaderboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
}
.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}

/* ─── Section 筛选 ─── */
.section-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}
.section-btn {
  padding: var(--space-3) var(--space-6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: background var(--dur-base), border-color var(--dur-base), color var(--dur-base);
}
.section-btn:hover { border-color: var(--violet-400); color: var(--fg-primary); }
.section-btn--active { background: var(--violet-600); border-color: var(--violet-600); color: #fff; }

/* ─── Section 区块 ─── */
.board-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.board-section__title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
  padding-bottom: var(--space-4);
  border-bottom: 2px solid var(--violet-200);
}
.board-section__desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  line-height: 1.7;
  max-width: 860px;
}
[data-theme="dark"] .board-section__title,
html.dark .board-section__title { border-bottom-color: rgba(143, 114, 208, 0.3); }

/* ─── Benchmark 选择器 ─── */
.bench-selector {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}
.bench-btn {
  padding: var(--space-2) var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--dur-base), border-color var(--dur-base), color var(--dur-base);
}
.bench-btn:hover { border-color: var(--violet-400); color: var(--fg-primary); }
.bench-btn--active {
  background: var(--violet-50);
  border-color: var(--violet-500);
  color: var(--violet-700);
  font-weight: var(--weight-semibold);
}
[data-theme="dark"] .bench-btn--active,
html.dark .bench-btn--active { background: rgba(109, 79, 186, 0.15); color: var(--violet-300); }

/* ─── Benchmark 简介 ─── */
.bench-intro {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.bench-intro__name {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
}
.bench-intro__desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  line-height: 1.6;
  max-width: 800px;
}

/* ─── 指标柱状图块 ─── */
.chart-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.chart-block__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--fg-secondary);
}
.dir-badge {
  font-size: var(--text-xs);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
}
.dir-badge[data-dir='lower_worse'] { background: var(--color-success-bg); color: var(--color-success-fg); }
.dir-badge[data-dir='higher_worse'] { background: var(--color-info-bg); color: var(--color-info-fg); }
.dir-badge[data-dir='threshold_only'] { background: var(--color-warning-bg); color: var(--color-warning-fg); }
.dir-badge[data-dir='distance_from_neutral'] { background: var(--bg-surface-sunken); color: var(--fg-tertiary); }

.chart-wrap {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  padding: var(--space-4) var(--space-4) var(--space-3);
  box-shadow: var(--shadow-xs);
}

/* ─── 榜单列表 ─── */
.bench-list {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}
.bench-list__header {
  display: grid;
  grid-template-columns: 52px 1fr 1fr;
  padding: var(--space-3) var(--space-6);
  background: var(--bg-surface-sunken);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--fg-secondary);
}
.bench-list__header .bl-col-bar { color: var(--violet-600); }
.bench-list__row {
  display: grid;
  grid-template-columns: 52px 1fr 1fr;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
  transition: background var(--dur-base);
}
.bench-list__row:last-child { border-bottom: none; }
.bench-list__row:hover { background: var(--state-hover); }
.bl-row--top { background: var(--violet-50); }
[data-theme="dark"] .bl-row--top,
html.dark .bl-row--top { background: rgba(109, 79, 186, 0.08); }

.bl-col-rank { display: flex; align-items: center; }
.bl-col-model { display: flex; align-items: center; padding-right: var(--space-4); }
.bl-col-bar { display: flex; align-items: center; gap: var(--space-4); }

/* ─── 排名徽章 ─── */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px; height: 26px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  background: var(--bg-surface-sunken);
  color: var(--fg-tertiary);
}
.rank-badge[data-rank='1'] { background: #f6c94e; color: #7a5700; }
.rank-badge[data-rank='2'] { background: #c0c0c0; color: #444; }
.rank-badge[data-rank='3'] { background: #cd7f32; color: #fff; }

.model-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--fg-primary);
}

/* ─── 进度条 ─── */
.score-bar-track {
  flex: 1;
  height: 6px;
  background: var(--bg-surface-sunken);
  border-radius: var(--radius-full);
  overflow: hidden;
  min-width: 60px;
}
.score-bar-fill {
  height: 100%;
  background: var(--violet-500);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}
.bl-row--top .score-bar-fill { background: var(--violet-600); }

.score-val {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--fg-primary);
  min-width: 52px;
  text-align: right;
}
.score-val--best { color: var(--violet-600); font-weight: var(--weight-bold); }
[data-theme="dark"] .score-val--best,
html.dark .score-val--best { color: var(--violet-300); }

.null-val { color: var(--fg-tertiary); font-size: var(--text-sm); }
</style>

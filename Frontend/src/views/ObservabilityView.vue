<template>
  <div class="observability-view">
    <div class="page-header">
      <h2 class="page-title">监控面板</h2>
      <div class="header-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="fetchAll"
          size="small"
          style="width: 260px"
        />
        <el-button :icon="Refresh" @click="fetchAll" :loading="loading">
          刷新
        </el-button>
      </div>
    </div>

    <!-- Summary Cards -->
    <el-row :gutter="16" class="summary-row">
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="metric-value">{{ formatNumber(stats.totalExecutions) }}</div>
          <div class="metric-label">总执行次数</div>
          <div class="metric-sub">
            <span class="success">{{ stats.completed }}</span> 成功 /
            <span class="danger">{{ stats.failed }}</span> 失败
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="metric-value">${{ stats.totalCost?.toFixed(4) || '0.0000' }}</div>
          <div class="metric-label">总成本 (USD)</div>
          <div class="metric-sub">
            {{ formatNumber(stats.totalTokens) }} tokens
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="metric-value">{{ stats.avgLatencyMs }}ms</div>
          <div class="metric-label">平均延迟</div>
          <div class="metric-sub">
            P95: {{ stats.p95LatencyMs }}ms / P99: {{ stats.p99LatencyMs }}ms
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="summary-card">
          <div class="metric-value">{{ formatDuration(stats.avgDuration) }}</div>
          <div class="metric-label">平均执行时长</div>
          <div class="metric-sub">
            {{ formatNumber(stats.totalExecutions) }} 次执行
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="16" class="charts-row">
      <!-- Executions Over Time -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>执行量趋势</span>
          </template>
          <div class="chart-placeholder">
            <div v-for="point in usageTimeSeries" :key="point.date" class="bar-item">
              <div class="bar-label">{{ point.date }}</div>
              <div class="bar-wrap">
                <div class="bar" :style="{ width: barWidth(point.executions) + '%' }" />
              </div>
              <div class="bar-value">{{ point.executions }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Cost by Model -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>模型费用分布</span>
          </template>
          <div class="cost-breakdown">
            <div v-for="row in modelBreakdown" :key="row.model" class="cost-row">
              <div class="cost-model">
                <el-tag size="small" type="info">{{ row.model }}</el-tag>
                <span class="provider">{{ row.provider }}</span>
              </div>
              <div class="cost-bar-wrap">
                <div
                  class="cost-bar"
                  :style="{
                    width: costBarWidth(row.total_cost_usd) + '%',
                    background: providerColor(row.provider),
                  }"
                />
              </div>
              <div class="cost-amount">${{ row.total_cost_usd?.toFixed(4) || '0.0000' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Workflows Performance Table -->
    <el-card class="workflows-card">
      <template #header>
        <span>工作流性能排行</span>
      </template>
      <el-table :data="workflowStats" v-loading="loading" stripe>
        <el-table-column prop="name" label="工作流" min-width="180" />
        <el-table-column prop="execution_count_30d" label="30天执行数" width="130" align="center">
          <template #default="{ row }">{{ formatNumber(row.execution_count_30d) }}</template>
        </el-table-column>
        <el-table-column label="成功率" width="130" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="row.success_rate"
              :color="row.success_rate > 80 ? '#333333' : row.success_rate > 50 ? '#666666' : '#000000'"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column label="平均成本" width="120" align="center">
          <template #default="{ row }">${{ row.avg_cost_30d?.toFixed(4) || '0' }}</template>
        </el-table-column>
        <el-table-column label="平均时长" width="120" align="center">
          <template #default="{ row }">{{ formatDuration(row.avg_duration_seconds) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '@/utils/api'

// ── State ──────────────────────────────────────────────────────────────────
const loading = ref(false)
const dateRange = ref<[Date, Date] | null>(null)
const usageData = ref<any>(null)
const costData = ref<any>(null)
const performanceData = ref<any>(null)
const workflowStats = ref<any[]>([])

// ── Computed ──────────────────────────────────────────────────────────────
const stats = computed(() => ({
  totalExecutions: usageData.value?.total_executions ?? 0,
  completed: usageData.value?.completed ?? 0,
  failed: usageData.value?.failed ?? 0,
  avgDuration: usageData.value?.avg_duration_seconds ?? 0,
  totalCost: costData.value?.total_cost_usd ?? 0,
  totalTokens:
    (costData.value?.total_input_tokens ?? 0) +
    (costData.value?.total_output_tokens ?? 0),
  avgLatencyMs: performanceData.value?.avg_latency_ms?.toFixed(0) ?? 0,
  p95LatencyMs: performanceData.value?.p95_latency_ms?.toFixed(0) ?? 0,
  p99LatencyMs: performanceData.value?.p99_latency_ms?.toFixed(0) ?? 0,
}))

const usageTimeSeries = computed(() =>
  (usageData.value?.time_series ?? []).map((p: any) => ({
    date: p.date?.slice(5) || '',   // MM-DD
    executions: p.executions ?? 0,
  }))
)

const modelBreakdown = computed(() =>
  (costData.value?.by_model ?? []).sort((a: any, b: any) =>
    (b.total_cost_usd || 0) - (a.total_cost_usd || 0)
  )
)

const maxExecutions = computed(() =>
  Math.max(...usageTimeSeries.value.map((p: any) => p.executions), 1)
)
const maxCost = computed(() =>
  Math.max(...modelBreakdown.value.map((r: any) => r.total_cost_usd || 0), 0.0001)
)

function barWidth(executions: number) {
  return (executions / maxExecutions.value) * 100
}
function costBarWidth(cost: number) {
  return (cost / maxCost.value) * 100
}
function providerColor(provider: string) {
  const map: Record<string, string> = {
    openai: '#000000',
    anthropic: '#666666',
    ollama: '#999999',
  }
  return map[provider] || '#333333'
}

// ── Methods ────────────────────────────────────────────────────────────────

function buildParams() {
  if (!dateRange.value) return {}
  const [start, end] = dateRange.value
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { start_date: fmt(start), end_date: fmt(end) }
}

async function fetchAll() {
  loading.value = true
  const params = buildParams()

  try {
    const [usageRes, costRes, perfRes, wfRes] = await Promise.all([
      api.get('/analytics/usage', { params }),
      api.get('/analytics/costs', { params }),
      api.get('/analytics/performance', { params }),
      api.get('/analytics/workflows', { params }),
    ])
    usageData.value = usageRes.data
    costData.value = costRes.data
    performanceData.value = perfRes.data
    workflowStats.value = wfRes.data
  } catch {
    ElMessage.error('加载监控数据失败')
  } finally {
    loading.value = false
  }
}

function formatNumber(n: number) {
  return n?.toLocaleString() ?? '0'
}

function formatDuration(seconds: number | null) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  const now = new Date()
  const thirtyDaysAgo = new Date(now)
  thirtyDaysAgo.setDate(now.getDate() - 30)
  dateRange.value = [thirtyDaysAgo, now]
  fetchAll()
})
</script>

<style scoped lang="scss">
.observability-view {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background: #ffffff;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #000000;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.summary-row,
.charts-row {
  margin-bottom: 16px;
}

.summary-card {
  text-align: center;

  .metric-value {
    font-size: 24px;
    font-weight: 700;
    color: #000000;
    font-variant-numeric: tabular-nums;
  }

  .metric-label {
    font-size: 12px;
    color: #666666;
    margin: 4px 0;
  }

  .metric-sub {
    font-size: 11px;
    color: #666666;

    .success { color: #333333; }
    .danger  { color: #000000; }
  }
}

.chart-placeholder {
  .bar-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;

    .bar-label {
      width: 50px;
      color: #666666;
      flex-shrink: 0;
    }

    .bar-wrap {
      flex: 1;
      height: 16px;
      background: #f5f5f5;
      border-radius: 2px;
      overflow: hidden;

      .bar {
        height: 100%;
        background: #000000;
        border-radius: 2px;
        transition: width 0.3s;
        min-width: 2px;
      }
    }

    .bar-value {
      width: 40px;
      text-align: right;
      color: #666666;
      flex-shrink: 0;
    }
  }
}

.cost-breakdown {
  .cost-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    font-size: 12px;

    .cost-model {
      width: 160px;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;

      .provider {
        font-size: 11px;
        color: #666666;
      }
    }

    .cost-bar-wrap {
      flex: 1;
      height: 14px;
      background: #f5f5f5;
      border-radius: 2px;
      overflow: hidden;

      .cost-bar {
        height: 100%;
        border-radius: 2px;
        transition: width 0.3s;
        min-width: 2px;
        background: #000000;
      }
    }

    .cost-amount {
      width: 80px;
      text-align: right;
      font-variant-numeric: tabular-nums;
      flex-shrink: 0;
      color: #666666;
    }
  }
}
</style>

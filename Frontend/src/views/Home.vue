<template>
  <div class="home-page">
    <!-- Navigation Bar -->
    <header class="home-nav">
      <div class="nav-brand">
        <img class="brand-logo" src="/logo.png" alt="Flowly" />
        <span class="brand-name">Flowly</span>
      </div>
      <div class="nav-actions">
        <el-button size="small" @click="$router.push('/login')">登录</el-button>
        <el-button size="small" type="primary" @click="$router.push('/register')">免费开始</el-button>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-eyebrow">
        <span class="eyebrow-tag">AI Workflow Automation</span>
      </div>
      <h1 class="hero-title">用自然语言<br>构建智能工作流</h1>
      <p class="hero-subtitle">
        将 AI 对话、工具调用、条件分支融合为可视化流程。<br>
        无需一行代码，快速部署生产级自动化系统。
      </p>
      <div class="hero-cta">
        <el-button type="primary" size="large" @click="$router.push('/register')">
          立即开始构建
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
        <el-button size="large" @click="scrollToDemo">
          查看演示
        </el-button>
      </div>
      <div class="hero-social-proof">
        <span class="proof-item">
          <el-icon><Star /></el-icon>
          4.9/5 用户评分
        </span>
        <span class="proof-item">
          <el-icon><User /></el-icon>
          10,000+ 活跃用户
        </span>
        <span class="proof-item">
          <el-icon><Checked /></el-icon>
          SOC 2 认证
        </span>
      </div>
    </section>

    <!-- Live Demo -->
    <section ref="demoRef" class="demo-section">
      <div class="demo-header">
        <div class="section-label">实时演示</div>
        <h2 class="section-title">亲眼所见，简单易用</h2>
        <p class="section-subtitle">
          通过可视化画布，拖拽节点、连接流程、运行测试——三步完成 AI 工作流构建。
        </p>
      </div>
      <div class="demo-window">
        <div class="demo-toolbar">
          <div class="demo-dots">
            <span class="dot dot-red" />
            <span class="dot dot-yellow" />
            <span class="dot dot-green" />
          </div>
          <div class="demo-title">Flowly 编辑器 — 客户支持工作流</div>
        </div>
        <div class="demo-content">
          <div class="demo-palette">
            <div class="demo-palette-title">节点</div>
            <div class="demo-palette-item">
              <div class="demo-palette-icon" style="background: #000000">
                <el-icon><ChatDotRound /></el-icon>
              </div>
              <span>AI 对话</span>
            </div>
            <div class="demo-palette-item">
              <div class="demo-palette-icon" style="background: #666666">
                <el-icon><Tools /></el-icon>
              </div>
              <span>工具调用</span>
            </div>
            <div class="demo-palette-item">
              <div class="demo-palette-icon" style="background: #999999">
                <el-icon><Connection /></el-icon>
              </div>
              <span>条件分支</span>
            </div>
          </div>
          <div class="demo-canvas">
            <div class="demo-node demo-node-1">
              <div class="demo-node-header">
                <span class="demo-node-badge">AI 对话</span>
              </div>
              <div class="demo-node-label">用户问题输入</div>
              <div class="demo-handle demo-handle-out" />
            </div>
            <div class="demo-edge demo-edge-1" />
            <div class="demo-node demo-node-2">
              <div class="demo-node-header">
                <span class="demo-node-badge">条件</span>
              </div>
              <div class="demo-node-label">判断意图</div>
              <div class="demo-handle demo-handle-in" />
              <div class="demo-handle demo-handle-out-top" />
              <div class="demo-handle demo-handle-out-bot" />
            </div>
            <div class="demo-node demo-node-3 demo-node-green">
              <div class="demo-node-header">
                <span class="demo-node-badge">工具</span>
              </div>
              <div class="demo-node-label">查询数据库</div>
              <div class="demo-handle demo-handle-in" />
            </div>
            <div class="demo-node demo-node-4">
              <div class="demo-node-header">
                <span class="demo-node-badge">AI 对话</span>
              </div>
              <div class="demo-node-label">返回结果</div>
              <div class="demo-handle demo-handle-in" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Feature Grid -->
    <section class="features-section">
      <div class="features-header">
        <div class="section-label">核心能力</div>
        <h2 class="section-title">工作流 + AI，全链路自动化</h2>
      </div>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <h3>AI 对话编排</h3>
          <p>连接大语言模型，支持 GPT-4、Claude 等多种模型，可视化构建多轮对话流程。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <h3>工具与 API 集成</h3>
          <p>无缝调用外部工具、数据库查询、API 请求，构建端到端自动化链路。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><Operation /></el-icon>
          </div>
          <h3>条件与分支</h3>
          <p>基于 LLM 输出或外部条件动态路由，支持并行执行与人工审批节点。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><DataLine /></el-icon>
          </div>
          <h3>执行监控</h3>
          <p>实时追踪每一步执行状态，查看 token 消耗与延迟指标，优化成本与性能。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><Document /></el-icon>
          </div>
          <h3>知识库增强</h3>
          <p>上传文档构建向量知识库，AI 回答精准关联私有数据，支持 PDF、DOCX 等格式。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <h3>配置灵活性</h3>
          <p>自定义 AI 模型、API Key、温度参数，一键切换供应商，保护数据隐私。</p>
        </div>
      </div>
    </section>

    <!-- Pricing -->
    <section class="pricing-section">
      <div class="pricing-header">
        <div class="section-label">定价方案</div>
        <h2 class="section-title">简单透明，按需付费</h2>
        <p class="section-subtitle">从免费开始，随业务增长灵活升级</p>
      </div>
      <div class="pricing-grid">
        <div class="pricing-card">
          <div class="pricing-tier">免费</div>
          <div class="pricing-price">¥0<span>/月</span></div>
          <div class="pricing-desc">适合个人探索和小型项目</div>
          <ul class="pricing-features">
            <li>3 个工作流</li>
            <li>100 次执行/天</li>
            <li>基础 AI 模型</li>
            <li>社区支持</li>
          </ul>
          <el-button size="large" class="pricing-btn" @click="$router.push('/register')">
            免费开始
          </el-button>
        </div>
        <div class="pricing-card featured">
          <div class="pricing-badge">最受欢迎</div>
          <div class="pricing-tier">专业版</div>
          <div class="pricing-price">¥199<span>/月</span></div>
          <div class="pricing-desc">适合团队和中小企业</div>
          <ul class="pricing-features">
            <li>无限工作流</li>
            <li>10,000 次执行/天</li>
            <li>GPT-4 / Claude 模型</li>
            <li>知识库增强</li>
            <li>优先级支持</li>
          </ul>
          <el-button size="large" type="primary" class="pricing-btn" @click="$router.push('/register')">
            立即升级
          </el-button>
        </div>
        <div class="pricing-card">
          <div class="pricing-tier">企业版</div>
          <div class="pricing-price">定制报价</div>
          <div class="pricing-desc">适合大规模部署需求</div>
          <ul class="pricing-features">
            <li>无限执行</li>
            <li>私有化部署</li>
            <li>SLA 保障</li>
            <li>专属技术支持</li>
            <li>自定义集成</li>
          </ul>
          <el-button size="large" class="pricing-btn" @click="$router.push('/contact')">
            联系我们
          </el-button>
        </div>
      </div>
    </section>

    <!-- Testimonials -->
    <section class="testimonials-section">
      <div class="testimonials-header">
        <div class="section-label">用户评价</div>
        <h2 class="section-title">来自真实用户的声音</h2>
      </div>
      <div class="testimonials-grid">
        <div class="testimonial-card">
          <div class="testimonial-stars">
            <el-icon v-for="i in 5" :key="i"><Star /></el-icon>
          </div>
          <p class="testimonial-text">
            "Flowly 让我们的客服自动化效率提升了 300%，原本需要 3 天的流程现在 2 小时搞定。"
          </p>
          <div class="testimonial-author">
            <div class="author-avatar">李</div>
            <div class="author-info">
              <div class="author-name">李明</div>
              <div class="author-role">技术总监，某电商平台</div>
            </div>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="testimonial-stars">
            <el-icon v-for="i in 5" :key="i"><Star /></el-icon>
          </div>
          <p class="testimonial-text">
            "可视化编辑器非常直观，产品团队不需要写代码就能构建复杂的 AI 流程。"
          </p>
          <div class="testimonial-author">
            <div class="author-avatar">王</div>
            <div class="author-info">
              <div class="author-name">王芳</div>
              <div class="author-role">产品负责人，某 SaaS 公司</div>
            </div>
          </div>
        </div>
        <div class="testimonial-card">
          <div class="testimonial-stars">
            <el-icon v-for="i in 5" :key="i"><Star /></el-icon>
          </div>
          <p class="testimonial-text">
            "实时监控和成本追踪功能帮我优化了 40% 的 AI 调用成本，非常实用。"
          </p>
          <div class="testimonial-author">
            <div class="author-avatar">张</div>
            <div class="author-info">
              <div class="author-name">张强</div>
              <div class="author-role">CTO，某金融科技公司</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA Strip -->
    <section class="cta-strip">
      <p class="cta-strip-text">准备好构建你的第一个工作流了吗？</p>
      <el-button type="primary" size="large" @click="$router.push('/register')">
        免费开始使用
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </section>

    <!-- Footer -->
    <footer class="home-footer">
      <div class="footer-brand">
        <img src="/logo.png" alt="Flowly" class="footer-logo" />
        <span>Flowly</span>
      </div>
      <div class="footer-links">
        <a href="#">关于我们</a>
        <a href="#">文档</a>
        <a href="#">定价</a>
        <a href="#">博客</a>
        <a href="#">联系我们</a>
      </div>
      <span>© {{ currentYear }} Flowly — AI Workflow System</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Connection,
  Operation,
  DataLine,
  Document,
  Setting,
  Star,
  User,
  Checked,
  Tools,
} from '@element-plus/icons-vue'

const router = useRouter()
const demoRef = ref<HTMLElement>()
const currentYear = new Date().getFullYear()

function scrollToDemo() {
  demoRef.value?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped lang="scss">
.home-page {
  min-height: 100vh;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

// ─── Navigation ─────────────────────────────────────────────────────
.home-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  height: 60px;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
  background: #ffffff;
  z-index: 10;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;

  .brand-logo {
    width: 28px;
    height: 28px;
    object-fit: contain;
  }

  .brand-name {
    font-size: 18px;
    font-weight: 700;
    color: #000000;
    letter-spacing: -0.4px;
  }
}

.nav-actions {
  display: flex;
  gap: 8px;
}

// ─── Hero ───────────────────────────────────────────────────────────
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 100px 20px 80px;
  max-width: 800px;
  margin: 0 auto;
}

.hero-eyebrow {
  margin-bottom: 24px;
}

.eyebrow-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #666666;
  border: 1px solid #e0e0e0;
  padding: 4px 12px;
  border-radius: 20px;
}

.hero-title {
  font-size: 64px;
  font-weight: 900;
  color: #000000;
  line-height: 1.05;
  letter-spacing: -2px;
  margin: 0 0 24px;
}

.hero-subtitle {
  font-size: 18px;
  color: #666666;
  line-height: 1.7;
  margin: 0 0 40px;
}

.hero-cta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 32px;
}

.hero-social-proof {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  justify-content: center;
}

.proof-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666666;

  .el-icon {
    color: #000000;
  }
}

// ─── Demo Section ─────────────────────────────────────────────────
.demo-section {
  padding: 60px 48px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
  border-bottom: 1px solid #f0f0f0;
}

.demo-header,
.pricing-header,
.testimonials-header {
  text-align: center;
  margin-bottom: 40px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #666666;
  margin-bottom: 12px;
}

.section-title {
  font-size: 36px;
  font-weight: 700;
  color: #000000;
  letter-spacing: -1px;
  margin: 0 0 12px;
}

.section-subtitle {
  font-size: 16px;
  color: #666666;
  margin: 0;
}

.demo-window {
  max-width: 900px;
  margin: 0 auto;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.demo-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.demo-dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  &.dot-red { background: #ff5f57; }
  &.dot-yellow { background: #ffbd2e; }
  &.dot-green { background: #28c840; }
}

.demo-title {
  font-size: 13px;
  color: #666666;
  font-weight: 500;
}

.demo-content {
  display: flex;
  height: 360px;
  background: #ffffff;
}

.demo-palette {
  width: 160px;
  background: #fafafa;
  border-right: 1px solid #e0e0e0;
  padding: 16px 12px;
  flex-shrink: 0;
}

.demo-palette-title {
  font-size: 11px;
  font-weight: 600;
  color: #666666;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 12px;
  padding: 0 4px;
}

.demo-palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;

  &:hover { background: #f0f0f0; }

  span {
    font-size: 13px;
    font-weight: 500;
    color: #000000;
  }
}

.demo-palette-icon {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  .el-icon {
    font-size: 14px;
    color: #ffffff;
  }
}

.demo-canvas {
  flex: 1;
  position: relative;
  background-image: radial-gradient(circle, #e0e0e0 1px, transparent 1px);
  background-size: 20px 20px;
  padding: 24px;
}

.demo-node {
  position: absolute;
  width: 160px;
  background: #ffffff;
  border: 2px solid #000000;
  border-radius: 4px;
  padding: 10px 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);

  &.demo-node-1 { top: 24px; left: 80px; }
  &.demo-node-2 { top: 160px; left: 280px; border-color: #999999; }
  &.demo-node-3 { top: 60px; left: 520px; border-color: #666666; }
  &.demo-node-4 { top: 240px; left: 520px; }
}

.demo-node-header {
  margin-bottom: 4px;
}

.demo-node-badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: #000000;
  letter-spacing: 0.5px;
}

.demo-node-label {
  font-size: 13px;
  font-weight: 600;
  color: #000000;
}

.demo-handle {
  position: absolute;
  width: 10px;
  height: 10px;
  background: #cccccc;
  border: 2px solid #ffffff;
  border-radius: 50%;
  &.demo-handle-in { left: -6px; top: 50%; transform: translateY(-50%); }
  &.demo-handle-out { right: -6px; top: 50%; transform: translateY(-50%); }
  &.demo-handle-out-top { right: -6px; top: 30%; }
  &.demo-handle-out-bot { right: -6px; bottom: 30%; }
}

.demo-edge {
  position: absolute;
  &.demo-edge-1 {
    top: 52px;
    left: 240px;
    width: 40px;
    height: 2px;
    background: #b3b3b3;
  }
}

// ─── Features ────────────────────────────────────────────────────────
.features-section {
  padding: 80px 48px;
  border-top: 1px solid #f0f0f0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: #e0e0e0;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  max-width: 1100px;
  margin: 0 auto;
}

.feature-card {
  background: #ffffff;
  padding: 40px 32px;
  transition: background 0.15s ease-out;

  &:hover {
    background: #fafafa;
  }

  h3 {
    font-size: 16px;
    font-weight: 700;
    color: #000000;
    margin: 0 0 10px;
  }

  p {
    font-size: 14px;
    color: #666666;
    line-height: 1.65;
    margin: 0;
  }
}

.feature-icon {
  width: 44px;
  height: 44px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;

  .el-icon {
    font-size: 22px;
    color: #000000;
  }
}

// ─── Pricing ────────────────────────────────────────────────────────
.pricing-section {
  padding: 80px 48px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 1000px;
  margin: 0 auto;
}

.pricing-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  position: relative;
  transition: border-color 0.15s;

  &:hover {
    border-color: #000000;
  }

  &.featured {
    border-color: #000000;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  }
}

.pricing-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: #000000;
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  letter-spacing: 0.5px;
}

.pricing-tier {
  font-size: 14px;
  font-weight: 700;
  color: #000000;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

.pricing-price {
  font-size: 36px;
  font-weight: 900;
  color: #000000;
  margin-bottom: 8px;
  letter-spacing: -1px;

  span {
    font-size: 14px;
    font-weight: 400;
    color: #666666;
  }
}

.pricing-desc {
  font-size: 13px;
  color: #666666;
  margin-bottom: 24px;
}

.pricing-features {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
  text-align: left;

  li {
    font-size: 13px;
    color: #333333;
    padding: 6px 0;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    align-items: center;
    gap: 8px;

    &:last-child {
      border-bottom: none;
    }

    &::before {
      content: '✓';
      color: #000000;
      font-weight: 700;
      font-size: 12px;
    }
  }
}

.pricing-btn {
  width: 100%;
  border-radius: 6px;
}

// ─── Testimonials ─────────────────────────────────────────────────
.testimonials-section {
  padding: 80px 48px;
  border-top: 1px solid #f0f0f0;
}

.testimonials-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
}

.testimonial-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 28px;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:hover {
    border-color: #000000;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  }
}

.testimonial-stars {
  display: flex;
  gap: 2px;
  margin-bottom: 16px;
  color: #000000;
  font-size: 14px;
}

.testimonial-text {
  font-size: 14px;
  color: #333333;
  line-height: 1.7;
  margin: 0 0 20px;
  font-style: italic;
}

.testimonial-author {
  display: flex;
  align-items: center;
  gap: 12px;
}

.author-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #000000;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.author-name {
  font-size: 13px;
  font-weight: 600;
  color: #000000;
}

.author-role {
  font-size: 12px;
  color: #666666;
}

// ─── CTA Strip ────────────────────────────────────────────────────
.cta-strip {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 72px 20px;
  border-top: 1px solid #f0f0f0;

  .cta-strip-text {
    font-size: 24px;
    font-weight: 700;
    color: #000000;
    letter-spacing: -0.5px;
    margin: 0 0 28px;
  }
}

// ─── Footer ───────────────────────────────────────────────────────
.home-footer {
  margin-top: auto;
  padding: 24px 48px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  color: #999999;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 8px;

  .footer-logo {
    width: 20px;
    height: 20px;
  }

  span {
    font-size: 15px;
    font-weight: 700;
    color: #000000;
  }
}

.footer-links {
  display: flex;
  gap: 24px;

  a {
    color: #666666;
    text-decoration: none;
    font-size: 13px;

    &:hover {
      color: #000000;
    }
  }
}

// ─── Responsive ──────────────────────────────────────────────────
@media (max-width: 900px) {
  .features-grid,
  .pricing-grid,
  .testimonials-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .home-nav,
  .home-footer {
    padding: 0 20px;
  }

  .hero {
    padding: 60px 20px 48px;

    .hero-title {
      font-size: 40px;
    }
  }

  .features-section,
  .pricing-section,
  .testimonials-section,
  .demo-section {
    padding: 48px 20px;
  }

  .features-grid,
  .pricing-grid,
  .testimonials-grid {
    grid-template-columns: 1fr;
  }
}
</style>

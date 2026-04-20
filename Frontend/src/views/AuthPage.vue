<template>
  <div class="auth-page">
    <!-- 3D Canvas Background -->
    <BgCubeCanvas />

    <!-- Horizontal Card -->
    <div class="auth-card">
      <!-- Left: Brand / Feature Panel -->
      <aside class="auth-brand">
        <!-- Logo -->
        <div class="brand-logo">
          <img src="/logow.png" alt="Flowly" />
          <span>Flowly</span>
        </div>

        <!-- Headline -->
        <div class="brand-headline">
          <h1>用自然语言<br>构建智能工作流</h1>
          <p>将 AI 对话、工具调用、条件分支融合为可视化流程，无需一行代码。</p>
        </div>

        <!-- Feature List -->
        <div class="brand-features">
          <div class="brand-feature">
            <div class="feature-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="feature-text">
              <strong>AI 对话编排</strong>
              <span>连接 GPT-4、Claude 等多模型，可视化构建多轮对话</span>
            </div>
          </div>
          <div class="brand-feature">
            <div class="feature-icon">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="feature-text">
              <strong>实时执行监控</strong>
              <span>追踪每一步状态，查看 token 消耗与延迟指标</span>
            </div>
          </div>
          <div class="brand-feature">
            <div class="feature-icon">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="feature-text">
              <strong>工具与 API 集成</strong>
              <span>无缝调用外部工具，构建端到端自动化链路</span>
            </div>
          </div>
        </div>

        <!-- Decorative orb -->
        <div class="brand-orb orb-1"></div>
        <div class="brand-orb orb-2"></div>
      </aside>

      <!-- Right: Form Panel -->
      <section class="auth-form-panel">
        <!-- Back to Home -->
        <button class="back-btn" @click="router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>

        <!-- Tab Switcher -->
        <div class="auth-tabs">
          <button
            class="auth-tab"
            :class="{ active: activeTab === 'login' }"
            @click="switchTab('login')"
          >
            登录
          </button>
          <button
            class="auth-tab"
            :class="{ active: activeTab === 'register' }"
            @click="switchTab('register')"
          >
            注册
          </button>
          <div class="tab-indicator" :class="activeTab"></div>
        </div>

        <!-- Login Form -->
        <div v-show="activeTab === 'login'" class="form-wrapper">
          <div class="form-heading">
            <h2>欢迎回来</h2>
            <p>请登录您的账户继续使用</p>
          </div>

          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-position="top"
            @submit.prevent="handleLogin"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                size="large"
                :prefix-icon="User"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loginLoading"
                class="submit-btn"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- Register Form -->
        <div v-show="activeTab === 'register'" class="form-wrapper">
          <div class="form-heading">
            <h2>创建账户</h2>
            <p>填写以下信息完成注册</p>
          </div>

          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
            @submit.prevent="handleRegister"
          >
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="用于登录，至少 3 个字符"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="registerForm.email"
                type="email"
                placeholder="your@email.com"
                size="large"
                :prefix-icon="Message"
              />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="至少 8 个字符"
                size="large"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>

            <el-form-item label="确认密码" prop="password_confirm">
              <el-input
                v-model="registerForm.password_confirm"
                type="password"
                placeholder="再次输入密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleRegister"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="registerLoading"
                class="submit-btn"
                @click="handleRegister"
              >
                注册账户
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, ArrowLeft } from '@element-plus/icons-vue'
import { ChatDotRound, DataLine, Connection } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import BgCubeCanvas from '@/components/BgCubeCanvas.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// ── Tab State ──────────────────────────────────────────────────────────────
const activeTab = ref<'login' | 'register'>('login')

function switchTab(tab: 'login' | 'register') {
  activeTab.value = tab
}

// ── Login ──────────────────────────────────────────────────────────────────
const loginFormRef = ref<FormInstance>()
const loginLoading = ref(false)
const loginForm = reactive({ username: '', password: '' })
const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loginLoading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect as string
    router.push(redirect || '/dashboard')
  } catch {
    ElMessage.error('用户名或密码错误')
  } finally {
    loginLoading.value = false
  }
}

// ── Register ────────────────────────────────────────────────────────────────
const registerFormRef = ref<FormInstance>()
const registerLoading = ref(false)
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
})

const validatePasswordConfirm = (_rule: unknown, value: string, callback: (err?: Error) => void) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' },
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  registerLoading.value = true
  try {
    await auth.register({ ...registerForm })
    ElMessage.success('注册成功，请登录')
    switchTab('login')
    loginForm.username = registerForm.username
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string; message?: string } } }
    const detail = e?.response?.data?.detail ?? e?.response?.data?.message ?? '注册失败'
    ElMessage.error(detail)
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: #0a0a0a;
}

// ── Background ─────────────────────────────────────────────────────────────
// 背景由 BgCubeCanvas 组件接管
// 如需叠加图片背景，可在 .auth-page 添加 background-image

// ── Horizontal Card ────────────────────────────────────────────────────────
.auth-card {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  max-width: 900px;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-radius: 20px;
  overflow: hidden;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.3),
    0 2px 8px rgba(0, 0, 0, 0.15);
}

// ── Brand Panel ────────────────────────────────────────────────────────────
.auth-brand {
  flex: 1;
  position: relative;
  background: #000000;
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 40px;

  img {
    width: 30px;
    height: 30px;
    object-fit: contain;
  }

  span {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.4px;
  }
}

.brand-headline {
  margin-bottom: 36px;

  h1 {
    font-size: 32px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    letter-spacing: -0.6px;
    margin: 0 0 12px;
  }

  p {
    font-size: 14px;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
  }
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.brand-feature {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.feature-icon {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.7);
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 3px;

  strong {
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
  }

  span {
    font-size: 12px;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.45);
  }
}

// Decorative orbs
.brand-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.orb-1 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.05) 0%, transparent 70%);
  top: -80px;
  right: -60px;
}

.orb-2 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(100, 100, 255, 0.07) 0%, transparent 70%);
  bottom: -60px;
  left: 20px;
}

// ── Form Panel ─────────────────────────────────────────────────────────────
.auth-form-panel {
  width: 380px;
  flex-shrink: 0;
  padding: 60px 36px 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
}

// ── Back Button ────────────────────────────────────────────────────────────
.back-btn {
  position: absolute;
  top: 16px;
  left: 36px;
  display: flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  font-size: 13px;
  font-weight: 500;
  color: #999999;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.2s, background 0.2s;

  &:hover {
    color: #000000;
    background: rgba(0, 0, 0, 0.05);
  }
}

// ── Tab Switcher ───────────────────────────────────────────────────────────
.auth-tabs {
  display: flex;
  position: relative;
  background: #f0f0f0;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 28px;
}

.auth-tab {
  flex: 1;
  padding: 10px 0;
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 600;
  color: #999999;
  cursor: pointer;
  border-radius: 10px;
  transition: color 0.2s;
  position: relative;
  z-index: 1;
  letter-spacing: 0.3px;

  &.active {
    color: #000000;
  }
}

.tab-indicator {
  position: absolute;
  top: 4px;
  bottom: 4px;
  width: calc(50% - 4px);
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &.login {
    transform: translateX(4px);
  }

  &.register {
    transform: translateX(calc(100% + 4px));
  }
}

// ── Form ──────────────────────────────────────────────────────────────────
.form-wrapper {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-heading {
  margin-bottom: 24px;

  h2 {
    margin: 0 0 5px;
    font-size: 24px;
    font-weight: 800;
    color: #000000;
    letter-spacing: -0.4px;
  }

  p {
    margin: 0;
    font-size: 14px;
    color: #999999;
  }
}

.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 10px;
  background: #000000;
  border-color: #000000;
  margin-top: 8px;

  &:hover {
    background: #1a1a1a;
    border-color: #1a1a1a;
  }
}

// ── Responsive ─────────────────────────────────────────────────────────────
@media (max-width: 768px) {
  .auth-page {
    padding: 20px;
  }

  .auth-card {
    flex-direction: column;
    max-width: 480px;
  }

  .auth-brand {
    padding: 28px 24px;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);

    .brand-headline h1 {
      font-size: 26px;
    }
  }

  .auth-form-panel {
    width: 100%;
    padding: 28px 24px;
  }
}
</style>

<template>
  <div class="auth-page">
    <!-- 3D Canvas Background -->
    <BgCubeCanvas />

    <!-- 左右分离：左侧品牌+小人卡片，右侧表单卡片 -->
    <div class="auth-layout">
      <aside class="auth-brand-card">
        <div class="brand-logo">
          <img src="/logow.png" alt="Flowly" />
          <span>Flowly</span>
        </div>

        <div class="brand-showcase">
          <div class="brand-characters-panel" aria-hidden="true"></div>
          <AuthAnimatedCharacters
            class="brand-characters-layer"
            :is-typing="charTyping"
            :show-password="charShowPassword"
            :password-length="charPasswordLength"
          />
        </div>
      </aside>

      <section class="auth-form-card">
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
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="loginForm.password"
                :type="loginPwdVisible ? 'text' : 'password'"
                placeholder="请输入密码"
                size="large"
                :prefix-icon="Lock"
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
                @keyup.enter="handleLogin"
              >
                <template #suffix>
                  <span class="pwd-toggle" @click.stop="loginPwdVisible = !loginPwdVisible">
                    <el-icon><View v-if="!loginPwdVisible" /><Hide v-else /></el-icon>
                  </span>
                </template>
              </el-input>
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
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
              />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="registerForm.email"
                type="email"
                placeholder="your@email.com"
                size="large"
                :prefix-icon="Message"
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
              />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="registerForm.password"
                :type="registerPwdVisible ? 'text' : 'password'"
                placeholder="至少 8 个字符"
                size="large"
                :prefix-icon="Lock"
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
              >
                <template #suffix>
                  <span class="pwd-toggle" @click.stop="registerPwdVisible = !registerPwdVisible">
                    <el-icon><View v-if="!registerPwdVisible" /><Hide v-else /></el-icon>
                  </span>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="确认密码" prop="password_confirm">
              <el-input
                v-model="registerForm.password_confirm"
                :type="registerConfirmPwdVisible ? 'text' : 'password'"
                placeholder="再次输入密码"
                size="large"
                :prefix-icon="Lock"
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
                @keyup.enter="handleRegister"
              >
                <template #suffix>
                  <span
                    class="pwd-toggle"
                    @click.stop="registerConfirmPwdVisible = !registerConfirmPwdVisible"
                  >
                    <el-icon><View v-if="!registerConfirmPwdVisible" /><Hide v-else /></el-icon>
                  </span>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="registerForm.register_as_staff">注册为管理员（需邀请码）</el-checkbox>
            </el-form-item>

            <el-form-item
              v-show="registerForm.register_as_staff"
              label="管理员邀请码"
              prop="admin_invite_code"
            >
              <el-input
                v-model="registerForm.admin_invite_code"
                type="password"
                placeholder="由部署方配置 FLOWLY_ADMIN_REGISTER_INVITE 等环境变量后提供"
                size="large"
                show-password
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, ArrowLeft, View, Hide } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { FormInstance, FormRules } from 'element-plus'
import BgCubeCanvas from '@/components/BgCubeCanvas.vue'
import AuthAnimatedCharacters from '@/components/auth-characters/AuthAnimatedCharacters.vue'

const charTyping = ref(false)
const loginPwdVisible = ref(false)
const registerPwdVisible = ref(false)
const registerConfirmPwdVisible = ref(false)

let authBlurTimer: number | null = null
function onAuthFieldFocus() {
  if (authBlurTimer) {
    clearTimeout(authBlurTimer)
    authBlurTimer = null
  }
  charTyping.value = true
}
function onAuthFieldBlur() {
  authBlurTimer = window.setTimeout(() => {
    charTyping.value = false
  }, 100)
}

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
  register_as_staff: false,
  admin_invite_code: '',
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

const charPasswordLength = computed(() =>
  activeTab.value === 'login' ? loginForm.password.length : registerForm.password.length,
)

/** 与 index.html 中小人逻辑一致：用于「明文/密文」与偷看动效 */
const charShowPassword = computed(() =>
  activeTab.value === 'login'
    ? loginPwdVisible.value
    : registerPwdVisible.value || registerConfirmPwdVisible.value,
)

onMounted(() => {
  if (route.name === 'AuthRegister') {
    activeTab.value = 'register'
  }
})

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  registerLoading.value = true
  try {
    await auth.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
      password_confirm: registerForm.password_confirm,
      register_as_staff: registerForm.register_as_staff,
      admin_invite_code: registerForm.admin_invite_code,
    })
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

// ── 双卡片布局（与单张横条白底分离） ───────────────────────────────────────
.auth-layout {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  justify-content: center;
  gap: 28px;
  width: 100%;
  max-width: 980px;
}

.auth-brand-card {
  flex: 1 1 380px;
  max-width: 460px;
  min-width: 280px;
  min-height: 480px;
  position: relative;
  padding: 36px 32px 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.45),
    0 2px 12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
  position: relative;
  z-index: 2;

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
    text-shadow: 0 1px 12px rgba(0, 0, 0, 0.35);
  }
}

.brand-showcase {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  margin-top: 8px;
}

.brand-characters-panel {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  max-width: 340px;
  height: 90%;
  min-height: 220px;
  max-height: 300px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
  pointer-events: none;
}

.brand-characters-layer {
  position: relative;
  z-index: 1;
  width: 100%;
}

// ── 右侧表单独立白卡片 ─────────────────────────────────────────────────────
.auth-form-card {
  width: 400px;
  flex: 0 1 400px;
  padding: 60px 36px 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.28),
    0 2px 12px rgba(0, 0, 0, 0.12);
}

.pwd-toggle {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  color: #909399;
  padding: 0 4px;
  margin-right: -4px;

  &:hover {
    color: #303133;
  }
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

  .auth-layout {
    flex-direction: column;
    max-width: 480px;
  }

  .auth-brand-card {
    min-height: auto;
    padding: 28px 24px 32px;
  }

  .brand-showcase {
    min-height: 200px;
  }

  .auth-form-card {
    width: 100%;
    flex: 1 1 auto;
    padding: 28px 24px;
  }
}
</style>

<template>
  <div class="auth-page">
    <!-- 三维画布背景 -->
    <BgCubeCanvas />

    <!-- 左右分离：左侧品牌+小人卡片，右侧表单卡片 -->
    <div class="auth-layout">
      <aside class="auth-brand-card">
        <div class="brand-logo">
          <img :src="logowUrl" alt="Flowly" />
          <span>Flowly</span>
        </div>

        <div class="brand-showcase">
          <!-- 文字内容在上 -->
          <div class="brand-text-block">
            <p class="brand-tagline">用自然语言，构建智能工作流</p>
            <p class="brand-sub">AI 驱动的可视化自动化平台</p>
            <div class="brand-features">
              <div class="brand-feature-item">
                <span class="feature-dot" />
                <span>拖拽式流程编排</span>
              </div>
              <div class="brand-feature-item">
                <span class="feature-dot" />
                <span>多模型灵活切换</span>
              </div>
              <div class="brand-feature-item">
                <span class="feature-dot" />
                <span>实时执行监控</span>
              </div>
            </div>
          </div>

          <!-- 插画区域在下，卡通人物嵌入灰色方框内 -->
          <div class="brand-characters-panel">
            <AuthAnimatedCharacters
              class="brand-characters-layer"
              :is-typing="charTyping"
              :show-password="charShowPassword"
              :password-length="charPasswordLength"
            />
          </div>
        </div>
      </aside>

      <section class="auth-form-card">
        <!-- 返回首页 -->
        <button class="back-btn" @click="router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </button>

        <!-- 登录/注册切换（忘记密码时隐藏） -->
        <div v-show="activeTab !== 'forgot'" class="auth-tabs">
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

        <!-- 忘记密码：返回登录 -->
        <div v-show="activeTab === 'forgot'" class="forgot-toolbar">
          <button type="button" class="back-btn ghost" @click="switchTab('login')">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回登录</span>
          </button>
        </div>

        <!-- 登录表单 -->
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

            <div class="forgot-inline">
              <button type="button" class="text-link" @click="switchTab('forgot')">忘记密码？</button>
            </div>

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

          <!-- 第三方登录 -->
          <div class="social-login-section">
            <div class="social-divider">
              <span>或</span>
            </div>
            <div class="social-icons">
              <button
                class="social-btn"
                title="GitHub"
                :disabled="social.isLoggingIn.github"
                @click="handleSocialLogin('github')"
              >
                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                  <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
                </svg>
              </button>
              <button
                class="social-btn"
                title="Google"
                :disabled="social.isLoggingIn.google"
                @click="handleSocialLogin('google')"
              >
                <svg viewBox="0 0 24 24" width="22" height="22">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              </button>
              <button
                class="social-btn"
                title="QQ"
                :disabled="social.isLoggingIn.qq"
                @click="handleSocialLogin('qq')"
              >
                <img src="@/assets/images/QQ.png" alt="QQ" width="22" height="22" />
              </button>
            </div>
          </div>
        </div>

        <!-- 注册表单 -->
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

            <el-form-item label="邮箱验证码" prop="email_verification_code">
              <div class="email-code-row">
                <el-input
                  v-model="registerForm.email_verification_code"
                  maxlength="4"
                  placeholder="4 位数字（后台已配置 FLOWLY_SMTP 时必填）"
                  size="large"
                  inputmode="numeric"
                  @keyup.enter="handleRegister"
                />
                <el-button
                  size="large"
                  :disabled="registerCodeCooldown > 0 || registerSendCodeLoading"
                  :loading="registerSendCodeLoading"
                  @click="handleSendRegisterCode"
                >
                  {{ registerCodeCooldown > 0 ? `${registerCodeCooldown}s` : '获取验证码' }}
                </el-button>
              </div>
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
                placeholder="由管理员在后台「接入配置」设置邀请码后提供"
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

        <!-- 忘记密码 -->
        <div v-show="activeTab === 'forgot'" class="form-wrapper">
          <div class="form-heading">
            <h2>重置密码</h2>
            <p>通过注册邮箱收取验证码后设置新密码</p>
          </div>

          <el-form
            ref="forgotFormRef"
            :model="forgotForm"
            :rules="forgotRules"
            label-position="top"
            @submit.prevent="handleForgotSubmit"
          >
            <el-form-item label="邮箱" prop="email">
              <el-input
                v-model="forgotForm.email"
                type="email"
                placeholder="注册时使用的邮箱"
                size="large"
                :prefix-icon="Message"
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
              />
            </el-form-item>

            <el-form-item label="邮箱验证码" prop="code">
              <div class="email-code-row">
                <el-input
                  v-model="forgotForm.code"
                  maxlength="4"
                  placeholder="4 位数字"
                  size="large"
                  inputmode="numeric"
                />
                <el-button
                  size="large"
                  :disabled="forgotCodeCooldown > 0 || forgotSendCodeLoading"
                  :loading="forgotSendCodeLoading"
                  @click="handleSendForgotCode"
                >
                  {{ forgotCodeCooldown > 0 ? `${forgotCodeCooldown}s` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="forgotForm.new_password"
                type="password"
                placeholder="至少 8 个字符"
                size="large"
                :prefix-icon="Lock"
                show-password
                @focus="onAuthFieldFocus"
                @blur="onAuthFieldBlur"
              />
            </el-form-item>

            <el-form-item label="确认新密码" prop="new_password_confirm">
              <el-input
                v-model="forgotForm.new_password_confirm"
                type="password"
                placeholder="再次输入新密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleForgotSubmit"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="forgotLoading"
                class="submit-btn"
                @click="handleForgotSubmit"
              >
                重置密码
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, ArrowLeft, View, Hide } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useSocialStore, type OAuthProvider } from '@/stores/social'
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
const social = useSocialStore()

const base = (import.meta.env.BASE_URL || '/').toString()
const logowUrl = computed(() => `${base}logow.png`)

// ── Tab 状态 ──────────────────────────────────────────────────────────────
const activeTab = ref<'login' | 'register' | 'forgot'>('login')

function switchTab(tab: 'login' | 'register' | 'forgot') {
  activeTab.value = tab
}

const registerCooldownIntervalId = ref<number | null>(null)
const forgotCooldownIntervalId = ref<number | null>(null)

onUnmounted(() => {
  if (registerCooldownIntervalId.value != null) window.clearInterval(registerCooldownIntervalId.value)
  if (forgotCooldownIntervalId.value != null) window.clearInterval(forgotCooldownIntervalId.value)
})

function startCooldown(seconds: number, cooldownRef: Ref<number>, intervalRef: Ref<number | null>) {
  cooldownRef.value = seconds
  if (intervalRef.value != null) window.clearInterval(intervalRef.value)
  intervalRef.value = window.setInterval(() => {
    cooldownRef.value -= 1
    if (cooldownRef.value <= 0 && intervalRef.value != null) {
      window.clearInterval(intervalRef.value)
      intervalRef.value = null
    }
  }, 1000) as unknown as number
}

const registerSendCodeLoading = ref(false)
const registerCodeCooldown = ref(0)

async function handleSendRegisterCode() {
  const email = registerForm.email.trim()
  if (!email) {
    ElMessage.warning('请先填写邮箱')
    return
  }
  registerSendCodeLoading.value = true
  try {
    const data = await auth.sendEmailCode(email, 'register')
    ElMessage.success(data.detail || '验证码已发送')
    startCooldown(60, registerCodeCooldown, registerCooldownIntervalId)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string; message?: string } } }
    const detail = e?.response?.data?.detail ?? e?.response?.data?.message ?? '发送失败'
    ElMessage.error(detail)
  } finally {
    registerSendCodeLoading.value = false
  }
}

const forgotFormRef = ref<FormInstance>()
const forgotLoading = ref(false)
const forgotSendCodeLoading = ref(false)
const forgotCodeCooldown = ref(0)

const forgotForm = reactive({
  email: '',
  code: '',
  new_password: '',
  new_password_confirm: '',
})

const validateForgotPasswordConfirm = (
  _rule: unknown,
  value: string,
  callback: (err?: Error) => void,
) => {
  if (value !== forgotForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const forgotRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码为 4 位', trigger: 'blur' },
    { pattern: /^\d{4}$/, message: '须为数字', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' },
  ],
  new_password_confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateForgotPasswordConfirm, trigger: 'blur' },
  ],
}

async function handleSendForgotCode() {
  const email = forgotForm.email.trim()
  if (!email) {
    ElMessage.warning('请先填写邮箱')
    return
  }
  forgotSendCodeLoading.value = true
  try {
    const data = await auth.sendEmailCode(email, 'password_reset')
    ElMessage.success(data.detail || '若该邮箱已注册，将收到验证码')
    startCooldown(60, forgotCodeCooldown, forgotCooldownIntervalId)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string; message?: string } } }
    const detail = e?.response?.data?.detail ?? e?.response?.data?.message ?? '发送失败'
    ElMessage.error(detail)
  } finally {
    forgotSendCodeLoading.value = false
  }
}

async function handleForgotSubmit() {
  const valid = await forgotFormRef.value?.validate().catch(() => false)
  if (!valid) return
  forgotLoading.value = true
  try {
    const data = await auth.resetPasswordConfirm({
      email: forgotForm.email.trim(),
      code: forgotForm.code.trim(),
      new_password: forgotForm.new_password,
      new_password_confirm: forgotForm.new_password_confirm,
    })
    ElMessage.success(data.detail || '密码已重置')
    switchTab('login')
    loginForm.username = ''
    forgotForm.email = ''
    forgotForm.code = ''
    forgotForm.new_password = ''
    forgotForm.new_password_confirm = ''
  } catch (err: unknown) {
    const e = err as { response?: { data?: { detail?: string; message?: string } } }
    const detail = e?.response?.data?.detail ?? e?.response?.data?.message ?? '重置失败'
    ElMessage.error(detail)
  } finally {
    forgotLoading.value = false
  }
}

// ── 登录 ──────────────────────────────────────────────────────────────────
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

// ── 第三方登录 ────────────────────────────────────────────────────────────────

async function handleSocialLogin(provider: OAuthProvider) {
  try {
    await social.loginWithPopup(provider)
    const redirect = route.query.redirect as string
    router.push(redirect || '/dashboard')
  } catch {
    // 错误消息已在 store 中显示
  }
}

// ── 注册 ────────────────────────────────────────────────────────────────
const registerFormRef = ref<FormInstance>()
const registerLoading = ref(false)
const registerForm = reactive({
  username: '',
  email: '',
  email_verification_code: '',
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

const validateRegisterEmailCode = (_rule: unknown, value: string, callback: (err?: Error) => void) => {
  const v = (value || '').trim()
  if (!v) {
    callback()
    return
  }
  if (!/^\d{4}$/.test(v)) {
    callback(new Error('验证码须为 4 位数字'))
    return
  }
  callback()
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
  email_verification_code: [{ validator: validateRegisterEmailCode, trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' },
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePasswordConfirm, trigger: 'blur' },
  ],
}

const charPasswordLength = computed(() => {
  if (activeTab.value === 'login') return loginForm.password.length
  if (activeTab.value === 'register') return registerForm.password.length
  return forgotForm.new_password.length
})

/** 与 index.html 中小人逻辑一致：用于「明文/密文」与偷看动效 */
const charShowPassword = computed(() => {
  if (activeTab.value === 'login') return loginPwdVisible.value
  if (activeTab.value === 'forgot') return false
  return registerPwdVisible.value || registerConfirmPwdVisible.value
})

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
      email_verification_code: registerForm.email_verification_code.trim(),
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

// ── 背景 ─────────────────────────────────────────────────────────────
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
  min-height: 580px;
  position: relative;
  padding: 36px 32px 40px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.13);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow:
    0 12px 48px rgba(0, 0, 0, 0.45),
    0 2px 12px rgba(0, 0, 0, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  overflow: hidden;

  // Top gradient accent line
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 20%;
    right: 20%;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(108, 63, 245, 0.7) 30%,
      rgba(108, 63, 245, 0.9) 50%,
      rgba(108, 63, 245, 0.7) 70%,
      transparent 100%
    );
  }
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
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  min-height: 320px;
  margin-top: 8px;
}

.brand-text-block {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 0 12px 16px;
  flex-shrink: 0;
}

.brand-characters-panel {
  position: relative;
  z-index: 1;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: rgba(255, 255, 255, 0.45);
  border-radius: 14px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    inset 0 -1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
  flex-shrink: 0;
  margin-top: 4px;
}

.brand-characters-layer {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-tagline {
  font-size: 15px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
  margin: 0 0 6px;
  letter-spacing: -0.2px;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.3);
}

.brand-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  margin: 0 0 10px;
  letter-spacing: 0.2px;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 12px;
  width: 100%;
}

.brand-feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  font-weight: 500;
}

.feature-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #6C3FF5;
  flex-shrink: 0;
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

// ── 返回按钮 ────────────────────────────────────────────────────────────
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

  &.ghost {
    position: static;
    margin-bottom: 0;
  }
}

.forgot-toolbar {
  margin-bottom: 20px;
  padding-top: 4px;
}

.email-code-row {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: stretch;

  :deep(.el-input) {
    flex: 1;
    min-width: 0;
  }
}

.forgot-inline {
  margin: -8px 0 12px;
  text-align: right;
}

.text-link {
  background: none;
  border: none;
  color: #6c3ff5;
  cursor: pointer;
  font-size: 13px;
  padding: 0;

  &:hover {
    text-decoration: underline;
  }
}

// ── Tab 切换 ───────────────────────────────────────────────────────────
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

// ── 表单 ──────────────────────────────────────────────────────────────────
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

// ── 第三方登录 ───────────────────────────────────────────────────────────
.social-login-section {
  margin-top: 24px;
}

.social-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(0, 0, 0, 0.1);
  }

  span {
    font-size: 12px;
    color: rgba(0, 0, 0, 0.4);
    white-space: nowrap;
  }
}

.social-icons {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.social-btn {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #333;

  &:hover {
    background: rgba(255, 255, 255, 0.98);
    border-color: rgba(0, 0, 0, 0.2);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &:active {
    transform: translateY(0);
  }
}

// ── 响应式 ─────────────────────────────────────────────────────────────
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
    min-height: auto;
  }

  .brand-characters-panel {
    aspect-ratio: 1 / 1;
  }

  .auth-form-card {
    width: 100%;
    flex: 1 1 auto;
    padding: 28px 24px;
  }
}
</style>

/* 深色主题覆盖 - 必须放在 scoped 样式之外 */
<style>
/* 深色主题下 AuthPage 整体背景 */
html.theme-dark .auth-page {
  background: #0d0f14;
}

/* 深色主题下左侧品牌卡片 */
html.theme-dark .auth-brand-card {
  background: rgba(20, 23, 32, 0.85) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

html.theme-dark .brand-logo span {
  color: #f0f2f8;
}

html.theme-dark .brand-tagline {
  color: rgba(240, 242, 248, 0.92);
}

html.theme-dark .brand-sub {
  color: rgba(240, 242, 248, 0.55);
}

html.theme-dark .brand-feature-item {
  color: rgba(240, 242, 248, 0.72);
}

html.theme-dark .brand-characters-panel {
  background: rgba(255, 255, 255, 0.08) !important;
}

html.theme-dark .brand-characters-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(13, 15, 20, 0.3);
  pointer-events: none;
  z-index: 0;
}

/* 深色主题下右侧表单卡片 - 使用更高优先级 */
html.theme-dark .auth-form-card {
  background: rgba(20, 23, 32, 0.95) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
}

html.theme-dark .back-btn {
  color: rgba(240, 242, 248, 0.5);
}

html.theme-dark .back-btn:hover {
  color: #f0f2f8;
  background: rgba(255, 255, 255, 0.08);
}

/* Tab 切换 */
html.theme-dark .auth-tabs {
  background: rgba(255, 255, 255, 0.06) !important;
}

html.theme-dark .auth-tab {
  color: rgba(240, 242, 248, 0.5) !important;
}

html.theme-dark .auth-tab.active {
  color: #f0f2f8 !important;
}

html.theme-dark .tab-indicator {
  background: #1c2030 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
}

/* 表单标题 */
html.theme-dark .form-heading h2 {
  color: #f0f2f8 !important;
}

html.theme-dark .form-heading p {
  color: rgba(240, 242, 248, 0.55) !important;
}

/* 分隔线 - 使用最高优先级 */
html.theme-dark .auth-page .social-divider::before,
html.theme-dark .auth-page .social-divider::after {
  background: rgba(255, 255, 255, 0.12) !important;
}

html.theme-dark .auth-page .social-divider span {
  color: rgba(240, 242, 248, 0.5) !important;
}

/* 社交登录按钮 - 深色主题下用亮色背景 */
html.theme-dark .auth-page .social-btn {
  background: rgba(255, 255, 255, 0.15) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  color: #f0f2f8 !important;
}

html.theme-dark .auth-page .social-btn:hover {
  background: rgba(255, 255, 255, 0.25) !important;
  border-color: rgba(255, 255, 255, 0.35) !important;
}

/* Element Plus 表单标签 */
html.theme-dark .auth-form-card .el-form-item__label {
  color: rgba(240, 242, 248, 0.7) !important;
}

/* 密码切换图标 */
html.theme-dark .pwd-toggle {
  color: rgba(240, 242, 248, 0.4) !important;
}

html.theme-dark .pwd-toggle:hover {
  color: rgba(240, 242, 248, 0.7) !important;
}
</style>

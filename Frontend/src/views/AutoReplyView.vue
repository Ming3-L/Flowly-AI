<template>
  <div class="auto-reply-page">
    <header class="page-head">
      <h1>AI 自动回复</h1>
      <div v-if="whoami" class="whoami">当前用户：{{ whoami }}</div>
      <p class="sub">
        Vue 页面 + 服务端入库；规则支持自定义系统提示或「人格 / 情景」预设（与参考项目键一致）。任务在后台执行，数据存数据库。
      </p>
      <p class="sub sub2">
        原 Tk 四页（配置 / 好友风格 / 资料库 / 监控）已并入下方标签；<code>config.json</code>、聊天记录、资料与日志均入库。权重
        <code>best.pt</code> 填「YOLO 权重路径」或由环境变量 <code>FLOWLY_SCREEN_YOLO_WEIGHTS</code> 指定。导入旧配置：
        <code>python manage.py import_auto_reply_config path/to/config.json</code>。
      </p>
    </header>

    <el-tabs v-model="mainTab" class="main-tabs" @tab-change="onMainTabChange">
      <el-tab-pane label="总览" name="overview">
    <el-row :gutter="20">
      <el-col :xs="24" :md="9">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-hdr">
              <span>回复规则</span>
              <el-button type="primary" size="small" @click="openCreateRule">新建</el-button>
            </div>
          </template>
          <el-table :data="rules" size="small" stripe empty-text="暂无规则，请先新建">
            <el-table-column prop="name" label="名称" min-width="88" show-overflow-tooltip />
            <el-table-column label="预设" min-width="100" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.personality_key || row.scene_key" class="preset-cell">
                  {{ row.personality_key || '—' }} / {{ row.scene_key || '—' }}
                </span>
                <span v-else class="preset-cell muted">自定义提示</span>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" @change="() => toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="right">
              <template #default="{ row }">
                <el-button type="danger" link size="small" @click="removeRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="15">
        <el-card shadow="never" class="card">
          <template #header>生成回复</template>
          <el-form label-position="top">
            <el-form-item label="选用规则（可选）">
              <el-select
                v-model="selectedRuleId"
                clearable
                placeholder="不选则使用内置默认说明；选中的规则须已启用"
                style="width: 100%"
              >
                <el-option
                  v-for="r in activeRules"
                  :key="r.id"
                  :label="r.name"
                  :value="r.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="对方显示名（可选，用于按好友筛选资料库）">
              <el-input v-model="tryFriendName" maxlength="128" placeholder="与监听名单一致，可留空" clearable />
            </el-form-item>
            <el-form-item label="客户 / 对方消息">
              <el-input v-model="tryMessage" type="textarea" :rows="6" placeholder="粘贴需要回复的内容…" />
            </el-form-item>
            <el-button type="primary" :loading="sending" :disabled="!tryMessage.trim()" @click="runGenerate">
              生成回复
            </el-button>
          </el-form>

          <div v-if="lastJob" class="result-block">
            <div class="result-meta">
              <span>任务 #{{ lastJob.id }}</span>
              <el-tag size="small" :type="statusTag(lastJob.status)">{{ lastJob.status }}</el-tag>
              <span v-if="lastJob.model_key_used" class="model-used">模型: {{ lastJob.model_key_used }}</span>
            </div>
            <div v-if="lastJob.reply_text" class="reply-box" v-html="escapeHtml(lastJob.reply_text).replace(/\n/g, '<br>')" />
            <div v-else-if="lastJob.status === 'pending' || lastJob.status === 'processing'" class="hint">生成中，请稍候…</div>
            <el-alert v-if="lastJob.error_message" type="error" :closable="false" :title="lastJob.error_message" />
          </div>
        </el-card>

        <el-card shadow="never" class="card mt">
          <template #header>最近记录</template>
          <el-table :data="jobs" size="small" stripe max-height="360" empty-text="暂无任务">
            <el-table-column prop="id" label="#" width="56" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="input_text" label="输入摘要" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                {{ snippet(row.input_text) }}
              </template>
            </el-table-column>
            <el-table-column prop="reply_text" label="回复摘要" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                {{ snippet(row.reply_text) }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
      </el-tab-pane>

      <el-tab-pane label="配置选项" name="layout">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-hdr">
              <span>配置选项（坐标与软件）</span>
              <div>
                <el-button size="small" :loading="regionDetectLoading" @click="requestRegionDetect">请求本机识别并写回区域</el-button>
                <el-button type="primary" size="small" :loading="screenSaving" @click="() => saveScreenProfile()">保存配置</el-button>
              </div>
            </div>
          </template>
          <el-form label-position="top" class="screen-form">
            <el-row :gutter="16">
              <el-col :xs="24" :sm="8">
                <el-form-item label="选择聊天软件">
                  <el-select v-model="screenForm.chat_software" style="width: 100%">
                    <el-option label="微信" value="wechat" />
                    <el-option label="QQ" value="qq" />
                    <el-option label="TIM" value="tim" />
                    <el-option label="其他" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="8">
                <el-form-item label="检测间隔（秒）">
                  <el-input-number v-model="screenForm.check_interval_seconds" :min="1" :max="600" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="8">
                <el-form-item label="默认规则（可选）">
                  <el-select v-model="screenForm.default_rule_id" clearable placeholder="不选则无" style="width: 100%">
                    <el-option v-for="r in rules" :key="r.id" :label="r.name" :value="r.id" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="启用 YOLO 区域检测">
              <el-switch v-model="screenForm.use_yolo" />
            </el-form-item>
            <p class="box-hint">各区域为 x1, y1, x2, y2，与参考「更新聊天窗口」/ config.json 字段一致。</p>
            <el-form-item label="聊天区域 chat_window_box">
              <div class="coord-row">
                <el-input-number v-for="i in [0, 1, 2, 3]" :key="'cw' + i" v-model="nbox.chat_window[i]" :min="0" :step="1" controls-position="right" class="coord-num" />
              </div>
              <el-input v-model="screenBoxes.chat_window" class="coord-str" placeholder="或逗号分隔" clearable @blur="syncNboxFromStrings" />
            </el-form-item>
            <el-form-item label="用户名区域 user_name_box">
              <div class="coord-row">
                <el-input-number v-for="i in [0, 1, 2, 3]" :key="'un' + i" v-model="nbox.user_name[i]" :min="0" :step="1" controls-position="right" class="coord-num" />
              </div>
              <el-input v-model="screenBoxes.user_name" class="coord-str" placeholder="或逗号分隔" clearable @blur="syncNboxFromStrings" />
            </el-form-item>
            <el-form-item label="好友列表区域 friend_list_box">
              <div class="coord-row">
                <el-input-number v-for="i in [0, 1, 2, 3]" :key="'fl' + i" v-model="nbox.friend_list[i]" :min="0" :step="1" controls-position="right" class="coord-num" />
              </div>
              <el-input v-model="screenBoxes.friend_list" class="coord-str" placeholder="或逗号分隔" clearable @blur="syncNboxFromStrings" />
            </el-form-item>
            <el-form-item label="输入框区域 input_box_pos">
              <div class="coord-row">
                <el-input-number v-for="i in [0, 1, 2, 3]" :key="'ip' + i" v-model="nbox.input_box[i]" :min="0" :step="1" controls-position="right" class="coord-num" />
              </div>
              <el-input v-model="screenBoxes.input_box" class="coord-str" placeholder="或逗号分隔" clearable @blur="syncNboxFromStrings" />
            </el-form-item>
            <el-alert type="info" :closable="false" show-icon>
              <template #title>本机代理</template>
              <pre class="cmd-pre">cd Backend
$env:FLOWLY_API_BASE="http://127.0.0.1:8000/api"
$env:FLOWLY_ACCESS_TOKEN="你的JWT"
python -m ai_engine.desktop_screen_agent</pre>
            </el-alert>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="好友与风格" name="friends">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-hdr">
              <span>好友与 AI 设定</span>
              <el-button type="primary" size="small" :loading="screenSaving" @click="() => saveScreenProfile()">保存</el-button>
            </div>
          </template>
          <p class="box-hint">与参考「聊天风格设置」一致：按好友名存人格/情景/自定义提示；监听名单在「监控界面」管理。</p>
          <el-button size="small" class="mb8" @click="openFriendDialog()">添加好友配置</el-button>
          <el-table :data="friendTableRows" size="small" stripe empty-text="暂无好友配置">
            <el-table-column prop="name" label="好友名称" min-width="100" />
            <el-table-column prop="personality_key" label="人格" min-width="120" show-overflow-tooltip />
            <el-table-column prop="scene_key" label="情景" min-width="120" show-overflow-tooltip />
            <el-table-column label="提示词" width="88">
              <template #default="{ row }">
                {{ row.custom_system_prompt ? '自定义' : '默认' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openFriendDialog(row.name)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="资料库" name="knowledge">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-hdr">
              <span>资料库（入库替代 knowledge/ 目录）</span>
              <el-button type="primary" size="small" :loading="screenSaving" @click="saveKnowledgeSwitch">应用资料开关</el-button>
            </div>
          </template>
          <el-form label-position="top">
            <el-form-item label="合并「好友与风格」里挂载的资料；触发关键词非空则仅命中时挂载；关键词全空则每条消息都可挂载（总开关）">
              <el-switch v-model="screenForm.knowledge_reply_enabled" />
            </el-form-item>
          </el-form>
          <el-button type="primary" size="small" class="mb8" @click="openKbDialog()">新建资料条目</el-button>
          <el-table :data="kbEntries" size="small" stripe max-height="360" empty-text="暂无资料">
            <el-table-column prop="title" label="标题" min-width="100" show-overflow-tooltip />
            <el-table-column prop="scope" label="范围" width="88" />
            <el-table-column prop="friend_name" label="好友" width="100" show-overflow-tooltip />
            <el-table-column label="关键词" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                {{ (row.trigger_keywords || []).join('；') }}
              </template>
            </el-table-column>
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" @change="() => patchKbActive(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openKbDialog(row)">编辑</el-button>
                <el-button type="danger" link size="small" @click="removeKb(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="监控界面" name="monitor">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-hdr">
              <span>监控状态</span>
              <el-button type="primary" size="small" :loading="screenSaving" @click="() => saveScreenProfile()">保存</el-button>
            </div>
          </template>
          <el-alert v-if="agentError" type="warning" :closable="false" class="mb8" :title="agentError" />
          <el-descriptions :column="2" border size="small" class="mb8">
            <el-descriptions-item label="聊天软件">{{ screenForm.chat_software || '—' }}</el-descriptions-item>
            <el-descriptions-item label="检测间隔">{{ screenForm.check_interval_seconds }}s</el-descriptions-item>
            <el-descriptions-item label="YOLO 区域检测">{{ screenForm.use_yolo ? '启用' : '关闭' }}</el-descriptions-item>
            <el-descriptions-item label="资料库合并">{{ screenForm.knowledge_reply_enabled ? '启用' : '关闭' }}</el-descriptions-item>
            <el-descriptions-item label="区域识别 nonce">{{ screenFormRegionNonce }}</el-descriptions-item>
            <el-descriptions-item label="配置更新时间">{{ screenUpdatedAt }}</el-descriptions-item>
            <el-descriptions-item label="聊天区域">{{ screenBoxes.chat_window || '未配置' }}</el-descriptions-item>
            <el-descriptions-item label="输入框区域">{{ screenBoxes.input_box || '未配置' }}</el-descriptions-item>
            <el-descriptions-item label="用户名区域">{{ screenBoxes.user_name || '未配置' }}</el-descriptions-item>
            <el-descriptions-item label="好友列表区域">{{ screenBoxes.friend_list || '未配置' }}</el-descriptions-item>
            <el-descriptions-item label="默认规则（含模型）" :span="2">
              {{ defaultRuleLabel }}
            </el-descriptions-item>
          </el-descriptions>
          <div class="mb8" style="font-weight: 600; font-size: 13px; margin: 8px 0 6px">运行检测（本机代理上报）</div>
          <el-descriptions :column="2" border size="small" class="mb8">
            <el-descriptions-item label="快照时间">
              {{ String(agentRuntimeSnapshot.updated_at || '—') }}
            </el-descriptions-item>
            <el-descriptions-item label="检测到聊天区域">
              {{ yn(agentRuntimeSnapshot.detected_chat_area) }}
            </el-descriptions-item>
            <el-descriptions-item label="检测到输入框">
              {{ yn(agentRuntimeSnapshot.detected_input_box) }}
            </el-descriptions-item>
            <el-descriptions-item label="检测到用户名区域">
              {{ yn(agentRuntimeSnapshot.detected_user_name_area) }}
            </el-descriptions-item>
            <el-descriptions-item label="检测到好友列表区域">
              {{ yn(agentRuntimeSnapshot.detected_friend_list) }}
            </el-descriptions-item>
            <el-descriptions-item label="检测到消息变化">
              {{ yn(agentRuntimeSnapshot.detected_message_change) }}
            </el-descriptions-item>
            <el-descriptions-item label="区域识别说明" :span="2">
              {{ String(agentRuntimeSnapshot.chat_area_source || '—') }}
            </el-descriptions-item>
            <el-descriptions-item label="最近 OCR 摘要" :span="2">
              <span style="white-space: pre-wrap; word-break: break-all">{{
                String(agentRuntimeSnapshot.chat_ocr_preview || '').slice(0, 600) || '—'
              }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="最近一句聊天文本" :span="2">
              {{ String(agentRuntimeSnapshot.chat_last_line || '—') }}
            </el-descriptions-item>
          </el-descriptions>
          <el-form label-position="left" label-width="120px">
            <el-form-item label="开始监控">
              <el-switch v-model="screenForm.monitoring_active" active-text="运行中" inactive-text="已暂停" />
            </el-form-item>
            <el-form-item label="本机进程">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <el-tag size="small" :type="agentRunning ? 'success' : 'info'">
                  {{ agentRunning ? `运行中 PID=${agentPid ?? '-'}` : '未启动' }}
                </el-tag>
                <el-button size="small" type="primary" :disabled="agentRunning" :loading="agentLoading" @click="startAgent">
                  启动
                </el-button>
                <el-button size="small" :disabled="!agentRunning" :loading="agentLoading" @click="stopAgent">
                  停止
                </el-button>
                <el-button size="small" :loading="agentLoading" @click="refreshAgentStatus">
                  刷新状态
                </el-button>
              </div>
            </el-form-item>
          </el-form>
          <p class="box-hint">本机代理拉取该开关；关闭时仅低频轮询配置。</p>
        </el-card>
        <el-card shadow="never" class="card mt">
          <template #header>
            <div class="card-hdr">
              <span>自动回复对话记录</span>
              <el-button size="small" type="primary" @click="loadMonitorHistory">刷新</el-button>
            </div>
          </template>
          <el-table :data="monitorChatHistory" size="small" stripe max-height="320" empty-text="暂无记录（成功自动回复后会写入）">
            <el-table-column prop="created_at" label="时间" width="160" />
            <el-table-column prop="friend_name" label="好友" width="120" show-overflow-tooltip />
            <el-table-column prop="role" label="角色" width="100" />
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
          </el-table>
        </el-card>
        <el-card shadow="never" class="card mt">
          <template #header>
            <div class="card-hdr">
              <span>监听好友列表</span>
              <span />
            </div>
          </template>
          <div class="tags-row mb8">
            <el-tag
              v-for="(n, idx) in screenForm.monitored_friends"
              :key="`${n}-${idx}`"
              closable
              class="tag-item"
              @close="screenForm.monitored_friends.splice(idx, 1)"
            >
              {{ n }}
            </el-tag>
            <el-input v-model="friendNameInput" class="friend-input" placeholder="回车添加监听" @keyup.enter="addMonitoredFriend" />
          </div>
          <el-table :data="monitoredFriendRows" size="small" stripe empty-text="暂无监听好友">
            <el-table-column prop="name" label="好友名称" min-width="100" />
            <el-table-column prop="personality_label" label="风格" min-width="120" />
            <el-table-column prop="scene_label" label="情景" min-width="120" />
            <el-table-column prop="rule_label" label="规则（含模型）" min-width="160" show-overflow-tooltip />
            <el-table-column prop="effective_model_key" label="实际模型 key" min-width="160" show-overflow-tooltip />
            <el-table-column label="提示词" width="88">
              <template #default="{ row }">
                {{ row.has_custom ? '自定义' : '默认' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="right">
              <template #default="{ row }">
                <el-button link size="small" @click="openFriendDialog(row.name)">配置</el-button>
                <el-button type="danger" link size="small" @click="removeMonitored(row.name)">取消监听</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleDialogVisible" title="新建规则" width="560px" destroy-on-close @closed="resetRuleForm">
      <el-form :model="ruleForm" label-position="top">
        <el-form-item label="规则名称" required>
          <el-input v-model="ruleForm.name" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="人格预设（可选）">
          <el-select v-model="ruleForm.personality_key" clearable placeholder="不选则依赖下方自定义提示" style="width: 100%">
            <el-option
              v-for="p in presetPersonalities"
              :key="p.key"
              :label="p.label"
              :value="p.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="沟通情景（可选）">
          <el-select v-model="ruleForm.scene_key" clearable placeholder="不选则依赖下方自定义提示" style="width: 100%">
            <el-option
              v-for="s in presetScenes"
              :key="s.key"
              :label="s.label"
              :value="s.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义系统提示（可选；填写后将覆盖人格/情景组合）">
          <el-input v-model="ruleForm.system_prompt" type="textarea" :rows="6" placeholder="留空且已选人格/情景时，由服务端按预设生成系统提示" />
        </el-form-item>
        <el-form-item label="模型（可选，使用项目内「语言/文本」模型目录）">
          <el-select
            v-model="ruleForm.model_key"
            filterable
            clearable
            placeholder="留空则用服务端 FLOWLY_AUTO_REPLY_MODEL_KEY"
            style="width: 100%"
          >
            <el-option label="（留空：用服务端默认）" value="" />
            <el-option-group
              v-for="(grp, idx) in autoReplyModelGroups"
              :key="`${grp.label}-${idx}`"
              :label="grp.label"
            >
              <el-option
                v-for="m in grp.rows"
                :key="m.key"
                :label="m.label"
                :value="m.key"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="ruleSaving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="friendDialogVisible" :title="friendDialogTitle" width="560px" destroy-on-close @closed="resetFriendForm">
      <el-form :model="friendForm" label-position="top">
        <el-form-item label="好友名称" required>
          <el-input v-model="friendForm.name" maxlength="128" :disabled="friendForm.nameLocked" />
        </el-form-item>
        <el-form-item label="触发规则（可选；用于按好友选择不同模型/提示）">
          <el-select v-model="friendForm.rule_id" clearable placeholder="默认规则（屏幕配置中的 default_rule）" style="width: 100%">
            <el-option v-for="r in activeRules" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="对话模型（可选；覆盖规则内模型，仅文本类）">
          <el-select
            v-model="friendForm.model_key"
            filterable
            clearable
            placeholder="留空则使用规则或服务端默认模型"
            style="width: 100%"
          >
            <el-option label="（留空：跟随规则/默认）" value="" />
            <el-option-group
              v-for="(grp, idx) in autoReplyModelGroups"
              :key="`ff-${grp.label}-${idx}`"
              :label="grp.label"
            >
              <el-option v-for="m in grp.rows" :key="`ff-${m.key}`" :label="m.label" :value="m.key" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="聊天风格（人格键）">
          <el-select v-model="friendForm.personality_key" clearable placeholder="默认" style="width: 100%">
            <el-option v-for="p in presetPersonalities" :key="p.key" :label="p.label" :value="p.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="聊天情景">
          <el-select v-model="friendForm.scene_key" clearable placeholder="默认" style="width: 100%">
            <el-option v-for="s in presetScenes" :key="s.key" :label="s.label" :value="s.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义系统提示（非空时覆盖上方风格+情景）">
          <el-input v-model="friendForm.custom_system_prompt" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="资料触发关键词（每行一条子串；与参考 knowledge_match_keywords 一致）">
          <el-input v-model="friendForm.keywordsText" type="textarea" :rows="4" placeholder="留空表示不限制关键词（仍受资料库总开关与条目关键词规则约束）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="friendDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveFriendOverride">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="kbDialogVisible" :title="kbEditId ? '编辑资料' : '新建资料'" width="600px" destroy-on-close>
      <el-form :model="kbForm" label-position="top">
        <el-form-item label="范围">
          <el-radio-group v-model="kbForm.scope">
            <el-radio-button label="shared">共享</el-radio-button>
            <el-radio-button label="friend">指定好友</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="kbForm.scope === 'friend'" label="好友显示名" required>
          <el-input v-model="kbForm.friend_name" maxlength="128" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="kbForm.title" maxlength="256" />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="kbForm.body" type="textarea" :rows="10" />
        </el-form-item>
        <el-form-item label="触发关键词（每行一条；全空则总开关开启时每条消息可挂载本条目）">
          <el-input v-model="kbForm.keywordsText" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="排序（小在前）">
          <el-input-number v-model="kbForm.sort_order" :min="-100" :max="1000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbSaving" @click="saveKbEntry">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

interface PresetOpt {
  key: string
  label: string
  hint?: string
}

interface Rule {
  id: number
  name: string
  system_prompt: string
  personality_key?: string
  scene_key?: string
  model_key: string
  is_active: boolean
  updated_at: string
}

interface Job {
  id: number
  status: string
  input_text: string
  reply_text: string
  error_message: string
  model_key_used: string
  rule_id: number | null
  created_at: string
  updated_at: string
}

interface ScreenProfile {
  chat_software: string
  chat_window_box: number[] | null
  input_box_pos: number[] | null
  user_name_box: number[] | null
  friend_list_box: number[] | null
  monitored_friends: string[]
  friends_overrides: Record<string, unknown>
  check_interval_seconds: number
  use_yolo: boolean
  knowledge_reply_enabled: boolean
  monitoring_active: boolean
  yolo_weights_path: string
  region_detect_nonce: number
  region_detect_ack_nonce: number
  default_rule_id: number | null
  updated_at: string
  agent_runtime_snapshot?: Record<string, unknown>
}

interface KbEntry {
  id: number
  scope: string
  friend_name: string
  title: string
  body: string
  trigger_keywords: string[]
  is_active: boolean
  sort_order: number
}

// 监控日志（AutoReplyMonitorLogLine）已下线：不再入库，也不在前端展示

interface FriendOverrideRow {
  name: string
  personality_key: string
  scene_key: string
  custom_system_prompt: string
}

interface MonitoredRow {
  name: string
  personality_label: string
  scene_label: string
  rule_label: string
  effective_model_key: string
  has_custom: boolean
}

// 监控事件（AutoReplyScreenEvent）已下线：不再入库，也不在前端展示

const mainTab = ref('overview')
const auth = useAuthStore()
const whoami = computed(() => {
  const u = auth.user as any
  if (!u) return ''
  const nm = u.username || u.email || ''
  return nm ? `${nm}（id=${u.id}）` : `id=${u.id}`
})
const rules = ref<Rule[]>([])
const jobs = ref<Job[]>([])
const selectedRuleId = ref<number | undefined>(undefined)
const tryFriendName = ref('')
const tryMessage = ref('')
const sending = ref(false)
const lastJob = ref<Job | null>(null)

const ruleDialogVisible = ref(false)
const ruleSaving = ref(false)
const ruleForm = ref({
  name: '',
  system_prompt: '',
  personality_key: '',
  scene_key: '',
  model_key: '',
})

const presetScenes = ref<PresetOpt[]>([])
const presetPersonalities = ref<PresetOpt[]>([])

type CatalogModelRow = {
  key: string
  label: string
  route: string
  api_kind?: string
  show_in_canvas_llm_nodes?: boolean
  category?: string
  category_label?: string
  category_order?: number
}

type ModelGroup = { label: string; order: number; rows: CatalogModelRow[] }

const aiModelsCatalog = ref<{ models: CatalogModelRow[] } | null>(null)

function buildGroups(rows: CatalogModelRow[]): ModelGroup[] {
  const map = new Map<string, ModelGroup>()
  for (const r of rows) {
    const cid = String(r.category ?? 'other')
    const lab = String(r.category_label ?? '其它')
    const key = `${cid}@@${lab}`
    const order = typeof r.category_order === 'number' ? r.category_order : 999
    const g = map.get(key)
    if (g) g.rows.push(r)
    else map.set(key, { label: lab, order, rows: [r] })
  }
  return [...map.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
}

const autoReplyModelGroups = computed<ModelGroup[]>(() => {
  const all = aiModelsCatalog.value?.models ?? []
  // 自动回复只需要“对话/补全”类模型（ark_chat/openai兼容等）；向量/生图等不需要
  const rows = all.filter((m) => (m.api_kind ?? 'ark_chat') === 'ark_chat')
  return buildGroups(rows)
})

const screenSaving = ref(false)
const screenForm = ref({
  chat_software: 'wechat',
  check_interval_seconds: 3,
  use_yolo: true,
  knowledge_reply_enabled: false,
  monitoring_active: false,
  yolo_weights_path: '',
  default_rule_id: undefined as number | undefined,
  monitored_friends: [] as string[],
  friends_overrides: {} as Record<string, unknown>,
})
const screenBoxes = ref({
  chat_window: '',
  input_box: '',
  user_name: '',
  friend_list: '',
})
const friendNameInput = ref('')
// 屏幕事件/监控日志相关前端数据结构已移除
const kbEntries = ref<KbEntry[]>([])
const regionDetectLoading = ref(false)
const agentRunning = ref(false)
const agentPid = ref<number | null>(null)
const agentLoading = ref(false)
const agentError = ref('')
const agentRuntimeSnapshot = ref<Record<string, unknown>>({})

interface MonitorChatHistRow {
  id: number
  friend_name: string
  role: string
  content: string
  created_at: string
}

const monitorChatHistory = ref<MonitorChatHistRow[]>([])

function yn(v: unknown): string {
  return v === true || v === 'true' || v === 1 ? '是' : '否'
}

const nbox = reactive({
  chat_window: [0, 0, 0, 0],
  user_name: [0, 0, 0, 0],
  friend_list: [0, 0, 0, 0],
  input_box: [0, 0, 0, 0],
})

const friendDialogVisible = ref(false)
const friendForm = ref({
  name: '',
  nameLocked: false,
  rule_id: undefined as number | undefined,
  model_key: '',
  personality_key: '',
  scene_key: '',
  custom_system_prompt: '',
  keywordsText: '',
})

const kbDialogVisible = ref(false)
const kbSaving = ref(false)
const kbEditId = ref<number | null>(null)
const kbForm = ref({
  scope: 'shared' as 'shared' | 'friend',
  friend_name: '',
  title: '',
  body: '',
  keywordsText: '',
  sort_order: 0,
})

const activeRules = computed(() => rules.value.filter((r) => r.is_active))

const screenProfileUpdatedAt = ref('')
const screenProfileNonce = ref(0)
const screenProfileAckNonce = ref(0)

const screenUpdatedAt = computed(
  () => (screenProfileUpdatedAt.value || '').slice(0, 19).replace('T', ' ') || '—'
)
const screenFormRegionNonce = computed(
  () => `${screenProfileNonce.value}/${screenProfileAckNonce.value}`
)

const defaultRuleLabel = computed(() => {
  const rid = Number(screenForm.value.default_rule_id || 0) || 0
  if (!rid) return '（未设置：由服务端默认/好友覆盖决定）'
  const r = rules.value.find((x) => x.id === rid)
  if (!r) return `规则#${rid}`
  return `${r.name}${r.model_key ? `（${r.model_key}）` : '（使用服务端默认模型）'}`
})

function ruleLabelById(id: number) {
  const r = rules.value.find((x) => x.id === id)
  return r ? r.name : `规则#${id}`
}

const friendDialogTitle = computed(() => (friendForm.value.nameLocked ? '编辑好友' : '添加好友配置'))

const friendTableRows = computed<FriendOverrideRow[]>(() => {
  const fo = screenForm.value.friends_overrides as Record<string, Record<string, unknown>>
  return Object.keys(fo || {}).map((name) => {
    const o = fo[name] || {}
    return {
      name,
      personality_key: String(o.personality || o.personality_key || ''),
      scene_key: String(o.scene || o.scene_key || ''),
      custom_system_prompt: String(o.custom_system_prompt || ''),
    }
  })
})

function presetPersonalityLabel(key: string) {
  const p = presetPersonalities.value.find((x) => x.key === key)
  return p ? p.label : key || '—'
}

function presetSceneLabel(key: string) {
  const s = presetScenes.value.find((x) => x.key === key)
  return s ? s.label : key || '—'
}

const monitoredFriendRows = computed<MonitoredRow[]>(() => {
  return (screenForm.value.monitored_friends || []).map((name) => {
    const fo = screenForm.value.friends_overrides as Record<string, Record<string, unknown>>
    const o = fo[name] || {}
    const pk = String(o.personality || o.personality_key || '')
    const sk = String(o.scene || o.scene_key || '')
    const rid = Number(o.rule_id || 0) || 0
    const rule = rid ? rules.value.find((x) => x.id === rid) : null
    const defRid = Number(screenForm.value.default_rule_id || 0) || 0
    const defRule = !rid && defRid ? rules.value.find((x) => x.id === defRid) : null
    const directMk = String(o.model_key || '').trim()
    const effectiveModelKey =
      directMk ||
      (rule?.model_key || '').trim() ||
      (defRule?.model_key || '').trim() ||
      '（服务端默认：FLOWLY_AUTO_REPLY_MODEL_KEY）'
    return {
      name,
      personality_label: presetPersonalityLabel(pk),
      scene_label: presetSceneLabel(sk),
      rule_label: directMk
        ? `好友直选模型（${directMk}）`
        : rid
          ? `${ruleLabelById(rid)}${rule?.model_key ? `（${rule.model_key}）` : '（服务端默认模型）'}`
          : defRule
            ? `${ruleLabelById(defRid)}${defRule.model_key ? `（${defRule.model_key}）` : '（服务端默认模型）'}`
            : '默认规则（服务端默认模型）',
      effective_model_key: effectiveModelKey,
      has_custom: !!String(o.custom_system_prompt || '').trim(),
    }
  })
})

function snippet(s: string) {
  const t = (s || '').replace(/\s+/g, ' ').trim()
  return t.length > 80 ? `${t.slice(0, 80)}…` : t
}

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function statusTag(s: string) {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'processing') return 'warning'
  return 'info'
}

function formatBox4(box: number[] | null | undefined): string {
  if (!box || box.length !== 4) return ''
  return box.join(', ')
}

function parseBox4(s: string): number[] | null {
  const parts = s
    .split(/[,，\s]+/)
    .map((x) => x.trim())
    .filter(Boolean)
  if (parts.length !== 4) return null
  const nums = parts.map((p) => Number(p))
  if (nums.some((n) => Number.isNaN(n))) return null
  return nums
}

function fillNboxFromArrays(
  key: 'chat_window' | 'user_name' | 'friend_list' | 'input_box',
  box: number[] | null | undefined,
) {
  const arr = nbox[key]
  if (box && box.length === 4) {
    for (let i = 0; i < 4; i++) arr[i] = Number(box[i]) || 0
  } else {
    for (let i = 0; i < 4; i++) arr[i] = 0
  }
}

function syncNboxFromStrings() {
  (['chat_window', 'user_name', 'friend_list', 'input_box'] as const).forEach((k) => {
    const s =
      k === 'chat_window'
        ? screenBoxes.value.chat_window
        : k === 'user_name'
          ? screenBoxes.value.user_name
          : k === 'friend_list'
            ? screenBoxes.value.friend_list
            : screenBoxes.value.input_box
    const p = parseBox4(s.trim())
    fillNboxFromArrays(k, p)
  })
}

function boxFromNboxOrString(n: number[], s: string): number[] | null {
  if (n.some((x) => x !== 0)) {
    return [Math.round(n[0]), Math.round(n[1]), Math.round(n[2]), Math.round(n[3])]
  }
  const t = s.trim()
  if (!t) return null
  return parseBox4(t)
}

function applyScreenProfile(p: ScreenProfile) {
  screenForm.value = {
    chat_software: p.chat_software || 'wechat',
    check_interval_seconds: p.check_interval_seconds ?? 3,
    use_yolo: p.use_yolo !== false,
    knowledge_reply_enabled: !!p.knowledge_reply_enabled,
    monitoring_active: !!p.monitoring_active,
    yolo_weights_path: p.yolo_weights_path || '',
    default_rule_id: p.default_rule_id ?? undefined,
    monitored_friends: Array.isArray(p.monitored_friends) ? [...p.monitored_friends] : [],
    friends_overrides: p.friends_overrides && typeof p.friends_overrides === 'object' ? { ...p.friends_overrides } : {},
  }
  screenBoxes.value = {
    chat_window: formatBox4(p.chat_window_box),
    input_box: formatBox4(p.input_box_pos),
    user_name: formatBox4(p.user_name_box),
    friend_list: formatBox4(p.friend_list_box),
  }
  screenProfileUpdatedAt.value = p.updated_at || ''
  screenProfileNonce.value = Number(p.region_detect_nonce || 0) || 0
  screenProfileAckNonce.value = Number(p.region_detect_ack_nonce || 0) || 0
  fillNboxFromArrays('chat_window', p.chat_window_box)
  fillNboxFromArrays('user_name', p.user_name_box)
  fillNboxFromArrays('friend_list', p.friend_list_box)
  fillNboxFromArrays('input_box', p.input_box_pos)
  agentRuntimeSnapshot.value =
    p.agent_runtime_snapshot && typeof p.agent_runtime_snapshot === 'object'
      ? { ...p.agent_runtime_snapshot }
      : {}
}

async function loadScreenProfile() {
  const { data } = await api.get<ScreenProfile>('/auto-reply/screen-profile')
  applyScreenProfile(data)
}

async function refreshAgentStatus() {
  agentLoading.value = true
  agentError.value = ''
  try {
    const { data } = await api.get<{ running: boolean; pid: number | null }>('/auto-reply/agent/status')
    agentRunning.value = !!data.running
    agentPid.value = data.pid ?? null
    await loadScreenProfile()
    await loadMonitorHistory()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    agentError.value = err?.response?.data?.detail || '无法获取本机进程状态（后端未启动或权限不足）'
  } finally {
    agentLoading.value = false
  }
}

async function startAgent() {
  agentLoading.value = true
  agentError.value = ''
  try {
    const { data } = await api.post<{ running: boolean; pid: number | null }>('/auto-reply/agent/start')
    agentRunning.value = !!data.running
    agentPid.value = data.pid ?? null
    ElMessage.success('已启动本机进程')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    agentError.value = err?.response?.data?.detail || '启动失败'
  } finally {
    agentLoading.value = false
  }
}

async function stopAgent() {
  agentLoading.value = true
  agentError.value = ''
  try {
    await api.post('/auto-reply/agent/stop')
    agentRunning.value = false
    agentPid.value = null
    ElMessage.success('已停止本机进程')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    agentError.value = err?.response?.data?.detail || '停止失败'
  } finally {
    agentLoading.value = false
  }
}

async function saveScreenProfile(successTip: string | undefined = '屏幕配置已保存') {
  const cw = boxFromNboxOrString(nbox.chat_window, screenBoxes.value.chat_window)
  const ip = boxFromNboxOrString(nbox.input_box, screenBoxes.value.input_box)
  const un = boxFromNboxOrString(nbox.user_name, screenBoxes.value.user_name)
  const fl = boxFromNboxOrString(nbox.friend_list, screenBoxes.value.friend_list)
  for (const b of [cw, ip, un, fl]) {
    if (b && b.length !== 4) {
      ElMessage.warning('坐标须为四个有效数字')
      return
    }
  }
  screenSaving.value = true
  try {
    const { data } = await api.put<ScreenProfile>('/auto-reply/screen-profile', {
      chat_software: screenForm.value.chat_software,
      chat_window_box: cw,
      input_box_pos: ip,
      user_name_box: un,
      friend_list_box: fl,
      monitored_friends: screenForm.value.monitored_friends,
      friends_overrides: screenForm.value.friends_overrides,
      check_interval_seconds: screenForm.value.check_interval_seconds,
      use_yolo: screenForm.value.use_yolo,
      knowledge_reply_enabled: screenForm.value.knowledge_reply_enabled,
      monitoring_active: screenForm.value.monitoring_active,
      yolo_weights_path: screenForm.value.yolo_weights_path.trim(),
      default_rule_id: screenForm.value.default_rule_id ?? null,
    })
    applyScreenProfile(data)
    ElMessage.success(successTip)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    screenSaving.value = false
  }
}

function addMonitoredFriend() {
  const n = friendNameInput.value.trim()
  if (!n) return
  if (!screenForm.value.monitored_friends.includes(n)) {
    screenForm.value.monitored_friends.push(n)
  }
  friendNameInput.value = ''
}

async function loadPresets() {
  const { data } = await api.get<{ scenes: PresetOpt[]; personalities: PresetOpt[] }>('/auto-reply/presets')
  presetScenes.value = data.scenes || []
  presetPersonalities.value = data.personalities || []
}

async function loadAiModelsCatalog() {
  try {
    const { data } = await api.get<{ models: CatalogModelRow[] }>('/ai/models')
    aiModelsCatalog.value = data
  } catch {
    aiModelsCatalog.value = null
  }
}

async function loadRules() {
  const { data } = await api.get<Rule[]>('/auto-reply/rules')
  rules.value = Array.isArray(data) ? data : []
}

async function loadJobs() {
  const { data } = await api.get<Job[]>('/auto-reply/jobs', { params: { limit: 40 } })
  jobs.value = Array.isArray(data) ? data : []
}

async function pollJob(id: number) {
  for (let i = 0; i < 120; i++) {
    const { data } = await api.get<Job>(`/auto-reply/jobs/${id}`)
    lastJob.value = data
    if (data.status === 'completed' || data.status === 'failed') {
      await loadJobs()
      return
    }
    await new Promise((r) => setTimeout(r, 800))
  }
  ElMessage.warning('等待超时，请稍后刷新记录列表')
  await loadJobs()
}

async function requestRegionDetect() {
  regionDetectLoading.value = true
  try {
    await api.post<ScreenProfile>('/auto-reply/screen-profile/request-region-detect')
    ElMessage.success('已通知本机代理识别区域（请保持代理运行）')
    await loadScreenProfile()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '请求失败')
  } finally {
    regionDetectLoading.value = false
  }
}

async function loadKbEntries() {
  const { data } = await api.get<KbEntry[]>('/auto-reply/knowledge-entries')
  kbEntries.value = Array.isArray(data) ? data : []
}

function onMainTabChange(tab: string | number) {
  const t = String(tab)
  if (t === 'knowledge') void loadKbEntries()
  if (t === 'monitor') {
    void refreshAgentStatus()
    void loadScreenProfile()
    void loadMonitorHistory()
  }
}

async function loadMonitorHistory() {
  try {
    const { data } = await api.get<MonitorChatHistRow[]>('/auto-reply/chat-history?limit=40')
    monitorChatHistory.value = Array.isArray(data) ? data : []
  } catch {
    monitorChatHistory.value = []
  }
}

async function saveKnowledgeSwitch() {
  screenSaving.value = true
  try {
    const cw = boxFromNboxOrString(nbox.chat_window, screenBoxes.value.chat_window)
    const ip = boxFromNboxOrString(nbox.input_box, screenBoxes.value.input_box)
    const un = boxFromNboxOrString(nbox.user_name, screenBoxes.value.user_name)
    const fl = boxFromNboxOrString(nbox.friend_list, screenBoxes.value.friend_list)
    const { data } = await api.put<ScreenProfile>('/auto-reply/screen-profile', {
      chat_software: screenForm.value.chat_software,
      chat_window_box: cw,
      input_box_pos: ip,
      user_name_box: un,
      friend_list_box: fl,
      monitored_friends: screenForm.value.monitored_friends,
      friends_overrides: screenForm.value.friends_overrides,
      check_interval_seconds: screenForm.value.check_interval_seconds,
      use_yolo: screenForm.value.use_yolo,
      knowledge_reply_enabled: screenForm.value.knowledge_reply_enabled,
      monitoring_active: screenForm.value.monitoring_active,
      yolo_weights_path: screenForm.value.yolo_weights_path.trim(),
      default_rule_id: screenForm.value.default_rule_id ?? null,
    })
    applyScreenProfile(data)
    ElMessage.success('资料开关已保存')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    screenSaving.value = false
  }
}

function openFriendDialog(name?: string) {
  if (name) {
    const fo = screenForm.value.friends_overrides as Record<string, Record<string, unknown>>
    const o = fo[name] || {}
    friendForm.value = {
      name,
      nameLocked: true,
      rule_id: typeof o.rule_id === 'number' ? (o.rule_id as number) : undefined,
      model_key: String(o.model_key || ''),
      personality_key: String(o.personality || o.personality_key || ''),
      scene_key: String(o.scene || o.scene_key || ''),
      custom_system_prompt: String(o.custom_system_prompt || ''),
      keywordsText: Array.isArray(o.knowledge_match_keywords)
        ? (o.knowledge_match_keywords as string[]).join('\n')
        : '',
    }
  } else {
    friendForm.value = {
      name: '',
      nameLocked: false,
      rule_id: undefined,
      model_key: '',
      personality_key: '',
      scene_key: '',
      custom_system_prompt: '',
      keywordsText: '',
    }
  }
  friendDialogVisible.value = true
}

function resetFriendForm() {
  friendForm.value = {
    name: '',
    nameLocked: false,
    rule_id: undefined,
    model_key: '',
    personality_key: '',
    scene_key: '',
    custom_system_prompt: '',
    keywordsText: '',
  }
}

async function saveFriendOverride() {
  const nm = friendForm.value.name.trim()
  if (!nm) {
    ElMessage.warning('请填写好友名称')
    return
  }
  const kws = friendForm.value.keywordsText
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
  const fo = { ...(screenForm.value.friends_overrides as Record<string, unknown>) }
  fo[nm] = {
    name: nm,
    rule_id: friendForm.value.rule_id ?? null,
    model_key: friendForm.value.model_key.trim(),
    personality: friendForm.value.personality_key || 'gentle_healing',
    scene: friendForm.value.scene_key || 'daily_chat',
    custom_system_prompt: friendForm.value.custom_system_prompt.trim(),
    knowledge_paths: [],
    knowledge_match_keywords: kws,
  }
  screenForm.value.friends_overrides = fo
  friendDialogVisible.value = false
  await saveScreenProfile('好友配置已保存')
}

async function removeMonitored(name: string) {
  try {
    await ElMessageBox.confirm(`取消监听「${name}」？`, '确认', { type: 'warning' })
  } catch {
    return
  }
  screenForm.value.monitored_friends = screenForm.value.monitored_friends.filter((x) => x !== name)
  await saveScreenProfile()
}

function openKbDialog(row?: KbEntry) {
  if (row) {
    kbEditId.value = row.id
    kbForm.value = {
      scope: row.scope === 'friend' ? 'friend' : 'shared',
      friend_name: row.friend_name || '',
      title: row.title || '',
      body: row.body || '',
      keywordsText: (row.trigger_keywords || []).join('\n'),
      sort_order: row.sort_order ?? 0,
    }
  } else {
    kbEditId.value = null
    kbForm.value = {
      scope: 'shared',
      friend_name: '',
      title: '',
      body: '',
      keywordsText: '',
      sort_order: 0,
    }
  }
  kbDialogVisible.value = true
}

async function saveKbEntry() {
  if (!kbForm.value.body.trim()) {
    ElMessage.warning('请填写正文')
    return
  }
  if (kbForm.value.scope === 'friend' && !kbForm.value.friend_name.trim()) {
    ElMessage.warning('指定好友范围须填写好友名')
    return
  }
  const kws = kbForm.value.keywordsText
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
  kbSaving.value = true
  try {
    if (kbEditId.value) {
      await api.patch(`/auto-reply/knowledge-entries/${kbEditId.value}`, {
        scope: kbForm.value.scope,
        friend_name: kbForm.value.friend_name.trim(),
        title: kbForm.value.title.trim(),
        body: kbForm.value.body.trim(),
        trigger_keywords: kws,
        sort_order: kbForm.value.sort_order,
      })
    } else {
      await api.post('/auto-reply/knowledge-entries', {
        scope: kbForm.value.scope,
        friend_name: kbForm.value.friend_name.trim(),
        title: kbForm.value.title.trim(),
        body: kbForm.value.body.trim(),
        trigger_keywords: kws,
        sort_order: kbForm.value.sort_order,
        is_active: true,
      })
    }
    ElMessage.success('已保存')
    kbDialogVisible.value = false
    await loadKbEntries()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    kbSaving.value = false
  }
}

async function patchKbActive(row: KbEntry) {
  try {
    await api.patch(`/auto-reply/knowledge-entries/${row.id}`, { is_active: row.is_active })
  } catch {
    row.is_active = !row.is_active
    ElMessage.error('更新失败')
  }
}

async function removeKb(row: KbEntry) {
  try {
    await ElMessageBox.confirm('确定删除该资料条目？', '确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.delete(`/auto-reply/knowledge-entries/${row.id}`)
    ElMessage.success('已删除')
    await loadKbEntries()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function runGenerate() {
  const msg = tryMessage.value.trim()
  if (!msg) return
  sending.value = true
  lastJob.value = null
  try {
    const { data } = await api.post<Job>('/auto-reply/jobs', {
      message: msg,
      rule_id: selectedRuleId.value ?? null,
      friend_name: tryFriendName.value.trim() || undefined,
    })
    lastJob.value = data
    await pollJob(data.id)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '请求失败')
  } finally {
    sending.value = false
  }
}

async function toggleRule(row: Rule) {
  try {
    await api.patch(`/auto-reply/rules/${row.id}`, { is_active: row.is_active })
  } catch {
    row.is_active = !row.is_active
    ElMessage.error('更新失败')
  }
}

async function removeRule(row: Rule) {
  try {
    await ElMessageBox.confirm(`确定删除规则「${row.name}」？`, '确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.delete(`/auto-reply/rules/${row.id}`)
    ElMessage.success('已删除')
    if (selectedRuleId.value === row.id) selectedRuleId.value = undefined
    await loadRules()
  } catch {
    ElMessage.error('删除失败')
  }
}

function openCreateRule() {
  resetRuleForm()
  ruleDialogVisible.value = true
}

function resetRuleForm() {
  ruleForm.value = {
    name: '',
    system_prompt: '',
    personality_key: '',
    scene_key: '',
    model_key: '',
  }
}

async function saveRule() {
  if (!ruleForm.value.name.trim()) {
    ElMessage.warning('请填写规则名称')
    return
  }
  const sp = ruleForm.value.system_prompt.trim()
  const pk = (ruleForm.value.personality_key || '').trim()
  const sk = (ruleForm.value.scene_key || '').trim()
  if (!sp && !pk && !sk) {
    ElMessage.warning('请填写自定义系统提示，或至少选择人格 / 情景之一')
    return
  }
  ruleSaving.value = true
  try {
    await api.post('/auto-reply/rules', {
      name: ruleForm.value.name.trim(),
      system_prompt: sp,
      personality_key: pk,
      scene_key: sk,
      model_key: ruleForm.value.model_key.trim(),
      is_active: true,
    })
    ElMessage.success('已保存')
    ruleDialogVisible.value = false
    await loadRules()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    ruleSaving.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      loadAiModelsCatalog(),
      loadPresets(),
      loadRules(),
      loadJobs(),
      loadScreenProfile(),
      loadKbEntries(),
    ])
    await refreshAgentStatus()
  } catch {
    ElMessage.error('加载失败，请确认已登录且后端可用')
  }
})
</script>

<style scoped lang="scss">
.auto-reply-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 40px;
}

.page-head {
  margin-bottom: 20px;

  h1 {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 700;
    color: #111;
  }

  .sub {
    margin: 0;
    font-size: 13px;
    color: #666;
    line-height: 1.5;
  }

  .sub2 {
    margin-top: 8px;
  }
}

.whoami {
  font-size: 12px;
  color: #666;
  margin: 6px 0 0;
}

.card {
  border-radius: 8px;

  :deep(.el-card__header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
  }
}

.card-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.mt {
  margin-top: 16px;
}

.result-block {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  color: #555;

  .model-used {
    margin-left: auto;
    color: #888;
  }
}

.reply-box {
  padding: 12px 14px;
  background: #f7f7f7;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
  color: #111;
}

.hint {
  font-size: 13px;
  color: #888;
}

.preset-cell {
  font-size: 12px;
  color: #333;

  &.muted {
    color: #999;
  }
}

.screen-card {
  margin-top: 20px;
}

.screen-form .box-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: #888;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tag-item {
  margin: 0;
}

.friend-input {
  max-width: 220px;
}

.cmd-pre {
  margin: 8px 0 0;
  padding: 10px 12px;
  background: #f4f4f5;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.main-tabs {
  margin-top: 8px;
}

.coord-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.coord-num {
  width: 120px;
}

.coord-str {
  max-width: 420px;
}

.mb8 {
  margin-bottom: 8px;
}

.hint-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 900px) {
  .hint-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.hint-item {
  padding: 10px 12px;
  border: 1px solid #eee;
  border-radius: 8px;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.hint-item .k {
  font-size: 12px;
  color: #666;
}

.hint-item .v {
  font-size: 12px;
  color: #111;
  font-variant-numeric: tabular-nums;
}

.log-box {
  max-height: 260px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.6;
  color: #333;
}

.log-line {
  margin-bottom: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.log-t {
  color: #888;
  font-family: ui-monospace, monospace;
}
</style>

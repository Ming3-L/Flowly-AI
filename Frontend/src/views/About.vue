<template>
  <div class="about">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>关于 Flowly</h1>
        </div>
      </el-header>
      <el-main>
        <el-card>
          <h2>Flowly — AI 工作流系统</h2>
          <p>版本：1.0.0</p>
          <p>Flowly 是一个基于 Django、Vue 和 LangGraph 构建的 AI 工作流自动化系统。</p>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
.about {
  height: 100vh;
}

.el-header {
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
}

.header-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 20px;

  h1 {
    color: #000000;
    margin: 0;
    font-size: 18px;
    font-weight: 700;
  }
}

.el-main {
  padding: 40px;
}

.el-card {
  max-width: 600px;
  margin: 0 auto;

  h2 {
    margin-bottom: 16px;
    font-size: 20px;
    font-weight: 700;
    color: #000000;
  }

  p {
    color: #666666;
    line-height: 1.6;
    margin-bottom: 12px;
  }
}
</style>

<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="wordmark">CareerPilot</div>
      <h1>登录</h1>
      <p class="lede">上传简历、解析招聘要求，并得到可追溯的匹配分析和优化建议。建议只基于你的真实经历，不会编造项目成果。</p>
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-button type="primary" :loading="loading" native-type="submit">进入工作台</el-button>
      </el-form>
      <p class="switch">还没有账号？<router-link to="/register">注册</router-link></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage } from "../api/http";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const form = reactive({ email: "", password: "" });

async function submit() {
  loading.value = true;
  try {
    const { data } = await http.post("/auth/login", form);
    auth.setSession(data);
    router.push("/dashboard");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

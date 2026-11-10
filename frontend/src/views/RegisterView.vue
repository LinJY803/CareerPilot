<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="wordmark">CareerPilot</div>
      <h1>注册</h1>
      <p class="lede">从一份真实简历开始。密码至少 8 位，并且同时包含字母和数字。</p>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="form.confirm_password" type="password" show-password /></el-form-item>
        <el-button type="primary" :loading="loading" native-type="submit">注册并进入</el-button>
      </el-form>
      <p class="switch">已有账号？<router-link to="/login">登录</router-link></p>
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
const form = reactive({ email: "", password: "", confirm_password: "" });

async function submit() {
  loading.value = true;
  try {
    const { data } = await http.post("/auth/register", form);
    auth.setSession(data);
    router.push("/dashboard");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

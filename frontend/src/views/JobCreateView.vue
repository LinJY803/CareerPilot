<template>
  <div class="panel narrow">
    <h2>创建岗位</h2>
    <el-form label-position="top">
      <el-form-item label="岗位名称"><el-input v-model="form.title" /></el-form-item>
      <el-form-item label="公司"><el-input v-model="form.company_name" /></el-form-item>
      <el-form-item label="城市"><el-input v-model="form.city" /></el-form-item>
      <el-form-item label="薪资范围"><el-input v-model="form.salary_range" /></el-form-item>
      <el-form-item label="经验要求"><el-input v-model="form.experience_requirement" /></el-form-item>
      <el-form-item label="学历要求"><el-input v-model="form.education_requirement" /></el-form-item>
      <el-form-item label="招聘 JD"><el-input v-model="form.raw_jd" type="textarea" :rows="10" /></el-form-item>
      <el-button type="primary" :loading="loading" @click="submit">保存并解析</el-button>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";

const router = useRouter();
const loading = ref(false);
const form = reactive({ title: "", company_name: "", city: "", salary_range: "", experience_requirement: "", education_requirement: "", raw_jd: "" });

async function submit() {
  loading.value = true;
  try {
    const { data } = await http.post("/jobs", form);
    const task = await pollTask(data.task_id);
    if (task.status === "FAILED") ElMessage.warning(task.error_message || "解析失败，可稍后重试");
    router.push(`/jobs/${data.id}`);
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

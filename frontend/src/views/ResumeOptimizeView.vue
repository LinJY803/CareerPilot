<template>
  <div class="stack" v-if="resume">
    <div class="topbar">
      <h2>优化 {{ resume.title }}</h2>
    </div>
    <div class="panel">
      <el-form label-position="top">
        <el-form-item label="优化方式">
          <el-radio-group v-model="form.optimize_type">
            <el-radio value="project">项目经历</el-radio>
            <el-radio value="expression">整体表达润色</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.optimize_type === 'project'" label="项目">
          <el-select v-model="form.project_id" style="width: 100%">
            <el-option v-for="item in resume.version?.projects || []" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标岗位">
          <el-select v-model="form.job_id" clearable style="width: 100%">
            <el-option v-for="item in jobs" :key="item.id" :label="item.title" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="create">生成建议</el-button>
      </el-form>
    </div>
    <div class="panel" v-if="result">
      <p class="muted">{{ taskStatus[result.status] }} {{ result.error_message }}</p>
      <div class="diff">
        <div><h3>原文</h3><pre>{{ result.original_text }}</pre></div>
        <div><h3>优化后</h3><pre>{{ result.optimized_text }}</pre></div>
      </div>
      <ul><li v-for="item in result.suggestions" :key="item">{{ item }}</li></ul>
      <div class="actions">
        <el-button @click="copyText">复制优化内容</el-button>
        <el-button type="primary" :disabled="result.status !== 'success'" @click="save">保存为新版本</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";
import { taskStatus } from "../labels";

const route = useRoute();
const resume = ref<any>(null);
const jobs = ref<any[]>([]);
const result = ref<any>(null);
const loading = ref(false);
const form = reactive<{ optimize_type: "project" | "expression"; project_id: number | null; job_id: number | null }>({
  optimize_type: "project",
  project_id: null,
  job_id: null,
});

onMounted(async () => {
  resume.value = (await http.get(`/resumes/${route.params.id}`)).data;
  jobs.value = (await http.get("/jobs")).data;
  form.project_id = resume.value.version?.projects?.[0]?.id || null;
});

async function create() {
  loading.value = true;
  try {
    const { data } = await http.post("/optimizations", { ...form, resume_id: Number(route.params.id) });
    const task = await pollTask(data.task_id);
    result.value = (await http.get(`/optimizations/${data.id}`)).data;
    if (task.status === "FAILED") ElMessage.error(task.error_message || "优化失败");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}

async function copyText() {
  await navigator.clipboard.writeText(result.value?.optimized_text || "");
  ElMessage.success("已复制");
}

async function save() {
  const { data } = await http.post(`/optimizations/${result.value.id}/save`);
  ElMessage.success(`已保存为版本 ${data.version_no}`);
}
</script>

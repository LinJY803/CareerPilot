<template>
  <div class="panel narrow">
    <h2>上传简历</h2>
    <p class="muted">支持 PDF、DOCX，最大 10 MB。扫描版 PDF 暂不识别。</p>
    <el-form label-position="top">
      <el-form-item label="简历名称"><el-input v-model="title" placeholder="可留空，默认使用文件名" /></el-form-item>
      <el-form-item label="文件">
        <input type="file" accept=".pdf,.docx" @change="onFile" />
      </el-form-item>
      <el-button type="primary" :loading="loading" @click="submit">上传并解析</el-button>
    </el-form>
    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";

const router = useRouter();
const title = ref("");
const file = ref<File | null>(null);
const loading = ref(false);
const message = ref("");

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null;
}

async function submit() {
  if (!file.value) return ElMessage.warning("请选择文件");
  const lower = file.value.name.toLowerCase();
  if (!lower.endsWith(".pdf") && !lower.endsWith(".docx")) return ElMessage.warning("只支持 PDF 和 DOCX");
  if (file.value.size > 10 * 1024 * 1024) return ElMessage.warning("文件不能超过 10 MB");
  loading.value = true;
  try {
    const form = new FormData();
    form.append("file", file.value);
    form.append("title", title.value);
    const { data } = await http.post("/resumes", form);
    message.value = "正在解析简历…";
    const task = await pollTask(data.task_id);
    if (task.status === "FAILED") throw new Error(task.error_message || "解析失败");
    message.value = "正在生成诊断…";
    const analysis = await waitAnalysis(data.id);
    if (analysis?.task?.status === "FAILED") ElMessage.warning(analysis.task.error_message || "诊断失败");
    router.push(`/resumes/${data.id}`);
  } catch (error) {
    ElMessage.error(error instanceof Error && error.message && !("response" in error) ? error.message : errorMessage(error));
  } finally {
    loading.value = false;
  }
}

async function waitAnalysis(id: number) {
  for (let i = 0; i < 40; i += 1) {
    const { data } = await http.get(`/resumes/${id}/analysis`);
    if (data.report || data.task?.status === "FAILED") return data;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return null;
}
</script>

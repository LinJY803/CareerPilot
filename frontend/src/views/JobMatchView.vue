<template>
  <div class="panel narrow">
    <h2>岗位匹配</h2>
    <p class="muted">选择一份已解析的简历和一个已解析的岗位。</p>
    <el-form label-position="top">
      <el-form-item label="简历">
        <el-select v-model="resumeId" style="width: 100%">
          <el-option v-for="item in resumes" :key="item.id" :label="item.title" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="岗位">
        <el-select v-model="jobId" style="width: 100%">
          <el-option v-for="item in jobs" :key="item.id" :label="`${item.title} · ${item.company_name || '未填公司'}`" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-button type="primary" :loading="loading" @click="submit">开始分析</el-button>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage } from "../api/http";

const route = useRoute();
const router = useRouter();
const resumes = ref<any[]>([]);
const jobs = ref<any[]>([]);
const resumeId = ref<number | null>(null);
const jobId = ref<number | null>(route.query.jobId ? Number(route.query.jobId) : null);
const loading = ref(false);

onMounted(async () => {
  resumes.value = (await http.get("/resumes")).data;
  jobs.value = (await http.get("/jobs")).data;
});

async function submit() {
  loading.value = true;
  try {
    const { data } = await http.post("/jobs/match", { resume_id: resumeId.value, job_id: jobId.value });
    router.push(`/jobs/match/${data.id}`);
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

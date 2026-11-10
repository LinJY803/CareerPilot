<template>
  <div v-if="job" class="stack">
    <div class="topbar">
      <div>
        <h2>{{ job.title }}</h2>
        <p class="muted">{{ job.company_name }} · {{ job.city }} · {{ parseStatus[job.parse_status] }}</p>
      </div>
      <div class="actions">
        <el-button @click="reparse">重新解析</el-button>
        <el-button type="primary" @click="$router.push({ path: '/jobs/match', query: { jobId: job.id } })">去匹配</el-button>
      </div>
    </div>
    <div class="grid-2">
      <div class="panel">
        <h3>原始 JD</h3>
        <pre>{{ job.raw_jd }}</pre>
      </div>
      <div class="panel">
        <h3>结构化要求</h3>
        <p v-if="job.parse_error">{{ job.parse_error }}</p>
        <template v-if="job.requirement">
          <p>经验：{{ job.requirement.experience_requirement || "无法判断" }}</p>
          <p>学历：{{ job.requirement.education_requirement || "无法判断" }}</p>
          <div v-for="item in job.requirement.skills" :key="item.name + item.type" style="margin-bottom: 8px">
            <el-tag>{{ skillType[item.type] || item.type }}</el-tag> {{ item.name }}
            <div class="muted">依据：{{ item.evidence }}</div>
          </div>
          <p v-for="item in job.requirement.responsibilities" :key="item">{{ item }}</p>
          <p v-if="job.requirement.uncertain_fields.length" class="muted">无法判断：{{ job.requirement.uncertain_fields.join("、") }}</p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";
import { parseStatus, skillType } from "../labels";

const route = useRoute();
const job = ref<any>(null);
async function load() { job.value = (await http.get(`/jobs/${route.params.id}`)).data; }
onMounted(load);
async function reparse() {
  try {
    const { data } = await http.post(`/jobs/${route.params.id}/parse`);
    const task = await pollTask(data.id);
    if (task.status === "FAILED") throw new Error(task.error_message);
    await load();
  } catch (error) {
    ElMessage.error(error instanceof Error && !("response" in error) ? error.message : errorMessage(error));
  }
}
</script>

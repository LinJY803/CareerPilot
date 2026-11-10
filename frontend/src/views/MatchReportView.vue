<template>
  <div v-if="report" class="stack">
    <div class="topbar">
      <div>
        <h2>{{ report.job_title || "匹配报告" }}</h2>
        <p class="muted">{{ report.company_name }} · {{ taskStatus[report.status] || report.status }}</p>
      </div>
      <el-button v-if="report.status === 'failed'" @click="retry">重新执行</el-button>
    </div>
    <div class="grid-2" v-if="report.status === 'success'">
      <div class="panel">
        <h3>综合分</h3>
        <p class="score">{{ report.overall_score }}</p>
        <p class="muted">规则分 {{ report.rule_score }}，AI 调整 {{ report.ai_adjustment }}。{{ report.ai_validated ? "AI 判断已通过依据校验。" : "AI 未通过校验，当前展示规则分。" }}</p>
        <p>{{ report.summary }}</p>
        <ScoreRadar :items="(report.dimensions || []).map((item: any) => ({ name: item.name, score: item.score }))" />
      </div>
      <div class="panel">
        <h3>技能差距</h3>
        <el-table :data="report.skills">
          <el-table-column prop="name" label="技能" />
          <el-table-column label="类型" width="110"><template #default="{ row }">{{ skillType[row.type] }}</template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }">{{ skillStatus[row.status] }}</template></el-table-column>
          <el-table-column prop="evidence" label="依据" />
        </el-table>
        <h3>建议</h3>
        <ul><li v-for="item in report.suggestions" :key="item">{{ item }}</li></ul>
        <p class="muted">{{ report.score_breakdown?.notes?.skills }}</p>
      </div>
    </div>
    <div class="panel" v-else>
      <p>{{ report.error_message || "分析进行中，页面会自动刷新。" }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import http, { pollTask } from "../api/http";
import ScoreRadar from "../components/ScoreRadar.vue";
import { skillStatus, skillType, taskStatus } from "../labels";

const route = useRoute();
const report = ref<any>(null);

async function load() {
  report.value = (await http.get(`/jobs/match/${route.params.id}`)).data;
  if (report.value.status === "pending" || report.value.status === "processing") {
    if (report.value.task_id) await pollTask(report.value.task_id);
    report.value = (await http.get(`/jobs/match/${route.params.id}`)).data;
  }
}
onMounted(load);

async function retry() {
  if (!report.value.task_id) return;
  await http.post(`/tasks/${report.value.task_id}/retry`);
  ElMessage.info("已重新执行");
  await load();
}
</script>

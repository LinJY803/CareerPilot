<template>
  <div v-if="resume" class="stack">
    <div class="topbar">
      <div>
        <h2>{{ resume.title }}</h2>
        <p class="muted">{{ parseStatus[resume.parse_status] }} · {{ diagnosisStatus[resume.diagnosis_status] }}</p>
        <p v-if="resume.parse_error" class="muted">{{ resume.parse_error }}</p>
      </div>
      <div class="actions">
        <el-button @click="reparse">重新解析</el-button>
        <el-button type="primary" @click="$router.push(`/resumes/${resume.id}/optimize`)">优化简历</el-button>
      </div>
    </div>
    <div class="grid-2" v-if="report">
      <div class="panel">
        <h3>诊断</h3>
        <p class="score">{{ report.overall_score }}</p>
        <ScoreRadar :items="report.dimensions.map((item: any) => ({ name: item.name, score: item.score }))" />
      </div>
      <div class="panel">
        <h3>问题和建议</h3>
        <div v-for="issue in report.issues" :key="issue.evidence" style="margin-bottom: 14px">
          <strong>{{ issue.problem }}</strong>
          <p class="muted">原文：{{ issue.evidence }}</p>
          <p>{{ issue.suggestion }}</p>
          <p v-if="issue.example">示例：{{ issue.example }}</p>
        </div>
        <el-empty v-if="!report.issues.length" description="没有发现带原文依据的问题" />
      </div>
    </div>
    <div class="panel" v-if="resume.version">
      <h3>解析结果 · 版本 {{ resume.version.version_no }}</h3>
      <p>{{ resume.version.basic.name }} · {{ resume.version.basic.email }} · {{ resume.version.basic.phone }} · {{ resume.version.basic.city }}</p>
      <h4>教育</h4>
      <p v-for="item in resume.version.educations" :key="item.id">{{ item.school }} {{ item.major }} {{ item.degree }} {{ item.start_date }}-{{ item.end_date }}</p>
      <h4>工作</h4>
      <p v-for="item in resume.version.experiences" :key="item.id"><strong>{{ item.company }} · {{ item.title }}</strong><br />{{ item.content }}</p>
      <h4>项目</h4>
      <div v-for="item in resume.version.projects" :key="item.id">
        <strong>{{ item.name }}</strong>
        <p>{{ item.background }}</p>
        <p>技术栈：{{ item.tech_stack }}</p>
        <p>{{ item.responsibilities }}</p>
        <p>{{ item.achievements }}</p>
      </div>
      <h4>技能</h4>
      <el-tag v-for="item in resume.version.skills" :key="item.id" style="margin-right: 8px">{{ item.name }}</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";
import ScoreRadar from "../components/ScoreRadar.vue";
import { diagnosisStatus, parseStatus } from "../labels";

const route = useRoute();
const resume = ref<any>(null);
const report = ref<any>(null);

async function load() {
  resume.value = (await http.get(`/resumes/${route.params.id}`)).data;
  const analysis = (await http.get(`/resumes/${route.params.id}/analysis`)).data;
  report.value = analysis.report;
}
onMounted(load);

async function reparse() {
  try {
    const { data } = await http.post(`/resumes/${route.params.id}/parse`);
    const task = await pollTask(data.id);
    if (task.status === "FAILED") throw new Error(task.error_message);
    await load();
  } catch (error) {
    ElMessage.error(error instanceof Error && !("response" in error) ? error.message : errorMessage(error));
  }
}
</script>

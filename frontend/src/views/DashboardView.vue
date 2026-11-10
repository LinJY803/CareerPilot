<template>
  <div class="stack">
    <div class="topbar">
      <div>
        <h2>工作台</h2>
        <p class="muted">看自己有什么，岗位要什么，以及差距在哪里。</p>
      </div>
      <div class="actions">
        <el-button type="primary" @click="$router.push('/resumes/upload')">上传简历</el-button>
        <el-button @click="$router.push('/jobs/create')">添加岗位</el-button>
        <el-button @click="$router.push('/jobs/match')">开始匹配</el-button>
      </div>
    </div>
    <div class="metrics">
      <div class="metric"><span>简历</span><strong>{{ summary.resume_count }}</strong></div>
      <div class="metric"><span>诊断</span><strong>{{ summary.diagnosis_count }}</strong></div>
      <div class="metric"><span>岗位</span><strong>{{ summary.job_count }}</strong></div>
      <div class="metric"><span>已完成匹配</span><strong>{{ summary.match_count }}</strong></div>
    </div>
    <div class="grid-2">
      <div class="panel">
        <h3>最近的简历</h3>
        <el-table :data="summary.recent_resumes" @row-click="openResume">
          <el-table-column prop="title" label="名称" />
          <el-table-column prop="file_type" label="类型" width="90" />
          <el-table-column label="解析" width="100">
            <template #default="{ row }">{{ parseStatus[row.parse_status] }}</template>
          </el-table-column>
        </el-table>
      </div>
      <div class="panel">
        <h3>最近的匹配</h3>
        <ScoreRadar v-if="chartItems.length" :items="chartItems" />
        <el-empty v-else description="完成一次匹配后，这里会显示分数" />
        <el-table :data="summary.recent_matches" @row-click="openMatch">
          <el-table-column prop="job_title" label="岗位" />
          <el-table-column prop="overall_score" label="综合分" width="90" />
        </el-table>
      </div>
    </div>
    <div class="panel">
      <h3>个人资料</h3>
      <el-form :model="profile" label-width="90px">
        <el-form-item label="姓名"><el-input v-model="profile.display_name" /></el-form-item>
        <el-form-item label="目标岗位"><el-input v-model="profile.target_role" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="profile.city" /></el-form-item>
        <el-form-item label="经验"><el-input v-model="profile.years_experience" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="profile.bio" type="textarea" /></el-form-item>
        <el-button type="primary" @click="saveProfile">保存资料</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http, { errorMessage } from "../api/http";
import ScoreRadar from "../components/ScoreRadar.vue";
import { parseStatus } from "../labels";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();
const summary = ref<any>({ resume_count: 0, diagnosis_count: 0, job_count: 0, match_count: 0, recent_resumes: [], recent_matches: [] });
const profile = reactive({ display_name: "", phone: "", city: "", target_role: "", years_experience: "", bio: "" });
const chartItems = computed(() =>
  summary.value.recent_matches
    .filter((item: any) => item.overall_score !== null)
    .map((item: any) => ({ name: item.job_title || "岗位", score: item.overall_score }))
);

onMounted(async () => {
  const { data } = await http.get("/dashboard/summary");
  summary.value = data;
  if (!auth.user) await auth.fetchMe();
  Object.assign(profile, auth.user?.profile || {});
});

function openResume(row: { id: number }) { router.push(`/resumes/${row.id}`); }
function openMatch(row: { id: number }) { router.push(`/jobs/match/${row.id}`); }

async function saveProfile() {
  try {
    const { data } = await http.put("/users/me", profile);
    auth.user = data;
    ElMessage.success("资料已保存");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}
</script>

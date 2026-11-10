<template>
  <div>
    <div class="topbar">
      <h2>简历</h2>
      <el-button type="primary" @click="$router.push('/resumes/upload')">上传简历</el-button>
    </div>
    <div class="panel">
      <el-table :data="rows">
        <el-table-column prop="title" label="简历名称" />
        <el-table-column prop="created_at" label="上传时间" />
        <el-table-column prop="file_type" label="文件类型" width="100" />
        <el-table-column label="解析状态" width="110">
          <template #default="{ row }">{{ parseStatus[row.parse_status] }}</template>
        </el-table-column>
        <el-table-column label="诊断状态" width="110">
          <template #default="{ row }">{{ diagnosisStatus[row.diagnosis_status] }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button link @click="$router.push(`/resumes/${row.id}`)">查看</el-button>
            <el-button link @click="reparse(row)">重新解析</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import http, { errorMessage, pollTask } from "../api/http";
import { diagnosisStatus, parseStatus } from "../labels";

const rows = ref<any[]>([]);
async function load() { rows.value = (await http.get("/resumes")).data; }
onMounted(load);

async function reparse(row: any) {
  try {
    const { data } = await http.post(`/resumes/${row.id}/parse`);
    ElMessage.info("已开始重新解析");
    await pollTask(data.id);
    await load();
  } catch (error) { ElMessage.error(errorMessage(error)); }
}
async function remove(row: any) {
  await http.delete(`/resumes/${row.id}`);
  await load();
}
</script>

<template>
  <div>
    <div class="topbar">
      <h2>目标岗位</h2>
      <el-button type="primary" @click="$router.push('/jobs/create')">创建岗位</el-button>
    </div>
    <div class="panel">
      <el-table :data="rows" @row-click="(row: any) => $router.push(`/jobs/${row.id}`)">
        <el-table-column prop="title" label="岗位" />
        <el-table-column prop="company_name" label="公司" />
        <el-table-column prop="city" label="城市" />
        <el-table-column label="解析" width="110">
          <template #default="{ row }">{{ parseStatus[row.parse_status] }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import http from "../api/http";
import { parseStatus } from "../labels";
const rows = ref<any[]>([]);
onMounted(async () => { rows.value = (await http.get("/jobs")).data; });
</script>

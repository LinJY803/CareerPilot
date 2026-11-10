<template>
  <div class="app-shell">
    <header class="topnav">
      <div class="topnav-bar">
        <router-link class="wordmark" to="/dashboard">CareerPilot</router-link>
        <nav class="nav">
          <router-link to="/dashboard" class="nav-link" :class="{ 'is-current': dashOn }">工作台</router-link>
          <router-link to="/resumes" class="nav-link" :class="{ 'is-current': resumeOn }">简历</router-link>
          <router-link to="/jobs" class="nav-link" :class="{ 'is-current': jobOn }">岗位</router-link>
          <router-link to="/jobs/match" class="nav-link" :class="{ 'is-current': matchOn }">岗位匹配</router-link>
        </nav>
        <div class="nav-user">
          <span class="nav-name">{{ displayName }}</span>
          <button type="button" class="text-btn" @click="onLogout">退出</button>
        </div>
      </div>
    </header>
    <main class="main">
      <div class="page">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const displayName = computed(() => auth.user?.profile.display_name || auth.user?.email || "");
const dashOn = computed(() => route.path.startsWith("/dashboard"));
const resumeOn = computed(() => route.path.startsWith("/resumes"));
const matchOn = computed(() => route.path.startsWith("/jobs/match"));
const jobOn = computed(() => route.path.startsWith("/jobs") && !matchOn.value);

onMounted(async () => {
  if (!auth.user && auth.accessToken) {
    try {
      await auth.fetchMe();
    } catch {
      auth.clear();
      router.push("/login");
    }
  }
});

async function onLogout() {
  await auth.logout();
  router.push("/login");
}
</script>

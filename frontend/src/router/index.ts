import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
import AppLayout from "../layouts/AppLayout.vue";
import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";
import DashboardView from "../views/DashboardView.vue";
import ResumeListView from "../views/ResumeListView.vue";
import ResumeUploadView from "../views/ResumeUploadView.vue";
import ResumeDetailView from "../views/ResumeDetailView.vue";
import ResumeOptimizeView from "../views/ResumeOptimizeView.vue";
import JobListView from "../views/JobListView.vue";
import JobCreateView from "../views/JobCreateView.vue";
import JobDetailView from "../views/JobDetailView.vue";
import JobMatchView from "../views/JobMatchView.vue";
import MatchReportView from "../views/MatchReportView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { guest: true } },
    { path: "/register", component: RegisterView, meta: { guest: true } },
    {
      path: "/",
      component: AppLayout,
      meta: { auth: true },
      children: [
        { path: "", redirect: "/dashboard" },
        { path: "dashboard", component: DashboardView },
        { path: "resumes", component: ResumeListView },
        { path: "resumes/upload", component: ResumeUploadView },
        { path: "resumes/:id/optimize", component: ResumeOptimizeView },
        { path: "resumes/:id", component: ResumeDetailView },
        { path: "jobs", component: JobListView },
        { path: "jobs/create", component: JobCreateView },
        { path: "jobs/match/:id", component: MatchReportView },
        { path: "jobs/match", component: JobMatchView },
        { path: "jobs/:id", component: JobDetailView },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.auth && !auth.accessToken) return "/login";
  if (to.meta.guest && auth.accessToken) return "/dashboard";
  return true;
});

export default router;

import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const http = axios.create({ baseURL: "/api/v1", timeout: 30000 });

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("cp_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string> | null = null;

async function refreshAccess() {
  const refresh = localStorage.getItem("cp_refresh");
  if (!refresh) throw new Error("missing refresh token");
  const { data } = await axios.post("/api/v1/auth/refresh", { refresh_token: refresh });
  localStorage.setItem("cp_access", data.access_token);
  localStorage.setItem("cp_refresh", data.refresh_token);
  return data.access_token as string;
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const url = original?.url || "";
    if (error.response?.status === 401 && original && !original._retry && !url.includes("/auth/")) {
      original._retry = true;
      try {
        refreshing = refreshing || refreshAccess();
        const token = await refreshing;
        refreshing = null;
        original.headers.Authorization = `Bearer ${token}`;
        return http(original);
      } catch (refreshError) {
        refreshing = null;
        localStorage.removeItem("cp_access");
        localStorage.removeItem("cp_refresh");
        if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export function errorMessage(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => (item as { msg?: string }).msg || "输入有误").join("；");
  return "请求失败，请稍后重试";
}

export async function pollTask(taskId: string, onTick?: (task: TaskView) => void) {
  for (let i = 0; i < 60; i += 1) {
    const { data } = await http.get<TaskView>(`/tasks/${taskId}`);
    onTick?.(data);
    if (data.status === "SUCCESS" || data.status === "FAILED" || data.status === "CANCELLED") return data;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("任务等待超时");
}

export interface TaskView {
  id: string;
  task_type: string;
  status: string;
  error_message: string;
  result_ref: string;
  retry_count: number;
}

export default http;

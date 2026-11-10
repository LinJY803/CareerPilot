import { defineStore } from "pinia";
import http from "../api/http";

export interface UserProfile {
  display_name: string;
  phone: string;
  city: string;
  target_role: string;
  years_experience: string;
  bio: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  status: string;
  profile: UserProfile;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: localStorage.getItem("cp_access") || "",
    refreshToken: localStorage.getItem("cp_refresh") || "",
    user: null as CurrentUser | null,
  }),
  actions: {
    setSession(data: { access_token: string; refresh_token: string; user?: CurrentUser }) {
      this.accessToken = data.access_token;
      this.refreshToken = data.refresh_token;
      localStorage.setItem("cp_access", data.access_token);
      localStorage.setItem("cp_refresh", data.refresh_token);
      if (data.user) this.user = data.user;
    },
    clear() {
      this.accessToken = "";
      this.refreshToken = "";
      this.user = null;
      localStorage.removeItem("cp_access");
      localStorage.removeItem("cp_refresh");
    },
    async fetchMe() {
      const { data } = await http.get<CurrentUser>("/users/me");
      this.user = data;
    },
    async logout() {
      try {
        await http.post("/auth/logout", { refresh_token: this.refreshToken || null });
      } finally {
        this.clear();
      }
    },
  },
});

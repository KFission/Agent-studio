"use client";

import AgentStudio from "../components/AgentStudio";
import LoginPage from "../components/LoginPage";
import useAuthStore from "../stores/authStore";

export default function Home() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (!isAuthenticated) return <LoginPage />;

  return <AgentStudio />;
}

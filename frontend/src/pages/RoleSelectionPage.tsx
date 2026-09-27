import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { UserRole } from "../types";
import Logo from "../components/Logo";

const WORKSPACES: {
  role: UserRole;
  title: string;
  detail: string;
  email: string;
  destination: string;
  icon: string;
  accent: string;
}[] = [
  {
    role: "ADMIN",
    title: "Admin",
    detail: "System overview and configuration",
    email: "admin@fraudshield.ai",
    destination: "/admin-dashboard",
    icon: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    accent: "text-emerald-700 bg-emerald-100",
  },
  {
    role: "BUSINESS_MANAGER",
    title: "Business Manager",
    detail: "Transaction performance and risk",
    email: "manager@fraudshield.ai",
    destination: "/dashboard",
    icon: "M3 4h18v16H3zM3 9h18M8 14h3m3 0h2",
    accent: "text-sky-700 bg-sky-100",
  },
  {
    role: "ANALYST",
    title: "Analyst",
    detail: "Alerts and fraud investigations",
    email: "analyst@fraudshield.ai",
    destination: "/dashboard",
    icon: "M12 3 21 19H3L12 3zM12 9v4m0 3h.01",
    accent: "text-amber-700 bg-amber-100",
  },
];

export default function RoleSelectionPage() {
  const { user, login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(null);

  if (user) {
    return <Navigate to={user.role === "ADMIN" ? "/admin-dashboard" : "/dashboard"} replace />;
  }

  async function enterWorkspace(workspace: (typeof WORKSPACES)[number]) {
    setError(null);
    setSelectedRole(workspace.role);
    try {
      await login(workspace.email, "Demo123!");
      navigate(workspace.destination);
    } catch {
      setError("Could not open this workspace. Check that the backend is running and try again.");
      setSelectedRole(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#eef3ec] px-5 py-8 text-[#183c32] dark:bg-[#101b17] dark:text-slate-100 sm:px-10 sm:py-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col">
        <header className="mb-14 flex items-center justify-between sm:mb-20">
          <Logo size={38} />
          <a href="/login" className="text-sm font-semibold text-[#527369] transition hover:text-[#183c32] dark:text-slate-400 dark:hover:text-white">
            Sign in with an account
          </a>
        </header>

        <section className="mx-auto w-full max-w-5xl">
          <div className="mb-9 max-w-2xl">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-400">FraudSense workspace</p>
            <h1 className="text-3xl font-extrabold leading-tight sm:text-4xl">Choose your workspace</h1>
            <p className="mt-3 text-base text-slate-600 dark:text-slate-400">Select a role to open its dashboard.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {WORKSPACES.map((workspace) => (
              <button
                key={workspace.role}
                type="button"
                onClick={() => enterWorkspace(workspace)}
                disabled={isLoading}
                className="group flex min-h-56 flex-col items-start rounded-xl border border-[#dce6dc] bg-white p-6 text-left shadow-sm transition duration-200 hover:-translate-y-1 hover:border-emerald-300 hover:shadow-md disabled:cursor-wait disabled:opacity-60 dark:border-white/10 dark:bg-[#17261f] dark:hover:border-emerald-500/50"
              >
                <span className={`mb-8 flex h-12 w-12 items-center justify-center rounded-lg ${workspace.accent}`}>
                  <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d={workspace.icon} />
                  </svg>
                </span>
                <span className="text-lg font-bold">{workspace.title}</span>
                <span className="mt-1 text-sm text-slate-500 dark:text-slate-400">{workspace.detail}</span>
                <span className="mt-auto flex w-full items-center justify-between pt-7 text-sm font-semibold text-emerald-800 dark:text-emerald-400">
                  {isLoading && selectedRole === workspace.role ? "Opening..." : "Open workspace"}
                  <span aria-hidden="true">→</span>
                </span>
              </button>
            ))}
          </div>

          {error && <p role="alert" className="mt-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">{error}</p>}
        </section>

        <footer className="mt-16 text-xs text-slate-500 dark:text-slate-500">© {new Date().getFullYear()} FraudSense</footer>
      </div>
    </main>
  );
}
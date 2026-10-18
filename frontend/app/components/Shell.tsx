"use client";

import {
  ArrowUpRight,
  CircleHelp,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  UsersRound,
  Waypoints,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { apiRequest, initials, type ApiUser } from "../../lib/api";

type ShellProps = {
  user: ApiUser;
  active: "dashboard" | "members" | "tasks";
  children: ReactNode;
};

export default function Shell({ user, active, children }: ShellProps) {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);
  const [apiOnline, setApiOnline] = useState(true);

  useEffect(() => {
    let mounted = true;
    const ping = () => {
      apiRequest<{ status: string }>("/api/health", { cache: "no-store" })
        .then(({ status }) => {
          if (mounted) setApiOnline(status === "ok");
        })
        .catch(() => {
          if (mounted) setApiOnline(false);
        });
    };
    ping();
    const interval = window.setInterval(ping, 5 * 60 * 1000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  async function logout() {
    setLoggingOut(true);
    try {
      await apiRequest("/api/logout", { method: "POST" });
      router.replace("/login");
    } catch (error) {
      setLoggingOut(false);
      window.alert(error instanceof Error ? error.message : "Could not sign out.");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Sangam dashboard">
          <span className="brand-mark"><Waypoints size={21} strokeWidth={2.1} /></span>
          <span className="brand-copy">sangam<small>outreach workspace</small></span>
        </a>

        <div className="nav-label">Workspace</div>
        <nav className="nav-list" aria-label="Main navigation">
          <a className={`nav-link ${active === "dashboard" ? "active" : ""}`} href="/">
            <LayoutDashboard size={17} /><span>Overview</span>
          </a>
          {user.isAdmin && (
            <a className={`nav-link ${active === "members" ? "active" : ""}`} href="/members">
              <UsersRound size={17} /><span>Committee</span>
            </a>
          )}
          <a className={`nav-link ${active === "tasks" ? "active" : ""}`} href="/tasks">
            <ClipboardList size={17} /><span>Data tasks</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="help-card">
            <CircleHelp size={17} color="#cbf36a" />
            <strong>Thoughtful outreach</strong>
            <p>Every contact is an opportunity to listen, connect and follow through.</p>
          </div>
          <div className="user-card">
            <span className="avatar">{initials(user.name)}</span>
            <span className="user-copy">
              <span className="user-name">{user.name}</span>
              <span className="user-role">{user.isAdmin ? "Workspace admin" : "Committee member"}</span>
            </span>
            <button
              className="logout-button"
              type="button"
              aria-label="Sign out"
              title="Sign out"
              disabled={loggingOut}
              onClick={logout}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span aria-hidden="true">/</span> <b>{active === "dashboard" ? "Overview" : active === "members" ? "Committee" : "Data tasks"}</b></div>
          <div className="topbar-right">
            <span className={`api-indicator ${apiOnline ? "" : "offline"}`} title={apiOnline ? "Backend is responding" : "Backend is not responding"}><span />{apiOnline ? "Connected" : "Offline"}</span>
            <span className="today">A little progress goes a long way.</span>
            <button
              className="mobile-logout"
              type="button"
              aria-label="Sign out"
              title="Sign out"
              disabled={loggingOut}
              onClick={logout}
            >
              <LogOut size={16} />
            </button>
            <span className="avatar">{initials(user.name)}</span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

export function PageLink({ href, children }: { href: string; children: ReactNode }) {
  return <a className="text-link" href={href}>{children}<ArrowUpRight size={14} /></a>;
}

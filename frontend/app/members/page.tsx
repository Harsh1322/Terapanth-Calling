"use client";

import { ArrowLeft, Pencil, UserPlus, UsersRound, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { ApiUser } from "../../lib/api";
import { apiRequest, initials } from "../../lib/api";
import Shell from "../components/Shell";

type Member = {
  id: number;
  name: string;
  mobile: string;
  active: boolean;
};

export default function MembersPage() {
  const router = useRouter();
  const [user, setUser] = useState<ApiUser | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Member | null>(null);
  const [name, setName] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const loadMembers = useCallback(async () => {
    const session = await apiRequest<{ user: ApiUser | null }>("/api/session");
    if (!session.user) {
      router.replace("/login");
      return;
    }
    if (!session.user.isAdmin) {
      router.replace("/");
      return;
    }
    setUser(session.user);
    const result = await apiRequest<{ members: Member[] }>("/api/members");
    setMembers(result.members);
  }, [router]);

  useEffect(() => {
    loadMembers()
      .catch((error: unknown) => notify(error instanceof Error ? error.message : "Could not load committee members.", true))
      .finally(() => setLoading(false));
  }, [loadMembers, notify]);

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      const result = await apiRequest<{ member: Member }>(
        editing ? `/api/members/${editing.id}` : "/api/members",
        {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ displayName: name, mobile, password }),
      });
      setMembers((current) => (editing
        ? current.map((member) => member.id === editing.id ? result.member : member)
        : [...current, result.member]).sort((a, b) => a.name.localeCompare(b.name)));
      setName("");
      setMobile("");
      setPassword("");
      setEditing(null);
      notify(editing ? "Committee member details updated." : "Your new committee member is ready.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not add this member.", true);
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(member: Member) {
    if (!window.confirm(`Remove ${member.name} from the committee? Their sign-in will be disabled and historical contact assignments will be retained.`)) return;
    try {
      await apiRequest(`/api/members/${member.id}/deactivate`, { method: "POST" });
      setMembers((current) => current.map((item) => item.id === member.id ? { ...item, active: false } : item));
      notify("Member removed. Historical contact assignments were retained.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not deactivate this member.", true);
    }
  }

  if (loading) return <div className="loading-screen"><span className="spinner" aria-label="Loading committee" /></div>;
  if (!user) return <div className="loading-screen"><div className="login-error">We couldn’t load the committee. Please refresh and try again.</div></div>;

  return (
    <Shell user={user} active="members">
      {toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.message}</div>}
      <section className="page-content">
        <div className="page-head">
          <div>
            <div className="eyebrow"><span className="eyebrow-dot" /> THE PEOPLE BEHIND THE CALLS</div>
            <h1>Your committee</h1>
            <p>Bring thoughtful people together and make every assignment count.</p>
          </div>
          <a className="button secondary" href="/"><ArrowLeft size={15} /> <span>Back to overview</span></a>
        </div>

        <div className="members-grid">
          <section className="panel form-card">
            <div className="panel-head">
              <div>
                <h2>{editing ? "Edit committee member" : "Add a committee member"}</h2>
                <p>{editing ? "Update their name or registered mobile number." : "They’ll be able to see and update their own assigned contacts."}</p>
              </div>
              {editing
                ? <button className="icon-button" type="button" title="Cancel editing" onClick={() => { setEditing(null); setName(""); setMobile(""); }}><X size={15} /></button>
                : <span className="stat-icon"><UserPlus size={16} /></span>}
            </div>
            <form onSubmit={addMember}>
              <div className="form-field">
                <label className="field-label" htmlFor="display-name">Full name</label>
                <div className="input-wrap"><input id="display-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={150} placeholder="e.g. Asha Patel" required /></div>
              </div>
              <div className="form-field">
                <label className="field-label" htmlFor="member-mobile">Mobile number</label>
                <div className="input-wrap"><input id="member-mobile" type="tel" inputMode="tel" value={mobile} onChange={(event) => setMobile(event.target.value)} maxLength={20} placeholder="Their registered mobile number" required /></div>
              </div>
              {!editing && <div className="form-field">
                <label className="field-label" htmlFor="member-password">Temporary password</label>
                <div className="input-wrap"><input id="member-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} placeholder="At least 8 characters" required /></div>
              </div>}
              <button className="button" type="submit" disabled={saving}>{editing ? <Pencil size={15} /> : <UserPlus size={15} />} {saving ? "Saving…" : editing ? "Save changes" : "Add member"}</button>
            </form>
            {!editing && <p style={{ margin: "14px 0 0", fontSize: 10 }}>Share sign-in details privately with the new member.</p>}
          </section>

          <section className="panel" aria-labelledby="member-list-heading">
            <div className="panel-head">
              <div><h2 id="member-list-heading">Committee directory</h2><p>{members.length} {members.length === 1 ? "member" : "members"} · contact assignments stay with their owner</p></div>
              <span className="stat-icon"><UsersRound size={16} /></span>
            </div>
            <div className="table-scroll">
              <table className="member-table">
                <thead><tr><th>Member</th><th>Mobile</th><th>Access</th><th /></tr></thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.id}>
                      <td>
                        <div className="contact-person">
                          <span className="contact-avatar">{initials(member.name)}</span>
                          <span className="contact-name">{member.name}</span>
                        </div>
                      </td>
                      <td>{member.mobile}</td>
                      <td><span className={`active-indicator ${member.active ? "" : "inactive"}`}>{member.active ? "Active" : "Inactive"}</span></td>
                      <td>
                        {member.active && <div className="table-actions">
                          <button className="icon-button" type="button" title={`Edit ${member.name}`} aria-label={`Edit ${member.name}`} onClick={() => { setEditing(member); setName(member.name); setMobile(member.mobile); }}><Pencil size={14} /></button>
                          <button className="button danger small" type="button" onClick={() => deactivate(member)}>Delete</button>
                        </div>}
                      </td>
                    </tr>
                  ))}
                  {!members.length && <tr><td className="empty-table" colSpan={4}>No committee members yet. Add your first member to begin sharing contact assignments.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </Shell>
  );
}

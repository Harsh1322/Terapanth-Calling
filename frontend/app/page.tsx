"use client";

import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CheckCheck,
  CircleHelp,
  Clock3,
  FileSpreadsheet,
  Headphones,
  MessageCircle,
  Phone,
  Search,
  Send,
  Upload,
  UsersRound,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import Shell, { PageLink } from "./components/Shell";
import { apiRequest, initials, type ApiUser } from "../lib/api";

type Contact = {
  id: number;
  name: string;
  phone: string;
  status: string;
  statusDisplay: string;
  destination: string;
  destinationDisplay: string;
  assignedTo: string;
  requiresCollection: boolean;
};

type MemberProgress = {
  id: number;
  name: string;
  mobile: string;
  total: number;
  success: number;
  pending: number;
  invalid: number;
  reached: number;
};

type DashboardData = {
  stats: Record<string, number>;
  contacts: Contact[];
  user: ApiUser;
  requiresCollection: boolean;
  memberStats?: MemberProgress[];
};

const STATUS_OPTIONS = [
  ["pending", "Pending"],
  ["typ_member", "TYP member"],
  ["kilpauk_member", "Kilpauk member"],
  ["success", "Success"],
  ["no_answer", "Call didn't pick up"],
  ["invalid", "Number invalid"],
  ["follow_up", "Need to follow up"],
];
const DESTINATION_OPTIONS = [
  ["chennai", "Chennai"],
  ["kilpauk", "Kilpauk"],
  ["typ", "TYP"],
  ["other", "Other / collected"],
];

function statusClass(status: string) {
  return status.replaceAll("_", "-");
}

function ContactRow({
  contact,
  isAdmin,
  requiresCollection,
  onSaved,
  notify,
}: {
  contact: Contact;
  isAdmin: boolean;
  requiresCollection: boolean;
  onSaved: (updated: Contact) => void;
  notify: (message: string, isError?: boolean) => void;
}) {
  const [status, setStatus] = useState(contact.status);
  const [destination, setDestination] = useState(contact.destination);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setStatus(contact.status);
    setDestination(contact.destination);
  }, [contact.status, contact.destination]);

  async function save() {
    setSaving(true);
    try {
      const result = await apiRequest<{ contact: Contact }>(
        `/api/contacts/${contact.id}/status`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status, destination }),
        },
      );
      onSaved(result.contact);
      notify("Contact updated. Thank you for following through.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not update this contact.", true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr>
      <td>
        <div className="contact-person">
          <span className="contact-avatar">{initials(contact.name)}</span>
          <span><span className="contact-name">{contact.name}</span><span className="contact-phone">{contact.phone}</span></span>
        </div>
      </td>
      {isAdmin && <td>{contact.assignedTo}</td>}
      <td>
        <span className={`badge ${statusClass(contact.status)}`}>{contact.statusDisplay}</span>
        {contact.destinationDisplay && <div className="contact-phone">{contact.destinationDisplay}</div>}
      </td>
      <td>
        <div className="table-actions">
          <a className="icon-button" href={`tel:${contact.phone}`} aria-label={`Call ${contact.name}`} title="Call contact"><Phone size={14} /></a>
          <a className="icon-button" href={`sms:${contact.phone}`} aria-label={`Text ${contact.name}`} title="Text contact"><Send size={13} /></a>
        </div>
      </td>
      <td>
        <div className="table-update">
          <select
            className="select"
            aria-label={`Status for ${contact.name}`}
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {STATUS_OPTIONS
              .filter(([value]) => !(requiresCollection || contact.requiresCollection) || value === status || !["success", "typ_member", "kilpauk_member"].includes(value))
              .map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          {status === "success" && (
            <select
              className="select destination-select"
              aria-label={`Destination for ${contact.name}`}
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
            >
              <option value="">Destination</option>
              {DESTINATION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          )}
          <button className="icon-button" type="button" aria-label={`Save ${contact.name}`} title="Save update" disabled={saving} onClick={save}>
            {saving ? <span className="spinner" style={{ width: 13, height: 13, borderWidth: 2 }} /> : <Check size={15} />}
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [user, setUser] = useState<ApiUser | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState("");
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const loadDashboard = useCallback(async () => {
    const session = await apiRequest<{ user: ApiUser | null }>("/api/session");
    if (!session.user) {
      router.replace("/login");
      return;
    }
    setUser(session.user);
    const dashboard = await apiRequest<DashboardData>("/api/dashboard");
    setData(dashboard);
  }, [router]);

  useEffect(() => {
    loadDashboard()
      .catch((error: unknown) => notify(error instanceof Error ? error.message : "Could not load the workspace.", true))
      .finally(() => setLoading(false));
  }, [loadDashboard, notify]);

  const visibleContacts = useMemo(() => {
    const contacts = data?.contacts || [];
    const normalized = query.trim().toLowerCase();
    return contacts.filter((contact) => {
      const matchesQuery = !normalized
        || contact.name.toLowerCase().includes(normalized)
        || contact.phone.toLowerCase().includes(normalized);
      return matchesQuery && (statusFilter === "all" || contact.status === statusFilter);
    });
  }, [data?.contacts, query, statusFilter]);

  async function importFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      notify("Choose a CSV or Excel file to import.", true);
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    try {
      const result = await apiRequest<{ message: string }>("/api/contacts/import", {
        method: "POST",
        body: formData,
      });
      if (fileRef.current) fileRef.current.value = "";
      setSelectedFile("");
      notify(result.message);
      await loadDashboard();
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not import this file.", true);
    } finally {
      setUploading(false);
    }
  }

  function updateContact(updated: Contact) {
    setData((current) => {
      if (!current) return current;
      const previous = current.contacts.find((contact) => contact.id === updated.id)?.status;
      const stats = { ...current.stats };
      if (previous && previous !== updated.status) {
        stats[previous] = Math.max(0, (stats[previous] || 0) - 1);
        stats[updated.status] = (stats[updated.status] || 0) + 1;
      }
      return {
        ...current,
        contacts: current.contacts.map((contact) => contact.id === updated.id ? updated : contact),
        stats,
      };
    });
  }

  if (loading) {
    return <div className="loading-screen"><span className="spinner" aria-label="Loading workspace" /></div>;
  }
  if (!user || !data) {
    return <div className="loading-screen"><div className="login-error">We couldn’t load the workspace. Please refresh and try again.</div></div>;
  }

  const stats = data.stats;
  const callbackCount = (stats.follow_up || 0) + (stats.no_answer || 0);
  const reached = stats.reached ?? stats.success ?? 0;
  const completion = stats.total ? Math.round((reached / stats.total) * 100) : 0;

  return (
    <Shell user={user} active="dashboard">
      {toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.message}</div>}
      <section className="page-content">
        <div className="page-head">
          <div>
            <div className="eyebrow"><span className="eyebrow-dot" /> YOUR COMMUNITY, IN GOOD HANDS</div>
            <h1>{user.isAdmin ? "A little progress, together." : "Your conversations matter."}</h1>
            <p>{user.isAdmin ? "Here’s the latest rhythm of your committee outreach." : "Here’s where your thoughtful follow-ups stand."}</p>
          </div>
          {user.isAdmin && (
            <a className="button secondary" href="/api/contacts/export.xlsx">
              <ArrowDownToLine size={15} /> <span>Export report</span>
            </a>
          )}
        </div>

        <div className="stat-grid">
          <StatCard label="Total contacts" value={stats.total || 0} detail="Across your workspace" icon={<UsersRound size={16} />} accent="#648e73" soft="#edf4eb" />
          <StatCard label="Calls completed" value={reached} detail={`${completion}% of all contacts`} icon={<CheckCheck size={16} />} accent="#66936b" soft="#eaf4e9" />
          <StatCard label="Needs a call back" value={callbackCount} detail="Follow-ups & missed calls" icon={<Headphones size={16} />} accent="#cb8954" soft="#fff3e8" />
          <StatCard label="Yet to contact" value={stats.pending || 0} detail="Ready for a first hello" icon={<Clock3 size={16} />} accent="#758394" soft="#eef2f6" />
        </div>

        {!user.isAdmin && (
          <section className="panel call-guide" aria-labelledby="call-guide-title">
            <div className="panel-head">
              <div><h2 id="call-guide-title">Quick guide for your calls</h2><p>A simple path from hello to a complete record.</p></div>
              <a className="text-link" href="/tasks">Open assigned tasks <ArrowRight size={13} /></a>
            </div>
            <div className="guide-steps">
              <GuideStep number="01" title="Ask age and area" text="Confirm their age and current area respectfully." />
              <GuideStep number="02" title="Classify correctly" text="Over 21 → TYP. Otherwise, a listed Kilpauk area → Kilpauk. TYP takes priority." />
              <GuideStep number="03" title="Collect and save" text="For everyone else, mark successful and complete every required field in your assigned data task." />
            </div>
            <p className="guide-foot">Kilpauk areas: Ayanavaram, Kilpauk, Vepery, Puraswalkam, North Town and ICF.</p>
          </section>
        )}

        <div className="content-grid">
          {user.isAdmin && (
            <section className="panel" aria-labelledby="progress-title">
              <div className="panel-head">
                <div><h2 id="progress-title">Committee pulse</h2><p>Progress from your active members</p></div>
                <PageLink href="/members">Manage team</PageLink>
              </div>
              <div className="progress-list">
                {data.memberStats?.length ? data.memberStats.map((member) => {
                  const percent = member.total ? Math.round((member.reached / member.total) * 100) : 0;
                  return (
                    <div key={member.id}>
                      <div className="progress-row-head">
                        <div className="progress-person">
                          <span className="mini-avatar">{initials(member.name)}</span>
                          <span><strong>{member.name}</strong><span>{member.mobile}</span></span>
                        </div>
                        <span className="progress-count">{member.reached} / {member.total} reached</span>
                      </div>
                      <div className="progress-track"><div className={`progress-fill ${percent < 30 ? "warm" : ""}`} style={{ width: `${percent}%` }} /></div>
                    </div>
                  );
                }) : (
                  <div className="empty-note">Add committee members to share contact assignments and follow their progress here.</div>
                )}
              </div>
            </section>
          )}

          {user.isAdmin ? (
            <section className="panel import-panel" aria-labelledby="import-title">
              <div className="panel-head">
                <h2 id="import-title"><MessageCircle size={18} style={{ verticalAlign: "middle", marginRight: 7 }} />WhatsApp group contacts</h2>
                <p>Sign in to WhatsApp Web, scan the group’s visible participant list with the companion extension, then import its CSV here.</p>
              </div>
              <a className="button whatsapp-open" href="https://web.whatsapp.com/" target="_blank" rel="noreferrer">
                <MessageCircle size={15} /> Open WhatsApp Web
              </a>
              <div className="whatsapp-note">Open your group and participant list, then use the installed Sangam contact scanner. Review the downloaded list before importing.</div>
              <form onSubmit={importFile}>
                <label className="import-drop" htmlFor="contact-file">
                  <Upload size={20} />
                  <span>{selectedFile || "Choose the scanned CSV or Excel file"}</span>
                  <small>CSV or XLSX · names and mobile numbers</small>
                </label>
                <input
                  ref={fileRef}
                  id="contact-file"
                  type="file"
                  accept=".csv,.xlsx"
                  hidden
                  onChange={(event) => setSelectedFile(event.target.files?.[0]?.name || "")}
                />
                <button className="button" type="submit" disabled={uploading}>
                  <FileSpreadsheet size={15} /> {uploading ? "Importing contacts…" : "Import & distribute"}
                </button>
              </form>
              <details className="whatsapp-help">
                <summary>First time? Set up the participant scanner</summary>
                <ol>
                  <li>Open your browser’s extensions page and enable Developer mode.</li>
                  <li>Choose “Load unpacked” and select this project’s <code>whatsapp-extension</code> folder.</li>
                  <li>Open WhatsApp Web, sign in, open the authorized group and its participant list, then scan visible members.</li>
                  <li>Review the downloaded CSV and import it above.</li>
                </ol>
              </details>
            </section>
          ) : (
            <section className="panel import-panel" aria-labelledby="member-note-title">
              <div className="panel-head">
                <h2 id="member-note-title">Make the connection</h2>
                <p>Reach out when it feels right, then record the outcome so your team can follow along.</p>
              </div>
              <div className="import-drop"><Phone size={20} /><span>Your next conversation can make a difference.</span><small>Small steps create lasting connections.</small></div>
            </section>
          )}
        </div>

        <section className="panel table-panel" aria-labelledby="contacts-title">
          <div className="panel-head">
            <div><h2 id="contacts-title">{user.isAdmin ? "All contacts" : "My contacts"}</h2><p>Keep every connection moving forward</p></div>
            <div className="table-actions">
              <label className="search-box">
                <Search size={15} />
                <input aria-label="Search contacts" placeholder="Search people…" value={query} onChange={(event) => setQuery(event.target.value)} />
              </label>
              <select className="filter-select" aria-label="Filter by status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="all">All status</option>
                {STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>
          </div>
          <div className="table-scroll">
            <table className="contact-table">
              <thead><tr><th>Contact</th>{user.isAdmin && <th>Assigned to</th>}<th>Outcome</th><th>Reach out</th><th>Update status</th></tr></thead>
              <tbody>
                {visibleContacts.map((contact) => (
                  <ContactRow key={contact.id} contact={contact} isAdmin={user.isAdmin} requiresCollection={data.requiresCollection} onSaved={updateContact} notify={notify} />
                ))}
                {!visibleContacts.length && (
                  <tr><td className="empty-table" colSpan={user.isAdmin ? 5 : 4}>
                    {query || statusFilter !== "all" ? "No contacts match your search." : "No contacts yet. Your administrator can import a CSV or Excel file."}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="panel-head" style={{ margin: 0, padding: "12px 20px", borderTop: "1px solid #f0f2ef" }}>
            <p style={{ margin: 0 }}>Showing {visibleContacts.length} of {data.contacts.length} contacts</p>
            {user.isAdmin && <PageLink href="/members">View committee <ArrowRight size={13} /></PageLink>}
          </div>
        </section>
        <p className="empty-note" style={{ textAlign: "center" }}>
          {user.isAdmin ? "Only scan and import participant information you are authorized to use." : <><CircleHelp size={12} style={{ verticalAlign: "middle" }} /> Need a hand? Reach out to your committee administrator.</>}
        </p>
      </section>
    </Shell>
  );
}

function GuideStep({ number, title, text }: { number: string; title: string; text: string }) {
  return (
    <div className="guide-step">
      <span className="guide-number">{number}</span>
      <span><strong>{title}</strong><span>{text}</span></span>
    </div>
  );
}

function StatCard({
  label,
  value,
  detail,
  icon,
  accent,
  soft,
}: {
  label: string;
  value: number;
  detail: string;
  icon: ReactNode;
  accent: string;
  soft: string;
}) {
  return (
    <div className="stat-card" style={{ "--accent": accent, "--accent-soft": soft } as CSSProperties}>
      <div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div>
      <div className="stat-value">{value.toLocaleString()}</div>
      <div className="stat-foot">{detail}</div>
    </div>
  );
}

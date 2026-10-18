"use client";

import {
  Archive,
  ArrowRight,
  Check,
  ClipboardList,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { ApiUser } from "../../lib/api";
import { apiRequest } from "../../lib/api";
import Shell from "../components/Shell";

type FieldType = "text" | "long_text" | "number" | "date" | "boolean";
type TaskField = { key: string; label: string; type: FieldType; required: boolean };
type Member = { id: number; name: string; mobile: string; active: boolean };
type Task = {
  id: number;
  title: string;
  instructions: string;
  fields: TaskField[];
  active: boolean;
  assignedMembers: { id: number; name: string; active: boolean }[];
};
type TaskContact = {
  id: number;
  name: string;
  phone: string;
  status: string;
  submission: null | {
    age: number;
    area: string;
    classification: string;
    fields: Record<string, string | boolean>;
  };
};

const AREA_OPTIONS = [
  "Ayanavaram",
  "Kilpauk",
  "Vepery",
  "Puraswalkam",
  "North Town",
  "ICF",
  "Other",
];

function fieldKey(label: string) {
  const key = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40);
  return /^[a-z]/.test(key) ? key : `field_${key}`.slice(0, 40);
}

export default function TasksPage() {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Task | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [fields, setFields] = useState<TaskField[]>([]);
  const [memberIds, setMemberIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [contacts, setContacts] = useState<TaskContact[]>([]);
  const [contactId, setContactId] = useState("");
  const [age, setAge] = useState("");
  const [area, setArea] = useState("");
  const [otherArea, setOtherArea] = useState("");
  const [answers, setAnswers] = useState<Record<string, string | boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const load = useCallback(async () => {
    const session = await apiRequest<{ user: ApiUser | null }>("/api/session");
    if (!session.user) {
      window.location.replace("/login");
      return;
    }
    setUser(session.user);
    const result = await apiRequest<{ tasks: Task[] }>("/api/tasks");
    setTasks(result.tasks);
    if (session.user.isAdmin) {
      const membersResult = await apiRequest<{ members: Member[] }>("/api/members");
      setMembers(membersResult.members.filter((member) => member.active));
    }
  }, []);

  useEffect(() => {
    load()
      .catch((error: unknown) => notify(error instanceof Error ? error.message : "Could not load data tasks.", true))
      .finally(() => setLoading(false));
  }, [load, notify]);

  function resetEditor(task?: Task) {
    setEditing(task || null);
    setTitle(task?.title || "");
    setInstructions(task?.instructions || "");
    setFields(task?.fields.map((field) => ({ ...field })) || []);
    setMemberIds(task?.assignedMembers.filter((member) => member.active).map((member) => member.id) || []);
    setEditorOpen(true);
  }

  function changeField(index: number, patch: Partial<TaskField>) {
    setFields((current) => current.map((field, i) => i === index ? { ...field, ...patch } : field));
  }

  function addField() {
    setFields((current) => [...current, { key: `field_${current.length + 1}`, label: "", type: "text", required: true }]);
  }

  async function saveTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = { title, instructions, fields, memberIds };
      const result = await apiRequest<{ task: Task }>(
        editing ? `/api/tasks/${editing.id}` : "/api/tasks",
        {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      setTasks((current) => {
        const next = editing
          ? current.map((task) => task.id === result.task.id ? result.task : task)
          : [result.task, ...current];
        return next.sort((a, b) => b.id - a.id);
      });
      setEditorOpen(false);
      notify(editing ? "Task updated." : "New data task assigned.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not save this task.", true);
    } finally {
      setSaving(false);
    }
  }

  async function toggleTask(task: Task) {
    if (task.active && !window.confirm(`Disable “${task.title}”? Members will no longer be able to submit it; existing collected data will be kept.`)) return;
    try {
      if (task.active) {
        await apiRequest(`/api/tasks/${task.id}`, { method: "DELETE" });
        setTasks((current) => current.map((item) => item.id === task.id ? { ...item, active: false } : item));
        notify("Task disabled. Existing collected data is preserved.");
      } else {
        const result = await apiRequest<{ task: Task }>(`/api/tasks/${task.id}/enable`, { method: "POST" });
        setTasks((current) => current.map((item) => item.id === task.id ? result.task : item));
        notify("Task enabled.");
      }
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not update this task.", true);
    }
  }

  async function startTask(task: Task) {
    setSelectedTask(task);
    setContactId("");
    setContacts([]);
    setAge("");
    setArea("");
    setOtherArea("");
    setAnswers({});
    try {
      const result = await apiRequest<{ contacts: TaskContact[] }>(`/api/tasks/${task.id}/contacts`);
      setContacts(result.contacts);
      if (!result.contacts.length) notify("No contacts are assigned to your account yet.", true);
    } catch (error) {
      setSelectedTask(null);
      notify(error instanceof Error ? error.message : "Could not open this task.", true);
    }
  }

  function chooseContact(value: string) {
    setContactId(value);
    const contact = contacts.find((item) => item.id === Number(value));
    const submission = contact?.submission;
    setAge(submission ? String(submission.age) : "");
    setArea(submission && AREA_OPTIONS.includes(submission.area) ? submission.area : submission ? "Other" : "");
    setOtherArea(submission && !AREA_OPTIONS.includes(submission.area) ? submission.area : "");
    setAnswers(submission?.fields || {});
  }

  async function submitCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTask) return;
    setSubmitting(true);
    try {
      const result = await apiRequest<{ classificationDisplay: string; status: string }>(
        `/api/tasks/${selectedTask.id}/submissions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contactId: Number(contactId),
            age: Number(age),
            area: area === "Other" ? otherArea : area,
            fields: answers,
          }),
        },
      );
      notify(`Saved successfully — ${result.classificationDisplay}.`);
      setContacts((current) => current.map((contact) => contact.id === Number(contactId)
        ? { ...contact, status: result.status, submission: { age: Number(age), area: area === "Other" ? otherArea : area, classification: result.classificationDisplay, fields: answers } }
        : contact));
      setSelectedTask(null);
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not save collected details.", true);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="loading-screen"><span className="spinner" aria-label="Loading tasks" /></div>;
  if (!user) return <div className="loading-screen"><div className="login-error">Sign in to view your data tasks.</div></div>;

  return (
    <Shell user={user} active="tasks">
      {toast && <div className={`toast ${toast.error ? "error" : ""}`} role="status">{toast.message}</div>}
      <section className="page-content">
        <div className="page-head">
          <div>
            <div className="eyebrow"><span className="eyebrow-dot" /> CALL WITH CARE, RECORD WITH CONFIDENCE</div>
            <h1>{user.isAdmin ? "Data collection tasks" : "Your assigned tasks"}</h1>
            <p>{user.isAdmin ? "Create clear instructions, choose required details, and assign each task to members." : "Follow the task instructions and capture every required detail during your calls."}</p>
          </div>
          {user.isAdmin && <button className="button" type="button" onClick={() => resetEditor()}><Plus size={16} /> New task</button>}
        </div>

        {!user.isAdmin && (
          <section className="panel call-guide" aria-labelledby="call-guide-title">
            <div className="panel-head"><div><h2 id="call-guide-title">Quick instructions for your calls</h2><p>Ask politely, confirm the details, then complete the selected task.</p></div></div>
            <div className="guide-steps">
              <GuideStep number="01" title="Ask age and area" text="Confirm both before deciding the call outcome." />
              <GuideStep number="02" title="Apply the member rule" text="Over 21 is TYP. Otherwise, Ayanavaram, Kilpauk, Vepery, Puraswalkam, North Town or ICF is Kilpauk. TYP takes priority if both match." />
              <GuideStep number="03" title="Record the details" text="If neither rule matches, mark it successful and complete every required field in the assigned task." />
            </div>
          </section>
        )}

        {user.isAdmin && editorOpen && (
          <section className="panel task-editor" aria-labelledby="task-editor-title">
            <div className="panel-head">
              <div><h2 id="task-editor-title">{editing ? "Edit data task" : "Create a data task"}</h2><p>Field labels can match the shared spreadsheet. Age and area are collected separately for member classification.</p></div>
              <button className="icon-button" type="button" aria-label="Close task editor" onClick={() => setEditorOpen(false)}><X size={15} /></button>
            </div>
            <form onSubmit={saveTask}>
              <div className="task-editor-grid">
                <div className="form-field">
                  <label className="field-label" htmlFor="task-title">Task name</label>
                  <div className="input-wrap"><input id="task-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={150} placeholder="e.g. Community data collection" required /></div>
                </div>
                <div className="form-field">
                  <label className="field-label" htmlFor="task-instructions">Instructions for callers</label>
                  <textarea className="task-textarea" id="task-instructions" value={instructions} onChange={(event) => setInstructions(event.target.value)} maxLength={4000} placeholder="Explain what to ask and how to complete this task…" required />
                </div>
              </div>
              <div className="task-fields-head"><div><strong>Details to collect</strong><span>Add the column headings from the shared Excel sheet.</span></div><button className="button secondary small" type="button" onClick={addField}><Plus size={14} /> Add field</button></div>
              <div className="task-field-list">
                {fields.map((field, index) => (
                  <div className="task-field-row" key={`${field.key}-${index}`}>
                    <input aria-label={`Field ${index + 1} label`} value={field.label} maxLength={80} placeholder="Excel column / question" onChange={(event) => changeField(index, { label: event.target.value, key: fieldKey(event.target.value) })} />
                    <select aria-label={`Field ${index + 1} type`} value={field.type} onChange={(event) => changeField(index, { type: event.target.value as FieldType })}>
                      <option value="text">Short answer</option><option value="long_text">Long answer</option><option value="number">Number</option><option value="date">Date</option><option value="boolean">Yes / no</option>
                    </select>
                    <label className="required-toggle"><input type="checkbox" checked={field.required} onChange={(event) => changeField(index, { required: event.target.checked })} /> Required</label>
                    <button className="icon-button" type="button" aria-label={`Remove field ${index + 1}`} onClick={() => setFields((current) => current.filter((_, i) => i !== index))}><X size={14} /></button>
                  </div>
                ))}
                {!fields.length && <p className="empty-note">No extra fields yet. Age and area are always included automatically.</p>}
              </div>
              <div className="task-fields-head"><div><strong>Assign to members</strong><span>Select one or more active committee members.</span></div></div>
              <div className="member-checkboxes">
                {members.map((member) => (
                  <label className="member-checkbox" key={member.id}>
                    <input type="checkbox" checked={memberIds.includes(member.id)} onChange={(event) => setMemberIds((current) => event.target.checked ? [...current, member.id] : current.filter((id) => id !== member.id))} />
                    <span><strong>{member.name}</strong><small>{member.mobile}</small></span>
                  </label>
                ))}
                {!members.length && <p className="empty-note">Add an active committee member before assigning a task.</p>}
              </div>
              <div className="task-editor-actions">
                <button className="button secondary" type="button" onClick={() => setEditorOpen(false)}>Cancel</button>
                <button className="button" type="submit" disabled={saving || !members.length}><Save size={15} /> {saving ? "Saving…" : editing ? "Save changes" : "Create & assign task"}</button>
              </div>
            </form>
          </section>
        )}

        {!user.isAdmin && selectedTask && (
          <section className="panel collection-panel" aria-labelledby="collection-title">
            <div className="panel-head">
              <div><h2 id="collection-title">{selectedTask.title}</h2><p>{selectedTask.instructions}</p></div>
              <button className="icon-button" type="button" aria-label="Close collection form" onClick={() => setSelectedTask(null)}><X size={15} /></button>
            </div>
            <form onSubmit={submitCollection}>
              <div className="collection-grid">
                <div className="form-field full-span">
                  <label className="field-label" htmlFor="contact-choice">Contact assigned to you</label>
                  <select className="select full-width" id="contact-choice" value={contactId} onChange={(event) => chooseContact(event.target.value)} required>
                    <option value="">Choose a contact</option>
                    {contacts.map((contact) => <option value={contact.id} key={contact.id}>{contact.name} · {contact.phone}{contact.submission ? " · previously collected" : ""}</option>)}
                  </select>
                </div>
                <div className="form-field">
                  <label className="field-label" htmlFor="contact-age">Age</label>
                  <div className="input-wrap"><input id="contact-age" type="number" min="0" max="130" value={age} onChange={(event) => setAge(event.target.value)} required /></div>
                  <small className="field-hint">Over 21 is classified as TYP.</small>
                </div>
                <div className="form-field">
                  <label className="field-label" htmlFor="contact-area">Area</label>
                  <select className="select full-width" id="contact-area" value={area} onChange={(event) => setArea(event.target.value)} required>
                    <option value="">Choose area</option>{AREA_OPTIONS.map((option) => <option key={option}>{option}</option>)}
                  </select>
                  <small className="field-hint">If both match, TYP takes priority.</small>
                </div>
                {area === "Other" && <div className="form-field full-span"><label className="field-label" htmlFor="other-area">Enter area</label><div className="input-wrap"><input id="other-area" value={otherArea} onChange={(event) => setOtherArea(event.target.value)} maxLength={120} required /></div></div>}
                {selectedTask.fields.map((field) => (
                  <div className={`form-field ${field.type === "long_text" ? "full-span" : ""}`} key={field.key}>
                    <label className="field-label" htmlFor={`answer-${field.key}`}>{field.label}{field.required ? " *" : " (optional)"}</label>
                    {field.type === "long_text" ? (
                      <textarea className="task-textarea" id={`answer-${field.key}`} value={String(answers[field.key] ?? "")} required={field.required} maxLength={2000} onChange={(event) => setAnswers((current) => ({ ...current, [field.key]: event.target.value }))} />
                    ) : field.type === "boolean" ? (
                      <select className="select full-width" id={`answer-${field.key}`} value={answers[field.key] === true ? "true" : answers[field.key] === false ? "false" : ""} required={field.required} onChange={(event) => setAnswers((current) => ({ ...current, [field.key]: event.target.value === "true" }))}>
                        <option value="">Choose yes or no</option><option value="true">Yes</option><option value="false">No</option>
                      </select>
                    ) : (
                      <div className="input-wrap"><input id={`answer-${field.key}`} type={field.type} value={String(answers[field.key] ?? "")} required={field.required} maxLength={2000} onChange={(event) => setAnswers((current) => ({ ...current, [field.key]: event.target.value }))} /></div>
                    )}
                  </div>
                ))}
              </div>
              <div className="task-editor-actions">
                <button className="button secondary" type="button" onClick={() => setSelectedTask(null)}>Cancel</button>
                <button className="button" type="submit" disabled={submitting || !contactId}><Check size={15} /> {submitting ? "Saving details…" : "Save details & mark successful"}</button>
              </div>
            </form>
          </section>
        )}

        <div className="task-list">
          {tasks.map((task) => {
            const assignedNames = task.assignedMembers.map((member) => member.name).join(", ");
            const doneCount = contacts.filter((contact) => contact.submission).length;
            return (
              <article className={`panel task-card ${task.active ? "" : "disabled"}`} key={task.id}>
                <div className="task-card-icon"><ClipboardList size={19} /></div>
                <div className="task-card-copy">
                  <div className="task-card-title">{task.title}<span className={`task-state ${task.active ? "active" : ""}`}>{task.active ? "Active" : "Disabled"}</span></div>
                  <p>{task.instructions}</p>
                  <div className="task-meta"><span>{task.fields.length + 2} data fields</span><span>Assigned to {assignedNames || "no active members"}</span></div>
                  {task.fields.length > 0 && <div className="task-field-chips">{task.fields.map((field) => <span key={field.key}>{field.label}</span>)}</div>}
                </div>
                {user.isAdmin ? (
                  <div className="task-card-actions">
                    <button className="icon-button" type="button" title={`Edit ${task.title}`} aria-label={`Edit ${task.title}`} onClick={() => resetEditor(task)}><Pencil size={14} /></button>
                    <button className={`icon-button ${task.active ? "danger-outline" : ""}`} type="button" title={task.active ? "Disable task" : "Enable task"} aria-label={task.active ? `Disable ${task.title}` : `Enable ${task.title}`} onClick={() => toggleTask(task)}>{task.active ? <Archive size={14} /> : <RotateCcw size={14} />}</button>
                  </div>
                ) : task.active ? (
                  <button className="button small" type="button" onClick={() => startTask(task)}> {contacts.length && selectedTask?.id === task.id ? `${doneCount} collected` : "Start task"} <ArrowRight size={14} /></button>
                ) : null}
              </article>
            );
          })}
          {!tasks.length && <section className="panel empty-task-state"><ClipboardList size={25} /><h2>{user.isAdmin ? "No data tasks yet" : "No tasks assigned yet"}</h2><p>{user.isAdmin ? "Create a task, add the details your spreadsheet requires, and assign it to committee members." : "Your administrator will assign data collection tasks here."}</p>{user.isAdmin && <button className="button" type="button" onClick={() => resetEditor()}><Plus size={15} /> Create your first task</button>}</section>}
        </div>
      </section>
    </Shell>
  );
}

function GuideStep({ number, title, text }: { number: string; title: string; text: string }) {
  return <div className="guide-step"><span className="guide-number">{number}</span><span><strong>{title}</strong><span>{text}</span></span></div>;
}

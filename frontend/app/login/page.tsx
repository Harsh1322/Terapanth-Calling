"use client";

import { ArrowRight, LockKeyhole, Smartphone, Waypoints } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest, type ApiUser } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mobile, setMobile] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiRequest<{ user: ApiUser | null }>("/api/session")
      .then(({ user }) => {
        if (user) router.replace("/");
      })
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : "Could not check your sign-in status.");
      });
  }, [router]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiRequest("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile }),
      });
      router.replace("/");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign in.");
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-art">
        <a className="brand" href="/" aria-label="Sangam home">
          <span className="brand-mark"><Waypoints size={21} /></span>
          <span className="brand-copy">sangam<small>outreach workspace</small></span>
        </a>
        <div className="login-art-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> PEOPLE FIRST, ALWAYS</div>
          <h1>Good things<br />begin with a <span>hello.</span></h1>
          <p>A calmer, more thoughtful way to organize the conversations that bring your community together.</p>
        </div>
        <div className="login-quote">
          “The smallest act of kindness is worth more than the grandest intention.”
          <strong>— Your committee outreach workspace</strong>
        </div>
      </section>

      <section className="login-form-side">
        <div className="login-form-wrap">
          <div className="mobile-brand brand">
            <span className="brand-mark"><Waypoints size={21} /></span>
            <span className="brand-copy">sangam<small>outreach workspace</small></span>
          </div>
          <div className="eyebrow"><span className="eyebrow-dot" /> WELCOME BACK</div>
          <h2>Sign in to Sangam</h2>
          <p>Your community is just a conversation away.</p>

          {error && <div className="login-error" role="alert">{error}</div>}
          <form onSubmit={signIn}>
            <div className="form-field">
              <label className="field-label" htmlFor="mobile">Registered mobile number</label>
              <div className="input-wrap">
                <Smartphone size={17} />
                <input
                  id="mobile"
                  name="mobile"
                  autoComplete="tel"
                  inputMode="tel"
                  placeholder="Enter your mobile number"
                  value={mobile}
                  onChange={(event) => setMobile(event.target.value)}
                  required
                  autoFocus
                />
              </div>
            </div>
            <button className="button login-submit" type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Continue"} <ArrowRight size={16} />
            </button>
          </form>
          <div className="login-note"><LockKeyhole size={14} /> Sign in with the mobile number registered by your committee administrator.</div>
        </div>
      </section>
    </main>
  );
}

import { useState, useEffect } from "react";
import axios from "axios";

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const api = axios.create({ baseURL: "https://autobrief-1.onrender.com" });

// ─── Preferences Form ──────────────────────────────────────────────────────

function PreferencesForm() {
  const [form, setForm] = useState({
    city: "",
    news_topics: "",
    telegram_chat_id: "",
  });
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/preferences")
      .then((r) => {
        if (r.data) {
          setForm({
            city: r.data.city || "",
            news_topics: r.data.news_topics || "",
            telegram_chat_id: r.data.telegram_chat_id || "",
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    await api.post("/preferences", form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading)
    return <p className="text-gray-400 animate-pulse">Loading preferences…</p>;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          City (Weather)
        </label>
        <input
          type="text"
          value={form.city}
          onChange={(e) => setForm({ ...form, city: e.target.value })}
          className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          placeholder="e.g. New York"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          News Topics
        </label>
        <input
          type="text"
          value={form.news_topics}
          onChange={(e) => setForm({ ...form, news_topics: e.target.value })}
          className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          placeholder="e.g. technology, science"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Telegram Chat ID
        </label>
        <input
          type="text"
          value={form.telegram_chat_id}
          onChange={(e) =>
            setForm({ ...form, telegram_chat_id: e.target.value })
          }
          className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          placeholder="Numeric ID, e.g. 123456789"
          required
        />
        <p className="text-xs text-gray-500 mt-1">
          Message <span className="text-gray-400">@userinfobot</span> on Telegram to get your numeric chat ID.
        </p>
      </div>
      <button
        type="submit"
        className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2.5 font-semibold transition-colors"
      >
        Save Preferences
      </button>
      {saved && (
        <p className="text-emerald-400 text-sm text-center">
          ✓ Preferences saved!
        </p>
      )}
    </form>
  );
}

// ─── Schedule Manager ───────────────────────────────────────────────────────

function ScheduleManager() {
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState({
    day_of_week: "Monday",
    time: "09:00",
    subject: "",
    location: "",
  });
  const [editingId, setEditingId] = useState(null);

  const load = () =>
    api.get("/schedule").then((r) => setEntries(r.data));

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (editingId) {
      await api.put(`/schedule/${editingId}`, form);
      setEditingId(null);
    } else {
      await api.post("/schedule", form);
    }
    setForm({ day_of_week: "Monday", time: "09:00", subject: "", location: "" });
    load();
  };

  const handleEdit = (entry) => {
    setEditingId(entry.id);
    setForm({
      day_of_week: entry.day_of_week,
      time: entry.time,
      subject: entry.subject,
      location: entry.location,
    });
  };

  const handleDelete = async (id) => {
    await api.delete(`/schedule/${id}`);
    load();
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm({ day_of_week: "Monday", time: "09:00", subject: "", location: "" });
  };

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      >
        <select
          value={form.day_of_week}
          onChange={(e) => setForm({ ...form, day_of_week: e.target.value })}
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
        >
          {DAYS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <input
          type="time"
          value={form.time}
          onChange={(e) => setForm({ ...form, time: e.target.value })}
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          required
        />
        <input
          type="text"
          value={form.subject}
          onChange={(e) => setForm({ ...form, subject: e.target.value })}
          placeholder="Subject"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          required
        />
        <input
          type="text"
          value={form.location}
          onChange={(e) => setForm({ ...form, location: e.target.value })}
          placeholder="Location"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
        />
        <div className="col-span-2 sm:col-span-4 flex gap-2">
          <button
            type="submit"
            className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 font-semibold transition-colors"
          >
            {editingId ? "Update" : "Add Class"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded-lg bg-gray-700 hover:bg-gray-600 px-4 py-2 font-semibold transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {entries.length === 0 ? (
        <p className="text-gray-500 text-sm">No classes added yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-800">
                <th className="pb-2 pr-4">Day</th>
                <th className="pb-2 pr-4">Time</th>
                <th className="pb-2 pr-4">Subject</th>
                <th className="pb-2 pr-4">Location</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr
                  key={e.id}
                  className="border-b border-gray-800/50 hover:bg-gray-800/40"
                >
                  <td className="py-2 pr-4">{e.day_of_week}</td>
                  <td className="py-2 pr-4 font-mono">{e.time}</td>
                  <td className="py-2 pr-4">{e.subject}</td>
                  <td className="py-2 pr-4 text-gray-400">{e.location || "—"}</td>
                  <td className="py-2 text-right space-x-2">
                    <button
                      onClick={() => handleEdit(e)}
                      className="text-indigo-400 hover:text-indigo-300 text-xs"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(e.id)}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Briefing Preview Card ──────────────────────────────────────────────────

function BriefingPreview({ data }) {
  const { weather, news, schedule, day, date } = data;

  return (
    <div className="mt-5 rounded-xl overflow-hidden border border-gray-700 bg-gradient-to-br from-gray-900 via-gray-850 to-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
        <h3 className="text-xl font-bold text-white">Daily Briefing</h3>
        <p className="text-indigo-200 text-sm">{day}, {date}</p>
      </div>

      <div className="p-5 space-y-5">
        {/* Weather Card */}
        <div className="rounded-lg bg-gradient-to-br from-sky-900/40 to-blue-900/30 border border-sky-800/40 p-4">
          <h4 className="text-sm font-semibold text-sky-400 uppercase tracking-wider mb-3">
            Weather
          </h4>
          {weather ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center">
                <p className="text-3xl font-bold text-white">{weather.temp}°C</p>
                <p className="text-xs text-sky-300 mt-1">{weather.city}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-white">{weather.wind_speed}</p>
                <p className="text-xs text-sky-300 mt-1">km/h wind</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-white">
                  {weather.humidity != null ? `${weather.humidity}%` : "—"}
                </p>
                <p className="text-xs text-sky-300 mt-1">humidity</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-medium text-white">{weather.description}</p>
                <p className="text-xs text-sky-300 mt-1">conditions</p>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 italic">Weather data unavailable</p>
          )}
        </div>

        {/* News Card */}
        <div className="rounded-lg bg-gradient-to-br from-amber-900/30 to-orange-900/20 border border-amber-800/30 p-4">
          <h4 className="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3">
            Top Headlines
          </h4>
          {news && news.length > 0 ? (
            <div className="space-y-3">
              {news.map((article, i) => (
                <div key={i} className="flex gap-3 items-start">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-600/30 text-amber-400 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-gray-100 hover:text-amber-300 transition-colors font-medium leading-snug block"
                    >
                      {article.title}
                    </a>
                    <p className="text-xs text-amber-500/80 mt-0.5">{article.source}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 italic">No headlines found</p>
          )}
        </div>

        {/* Schedule Card */}
        <div className="rounded-lg bg-gradient-to-br from-emerald-900/30 to-teal-900/20 border border-emerald-800/30 p-4">
          <h4 className="text-sm font-semibold text-emerald-400 uppercase tracking-wider mb-3">
            Today's Classes — {day}
          </h4>
          {schedule && schedule.length > 0 ? (
            <div className="space-y-2">
              {schedule.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-md bg-emerald-950/40 px-3 py-2"
                >
                  <span className="font-mono text-sm text-emerald-300 font-semibold w-14">
                    {entry.time}
                  </span>
                  <span className="text-sm text-gray-100 font-medium">
                    {entry.subject}
                  </span>
                  {entry.location && (
                    <span className="ml-auto text-xs text-emerald-500/80 bg-emerald-900/40 px-2 py-0.5 rounded">
                      {entry.location}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 italic">No classes scheduled for today</p>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 bg-gray-900/80 border-t border-gray-800 text-center">
        <p className="text-xs text-gray-500">Have a productive day!</p>
      </div>
    </div>
  );
}

// ─── Trigger Button ─────────────────────────────────────────────────────────

function TriggerButton() {
  const [status, setStatus] = useState(null);
  const [briefingData, setBriefingData] = useState(null);
  const [activeAction, setActiveAction] = useState(null); // "preview" or "send"

  const trigger = async (endpoint, action) => {
    setActiveAction(action);
    setStatus(null);
    setBriefingData(null);
    try {
      const r = await api.post(endpoint);
      const sent = r.data.sent;
      const detail = r.data.detail;
      if (sent) {
        setStatus({ ok: true, msg: "Briefing sent to Telegram!" });
      } else if (action === "send" && detail) {
        setStatus({ ok: false, msg: detail });
      } else {
        setStatus({ ok: true, msg: "Briefing preview generated." });
      }
      if (r.data.weather !== undefined) {
        setBriefingData(r.data);
      }
    } catch (err) {
      const detail =
        err.response?.data?.detail || err.message || "Unknown error";
      setStatus({ ok: false, msg: detail });
    } finally {
      setActiveAction(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <button
          onClick={() => trigger("/preview", "preview")}
          disabled={activeAction !== null}
          className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-6 py-3 text-lg font-bold transition-colors"
        >
          {activeAction === "preview" ? "Loading…" : "Preview Briefing"}
        </button>
        <button
          onClick={() => trigger("/trigger", "send")}
          disabled={activeAction !== null}
          className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-6 py-3 text-lg font-bold transition-colors"
        >
          {activeAction === "send" ? "Sending…" : "Send via Telegram"}
        </button>
      </div>
      {status && (
        <p
          className={`text-sm ${status.ok ? "text-emerald-400" : "text-red-400"}`}
        >
          {status.msg}
        </p>
      )}
      {briefingData && <BriefingPreview data={briefingData} />}
    </div>
  );
}

// ─── App Shell ──────────────────────────────────────────────────────────────

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-5">
        <h1 className="text-2xl font-bold tracking-tight">
          📋 AutoBrief{" "}
          <span className="text-gray-500 font-normal text-base">
            Daily Briefing Bot
          </span>
        </h1>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-10">
        {/* Preferences */}
        <section className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">⚙️ Preferences</h2>
          <PreferencesForm />
        </section>

        {/* Schedule */}
        <section className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">📚 Class Schedule</h2>
          <ScheduleManager />
        </section>

        {/* Trigger */}
        <section className="rounded-xl bg-gray-900 border border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">🚀 Manual Trigger</h2>
          <TriggerButton />
        </section>
      </main>

      <footer className="text-center text-gray-600 text-xs py-6">
        AutoBrief v1.0 — Scheduled daily at 07:00 AM
      </footer>
    </div>
  );
}

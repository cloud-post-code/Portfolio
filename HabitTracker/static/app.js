/**
 * Daily habit tracker — client UI.
 * @typedef {{ id: number; name: string }} Habit
 * @typedef {{ hours_worked: number | null; wake_time: string | null; bed_time: string | null }} DayMeta
 * @typedef {{ date: string; meta: DayMeta; completions: Record<string, number>; complete: boolean }} DayRow
 */

const state = {
  /** @type {Habit[]} */
  habits: [],
  /** @type {DayRow[]} */
  days: [],
  stats: { current_streak: 0, longest_streak: 0 },
  /** @type {Record<string, number>} */
  habit_streaks: {},
  today: "",
  has_more: true,
};

let wasTodayComplete = false;
let loadedCount = 0;
/** @type {boolean} */
let addingHabit = false;

/** @param {string} msg @param {boolean} [isError] */
function toast(msg, isError) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
  el.classList.toggle("toast--error", !!isError);
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 3200);
}

/** @param {string} url @param {RequestInit} [opts] */
async function fetchJSON(url, opts) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(opts && opts.headers),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || res.statusText || "Request failed");
    /** @type {any} */ (err).status = res.status;
    /** @type {any} */ (err).body = data;
    throw err;
  }
  return data;
}

function burstConfetti() {
  if (typeof confetti !== "function") return;
  const end = Date.now() + 800;
  const frame = () => {
    confetti({
      particleCount: 4,
      angle: 60,
      spread: 55,
      origin: { x: 0 },
      colors: ["#34d399", "#6ee7b7", "#a7f3d0", "#fbbf24"],
    });
    confetti({
      particleCount: 4,
      angle: 120,
      spread: 55,
      origin: { x: 1 },
      colors: ["#34d399", "#6ee7b7", "#a7f3d0", "#fbbf24"],
    });
    if (Date.now() < end) requestAnimationFrame(frame);
  };
  frame();
}

/** @param {string} iso */
function formatHeaderDate(iso) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/** @param {DayMeta} meta */
function metaValueHours(meta) {
  if (meta.hours_worked == null || Number.isNaN(meta.hours_worked)) return "";
  return String(meta.hours_worked);
}

/** @param {string | null | undefined} t */
function metaValueTime(t) {
  if (!t) return "";
  const m = /^(\d{1,2}):(\d{2})/.exec(String(t).trim());
  if (!m) return "";
  const h = Math.min(23, Math.max(0, parseInt(m[1], 10)));
  const min = Math.min(59, Math.max(0, parseInt(m[2], 10)));
  return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
}

/** Normalize `<input type="time">` value to `HH:MM` or null (drops seconds). */
function normalizeTimeValue(raw) {
  if (raw == null || String(raw).trim() === "") return null;
  const m = /^(\d{1,2}):(\d{2})(?::\d{1,2})?/.exec(String(raw).trim());
  if (!m) return null;
  const h = parseInt(m[1], 10);
  const min = parseInt(m[2], 10);
  if (Number.isNaN(h) || Number.isNaN(min) || h < 0 || h > 23 || min < 0 || min > 59) return null;
  return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
}

function applyStats(stats) {
  state.stats = stats;
  const cur = document.getElementById("stat-current");
  const lng = document.getElementById("stat-longest");
  if (cur) cur.textContent = String(stats.current_streak ?? 0);
  if (lng) lng.textContent = String(stats.longest_streak ?? 0);
}

function syncTodayCompleteFlag() {
  const todayRow = state.days[0];
  wasTodayComplete = !!(todayRow && todayRow.complete);
}

/** @param {DayRow} day */
function renderDayMetaHTML(day, compact) {
  const cls = compact ? "day-meta" : "day-meta day-meta--today";
  const hw = metaValueHours(day.meta);
  const w = metaValueTime(day.meta.wake_time);
  const b = metaValueTime(day.meta.bed_time);
  return `
    <div class="${cls}" data-date="${day.date}">
      <div class="field">
        <label for="wake-${day.date}">Wake</label>
        <input type="time" step="60" id="wake-${day.date}" data-field="wake_time" data-date="${day.date}" value="${w}" />
      </div>
      <div class="field">
        <label for="bed-${day.date}">Bed</label>
        <input type="time" step="60" id="bed-${day.date}" data-field="bed_time" data-date="${day.date}" value="${b}" />
      </div>
      <div class="field">
        <label for="hrs-${day.date}">Hours worked</label>
        <input type="number" step="0.25" min="0" max="24" id="hrs-${day.date}" data-field="hours_worked" data-date="${day.date}" value="${hw}" placeholder="—" />
      </div>
    </div>
  `;
}

/** @param {DayRow} day @param {boolean} isToday */
function renderHabitTiles(day, isToday) {
  if (!state.habits.length) {
    return `<p class="header__date" style="margin:0">Add a habit below to start tracking.</p>`;
  }
  return state.habits
    .map((h) => {
      const key = String(h.id);
      const checked = day.completions[key] === 1 ? "checked" : "";
      if (isToday) {
        const streak = state.habit_streaks[key] ?? 0;
        const streakHtml = streak > 0
          ? `<span class="habit-tile__streak">${streak} day streak</span>`
          : `<span class="habit-tile__streak habit-tile__streak--zero">No streak yet</span>`;
        return `
          <div class="habit-tile" data-habit-id="${h.id}">
            <button type="button" class="habit-tile__remove" data-archive="${h.id}" title="Archive habit">×</button>
            <span class="habit-tile__name">${escapeHtml(h.name)}</span>
            ${streakHtml}
            <div class="habit-tile__row">
              <input type="checkbox" data-toggle="${h.id}" data-date="${day.date}" ${checked} aria-label="${escapeHtml(h.name)} done" />
              <span>Done</span>
            </div>
          </div>`;
      }
      return `
        <label class="habit-pill">
          <input type="checkbox" data-toggle="${h.id}" data-date="${day.date}" ${checked} />
          <span title="${escapeHtml(h.name)}">${escapeHtml(h.name)}</span>
        </label>`;
    })
    .join("");
}

/** @param {string} s */
function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderAddTile() {
  if (addingHabit) {
    return `
      <div class="habit-tile habit-tile--add" id="add-tile">
        <form class="add-form" id="add-habit-form">
          <input type="text" name="name" maxlength="200" placeholder="New habit name" autocomplete="off" required autofocus />
          <div class="add-form__actions">
            <button type="submit" class="btn btn--small" style="background:var(--accent-dim);color:#042f2e">Add</button>
            <button type="button" class="btn btn--small btn--ghost" id="add-habit-cancel">Cancel</button>
          </div>
        </form>
      </div>`;
  }
  return `<button type="button" class="habit-tile habit-tile--add" id="add-tile-btn">+ Add habit</button>`;
}

function renderToday() {
  const today = state.days[0];
  const metaEl = document.getElementById("today-meta");
  const grid = document.getElementById("today-habits");
  if (!today || !metaEl || !grid) return;

  metaEl.innerHTML = renderDayMetaHTML(today, false);
  const habitsHtml = renderHabitTiles(today, true);
  grid.innerHTML = habitsHtml + renderAddTile();
  wireTodayGrid(grid);
}

function renderHistory() {
  const list = document.getElementById("history-list");
  if (!list) return;
  const past = state.days.slice(1);
  if (!past.length) {
    list.innerHTML = "";
    return;
  }
  list.innerHTML = past
    .map((day) => {
      const meta = renderDayMetaHTML(day, true);
      const habits = `<div class="history-habits">${renderHabitTiles(day, false)}</div>`;
      const label = formatHeaderDate(day.date);
      return `
        <article class="history-row" data-history-date="${day.date}">
          <div class="history-row__top">
            <div class="history-row__date">${escapeHtml(label)}</div>
            ${meta}
          </div>
          ${habits}
        </article>`;
    })
    .join("");
}

/** @param {HTMLInputElement} t */
async function persistDayMeta(t) {
  const parent = t.closest(".day-meta");
  if (!parent) return;
  const date = parent.getAttribute("data-date");
  if (!date) return;

  const row = state.days.find((d) => d.date === date);
  if (!row) return;

  const wakeEl = /** @type {HTMLInputElement | null} */ (
    parent.querySelector('input[data-field="wake_time"]')
  );
  const bedEl = /** @type {HTMLInputElement | null} */ (
    parent.querySelector('input[data-field="bed_time"]')
  );
  const hrsEl = /** @type {HTMLInputElement | null} */ (
    parent.querySelector('input[data-field="hours_worked"]')
  );

  const wake_time = wakeEl ? normalizeTimeValue(wakeEl.value) : row.meta.wake_time;
  const bed_time = bedEl ? normalizeTimeValue(bedEl.value) : row.meta.bed_time;

  let hours_worked = row.meta.hours_worked;
  if (hrsEl) {
    const v = hrsEl.value.trim();
    hours_worked = v === "" ? null : parseFloat(v);
    if (v !== "" && Number.isNaN(hours_worked)) {
      toast("Invalid hours", true);
      return;
    }
  }

  try {
    const res = await fetchJSON("/api/meta", {
      method: "POST",
      body: JSON.stringify({ date, wake_time, bed_time, hours_worked }),
    });
    row.meta = {
      wake_time,
      bed_time,
      hours_worked,
    };
    if (wakeEl && wake_time) wakeEl.value = wake_time;
    else if (wakeEl) wakeEl.value = "";
    if (bedEl && bed_time) bedEl.value = bed_time;
    else if (bedEl) bedEl.value = "";
    applyStats(res.stats);
  } catch (err) {
    toast(/** @type {Error} */ (err).message, true);
  }
}

/** @param {Event} e */
function onMetaBlur(e) {
  const t = /** @type {HTMLInputElement} */ (e.target);
  if (!t.dataset.field || !t.dataset.date) return;
  void persistDayMeta(t);
}

/** Save on time-picker commit / number change (blur alone is unreliable for some browsers). */
/** @param {Event} e */
function onMetaFieldChange(e) {
  const t = /** @type {HTMLInputElement} */ (e.target);
  if (!t.dataset.field || !t.dataset.date) return;
  if (t.dataset.field === "wake_time" || t.dataset.field === "bed_time") {
    void persistDayMeta(t);
  } else if (t.dataset.field === "hours_worked") {
    void persistDayMeta(t);
  }
}

/** @param {HTMLElement} grid */
function wireTodayGrid(grid) {
  const addBtn = document.getElementById("add-tile-btn");
  if (addBtn) {
    addBtn.addEventListener("click", () => {
      addingHabit = true;
      renderToday();
    });
  }
  const form = document.getElementById("add-habit-form");
  if (form) {
    form.addEventListener("submit", onAddHabitSubmit);
  }
  const cancel = document.getElementById("add-habit-cancel");
  if (cancel) {
    cancel.addEventListener("click", () => {
      addingHabit = false;
      renderToday();
    });
  }
  grid.querySelectorAll("[data-archive]").forEach((btn) => {
    btn.addEventListener("click", onArchiveClick);
  });
}

/** @param {Event} e */
async function onArchiveClick(e) {
  const t = /** @type {HTMLElement} */ (e.currentTarget);
  const id = t.getAttribute("data-archive");
  if (!id || !confirm("Archive this habit? Past data stays in the database.")) return;
  try {
    const res = await fetchJSON(`/api/habits/${id}`, { method: "DELETE" });
    applyStats(res.stats);
    addingHabit = false;
    await refreshFromServer();
  } catch (err) {
    toast(/** @type {Error} */ (err).message, true);
  }
}

/** @param {Event} e */
async function onAddHabitSubmit(e) {
  e.preventDefault();
  const form = /** @type {HTMLFormElement} */ (e.target);
  const fd = new FormData(form);
  const name = String(fd.get("name") || "").trim();
  if (!name) return;
  try {
    await fetchJSON("/api/habits", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    addingHabit = false;
    await refreshFromServer();
    toast("Habit added");
  } catch (err) {
    toast(/** @type {Error} */ (err).message, true);
  }
}

/** @param {Event} e */
async function onToggleChange(e) {
  const t = /** @type {HTMLInputElement} */ (e.target);
  if (t.tagName !== "INPUT" || t.type !== "checkbox" || !t.dataset.toggle) return;

  const habitId = parseInt(t.dataset.toggle, 10);
  const date = t.dataset.date;
  if (!date || Number.isNaN(habitId)) return;

  const completed = t.checked;
  const isToday = date === state.today;

  try {
    const res = await fetchJSON("/api/toggle", {
      method: "POST",
      body: JSON.stringify({ habit_id: habitId, date, completed }),
    });

    const row = state.days.find((d) => d.date === date);
    if (row) {
      row.completions[String(habitId)] = completed ? 1 : 0;
      row.complete = res.day_complete;
    }
    applyStats(res.stats);
    if (res.habit_streaks) {
      state.habit_streaks = res.habit_streaks;
      if (isToday) renderToday();
    }

    if (isToday) {
      const nowComplete = !!res.day_complete;
      if (nowComplete && !wasTodayComplete) burstConfetti();
      wasTodayComplete = nowComplete;
    }
  } catch (err) {
    t.checked = !completed;
    toast(/** @type {Error} */ (err).message, true);
  }
}

function updateSeeMoreButton() {
  const btn = document.getElementById("btn-see-more");
  if (!btn) return;
  btn.hidden = !state.has_more;
}

function renderHeader() {
  const hd = document.getElementById("header-date");
  if (hd && state.today) hd.textContent = formatHeaderDate(state.today);
  applyStats(state.stats);
}

function renderAll() {
  renderHeader();
  renderToday();
  renderHistory();
  updateSeeMoreButton();
}

/** @param {any} payload */
function mergeState(payload) {
  state.habits = payload.habits || [];
  state.days = payload.days || [];
  state.stats = payload.stats || { current_streak: 0, longest_streak: 0 };
  state.habit_streaks = payload.habit_streaks || {};
  state.today = payload.today || "";
  state.has_more = payload.has_more !== false;
}

async function refreshFromServer() {
  const limit = Math.max(11, loadedCount || 11);
  const data = await fetchJSON(`/api/state?offset=0&limit=${limit}`);
  mergeState(data);
  loadedCount = state.days.length;
  syncTodayCompleteFlag();
  renderAll();
}

async function loadInitial() {
  const data = await fetchJSON("/api/state?offset=0&limit=11");
  mergeState(data);
  loadedCount = state.days.length;
  syncTodayCompleteFlag();
  renderAll();
}

async function loadMore() {
  const btn = document.getElementById("btn-see-more");
  if (btn) btn.disabled = true;
  try {
    const data = await fetchJSON(`/api/state?offset=${loadedCount}&limit=10`);
    const newDays = data.days || [];
    if (data.habits) state.habits = data.habits;
    if (data.stats) state.stats = data.stats;
    state.days = state.days.concat(newDays);
    loadedCount = state.days.length;
    state.has_more = data.has_more !== false;
    renderHeader();
    renderHistory();
    updateSeeMoreButton();
  } catch (err) {
    toast(/** @type {Error} */ (err).message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function initDelegationOnce() {
  const main = document.querySelector("main");
  if (!main || main.dataset.habitDelegation) return;
  main.dataset.habitDelegation = "1";
  main.addEventListener("change", onToggleChange);
  main.addEventListener("change", onMetaFieldChange);
  main.addEventListener("blur", onMetaBlur, true);
}

document.addEventListener("DOMContentLoaded", () => {
  initDelegationOnce();
  const btn = document.getElementById("btn-see-more");
  if (btn) btn.addEventListener("click", loadMore);

  loadInitial().catch((err) => {
    toast(/** @type {Error} */ (err).message || "Failed to load", true);
  });
});

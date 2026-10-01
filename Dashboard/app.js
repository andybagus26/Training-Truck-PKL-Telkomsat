"use strict";
// Dashboard visual untuk data deteksi. Semua data diambil dari backend FastAPI (backend/app/main.py),
// tidak langsung ke Frigate.
// Alamat backend: asal halaman ini (backend menyajikannya di /dashboard/), atau ?api=http://host:8000
// bila halaman dibuka dari tempat lain.

const API = (() => {
  const fromQuery = new URLSearchParams(location.search).get("api");
  if (fromQuery) return fromQuery.replace(/\/+$/, "");
  return location.protocol.startsWith("http") ? location.origin : "http://localhost:8000";
})();

const INTERVAL_DATA = 10000;    // status, rekap, tabel
const INTERVAL_FRAME = 3000;    // gambar kamera
const INTERVAL_CAMERAS = 60000; // daftar kamera jarang berubah
const TIMEOUT_MS = 15000;
const SUMMARY_LIMIT = 2000;     // batas maksimal /summary di backend
const TABLE_LIMIT = 100;

const DEFAULT_LABELS = ["truck", "full_load", "empty_load", "excavator", "bed_raised"];
const LABEL_NAME = { truck: "Truk", full_load: "Bermuatan", empty_load: "Kosong", excavator: "Excavator",
  bed_raised: "Bak terangkat" };

// Keadaan truk hasil penyimpulan backend (activity.py). Urutan = urutan tampil.
const STATES = ["loading", "dumping", "idle", "moving"];
const STATE_NAME = { loading: "Dimuat", dumping: "Dumping", idle: "Idle", moving: "Bergerak", unknown: "Tidak diketahui" };
const ACTIVITY_LIMIT = 50;
// /operations dihitung ulang dari seluruh sampel dan memblokir backend selama menghitung (lokasi ramai:
// 0,75 dtk untuk 1 jam, 4 dtk untuk 6 jam). Jadi grafiknya dibatasi 1 jam dan diperbarui tiap menit.
const OPS_MAX_MIN = 60;
const OPS_INTERVAL = 60000;
// Warna kotak di atas gambar kamera (style.css --ov-*). Truk diwarnai menurut keadaannya.
const OV_LABEL = { excavator: "--ov-excavator", bed_raised: "--ov-bed_raised", full_load: "--ov-load", empty_load: "--ov-load" };

const $ = (id) => document.getElementById(id);

const state = {
  labels: DEFAULT_LABELS.slice(),
  cameras: [],          // dari /cameras
  cards: new Map(),     // nama kamera -> elemen kartu
  thumbs: new Map(),    // id deteksi -> <img> thumbnail (dipakai ulang agar tidak diunduh ulang)
  frigateOk: false,
  paused: false,
  seq: 0,               // naik tiap filter berubah; hasil lama dibuang
  camerasFetchedAt: 0,
  dataTimer: null,
  frameTimer: null,
  inflight: false,
  rerun: false,
  ops: { data: null, key: "", at: 0 }, // hasil /operations terakhir, dipakai ulang sampai OPS_INTERVAL
  boxes: "state",       // kotak di gambar kamera: "state" (keadaan truk) atau "frigate" (kotak bawaan Frigate)
  objectsMissing: false, // backend lama tanpa /cameras/{kamera}/objects
  mqttOk: null,
  zoom: null,           // kamera yang sedang diperbesar: { cam, view }
};

// ---------- utilitas ----------

class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function apiUrl(path, params = {}) {
  const url = new URL(API + path);
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v !== null && v !== undefined) url.searchParams.set(k, String(v));
  }
  return url.toString();
}

async function api(path, params) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res;
  try {
    res = await fetch(apiUrl(path, params), { signal: ctrl.signal, cache: "no-store" });
  } catch (e) {
    throw new ApiError(0, e.name === "AbortError"
      ? `Backend tidak merespons dalam ${TIMEOUT_MS / 1000} detik (${API}).`
      : `Backend tidak bisa dihubungi di ${API}. Pastikan uvicorn berjalan.`);
  } finally {
    clearTimeout(timer);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errorText(body, res.status));
  return body;
}

function errorText(body, status) {
  const d = body && body.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return `Backend mengembalikan status ${status}.`;
}

// Membuat elemen DOM. Isi teks selalu lewat textContent, jadi data dari server tidak pernah jadi HTML.
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style") Object.assign(node.style, v);
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : String(c));
  }
  return node;
}

const labelName = (l) => LABEL_NAME[l] || l;
const labelColor = (l) => (DEFAULT_LABELS.includes(l) ? `var(--${l})` : "var(--other)");
const swatch = (l) => el("span", { class: "swatch", style: { background: labelColor(l) }, "aria-hidden": "true" });
const stateName = (s) => STATE_NAME[s] || s;
const stateColor = (s) => (STATES.includes(s) ? `var(--st-${s})` : "var(--other)");
const stateSwatch = (s) => el("span", { class: "swatch", style: { background: stateColor(s) }, "aria-hidden": "true" });
const badge = (s) => {
  const b = el("span", { class: "badge" }, stateName(s));
  b.style.setProperty("--c", stateColor(s));
  return b;
};
const shortId = (id) => (id ? String(id).split("-").pop() : "–");
const fmtInt = (n) => (Number.isFinite(n) ? n.toLocaleString("id-ID") : "–");
const fmtScore = (s) => (typeof s === "number" ? `${Math.round(s * 100)}%` : "–");

// Backend mengirim waktu UTC dengan 6 digit mikrodetik; dipotong ke 3 digit agar aman di semua browser.
function parseTime(iso) {
  if (!iso) return null;
  const d = new Date(String(iso).replace(/(\.\d{3})\d+/, "$1"));
  return Number.isNaN(d.getTime()) ? null : d;
}

function fmtTime(d) {
  if (!d) return "–";
  return d.toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const rtf = new Intl.RelativeTimeFormat("id", { numeric: "auto" });
function ago(d) {
  if (!d) return "";
  const s = Math.round((d.getTime() - Date.now()) / 1000);
  const a = Math.abs(s);
  if (a < 60) return rtf.format(s, "second");
  if (a < 3600) return rtf.format(Math.round(s / 60), "minute");
  if (a < 86400) return rtf.format(Math.round(s / 3600), "hour");
  return rtf.format(Math.round(s / 86400), "day");
}

// Versi ringkas untuk label di atas kotak: "24 dtk", "3 mnt 5 dtk".
function fmtShort(sec) {
  const total = Math.round(sec);
  return total < 60 ? `${total} dtk` : `${Math.floor(total / 60)} mnt ${total % 60} dtk`;
}

function fmtDuration(sec) {
  if (typeof sec !== "number") return "–";
  if (Math.round(sec * 10) / 10 < 60) return `${sec.toFixed(1)} dtk`;
  const total = Math.round(sec);        // bulatkan dulu, supaya tidak muncul "6 mnt 60 dtk"
  return `${Math.floor(total / 60)} mnt ${total % 60} dtk`;
}

function setPill(id, kind, text) {
  const p = $(id);
  p.className = `pill ${kind || ""}`.trim();
  p.textContent = text;
}

// Beban mesin: kuning mulai 70%, merah mulai 90%.
function setLoadPill(id, name, value, what) {
  const p = $(id);
  if (typeof value !== "number") { p.hidden = true; return; }  // backend lama belum mengirim angka ini
  p.hidden = false;
  const shown = Math.round(value);   // warna mengikuti angka yang terlihat, jadi "90%" tidak pernah kuning
  setPill(id, shown >= 90 ? "bad" : shown >= 70 ? "warn" : "ok", `${name} ${shown}%`);
  p.title = `${what} seluruh mesin tempat Frigate berjalan`;
}

function hideLoadPills() { $("pill-cpu").hidden = true; $("pill-ram").hidden = true; }

function showBanner(msg) { const b = $("banner"); b.textContent = msg; b.hidden = false; }
function hideBanner() { $("banner").hidden = true; }

function filters() {
  return { range: Number($("f-range").value), camera: $("f-camera").value, label: $("f-label").value };
}

// ---------- status ----------

async function refreshStatus() {
  let health;
  try {
    health = await api("/health");
  } catch (e) {
    setPill("pill-backend", "bad", "Backend tidak terjangkau");
    setPill("pill-frigate", "", "Frigate ?");
    setPill("pill-detector", "", "Detektor ?");
    hideLoadPills();
    state.frigateOk = false;
    throw e;
  }
  setPill("pill-backend", "ok", "Backend aktif");
  state.frigateOk = !!health.frigate_reachable;
  if (Array.isArray(health.model_labels) && health.model_labels.length) state.labels = health.model_labels;
  if (!state.frigateOk) {
    setPill("pill-frigate", "bad", "Frigate tidak terjangkau");
    setPill("pill-detector", "", "Detektor ?");
    hideLoadPills();
    throw new ApiError(503, `Backend aktif, tetapi Frigate tidak bisa dihubungi (${health.frigate_url}). ` +
      "Gambar dan data akan muncul lagi otomatis setelah Frigate menyala.");
  }
  const version = health.frigate_version ? String(health.frigate_version).split("-")[0] : "";
  setPill("pill-frigate", "ok", `Frigate ${version}`.trim());
}

async function refreshStats() {
  const s = await api("/stats");
  const det = (s.detectors || [])[0];
  if (det && typeof det.inference_speed_ms === "number") {
    setPill("pill-detector", "ok", `Detektor ${det.name}: ${det.inference_speed_ms.toFixed(1)} ms`);
  } else {
    setPill("pill-detector", "", "Detektor belum aktif");
  }
  $("pill-detector").title = det && typeof det.cpu_percent === "number"
    ? `Proses detektor di Frigate memakai CPU ${Math.round(det.cpu_percent)}% (dari satu inti prosesor)` : "";
  setLoadPill("pill-cpu", "CPU", s.system && s.system.cpu_percent, "Pemakaian prosesor");
  setLoadPill("pill-ram", "RAM", s.system && s.system.mem_percent, "Pemakaian memori");
  for (const c of s.cameras || []) {
    const card = state.cards.get(c.camera);
    if (!card) continue;
    const fps = typeof c.process_fps === "number" ? c.process_fps.toFixed(1) : "–";
    const skipped = typeof c.skipped_fps === "number" && c.skipped_fps > 0 ? ` · terlewat ${c.skipped_fps.toFixed(1)} fps` : "";
    const load = [typeof c.cpu_percent === "number" ? `CPU ${Math.round(c.cpu_percent)}%` : null,
      typeof c.mem_percent === "number" ? `RAM ${Math.round(c.mem_percent)}%` : null].filter(Boolean).join(" · ");
    card.stats.textContent = `Diproses ${fps} fps${skipped}${load ? ` · ${load}` : ""}`;
    card.stats.title = load ? "CPU dihitung dari satu inti prosesor (seperti halaman System di Frigate); " +
      "RAM dari seluruh memori mesin." : "";
  }
}

// ---------- kamera ----------

async function refreshCameras(force) {
  if (!force && Date.now() - state.camerasFetchedAt < INTERVAL_CAMERAS && state.cameras.length) return;
  const cams = await api("/cameras");
  state.camerasFetchedAt = Date.now();
  const sameList = JSON.stringify(cams.map((c) => [c.name, c.enabled])) ===
    JSON.stringify(state.cameras.map((c) => [c.name, c.enabled]));
  state.cameras = cams;
  fillSelect($("f-camera"), cams.map((c) => c.name), "Semua kamera", (n) => n);
  if (!sameList || state.cards.size === 0) buildCameraCards();
}

function fillSelect(select, values, allText, labelOf) {
  const current = select.value;
  select.replaceChildren(el("option", { value: "" }, allText), ...values.map((v) => el("option", { value: v }, labelOf(v))));
  select.value = values.includes(current) ? current : "";
}

function buildCameraCards() {
  const root = $("cams");
  state.cards.clear();
  if (!state.cameras.length) {
    root.replaceChildren(el("p", { class: "empty" }, "Tidak ada kamera di konfigurasi Frigate."));
    return;
  }
  root.replaceChildren(...state.cameras.map((cam) => {
    const open = () => openCamera(cam.name);
    const frame = el("div", cam.enabled ? {
      class: "cam-frame", role: "button", tabindex: 0, title: "Perbesar", "aria-label": `Perbesar kamera ${cam.name}`,
      onclick: open,
      onkeydown: (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } },
    } : { class: "cam-frame" });
    const view = makeView(frame, cam.enabled ? "Memuat gambar…" : "Kamera nonaktif", `Frame terbaru kamera ${cam.name}`);
    const stats = el("span", { class: "cam-info" }, cam.enabled ? "Diproses – fps" : "");
    const info = [cam.resolution, cam.detect_fps ? `${cam.detect_fps} fps deteksi` : null,
      cam.zones.length ? `zone: ${cam.zones.join(", ")}` : null].filter(Boolean).join(" · ");
    const card = el("div", { class: "cam" }, frame,
      el("div", { class: "cam-meta" }, el("span", { class: "cam-name" }, cam.name), el("span", { class: "cam-info" }, info), stats));
    state.cards.set(cam.name, { cam, view, stats });
    return card;
  }));
  loadFrames();
}

function makeView(frame, overlayText, alt) {
  const img = el("img", { alt });
  const layer = el("div", { class: "boxes", "aria-hidden": "true" });
  const overlay = el("div", { class: "cam-overlay" }, overlayText);
  frame.replaceChildren(img, layer, overlay);
  return { frame, img, layer, overlay, loading: false };
}

function loadFrames() {
  if (!state.frigateOk) return;
  for (const card of state.cards.values()) {
    if (card.cam.enabled) refreshView(card.view, card.cam.name, 360, state.boxes === "state");
  }
  if (state.zoom) refreshZoom();
}

function preload(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

async function fetchObjects(camName) {
  if (state.objectsMissing) return null;
  try {
    return await api(`/cameras/${encodeURIComponent(camName)}/objects`);
  } catch (e) {
    if (e.status === 404) { state.objectsMissing = true; updateBoxNote(); }
    return null;
  }
}

// Gambar dan kotaknya diambil bersamaan lalu ditukar sekaligus: gambar tidak berkedip, dan kotak tidak
// tertinggal dari gambarnya. Mengembalikan objek yang sedang terlihat (null bila tidak diminta atau gagal).
async function refreshView(view, camName, height, wantObjects) {
  if (view.loading) return null;
  view.loading = true;
  const drawState = state.boxes === "state" && !state.objectsMissing;
  const src = apiUrl(`/cameras/${encodeURIComponent(camName)}/latest`, { height, bbox: !drawState, t: Date.now() });
  try {
    const [pre, objs] = await Promise.all([preload(src), wantObjects || drawState ? fetchObjects(camName) : null]);
    view.img.src = src;
    view.overlay.hidden = true;
    fitLayer(view, pre.naturalWidth, pre.naturalHeight);
    view.layer.replaceChildren(...(drawState && objs ? objs.map(boxFor) : []));
    return objs;
  } catch {
    view.overlay.textContent = "Frame belum tersedia";
    view.overlay.hidden = false;
    view.layer.replaceChildren();
    return null;
  } finally {
    view.loading = false;
  }
}

// Gambar ditampilkan dengan object-fit: contain, jadi bila rasionya beda dengan bingkai ada pita hitam.
// Lapisan kotak diletakkan tepat di atas area gambarnya saja, supaya kotak jatuh di tempat yang benar.
function fitLayer(view, w, h) {
  const r = view.frame.getBoundingClientRect();
  const frameRatio = r.width && r.height ? r.width / r.height : 16 / 9;
  const imgRatio = w && h ? w / h : frameRatio;
  const st = view.layer.style;
  if (imgRatio >= frameRatio) {
    const hh = (frameRatio / imgRatio) * 100;
    Object.assign(st, { left: "0", width: "100%", top: `${(100 - hh) / 2}%`, height: `${hh}%` });
  } else {
    const ww = (imgRatio / frameRatio) * 100;
    Object.assign(st, { top: "0", height: "100%", left: `${(100 - ww) / 2}%`, width: `${ww}%` });
  }
}

// Truk: kotak tebal berwarna keadaan (kesimpulan backend). Objek lain: kotak putus-putus (hasil model).
function boxFor(o) {
  const b = o.box;
  const truck = o.label === "truck";
  const color = truck ? `var(--ov-${STATES.includes(o.state) ? o.state : "unknown"})` : `var(${OV_LABEL[o.label] || "--ov-unknown"})`;
  const text = truck
    ? `${STATES.includes(o.state) ? stateName(o.state) : "Truk"}${o.state_seconds ? ` ${fmtShort(o.state_seconds)}` : ""}`
    : labelName(o.label);
  const edge = truck ? b.y < 0.08 : b.y + b.h > 0.92; // label akan terpotong tepi gambar: taruh di dalam kotak
  const node = el("div", {
    class: `bx${truck ? "" : " thin"}${edge ? " in" : ""}${b.x + b.w > 0.85 ? " r" : ""}`,
    style: { left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` },
  }, el("b", {}, text));
  node.style.setProperty("--c", color);
  return node;
}

function updateBoxNote() {
  let msg = "";
  if (state.boxes === "state") {
    if (state.objectsMissing) {
      msg = "Backend ini belum bisa memberi posisi objek terkini (/cameras/{kamera}/objects), jadi kamera menampilkan " +
        "kotak Frigate. Perbarui backend untuk melihat keadaan truk di gambar.";
    } else if (state.mqttOk === false) {
      msg = "Backend tidak menerima posisi terkini lewat MQTT, jadi letak kotak dan keadaan truk di gambar bisa tidak sesuai.";
    }
  }
  $("box-note").textContent = msg;
  $("box-note").hidden = !msg;
}

// ---------- kamera diperbesar ----------

function openCamera(name) {
  $("cam-dialog-title").textContent = name;
  $("cam-dialog-info").textContent = "";
  $("cam-dialog-trucks").replaceChildren();
  $("cam-dialog-raw").href = apiUrl(`/cameras/${encodeURIComponent(name)}/latest`, { height: 1080, bbox: true });
  state.zoom = { cam: name, view: makeView($("cam-dialog-frame"), "Memuat gambar…", `Frame terbaru kamera ${name}`) };
  const dlg = $("cam-dialog");
  if (!dlg.open) dlg.showModal();
  refreshZoom();
}

async function refreshZoom() {
  const z = state.zoom;
  if (!z || !state.frigateOk) return;
  const objs = await refreshView(z.view, z.cam, 720, true);
  if (state.zoom !== z) return; // sudah ditutup atau ganti kamera
  if (state.objectsMissing) {
    $("cam-dialog-info").textContent = "Keadaan tiap truk butuh backend versi terbaru.";
    return;
  }
  if (!objs) return;
  const trucks = objs.filter((o) => o.label === "truck");
  $("cam-dialog-info").textContent = `${fmtInt(trucks.length)} truk · ${fmtInt(objs.length)} objek terdeteksi`;
  $("cam-dialog-trucks").replaceChildren(...(trucks.length ? trucks.map((t) => el("span", { class: "pill" },
    badge(STATES.includes(t.state) ? t.state : "unknown"),
    t.state_seconds ? el("strong", {}, fmtShort(t.state_seconds)) : null,
    t.load_state ? `· ${labelName(t.load_state)}` : null))
    : [el("span", { class: "hint" }, "Tidak ada truk di gambar saat ini.")]));
}

function frameLoop() {
  clearTimeout(state.frameTimer);
  if (!state.paused && !document.hidden) loadFrames();
  state.frameTimer = setTimeout(frameLoop, INTERVAL_FRAME);
}

// ---------- rekap & grafik ----------

function renderSummary(sum, ongoingCount) {
  const count = (label) => (sum.per_label.find((x) => x.label === label) || {}).count || 0;
  $("kpi-total").textContent = fmtInt(sum.total);
  $("kpi-truck").textContent = fmtInt(count("truck"));
  $("kpi-excavator").textContent = fmtInt(count("excavator"));
  $("kpi-ongoing").textContent = fmtInt(ongoingCount);

  // semua label model tetap tampil, walau nol, supaya mudah dibandingkan
  const labels = [...state.labels, ...sum.per_label.map((x) => x.label).filter((l) => !state.labels.includes(l))];
  const rows = labels.map((l) => sum.per_label.find((x) => x.label === l) || { label: l, count: 0, average_score: null });
  const max = Math.max(1, ...rows.map((r) => r.count));
  $("chart-label").replaceChildren(...rows.map((r) => el("div", { class: "bar-row" },
    el("span", { class: "bar-name tag" }, swatch(r.label), labelName(r.label)),
    el("div", { class: "bar-track", role: "img", "aria-label": `${labelName(r.label)}: ${r.count}` },
      el("div", { class: "bar-fill", style: { width: `${(r.count / max) * 100}%`, background: labelColor(r.label) } })),
    el("span", { class: "bar-val" }, el("strong", {}, fmtInt(r.count)),
      r.average_score != null ? ` · rata-rata ${fmtScore(r.average_score)}` : ""),
  )));

  $("legend").replaceChildren(...labels.map((l) => el("span", {}, swatch(l), labelName(l))));
  if (!sum.per_camera.length) {
    $("chart-camera").replaceChildren(el("p", { class: "empty" }, "Belum ada deteksi dalam rentang ini."));
  } else {
    const maxCam = Math.max(1, ...sum.per_camera.map((c) => c.total));
    $("chart-camera").replaceChildren(...sum.per_camera.map((c) => {
      const detail = c.per_label.map((x) => `${labelName(x.label)} ${x.count}`).join(", ");
      return el("div", { class: "bar-row" },
        el("span", { class: "bar-name", title: c.camera }, c.camera),
        el("div", { class: "bar-track", role: "img", "aria-label": `${c.camera}: ${detail}` },
          ...labels.map((l) => {
            const n = (c.per_label.find((x) => x.label === l) || {}).count || 0;
            return n ? el("div", { class: "bar-fill", title: `${labelName(l)}: ${n}`,
              style: { width: `${(n / maxCam) * 100}%`, background: labelColor(l) } }) : null;
          })),
        el("span", { class: "bar-val" }, el("strong", {}, fmtInt(c.total))));
    }));
  }

  const note = $("note-summary");
  const truncated = sum.total >= SUMMARY_LIMIT;
  note.className = truncated ? "note warn" : "note";
  note.textContent = truncated
    ? `Data terpotong: lebih dari ${fmtInt(SUMMARY_LIMIT)} event dalam rentang ini, angka sebenarnya lebih besar. Persempit rentang waktu.`
    : "Angka adalah jumlah event Frigate (objek yang dilacak), bukan jumlah kendaraan unik.";
}

// ---------- tabel deteksi ----------

function thumbFor(d) {
  if (!d.has_snapshot) return el("div", { class: "no-thumb" }, "tanpa foto");
  let img = state.thumbs.get(d.id);
  if (!img) {
    img = el("img", {
      class: "thumb", loading: "lazy", alt: `Foto ${labelName(d.label)} di ${d.camera}`,
      src: apiUrl(`/detections/${encodeURIComponent(d.id)}/snapshot`, { bbox: true }),
    });
    img.addEventListener("error", () => img.replaceWith(el("div", { class: "no-thumb" }, "foto hilang")), { once: true });
    state.thumbs.set(d.id, img);
  }
  return img;
}

function renderDetections(list) {
  const body = $("det-body");
  const keep = new Set(list.map((d) => d.id));
  for (const id of state.thumbs.keys()) if (!keep.has(id)) state.thumbs.delete(id);

  $("det-count").textContent = list.length >= TABLE_LIMIT
    ? `Menampilkan ${TABLE_LIMIT} terbaru` : `${fmtInt(list.length)} deteksi`;

  if (!list.length) {
    body.replaceChildren(el("tr", { class: "empty-row" }, el("td", { colspan: 8, class: "empty" }, "Belum ada deteksi yang cocok dengan filter.")));
    return;
  }
  body.replaceChildren(...list.map((d) => {
    const start = parseTime(d.start_time);
    const open = () => openDetail(d);
    return el("tr", {
      tabindex: 0, "aria-label": `Detail ${labelName(d.label)} di ${d.camera}`,
      onclick: open,
      onkeydown: (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); open(); } },
    },
      el("td", {}, thumbFor(d)),
      el("td", { title: fmtTime(start) }, fmtTime(start), el("div", { class: "hint" }, ago(start))),
      el("td", {}, d.camera),
      el("td", {}, el("span", { class: "tag" }, swatch(d.label), labelName(d.label))),
      el("td", { class: "num" }, fmtScore(d.score)),
      el("td", { class: "num" }, d.ongoing ? "–" : fmtDuration(d.duration_seconds)),
      el("td", {}, d.zones.length ? d.zones.join(", ") : "–"),
      el("td", {}, d.ongoing ? el("span", { class: "status-live" }, "Masih terlihat") : el("span", { class: "status-done" }, "Selesai")),
    );
  }));
}

function openDetail(d) {
  const start = parseTime(d.start_time);
  const end = parseTime(d.end_time);
  const box = d.box ? `x ${d.box.x.toFixed(3)}, y ${d.box.y.toFixed(3)}, lebar ${d.box.w.toFixed(3)}, tinggi ${d.box.h.toFixed(3)} (relatif 0–1)` : "–";
  const fields = [
    ["Label", labelName(d.label) + (LABEL_NAME[d.label] ? ` (${d.label})` : "")],
    ["Kamera", d.camera],
    ["Skor tertinggi", fmtScore(d.score)],
    ["Mulai", `${fmtTime(start)} (${ago(start)})`],
    ["Selesai", d.ongoing ? "Masih terlihat" : fmtTime(end)],
    ["Durasi", d.ongoing ? "–" : fmtDuration(d.duration_seconds)],
    ["Zone", d.zones.length ? d.zones.join(", ") : "–"],
    ["Kotak", box],
    ["Klip rekaman", d.has_clip ? "Ada (buka di Frigate)" : "Tidak ada"],
    ["ID", d.id],
  ];
  $("detail-title").textContent = `${labelName(d.label)} di ${d.camera}`;
  $("detail-body").replaceChildren(
    d.has_snapshot
      ? el("img", { class: "detail-img", alt: `Foto deteksi ${labelName(d.label)}`,
        src: apiUrl(`/detections/${encodeURIComponent(d.id)}/snapshot`, { bbox: true, t: Date.now() }) })
      : el("div", { class: "no-thumb", style: { width: "100%", height: "120px" } }, "Deteksi ini tidak punya foto"),
    el("dl", { class: "fields" }, ...fields.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)])),
  );
  const dlg = $("detail");
  if (!dlg.open) dlg.showModal();
}

// ---------- aktivitas truk (idle / dimuat / dumping) ----------

function renderStateKpis(live) {
  const count = (s) => live.filter((t) => t.state === s).length;
  $("state-kpis").replaceChildren(...STATES.map((s) => {
    const k = el("div", { class: "kpi state" },
      el("span", { class: "kpi-label" }, `${stateName(s)} sekarang`),
      el("span", { class: "kpi-value" }, fmtInt(count(s))));
    k.style.setProperty("--c", stateColor(s));
    return k;
  }));
}

function renderStateChart(ops, minutes) {
  $("state-window").textContent = `${minutes >= 60 ? "1 jam" : `${minutes} menit`} terakhir`;
  $("state-legend").replaceChildren(...STATES.map((s) => el("span", {}, stateSwatch(s), stateName(s))));
  if (!ops.length) {
    $("chart-state").replaceChildren(el("p", { class: "empty" }, "Belum ada data keadaan truk dalam rentang ini."));
  } else {
    $("chart-state").replaceChildren(...ops.map((c) => {
      const total = Object.values(c.seconds).reduce((a, b) => a + b, 0) || 1;
      const events = Object.entries(c.events || {})
        .map(([t, e]) => `${stateName(t)} ${e.count}× (rata-rata ${fmtDuration(e.average_seconds)})`).join(", ");
      const title = STATES.filter((s) => c.seconds[s]).map((s) => `${stateName(s)} ${fmtDuration(c.seconds[s])}`).join(", ");
      return el("div", { class: "bar-row" },
        el("span", { class: "bar-name", title: c.camera }, c.camera),
        el("div", { class: "bar-track", role: "img", "aria-label": `${c.camera}: ${title}` },
          ...STATES.map((s) => (c.seconds[s] ? el("div", { class: "bar-fill", title: `${stateName(s)}: ${fmtDuration(c.seconds[s])}`,
            style: { width: `${(c.seconds[s] / total) * 100}%`, background: stateColor(s) } }) : null))),
        el("span", { class: "bar-val", title: events || "Belum ada aktivitas yang selesai" },
          el("strong", {}, c.idle_share == null ? "–" : `${Math.round(c.idle_share * 100)}%`), " idle",
          events ? el("div", { class: "hint" }, events) : null));
    }));
  }
  $("note-state").textContent = "Panjang batang = bagian waktu truk di tiap keadaan; persen = bagian waktu truk berhenti " +
    "tanpa dilayani (idle). Grafik ini paling jauh mencakup 1 jam terakhir dan diperbarui tiap menit, supaya " +
    "perhitungannya tidak membebani backend.";
}

function renderLive(live) {
  const order = (t) => STATES.indexOf(t.state) === -1 ? STATES.length : STATES.indexOf(t.state);
  const rows = live.slice().sort((a, b) => order(a) - order(b) || a.camera.localeCompare(b.camera));
  $("live-count").textContent = rows.length ? `${fmtInt(rows.length)} truk` : "";
  $("live-body").replaceChildren(...(rows.length ? rows.map((t) => {
    const seen = parseTime(t.last_seen);
    return el("tr", { class: "static" },
      el("td", {}, t.camera),
      el("td", { title: t.truck_id }, shortId(t.truck_id)),
      el("td", {}, badge(t.state)),
      el("td", {}, t.load_state ? el("span", { class: "tag" }, swatch(t.load_state), labelName(t.load_state)) : "–"),
      el("td", { title: t.excavator_nearby || "" }, t.excavator_nearby ? shortId(t.excavator_nearby) : "–"),
      el("td", {}, t.activity ? `${stateName(t.activity)} · ${fmtDuration(t.activity_seconds)}` : "–"),
      el("td", { title: fmtTime(seen) }, ago(seen)));
  }) : [el("tr", { class: "empty-row" }, el("td", { colspan: 7, class: "empty" }, "Tidak ada truk yang sedang terlihat."))]));
}

function renderActivities(acts) {
  $("act-count").textContent = acts.length >= ACTIVITY_LIMIT ? `${ACTIVITY_LIMIT} terbaru` : (acts.length ? `${fmtInt(acts.length)} aktivitas` : "");
  $("act-body").replaceChildren(...(acts.length ? acts.map((a) => {
    const start = parseTime(a.start_time);
    const load = (a.load_before || a.load_after)
      ? `${a.load_before ? labelName(a.load_before) : "?"} → ${a.load_after ? labelName(a.load_after) : "?"}` : "–";
    return el("tr", { class: "static" },
      el("td", {}, badge(a.type)),
      el("td", {}, a.camera),
      el("td", { title: a.truck_id }, shortId(a.truck_id)),
      el("td", { title: fmtTime(start) }, fmtTime(start), el("div", { class: "hint" }, ago(start))),
      el("td", { class: "num" }, a.ongoing ? "–" : fmtDuration(a.duration_seconds)),
      el("td", {}, load),
      el("td", {}, a.ongoing ? el("span", { class: "status-live" }, "Berjalan") : el("span", { class: "status-done" }, "Selesai")));
  }) : [el("tr", { class: "empty-row" }, el("td", { colspan: 7, class: "empty" }, "Belum ada aktivitas dalam rentang ini."))]));
}

function renderPoller(p) {
  const connected = p.source === "mqtt" && p.mqtt && p.mqtt.connected;
  // receiving === false: broker tersambung tapi Frigate tidak mengirim data (backend lama tidak punya field ini)
  const silent = connected && p.mqtt.receiving === false;
  const ok = connected && !silent;
  const m = p.mqtt || {};
  $("poller-info").textContent = [
    `Sumber data: ${p.source === "mqtt" ? "MQTT" : p.source || "–"}`,
    connected ? `${fmtInt(m.tracked_objects)} objek terpantau` : null,
    `${fmtInt(p.activities_in_db)} aktivitas tersimpan`,
  ].filter(Boolean).join(" · ");
  if (state.mqttOk !== ok) { state.mqttOk = ok; updateBoxNote(); }
  setPill("pill-mqtt", ok ? "ok" : "bad",
    ok ? "Aktivitas: MQTT tersambung" : (silent ? "Aktivitas: MQTT tanpa data" : "Aktivitas: tanpa MQTT"));
  const w = $("act-warning");
  if (ok) { w.hidden = true; return; }
  w.textContent = silent
    ? (p.warning || "Broker MQTT tersambung, tetapi Frigate tidak mengirim data, jadi aktivitas tidak tercatat.")
    : "Backend tidak tersambung ke MQTT, jadi posisi truk yang dipakai bukan posisi terkini. " +
      "Keadaan idle, dimuat, dan dumping di bawah ini tidak bisa diandalkan sampai MQTT tersambung.";
  w.hidden = false;
}

// Bagian ini diperbarui terpisah: bila backend lama belum punya endpoint aktivitas atau salah satunya gagal,
// bagian deteksi lain tetap jalan.
async function refreshActivity() {
  const seq = state.seq;
  const f = filters();
  const opsMin = Math.min(f.range, OPS_MAX_MIN);
  const opsKey = `${f.camera}|${opsMin}`;
  const needOps = opsKey !== state.ops.key || !state.ops.data || Date.now() - state.ops.at >= OPS_INTERVAL;
  try {
    const [live, acts, ops, poller] = await Promise.all([
      api("/trucks/live", { camera: f.camera }),
      api("/activities", { camera: f.camera, since_minutes: Math.min(f.range, 10080), limit: ACTIVITY_LIMIT }),
      needOps ? api("/operations", { camera: f.camera, since_minutes: opsMin }) : Promise.resolve(state.ops.data),
      api("/poller"),
    ]);
    if (seq !== state.seq) return;
    if (needOps) state.ops = { data: ops, key: opsKey, at: Date.now() };
    renderPoller(poller);
    renderStateKpis(live);
    renderStateChart(ops, opsMin);
    renderLive(live);
    renderActivities(acts);
  } catch (e) {
    if (seq !== state.seq) return;
    setPill("pill-mqtt", "bad", "Aktivitas: gagal dimuat");
    const w = $("act-warning");
    w.textContent = e.status === 404
      ? "Backend ini belum punya endpoint aktivitas (/trucks/live, /activities). Perbarui backend ke versi terbaru."
      : `Data aktivitas gagal dimuat: ${e.message}`;
    w.hidden = false;
  }
}

// ---------- siklus pembaruan ----------

async function refreshData() {
  const seq = state.seq;
  const f = filters();
  const [sum, ongoing, list] = await Promise.all([
    api("/summary", { since_minutes: f.range, camera: f.camera, limit: SUMMARY_LIMIT }),
    api("/detections", { ongoing_only: true, camera: f.camera, limit: 500 }),
    api("/detections", { since_minutes: f.range, camera: f.camera, label: f.label, limit: TABLE_LIMIT }),
  ]);
  if (seq !== state.seq) return false; // filter sudah berubah saat menunggu; hasil ini usang
  renderSummary(sum, ongoing.length);
  renderDetections(list);
  return true;
}

async function tick() {
  try {
    await refreshStatus();
    await refreshCameras(false);
    await refreshStats();
    const applied = await refreshData();
    await refreshActivity();
    hideBanner();
    if (applied) $("updated").textContent = `Diperbarui ${new Date().toLocaleTimeString("id-ID")}`;
  } catch (e) {
    showBanner(e.message || String(e));
    $("updated").textContent = `Gagal memperbarui ${new Date().toLocaleTimeString("id-ID")}, mencoba lagi…`;
  }
}

async function dataLoop() {
  clearTimeout(state.dataTimer);
  if (state.paused || document.hidden) return;
  if (state.inflight) { state.rerun = true; return; }
  state.inflight = true;
  try { await tick(); } finally { state.inflight = false; }
  if (state.rerun) { state.rerun = false; return dataLoop(); }
  if (!state.paused && !document.hidden) state.dataTimer = setTimeout(dataLoop, INTERVAL_DATA);
}

function onFilterChange() {
  state.seq += 1;
  dataLoop();
}

function init() {
  fillSelect($("f-label"), DEFAULT_LABELS, "Semua label", labelName);
  $("f-range").addEventListener("change", onFilterChange);
  $("f-camera").addEventListener("change", onFilterChange);
  $("f-label").addEventListener("change", onFilterChange);
  $("f-boxes").addEventListener("change", () => {
    state.boxes = $("f-boxes").value;
    for (const card of state.cards.values()) card.view.layer.replaceChildren();
    if (state.zoom) state.zoom.view.layer.replaceChildren();
    updateBoxNote();
    if (!state.paused) loadFrames();
  });

  $("btn-pause").addEventListener("click", () => {
    state.paused = !state.paused;
    const b = $("btn-pause");
    b.setAttribute("aria-pressed", String(state.paused));
    b.textContent = state.paused ? "Lanjutkan" : "Jeda";
    if (state.paused) {
      clearTimeout(state.dataTimer);
      $("updated").textContent = "Pembaruan dijeda";
    } else {
      dataLoop();
      loadFrames();
    }
  });

  const dlg = $("detail");
  $("detail-close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); }); // klik area gelap

  const camDlg = $("cam-dialog");
  $("cam-dialog-close").addEventListener("click", () => camDlg.close());
  camDlg.addEventListener("click", (ev) => { if (ev.target === camDlg) camDlg.close(); });
  camDlg.addEventListener("close", () => { state.zoom = null; });

  // Hemat sumber daya: berhenti saat tab tidak terlihat, lanjut lagi saat kembali.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !state.paused) { dataLoop(); loadFrames(); }
  });

  dataLoop();
  frameLoop();
}

init();

/* Admin panel: umumiy funksiyalar, foydalanuvchilar, chat */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => Number(n || 0).toLocaleString("ru-RU").replace(/,/g, " ");

async function api(path, opts = {}) {
  const init = { ...opts, headers: { "X-Admin": "1", ...(opts.headers || {}) } };
  if (opts.json !== undefined) {
    init.body = JSON.stringify(opts.json);
    init.headers["Content-Type"] = "application/json";
    init.method = init.method || "POST";
  }
  const r = await fetch(path, init);
  if (r.status === 401) { location.href = "/login"; throw new Error("auth"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Xato (${r.status})`);
  return data;
}

let toastTimer;
function toast(msg, isErr = false) {
  let el = $(".toast");
  if (!el) { el = document.createElement("div"); el.className = "toast"; document.body.append(el); }
  el.innerHTML = icon(isErr ? "alert" : "check-circle") + `<span>${esc(msg)}</span>`;
  el.classList.toggle("err", isErr);
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), isErr ? 6000 : 3000);
}

function lightbox(src) {
  const el = document.createElement("div");
  el.className = "lightbox";
  el.innerHTML = `<img src="${esc(src)}">`;
  el.onclick = () => el.remove();
  document.body.append(el);
}

/* ---------------- Tablar ---------------- */
const tabHandlers = {};
function showTab(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$("main > section").forEach((s) => s.classList.toggle("hidden", s.id !== `tab-${name}`));
  try { localStorage.setItem("tab", name); } catch (_) {}
  tabHandlers[name]?.();
}
$$(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
$("#logout").onclick = async () => { await api("/api/logout", { method: "POST" }); location.href = "/login"; };

/* ================= FOYDALANUVCHILAR ================= */
const users = { page: 1, pages: 1 };

async function loadStats() {
  const s = await api("/api/stats");
  const items = [
    ["Jami lidlar", s.total, "users"], ["Ro'yxatdan o'tgan", s.registered, "user-check"], ["Bepul kanalda", s.free_members, "megaphone"],
    ["Faol pullik obuna", s.active_subs, "crown"], ["Kutilayotgan to'lov", s.pending, "clock"], ["Tushum, so'm", money(s.revenue), "trend"],
  ];
  $("#stats").innerHTML = items.map(([l, v, ic], i) => `<div class="card stat ${i === 0 ? "dark" : ""}">
    <div class="top"><span class="l">${l}</span><span class="ico">${icon(ic)}</span></div><div class="v">${v}</div></div>`).join("");
  setChatBadge(s.unread_chats);
}

async function loadGroupsFilter() {
  const groups = await api("/api/groups");
  const sel = $("#f-group");
  sel.innerHTML = `<option value="">Guruh: hammasi</option><option value="any">Kursga yozilganlar</option><option value="waiting">Guruh kutayotganlar</option>` +
    groups.map((g) => `<option value="${g.id}">${esc(g.title)} (${g.members}/${g.capacity})</option>`).join("");
}

function freeCell(u) {
  if (u.free_member === true) return `<span class="pill ok">${icon("check", "sm")}Obuna</span>`;
  if (u.free_member === false) return `<span class="pill bad">${icon("x", "sm")}Obuna emas</span>`;
  return `<span class="pill neutral">Tekshirilmagan</span>`;
}

function paidCell(p) {
  let pill;
  if (p.status === "active") pill = `<span class="pill ok">${icon("crown", "sm")}${esc(p.end)} gacha</span>`;
  else if (p.status === "none") pill = `<span class="pill neutral">Yo'q</span>`;
  else pill = `<span class="pill warn">${icon("clock", "sm")}${p.status === "cancelled" ? "Bekor qilingan" : "Tugagan"} (${esc(p.end)})</span>`;
  let member = "";
  if (p.member === true) member = `<div class="sub">Kanalda bor</div>`;
  else if (p.member === false && p.status !== "none") member = `<div class="sub">Kanalda yo'q</div>`;
  return pill + member;
}

function groupCell(groups) {
  if (!groups.length) return `<span class="muted">—</span>`;
  const st = { waiting_group: "guruh kutmoqda", link_sent: "havola yuborildi", joined: "qo'shilgan" };
  return groups.map((g) => `<div class="group-line"><b>${esc(g.tariff)}</b>: ${g.title ? esc(g.title) : ""} <span class="sub">${st[g.status] || g.status}</span></div>`).join("");
}

function userRow(u) {
  const name = esc(u.name || "—") + (u.blocked ? ` <span class="pill bad">bloklagan</span>` : "");
  const meta = [u.username ? "@" + esc(u.username) : "", esc(u.segment || ""), u.source ? "manba: " + esc(u.source) : ""].filter(Boolean).join(" · ");
  return `<tr data-id="${u.id}">
    <td data-l="Ism"><div><span class="user-name">${name}</span><div class="sub">${meta}</div><div class="sub">ID: ${u.tg_id}</div></div></td>
    <td data-l="Telefon">${u.phone ? `<a href="tel:${esc(u.phone)}">${esc(u.phone)}</a>` : "—"}</td>
    <td data-l="Bepul kanal"><div>${freeCell(u)}${u.checked ? `<div class="sub">${esc(u.checked)}</div>` : ""}</div></td>
    <td data-l="Pullik kanal"><div>${paidCell(u.paid)}</div></td>
    <td data-l="Kurs guruhi"><div>${groupCell(u.groups)}</div></td>
    <td data-l="Xaridlar">${u.purchases.count ? `${u.purchases.count} ta<div class="sub">${money(u.purchases.sum)} so'm</div>` : "—"}</td>
    <td data-l="Sana"><span class="small">${esc(u.created)}</span></td>
    <td class="actions" data-l="">
      <button class="btn icon" data-act="check" title="Kanallardagi a'zolikni hozir tekshirish">${icon("refresh")}</button>
      <button class="btn icon" data-act="chat" title="Chat ochish">${icon("chat")}${u.unread ? `<span class="badge">${u.unread}</span>` : ""}</button>
    </td>
  </tr>`;
}

async function loadUsers() {
  const params = new URLSearchParams({
    q: $("#f-q").value.trim(), free: $("#f-free").value, paid: $("#f-paid").value,
    group: $("#f-group").value, segment: $("#f-segment").value, status: $("#f-status").value, page: users.page,
  });
  const data = await api("/api/users?" + params);
  users.pages = data.pages;
  users.items = Object.fromEntries(data.items.map((u) => [u.id, u]));
  $("#users-body").innerHTML = data.items.length ? data.items.map(userRow).join("") : `<tr><td colspan="8" class="empty">Hech kim topilmadi</td></tr>`;
  $("#users-total").textContent = `Jami: ${data.total}`;
  $("#page-info").textContent = ` ${data.page} / ${data.pages} `;
  $("#prev").disabled = data.page <= 1;
  $("#next").disabled = data.page >= data.pages;
}

let searchTimer;
$("#f-q").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { users.page = 1; loadUsers(); }, 350); });
["#f-free", "#f-paid", "#f-group", "#f-segment", "#f-status"].forEach((s) => $(s).addEventListener("change", () => { users.page = 1; loadUsers(); }));
$("#prev").onclick = () => { users.page--; loadUsers(); };
$("#next").onclick = () => { users.page++; loadUsers(); };

$("#users-body").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const tr = btn.closest("tr");
  const id = Number(tr.dataset.id);
  if (btn.dataset.act === "chat") { showTab("chat"); openChat(id); return; }
  btn.disabled = true;
  try {
    const u = await api(`/api/users/${id}/check`, { method: "POST" });
    tr.outerHTML = userRow(u);
    toast("Yangilandi");
  } catch (err) { toast(err.message, true); btn.disabled = false; }
});

let checkTimer;
async function pollCheckAll(start = false) {
  const p = await api("/api/users/check-all", { method: start ? "POST" : "GET" });
  const btn = $("#check-all");
  if (p.running) {
    btn.disabled = true;
    btn.querySelector("span").textContent = `Tekshirilmoqda ${p.done}/${p.total || "…"}`;
    checkTimer = setTimeout(() => pollCheckAll(), 2000);
  } else {
    btn.disabled = false;
    btn.querySelector("span").textContent = "A'zolikni yangilash";
    if (!start && checkTimer) { toast("A'zolik yangilandi"); loadUsers(); loadStats(); }
    checkTimer = null;
  }
}
$("#check-all").onclick = () => {
  if (confirm("Barcha foydalanuvchilarning kanallardagi a'zoligi Telegram'dan qayta tekshiriladi. Ko'p foydalanuvchi bo'lsa bir necha daqiqa oladi. Boshlaymizmi?")) pollCheckAll(true);
};

tabHandlers.users = () => { loadStats(); loadUsers(); };

/* ================= CHAT ================= */
const chat = { current: null, lastId: 0, items: [], file: null };

function setChatBadge(n) {
  const b = $("#chat-badge");
  b.textContent = n;
  b.classList.toggle("hidden", !n);
}

function initials(name) {
  return (name || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

const MEDIA = {
  photo: ["image", "Rasm"], video: ["video", "Video"], voice: ["mic", "Ovozli xabar"], document: ["file", "Fayl"],
  sticker: ["image", "Stiker"], audio: ["music", "Audio"], video_note: ["video", "Video xabar"], animation: ["image", "GIF"],
};
// HTML qaytaradi (xavfsiz)
function lastPreview(m) {
  const prefix = m.dir === "out" ? "Siz: " : "";
  const media = MEDIA[m.media_type];
  const mediaHtmlPart = media ? icon(media[0], "sm") + (m.text ? "" : media[1]) : "";
  return esc(prefix) + mediaHtmlPart + esc(m.text || "");
}

async function loadChats() {
  const q = $("#chat-q").value.trim();
  const list = await api("/api/chats?" + new URLSearchParams({ q }));
  chat.items = list;
  setChatBadge(list.filter((c) => c.unread && c.user_id !== chat.current).length);
  const box = $("#chat-items");
  if (!list.length) { box.innerHTML = `<div class="empty">Hali hech kim yozmagan.<br><span class="small">Foydalanuvchi botga istalgan xabar yozsa, shu yerda paydo bo'ladi.</span></div>`; return; }
  box.innerHTML = list.map((c) => `
    <div class="chat-item ${c.user_id === chat.current ? "active" : ""}" data-id="${c.user_id}">
      <div class="avatar">${esc(initials(c.name))}</div>
      <div class="meta">
        <div class="top"><span class="name">${esc(c.name || c.tg_id)}</span><span class="time">${esc(c.last.time)}</span></div>
        <div class="last"><span>${lastPreview(c.last)}</span>${c.unread && c.user_id !== chat.current ? `<span class="badge">${c.unread}</span>` : ""}</div>
      </div>
    </div>`).join("");
}
$("#chat-items").addEventListener("click", (e) => {
  const item = e.target.closest(".chat-item");
  if (item) openChat(Number(item.dataset.id));
});
let chatSearchTimer;
$("#chat-q").addEventListener("input", () => { clearTimeout(chatSearchTimer); chatSearchTimer = setTimeout(loadChats, 300); });

function mediaHtml(m) {
  if (!m.file_id) return "";
  const src = `/api/file/${encodeURIComponent(m.file_id)}`;
  switch (m.media_type) {
    case "photo": case "sticker": return `<img src="${src}" loading="lazy" data-zoom>`;
    case "video": case "animation": case "video_note": return `<video src="${src}" controls preload="none"></video>`;
    case "voice": case "audio": return `<audio src="${src}" controls preload="none"></audio>`;
    default: return `<a class="file-link" href="${src}" target="_blank">${icon("file")}${esc(m.file_name || "Fayl")}</a><br>`;
  }
}

function msgHtml(m) {
  const who = m.dir === "out" && m.admin ? `${esc(m.admin)} · ` : "";
  return `<div class="msg ${m.dir}">${mediaHtml(m)}${m.text ? esc(m.text) : ""}<div class="t">${who}${esc(m.time)}</div></div>`;
}

function appendMessages(list) {
  if (!list.length) return;
  const box = $("#messages");
  const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
  box.insertAdjacentHTML("beforeend", list.map(msgHtml).join(""));
  chat.lastId = list[list.length - 1].id;
  if (nearBottom || chat.forceScroll) box.scrollTop = box.scrollHeight;
  chat.forceScroll = false;
}

async function openChat(userId) {
  chat.current = userId;
  chat.lastId = 0;
  chat.forceScroll = true;
  $("#chat").classList.add("open");
  ["#conv-head", "#messages", "#composer"].forEach((s) => $(s).classList.remove("hidden"));
  $("#conv-empty").classList.add("hidden");
  $("#messages").innerHTML = "";
  const data = await api(`/api/chats/${userId}`);
  const u = data.user;
  $("#conv-avatar").textContent = initials(u.name);
  $("#conv-name").textContent = u.name || u.tg_id;
  $("#conv-sub").innerHTML = [u.phone ? esc(u.phone) : "", u.username ? `<a href="https://t.me/${esc(u.username)}" target="_blank">@${esc(u.username)}</a>` : "", u.blocked ? `<span class="pill bad">botni bloklagan</span>` : ""].filter(Boolean).join(" · ");
  if (!data.messages.length) $("#messages").innerHTML = `<div class="muted small" style="text-align:center">Hali yozishma yo'q. Birinchi bo'lib yozishingiz mumkin.</div>`;
  appendMessages(data.messages);
  $("#chat-text").focus();
  loadChats();
}
$("#messages").addEventListener("click", (e) => { if (e.target.matches("img[data-zoom]")) lightbox(e.target.src); });
$("#conv-back").onclick = () => { $("#chat").classList.remove("open"); chat.current = null; loadChats(); };

async function pollConversation() {
  if (!chat.current || document.hidden || $("#tab-chat").classList.contains("hidden")) return;
  const data = await api(`/api/chats/${chat.current}?after=${chat.lastId}`);
  appendMessages(data.messages);
}

$("#chat-file").addEventListener("change", (e) => {
  chat.file = e.target.files[0] || null;
  const el = $("#attach-name");
  el.classList.toggle("hidden", !chat.file);
  el.innerHTML = chat.file ? `${icon("clip", "sm")}${esc(chat.file.name)} <a href="#" id="attach-x">olib tashlash</a>` : "";
  if (chat.file) $("#attach-x").onclick = (ev) => { ev.preventDefault(); resetAttach(); };
});
function resetAttach() { chat.file = null; $("#chat-file").value = ""; $("#attach-name").classList.add("hidden"); }

const chatText = $("#chat-text");
chatText.addEventListener("input", () => { chatText.style.height = "auto"; chatText.style.height = Math.min(chatText.scrollHeight, 160) + "px"; });
chatText.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("#composer").requestSubmit(); }
});
$("#composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatText.value.trim();
  if (!text && !chat.file) return;
  const fd = new FormData();
  fd.append("text", text);
  if (chat.file) fd.append("file", chat.file);
  const btn = $("#chat-send");
  btn.disabled = true;
  try {
    const m = await api(`/api/chats/${chat.current}/send`, { method: "POST", body: fd });
    chatText.value = "";
    chatText.style.height = "auto";
    resetAttach();
    chat.forceScroll = true;
    if (m.id > chat.lastId) appendMessages([m]);
    loadChats();
  } catch (err) { toast(err.message, true); }
  btn.disabled = false;
});

tabHandlers.chat = () => loadChats();

/* Fon yangilanishlari */
setInterval(() => { pollConversation().catch(() => {}); }, 3000);
setInterval(() => {
  if (document.hidden) return;
  if (!$("#tab-chat").classList.contains("hidden")) loadChats().catch(() => {});
  else api("/api/stats").then((s) => setChatBadge(s.unread_chats)).catch(() => {});
}, 8000);

/* Boshlash (editor.js ham yuklangandan keyin) */
document.addEventListener("DOMContentLoaded", () => {
  loadGroupsFilter().catch(() => {});
  pollCheckAll().catch(() => {});
  let startTab = "users";
  try { startTab = localStorage.getItem("tab") || "users"; } catch (_) {}
  if (!["users", "chat", "content", "settings"].includes(startTab)) startTab = "users";
  showTab(startTab);
  if (startTab !== "users") loadStats().catch(() => {});
});

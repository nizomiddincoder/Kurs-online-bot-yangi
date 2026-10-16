/* Sozlamalar: kanal ID lari, havolalar, karta, narxlar, bot matnlari, panel paroli */
(function () {
  let state = null;

  /* ---------- Kichik matn muharriri (bot matnlari, tarif tavsiflari uchun) ---------- */
  function miniEditor(html, placeholder = "") {
    const wrap = document.createElement("div");
    wrap.className = "mini";
    wrap.innerHTML = `<div class="toolbar">
        <button type="button" class="btn" data-cmd="bold" title="Qalin"><b>B</b></button>
        <button type="button" class="btn" data-cmd="italic" title="Kursiv"><i>I</i></button>
        <button type="button" class="btn" data-cmd="underline" title="Tagiga chizilgan"><u>U</u></button>
        <button type="button" class="btn" data-wrap="code" title="Nusxalanadigan matn (prompt uchun qulay)">${icon("code")}</button>
        <button type="button" class="btn" data-link title="Havola">${icon("link")}</button>
      </div>
      <div class="editor" contenteditable="true"></div>`;
    const ed = wrap.querySelector(".editor");
    ed.innerHTML = html || "";
    ed.dataset.placeholder = placeholder;
    const tb = wrap.querySelector(".toolbar");
    tb.addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); });
    tb.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      const sel = getSelection();
      const r = sel.rangeCount ? sel.getRangeAt(0) : null;
      const inside = r && ed.contains(r.commonAncestorContainer);
      if (b.dataset.cmd) { ed.focus(); document.execCommand(b.dataset.cmd); }
      else if (b.dataset.wrap) {
        if (!inside || r.collapsed) return toast("Avval matnni belgilang");
        const el = document.createElement("code");
        el.appendChild(r.extractContents());
        r.insertNode(el);
      } else if (b.hasAttribute("data-link")) {
        if (!inside || r.collapsed) return toast("Avval havola bo'ladigan so'zni belgilang");
        const url = prompt("Havola (https://...):", "https://");
        if (url && /^https?:\/\//i.test(url)) { sel.removeAllRanges(); sel.addRange(r); document.execCommand("createLink", false, url); }
      }
      ed.dispatchEvent(new Event("input", { bubbles: true }));
    });
    ed.addEventListener("paste", (e) => { e.preventDefault(); document.execCommand("insertText", false, e.clipboardData.getData("text/plain")); });
    wrap.getHtml = () => ed.innerHTML;
    return wrap;
  }

  /* ---------- Maydonlar ---------- */
  const SOURCE = {
    panel: `<span class="pill ok src">Panelda kiritilgan</span>`,
    env: `<span class="pill neutral src">Railway Variables'dan</span>`,
    empty: `<span class="pill bad src">Kiritilmagan</span>`,
  };

  function fieldHtml(f) {
    const reset = f.source === "panel" && f.env_value
      ? `<button type="button" class="reset-link" data-reset="${f.name}" title="Railway'dagi qiymat: ${esc(f.env_value)}">Railway qiymatiga qaytarish</button>` : "";
    const check = f.kind === "chat" ? `<button type="button" class="btn" data-check="${f.name}">${icon("search")}Tekshirish</button>` : "";
    return `<div class="field" data-field="${f.name}">
      <label for="f-${f.name}">${esc(f.label)} ${SOURCE[f.source]} ${reset}</label>
      <div class="row"><input type="text" id="f-${f.name}" name="${f.name}" value="${esc(f.value)}" placeholder="${esc(f.placeholder)}" autocomplete="off">${check}</div>
      ${f.help ? `<div class="help">${esc(f.help)}</div>` : ""}
      <div class="fmsg"></div>
    </div>`;
  }

  function setMsg(name, cls, text) {
    const box = $(`[data-field="${name}"]`);
    if (!box) return;
    box.classList.toggle("invalid", cls === "field-err");
    const ic = { "field-ok": "check-circle", "field-warn": "alert", "field-err": "x-circle" }[cls];
    box.querySelector(".fmsg").innerHTML = text ? `<div class="${cls}">${icon(ic)}<span>${esc(text)}</span></div>` : "";
  }

  function render(s) {
    state = s;
    for (const sec of ["channels", "payment"]) {
      $(`#sec-${sec} .fields`).innerHTML = s.fields.filter((f) => f.section === sec).map(fieldHtml).join("");
    }

    const tf = $("#tariff-fields");
    tf.innerHTML = "";
    for (const t of s.tariffs) {
      const box = document.createElement("div");
      box.className = "tariff-box";
      box.dataset.code = t.code;
      box.innerHTML = `<h4>${esc(t.title)}</h4>
        <div class="field"><label>Narxi (so'm)</label><input type="text" inputmode="numeric" class="t-price" value="${t.price}" style="max-width:200px"></div>
        <div class="field"><label>Tavsifi</label><div class="t-desc"></div></div>`;
      const ed = miniEditor(t.desc, "Tarifga nimalar kiradi…");
      box.querySelector(".t-desc").append(ed);
      box.editor = ed;
      tf.append(box);
    }
    $("#senior-limit").value = s.senior_limit;

    const txt = $("#text-fields");
    txt.innerHTML = "";
    for (const t of s.texts) {
      const box = document.createElement("div");
      box.className = "field";
      box.innerHTML = `<label>${esc(t.label)}</label><div class="help" style="margin:0 0 6px">${esc(t.help)}</div><div class="ed"></div>
        <div class="sec-foot" style="margin-top:8px">
          <button type="button" class="btn" data-act="test">${icon("flask")}Menga yuborib ko'rish</button>
          <button type="button" class="btn primary" data-act="save">${icon("save")}Saqlash</button>
        </div>`;
      const ed = miniEditor(t.html);
      box.querySelector(".ed").append(ed);
      box.querySelectorAll("button[data-act]").forEach((b) => b.onclick = () => saveText(t.key, ed, b));
      txt.append(box);
    }

    $("#pw-source").textContent = s.system.password_source === "panel"
      ? "Parol shu paneldan o'rnatilgan."
      : "Hozir Railway'dagi ADMIN_PANEL_PASSWORD ishlatilmoqda. Bu yerda o'zgartirsangiz, yangisi ustun bo'ladi.";

    const sys = s.system;
    $("#system-info").innerHTML = [
      ["BOT_TOKEN", sys.bot ? `${icon("check-circle")}Ulangan: <b>${esc(sys.bot)}</b>` : `<span class="pill bad">Bot bilan aloqa yo'q</span>`],
      ["DATABASE_URL", sys.database.startsWith("PostgreSQL") ? `${icon("check-circle")}${esc(sys.database)}` : `${icon("alert")}${esc(sys.database)} — Railway'da Postgres ulang`],
      ["TIMEZONE", esc(sys.timezone)],
      ["ADMIN_PANEL_PASSWORD", "Panelga birinchi kirish paroli"],
    ].map(([k, v]) => `<div class="sys-line"><code>${k}</code><span>${v}</span></div>`).join("");
  }

  async function load() {
    try { render(await api("/api/settings")); } catch (e) { toast(e.message, true); }
  }

  /* ---------- Kanal tekshirish / qaytarish ---------- */
  document.addEventListener("click", async (e) => {
    const chk = e.target.closest("[data-check]");
    if (chk) {
      const name = chk.dataset.check;
      const value = $(`#f-${name}`).value.trim();
      if (!value) return setMsg(name, "field-err", "Avval ID ni kiriting");
      chk.disabled = true;
      try {
        const r = await api("/api/settings/check-chat", { json: { value } });
        if (r.ok) setMsg(name, "field-ok", `«${r.title}» — bot admin, huquqlari yetarli. ID: ${r.id}`);
        else if (r.id) setMsg(name, "field-warn", `«${r.title}» topildi (ID: ${r.id}), lekin ${r.problem}`);
        else setMsg(name, "field-err", r.problem);
      } catch (err) { setMsg(name, "field-err", err.message); }
      chk.disabled = false;
      return;
    }
    const rst = e.target.closest("[data-reset]");
    if (rst) {
      if (!confirm("Panelda kiritilgan qiymat o'chiriladi va Railway Variables'dagi qiymat ishlatiladi. Davom etamizmi?")) return;
      try { render((await api("/api/settings/reset", { json: { name: rst.dataset.reset } })).settings); toast("Qaytarildi"); }
      catch (err) { toast(err.message, true); }
    }
  });

  /* ---------- Saqlash: kanallar va to'lov ---------- */
  ["channels", "payment"].forEach((sec) => {
    $(`#sec-${sec}`).addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.currentTarget;
      const values = Object.fromEntries($$("input[name]", form).map((i) => [i.name, i.value]));
      if (sec === "channels" && state) {
        const before = state.fields.find((f) => f.name === "admin_ids")?.value;
        if (before && values.admin_ids !== before &&
            !confirm("Adminlar ro'yxati o'zgaryapti. Ro'yxatdan chiqarilgan odam endi chek va xabarlarni olmaydi. Davom etamizmi?")) return;
      }
      Object.keys(values).forEach((n) => setMsg(n, "", ""));
      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      try {
        const r = await fetch("/api/settings/config", {
          method: "POST", headers: { "X-Admin": "1", "Content-Type": "application/json" }, body: JSON.stringify({ values }),
        });
        const data = await r.json();
        if (r.status === 401) { location.href = "/login"; return; }
        if (!r.ok) {
          Object.entries(data.errors || {}).forEach(([n, m]) => setMsg(n, "field-err", m));
          toast(data.error || "Xatolarni to'g'rilang — saqlanmadi", true);
        } else {
          render(data.settings);
          Object.entries(data.warnings || {}).forEach(([n, m]) => setMsg(n, "field-warn", "Saqlandi, lekin: " + m));
          toast("Saqlandi va darhol kuchga kirdi");
        }
      } catch (err) { toast(err.message, true); }
      btn.disabled = false;
    });
  });

  /* ---------- Tariflar ---------- */
  $("#sec-tariffs").addEventListener("submit", async (e) => {
    e.preventDefault();
    const tariffs = {};
    $$("#tariff-fields .tariff-box").forEach((b) => {
      tariffs[b.dataset.code] = { price: b.querySelector(".t-price").value, desc: b.editor.getHtml() };
    });
    try {
      const r = await api("/api/settings/tariffs", { json: { tariffs, senior_limit: $("#senior-limit").value } });
      render(r.settings);
      toast("Tariflar saqlandi");
    } catch (err) { toast(err.message, true); }
  });

  /* ---------- Bot matnlari ---------- */
  async function saveText(key, ed, btn) {
    btn.disabled = true;
    try {
      if (btn.dataset.act === "test") {
        await api("/api/settings/text/test", { json: { html: ed.getHtml() } });
        toast("Telegram'ingizga yuborildi");
      } else {
        await api("/api/settings/text", { json: { key, html: ed.getHtml() } });
        toast("Saqlandi");
      }
    } catch (err) { toast(err.message, true); }
    btn.disabled = false;
  }

  /* ---------- Parol ---------- */
  $("#sec-password").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/settings/password", {
        json: { current: $("#pw-current").value, new: $("#pw-new").value, confirm: $("#pw-confirm").value },
      });
      ["#pw-current", "#pw-new", "#pw-confirm"].forEach((s) => ($(s).value = ""));
      toast("Parol o'zgardi. Boshqa qurilmalarda qayta kirish kerak bo'ladi.");
      load();
    } catch (err) { toast(err.message, true); }
  });

  tabHandlers.settings = load;
})();

/* Kontent muharriri: rasm, matn formatlash, so'zlarga ishlov berish, tugmalar, joylash */
(function () {
  const editor = $("#editor");
  const post = { media: [] }; // [{file, url, kind}]
  const EMOJIS = ["🔥", "✅", "❗️", "👉", "💡", "🎁", "📌", "🚀", "💎", "📚", "🤖", "⚡️", "🎯", "👇", "❤️", "😊", "🙌", "📈", "⏰", "🆕"];

  try { document.execCommand("defaultParagraphSeparator", false, "div"); } catch (_) {}

  /* ---------- Media ---------- */
  const input = $("#media-input");
  const drop = $("#dropzone");
  drop.onclick = () => input.click();
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); });
  input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

  function addFiles(files) {
    for (const f of files) {
      if (!/^(image|video)\//.test(f.type)) { toast(`${f.name}: faqat rasm yoki video`, true); continue; }
      if (post.media.length >= 10) { toast("Ko'pi bilan 10 ta", true); break; }
      post.media.push({ file: f, url: URL.createObjectURL(f), kind: f.type.startsWith("video/") ? "video" : "photo" });
    }
    renderMedia();
  }

  function mediaTag(m) {
    return m.kind === "video" ? `<video src="${m.url}" muted></video>` : `<img src="${m.url}">`;
  }

  function renderMedia() {
    $("#thumbs").innerHTML = post.media.map((m, i) => `<div class="thumb">${mediaTag(m)}<button data-i="${i}" title="O'chirish">${icon("x")}</button></div>`).join("");
    const n = post.media.length;
    const pv = $("#pv-media");
    pv.className = "tg-media " + (n > 4 ? "many" : `n${n}`);
    pv.innerHTML = post.media.map(mediaTag).join("");
    updateCounter();
  }
  $("#thumbs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-i]");
    if (!b) return;
    const [m] = post.media.splice(Number(b.dataset.i), 1);
    URL.revokeObjectURL(m.url);
    renderMedia();
  });

  /* ---------- Formatlash ---------- */
  function selectionInEditor() {
    const sel = getSelection();
    if (!sel.rangeCount) return null;
    const r = sel.getRangeAt(0);
    return editor.contains(r.commonAncestorContainer) ? r : null;
  }

  $("#toolbar").addEventListener("mousedown", (e) => { if (e.target.closest("button")) e.preventDefault(); }); // belgilash yo'qolmasin

  $$("#toolbar [data-cmd]").forEach((b) => b.addEventListener("click", () => {
    editor.focus();
    document.execCommand(b.dataset.cmd);
    changed();
  }));

  $$("#toolbar [data-wrap]").forEach((b) => b.addEventListener("click", () => {
    const r = selectionInEditor();
    if (!r || r.collapsed) { toast("Avval matnni belgilang"); return; }
    const type = b.dataset.wrap;
    const el = document.createElement(type === "spoiler" ? "span" : type);
    if (type === "spoiler") el.className = "tg-spoiler";
    el.appendChild(r.extractContents());
    r.insertNode(el);
    const sel = getSelection();
    sel.removeAllRanges();
    const nr = document.createRange();
    nr.selectNodeContents(el);
    sel.addRange(nr);
    changed();
  }));

  $("#link-btn").onclick = () => {
    const r = selectionInEditor();
    if (!r || r.collapsed) { toast("Avval havola bo'ladigan so'zni belgilang"); return; }
    const url = prompt("Havola (https://...):", "https://");
    if (!url || !/^(https?:\/\/|tg:\/\/)/i.test(url)) { if (url) toast("Havola https:// bilan boshlanishi kerak", true); return; }
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    document.execCommand("createLink", false, url);
    changed();
  };

  $("#clear-format").onclick = () => {
    const r = selectionInEditor();
    if (!r || r.collapsed) {
      if (!confirm("Butun matndagi formatlash olib tashlansinmi?")) return;
      editor.innerText = editor.innerText;
    } else {
      document.execCommand("removeFormat");
      document.execCommand("unlink");
      $$("code, .tg-spoiler, blockquote", editor).forEach((el) => {
        if (r.intersectsNode(el)) el.replaceWith(...el.childNodes);
      });
    }
    changed();
  };
  $("#undo").onclick = () => { editor.focus(); document.execCommand("undo"); changed(); };

  // Boshqa joydan nusxalanganda ortiqcha stillar kelmasin
  editor.addEventListener("paste", (e) => {
    const text = e.clipboardData.getData("text/plain");
    if (e.clipboardData.files.length) { e.preventDefault(); addFiles(e.clipboardData.files); return; }
    e.preventDefault();
    document.execCommand("insertText", false, text);
  });

  /* ---------- So'zlarga ishlov berish ---------- */
  function textNodes(root) {
    const out = [];
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) out.push(w.currentNode);
    return out;
  }

  function transformText(fn) {
    const r = selectionInEditor();
    const nodes = textNodes(editor);
    if (!r || r.collapsed) {
      // Butun matn: bir nechta bo'lakka bo'lingan so'zlar ham to'g'ri chiqishi uchun birlashtirib ishlaymiz
      nodes.forEach((n) => { n.data = fn(n.data); });
      return;
    }
    for (const n of nodes) {
      if (!r.intersectsNode(n)) continue;
      const s = n === r.startContainer ? r.startOffset : 0;
      const e = n === r.endContainer ? r.endOffset : n.data.length;
      n.data = n.data.slice(0, s) + fn(n.data.slice(s, e)) + n.data.slice(e);
    }
  }

  const BLOCKS = new Set(["DIV", "P", "BLOCKQUOTE", "LI"]);
  function prefixLines(makePrefix) {
    const r = selectionInEditor();
    const limit = r && !r.collapsed ? r : null;
    let atStart = true, idx = 0;
    const w = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    const todo = [];
    while (w.nextNode()) {
      const n = w.currentNode;
      if (n.nodeType === 1) { if (n.tagName === "BR" || BLOCKS.has(n.tagName)) atStart = true; continue; }
      const parts = n.data.split("\n");
      const res = parts.map((p, i) => {
        if (i > 0) atStart = true;
        if (atStart && p.trim()) {
          atStart = false;
          if (!limit || limit.intersectsNode(n)) return makePrefix(++idx) + p.replace(/^\s+/, "");
        }
        return p;
      });
      todo.push([n, res.join("\n")]);
    }
    todo.forEach(([n, d]) => { n.data = d; });
  }

  $("#transform").addEventListener("change", (e) => {
    const name = e.target.value;
    e.target.value = "";
    if (!name) return;
    if (name === "bullets") prefixLines(() => "• ");
    else if (name === "numbers") prefixLines((i) => `${i}. `);
    else transformText(Translit[name]);
    changed();
    editor.focus();
  });

  /* ---------- Emoji (faqat post matni uchun, yashirin oynada) ---------- */
  $("#emoji-btn").addEventListener("click", () => $("#emoji-row").classList.toggle("hidden"));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".emoji-wrap")) $("#emoji-row").classList.add("hidden");
  });
  $("#emoji-row").innerHTML = EMOJIS.map((e) => `<button type="button">${e}</button>`).join("");
  $("#emoji-row").addEventListener("mousedown", (e) => e.preventDefault());
  $("#emoji-row").addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    if (!selectionInEditor()) { editor.focus(); placeCaretAtEnd(); }
    document.execCommand("insertText", false, e.target.textContent);
    changed();
  });
  function placeCaretAtEnd() {
    const r = document.createRange();
    r.selectNodeContents(editor);
    r.collapse(false);
    const s = getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  /* ---------- Tugmalar ---------- */
  function addButtonRow(text = "", url = "") {
    const row = document.createElement("div");
    row.className = "btn-row";
    row.innerHTML = `<input type="text" placeholder="Tugma matni" maxlength="64" value="${esc(text)}">
      <input type="url" placeholder="https://havola" value="${esc(url)}">
      <button class="btn icon danger" title="O'chirish">${icon("trash")}</button>`;
    row.querySelector("button").onclick = () => { row.remove(); changed(); };
    row.addEventListener("input", changed);
    $("#btn-rows").append(row);
  }
  $("#add-btn").onclick = () => addButtonRow();
  function getButtons() {
    return $$("#btn-rows .btn-row").map((r) => {
      const [t, u] = r.querySelectorAll("input");
      return [{ text: t.value.trim(), url: u.value.trim() }];
    }).filter((r) => r[0].text || r[0].url);
  }

  /* ---------- Ko'rinish va hisoblagich ---------- */
  function updateCounter() {
    const len = editor.innerText.replace(/\n$/, "").trim().length;
    const limit = post.media.length ? 1024 : 4096;
    const el = $("#counter");
    let note = "";
    if (post.media.length && len > 1024) note = "Rasm izohi uchun uzun — rasm va matn alohida xabar bo'lib ketadi";
    if (len > 4096) note = "Telegram limiti 4096 belgi!";
    el.innerHTML = `<span>${note}</span><span>${len} / ${limit}</span>`;
    el.classList.toggle("over", len > limit);
  }

  function changed() {
    $("#pv-text").innerHTML = editor.innerHTML;
    $("#pv-buttons").innerHTML = getButtons().map((row) => `<div class="row">${row.map((b) => `<span>${esc(b.text || "…")}</span>`).join("")}</div>`).join("");
    updateCounter();
    saveDraft();
  }
  editor.addEventListener("input", changed);

  /* ---------- Qoralama (brauzerda saqlanadi) ---------- */
  function saveDraft() {
    try { localStorage.setItem("post-draft", JSON.stringify({ html: editor.innerHTML, buttons: getButtons() })); } catch (_) {}
  }
  function loadDraft() {
    try {
      const d = JSON.parse(localStorage.getItem("post-draft") || "null");
      if (!d) return;
      editor.innerHTML = d.html || "";
      (d.buttons || []).forEach((r) => addButtonRow(r[0].text, r[0].url));
    } catch (_) {}
  }

  function clearPost() {
    editor.innerHTML = "";
    $("#btn-rows").innerHTML = "";
    post.media.forEach((m) => URL.revokeObjectURL(m.url));
    post.media = [];
    renderMedia();
    changed();
  }
  $("#clear-post").onclick = () => { if (confirm("Post tozalansinmi?")) clearPost(); };

  /* ---------- Yuborish ---------- */
  function formData(extra) {
    const fd = new FormData();
    fd.append("html", editor.innerHTML);
    fd.append("buttons", JSON.stringify(getButtons()));
    fd.append("silent", $("#opt-silent").checked ? "1" : "0");
    fd.append("no_preview", $("#opt-nopreview").checked ? "1" : "0");
    post.media.forEach((m) => fd.append("files", m.file, m.file.name));
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    return fd;
  }

  function validate() {
    if (!editor.innerText.trim() && !post.media.length) { toast("Matn yoki rasm qo'shing", true); return false; }
    return true;
  }

  $("#test-post").onclick = async (e) => {
    if (!validate()) return;
    e.target.disabled = true;
    try {
      const r = await api("/api/posts", { method: "POST", body: formData({ test: "1" }) });
      const bad = r.results.filter((x) => !x.ok);
      bad.length ? toast("Xato: " + bad.map((x) => x.info).join("; "), true) : toast("Telegram'ingizga yuborildi — tekshiring");
    } catch (err) { toast(err.message, true); }
    e.target.disabled = false;
  };

  const dlg = $("#publish-dlg");
  $("#publish").onclick = async () => {
    if (!validate()) return;
    $("#publish-body").innerHTML = `<div class="muted">Yuklanmoqda…</div>`;
    $("#publish-go").classList.remove("hidden");
    $("#publish-go").disabled = false;
    $("#publish-cancel").textContent = "Bekor qilish";
    dlg.showModal();
    try {
      const t = await api("/api/targets");
      $("#publish-body").innerHTML =
        t.targets.map((x) => `<div class="target"><label><input type="checkbox" name="target" value="${esc(x.key)}">
          <span class="t-ico">${icon(x.key.startsWith("group") ? "users" : x.key === "paid" ? "crown" : "megaphone")}</span>
          <span style="flex:1"><b>${esc(x.title)}</b><div class="kind">${esc(x.kind)}</div></span></label></div>`).join("") +
        `<div class="target"><label><input type="checkbox" name="target" value="bot" id="t-bot">
          <span class="t-ico">${icon("bot")}</span><span style="flex:1"><b>Bot foydalanuvchilariga</b><div class="kind">Botdagi har bir foydalanuvchiga shaxsiy xabar</div></span></label>
          <select id="t-audience" style="margin-top:8px;width:100%">
            ${t.audiences.map((a) => `<option value="${esc(a.key)}">${esc(a.title)} — ${a.count} kishi</option>`).join("")}
          </select></div>`;
    } catch (err) { $("#publish-body").innerHTML = `<div class="pill bad">${esc(err.message)}</div>`; }
  };
  $("#publish-cancel").onclick = () => dlg.close();

  $("#publish-go").onclick = async () => {
    const targets = $$("input[name=target]:checked", dlg).map((i) => i.value);
    if (!targets.length) { toast("Kamida bitta joyni tanlang", true); return; }
    const titles = $$("input[name=target]:checked", dlg).map((i) => i.closest(".target").querySelector("b").textContent.trim());
    if (!confirm("Post quyidagilarga joylanadi:\n\n• " + titles.join("\n• ") + "\n\nDavom etamizmi?")) return;
    const btn = $("#publish-go");
    btn.disabled = true;
    btn.querySelector("span").textContent = "Joylanmoqda…";
    try {
      const r = await api("/api/posts", {
        method: "POST",
        body: formData({ targets: JSON.stringify(targets), audience: $("#t-audience")?.value || "all" }),
      });
      $("#publish-body").innerHTML = r.results.map((x) => `<div class="result-line">
        <span class="${x.ok ? "ok" : "bad"}">${icon(x.ok ? "check-circle" : "x-circle")}</span><div><b>${esc(x.title)}</b>${x.info ? `<div class="small muted">${esc(x.info)}</div>` : ""}</div></div>`).join("");
      btn.classList.add("hidden");
      $("#publish-cancel").textContent = "Yopish";
      if (r.results.every((x) => x.ok)) clearPost();
      loadHistory();
    } catch (err) { toast(err.message, true); }
    btn.disabled = false;
    btn.querySelector("span").textContent = "Joylash";
  };

  /* ---------- Tarix ---------- */
  async function loadHistory() {
    const list = await api("/api/posts");
    $("#history").innerHTML = list.length ? list.map((p) => `<div class="history-item">
      <div class="small muted">${esc(p.date)}${p.media_count ? ` · ${icon("image", "sm")} ${p.media_count}` : ""}</div>
      <div>${esc(p.text || "(matnsiz)")}</div>
      <div class="res">${p.results.map((x) => `<span class="pill ${x.ok ? "ok" : "bad"}" title="${esc(x.info || "")}">${esc(x.title)}</span>`).join("")}</div>
    </div>`).join("") : `<div class="muted">Hali post yo'q</div>`;
  }

  loadDraft();
  changed();
  tabHandlers.content = () => loadHistory().catch((e) => toast(e.message, true));
})();

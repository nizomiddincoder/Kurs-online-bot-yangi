/* So'zlarga ishlov berish funksiyalari (lotin/kirill, registr, tipografiya) */
(function () {
  const APOS = "'’‘ʻʼ`";
  const LAT = /[a-zA-Z]/;
  const LETTER = /[a-zA-ZЀ-ӿ'’‘ʻʼ`]/;
  const L2C = {
    a: "а", b: "б", c: "ц", d: "д", e: "е", f: "ф", g: "г", h: "ҳ", i: "и", j: "ж", k: "к", l: "л",
    m: "м", n: "н", o: "о", p: "п", q: "қ", r: "р", s: "с", t: "т", u: "у", v: "в", x: "х", y: "й", z: "з",
  };
  const C2L = {
    а: "a", б: "b", в: "v", г: "g", ғ: "gʻ", д: "d", ё: "yo", ж: "j", з: "z", и: "i", й: "y", к: "k",
    қ: "q", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ў: "oʻ", ф: "f",
    х: "x", ҳ: "h", ч: "ch", ш: "sh", щ: "sh", ъ: "ʼ", ь: "", ы: "i", э: "e", ю: "yu", я: "ya", ц: "ts",
  };
  const CYR_VOWELS = "аеёиоуўэюяъь";
  const isUpper = (ch) => !!ch && ch !== ch.toLowerCase();

  function lat2cyr(s) {
    let out = "";
    for (let i = 0; i < s.length; i++) {
      const c = s[i], lc = c.toLowerCase(), n = s[i + 1] || "", ln = n.toLowerCase();
      const prev = s[i - 1] || "";
      const wordStart = !LETTER.test(prev);
      let r = null, skip = 0;
      if ((lc === "o" || lc === "g") && n && APOS.includes(n)) { r = lc === "o" ? "ў" : "ғ"; skip = 1; }
      else if (lc === "s" && ln === "h") { r = "ш"; skip = 1; }
      else if (lc === "c" && ln === "h") { r = "ч"; skip = 1; }
      else if (lc === "y" && ln && "oaue".includes(ln)) { r = { o: "ё", a: "я", u: "ю", e: "е" }[ln]; skip = 1; }
      else if (lc === "e") { r = wordStart ? "э" : "е"; }
      else if (APOS.includes(c)) { r = LAT.test(prev) && LAT.test(n) ? "ъ" : c; }
      else r = L2C[lc] ?? null;
      if (r === null) { out += c; continue; }
      out += isUpper(c) ? r.toUpperCase() : r;
      i += skip;
    }
    return out;
  }

  function cyr2lat(s) {
    let out = "";
    for (let i = 0; i < s.length; i++) {
      const c = s[i], lc = c.toLowerCase(), prev = s[i - 1] || "", next = s[i + 1] || "";
      let r;
      if (lc === "е") {
        const wordStart = !LETTER.test(prev);
        r = wordStart || CYR_VOWELS.includes(prev.toLowerCase()) ? "ye" : "e";
      } else if (lc in C2L) r = C2L[lc];
      else { out += c; continue; }
      if (isUpper(c) && r) {
        const allUp = isUpper(next) || (isUpper(prev) && !LETTER.test(next));
        r = allUp ? r.toUpperCase() : r[0].toUpperCase() + r.slice(1);
      }
      out += r;
    }
    return out;
  }

  const title = (s) => s.toLowerCase().replace(/(^|[\s«"(\-—])([^\s])/gu, (m, a, b) => a + b.toUpperCase());
  const sentence = (s) => s.toLowerCase().replace(/(^\s*|[.!?…]\s+|\n\s*)([^\s])/gu, (m, a, b) => a + b.toUpperCase());
  const apos = (s) => s.replace(/([oOgG])['’`ʼ‘]/g, "$1ʻ").replace(/([a-zA-Z])['’`‘](?=[a-zA-Z])/g, "$1ʼ");
  const typo = (s) => s
    .replace(/"([^"\n]*)"/g, "«$1»")
    .replace(/(\s)--?(\s)/g, "$1—$2")
    .replace(/\.\.\./g, "…");
  const spaces = (s) => s.replace(/[ \t ]{2,}/g, " ").replace(/ +([,.!?;:])/g, "$1");
  const hashtag = (s) => s.replace(/(^|\s)([^\s#][^\s]*)/gu, (m, a, w) => {
    const clean = w.replace(/[^\p{L}\p{N}_ʻʼ']/gu, "");
    return clean ? `${a}#${clean}` : m;
  });
  const lines = (fn) => (s) => s.split("\n").map(fn).join("\n");
  let num = 0;
  const bullets = lines((l) => (l.trim() && !/^\s*•/.test(l) ? "• " + l.replace(/^\s+/, "") : l));
  const numbers = (s) => { num = 0; return lines((l) => (l.trim() ? `${++num}. ${l.replace(/^\s*(\d+\.\s*)?/, "")}` : l))(s); };

  window.Translit = {
    upper: (s) => s.toUpperCase(), lower: (s) => s.toLowerCase(), title, sentence,
    lat2cyr, cyr2lat, apos, typo, spaces, hashtag, bullets, numbers,
  };
  // Bu funksiyalar butun qatorlarga ishlaydi (bitta matn bo'lagiga emas)
  window.Translit.lineBased = new Set(["bullets", "numbers"]);
})();

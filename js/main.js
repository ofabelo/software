/* Oscar Fabelo – personal page: navigation, Laue pattern, publication list. */
(function () {
  "use strict";

  /* ---------- Mobile menu ---------- */
  const toggle = document.querySelector(".nav__toggle");
  const links = document.getElementById("nav-links");
  toggle.addEventListener("click", () => {
    const open = links.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  links.addEventListener("click", (e) => {
    if (e.target.tagName === "A") {
      links.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  /* ---------- Active section in the nav ---------- */
  const navLinks = [...links.querySelectorAll("a")];
  const sections = navLinks.map((a) => document.querySelector(a.getAttribute("href")));
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === "#" + entry.target.id));
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  sections.forEach((s) => s && spy.observe(s));

  /* ---------- Reveal on scroll ---------- */
  const revealables = document.querySelectorAll(".card, .product, .timeline li, .highlights li");
  const reveal = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        reveal.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealables.forEach((el) => { el.classList.add("reveal"); reveal.observe(el); });

  /* ---------- Hero: a Laue-like diffraction pattern ---------- */
  // Spots on a few zone circles, with a fixed pseudo-random seed so the
  // pattern is the same on every visit.
  const g = document.getElementById("laue-spots");
  if (g) {
    let seed = 7;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const ns = "http://www.w3.org/2000/svg";
    const add = (x, y, r, o) => {
      const c = document.createElementNS(ns, "circle");
      c.setAttribute("cx", x.toFixed(1));
      c.setAttribute("cy", y.toFixed(1));
      c.setAttribute("r", r.toFixed(1));
      c.setAttribute("fill", "url(#spot)");
      c.setAttribute("opacity", o.toFixed(2));
      g.appendChild(c);
    };
    add(300, 300, 16, 0.9);
    [[80, 6], [150, 12], [220, 12], [290, 18]].forEach(([r, n], k) => {
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + k * 0.26;
        const size = 3 + rnd() * 7 * (1 - k * 0.15);
        add(300 + r * Math.cos(a), 300 + r * Math.sin(a), size, 0.25 + rnd() * 0.6);
      }
    });
    for (let i = 0; i < 40; i++) {
      const a = rnd() * Math.PI * 2, r = 40 + rnd() * 260;
      add(300 + r * Math.cos(a), 300 + r * Math.sin(a), 1.5 + rnd() * 3, 0.15 + rnd() * 0.35);
    }
  }

  /* ---------- Software: latest versions and release notes ---------- */
  const SOFT = window.SOFTWARE || {};
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const fmtDate = (d) => {
    const [y, m, day] = String(d || "").split("-").map(Number);
    if (!y) return "";
    if (!m) return String(y);
    return (day ? day + " " : "") + MONTHS[m - 1] + " " + y;
  };

  // Download buttons, version pills and dates come from js/releases.js,
  // so a new release only needs editing there.
  document.querySelectorAll("[data-product]").forEach((card) => {
    const sw = SOFT[card.dataset.product];
    if (!sw || card.classList.contains("tab")) return;
    const L = sw.latest;
    card.querySelectorAll('[data-field="version"]').forEach((el) => { el.textContent = "v" + L.version; });
    card.querySelectorAll('[data-field="date"]').forEach((el) => { el.textContent = fmtDate(L.date); });
    card.querySelectorAll('[data-field="size"]').forEach((el) => { el.textContent = L.size; });
    card.querySelectorAll('[data-field="file"]').forEach((el) => el.setAttribute("href", L.file));
    card.querySelectorAll('[data-field="manual"]').forEach((el) => el.setAttribute("href", L.manual));
  });

  const announce = document.getElementById("announce-text");
  if (announce && SOFT.panda && SOFT.editpycr) {
    announce.textContent = "PANDA " + SOFT.panda.latest.version + " · Edit_PyCR " + SOFT.editpycr.latest.version;
  }

  const panel = document.getElementById("news-panel");
  const tabs = [...document.querySelectorAll(".tab")];

  const RECENT = 4; // releases shown before "Show older versions"
  const TYPE_LABEL = { new: "New", improved: "Improved", fixed: "Fixed" };

  // A note is either plain text/HTML or {type, text}.
  const noteHtml = (n) => {
    const label = typeof n === "string" ? null : TYPE_LABEL[n.type];
    const text = typeof n === "string" ? n : n.text;
    if (!label) return '<li class="plain">' + text + "</li>";
    return '<li><span class="kind kind--' + n.type + '">' + label + "</span><span>" + text + "</span></li>";
  };

  function renderNews(key, showAll) {
    const sw = SOFT[key];
    if (!panel || !sw) return;
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.product === key)));
    let html = "";
    const list = showAll ? sw.releases : sw.releases.slice(0, RECENT);
    list.forEach((r) => {
      const isLatest = r.version === sw.latest.version;
      html +=
        '<article class="release' + (isLatest ? " release--latest" : "") + '">' +
        "<header><span class=\"release__v\">" + sw.name + " " + r.version + "</span>" +
        '<time class="release__date">' + fmtDate(r.date) + "</time>" +
        (isLatest ? '<a class="release__tag" href="' + sw.latest.file + '" download>Latest · download</a>' : "") +
        "</header><ul>" + r.notes.map(noteHtml).join("") + "</ul></article>";
    });
    const hidden = sw.releases.length - list.length;
    if (hidden > 0) {
      html += '<button type="button" class="btn btn--ghost release__more">Show ' + hidden +
        " older version" + (hidden > 1 ? "s" : "") + "</button>";
    }
    panel.innerHTML = html;
    const more = panel.querySelector(".release__more");
    if (more) more.addEventListener("click", () => renderNews(key, true));
  }

  tabs.forEach((t) => t.addEventListener("click", () => renderNews(t.dataset.product)));
  tabs.forEach((t, i) => t.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    next.focus();
    renderNews(next.dataset.product);
  }));
  document.querySelectorAll("[data-news]").forEach((a) =>
    a.addEventListener("click", () => renderNews(a.dataset.news)));
  renderNews("panda");

  /* ---------- Publications ---------- */
  const PUBS = (window.PUBLICATIONS || []).filter((p) => p.t);
  const list = document.getElementById("pub-list");
  const search = document.getElementById("pub-search");
  const yearsBox = document.getElementById("pub-years");
  const count = document.getElementById("pub-count");
  const more = document.getElementById("pub-more");
  const statPubs = document.getElementById("stat-pubs");
  const PAGE = 25;
  const MAX_AUTHORS = 8;

  if (statPubs && PUBS.length) statPubs.textContent = PUBS.length;

  const periods = [
    { label: "All", test: () => true },
    { label: "2024 –", test: (y) => y >= 2024 },
    { label: "2019 – 2023", test: (y) => y >= 2019 && y <= 2023 },
    { label: "2014 – 2018", test: (y) => y >= 2014 && y <= 2018 },
    { label: "2009 – 2013", test: (y) => y >= 2009 && y <= 2013 },
    { label: "– 2008", test: (y) => y <= 2008 },
  ];
  let period = 0;
  let shown = PAGE;

  periods.forEach((p, i) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.textContent = p.label;
    b.setAttribute("aria-pressed", String(i === 0));
    b.addEventListener("click", () => {
      period = i;
      shown = PAGE;
      [...yearsBox.children].forEach((c, j) => c.setAttribute("aria-pressed", String(j === i)));
      render();
    });
    yearsBox.appendChild(b);
  });

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // Titles carry <sub>/<sup>/<i> from Zotero; everything else is escaped.
  const safeTitle = (s) => esc(s).replace(/&lt;(\/?)(sub|sup|i)&gt;/g, "<$1$2>");
  const plain = (s) => s.replace(/<[^>]+>/g, "");
  const norm = (s) => plain(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  PUBS.forEach((p) => {
    p._hay = norm([p.t, p.a.join(" "), p.j, p.y, p.doi].join(" "));
  });

  function highlight(html, terms) {
    if (!terms.length) return html;
    // Only highlight in text nodes, never inside tags.
    return html.replace(/(^|>)([^<]+)/g, (m, lead, text) => {
      let out = text;
      terms.forEach((t) => {
        const re = new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
        out = out.replace(re, "<mark>$1</mark>");
      });
      return lead + out;
    });
  }

  function authors(a) {
    const shortList = a.length > MAX_AUTHORS ? a.slice(0, MAX_AUTHORS - 1) : a;
    let html = shortList.map((n) => (/fabelo/i.test(n) ? '<span class="me">' + esc(n) + "</span>" : esc(n))).join(", ");
    if (a.length > MAX_AUTHORS) {
      const me = a.find((n) => /fabelo/i.test(n));
      const mine = me && !shortList.includes(me) ? ', …, <span class="me">' + esc(me) + "</span>" : "";
      html += mine + ", et al.";
    }
    return html;
  }

  function source(p) {
    let s = "<em>" + esc(p.j) + "</em>";
    if (p.v) s += " <strong>" + esc(p.v) + "</strong>";
    if (p.p) s += ", " + esc(p.p);
    if (p.y) s += " (" + p.y + ")";
    return s;
  }

  function render() {
    const terms = norm(search.value).split(/\s+/).filter(Boolean);
    const hits = PUBS.filter((p) => periods[period].test(p.y || 0) && terms.every((t) => p._hay.includes(t)));
    count.textContent = hits.length === PUBS.length
      ? PUBS.length + " publications"
      : hits.length + " of " + PUBS.length + " publications";

    if (!hits.length) {
      list.innerHTML = '<p class="empty">No publications match your search.</p>';
      more.hidden = true;
      return;
    }

    let html = "";
    let lastYear = null;
    hits.slice(0, shown).forEach((p) => {
      if (p.y !== lastYear) {
        html += '<h4 class="year">' + (p.y || "—") + "</h4>";
        lastYear = p.y;
      }
      const url = p.doi ? "https://doi.org/" + encodeURI(p.doi) : null;
      const title = highlight(safeTitle(p.t), terms);
      html +=
        '<article class="pub">' +
        '<div class="pub__title">' + (url ? '<a href="' + url + '" target="_blank" rel="noopener">' + title + "</a>" : title) + "</div>" +
        '<div class="pub__authors">' + highlight(authors(p.a), terms) + "</div>" +
        '<div class="pub__src">' + highlight(source(p), terms) +
        (p.doi ? '<span class="pub__doi">doi:' + esc(p.doi) + "</span>" : "") +
        "</div></article>";
    });
    list.innerHTML = html;

    const rest = hits.length - shown;
    more.hidden = rest <= 0;
    more.textContent = "Show more (" + Math.max(rest, 0) + " remaining)";
  }

  let timer;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => { shown = PAGE; render(); }, 120);
  });
  more.addEventListener("click", () => { shown += PAGE; render(); });

  render();

  document.getElementById("year").textContent = new Date().getFullYear();
})();

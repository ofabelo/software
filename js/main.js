/* PANDA & Edit_PyCR – navigation, Laue pattern, screenshots, downloads and release notes. */
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
  // The guide sections below each product count as part of that product.
  const navLinks = [...links.querySelectorAll("a")];
  const owner = { "panda-guide": "panda", "edit-pycr-guide": "edit-pycr" };
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const id = owner[entry.target.id] || entry.target.id;
      navLinks.forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === "#" + id));
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  ["panda", "panda-guide", "edit-pycr", "edit-pycr-guide", "download", "news", "support"]
    .forEach((id) => { const s = document.getElementById(id); if (s) spy.observe(s); });

  /* ---------- Reveal on scroll ---------- */
  const revealables = document.querySelectorAll(".feature, .flow__step, .guide li, .dl, .gallery, .callout");
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

  /* ---------- Screenshot galleries ---------- */
  const lightbox = document.getElementById("lightbox");
  document.querySelectorAll("[data-gallery]").forEach((gal) => {
    const stageImg = gal.querySelector(".gallery__zoom img");
    const caption = gal.querySelector("figcaption");
    const thumbs = [...gal.querySelectorAll(".gallery__thumbs button")];
    thumbs.forEach((t) => t.addEventListener("click", () => {
      thumbs.forEach((b) => b.classList.toggle("is-active", b === t));
      stageImg.src = t.dataset.src;
      stageImg.alt = t.querySelector("img").alt;
      caption.textContent = t.dataset.caption;
    }));
    gal.querySelector(".gallery__zoom").addEventListener("click", () => {
      if (!lightbox || typeof lightbox.showModal !== "function") {
        window.open(stageImg.src, "_blank");
        return;
      }
      lightbox.querySelector("img").src = stageImg.src;
      lightbox.querySelector("img").alt = stageImg.alt;
      lightbox.querySelector(".lightbox__caption").textContent = caption.textContent;
      lightbox.showModal();
    });
  });
  if (lightbox) {
    // A click on the backdrop (outside the image) closes the lightbox.
    lightbox.addEventListener("click", (e) => { if (e.target === lightbox) lightbox.close(); });
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

  // Download buttons, version pills, dates and manual links come from
  // js/releases.js, so a new release only needs editing there.
  const fields = (box, name) => [box, ...box.querySelectorAll('[data-field="' + name + '"]')]
    .filter((el) => el.dataset.field === name);
  document.querySelectorAll("[data-product]").forEach((box) => {
    const sw = SOFT[box.dataset.product];
    if (!sw || box.classList.contains("tab")) return;
    const L = sw.latest;
    fields(box, "version").forEach((el) => { el.textContent = "v" + L.version; });
    fields(box, "date").forEach((el) => { el.textContent = fmtDate(L.date); });
    fields(box, "size").forEach((el) => { el.textContent = L.size; });
    fields(box, "file").forEach((el) => el.setAttribute("href", L.file));
    fields(box, "manual").forEach((el) => el.setAttribute("href", L.manual));
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
  renderNews("panda");

  document.getElementById("year").textContent = new Date().getFullYear();
})();

// HARDPRICE — mobile-app-style screen router + data layer.
(function () {
  "use strict";

  var IMG_BASE = window.HP_STATIC || "/static/price/img/hw/";
  var CATS = [
    { id: "gpu", label: "显卡", short: "GPU", color: "#6EA8FE" },
    { id: "cpu", label: "处理器", short: "CPU", color: "#A78BFA" },
    { id: "ram", label: "内存", short: "RAM", color: "#34D399" },
    { id: "ssd", label: "固态硬盘", short: "SSD", color: "#FBBF24" },
    { id: "motherboard", label: "主板", short: "主板", color: "#FB923C" },
    { id: "custom", label: "自定义", short: "自定义", color: "#F472B6" },
  ];
  var CAT_BY_ID = {}; CATS.forEach(function (c) { CAT_BY_ID[c.id] = c; });
  function catImg(cat) { return IMG_BASE + (CAT_BY_ID[cat] ? cat : "custom") + ".svg"; }
  function catLabel(cat) { return CAT_BY_ID[cat] ? CAT_BY_ID[cat].label : "自定义"; }
  function catColor(cat) { return CAT_BY_ID[cat] ? CAT_BY_ID[cat].color : "#F472B6"; }

  // Small flat line-icon glyphs for the category row / picker (kept separate from
  // the bigger illustrated artwork used on cards and the detail hero).
  var CAT_ICON_PATHS = {
    gpu: '<path d="M4 15v-4a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2z"/><circle cx="9" cy="13" r="2"/><circle cx="15" cy="13" r="2"/>',
    cpu: '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M9 4v3M12 4v3M15 4v3M9 17v3M12 17v3M15 17v3M4 9h3M4 12h3M4 15h3M17 9h3M17 12h3M17 15h3"/>',
    ram: '<rect x="4" y="9" width="16" height="8" rx="1.5"/><path d="M7 9V6M11 9V6M15 9V6M7 17v2M11 17v2M15 17v2"/>',
    ssd: '<rect x="4" y="6" width="16" height="12" rx="2"/><circle cx="15.5" cy="14.5" r="1.5"/><path d="M7 10h5"/>',
    motherboard: '<path d="M4 6h16v9l-3 3H7l-3-3z"/><rect x="7" y="9" width="5" height="5" rx="1"/><path d="M14 9h4M14 12h4"/>',
    custom: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/>',
  };
  function catIconSvg(cat, size) {
    size = size || 22;
    var d = CAT_ICON_PATHS[cat] || CAT_ICON_PATHS.custom;
    return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + d + "</svg>";
  }

  function fmtJPY(n) { return n == null ? "--" : "¥" + Math.round(n).toLocaleString(); }
  function fmtCNY(n) { return n == null ? "--" : "¥" + Number(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }); }
  function escHtml(s) { return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  // A price drop is good news for a buyer (green); a price rise is bad news (red).
  function pctBadge(pct) {
    if (pct == null || isNaN(pct)) return { text: "--", cls: "" };
    var sign = pct > 0 ? "+" : "";
    return { text: sign + pct.toFixed(1) + "%", cls: pct < 0 ? "price-good" : pct > 0 ? "price-bad" : "" };
  }
  // Infer a display "brand" line from the keyword text — a plain naming-convention
  // fact (RTX implies NVIDIA GeForce, etc.), not fabricated data.
  function brandLine(category, name) {
    name = name || "";
    if (category === "gpu") {
      if (/\bRTX\b|\bGTX\b/i.test(name)) return "NVIDIA GeForce";
      if (/\bRX\s?\d/i.test(name) || /Radeon/i.test(name)) return "AMD Radeon";
      if (/\bArc\b/i.test(name)) return "Intel Arc";
    } else if (category === "cpu") {
      if (/Ryzen/i.test(name)) return "AMD Ryzen";
      if (/Core Ultra/i.test(name)) return "Intel Core Ultra";
      if (/Core i\d/i.test(name)) return "Intel Core";
    }
    return "";
  }
  // Minimal inline sparkline from real trend points (no fabricated data).
  function sparklineSvg(points, color) {
    if (!points || points.length < 2) return "";
    var vals = points.map(function (p) { return p.avg; });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    var range = max - min || 1;
    var w = 100, h = 26;
    var coords = vals.map(function (v, i) {
      var x = (i / (vals.length - 1)) * w;
      var y = h - ((v - min) / range) * h;
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    return '<svg class="spark" viewBox="0 0 ' + w + " " + h + '" preserveAspectRatio="none"><polyline points="' + coords + '" stroke="' + color + '"/></svg>';
  }

  var toastEl = document.getElementById("toast");
  var toastTimer = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 2600);
  }

  // ── Global state ──────────────────────────────────────────────────────────
  var state = {
    tab: "home",
    category: "gpu",
    kwAll: [],            // full keyword list (all categories) from keywords-manage
    kwByName: {},
    exRate: null,
    overviewByCat: {},
    homeKeywords: [],     // keywords for current home category (with latest price)
    detailName: null,
    detailDaily: [],
    detailDays: 30,
    channelsName: null,
    alertName: null,
    alertCurrentPrice: null,
    alertDir: "below",
    collectList: [],      // ordered names sent to the running/last collect job
    collectTimer: null,
  };

  function api(path) { return fetch(path).then(function (r) { return r.json(); }); }

  // ── Splash ───────────────────────────────────────────────────────────────
  (function initSplash() {
    var splash = document.getElementById("splash");
    var alreadyEntered = false;
    try { alreadyEntered = !!sessionStorage.getItem("hardprice-entered"); } catch (e) {}
    if (alreadyEntered) return;

    var starsWrap = document.getElementById("splashStars");
    for (var i = 0; i < 60; i++) {
      var s = document.createElement("span");
      s.style.left = Math.random() * 100 + "%";
      s.style.top = Math.random() * 65 + "%";
      s.style.animationDelay = (Math.random() * 3).toFixed(2) + "s";
      s.style.opacity = (0.3 + Math.random() * 0.7).toFixed(2);
      starsWrap.appendChild(s);
    }

    var closed = false;
    function enterApp() {
      if (closed) return;
      closed = true;
      splash.close();
      try { sessionStorage.setItem("hardprice-entered", "1"); } catch (e) {}
    }

    try {
      splash.showModal();
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { document.getElementById("splashProgressFill").style.width = "100%"; });
      });
      setTimeout(enterApp, 2200);
      splash.addEventListener("click", enterApp);
    } catch (e) { enterApp(); }
  })();

  // ── Tab / screen router ──────────────────────────────────────────────────
  function showTab(tab) {
    state.tab = tab;
    document.querySelectorAll(".screen[data-screen-id]").forEach(function (sec) {
      var id = sec.getAttribute("data-screen-id");
      var isOverlay = sec.classList.contains("overlay");
      if (isOverlay) return; // overlays managed separately
      sec.hidden = id !== tab;
    });
    document.querySelectorAll("#bottomNav button").forEach(function (btn) {
      btn.setAttribute("aria-current", String(btn.getAttribute("data-tab") === tab));
    });
    closeAllOverlays();
    if (tab === "home") loadHome();
    else if (tab === "search") { document.getElementById("searchInput").focus(); }
    else if (tab === "collect") loadCollectTab();
    else if (tab === "watch") loadManageTab();
    else if (tab === "profile") loadProfileTab();
  }
  document.querySelectorAll("#bottomNav button").forEach(function (btn) {
    btn.addEventListener("click", function () { showTab(btn.getAttribute("data-tab")); });
  });

  function openOverlay(id) {
    closeAllOverlays();
    var el = document.querySelector('.screen.overlay[data-screen-id="' + id + '"]');
    if (el) el.hidden = false;
    document.getElementById("bottomNav").hidden = true;
  }
  function closeAllOverlays() {
    document.querySelectorAll(".screen.overlay").forEach(function (el) { el.hidden = true; });
    document.getElementById("bottomNav").hidden = false;
  }
  document.querySelectorAll(".screen.overlay [data-back]").forEach(function (btn) {
    btn.addEventListener("click", function () { closeAllOverlays(); });
  });

  // ── Category sheet ───────────────────────────────────────────────────────
  var catSheetBackdrop = document.getElementById("categorySheetBackdrop");
  var catSheet = document.getElementById("categorySheet");
  function renderCategorySheetList() {
    var list = document.getElementById("categorySheetList");
    list.innerHTML = CATS.map(function (c) {
      return '<div class="sheet-row' + (c.id === state.category ? " active" : "") + '" data-cat="' + c.id + '">' +
        '<div class="ico" style="background:' + c.color + '22;color:' + c.color + '">' + catIconSvg(c.id, 20) + "</div>" +
        '<div class="label">' + c.label + (c.short !== c.label ? " (" + c.short + ")" : "") + "</div>" +
        '<svg class="check" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>' +
        "</div>";
    }).join("");
    list.querySelectorAll(".sheet-row").forEach(function (row) {
      row.addEventListener("click", function () {
        state.category = row.getAttribute("data-cat");
        closeCategorySheet();
        loadHome();
      });
    });
  }
  function openCategorySheet() { renderCategorySheetList(); catSheetBackdrop.hidden = false; catSheet.hidden = false; }
  function closeCategorySheet() { catSheetBackdrop.hidden = true; catSheet.hidden = true; }
  catSheetBackdrop.addEventListener("click", closeCategorySheet);

  // ── Home ─────────────────────────────────────────────────────────────────
  function greeting() {
    var h = new Date().getHours();
    var g = h < 6 ? "Good night" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    return g + " 👋";
  }

  function renderHomeCatRow() {
    var row = document.getElementById("homeCatRow");
    row.innerHTML = CATS.map(function (c) {
      var active = c.id === state.category;
      return '<button type="button" class="cat-pill' + (active ? " active" : "") + '" data-cat="' + c.id + '" style="color:' + c.color + '">' +
        '<span class="cat-icon" style="background:' + c.color + (active ? "33" : "1c") + '">' + catIconSvg(c.id, 24) + "</span>" +
        '<span class="label">' + c.short + "</span></button>";
    }).join("") + '<button type="button" class="cat-pill" id="catMoreBtn" style="color:var(--hp-muted)"><span class="cat-icon" style="background:var(--hp-surface)">▾</span><span class="label">全部</span></button>';
    row.querySelectorAll(".cat-pill[data-cat]").forEach(function (btn) {
      btn.addEventListener("click", function () { state.category = btn.getAttribute("data-cat"); loadHome(); });
    });
    document.getElementById("catMoreBtn").addEventListener("click", openCategorySheet);
  }

  function renderOverviewTiles() {
    var wrap = document.getElementById("overviewTiles");
    var order = ["gpu", "ssd", "ram", "cpu", "motherboard", "custom"];
    var rows = order.filter(function (cat) { return state.overviewByCat[cat]; }).map(function (cat) {
      var d = state.overviewByCat[cat];
      var pct = d.change_pct;
      var b = pctBadge(pct);
      var color = catColor(cat);
      var spark = sparklineSvg(d.trend, b.cls === "price-good" ? "#34D399" : b.cls === "price-bad" ? "#FB7185" : color);
      return '<div class="overview-tile" style="--tile-accent:' + color + '"><p class="label">' + catLabel(cat) + '</p><p class="pct ' + b.cls + '">' + b.text + "</p>" + spark + "</div>";
    });
    wrap.innerHTML = rows.join("") || '<p class="search-empty" style="padding:20px 0">暂无市场数据</p>';
  }

  function renderRateBadge() {
    var el = document.getElementById("rateBadge");
    var r = state.exRate;
    if (!r) { el.textContent = "汇率加载中…"; return; }
    el.classList.toggle("stale", !!r.stale);
    el.innerHTML = "<span>实时汇率 · 1 CNY ≈ <b>¥" + r.cny_to_jpy.toFixed(2) + "</b> JPY</span>" +
      (r.stale ? "<span>⚠ 汇率获取失败，使用参考值</span>" : "<span>已更新</span>");
  }

  function isFav(name) {
    try { return (JSON.parse(localStorage.getItem("hp-favs") || "[]")).indexOf(name) !== -1; } catch (e) { return false; }
  }
  function toggleFav(name) {
    try {
      var favs = JSON.parse(localStorage.getItem("hp-favs") || "[]");
      var i = favs.indexOf(name);
      if (i === -1) favs.push(name); else favs.splice(i, 1);
      localStorage.setItem("hp-favs", JSON.stringify(favs));
    } catch (e) {}
  }

  function productCardHtml(kw) {
    var price = fmtJPY(kw.latest_low_price);
    var b = pctBadge(kw._changePct);
    var fav = isFav(kw.name);
    var brand = brandLine(kw.category, kw.name);
    return '<div class="product-card" data-name="' + escHtml(kw.name) + '">' +
      '<span class="thumb"><img src="' + catImg(kw.category) + '" alt=""></span>' +
      '<div class="info">' + (brand ? '<p class="brand">' + escHtml(brand) + "</p>" : "") +
      '<p class="name">' + escHtml(kw.name) + '</p><p class="meta">' + (kw.latest_date || "暂无数据") + '</p></div>' +
      '<div class="price-col"><p class="price">' + price + '</p><p class="pct ' + b.cls + '">' + b.text + '</p></div>' +
      '<button type="button" class="fav-btn' + (fav ? " active" : "") + '" data-fav="' + escHtml(kw.name) + '">' +
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="' + (fav ? "currentColor" : "none") + '" stroke="currentColor" stroke-width="2"><path d="M20.8 4.6a5.5 5.5 0 00-7.8 0L12 5.6l-1-1a5.5 5.5 0 00-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 000-7.8z"/></svg></button>' +
      "</div>";
  }
  function wireProductCards(wrap, onFavToggle) {
    wrap.querySelectorAll(".product-card").forEach(function (card) {
      card.addEventListener("click", function (e) {
        if (e.target.closest("[data-fav]")) return;
        openDetail(card.getAttribute("data-name"));
      });
    });
    wrap.querySelectorAll("[data-fav]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        toggleFav(btn.getAttribute("data-fav"));
        onFavToggle();
      });
    });
  }

  var HOME_LIST_PREVIEW = 6;
  function renderProductList() {
    var wrap = document.getElementById("productList");
    var empty = document.getElementById("productListEmpty");
    document.getElementById("productListTitle").textContent = "🔥 " + catLabel(state.category) + " 热门";
    if (!state.homeKeywords.length) { wrap.innerHTML = ""; empty.hidden = false; return; }
    empty.hidden = true;
    var preview = state.homeKeywords.slice(0, HOME_LIST_PREVIEW);
    wrap.innerHTML = preview.map(productCardHtml).join("");
    wireProductCards(wrap, renderProductList);
  }

  // ── Category list (full list + sort, opened from "查看全部") ────────────
  function sortCategoryItems(items, sort) {
    var out = items.slice();
    if (sort === "price") {
      out.sort(function (a, b) { return (a.latest_low_price == null) - (b.latest_low_price == null) || (a.latest_low_price || 0) - (b.latest_low_price || 0); });
    } else if (sort === "change") {
      out.sort(function (a, b) { return (a._changePct == null) - (b._changePct == null) || (a._changePct || 0) - (b._changePct || 0); });
    } else if (sort === "updated") {
      out.sort(function (a, b) { return (b.latest_date || "").localeCompare(a.latest_date || ""); });
    }
    return out;
  }
  function renderCategoryListItems() {
    var wrap = document.getElementById("categoryListItems");
    var empty = document.getElementById("categoryListEmpty");
    if (!state.homeKeywords.length) { wrap.innerHTML = ""; empty.hidden = false; return; }
    empty.hidden = true;
    var items = sortCategoryItems(state.homeKeywords, state.categoryListSort);
    wrap.innerHTML = items.map(productCardHtml).join("");
    wireProductCards(wrap, renderCategoryListItems);
  }
  function openCategoryList() {
    document.getElementById("categoryListTitle").textContent = catLabel(state.category) + " (" + (CAT_BY_ID[state.category] ? CAT_BY_ID[state.category].short : "") + ")";
    state.categoryListSort = "default";
    document.querySelectorAll("#categoryListSortTabs button").forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-sort") === "default"); });
    renderCategoryListItems();
    openOverlay("categoryList");
  }
  document.querySelectorAll("#categoryListSortTabs button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.categoryListSort = btn.getAttribute("data-sort");
      document.querySelectorAll("#categoryListSortTabs button").forEach(function (b) { b.classList.toggle("active", b === btn); });
      renderCategoryListItems();
    });
  });

  function loadCategoryOverview() {
    return api("/api/category-overview/").then(function (data) {
      state.overviewByCat = {};
      (data.categories || []).forEach(function (row) { state.overviewByCat[row.category] = row; });
    });
  }
  function loadExchangeRate() {
    return api("/api/exchange-rate/").then(function (r) { state.exRate = r; });
  }
  function loadKeywordsAll() {
    return api("/api/keywords-manage/").then(function (list) {
      state.kwAll = list || [];
      state.kwByName = {};
      state.kwAll.forEach(function (kw) { state.kwByName[kw.name] = kw; });
    });
  }

  function loadHome() {
    document.getElementById("greetingEyebrow").textContent = greeting();
    renderHomeCatRow();
    updateBellDot();
    var work = [];
    if (!Object.keys(state.overviewByCat).length) work.push(loadCategoryOverview());
    if (!state.exRate) work.push(loadExchangeRate());
    if (!state.kwAll.length) work.push(loadKeywordsAll());
    Promise.all(work).then(function () {
      renderOverviewTiles();
      renderRateBadge();
    });
    api("/api/dashboard-stats/?category=" + encodeURIComponent(state.category)).then(function (data) {
      var summaryByName = {};
      (data.summary || []).forEach(function (row) {
        summaryByName[row.keyword_name] = summaryByName[row.keyword_name] || [];
        summaryByName[row.keyword_name].push(row);
      });
      state.homeKeywords = (data.keywords || []).map(function (kw) {
        var hist = (summaryByName[kw.name] || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
        if (hist.length >= 2) {
          var prev = hist[hist.length - 2].avg_price, cur = hist[hist.length - 1].avg_price;
          kw._changePct = prev ? (cur - prev) / prev * 100 : null;
        } else kw._changePct = null;
        return kw;
      });
      renderHomeCatRow();
      renderProductList();
    });
  }
  document.getElementById("homeSearchBar").addEventListener("click", function () { showTab("search"); });
  document.getElementById("homeManageLink").addEventListener("click", openCategoryList);
  document.getElementById("overviewSeeAllBtn").addEventListener("click", openCategorySheet);

  // ── Search (Rakuten-only live search) ───────────────────────────────────
  var searchTimer = null;
  var searchInput = document.getElementById("searchInput");
  searchInput.addEventListener("input", function () {
    clearTimeout(searchTimer);
    var q = searchInput.value.trim();
    renderTrackedMatches(q);
    if (!q) { renderSearchResults([], ""); return; }
    searchTimer = setTimeout(function () { runSearch(q); }, 400);
  });
  function renderTrackedMatches(q) {
    var wrap = document.getElementById("searchTrackedWrap");
    var list = document.getElementById("searchTrackedList");
    if (!q) { wrap.hidden = true; list.innerHTML = ""; return; }
    var matches = state.kwAll.filter(function (kw) { return kw.name.toLowerCase().indexOf(q.toLowerCase()) !== -1; });
    if (!matches.length) { wrap.hidden = true; return; }
    wrap.hidden = false;
    list.innerHTML = matches.map(function (kw) {
      return '<div class="result-row" style="cursor:pointer" data-name="' + escHtml(kw.name) + '"><span class="name">📍 ' + escHtml(kw.name) + " · " + catLabel(kw.category) + "</span><span class=\"price\">查看详情 →</span></div>";
    }).join("");
    list.querySelectorAll("[data-name]").forEach(function (row) {
      row.addEventListener("click", function () { openDetail(row.getAttribute("data-name")); });
    });
  }
  function runSearch(q) {
    document.getElementById("searchEmpty").textContent = "搜索中…";
    document.getElementById("searchEmpty").hidden = false;
    api("/api/search/?q=" + encodeURIComponent(q)).then(function (data) {
      renderSearchResults(data.results || [], q);
    }).catch(function () {
      document.getElementById("searchEmpty").textContent = "搜索失败，请重试";
    });
  }
  function renderSearchResults(results, q) {
    var wrap = document.getElementById("searchResults");
    var empty = document.getElementById("searchEmpty");
    document.getElementById("searchResultCount").textContent = results.length ? results.length + " 条" : "";
    if (!q) { wrap.innerHTML = ""; empty.hidden = false; empty.textContent = "输入关键词，实时查询日本 Rakuten 价格"; return; }
    if (!results.length) { wrap.innerHTML = ""; empty.hidden = false; empty.textContent = "没有找到相关商品"; return; }
    empty.hidden = true;
    wrap.innerHTML = results.slice(0, 40).map(function (r) {
      return '<a class="result-row" href="' + escHtml(r.url) + '" target="_blank" rel="noopener"><span class="name">' + escHtml(r.name) + '</span><span class="price">' + fmtJPY(r.price) + "</span></a>";
    }).join("");
  }

  // ── Detail screen ────────────────────────────────────────────────────────
  var detailChart = null;
  Chart.defaults.color = "#94A3B8";
  Chart.defaults.borderColor = "rgba(148,163,184,.10)";
  Chart.defaults.font.family = "Inter, sans-serif";

  function openDetail(name) {
    state.detailName = name;
    var kw = state.kwByName[name] || {};
    document.getElementById("detailArt").src = catImg(kw.category || state.category);
    document.getElementById("detailName").textContent = name;
    document.getElementById("detailPrice").textContent = "--";
    document.getElementById("detailPct").textContent = "--";
    var guideLine = document.getElementById("detailGuideLine");
    if (kw.guide_price != null) { guideLine.hidden = false; guideLine.textContent = "个人指导价 " + fmtJPY(kw.guide_price); }
    else guideLine.hidden = true;
    state.detailDays = 30;
    document.querySelectorAll("#detailRangeTabs button").forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-days") === "30"); });
    openOverlay("detail");
    api("/api/daily-stats/?keyword=" + encodeURIComponent(name)).then(function (data) {
      state.detailDaily = data.daily || [];
      applyDetailRange();
      checkAlertsForKeyword(name, currentLatestPrice());
    });
  }

  function currentLatestPrice() {
    if (!state.detailDaily.length) return null;
    return state.detailDaily[state.detailDaily.length - 1].low_price;
  }

  function applyDetailRange() {
    var daily = state.detailDays > 0 ? state.detailDaily.slice(-state.detailDays) : state.detailDaily;
    renderDetailChart(daily);
    if (state.detailDaily.length) {
      var last = state.detailDaily[state.detailDaily.length - 1];
      document.getElementById("detailPrice").textContent = fmtJPY(last.low_price);
      if (state.detailDaily.length >= 2) {
        var prev = state.detailDaily[state.detailDaily.length - 2];
        var pct = prev.avg_price ? (last.avg_price - prev.avg_price) / prev.avg_price * 100 : null;
        var b = pctBadge(pct);
        var pctEl = document.getElementById("detailPct");
        pctEl.textContent = b.text; pctEl.className = "pct " + (pct < 0 ? "good" : pct > 0 ? "bad" : "");
      } else {
        document.getElementById("detailPct").textContent = "--";
      }
      var monthLine = document.getElementById("detailMonthLine");
      if (state.detailDaily.length >= 2) {
        var monthAgoIdx = Math.max(0, state.detailDaily.length - 31);
        var monthAgo = state.detailDaily[monthAgoIdx];
        if (monthAgoIdx > 0 || state.detailDaily.length > 5) {
          var diff = last.low_price - monthAgo.low_price;
          monthLine.hidden = false;
          monthLine.textContent = "较" + monthAgo.date + " " + (diff > 0 ? "+" : diff < 0 ? "-" : "") + "¥" + Math.abs(diff).toLocaleString();
        } else monthLine.hidden = true;
      } else monthLine.hidden = true;
    }
  }

  function renderDetailChart(daily) {
    var el = document.getElementById("detailChart");
    if (!daily.length) { if (detailChart) { detailChart.destroy(); detailChart = null; } return; }
    var cfg = {
      type: "line",
      data: {
        labels: daily.map(function (d) { return d.date; }),
        datasets: [
          { label: "最高价", data: daily.map(function (d) { return d.high_price; }), borderColor: "#A78BFA", borderDash: [4, 3], tension: .35, pointRadius: 0, fill: false },
          { label: "平均价", data: daily.map(function (d) { return d.avg_price; }), borderColor: "#6EA8FE", tension: .35, pointRadius: 0, fill: false },
          { label: "最低价", data: daily.map(function (d) { return d.low_price; }), borderColor: "#5EEAD4", tension: .35, pointRadius: 0, fill: true, backgroundColor: "rgba(94,234,212,0.08)" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: "#131A2A", titleColor: "#F8FAFC", bodyColor: "#94A3B8", padding: 12, cornerRadius: 10 } },
        scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 5 } }, y: { grid: { color: "rgba(148,163,184,.09)" } } },
      },
    };
    if (detailChart) {
      detailChart.data = cfg.data; detailChart.update();
    } else detailChart = new Chart(el, cfg);
  }
  document.querySelectorAll("#detailRangeTabs button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.detailDays = parseInt(btn.getAttribute("data-days"), 10);
      document.querySelectorAll("#detailRangeTabs button").forEach(function (b) { b.classList.toggle("active", b === btn); });
      applyDetailRange();
    });
  });
  document.getElementById("detailChannelsBtn").addEventListener("click", function () { openChannels(state.detailName); });
  document.getElementById("detailAlertBtn").addEventListener("click", function () { openAlertSheet(state.detailName, currentLatestPrice()); });
  document.getElementById("detailShareBtn").addEventListener("click", function () {
    var url = location.origin + location.pathname;
    var text = state.detailName + " " + fmtJPY(currentLatestPrice()) + " · HARDPRICE";
    if (navigator.share) {
      navigator.share({ title: "HARDPRICE", text: text, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text + " " + url).then(function () { toast("已复制到剪贴板"); });
    } else toast(text);
  });

  // ── Channels screen (Rakuten + JD, real data only) ──────────────────────
  function openChannels(name) {
    state.channelsName = name;
    document.getElementById("channelsTitle").textContent = name + " · 购买渠道";
    openOverlay("channels");
    var kw = state.kwByName[name] || {};
    Promise.all([
      api("/api/daily-stats/?keyword=" + encodeURIComponent(name)),
      state.exRate ? Promise.resolve(state.exRate) : loadExchangeRate().then(function () { return state.exRate; }),
    ]).then(function (results) {
      var daily = results[0].daily || [];
      var rate = state.exRate;
      document.getElementById("channelsUpdatedAt").textContent = rate ? new Date(rate.updated_at).toLocaleString() : "--";
      var last = daily.length ? daily[daily.length - 1] : null;
      var rows = [];
      if (last) {
        rows.push({ site: "Rakuten", badge: "R", color: "#bf0000", price: last.low_price, sub: "日本 · " + last.date, url: last.min_price_url });
      }
      if (kw.jd_price_cny != null && rate) {
        var jpy = kw.jd_price_cny * rate.cny_to_jpy;
        rows.push({
          site: "京东 JD.com", badge: "京", color: "#e2231a", price: jpy,
          sub: "¥" + kw.jd_price_cny + " CNY · 汇率 1CNY≈¥" + rate.cny_to_jpy.toFixed(2) + " JPY（人工维护）" + (rate.stale ? "（汇率为参考值）" : ""),
          url: null,
        });
      }
      if (!rows.length) {
        document.getElementById("channelRows").innerHTML = '<p class="search-empty">暂无渠道数据。可在"关注"页为该关键词填写京东参考价，或先执行一次采集。</p>';
      } else {
        var minPrice = Math.min.apply(null, rows.map(function (r) { return r.price; }));
        document.getElementById("channelRows").innerHTML = rows.map(function (r) {
          var isBest = r.price === minPrice && rows.length > 1;
          return '<div class="channel-row' + (isBest ? " best" : "") + '">' +
            '<span class="badge" style="background:' + r.color + '">' + r.badge + '</span>' +
            '<div class="info"><p class="name">' + r.site + (isBest ? '<span class="best-tag">最安值</span>' : "") + '</p><p class="sub">' + r.sub + '</p></div>' +
            '<span class="price">' + fmtJPY(r.price) + '</span>' +
            (r.url ? '<a class="go-btn" href="' + escHtml(r.url) + '" target="_blank" rel="noopener">去看看</a>' : '<span class="go-btn" style="opacity:.5">仅参考</span>') +
            "</div>";
        }).join("");
      }
      var histRows = daily.slice().reverse().slice(0, 20);
      document.getElementById("historyList").innerHTML = histRows.length ? histRows.map(function (d) {
        return '<div class="history-row"><span class="date">' + d.date + '</span><span>最低 ' + fmtJPY(d.low_price) + ' · 平均 ' + fmtJPY(d.avg_price) + '</span></div>';
      }).join("") : '<p class="search-empty">暂无历史记录</p>';
    });
  }

  // ── Alert sheet (local/browser-only reminders) ──────────────────────────
  var alertBackdrop = document.getElementById("alertBackdrop");
  var alertSheet = document.getElementById("alertSheet");
  function getAlerts() { try { return JSON.parse(localStorage.getItem("hp-alerts") || "{}"); } catch (e) { return {}; } }
  function setAlerts(a) { try { localStorage.setItem("hp-alerts", JSON.stringify(a)); } catch (e) {} }

  function openAlertSheet(name, currentPrice) {
    state.alertName = name;
    state.alertCurrentPrice = currentPrice;
    state.alertDir = "below";
    document.getElementById("alertKwName").textContent = name;
    document.getElementById("alertCurrentPrice").textContent = fmtJPY(currentPrice);
    document.querySelectorAll(".alert-toggle button").forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-dir") === "below"); });
    var sliderMax = Math.max(500000, (currentPrice || 200000) * 2);
    var target = currentPrice ? Math.round(currentPrice * 0.9 / 100) * 100 : 100000;
    document.getElementById("alertTargetPrice").value = target;
    document.getElementById("alertTargetSlider").max = sliderMax;
    document.getElementById("alertTargetSlider").value = target;
    document.getElementById("alertSliderMin").textContent = "0";
    document.getElementById("alertSliderMax").textContent = sliderMax.toLocaleString();
    document.querySelectorAll("#alertQuickPct button").forEach(function (b) { b.classList.toggle("active", b.getAttribute("data-pct") === "0"); });
    var pushToggle = document.getElementById("alertPushToggle");
    pushToggle.checked = window.Notification && Notification.permission === "granted";
    renderAlertList();
    alertBackdrop.hidden = false; alertSheet.hidden = false;
  }
  function closeAlertSheet() { alertBackdrop.hidden = true; alertSheet.hidden = true; }
  alertBackdrop.addEventListener("click", closeAlertSheet);
  document.getElementById("alertCloseBtn").addEventListener("click", closeAlertSheet);
  document.querySelectorAll(".alert-toggle button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.alertDir = btn.getAttribute("data-dir");
      document.querySelectorAll(".alert-toggle button").forEach(function (b) { b.classList.toggle("active", b === btn); });
    });
  });
  var alertPriceInput = document.getElementById("alertTargetPrice");
  var alertSlider = document.getElementById("alertTargetSlider");
  function clearAlertQuickPct() { document.querySelectorAll("#alertQuickPct button").forEach(function (b) { b.classList.remove("active"); }); }
  alertPriceInput.addEventListener("input", function () { alertSlider.value = alertPriceInput.value; clearAlertQuickPct(); document.querySelector('#alertQuickPct [data-pct="0"]').classList.add("active"); });
  alertSlider.addEventListener("input", function () { alertPriceInput.value = alertSlider.value; clearAlertQuickPct(); document.querySelector('#alertQuickPct [data-pct="0"]').classList.add("active"); });
  document.querySelectorAll("#alertQuickPct button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      clearAlertQuickPct();
      btn.classList.add("active");
      var pct = parseInt(btn.getAttribute("data-pct"), 10);
      if (pct > 0 && state.alertCurrentPrice) {
        var target = Math.round(state.alertCurrentPrice * (1 - pct / 100) / 100) * 100;
        alertPriceInput.value = target;
        alertSlider.value = target;
      }
    });
  });
  document.getElementById("alertPushToggle").addEventListener("change", function (e) {
    if (e.target.checked && window.Notification && Notification.permission === "default") {
      Notification.requestPermission().then(function (perm) { e.target.checked = perm === "granted"; });
    }
  });

  function renderAlertList() {
    var alerts = getAlerts()[state.alertName] || [];
    var el = document.getElementById("alertList");
    if (!alerts.length) { el.innerHTML = ""; return; }
    el.innerHTML = '<div class="section-title" style="padding:14px 0 4px"><h2 style="font-size:13px">已设置的提醒</h2></div>' +
      alerts.map(function (a, i) {
        return '<div class="alert-item"><span>当价格' + (a.dir === "below" ? "低于" : "高于") + " " + fmtJPY(a.target) + '</span><button data-i="' + i + '">删除</button></div>';
      }).join("");
    el.querySelectorAll("[data-i]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var all = getAlerts();
        all[state.alertName].splice(parseInt(btn.getAttribute("data-i"), 10), 1);
        if (!all[state.alertName].length) delete all[state.alertName];
        setAlerts(all); renderAlertList();
      });
    });
  }
  document.getElementById("alertCreateBtn").addEventListener("click", function () {
    var target = parseFloat(alertPriceInput.value);
    if (!target || target <= 0) { toast("请输入有效的目标价格"); return; }
    var all = getAlerts();
    all[state.alertName] = all[state.alertName] || [];
    all[state.alertName].push({ dir: state.alertDir, target: target });
    setAlerts(all);
    if (window.Notification && Notification.permission === "default") Notification.requestPermission();
    renderAlertList();
    updateBellDot();
    toast("已创建浏览器内提醒");
  });

  function checkAlertsForKeyword(name, price) {
    if (price == null) return;
    var all = getAlerts();
    var alerts = all[name];
    if (!alerts || !alerts.length) return;
    var remaining = [];
    alerts.forEach(function (a) {
      var hit = a.dir === "below" ? price <= a.target : price >= a.target;
      if (hit) {
        var msg = name + " 当前 " + fmtJPY(price) + "，已" + (a.dir === "below" ? "低于" : "高于") + fmtJPY(a.target);
        toast("🔔 " + msg);
        if (window.Notification && Notification.permission === "granted") {
          try { new Notification("HARDPRICE 价格提醒", { body: msg }); } catch (e) {}
        }
      } else remaining.push(a);
    });
    if (remaining.length !== alerts.length) {
      if (remaining.length) all[name] = remaining; else delete all[name];
      setAlerts(all);
      updateBellDot();
    }
  }

  // ── Notification bell (lists every local alert across keywords) ─────────
  var notifBackdrop = document.getElementById("notifBackdrop");
  var notifSheet = document.getElementById("notifSheet");
  function updateBellDot() {
    var all = getAlerts();
    var has = Object.keys(all).some(function (k) { return all[k] && all[k].length; });
    document.querySelectorAll(".bell-btn").forEach(function (btn) { btn.classList.toggle("has-alerts", has); });
  }
  var updateWatchBellDot = updateBellDot;
  function renderNotifSheet() {
    var all = getAlerts();
    var names = Object.keys(all).filter(function (k) { return all[k] && all[k].length; });
    var list = document.getElementById("notifItemList");
    if (!names.length) { list.innerHTML = '<p class="notif-empty">还没有设置任何价格提醒</p>'; return; }
    var rows = [];
    names.forEach(function (name) {
      all[name].forEach(function (a, i) {
        rows.push({ name: name, dir: a.dir, target: a.target, i: i });
      });
    });
    list.innerHTML = rows.map(function (r) {
      return '<div class="notif-item"><div><p class="kw">' + escHtml(r.name) + '</p><p class="cond">当价格' + (r.dir === "below" ? "低于" : "高于") + " " + fmtJPY(r.target) + '</p></div>' +
        '<button data-name="' + escHtml(r.name) + '" data-i="' + r.i + '">删除</button></div>';
    }).join("");
    list.querySelectorAll("button[data-name]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var all2 = getAlerts();
        var n = btn.getAttribute("data-name"), i = parseInt(btn.getAttribute("data-i"), 10);
        if (all2[n]) {
          all2[n].splice(i, 1);
          if (!all2[n].length) delete all2[n];
          setAlerts(all2);
        }
        renderNotifSheet();
        updateBellDot();
      });
    });
  }
  function openNotifSheet() {
    renderNotifSheet();
    notifBackdrop.hidden = false; notifSheet.hidden = false;
  }
  document.querySelectorAll(".bell-btn").forEach(function (btn) { btn.addEventListener("click", openNotifSheet); });
  notifBackdrop.addEventListener("click", function () { notifBackdrop.hidden = true; notifSheet.hidden = true; });

  // ── Collect tab ──────────────────────────────────────────────────────────
  function loadCollectTab() {
    if (!state.kwAll.length) loadKeywordsAll().then(renderCollectChecklist);
    else renderCollectChecklist();
    pollCollectProgress(true);
  }
  function renderCollectChecklist() {
    var wrap = document.getElementById("collectChecklist");
    wrap.innerHTML = state.kwAll.map(function (kw) {
      return '<label><input type="checkbox" class="collect-cb" value="' + escHtml(kw.name) + '" checked> ' + escHtml(kw.name) + ' <span style="color:var(--hp-muted)">· ' + catLabel(kw.category) + "</span></label>";
    }).join("");
  }
  document.getElementById("collectSelectAll").addEventListener("change", function () {
    var checked = this.checked;
    document.querySelectorAll(".collect-cb").forEach(function (cb) { cb.checked = checked; });
  });
  document.getElementById("collectStartBtn").addEventListener("click", function () {
    var checked = [];
    document.querySelectorAll(".collect-cb:checked").forEach(function (cb) { checked.push(cb.value); });
    if (!checked.length) { toast("请至少勾选一个关键词"); return; }
    state.collectList = checked;
    fetch("/api/run-collect-daily-prices/", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ keywords: checked }),
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.ok) { toast("启动失败：" + (data.error || "unknown")); return; }
      pollCollectProgress(true);
    });
  });
  document.getElementById("collectStopBtn").addEventListener("click", function () {
    fetch("/api/cancel-collect/", { method: "POST" }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.ok) toast(data.error || "停止失败");
    });
  });
  document.getElementById("collectBgBtn").addEventListener("click", function () {
    toast("采集仍在后台进行，可切换到其他页面");
    showTab("home");
  });
  function setRing(current, total) {
    var pct = total ? current / total : 0;
    var circumference = 2 * Math.PI * 74;
    document.getElementById("collectRingFg").style.strokeDashoffset = String(circumference * (1 - pct));
    document.getElementById("collectRingLabel").textContent = current + "/" + total;
  }
  function renderCollectKwStatus(progress) {
    var list = state.collectList.length ? state.collectList : state.kwAll.map(function (k) { return k.name; });
    var doneCount = Math.max(0, (progress.current || 0) - (progress.running ? 1 : 0));
    var skippedNames = {};
    (progress.skipped || []).forEach(function (s) { skippedNames[s.keyword] = s.error; });
    document.getElementById("collectKwStatusList").innerHTML = list.map(function (name, i) {
      var cls = "pending", tag = "等待中";
      if (skippedNames[name] != null) { cls = "failed"; tag = "失败"; }
      else if (i < doneCount) { cls = "done"; tag = "已完成"; }
      else if (progress.running && name === progress.keyword) { cls = "running"; tag = "采集中"; }
      else if (!progress.running && progress.current >= progress.total && progress.total > 0) { cls = "done"; tag = "已完成"; }
      return '<div class="collect-kw-row ' + cls + '"><span class="status-dot"></span><span class="name">' + escHtml(name) + '</span><span class="tag">' + tag + "</span></div>";
    }).join("");
  }
  function pollCollectProgress(immediate) {
    clearInterval(state.collectTimer);
    function tick() {
      api("/api/collect-progress/").then(function (p) {
        setRing(p.current || 0, p.total || 0);
        renderCollectKwStatus(p);
        var startBtn = document.getElementById("collectStartBtn"), stopBtn = document.getElementById("collectStopBtn");
        var bgBtn = document.getElementById("collectBgBtn"), titleEl = document.getElementById("collectStatusTitle");
        if (p.running) {
          startBtn.hidden = true; stopBtn.hidden = false; bgBtn.hidden = false;
          titleEl.hidden = false;
          document.getElementById("collectStatusText").textContent = "实时获取 Rakuten 最新价格 · " + (p.current || 0) + "/" + (p.total || 0) + (p.keyword ? " · " + p.keyword : "");
        } else {
          startBtn.hidden = false; stopBtn.hidden = true; bgBtn.hidden = true;
          titleEl.hidden = true;
          clearInterval(state.collectTimer); state.collectTimer = null;
          if (p.total > 0) {
            var skipped = p.skipped || [];
            document.getElementById("collectStatusText").textContent = p.error === "已手动停止" ? "已手动停止" :
              (skipped.length ? "采集完成，跳过 " + skipped.length + " 个" : "采集完成 ✓");
            if (state.tab === "home") loadHome();
          }
        }
      });
    }
    if (immediate) tick();
    state.collectTimer = setInterval(tick, 1500);
  }

  // ── Watch tab (keyword management) ──────────────────────────────────────
  var manageCatFilter = "", manageSearchTerm = "";
  function loadWatchPriceData() {
    return api("/api/dashboard-stats/").then(function (data) {
      var summaryByName = {};
      (data.summary || []).forEach(function (row) {
        summaryByName[row.keyword_name] = summaryByName[row.keyword_name] || [];
        summaryByName[row.keyword_name].push(row);
      });
      state.watchPriceByName = {};
      (data.keywords || []).forEach(function (kw) {
        var hist = (summaryByName[kw.name] || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; });
        var pct = null;
        if (hist.length >= 2) {
          var prev = hist[hist.length - 2].avg_price, cur = hist[hist.length - 1].avg_price;
          pct = prev ? (cur - prev) / prev * 100 : null;
        }
        state.watchPriceByName[kw.name] = { latest_low_price: kw.latest_low_price, latest_date: kw.latest_date, changePct: pct };
      });
    });
  }
  function alertDirFor(name) {
    var alerts = getAlerts()[name];
    if (!alerts || !alerts.length) return null;
    return alerts[0].dir; // "below" or "above"
  }
  function trendGlyph(pct) {
    var down = pct != null && pct < 0;
    var up = pct != null && pct > 0;
    var color = down ? "#34D399" : up ? "#FB7185" : "#94A3B8";
    var path = down ? "M2 5l5 5 4-4 5 6" : up ? "M2 13l5-5 4 4 5-6" : "M2 9h14";
    return '<svg width="20" height="14" viewBox="0 0 20 14" fill="none" stroke="' + color + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="' + path + '"/></svg>';
  }
  function loadManageTab() {
    loadKeywordsAll().then(function () {
      renderManageList();
      loadWatchPriceData().then(renderManageList);
    });
    updateWatchBellDot();
  }
  function renderManageList() {
    var filtered = state.kwAll.filter(function (kw) {
      var matchCat = !manageCatFilter || kw.category === manageCatFilter;
      var matchSearch = !manageSearchTerm || kw.name.toLowerCase().indexOf(manageSearchTerm.toLowerCase()) !== -1;
      return matchCat && matchSearch;
    });
    document.querySelectorAll(".cat-filter-btn").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-cat") === manageCatFilter);
    });
    var empty = document.getElementById("manageEmpty");
    var list = document.getElementById("manageCardList");
    if (!filtered.length) { list.innerHTML = ""; empty.hidden = false; return; }
    empty.hidden = true;
    list.innerHTML = "";
    var priceData = state.watchPriceByName || {};
    filtered.forEach(function (kw) {
      var card = document.createElement("div");
      card.className = "swipe-card";
      var minPrice = kw.min_price != null ? fmtJPY(kw.min_price) : "--";
      var guidePrice = kw.guide_price != null ? fmtJPY(kw.guide_price) : null;
      var jdPrice = kw.jd_price_cny != null ? "京东 ¥" + kw.jd_price_cny : null;
      var pd = priceData[kw.name];
      var price = pd && pd.latest_low_price != null ? fmtJPY(pd.latest_low_price) : "--";
      var b = pd ? pctBadge(pd.changePct) : { text: "", cls: "" };
      var dir = alertDirFor(kw.name);
      card.innerHTML =
        '<div class="delete-panel"><button data-del="' + kw.id + '" data-name="' + escHtml(kw.name) + '">删除</button></div>' +
        '<div class="card-content">' +
        '<span class="thumb" style="width:44px;height:44px;border-radius:10px;background:var(--hp-surface);display:flex;align-items:center;justify-content:center;flex-shrink:0"><img src="' + catImg(kw.category) + '" style="width:75%"></span>' +
        '<div style="flex:1;min-width:0">' +
        '<p style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escHtml(kw.name) + '</p>' +
        '<div style="display:flex;align-items:center;gap:7px;margin-top:3px;font-size:12.5px"><b>' + price + '</b><span class="' + b.cls + '" style="font-size:11px;font-weight:700">' + b.text + '</span></div>' +
        '<div style="display:flex;gap:8px;margin-top:2px;font-size:10.5px;color:var(--hp-muted)"><span>' + catLabel(kw.category) + '</span><span>门槛 ' + minPrice + '</span>' +
        (guidePrice ? '<span style="color:var(--hp-amber)">指导 ' + guidePrice + "</span>" : "") +
        (jdPrice ? '<span style="color:#F87171">' + jdPrice + "</span>" : "") +
        "</div></div>" +
        (pd ? trendGlyph(pd.changePct) : "") +
        '<button type="button" class="mini-bell' + (dir ? " dir-" + dir : "") + '" data-alert="' + escHtml(kw.name) + '" title="价格提醒">' +
        '<svg width="18" height="18" fill="' + (dir ? "currentColor" : "none") + '" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg></button>' +
        '<button data-edit="' + kw.id + '" style="flex-shrink:0;color:var(--hp-blue);font-size:12px;font-weight:600;padding:6px 10px;border-radius:8px;background:rgba(110,168,254,.1)">编辑</button>' +
        "</div>";
      list.appendChild(card);
      initCardSwipe(card);
    });
    list.querySelectorAll("[data-edit]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var kw = state.kwAll.find(function (k) { return String(k.id) === btn.getAttribute("data-edit"); });
        if (kw) openKwModal(kw);
      });
    });
    list.querySelectorAll("[data-del]").forEach(function (btn) {
      btn.addEventListener("click", function () { confirmDeleteKeyword(btn.getAttribute("data-del"), btn.getAttribute("data-name")); });
    });
    list.querySelectorAll("[data-alert]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var name = btn.getAttribute("data-alert");
        var pd = priceData[name];
        openAlertSheet(name, pd ? pd.latest_low_price : null);
      });
    });
  }
  function initCardSwipe(card) {
    var content = card.querySelector(".card-content");
    var DELETE_W = 80, startX = 0, startY = 0, isDragging = false, isOpen = false;
    function snap(open) {
      isOpen = open;
      content.style.transition = "transform .25s cubic-bezier(.25,.46,.45,.94)";
      content.style.transform = "translateX(" + (open ? -DELETE_W : 0) + "px)";
    }
    content.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; startY = e.touches[0].clientY; isDragging = false; content.style.transition = "none"; }, { passive: true });
    content.addEventListener("touchmove", function (e) {
      var dx = e.touches[0].clientX - startX, dy = Math.abs(e.touches[0].clientY - startY);
      if (!isDragging && dy > Math.abs(dx)) return;
      isDragging = true;
      var base = isOpen ? -DELETE_W : 0;
      content.style.transform = "translateX(" + Math.min(0, Math.max(-DELETE_W, base + dx)) + "px)";
    }, { passive: true });
    content.addEventListener("touchend", function (e) {
      if (!isDragging) return;
      var dx = e.changedTouches[0].clientX - startX;
      snap(isOpen ? dx < 20 : dx < -30);
    }, { passive: true });
    document.addEventListener("touchstart", function (e) { if (isOpen && !card.contains(e.target)) snap(false); }, { passive: true });
  }
  function confirmDeleteKeyword(id, name) {
    if (!confirm("确定要删除关键词「" + name + "」吗？\n\n此操作会同步删除其所有历史价格数据，不可恢复。")) return;
    fetch("/api/keywords-manage/" + id + "/", { method: "DELETE" }).then(function (r) { return r.json(); }).then(function (data) {
      if (data.ok) { loadKeywordsAll().then(renderManageList); toast("已删除"); }
      else toast("删除失败：" + (data.error || "unknown"));
    });
  }
  document.querySelectorAll(".cat-filter-btn").forEach(function (btn) {
    btn.addEventListener("click", function () { manageCatFilter = btn.getAttribute("data-cat"); renderManageList(); });
  });
  document.getElementById("manageSearch").addEventListener("input", function () {
    manageSearchTerm = this.value.trim(); renderManageList();
  });

  // ── Keyword add/edit modal (shared) ──────────────────────────────────────
  var kwModal = document.getElementById("kwModal");
  function openKwModal(kw) {
    document.getElementById("kwModalTitle").textContent = kw ? "编辑关键词" : "添加关键词";
    document.getElementById("kwModalId").value = kw ? kw.id : "";
    document.getElementById("kwModalName").value = kw ? kw.name : "";
    document.getElementById("kwModalCategory").value = kw ? kw.category : (manageCatFilter || "custom");
    document.getElementById("kwModalMinPrice").value = kw ? kw.min_price : 20000;
    document.getElementById("kwModalGuidePrice").value = kw && kw.guide_price != null ? kw.guide_price : "";
    document.getElementById("kwModalJdPrice").value = kw && kw.jd_price_cny != null ? kw.jd_price_cny : "";
    document.getElementById("kwModalError").classList.add("hidden");
    kwModal.style.display = "block";
    document.getElementById("kwModalName").focus();
  }
  function closeKwModal() { kwModal.style.display = "none"; }
  document.getElementById("addKwBtn").addEventListener("click", function () { openKwModal(null); });
  document.getElementById("kwModalCloseBtn").addEventListener("click", closeKwModal);
  document.getElementById("kwModalCancelBtn").addEventListener("click", closeKwModal);
  kwModal.addEventListener("click", function (e) { if (e.target === kwModal) closeKwModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && kwModal.style.display !== "none") closeKwModal(); });
  document.getElementById("kwModalSaveBtn").addEventListener("click", function () {
    var id = document.getElementById("kwModalId").value;
    var name = document.getElementById("kwModalName").value.trim();
    var category = document.getElementById("kwModalCategory").value;
    var minPrice = parseInt(document.getElementById("kwModalMinPrice").value, 10) || 20000;
    var guideRaw = document.getElementById("kwModalGuidePrice").value.trim();
    var guidePrice = guideRaw !== "" ? parseInt(guideRaw, 10) || null : null;
    var jdRaw = document.getElementById("kwModalJdPrice").value.trim();
    var jdPrice = jdRaw !== "" ? parseFloat(jdRaw) : null;
    var errEl = document.getElementById("kwModalError");
    if (!name) { errEl.textContent = "请输入关键词名称"; errEl.classList.remove("hidden"); return; }
    var body = JSON.stringify({ name: name, category: category, min_price: minPrice, guide_price: guidePrice, jd_price_cny: jdPrice });
    var req = id ? fetch("/api/keywords-manage/" + id + "/", { method: "PUT", headers: { "Content-Type": "application/json" }, body: body })
                 : fetch("/api/keywords-manage/", { method: "POST", headers: { "Content-Type": "application/json" }, body: body });
    req.then(function (r) { return r.json(); }).then(function (data) {
      if (data.ok) { closeKwModal(); loadKeywordsAll().then(renderManageList); toast("已保存"); }
      else { errEl.textContent = data.error || "保存失败"; errEl.classList.remove("hidden"); }
    });
  });

  // ── Profile (我的) tab ───────────────────────────────────────────────────
  function renderProfileNotifStatus() {
    var el = document.getElementById("profileNotifStatus");
    if (!window.Notification) { el.textContent = "此浏览器不支持通知"; return; }
    var map = { granted: "已授权", denied: "已拒绝（需在浏览器设置里重新开启）", default: "未授权，点击开启" };
    el.textContent = map[Notification.permission] || Notification.permission;
  }
  function renderProfileRate() {
    var r = state.exRate;
    var label = document.getElementById("profileRateLabel");
    var updated = document.getElementById("profileRateUpdated");
    if (!r) { label.textContent = "汇率加载中…"; updated.textContent = ""; return; }
    label.textContent = "1 CNY ≈ ¥" + r.cny_to_jpy.toFixed(2) + " JPY";
    updated.textContent = (r.stale ? "⚠ 获取失败，使用参考值 · " : "已更新 · ") + new Date(r.updated_at).toLocaleString();
  }
  function loadProfileTab() {
    document.getElementById("profileKwCount").textContent = state.kwAll.length ? "共 " + state.kwAll.length + " 个关键词" : "加载中…";
    renderProfileNotifStatus();
    if (state.exRate) renderProfileRate();
    else loadExchangeRate().then(renderProfileRate);
    if (!state.kwAll.length) loadKeywordsAll().then(function () {
      document.getElementById("profileKwCount").textContent = "共 " + state.kwAll.length + " 个关键词";
    });
  }
  document.getElementById("profileRateRefreshBtn").addEventListener("click", function (e) {
    e.stopPropagation();
    document.getElementById("profileRateLabel").textContent = "刷新中…";
    loadExchangeRate().then(renderProfileRate);
  });
  document.getElementById("profileNotifRow").addEventListener("click", function () {
    if (!window.Notification) return;
    if (Notification.permission === "default") {
      Notification.requestPermission().then(renderProfileNotifStatus);
    } else {
      toast(Notification.permission === "granted" ? "通知权限已开启" : "请在浏览器设置中开启通知权限");
    }
  });
  document.getElementById("profileWatchRow").addEventListener("click", function () { showTab("watch"); });
  document.getElementById("profileAdminRow").addEventListener("click", function () { window.open("/admin/", "_blank"); });
  document.getElementById("profileClearRow").addEventListener("click", function () {
    if (!confirm("确定要清除本机保存的收藏和价格提醒吗？此操作不影响服务器上的关键词数据。")) return;
    try { localStorage.removeItem("hp-favs"); localStorage.removeItem("hp-alerts"); } catch (e) {}
    updateBellDot();
    toast("已清除本地收藏与提醒");
  });

  // ── Init ─────────────────────────────────────────────────────────────────
  loadKeywordsAll().then(function () { showTab("home"); });
})();

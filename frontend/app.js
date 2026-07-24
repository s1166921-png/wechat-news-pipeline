/**
 * app.js — 跨境热点通 前端控制器
 *
 * 3 步向导: 发现热点 → 生成文章 → 配图导出
 */
(function () {
  "use strict";

  // 容错：marked 未加载时用简易渲染
  if (typeof marked === "undefined") {
    window.marked = {
      parse: function (t) {
        if (!t) return "";
        return "<p>" + t.replace(/</g, "&lt;").replace(/\n\n/g, "</p><p>").replace(/\n/g, "<br>") + "</p>";
      },
    };
  }

  // ── State ─────────────────────────────────────────
  const state = {
    currentStep: 1,
    currentKeyword: "",   // 当前搜索关键词，用于刷新时保持主题
    newsItems: [],
    selectedNews: null,
    activeStyle: "b2b",
    articleContent: "",
    generatedImages: { cover: null, body: [] },
  };

  // ── DOM refs ─────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    searchInput: $("#search-input"),
    btnSearch: $("#btn-search"),
    btnRefreshTopics: $("#btn-refresh-topics"),
    engineSelector: $("#engine-selector"),
    hotTags: $("#hot-tags"),
    newsList: $("#news-list"),
    newsCount: $("#news-badge"),
    newsDetailPanel: $("#news-detail-panel"),
    btnToStep2: $("#btn-to-step2"),
    selectedTopicDisplay: $("#selected-topic-display"),
    btnGenerate: $("#btn-generate"),
    generateStatus: $("#generate-status"),
    articlePreview: $("#article-preview"),
    articleCharCount: $("#article-char-count"),
    previewActions: $("#preview-actions"),
    btnRegenerate: $("#btn-regenerate"),
    btnToStep3: $("#btn-to-step3"),
    btnGenCover: $("#btn-gen-cover"),
    btnGenImages: $("#btn-gen-images"),
    coverPreview: $("#cover-preview"),
    bodyImagesPreview: $("#body-images-preview"),
    btnExportDocx: $("#btn-export-docx"),
    btnExportMd: $("#btn-export-md"),
    btnExportHtml: $("#btn-export-html"),
    btnExportTxt: $("#btn-export-txt"),
    exportStatus: $("#export-status"),
    btnAutoPipeline: $("#btn-auto-pipeline"),
    pipelineProgress: $("#pipeline-progress"),
    statusMessage: $("#status-message"),
    healthDot: $("#health-dot"),
    healthText: $("#health-text"),
  };

  // ── Toast ────────────────────────────────────────
  function toast(msg, type) {
    type = type || "info";
    var t = document.createElement("div");
    t.className = "toast " + type;
    t.textContent = msg;
    document.body.appendChild(t);
    // Shorter for success, longer for errors so users can read them
    var duration = type === "error" ? 6000 : type === "success" ? 2500 : 3000;
    setTimeout(function () {
      t.remove();
    }, duration);
  }

  // ── Health Check ─────────────────────────────────
  async function checkHealth() {
    try {
      var r = await fetch("/api/health");
      var d = await r.json();
      dom.healthDot.className = "health-dot " + (d.status === "ok" ? "ok" : "err");
      dom.healthText.textContent = "服务器正常";
    } catch (e) {
      dom.healthDot.className = "health-dot err";
      dom.healthText.textContent = "连接失败";
    }
  }

  // ── Step Navigation ──────────────────────────────
  function goToStep(step) {
    state.currentStep = step;
    $$(".step").forEach(function (el) {
      var s = parseInt(el.dataset.step);
      el.classList.remove("active", "done");
      if (s === step) el.classList.add("active");
      else if (s < step) el.classList.add("done");
    });
    $$(".step-panel").forEach(function (el) {
      el.classList.remove("active");
    });
    $("#step" + step + "-panel").classList.add("active");

    if (step === 2) updateStep2UI();
    if (step === 3) updateStep3UI();
  }

  $$(".step").forEach(function (el) {
    el.addEventListener("click", function () {
      var s = parseInt(el.dataset.step);
      if (s <= state.currentStep || (s === 2 && state.selectedNews) ||
          (s === 3 && state.articleContent)) {
        goToStep(s);
      }
    });
  });

  dom.btnToStep2.addEventListener("click", function () {
    if (state.selectedNews) goToStep(2);
  });

  dom.btnToStep3.addEventListener("click", function () {
    if (state.articleContent) goToStep(3);
  });

  // ── Step 1: Hot Tags ─────────────────────────────
  async function loadHotTags() {
    try {
      var r = await fetch("/config/keywords.json");
      if (!r.ok) return;
      var cfg = await r.json();
      var tags = cfg.hot_tags || [];
      dom.hotTags.innerHTML = tags
        .map(function (t) {
          return '<span class="hot-tag" data-kw="' + t + '">' + t + "</span>";
        })
        .join("");
      $$(".hot-tag").forEach(function (el) {
        el.addEventListener("click", function () {
          dom.searchInput.value = el.dataset.kw;
          searchNews();
        });
      });
    } catch (e) {
      console.log("Hot tags load failed", e);
    }
  }

  // ── Engine Selection Helper ──────────────────────
  function getSelectedEngines() {
    var chips = $$("#engine-selector .engine-chip input:checked");
    if (!chips.length) return [];  // empty = all default (backward compatible)
    var engines = [];
    chips.forEach(function (cb) {
      engines.push(cb.closest(".engine-chip").dataset.engine);
    });
    return engines;
  }

  // ── Step 1: Search ───────────────────────────────
  async function searchNews() {
    var kw = dom.searchInput.value.trim();
    if (!kw) return toast("请输入关键词", "error");

    state.currentKeyword = kw;  // 记住关键词，刷新时保持主题

    dom.btnSearch.disabled = true;
    dom.btnSearch.innerHTML = '<span class="spinner"></span> 搜索中...';
    dom.newsList.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>搜索中...</p></div>';

    try {
      var engines = getSelectedEngines();
      var r = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: kw, max_results: 15, engines: engines }),
      });
      var d = await r.json();
      state.newsItems = d.results || [];
      renderNewsList();
      dom.newsCount.textContent = state.newsItems.length;
      toast("找到 " + state.newsItems.length + " 条相关资讯", "success");
    } catch (e) {
      toast("搜索失败: " + e.message, "error");
      dom.newsList.innerHTML = '<div class="empty-state"><p>搜索失败，请检查网络</p></div>';
    } finally {
      dom.btnSearch.disabled = false;
      dom.btnSearch.innerHTML = "🔍 搜索";
    }
  }

  async function refreshTopics() {
    dom.btnRefreshTopics.disabled = true;
    dom.btnRefreshTopics.innerHTML = '<span class="spinner"></span> 刷新中...';
    dom.newsList.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>拉取最新热点...</p></div>';

    try {
      var url, method, body;
      if (state.currentKeyword) {
        // 有搜索关键词 → 搜索同主题但换一批结果
        url = "/api/search";
        method = "POST";
        var engines = getSelectedEngines();
        body = JSON.stringify({ keyword: state.currentKeyword, max_results: 15, refresh: true, engines: engines });
      } else {
        // 无关键词 → 刷新默认热点
        url = "/api/news-topics/refresh?limit=15";
        method = "POST";
        body = null;
      }
      var r = await fetch(url, { method: method, headers: { "Content-Type": "application/json" }, body: body });
      var d = await r.json();
      state.newsItems = d.results || d.items || [];
      renderNewsList();
      dom.newsCount.textContent = state.newsItems.length;
      toast("刷新完成，共 " + state.newsItems.length + " 条", "success");
    } catch (e) {
      toast("刷新失败: " + e.message, "error");
    } finally {
      dom.btnRefreshTopics.disabled = false;
      dom.btnRefreshTopics.innerHTML = "🔄 刷新热点";
    }
  }

  dom.btnSearch.addEventListener("click", searchNews);
  dom.btnRefreshTopics.addEventListener("click", refreshTopics);
  dom.searchInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") searchNews();
  });

  // ── News List Rendering ──────────────────────────
  function renderNewsList() {
    if (!state.newsItems.length) {
      dom.newsList.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>暂无结果，换个关键词试试</p></div>';
      return;
    }
    dom.newsList.innerHTML = state.newsItems
      .map(function (item, i) {
        // Use backend score (0-55) instead of simplistic frontend calculation
        var score = item.score || 0;
        var scoreClass = score >= 45 ? "high" : score >= 30 ? "medium" : "";
        var summaryHtml = item.article_summary
          ? '<div class="news-item-summary">' + escHtml(item.article_summary) + "</div>"
          : "";
        return [
          '<div class="news-item" data-index="' + i + '">',
          '<div class="news-item-title">' + escHtml(item.title) + "</div>",
          summaryHtml,
          '<div class="news-item-meta">',
          '<span class="news-item-score ' + scoreClass + '">' + score + "分</span>",
          "<span>" + escHtml(item.source || "未知来源") + "</span>",
          item.date ? "<span>" + escHtml(item.date) + "</span>" : "",
          "</div></div>",
        ].join("");
      })
      .join("");

    // Click handler
    $$(".news-item").forEach(function (el) {
      el.addEventListener("click", function () {
        var idx = parseInt(el.dataset.index);
        state.selectedNews = state.newsItems[idx];
        renderNewsDetail();
        $$(".news-item").forEach(function (e) {
          e.classList.remove("selected");
        });
        el.classList.add("selected");
        dom.btnToStep2.disabled = false;
      });
    });
  }

  function escHtml(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function renderNewsDetail() {
    if (!state.selectedNews) return;
    var n = state.selectedNews;
    dom.newsDetailPanel.innerHTML = [
      '<div class="detail-title">' + escHtml(n.title) + "</div>",
      '<div class="detail-field"><label>来源</label><div class="value">' +
        escHtml(n.source || "未知") +
        " · " +
        escHtml(n.source_type || "") +
        "</div></div>",
      n.suggested_topic
        ? '<div class="topic-suggestion"><strong>✏️ AI 建议标题</strong><br>' +
          escHtml(n.suggested_topic) +
          "</div>"
        : "",
      n.key_angle
        ? '<div class="topic-suggestion"><strong>📐 切入角度</strong><br>' +
          escHtml(n.key_angle) +
          "</div>"
        : "",
      '<div class="detail-field"><label>原文链接</label><div class="value"><a href="' +
        escHtml(n.url) +
        '" target="_blank" rel="noopener">' +
        escHtml(n.url ? n.url.substring(0, 60) + "..." : "") +
        "</a></div></div>",
    ].join("");
  }

  // ── Step 2: Article Generation ───────────────────
  function updateStep2UI() {
    if (state.selectedNews) {
      dom.selectedTopicDisplay.innerHTML =
        "<strong>" +
        escHtml(state.selectedNews.suggested_topic || state.selectedNews.title) +
        "</strong>";
    }
  }

  // ── Preview Tab Switching ─────────────────────────
  var currentPreviewTab = "markdown";

  function switchPreviewTab(tab) {
    currentPreviewTab = tab;
    $$(".preview-tab").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    var articlePreview = $("#article-preview");
    var wechatPreview = $("#wechat-preview");
    if (tab === "wechat") {
      articlePreview.style.display = "none";
      wechatPreview.style.display = "flex";
      renderWechatPreview();
    } else {
      articlePreview.style.display = "";
      wechatPreview.style.display = "none";
    }
  }

  $$(".preview-tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      switchPreviewTab(btn.dataset.tab);
    });
  });

  // WeChat preview state
  var wechatState = {
    theme: "default",
    fontSize: 15,
    accentColor: "#CE0E19",
    cachedHtml: "",
  };

  async function renderWechatPreview() {
    if (!state.articleContent) { console.log("[renderWechatPreview] Skipped: no articleContent"); return; }
    console.log("[renderWechatPreview] Called, content length:", state.articleContent.length);
    var title = (state.selectedNews && (state.selectedNews.suggested_topic || state.selectedNews.title)) || "跨境电商资讯";
    $("#wechat-title").textContent = title;
    var now = new Date();
    $("#wechat-date").textContent = now.getFullYear() + "年" + (now.getMonth() + 1) + "月" + now.getDate() + "日";

    // Use buildImageMap() which respects user's position edits
    var imageMap = buildImageMap();

    try {
      console.log("[renderWechatPreview] Sending: fs=" + wechatState.fontSize + " accent=" + wechatState.accentColor + " theme=" + wechatState.theme);
      var r = await fetch("/api/to-wechat-html", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: state.articleContent,
          title: title,
          theme: wechatState.theme,
          font_size: wechatState.fontSize,
          accent_color: wechatState.accentColor,
          images: imageMap || undefined,
        }),
      });
      console.log("[renderWechatPreview] Response status:", r.status);
      var d = await r.json();
      console.log("[renderWechatPreview] Got HTML length:", d.html ? d.html.length : 0, "font_size:", d.font_size);
      if (d.html) {
        wechatState.cachedHtml = d.html;
        var bodyMatch = d.html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
        var bodyHtml = bodyMatch ? bodyMatch[1] : d.html;
        $("#wechat-body").innerHTML = bodyHtml;
      } else {
        $("#wechat-body").innerHTML = marked.parse(state.articleContent);
      }
    } catch (e) {
      console.error("[renderWechatPreview] Failed:", e);
      $("#wechat-body").innerHTML = marked.parse(state.articleContent);
    }

    // Refresh image position editor
    renderImagePositionEditor();
  }

  // ── Image Position Editor ───────────────────────
  // Tracks which images are placed at which positions in the article
  // imageSlots: [{url, label, type: "cover"|"body", index: N}, ...]
  // Order in array = order in article
  var imageSlots = [];

  function syncImageSlots() {
    // Track existing URLs for dedup
    var existingUrls = {};
    imageSlots.forEach(function(s) { existingUrls[s.url] = true; });

    // Update cover: keep existing if still valid, otherwise add new
    var hasCover = imageSlots.some(function(s) { return s.type === 'cover'; });
    if (!hasCover && state.generatedImages.cover && state.generatedImages.cover.image_urls && state.generatedImages.cover.image_urls.length) {
      var coverUrl = state.generatedImages.cover.image_urls[0];
      if (!existingUrls[coverUrl]) {
        imageSlots.unshift({
          url: coverUrl,
          label: '封面图',
          type: 'cover',
          index: -1
        });
      }
    }
    // Update existing cover URL if changed (e.g. regenerated)
    if (hasCover && state.generatedImages.cover && state.generatedImages.cover.image_urls && state.generatedImages.cover.image_urls.length) {
      var newCoverUrl = state.generatedImages.cover.image_urls[0];
      imageSlots.forEach(function(s) {
        if (s.type === 'cover') { s.url = newCoverUrl; }
      });
    }

    // Add new body images that aren't already in slots
    if (state.generatedImages.body && state.generatedImages.body.length) {
      state.generatedImages.body.forEach(function(img, i) {
        if (img && img.image_urls && img.image_urls.length) {
          var bodyUrl = img.image_urls[0];
          var alreadyExists = imageSlots.some(function(s) { return s.url === bodyUrl; });
          if (!alreadyExists) {
            imageSlots.push({
              url: bodyUrl,
              label: '配图 ' + (i + 1),
              type: 'body',
              index: i,
              section_excerpt: img.section_excerpt || '',
            });
          }
        }
      });
    }

    // Update existing body image URLs that match by index (regenerated)
    if (state.generatedImages.body && state.generatedImages.body.length) {
      imageSlots.forEach(function(slot) {
        if (slot.type === 'body' && slot.index >= 0 && slot.index < state.generatedImages.body.length) {
          var freshImg = state.generatedImages.body[slot.index];
          if (freshImg && freshImg.image_urls && freshImg.image_urls.length) {
            slot.url = freshImg.image_urls[0];
            if (freshImg.section_excerpt) {
              slot.section_excerpt = freshImg.section_excerpt;
            }
          }
        }
      });
    }
  }

  function buildImageMap() {
    // Convert imageSlots array to the image map format the backend expects.
    // Each body image includes section_excerpt so the backend can place
    // images next to their related paragraphs instead of arbitrary positions.
    var map = {};
    imageSlots.forEach(function(slot, position) {
      if (slot.type === 'cover') {
        map['cover'] = slot.url;
      } else {
        map[String(position)] = {
          url: slot.url,
          section_excerpt: slot.section_excerpt || '',
        };
      }
    });
    return Object.keys(map).length > 0 ? map : undefined;
  }

  function renderImagePositionEditor() {
    syncImageSlots();
    var editor = $("#image-position-editor");
    var list = $("#image-position-list");
    if (!editor || !list) return;

    if (imageSlots.length === 0) {
      editor.style.display = 'block';
      list.innerHTML = '<div class="no-images-hint">📸 文章暂无配图，切换到 <strong>Step 3 配图导出</strong> 生成封面和正文图片</div>';
      return;
    }

    editor.style.display = 'block';
    var html = '';
    imageSlots.forEach(function(slot, pos) {
      var isFirst = pos === 0;
      var isLast = pos === imageSlots.length - 1;
      var badgeText = slot.type === 'cover' ? '封面' : '位置 ' + (pos + 1);
      html += '<div class="image-position-row" data-pos="' + pos + '">' +
        '<img class="image-position-thumb" src="' + slot.url + '" alt="">' +
        '<span class="image-position-label">' + escHtml(slot.label) + '</span>' +
        '<span class="image-position-badge">' + badgeText + '</span>' +
        '<div class="image-position-actions">' +
          '<button class="btn-img-pos btn-img-up" data-pos="' + pos + '" title="上移" ' + (isFirst ? 'disabled' : '') + '>▲</button>' +
          '<button class="btn-img-pos btn-img-down" data-pos="' + pos + '" title="下移" ' + (isLast ? 'disabled' : '') + '>▼</button>' +
          '<button class="btn-img-pos btn-img-remove" data-pos="' + pos + '" title="从文章中移除">✕</button>' +
        '</div>' +
      '</div>';
    });
    list.innerHTML = html;

    // Attach event listeners
    list.querySelectorAll('.btn-img-up').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var pos = parseInt(btn.dataset.pos);
        if (pos > 0) {
          var tmp = imageSlots[pos];
          imageSlots[pos] = imageSlots[pos - 1];
          imageSlots[pos - 1] = tmp;
          renderImagePositionEditor();
          renderWechatPreview();
        }
      });
    });
    list.querySelectorAll('.btn-img-down').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var pos = parseInt(btn.dataset.pos);
        if (pos < imageSlots.length - 1) {
          var tmp = imageSlots[pos];
          imageSlots[pos] = imageSlots[pos + 1];
          imageSlots[pos + 1] = tmp;
          renderImagePositionEditor();
          renderWechatPreview();
        }
      });
    });
    list.querySelectorAll('.btn-img-remove').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var pos = parseInt(btn.dataset.pos);
        imageSlots.splice(pos, 1);
        renderImagePositionEditor();
        renderWechatPreview();
      });
    });
  }

  // ── WeChat toolbar event handlers ──
  function setupWechatToolbar() {
    var themeSelect = $("#wechat-theme");
    var fontSizeSlider = $("#wechat-fontsize");
    var accentColorInput = $("#wechat-accent");
    var btnCopy = $("#btn-copy-wechat");
    var btnExport = $("#btn-export-wechat");

    if (themeSelect) {
      themeSelect.addEventListener("change", function () {
        wechatState.theme = this.value;
        renderWechatPreview();
      });
    }
    if (fontSizeSlider) {
      fontSizeSlider.addEventListener("input", function () {
        wechatState.fontSize = parseInt(this.value);
        $("#wechat-fontsize-val").textContent = this.value + "px";
        console.log("[Toolbar] fontSize changed to:", wechatState.fontSize);
        // Debounced live preview while dragging slider
        clearTimeout(wechatState._fontDebounce);
        wechatState._fontDebounce = setTimeout(function () {
          renderWechatPreview();
        }, 300);
      });
      fontSizeSlider.addEventListener("change", function () {
        clearTimeout(wechatState._fontDebounce);
        console.log("[Toolbar] fontSize change final:", wechatState.fontSize);
        renderWechatPreview();
      });
    }
    if (accentColorInput) {
      accentColorInput.addEventListener("input", function () {
        wechatState.accentColor = this.value;
        console.log("[Toolbar] accentColor changed to:", wechatState.accentColor);
        // Debounced live preview while dragging color picker
        clearTimeout(wechatState._colorDebounce);
        wechatState._colorDebounce = setTimeout(function () {
          renderWechatPreview();
        }, 300);
      });
      accentColorInput.addEventListener("change", function () {
        clearTimeout(wechatState._colorDebounce);
        console.log("[Toolbar] accentColor change final:", wechatState.accentColor);
        renderWechatPreview();
      });
    }
    if (btnCopy) {
      btnCopy.addEventListener("click", function () {
        if (!wechatState.cachedHtml) return toast("请先生成微信预览", "error");
        navigator.clipboard.writeText(wechatState.cachedHtml).then(function () {
          toast("HTML 已复制到剪贴板，可直接粘贴到公众号编辑器", "success");
        }).catch(function () {
          var ta = document.createElement("textarea");
          ta.value = wechatState.cachedHtml; ta.style.position = "fixed"; ta.style.opacity = "0";
          document.body.appendChild(ta); ta.select();
          document.execCommand("copy"); document.body.removeChild(ta);
          toast("HTML 已复制到剪贴板", "success");
        });
      });
    }
    if (btnExport) {
      btnExport.addEventListener("click", function () {
        if (!wechatState.cachedHtml) return toast("请先生成微信预览", "error");
        var blob = new Blob([wechatState.cachedHtml], { type: "text/html;charset=utf-8" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        var safeName = ((state.selectedNews && state.selectedNews.suggested_topic) || "文章").replace(/[^\w一-鿿]/g, "_").substring(0, 40);
        a.href = url; a.download = safeName + "_微信排版.html";
        document.body.appendChild(a); a.click();
        document.body.removeChild(a); URL.revokeObjectURL(url);
        toast("排版文件已下载，可直接导入公众号", "success");
      });
    }
  }

  // Style toggle
  $$(".style-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      $$(".style-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      state.activeStyle = btn.dataset.style;
    });
  });

  dom.btnGenerate.addEventListener("click", generateArticle);
  dom.btnRegenerate.addEventListener("click", generateArticle);

  async function generateArticle() {
    if (!state.selectedNews) return toast("请先在 Step 1 选择新闻", "error");

    dom.btnGenerate.disabled = true;
    dom.generateStatus.innerHTML = '<span class="spinner"></span> AI 正在创作文章...';

    try {
      var r = await fetch("/api/generate-article", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          news_item: state.selectedNews,
          style: state.activeStyle,
          custom_angle: $("#custom-angle") ? $("#custom-angle").value.trim() : "",
        }),
      });
      var d = await r.json();
      if (d.error) {
        toast(d.error, "error");
        dom.generateStatus.textContent = "❌ " + d.error;
        return;
      }
      state.articleContent = d.content;
      dom.articlePreview.innerHTML = marked.parse(d.content);
      dom.articleCharCount.textContent = d.char_count + " 字";
      dom.previewActions.style.display = "flex";
      dom.generateStatus.innerHTML = "✅ 生成完成 · " + d.char_count + " 字 · 已保存到 " + d.filename;
      // Refresh WeChat preview if visible
      if (currentPreviewTab === "wechat") {
        renderWechatPreview();
      }
    } catch (e) {
      toast("生成失败: " + e.message, "error");
      dom.generateStatus.textContent = "❌ 生成失败";
    } finally {
      dom.btnGenerate.disabled = false;
    }
  }

  // ── Step 3: Image Generation ─────────────────────
  function updateStep3UI() {
    // (Pre-populated by generate calls)
  }

  dom.btnGenCover.addEventListener("click", function () { generateCover(); });
  dom.btnGenImages.addEventListener("click", function () { generateBodyImages(); });

  async function generateCover(customPrompt) {
    if (!state.articleContent && !customPrompt) return toast("请先生成文章", "error");
    dom.btnGenCover.disabled = true;
    dom.btnGenCover.innerHTML = '<span class="spinner"></span> 生成中...';
    dom.coverPreview.innerHTML =
      '<div class="empty-state small"><div class="spinner"></div><p>通义万相正在生成封面...</p></div>';

    try {
      var body = { article_content: state.articleContent };
      if (customPrompt) { body.custom_prompt = customPrompt; }
      // AbortController: 120s timeout
      var controller = new AbortController();
      var timeoutId = setTimeout(function () { controller.abort(); }, 120000);
      var r = await fetch("/api/generate-cover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      var d = await r.json();
      // Check for API-level error
      if (d.error) {
        dom.coverPreview.innerHTML =
          '<div class="empty-state small"><p>⚠️ ' + escHtml(d.error) + '</p><button class="btn btn-outline btn-sm" onclick="document.getElementById(\'btn-gen-cover\').click()">🔄 重试</button></div>';
        toast("封面: " + d.error, "error");
        return;
      }
      state.generatedImages.cover = d;
      if (d.image_urls && d.image_urls.length) {
        dom.coverPreview.innerHTML =
          '<img src="' + d.image_urls[0] + '" alt="封面图">';
      } else {
        dom.coverPreview.innerHTML =
          '<div class="empty-state small"><p>⚠️ 生成失败，请重试</p><button class="btn btn-outline btn-sm" onclick="document.getElementById(\'btn-gen-cover\').click()">🔄 重试</button></div>';
      }
      // Show prompt editor with current prompt
      var promptEditor = $("#cover-prompt-editor");
      var promptInput = $("#cover-prompt-input");
      var promptLabel = $("#cover-prompt-label");
      var btnEdit = $("#btn-cover-edit");
      var btnRegen = $("#btn-cover-regen");
      if (promptEditor) {
        promptEditor.style.display = "block";
        promptInput.value = d.prompt || "";
        promptInput.style.display = "none";
        promptLabel.textContent = "Prompt: " + (d.prompt || "");
        promptLabel.style.display = "";
        btnEdit.style.display = "";
        btnEdit.textContent = "✏️ 编辑 Prompt";
        btnRegen.style.display = "";
      }
      toast("封面图 " + (d.image_urls && d.image_urls.length ? "生成成功" : "生成失败"), d.image_urls && d.image_urls.length ? "success" : "error");
      // Refresh WeChat preview to show new images
      if (currentPreviewTab === "wechat") { renderWechatPreview(); }
    } catch (e) {
      toast("封面生成失败: " + e.message, "error");
    } finally {
      dom.btnGenCover.disabled = false;
      dom.btnGenCover.innerHTML = "生成封面";
    }
  }

  // Cover prompt edit/regenerate button handlers
  function setupCoverPromptEditor() {
    var btnEdit = $("#btn-cover-edit");
    var btnRegen = $("#btn-cover-regen");
    if (!btnEdit || !btnRegen) return;
    btnEdit.addEventListener("click", function () {
      var promptInput = $("#cover-prompt-input");
      var promptLabel = $("#cover-prompt-label");
      var isEditing = promptInput.style.display !== "none";
      if (isEditing) {
        promptInput.style.display = "none";
        promptLabel.style.display = "";
        promptLabel.textContent = "Prompt: " + promptInput.value;
        btnEdit.textContent = "✏️ 编辑 Prompt";
        btnRegen.style.display = "";
      } else {
        promptInput.style.display = "";
        promptLabel.style.display = "none";
        btnEdit.textContent = "✓ 确认";
        btnRegen.style.display = "";
      }
    });
    btnRegen.addEventListener("click", function () {
      var customPrompt = $("#cover-prompt-input").value.trim();
      if (!customPrompt) return toast("请输入 Prompt", "error");
      // Reset UI state
      $("#cover-prompt-input").style.display = "none";
      $("#cover-prompt-label").style.display = "";
      btnEdit.textContent = "✏️ 编辑 Prompt";
      btnRegen.style.display = "none";
      generateCover(customPrompt);
    });
  }

  async function generateBodyImages(customPrompts) {
    if (!state.articleContent && !customPrompts) return toast("请先生成文章", "error");
    dom.btnGenImages.disabled = true;
    dom.btnGenImages.innerHTML = '<span class="spinner"></span> 生成中...';
    dom.bodyImagesPreview.innerHTML =
      '<div class="empty-state small" style="grid-column:1/-1"><div class="spinner"></div><p>通义万相正在生成 3 张配图...</p></div>';

    try {
      var body = { article_content: state.articleContent, count: 3 };
      if (customPrompts) { body.custom_prompts = customPrompts; }
      var controller = new AbortController();
      var timeoutId = setTimeout(function () { controller.abort(); }, 180000);
      var r = await fetch("/api/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      var d = await r.json();
      if (d.error) {
        toast("配图: " + d.error, "error");
        dom.bodyImagesPreview.innerHTML =
          '<div class="empty-state small" style="grid-column:1/-1"><p>⚠️ ' + escHtml(d.error) + '</p></div>';
        return;
      }
      state.generatedImages.body = d.images || [];
      renderBodyImages(d.images || []);
      renderBodyPromptEditors(d.images || []);
      toast(d.total + " 张配图生成完成", "success");
      // Refresh WeChat preview to show new images
      if (currentPreviewTab === "wechat") { renderWechatPreview(); }
    } catch (e) {
      var errMsg = e.name === "AbortError" ? "请求超时（>180s），请重试" : e.message;
      toast("配图生成失败: " + errMsg, "error");
    } finally {
      dom.btnGenImages.disabled = false;
      dom.btnGenImages.innerHTML = "生成配图";
    }
  }

  function renderBodyImages(images) {
    var slots = "";
    for (var i = 0; i < 4; i++) {
      var img = images[i];
      if (img && img.image_urls && img.image_urls.length) {
        slots +=
          '<div class="image-slot"><img src="' +
          img.image_urls[0] +
          '" alt="配图 ' +
          (i + 1) +
          '"><button class="btn-regenerate" data-idx="' +
          i +
          '" title="用相同 Prompt 重新生成">🔄</button><button class="btn-edit-prompt" data-idx="' +
          i +
          '" title="编辑 Prompt">✏️</button></div>';
      } else {
        slots += '<div class="image-slot empty" data-slot="' + i + '"><span>图 ' + (i + 1) + "</span></div>";
      }
    }
    dom.bodyImagesPreview.innerHTML = slots;

    // Simple regenerate (same prompt)
    $$(".btn-regenerate").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var idx = parseInt(btn.dataset.idx);
        var imgData = state.generatedImages.body[idx];
        var currentPrompt = imgData ? imgData.prompt : "";
        if (!currentPrompt) return toast("无 Prompt，请先生成图片", "error");
        btn.disabled = true;
        btn.textContent = "...";
        try {
          var r = await fetch("/api/generate-image", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ custom_prompts: [currentPrompt], count: 1 }),
          });
          var d = await r.json();
          if (d.images && d.images.length) {
            d.images[0].index = idx;
            state.generatedImages.body[idx] = d.images[0];
            renderBodyImages(state.generatedImages.body);
            renderBodyPromptEditors(state.generatedImages.body);
            toast("图 " + (idx + 1) + " 重新生成成功", "success");
            // Refresh WeChat preview to reflect new image
            if (currentPreviewTab === "wechat") { renderWechatPreview(); }
          }
        } catch (e) {
          toast("重新生成失败: " + e.message, "error");
        }
        btn.disabled = false;
        btn.textContent = "🔄";
      });
    });

    // Edit prompt button
    $$(".btn-edit-prompt").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var idx = parseInt(btn.dataset.idx);
        var imgData = state.generatedImages.body[idx];
        if (!imgData) return;
        // Focus the corresponding prompt input
        var promptInput = $("#body-prompt-input-" + idx);
        if (promptInput) {
          promptInput.focus();
          promptInput.scrollIntoView({ behavior: "smooth" });
        }
      });
    });
  }

  function renderBodyPromptEditors(images) {
    var html = "";
    for (var i = 0; i < Math.min(images.length, 4); i++) {
      var img = images[i];
      if (!img) continue;
      html +=
        '<div class="body-prompt-row">' +
        '<span class="body-prompt-label">图' + (i + 1) + '</span>' +
        '<input type="text" id="body-prompt-input-' + i + '" class="input-textarea prompt-input" value="' + escHtml(img.prompt || "") + '" placeholder="编辑 Prompt...">' +
        '<button class="btn btn-primary btn-sm body-regen-btn" data-idx="' + i + '">🔄</button>' +
        '</div>';
    }
    var editor = $("#body-prompts-editor");
    if (editor) {
      editor.innerHTML = html;
      editor.style.display = images.length > 0 ? "block" : "none";
    }

    // Regenerate buttons in prompt editor
    $$(".body-regen-btn").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var idx = parseInt(btn.dataset.idx);
        var promptInput = $("#body-prompt-input-" + idx);
        var newPrompt = promptInput ? promptInput.value.trim() : "";
        if (!newPrompt) return toast("请输入 Prompt", "error");
        btn.disabled = true;
        btn.textContent = "...";
        try {
          var r = await fetch("/api/generate-image", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ custom_prompts: [newPrompt], count: 1 }),
          });
          var d = await r.json();
          if (d.images && d.images.length) {
            d.images[0].index = idx;
            state.generatedImages.body[idx] = d.images[0];
            renderBodyImages(state.generatedImages.body);
            renderBodyPromptEditors(state.generatedImages.body);
            toast("图 " + (idx + 1) + " 重新生成成功", "success");
            // Refresh WeChat preview to reflect new image
            if (currentPreviewTab === "wechat") { renderWechatPreview(); }
          } else {
            toast("图 " + (idx + 1) + " 生成失败", "error");
          }
        } catch (e) {
          toast("重新生成失败: " + e.message, "error");
        }
        btn.disabled = false;
        btn.textContent = "🔄";
      });
    });
  }

  // ── Export ────────────────────────────────────────
  dom.btnExportDocx.addEventListener("click", function () {
    exportDocx();
  });
  dom.btnExportMd.addEventListener("click", function () {
    exportArticle("md");
  });
  dom.btnExportHtml.addEventListener("click", function () {
    exportArticle("html");
  });
  dom.btnExportTxt.addEventListener("click", function () {
    exportArticle("txt");
  });

  async function exportDocx() {
    if (!state.articleContent) return toast("请先生成文章", "error");

    var title = (state.selectedNews && (state.selectedNews.suggested_topic || state.selectedNews.title)) || "跨境电商资讯";
    var imageMap = buildImageMap() || {};

    dom.exportStatus.innerHTML = '<span class="spinner"></span> 正在生成 DOCX...';
    try {
      var r = await fetch("/api/export-docx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: state.articleContent,
          title: title,
          images: imageMap,
        }),
      });
      if (!r.ok) {
        var err = await r.json();
        throw new Error(err.error || "导出失败");
      }
      var blob = await r.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      var safeName = title.replace(/[^\w一-鿿\-_]/g, "_").substring(0, 40);
      a.href = url;
      a.download = safeName + ".docx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      dom.exportStatus.innerHTML = "✅ DOCX 已下载 · 含文章 + " + Object.keys(imageMap).length + " 张图片";
      toast("DOCX 导出成功: " + safeName + ".docx", "success");
    } catch (e) {
      dom.exportStatus.innerHTML = "❌ 导出失败: " + e.message;
      toast("DOCX 导出失败: " + e.message, "error");
    }
  }

  async function exportArticle(format) {
    if (!state.articleContent) return toast("请先生成文章", "error");
    try {
      var r = await fetch("/api/export-article", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: state.articleContent, format: format }),
      });
      var d = await r.json();
      dom.exportStatus.innerHTML = "✅ 已导出: <code>" + d.saved_path + "</code> (" + d.char_count + " 字)";
      toast("导出成功: " + d.filename, "success");
    } catch (e) {
      toast("导出失败", "error");
    }
  }

  // ── Auto Pipeline ─────────────────────────────────
  dom.btnAutoPipeline.addEventListener("click", async function () {
    var kw = $("#pipeline-keyword").value.trim();
    var style = $("#pipeline-style").value;
    if (!kw) return toast("请输入关键词", "error");

    dom.btnAutoPipeline.disabled = true;
    dom.btnAutoPipeline.innerHTML = '<span class="spinner"></span> 全流程执行中...';
    dom.pipelineProgress.innerHTML = "";

    try {
      var r = await fetch("/api/auto-pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: kw, style: style, generate_images: false }),
      });
      var d = await r.json();

      // Render steps
      var stepsHtml = "";
      d.steps.forEach(function (s) {
        var icon = s.status === "done" ? "✅" : s.status === "skipped" ? "⏭️" : "⏳";
        stepsHtml +=
          '<div class="pipeline-step"><span>' +
          icon +
          "</span> " +
          s.name +
          (s.count ? " (" + s.count + " 条)" : "") +
          (s.chars ? " (" + s.chars + " 字)" : "") +
          "</div>";
      });
      dom.pipelineProgress.innerHTML = stepsHtml;

      if (d.article && d.article.content) {
        state.articleContent = d.article.content;
        dom.articlePreview.innerHTML = marked.parse(d.article.content);
        dom.articleCharCount.textContent = d.article.char_count + " 字";
        dom.previewActions.style.display = "flex";
        if (currentPreviewTab === "wechat") { renderWechatPreview(); }

        // Extract the best news item from search
        if (d.keyword) {
          dom.searchInput.value = d.keyword;
        }
        toast("全流程完成！已跳转到文章预览", "success");
        goToStep(2);
      }
    } catch (e) {
      toast("Pipeline 失败: " + e.message, "error");
      dom.pipelineProgress.innerHTML =
        '<span style="color:var(--brand-red)">❌ ' + e.message + "</span>";
    } finally {
      dom.btnAutoPipeline.disabled = false;
      dom.btnAutoPipeline.innerHTML = "⚡ 一键全流程";
    }
  });

  // ── Keyboard Shortcuts ───────────────────────────
  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case "1":
          e.preventDefault();
          goToStep(1);
          break;
        case "2":
          e.preventDefault();
          if (state.selectedNews) goToStep(2);
          break;
        case "3":
          e.preventDefault();
          if (state.articleContent) goToStep(3);
          break;
        case "Enter":
          e.preventDefault();
          if (state.currentStep === 2) generateArticle();
          break;
      }
    }
  });

  // ── Article Rewrite ─────────────────────────────────
  var rewriteStyle = "b2p";

  function formatImportMeta(d) {
    var methodMap = {
      raw_input: "粘贴全文",
      trafilatura: "智能抽取",
      curl_cffi: "浏览器指纹抽取",
      beautifulsoup: "页面解析",
      jina_reader: "Reader 回退",
    };
    var modeMap = {
      raw_content: "全文导入",
      wechat_sogou_redirect: "搜狗微信跳转",
      wechat_direct: "公众号链接",
      url: "普通链接",
    };
    var method = methodMap[d.extraction_method] || d.extraction_method || "未知方式";
    var mode = modeMap[d.import_mode] || d.import_mode || "文章导入";
    var source = d.source_url ? " · 来源已解析" : "";
    return mode + " · " + method + source;
  }

  // Toggle rewrite bar
  var rewriteBarBody = $("#rewrite-bar-body");
  var toggleBtn = $("#btn-toggle-rewrite");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      var collapsed = rewriteBarBody.classList.toggle("collapsed");
      toggleBtn.classList.toggle("collapsed", collapsed);
    });
  }

  // Toggle paste area
  var pasteArea = $("#rewrite-paste-area");
  var btnShowPaste = $("#btn-show-paste");
  if (btnShowPaste) {
    btnShowPaste.addEventListener("click", function () {
      var isVisible = pasteArea.style.display !== "none";
      pasteArea.style.display = isVisible ? "none" : "flex";
      btnShowPaste.textContent = isVisible ? "展开全文" : "收起全文";
    });
  }

  // Rewrite style selector
  $$(".rewrite-style-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      $$(".rewrite-style-btn").forEach(function (b) { b.classList.remove("active"); });
      btn.classList.add("active");
      rewriteStyle = btn.dataset.rewriteStyle;
    });
  });

  // Rewrite button
  var btnRewrite = $("#btn-rewrite");
  var btnRecompose = $("#btn-recompose");
  var rewriteTemperature = $("#rewrite-temperature");
  var rewriteTemperatureVal = $("#rewrite-temperature-val");
  var rewriteStatus = $("#rewrite-status");
  if (rewriteTemperature && rewriteTemperatureVal) {
    rewriteTemperature.addEventListener("input", function () {
      rewriteTemperatureVal.textContent = Number(rewriteTemperature.value).toFixed(2);
    });
  }

  async function runRewrite(rewriteMode) {
    var url = ($("#rewrite-url").value || "").trim();
    var rawContent = ($("#rewrite-raw-content") ? $("#rewrite-raw-content").value.trim() : "");
    var rawTitle = ($("#rewrite-raw-title") ? $("#rewrite-raw-title").value.trim() : "");
    var hasUsableRawContent = rawContent.length >= 300;
    var isRecompose = rewriteMode === "recompose";

    if (!url && !rawContent) {
      rewriteStatus.className = "rewrite-status error";
      rewriteStatus.textContent = "请粘贴公众号全文，或输入可访问的文章链接";
      return;
    }

    // Build request body
    var body = {
      style: rewriteStyle,
      theme: wechatState.theme,
      rewrite_mode: isRecompose ? "recompose" : "rewrite",
      temperature: isRecompose && rewriteTemperature ? Number(rewriteTemperature.value) : 0.35,
    };
    if (hasUsableRawContent) {
      body.raw_content = rawContent;
      if (rawTitle) body.original_title = rawTitle;
    } else if (url) {
      // Accept any URL — no longer restricted to WeChat only
      body.url = url;
    } else if (rawContent) {
      rewriteStatus.className = "rewrite-status error";
      rewriteStatus.textContent = "粘贴内容太短，请粘贴完整文章，或输入文章链接";
      return;
    }

    btnRewrite.disabled = true;
    if (btnRecompose) btnRecompose.disabled = true;
    rewriteStatus.className = "rewrite-status loading";
    rewriteStatus.innerHTML = rawContent
      ? '<span class="spinner"></span> 正在基于粘贴全文' + (isRecompose ? "重新编写..." : "改写...")
      : '<span class="spinner"></span> 正在尝试从链接提取正文...';

    try {
      var r = await fetch("/api/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if (d.error) {
        rewriteStatus.className = "rewrite-status error";
        rewriteStatus.textContent = d.error_hint || d.hint || d.error;
        // If URL fetch failed, auto-expand paste area and prompt
        if (!rawContent && (d.manual_import_recommended || d.error.includes("无法提取") || d.error.includes("反爬"))) {
          var pasteArea = $("#rewrite-paste-area");
          if (pasteArea && pasteArea.style.display === "none") {
            pasteArea.style.display = "flex";
            var showPasteBtn = $("#btn-show-paste");
            if (showPasteBtn) showPasteBtn.textContent = "收起全文";
          }
          var rawTextarea = $("#rewrite-raw-content");
          if (rawTextarea) {
            rawTextarea.placeholder = "请在这里粘贴文章全文（在浏览器中打开文章 → 全选复制 → 粘贴到这里）";
            rawTextarea.focus();
          }
          rewriteStatus.innerHTML = (d.error_hint || d.hint || "服务器无法直接访问该文章。") + "<br>请在上方粘贴全文后再次点击「改写文章」。";
        }
        return;
      }

      // Copy result to state (like generateArticle does)
      state.articleContent = d.rewritten_markdown;
      state.selectedNews = {
        title: d.original_title,
        suggested_topic: d.original_title,
        url: url || "",
        source: d.original_author || "微信公众号",
      };

      // Render markdown preview
      dom.articlePreview.innerHTML = marked.parse(d.rewritten_markdown);
      dom.articleCharCount.textContent = d.char_count + " 字 (改写自: " + d.original_char_count + " 字原文)";
      dom.previewActions.style.display = "flex";
      dom.generateStatus.innerHTML = "✅ " + (d.rewrite_mode === "recompose" ? "重新编写完成" : "改写完成") + " · " + d.style_label + " · " + d.char_count + " 字 · " + formatImportMeta(d);

      // Also cache WeChat HTML for preview
      if (d.rewritten_html) {
        wechatState.cachedHtml = d.rewritten_html;
      }

      var factGuardNote = "";
      var remainingFactWarnings = d.fact_warnings || [];
      var initialFactWarnings = d.fact_warnings_initial || [];
      if (remainingFactWarnings.length) {
        factGuardNote = " · 存在 " + remainingFactWarnings.length + " 个事实需人工复核";
      } else if (d.fact_guard_retry_count > 0) {
        factGuardNote = " · 已校验并移除 " + initialFactWarnings.length + " 个未支持事实";
      }

      // Switch to preview
      goToStep(2);
      if (currentPreviewTab === "wechat") {
        renderWechatPreview();
      }

      var rewriteTemperatureNote = d.rewrite_mode === "recompose" ? " · 自由度 " + Number(d.rewrite_temperature || 0).toFixed(2) : "";
      rewriteStatus.className = "rewrite-status success";
      rewriteStatus.textContent = "✅ " + (d.rewrite_mode === "recompose" ? "重新编写完成" : "改写完成") + "！原文 " + d.original_char_count + " 字 → 成文 " + d.char_count + " 字 (" + formatImportMeta(d) + ")" + rewriteTemperatureNote + factGuardNote;
    } catch (e) {
      rewriteStatus.className = "rewrite-status error";
      rewriteStatus.textContent = "❌ 改写失败: " + e.message;
      toast("改写失败: " + e.message, "error");
    } finally {
      btnRewrite.disabled = false;
      if (btnRecompose) btnRecompose.disabled = false;
    }
  }

  if (btnRewrite) {
    btnRewrite.addEventListener("click", function () { runRewrite("rewrite"); });
  }
  if (btnRecompose) {
    btnRecompose.addEventListener("click", function () { runRewrite("recompose"); });
  }

  // ── Init ──────────────────────────────────────────
  async function init() {
    checkHealth();
    loadHotTags();
    setupCoverPromptEditor();
    setupWechatToolbar();
    // Load initial topics
    try {
      var r = await fetch("/api/news-topics?limit=15");
      var d = await r.json();
      state.newsItems = d.items || [];
      renderNewsList();
      dom.newsCount.textContent = state.newsItems.length;
      dom.statusMessage.textContent =
        "🟢 就绪 · " + (d.cache_valid ? "缓存" : "实时") + " · " + d.sources.length + " 个来源";
    } catch (e) {
      console.log("Initial topics load failed", e);
    }

    // Periodic health check
    setInterval(checkHealth, 30000);
  }

  init();
})();

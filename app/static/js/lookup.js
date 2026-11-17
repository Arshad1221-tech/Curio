/* ==========================================================================
   Curio - "Find it online" metadata lookup on the add/edit item form.
   Calls /api/metadata/* (server-side proxy) and fills in the form fields.
   ========================================================================== */
(function () {
  "use strict";

  var panel = document.getElementById("lookup-panel");
  if (!panel || !window.Curio) { return; }

  var SOURCES = { book: "Google Books", movie: "TMDB", tv: "TMDB", song: "iTunes", album: "iTunes" };
  var SOURCE_KEYS = { book: "google_books", movie: "tmdb", tv: "tmdb", song: "itunes", album: "itunes" };
  var unavailable = (panel.getAttribute("data-unavailable") || "").split(",").filter(Boolean);

  var typeSelect = document.getElementById("media_type");
  var queryInput = document.getElementById("lookup-query");
  var searchButton = document.getElementById("lookup-button");
  var resultsBox = document.getElementById("lookup-results");
  var statusBox = document.getElementById("lookup-status");
  var sourceLabel = document.getElementById("lookup-source");
  var controls = document.getElementById("lookup-controls");

  function currentType() { return typeSelect ? typeSelect.value : "book"; }

  function setStatus(message, variant) {
    statusBox.textContent = message || "";
    statusBox.className = "small mb-2 " + (variant ? "text-" + variant : "text-muted");
  }

  function refreshForType() {
    var type = currentType();
    resultsBox.innerHTML = "";
    if (!SOURCES[type]) {
      sourceLabel.textContent = "Not available";
      controls.classList.add("d-none");
      setStatus("Online lookup isn't available for “Other” items — just fill in the form below.");
      return;
    }
    sourceLabel.textContent = SOURCES[type];
    if (unavailable.indexOf(type) !== -1) {
      controls.classList.add("d-none");
      setStatus("Movie and TV lookup needs a free TMDB API key. Add it to your .env file (see README), or enter the details manually.", "warning");
      return;
    }
    controls.classList.remove("d-none");
    setStatus("");
  }

  function setField(id, value) {
    var field = document.getElementById(id);
    if (!field || value === null || value === undefined) { return; }
    if (Array.isArray(value)) { value = value.join(", "); }
    if (String(value).trim() === "") { return; }
    field.value = value;
    field.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function fillForm(result) {
    setField("title", result.title);
    setField("creator", result.creator);
    setField("release_year", result.release_year);
    setField("description", result.description);
    setField("genres", result.genres);
    setField("image_url", result.image_url);
    setField("external_source", result.source);
    setField("external_id", result.external_id);
    setField("external_url", result.external_url);
    setField("keywords", result.keywords);
  }

  function buildResult(result) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "lookup-result";

    var cover = document.createElement("div");
    cover.className = "cover" + (result.media_type === "song" || result.media_type === "album" ? " cover--square" : "");
    cover.setAttribute("data-type", result.media_type);
    var placeholder = document.createElement("div");
    placeholder.className = "cover-placeholder";
    placeholder.innerHTML = '<i class="bi bi-image"></i>';
    cover.appendChild(placeholder);
    if (result.image_url) {
      var img = document.createElement("img");
      img.className = "cover-img";
      img.src = result.image_url;
      img.alt = "";
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      cover.appendChild(img);
    }

    var text = document.createElement("div");
    text.className = "min-w-0";
    var title = document.createElement("div");
    title.className = "fw-semibold text-truncate";
    title.textContent = result.title;
    var meta = document.createElement("div");
    meta.className = "small text-muted text-truncate";
    meta.textContent = [result.creator, result.release_year].filter(Boolean).join(" · ") || "Details available";
    var genres = document.createElement("div");
    genres.className = "small text-muted text-truncate";
    genres.textContent = (result.genres || []).slice(0, 3).join(", ");
    text.appendChild(title);
    text.appendChild(meta);
    if (genres.textContent) { text.appendChild(genres); }

    button.appendChild(cover);
    button.appendChild(text);
    button.addEventListener("click", function () { chooseResult(result, button); });
    return button;
  }

  async function chooseResult(result, button) {
    fillForm(result);
    resultsBox.querySelectorAll(".lookup-result").forEach(function (el) { el.classList.remove("border-primary"); });
    button.classList.add("border-primary");
    setStatus("Filled in from " + SOURCES[result.media_type] + ". Fetching extra details…");
    try {
      var url = "/api/metadata/details?type=" + encodeURIComponent(result.media_type) +
        "&source=" + encodeURIComponent(result.source) + "&id=" + encodeURIComponent(result.external_id);
      var detailed = await window.Curio.getJSON(url);
      fillForm(detailed);
      setStatus("Details filled in. Review them, then add your rating, tags and notes.", "success");
    } catch (error) {
      setStatus("Basic details filled in. Extra details were unavailable: " + error.message, "warning");
    }
  }

  async function runSearch() {
    var type = currentType();
    var query = queryInput.value.trim();
    if (query.length < 2) { setStatus("Type at least two characters to search.", "warning"); return; }
    if (SOURCE_KEYS[type] === undefined) { return; }
    resultsBox.innerHTML = "";
    searchButton.disabled = true;
    setStatus("Searching " + SOURCES[type] + "…");
    try {
      var data = await window.Curio.getJSON("/api/metadata/search?type=" + encodeURIComponent(type) + "&q=" + encodeURIComponent(query));
      if (!data.results.length) {
        setStatus("No matches found. Try different words, or enter the details manually.", "warning");
        return;
      }
      data.results.forEach(function (result) { resultsBox.appendChild(buildResult(result)); });
      setStatus(data.results.length + " result" + (data.results.length === 1 ? "" : "s") + " from " + SOURCES[type] + ". Choose one to fill in the form.");
    } catch (error) {
      setStatus(error.message, "danger");
    } finally {
      searchButton.disabled = false;
    }
  }

  searchButton.addEventListener("click", runSearch);
  queryInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") { event.preventDefault(); runSearch(); }  // don't submit the item form
  });
  if (typeSelect) { typeSelect.addEventListener("change", refreshForType); }

  var titleInput = document.getElementById("title");
  if (titleInput && !queryInput.value) { queryInput.value = titleInput.value; }
  refreshForType();
})();

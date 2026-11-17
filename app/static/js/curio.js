/* ==========================================================================
   Curio - shared front-end behaviour
   ========================================================================== */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  /** POST JSON with the CSRF header; resolves with parsed JSON or throws. */
  async function postJSON(url, body) {
    var response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRF-Token": csrfToken(),
      },
      body: JSON.stringify(body || {}),
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
    }
    return data;
  }

  /** GET JSON; resolves with parsed JSON or throws. */
  async function getJSON(url) {
    var response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "Request failed (" + response.status + ").");
    }
    return data;
  }

  /** Small Bootstrap toast for asynchronous feedback. */
  function showToast(message, variant) {
    var container = document.getElementById("toast-container");
    if (!container || !window.bootstrap) { return; }
    var toast = document.createElement("div");
    toast.className = "toast align-items-center border-0 text-bg-" + (variant || "dark");
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    var wrapper = document.createElement("div");
    wrapper.className = "d-flex";
    var body = document.createElement("div");
    body.className = "toast-body";
    body.textContent = message;
    var close = document.createElement("button");
    close.type = "button";
    close.className = "btn-close btn-close-white me-2 m-auto";
    close.setAttribute("data-bs-dismiss", "toast");
    close.setAttribute("aria-label", "Close");
    wrapper.appendChild(body);
    wrapper.appendChild(close);
    toast.appendChild(wrapper);
    container.appendChild(toast);
    var instance = new window.bootstrap.Toast(toast, { delay: 3200 });
    toast.addEventListener("hidden.bs.toast", function () { toast.remove(); });
    instance.show();
  }

  window.Curio = { csrfToken: csrfToken, postJSON: postJSON, getJSON: getJSON, showToast: showToast };

  // Confirmation prompt for destructive forms: <form data-confirm="Are you sure?">
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.matches && form.matches("form[data-confirm]")) {
      if (!window.confirm(form.getAttribute("data-confirm"))) { event.preventDefault(); }
    }
  });

  // Broken cover images fall back to the styled placeholder underneath.
  document.addEventListener("error", function (event) {
    var img = event.target;
    if (img && img.tagName === "IMG" && img.classList.contains("cover-img")) { img.remove(); }
  }, true);

  // Favourite toggles: <button data-favourite-toggle data-item-id="1">
  document.addEventListener("click", async function (event) {
    var button = event.target.closest("[data-favourite-toggle]");
    if (!button) { return; }
    event.preventDefault();
    button.disabled = true;
    try {
      var data = await postJSON("/api/items/" + button.getAttribute("data-item-id") + "/favourite");
      document.querySelectorAll('[data-favourite-toggle][data-item-id="' + data.id + '"]').forEach(function (btn) {
        btn.classList.toggle("is-active", data.is_favourite);
        btn.setAttribute("aria-pressed", data.is_favourite ? "true" : "false");
        btn.setAttribute("title", data.is_favourite ? "Remove from favourites" : "Add to favourites");
        var icon = btn.querySelector("i");
        if (icon) { icon.className = data.is_favourite ? "bi bi-heart-fill" : "bi bi-heart"; }
        var label = btn.querySelector("[data-favourite-label]");
        if (label) { label.textContent = data.is_favourite ? "Favourited" : "Add to favourites"; }
      });
      showToast(data.is_favourite ? "Added to favourites" : "Removed from favourites", "dark");
    } catch (error) {
      showToast(error.message, "danger");
    } finally {
      button.disabled = false;
    }
  });

  // Copy-to-clipboard buttons: <button data-copy="#input-id">
  document.addEventListener("click", async function (event) {
    var button = event.target.closest("[data-copy]");
    if (!button) { return; }
    var target = document.querySelector(button.getAttribute("data-copy"));
    if (!target) { return; }
    var text = target.value || target.textContent;
    try {
      await navigator.clipboard.writeText(text);
      showToast("Link copied to clipboard", "dark");
    } catch (error) {
      target.select && target.select();
      showToast("Press Ctrl+C to copy the link", "dark");
    }
  });

  // Auto-submit filter forms when a select or checkbox changes.
  document.addEventListener("change", function (event) {
    var field = event.target;
    var form = field.closest && field.closest("form[data-autosubmit]");
    if (form && (field.tagName === "SELECT" || field.type === "checkbox")) { form.requestSubmit ? form.requestSubmit() : form.submit(); }
  });

  // Live preview for image URL inputs: <input data-image-preview="#preview-img">
  function updatePreview(input) {
    var target = document.querySelector(input.getAttribute("data-image-preview"));
    if (!target) { return; }
    var url = input.value.trim();
    var valid = /^https?:\/\//i.test(url);
    target.classList.toggle("d-none", !valid);
    var img = target.querySelector("img");
    if (img && valid) { img.src = url; }
  }
  document.querySelectorAll("[data-image-preview]").forEach(function (input) {
    input.addEventListener("input", function () { updatePreview(input); });
    updatePreview(input);
  });

  // Client-side "clear rating" link for the star input.
  document.addEventListener("click", function (event) {
    var link = event.target.closest("[data-clear-rating]");
    if (!link) { return; }
    event.preventDefault();
    var group = document.querySelector(link.getAttribute("data-clear-rating"));
    if (!group) { return; }
    group.querySelectorAll("input[type=radio]").forEach(function (radio) { radio.checked = radio.value === ""; });
  });
})();

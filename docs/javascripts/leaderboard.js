// Renders docs/data/leaderboard.json (written by scripts/build_site_data.py)
// into the #sm-leaderboard element on the leaderboard page.
(function () {
  "use strict";

  const COLUMNS = [
    { key: "mean_score", label: "Mean score", kind: "score" },
    { key: "valid_pct", label: "Valid design", kind: "pct" },
    { key: "requirements_pct", label: "Requirements met", kind: "pct" },
    { key: "best_score", label: "Best", kind: "num" },
    { key: "runs", label: "Runs", kind: "int" },
    { key: "cost_usd", label: "Cost", kind: "usd" },
    { key: "p50_latency_s", label: "Median latency", kind: "sec" },
  ];

  const esc = (value) =>
    String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function fmt(value, kind) {
    if (value === null || value === undefined) return '<span class="sm-lb-na">–</span>';
    switch (kind) {
      case "pct": return `${value.toFixed(0)}%`;
      case "int": return String(value);
      case "usd": return value < 0.01 ? "<$0.01" : `$${value.toFixed(2)}`;
      case "sec": return `${value.toFixed(1)} s`;
      default: return value.toFixed(3);
    }
  }

  function modelCell(row) {
    const [base, variant] = row.model.split("__reasoning-");
    const chip = variant ? `<span class="sm-lb-chip">reasoning: ${esc(variant)}</span>` : "";
    const meta = [row.provider, row.source === "Manual" ? "manual runs" : null].filter(Boolean).join(" · ");
    return `<div class="sm-lb-model"><strong title="${esc(row.model_id)}">${esc(base)}</strong>${chip}</div>` +
      (meta ? `<div class="sm-lb-sub">${esc(meta)}</div>` : "");
  }

  function renderTable(task, state) {
    const rows = [...task.leaderboard];
    if (state.sort) {
      const { key, dir } = state.sort;
      rows.sort((a, b) => {
        const av = a[key], bv = b[key];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        return dir * (av - bv);
      });
    }
    const max = Math.max(1e-9, ...task.leaderboard.map((r) => r.mean_score || 0));
    const head = COLUMNS.map((c) => {
      const active = state.sort && state.sort.key === c.key;
      const arrow = active ? (state.sort.dir < 0 ? " ↓" : " ↑") : "";
      return `<th class="sm-lb-num"><button type="button" data-sort="${c.key}"${active ? ' aria-sort="' + (state.sort.dir < 0 ? "descending" : "ascending") + '"' : ""}>${c.label}${arrow}</button></th>`;
    }).join("");
    const body = rows.map((row, i) => {
      const cells = COLUMNS.map((c) => {
        if (c.kind === "score") {
          const width = row.mean_score ? (100 * row.mean_score) / max : 0;
          return `<td class="sm-lb-num"><span class="sm-lb-score"><span class="sm-lb-bar"><span style="width:${width.toFixed(1)}%"></span></span><span class="sm-lb-val">${fmt(row.mean_score, "num")}</span></span></td>`;
        }
        return `<td class="sm-lb-num">${fmt(row[c.key], c.kind)}</td>`;
      }).join("");
      return `<tr><td class="sm-lb-rank">${state.sort ? "" : i + 1}</td><td>${modelCell(row)}</td>${cells}</tr>`;
    }).join("");
    return `<div class="sm-lb-scroll"><table class="sm-lb-table"><thead><tr><th class="sm-lb-rank">#</th><th>Model</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function renderFunnel(task) {
    const total = task.runs || 1;
    const stages = [{ stage: "Attempts", runs: task.runs }, ...task.funnel];
    return `<div class="sm-lb-funnel">` + stages.map((s) => {
      const pct = (100 * s.runs) / total;
      return `<div class="sm-lb-stage"><span class="sm-lb-stage-name">${esc(s.stage)}</span>` +
        `<span class="sm-lb-stage-track"><span style="width:${pct.toFixed(1)}%"></span></span>` +
        `<span class="sm-lb-stage-val">${s.runs} <small>${pct.toFixed(0)}%</small></span></div>`;
    }).join("") + `</div>`;
  }

  function renderTask(task, state) {
    const t = task.targets || {};
    const targets = [
      t.heat_duty_kw != null ? `duty ≥ ${t.heat_duty_kw} kW` : null,
      t.max_dp_tube_kpa != null ? `ΔP tube ≤ ${t.max_dp_tube_kpa} kPa` : null,
      t.max_dp_shell_kpa != null ? `ΔP shell ≤ ${t.max_dp_shell_kpa} kPa` : null,
    ].filter(Boolean).join(" · ");
    const date = (iso) => (iso ? iso.slice(0, 10) : "–");
    const facts = [
      ["Simulator", task.simulator_version || "legacy"],
      ["Score", task.score_version || "legacy"],
      ["Requirements", targets || "–"],
      ["Runs", `${task.runs} across ${task.models} models`],
      ["Recorded", `${date(task.first_run)} to ${date(task.last_run)}`],
    ].map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join("");
    return `<h2 class="sm-lb-title">${esc(task.title)}</h2>` +
      `<p class="sm-lb-slug"><code>${esc(task.slug)}</code> · <a href="https://github.com/suni-muhendis/sm-bench/tree/main/results/${encodeURIComponent(task.trackId)}/${encodeURIComponent(task.slug)}">task files</a></p>` +
      `<dl class="sm-lb-facts">${facts}</dl>` +
      renderTable(task, state) +
      `<h3>Where attempts stop</h3>` + renderFunnel(task);
  }

  function mount(root, data) {
    const tasks = data.tracks.flatMap((track) => track.tasks.map((task) => ({ ...task, track: track.label, trackId: track.id })));
    if (!tasks.length) {
      root.innerHTML = '<p class="sm-lb-status">No recorded runs yet.</p>';
      return;
    }
    const state = { slug: tasks[0].slug, sort: null };
    const fromHash = decodeURIComponent(location.hash.slice(1));
    if (tasks.some((t) => t.slug === fromHash)) state.slug = fromHash;

    const options = tasks.map((t) =>
      `<option value="${esc(t.slug)}">${esc(t.slug)} (${esc(t.track)}, ${t.runs} runs)</option>`).join("");
    root.innerHTML =
      `<div class="sm-lb-picker"><label for="sm-lb-task">Task</label><select id="sm-lb-task">${options}</select>` +
      `<span class="sm-lb-built">Built ${esc(data.generated_at.slice(0, 10))}</span></div><div class="sm-lb-body"></div>`;
    const select = root.querySelector("#sm-lb-task");
    const body = root.querySelector(".sm-lb-body");

    const draw = () => {
      select.value = state.slug;
      body.innerHTML = renderTask(tasks.find((t) => t.slug === state.slug), state);
    };
    select.addEventListener("change", () => {
      state.slug = select.value;
      state.sort = null;
      history.replaceState(null, "", "#" + encodeURIComponent(state.slug));
      draw();
    });
    body.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-sort]");
      if (!button) return;
      const key = button.dataset.sort;
      state.sort = state.sort && state.sort.key === key
        ? (state.sort.dir < 0 ? { key, dir: 1 } : null)
        : { key, dir: -1 };
      draw();
    });
    draw();
  }

  function init() {
    const root = document.getElementById("sm-leaderboard");
    if (!root) return;
    fetch(root.dataset.src)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => mount(root, data))
      .catch(() => {
        root.innerHTML = '<p class="sm-lb-status">The results could not be loaded. ' +
          'Build them with <code>python scripts/build_site_data.py</code> before serving the site.</p>';
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

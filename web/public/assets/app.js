const $ = (s) => document.querySelector(s);
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const brl = (v) =>
  Number(v || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  });
const num = (v) => Number(v || 0).toLocaleString("pt-BR");
const pct = (v) =>
  (Number(v || 0) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) +
  "%";
const paths = {
  overview: "M3 12h7V3H3z M14 21h7v-9h-7z M3 21h7v-5H3z M14 8h7V3h-7z",
  customers:
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M20 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
  segments:
    "M12 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6 M5 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6 M19 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6 M12 8v4 M5 16v-4h14v4",
  actions: "M3 17l6-6 4 4 8-10 M15 5h6v6 M3 21h18",
  assistant:
    "M12 3v3 M8 3h8 M5 7h14v13H5z M8 11h1 M15 11h1 M9 16h6 M2 11v5 M22 11v5",
  sentiment:
    "M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0 M8 9h.01 M16 9h.01 M8 14s1.5 3 4 3 4-3 4-3",
  bias: "M12 3l8 4v6c0 4-8 8-8 8s-8-4-8-8V7z M9 12l2 2 4-4",
  models:
    "M12 3c5 0 8 2 8 4s-3 4-8 4-8-2-8-4 3-4 8-4 M4 7v10c0 2 3 4 8 4s8-2 8-4V7 M4 12c0 2 3 4 8 4s8-2 8-4",
  search: "M21 21l-5-5 M18 10a8 8 0 1 0-16 0 8 8 0 0 0 16 0",
  plane: "M22 2L9 15 M22 2l-5 20-4-9-9-4z",
  chevron: "M9 5l7 7-7 7",
  close: "M6 6l12 12 M6 18L18 6",
};
const icon = (k) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[k] || paths.overview}"/></svg>`;
const pages = {
  overview: [
    "Visão geral",
    "Valor, risco e relacionamento em uma única visão de voo.",
  ],
  customers: [
    "Clientes",
    "Conheça o perfil, entenda os sinais e escolha o próximo contato.",
  ],
  segments: [
    "Segmentos",
    "Quatro perfis comportamentais. Uma estratégia para cada momento.",
  ],
  actions: [
    "Ações de CRM",
    "Do insight à ação, com revisão humana e evidência.",
  ],
  assistant: [
    "Assistente IA",
    "Uma nova perspectiva para decidir. Converse com os dados da carteira.",
  ],
  sentiment: [
    "Sentimento",
    "Escute a experiência. Identifique temas e pontos de atrito.",
  ],
  bias: [
    "Auditoria de viés",
    "Transparência nos critérios, atenção às diferenças.",
  ],
  models: ["Dados e modelos", "Da referência pública à decisão explicável."],
};
let state = {
  data: null,
  dashboard: null,
  selected: "SYN-0077",
  detail: null,
  page: "overview",
  tab: "360",
  listPage: 0,
  clientFilter: "all",
  search: "",
  months: 12,
  segment: "",
  route: "",
  chat: [],
  busy: false,
  draft: null,
};
let toastTimer;
function toast(text) {
  $("#toast").textContent = text;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("#toast").hidden = true), 6000);
}
async function api(path, options = {}) {
  const r = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  let body;
  try {
    body = await r.json();
  } catch {
    throw Error("Não foi possível interpretar a resposta do servidor.");
  }
  if (!r.ok) {
    if (r.status === 401) showLogin();
    throw Error(
      typeof body.detail === "string"
        ? body.detail
        : "Confira os campos da solicitação.",
    );
  }
  return body;
}
const post = (p, data) =>
  api(p, { method: "POST", body: JSON.stringify(data) });
const avatar = (cid) =>
  `<span class="avatar" aria-hidden="true">${esc(cid.replace("SYN-", "S").slice(-3))}</span>`;
const risk = (r) =>
  r >= 0.6
    ? ["Alto", "red"]
    : r >= 0.35
      ? ["Médio", "amber"]
      : ["Baixo", "green"];
const riskPill = (r) =>
  `<span class="pill ${risk(r)[1]}">${risk(r)[0]} · ${pct(r)}</span>`;
function header(key, action = "") {
  const [title, sub] = pages[key];
  return `<div class="page-header"><div><h1>${title}</h1><p>${sub}</p></div>${action}</div>`;
}
function details(title, value) {
  return `<details class="data-details"><summary>${esc(title)}</summary><pre>${esc(JSON.stringify(value, null, 2))}</pre></details>`;
}
function sources(evidence) {
  return (evidence || [])
    .map(
      (e) =>
        `<div class="source"><strong>${esc(e.title)}</strong><p>${esc(e.text)}</p><span class="muted">${esc(e.document_id)} · ${esc(e.version)}</span>${String(e.source).startsWith("https://") ? `<p><a href="${esc(e.source)}" target="_blank" rel="noopener noreferrer">Consultar fonte ↗</a></p>` : `<p>${esc(e.source)}</p>`}</div>`,
    )
    .join("");
}
function kpis(data) {
  const k = data.kpis;
  return `<div class="kpis">${[
    [
      "Clientes de alto valor",
      num(k.high_value),
      "Top 20% por valor potencial",
      "#00a9d4",
    ],
    [
      "Alto valor em risco",
      num(k.high_value_at_risk),
      "Prioridade de retenção · índice ≥ 60%",
      "#e93c69",
    ],
    [
      "CLV 12 meses · margem",
      brl(k.clv_12m),
      "Margem esperada, com desconto",
      "#08a686",
    ],
    [
      "CLV em risco",
      brl(k.clv_at_risk),
      "Margem ponderada pelo índice de risco",
      "#ffae33",
    ],
  ]
    .map(
      ([l, v, s, c]) =>
        `<div class="kpi" style="--accent:${c}"><div class="kpi-label">${l}</div><div class="kpi-value ${v.startsWith("R$") ? "money" : ""}">${v}</div><div class="kpi-sub">${s}</div></div>`,
    )
    .join("")}</div>`;
}
function filters() {
  const segs = [
    ...new Set(state.data.dashboard.rows.map((r) => r.segment)),
  ].sort();
  return `<div class="filters" id="filters"><div><label for="months">Período de viagens</label><select id="months">${[12, 6, 3, 1].map((n) => `<option value="${n}" ${n === state.months ? "selected" : ""}>Últimos ${n} ${n === 1 ? "mês" : "meses"}</option>`).join("")}</select></div><div><label for="segment">Segmento</label><select id="segment"><option value="">Todos os segmentos</option>${segs.map((s) => `<option ${s === state.segment ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></div><div class="route-filter"><label for="route">Rota</label><select id="route"><option value="">Todas as rotas</option>${(
    state.data.routes || [
      ...new Set(state.data.dashboard.rows.map((r) => r.route)),
    ]
  )
    .sort()
    .map(
      (r) =>
        `<option ${r === state.route ? "selected" : ""}>${esc(r)}</option>`,
    )
    .join(
      "",
    )}</select></div></div><button class="ghost filter-toggle" data-action="toggle-filters" style="display:none;margin-top:-12px;font-size:11px">Mostrar filtro de rota</button>`;
}
function radar(rows) {
  const top =
    Math.ceil(
      Math.max(1000, ...rows.map((r) => r.potential_value_12m)) / 1000,
    ) * 1000;
  const cutoff = state.data.dashboard.rows
    .filter((r) => r.is_high_value)
    .reduce((m, r) => Math.min(m, r.potential_value_12m), Infinity);
  const x = (r) => 70 + r * 334;
  const y = (v) => 252 - (v / top) * 210;
  let grid = "";
  for (let i = 0; i <= 4; i++) {
    const yy = 252 - i * 52.5;
    grid += `<line x1="70" y1="${yy}" x2="404" y2="${yy}" stroke="#e0e9f4"/><text x="60" y="${yy + 3}" text-anchor="end">${num((top * i) / 4)}</text><text x="${70 + i * 83.5}" y="274" text-anchor="middle">${i * 25}%</text>`;
  }
  const dots = rows
    .map((r) => {
      const color = r.is_high_value
        ? r.churn_risk >= 0.6
          ? "#d93260"
          : "#007af0"
        : "#8ba6c1";
      return `<circle tabindex="${state.selected === r.customer_id ? 0 : -1}" role="button" aria-label="Selecionar ${esc(r.customer_id)}, risco ${pct(r.churn_risk)}, valor potencial ${brl(r.potential_value_12m)}" data-cid="${esc(r.customer_id)}" cx="${x(r.churn_risk)}" cy="${y(r.potential_value_12m)}" r="${state.selected === r.customer_id ? 5.5 : 3.1}" fill="${color}" fill-opacity=".85" stroke="${state.selected === r.customer_id ? "#001e47" : "#fff"}" stroke-width="${state.selected === r.customer_id ? 2.5 : 0.8}"><title>${esc(r.customer_id)} · ${esc(r.segment)} · ${brl(r.potential_value_12m)}</title></circle>`;
    })
    .join("");
  return `<div class="radar-wrap"><svg class="radar" role="group" aria-label="Radar: índice de risco no eixo horizontal e valor potencial de margem no vertical" viewBox="0 0 430 305"><rect x="70" y="42" width="200.4" height="210" fill="#f0f7ff"/><rect x="270.4" y="42" width="133.6" height="210" fill="#fff1f4"/>${grid}<line x1="270.4" x2="270.4" y1="42" y2="252" stroke="#e4b2c2" stroke-dasharray="3 4"/><line x1="70" x2="404" y1="${y(cutoff)}" y2="${y(cutoff)}" stroke="#82abd1" stroke-dasharray="3 4"/><text class="quadrant" x="78" y="31" style="fill:#0061c9">Encantar</text><text class="quadrant" x="395" y="31" text-anchor="end" style="fill:#b8244c">Reter agora</text>${dots}<text x="237" y="298" text-anchor="middle">Índice de risco de evasão</text><text x="12" y="150" text-anchor="middle" transform="rotate(-90 12 150)">Valor potencial · margem 12 meses (R$)</text></svg></div><div class="radar-legend"><span><i class="legend-dot" style="background:#007af0"></i>Alto valor</span><span><i class="legend-dot" style="background:#d93260"></i>Alto valor em risco</span><span><i class="legend-dot" style="background:#8ba6c1"></i>Demais clientes</span></div><div id="chart-tip" class="chart-tip">Selecione um ponto para conhecer o cliente.</div>`;
}
function nextAction() {
  const d = state.detail;
  if (!d) return "";
  const r = state.data.dashboard.rows.find(
    (r) => r.customer_id === state.selected,
  );
  const rec = d.recommendation;
  return `<section class="panel next-action"><h2>Próxima melhor ação</h2><div class="customer-mini">${avatar(state.selected)}<div><strong>${esc(state.selected)}</strong><small>${esc(r.segment)}</small><small>Cliente sintético · ${esc(r.route.replace("-", " → "))}</small></div></div><div class="mini-values"><div class="mini-value"><small>Score de valor</small><strong>${num(r.value_score)}<small style="display:inline">/100</small></strong></div><div class="mini-value"><small>Índice de risco</small><strong>${pct(r.churn_risk)}</strong></div></div><div class="action-well"><h3>${icon("actions")} ${esc(rec.action.title)}</h3><p>${esc(rec.action.reason)}</p></div><div class="action-impact">CLV em risco deste cliente<strong>${brl(r.clv_at_risk)}</strong><small>Índice heurístico · sem probabilidade de sucesso</small></div><button class="primary full" data-action="review">Revisar recomendação ${icon("chevron")}</button></section>`;
}
function focusPanel() {
  const d = state.detail;
  if (!d) return "";
  const cid = state.selected;
  const r = state.data.dashboard.rows.find((v) => v.customer_id === cid);
  const options = state.data.dashboard.rows
    .map(
      (v) =>
        `<option value="${esc(v.customer_id)}" ${v.customer_id === cid ? "selected" : ""}>${esc(v.customer_id)} · ${esc(v.segment)}</option>`,
    )
    .join("");
  let body = "";
  if (state.tab === "trips") {
    body = `<h3>Histórico de viagens</h3><p class="caption">${d.trips.length} viagens na janela contratual</p><div class="table-scroll"><table class="queue-table"><thead><tr><th>Data</th><th>Rota</th><th class="num">Tarifa</th></tr></thead><tbody>${[
      ...d.trips,
    ]
      .sort((a, b) => b.flight_date.localeCompare(a.flight_date))
      .map(
        (t) =>
          `<tr><td>${esc(t.flight_date)}</td><td>${esc(t.origin)} → ${esc(t.destination)}</td><td class="num">${brl(t.fare_amount)}</td></tr>`,
      )
      .join("")}</tbody></table></div>`;
  } else if (state.tab === "loyalty") {
    body = `<h3>Fidelidade simulada</h3><div class="kv"><span>Saldo de pontos</span><strong>${num(d.loyalty.balance)}</strong></div><div class="kv"><span>Acumulados</span><strong>${num(d.loyalty.earned)}</strong></div><div class="kv"><span>Resgatados</span><strong>${num(d.loyalty.redeemed)}</strong></div><div class="notice">Categoria: ${esc(d.loyalty.tier || d.customer.loyalty_tier)}. Saldo sintético; não comprova elegibilidade a benefícios reais.</div>`;
  } else if (state.tab === "actions") {
    body = `<h3>${esc(d.recommendation.action.title)}</h3><p class="caption">${esc(d.recommendation.action.reason)}</p>${d.recommendation.offer ? `<div class="action-well"><h3>Ideia comercial · hipótese</h3><p>${esc(d.recommendation.offer.title)}</p><p>${esc(d.recommendation.offer.requires)}</p></div>` : ""}<button class="primary full" data-action="review">Revisar rascunho</button><div class="notice">Nenhum contato ou benefício é executado automaticamente.</div>`;
  } else {
    const routes = {};
    d.trips.forEach((t) => {
      const key = t.origin + " → " + t.destination;
      routes[key] = (routes[key] || 0) + 1;
    });
    const ranked = Object.entries(routes)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
    body = `<div class="focus-kpis"><div><small>CLV · 12 meses</small><strong>${brl(r.clv_12m)}</strong><small>Margem estimada</small></div><div><small>Índice de evasão</small><strong class="${r.churn_risk >= 0.6 ? "text-red" : ""}">${risk(r.churn_risk)[0]}</strong><small>${pct(r.churn_risk)} · heurístico</small></div><div><small>Score de valor</small><strong>${num(r.value_score)}/100</strong><small>Regra de valor</small></div></div><div class="focus-section"><h3>${icon("plane")} Rotas mais frequentes</h3>${ranked.map(([route, count]) => `<div class="route-row"><strong>${esc(route)}</strong><div class="route-track"><i style="width:${(count / d.trips.length) * 100}%"></i></div><span>${num(count)} voos</span></div>`).join("")}<small class="caption">Participação nas ${d.trips.length} viagens do cliente</small></div><div class="focus-section"><h3>${icon("assistant")} Sinais para a decisão</h3><ul class="driver-list">${r.drivers
      .slice(0, 4)
      .map((v) => `<li>${esc(v)}</li>`)
      .join(
        "",
      )}</ul>${d.explanation ? details("Contribuições de Shapley exatas", d.explanation) : ""}</div><div class="focus-section focus-note">${icon("sentiment")} <strong>Escuta do cliente</strong><br>Sem avaliações vinculadas a este perfil. O painel de sentimento analisa avaliações separadas.</div><div class="focus-footer"><button class="ghost" data-action="go-assistant">Perguntar à IA sobre este cliente →</button></div>`;
  }
  return `<aside class="customer-focus" aria-label="Cliente em foco"><div class="focus-top"><h2>${icon("customers")} Cliente em foco</h2><label class="sr-only" for="focus-customer">Selecionar cliente em foco</label><select id="focus-customer">${options}</select><div class="profile">${avatar(cid)}<div><span class="pill">${r.is_high_value ? "Cliente de alto valor" : "Carteira sintética"}</span><h3>${esc(cid)}</h3><small>${esc(r.home_airport)} · Canal: ${esc(d.customer.preferred_channel)}<br>${esc(r.segment)}</small></div></div></div><div class="tabs" role="tablist" aria-label="Dados do cliente">${[
    ["360", "Visão 360"],
    ["trips", "Viagens"],
    ["loyalty", "Fidelidade"],
    ["actions", "Ações"],
  ]
    .map(
      ([key, label]) =>
        `<button class="tab ${state.tab === key ? "active" : ""}" role="tab" id="tab-${key}" aria-controls="focus-panel" aria-selected="${state.tab === key}" data-tab="${key}">${label}</button>`,
    )
    .join(
      "",
    )}</div><div class="focus-body" id="focus-panel" role="tabpanel" aria-labelledby="tab-${state.tab}">${body}</div></aside>`;
}
function table(rows, limit = 5) {
  return `<div class="table-scroll"><table class="queue-table"><thead><tr><th>Cliente / segmento</th><th class="num">CLV 12 meses</th><th>Risco</th><th class="secondary-col num">Recência na base</th><th></th></tr></thead><tbody>${rows
    .slice(0, limit)
    .map(
      (r) =>
        `<tr><td><div class="client-cell">${avatar(r.customer_id)}<div><button class="row-button" data-cid="${esc(r.customer_id)}">${esc(r.customer_id)}</button><span class="sub">${esc(r.segment)}</span></div></div></td><td class="num">${brl(r.clv_12m)}</td><td>${riskPill(r.churn_risk)}</td><td class="secondary-col num">${num(r.recency_days)} dias</td><td><button class="icon-button" data-cid="${esc(r.customer_id)}" aria-label="Abrir ${esc(r.customer_id)}">${icon("chevron")}</button></td></tr>`,
    )
    .join(
      "",
    )}</tbody></table>${rows.length ? "" : '<div class="empty">Nenhum cliente neste recorte. Ajuste os filtros.</div>'}</div>`;
}
function overview() {
  const d = state.dashboard;
  return `<section class="hero"><div><h1>Visão geral</h1><p><strong>Decisões que aproximam.</strong> Valor, risco e relacionamento em uma única visão de voo.</p></div><div class="hero-status"><strong><span class="live-dot"></span>${state.data.llm.configured ? "Gemini configurado" : "Gemini não configurado"}</strong><small>Somente sob demanda · revisão humana</small></div></section>${filters()}${kpis(d)}<div class="overview-grid"><div><div class="radar-action"><section class="panel radar-panel"><h2>Radar de retenção</h2><span class="caption">Valor potencial × índice de evasão. Divisória horizontal = corte de alto valor.</span>${radar(d.rows)}</section>${nextAction()}</div><section class="panel section-gap"><div class="panel-head"><div><h2>Conexões que merecem atenção</h2><small>Fila ordenada por prioridade · ${d.rows.length} clientes no recorte</small></div><a class="ghost" href="#customers">Ver todos →</a></div>${table(d.rows)}</section></div>${focusPanel()}</div><p class="caption section-gap">${esc(d.notes)} Risco é índice heurístico, não probabilidade calibrada. Snapshot: ${esc(state.data.generated_at.slice(0, 10))}.</p>`;
}
function clients() {
  let rows = state.dashboard.rows.filter(
    (r) =>
      (state.clientFilter === "high"
        ? r.is_high_value
        : state.clientFilter === "risk"
          ? r.churn_risk >= 0.6
          : true) &&
      (!state.search ||
        [r.customer_id, r.segment, r.route].some((v) =>
          v.toLowerCase().includes(state.search.toLowerCase()),
        )),
  );
  const start = state.listPage * 20;
  if (start >= rows.length && state.listPage) {
    state.listPage = 0;
    return clients();
  }
  return `${header("customers")}${filters()}<div class="overview-grid"><section class="panel"><div class="table-toolbar"><label class="sr-only" for="client-search">Buscar cliente ou segmento</label><input id="client-search" value="${esc(state.search)}" placeholder="Buscar por código, segmento ou rota"><span class="caption">${rows.length} clientes encontrados</span></div><div class="chips">${[
    ["all", "Todos"],
    ["high", "Alto valor"],
    ["risk", "Em risco"],
  ]
    .map(
      ([key, label]) =>
        `<button class="chip ${state.clientFilter === key ? "active" : ""}" data-filter="${key}">${label}</button>`,
    )
    .join(
      "",
    )}</div>${table(rows.slice(state.listPage * 20), 20)}<div class="pager"><span>${rows.length ? state.listPage * 20 + 1 : 0}–${Math.min((state.listPage + 1) * 20, rows.length)} de ${rows.length}</span><div><button class="secondary" data-action="prev" ${!state.listPage ? "disabled" : ""}>Anterior</button><button class="secondary" data-action="next" ${(state.listPage + 1) * 20 >= rows.length ? "disabled" : ""}>Próxima</button></div></div></section>${focusPanel()}</div>`;
}
function segments() {
  const p = state.data.personas;
  return `${header("segments")}<div class="persona-grid">${(p.personas || []).map((v) => `<section class="panel persona-card"><div class="panel-head"><h2>${esc(v.name)}</h2><span class="pill blue">${pct(v.share)} da carteira</span></div><div class="persona-number">${num(v.size)} <small>clientes</small></div><p class="caption">${esc(v.description)}</p><div class="progress" aria-label="Participação de ${pct(v.share)}"><i style="width:${v.share * 100}%"></i></div><div class="kv"><span>Gasto médio observado</span><strong>${brl(v.profile.spend)}</strong></div><div class="kv"><span>Frequência média</span><strong>${num(v.profile.frequency)} viagens</strong></div><div class="kv"><span>Recência média</span><strong>${num(v.profile.recency_days)} dias</strong></div><button class="ghost" data-segment="${esc(v.name)}">Explorar estes clientes →</button></section>`).join("")}</div><div class="notice">Segmentação ${esc(p.method)} · silhouette ${num(p.quality?.silhouette)}. Grupos comportamentais da base sintética; não inferem características sensíveis.</div>${details("Metodologia e qualidade dos grupos", p.quality)}`;
}
function actions() {
  const s = state.data.strategy;
  return `${header("actions", `<button class="secondary" data-action="history">${icon("actions")} Histórico de revisão</button>`)}<div class="two-column">${s.rows.map((r) => `<section class="panel"><div class="panel-head"><h2>${esc(r.action)}</h2><span class="pill blue">${r.customers} clientes</span></div><p class="caption">${esc(r.persona)}</p><div class="kv"><span>CLV em risco</span><strong>${brl(r.value_at_risk)}</strong></div><div class="kv"><span>Custo assumido por contato</span><strong>${brl(r.assumed_cost_per_customer)}</strong></div><div class="kv"><span>Retenção assumida no cenário</span><strong>${pct(r.assumed_retention)}</strong></div><div class="kv"><span>Valor hipotético protegido</span><strong class="text-green">${brl(r.protected_value)}</strong></div>${r.offer ? `<div class="action-well"><h3>Ideia comercial · hipótese</h3><p>${esc(r.offer)}</p><p>Exige validação de elegibilidade e regras vigentes.</p></div>` : ""}<button class="ghost" data-segment="${esc(r.persona)}">Revisar clientes do segmento →</button></section>`).join("")}</div><div class="notice warning">${esc(s.disclaimer)}</div><section class="panel section-gap"><div class="panel-head"><h2>Simule antes de decidir</h2><span class="pill neutral">Cenário hipotético</span></div><form id="simulation-form" class="filters"><div><label for="sim-cost">Custo por cliente (R$)</label><input id="sim-cost" type="number" min="0" max="100000" value="10" step="0.01" required></div><div><label for="sim-retention">Retenção assumida (%)</label><input id="sim-retention" type="number" min="0" max="100" value="10" step="0.1" required></div><div><label>&nbsp;</label><button class="primary full">Calcular cenário</button></div></form><div id="simulation-result" class="caption">Use a carteira completa de ${state.data.dashboard.rows.length} clientes para comparar custo e valor em risco.</div></section>`;
}
function assistant() {
  const llm = state.data.llm;
  return `${header("assistant")}<div class="chat-layout"><section class="panel chat-panel"><div class="chat-context">${avatar(state.selected)}<div><strong>${esc(state.selected)}</strong><div class="caption">${esc(state.detail.scores.segment)} · ${esc(state.detail.customer.home_airport)}</div></div><span class="pill blue" style="margin-left:auto">Cliente sintético</span></div><div id="chat-log" class="chat-log">${state.chat.length ? state.chat.map((m) => chatMessage(m)).join("") : `<div class="chat-message assistant"><strong>${icon("assistant")} Seu copiloto de relacionamento</strong>Posso explicar os sinais de risco, comparar prioridades e ajudar a entender a próxima ação elegível. Cada resposta usa indicadores calculados e fontes citadas.<br><br>Escolha uma pergunta ao lado ou escreva abaixo. Nenhuma chamada é feita ao abrir esta tela.</div>`}</div><form id="chat-form" class="chat-form"><label class="sr-only" for="question">Pergunta para o Gemini</label><input id="question" placeholder="Pergunte sobre clientes, risco ou estratégias…" minlength="3" maxlength="2000" required ${state.busy ? "disabled" : ""}><button class="primary" ${state.busy ? "disabled" : ""}>${state.busy ? "Consultando…" : "Perguntar →"}</button></form></section><aside class="chat-side"><section class="panel"><h2>Inteligência com contexto</h2><ul class="status-list"><li><span class="live-dot"></span>${esc(llm.model)}</li><li>${icon("bias")} Fontes verificáveis</li><li>${icon("customers")} Revisão humana habilitada</li></ul><p class="caption">${llm.daily_limit} chamadas por dia para toda a aplicação. Uma tentativa por clique, intervalo de 20 s e cache de perguntas repetidas.</p><div class="prompt-list"><h3 class="section-gap">Explore a carteira</h3>${["Por que este cliente está em risco?", "Qual a próxima ação elegível para este cliente?", "Quais clientes precisam de atenção primeiro?"].map((q) => `<button class="prompt-button" data-prompt="${esc(q)}">${esc(q)} →</button>`).join("")}</div></section><div class="notice">A IA explica e redige. As regras calculam os indicadores e definem a ação elegível.</div></aside></div>`;
}
function chatMessage(m) {
  if (m.role === "user")
    return `<div class="chat-message user">${esc(m.text)}</div>`;
  return `<div class="chat-message assistant"><strong>${icon("assistant")} ${m.mode === "gemini_grounded" ? "Gemini · resposta com fontes" : "Consulta local · contingência"}</strong>${esc(m.text)}${m.notice ? `<div class="notice warning">${esc(m.notice)}</div>` : ""}<details><summary>Consultar ${m.evidence?.length || 0} fontes</summary>${sources(m.evidence)}</details></div>`;
}
function sentiment() {
  const s = state.data.sentiment;
  return `${header("sentiment")}<div class="sentiment-grid"><section class="panel"><h2>Escuta explicável</h2><p class="caption">Análise lexical em português, com negação, temas e evidências. Não é uma classificação feita pelo Gemini.</p><form id="sentiment-form"><label for="review-text">Avaliação sintética para análise</label><textarea id="review-text" maxlength="4000" required placeholder="Ex.: O atendimento foi ótimo, mas houve atraso no embarque."></textarea><button class="primary section-gap">Analisar avaliação</button></form><div id="sentiment-result"></div><label class="file-label" for="reviews-file">Importar CSV de avaliações (até 2 MiB / 1.000 linhas)<input id="reviews-file" type="file" accept=".csv,text/csv"></label><p class="caption">Colunas: review_id, text, source_url, is_synthetic. Avaliações públicas precisam de URL HTTPS; declare explicitamente a origem sintética.</p></section><section class="panel"><div class="panel-head"><h2>Amostra de demonstração</h2><span class="pill neutral">Base separada</span></div><p class="caption">Avaliações de exemplo sem vínculo individual com os clientes da carteira.</p><div id="sentiment-sample">${sentimentResults(s)}</div></section></div>`;
}
function sentimentResults(s) {
  const summary = s.summary || s.counts || {};
  const reviews = s.reviews || s.items || s.results || [];
  return `<div class="notice">Método: ${esc(s.method || "lexicon_pt_v2_topics_not_validated")} · ${reviews.length || summary.total || s.total || 0} avaliações</div>${Object.keys(summary).length ? details("Resumo da análise", summary) : ""}${reviews
    .slice(0, 30)
    .map(
      (r) =>
        `<div class="review-row"><span class="pill ${String(r.sentiment || r.label).includes("negat") ? "red" : String(r.sentiment || r.label).includes("posit") ? "green" : "neutral"}">${esc(r.sentiment || r.label || "Inconclusivo")}</span><p>${esc(r.text || r.review_id || "")}</p><small>Temas: ${esc((r.topics || []).map((t) => (typeof t === "string" ? t : t.subject || t.topic)).join(", ") || "não identificados")}</small>${details("Evidências lexicais", r)}</div>`,
    )
    .join("")}${reviews.length ? "" : details("Resultado da análise", s)}`;
}
function bias() {
  const b = state.data.bias;
  return `${header("bias")}<div class="notice">Base exclusivamente sintética. Resultado favorável: ${esc(b.settings?.favorable_outcome)}. Grupos pequenos são sinalizados; diferenças não demonstram discriminação ou causalidade.</div><div class="two-column">${Object.entries(
    b.attributes || {},
  )
    .map(
      ([key, v]) =>
        `<section class="panel"><div class="panel-head"><h2>${esc(v.label || key)}</h2><span class="pill ${v.verdict === "ok" ? "green" : "amber"}">${esc(v.verdict)}</span></div><div class="table-scroll"><table class="queue-table"><thead><tr><th>Grupo</th><th class="num">Clientes</th><th class="num">Seleção</th><th class="num">Risco médio</th></tr></thead><tbody>${(v.groups || []).map((g) => `<tr><td>${esc(g.group)}</td><td class="num">${num(g.customers)}</td><td class="num">${pct(g.selection_rate)}</td><td class="num">${pct(g.mean_predicted_risk)}</td></tr>`).join("")}</tbody></table></div>${details("Detalhes e grupos insuficientes", v)}</section>`,
    )
    .join("")}</div>${details("Critérios da auditoria", b.settings)}`;
}
function models() {
  const m = state.data.models;
  return `${header("models", `<button class="secondary" data-action="export">Exportar indicadores ↓</button>`)}<div class="two-column"><section class="panel"><h2>O dado percorre uma jornada</h2><div class="kv"><span>Referências públicas</span><strong>ANAC · tarifas e operações</strong></div><div class="kv"><span>Carteira</span><strong>${state.data.dashboard.rows.length} clientes sintéticos</strong></div><div class="kv"><span>Camadas</span><strong>Bronze → Silver → Gold</strong></div><div class="kv"><span>Snapshot publicado</span><strong>${esc(state.data.generated_at.slice(0, 10))}</strong></div><div class="kv"><span>Modelo em uso</span><strong>${esc(m.selected)}</strong></div><div class="notice">O pipeline analítico roda fora da Vercel. Este app usa uma projeção versionada dos seus resultados, sem importar os arquivos brutos.</div>${details("Premissas do CLV", state.data.clv)}</section><section class="panel"><h2>Modelos comparados com honestidade</h2><p class="caption">ROC AUC no teste com desfechos simulados. A escolha usa validação cruzada, sem consultar o teste.</p><div class="comparison"><div><small>Baseline heurístico</small><strong>${num(m.test_baseline?.roc_auc)}</strong><span class="pill blue">Selecionado</span></div><div><small>Modelo treinado</small><strong>${num(m.test_model?.roc_auc)}</strong><span class="pill neutral">Comparador</span></div></div><p class="caption">${esc(m.selection_rule)}</p><div class="notice warning">${esc(m.limitation)} Risco é índice heurístico, não probabilidade calibrada.</div>${details("Métricas e validação cruzada", m)}</section></div><section class="panel section-gap"><h2>Da evidência à ação</h2><p class="caption">Regras de CRM selecionam a ação. Gemini explica os fatos e redige sob demanda. Um revisor confirma as fontes e o checklist; a decisão registra exatamente o rascunho visto. A aplicação não envia campanhas.</p>${details("Metadados e contratos da versão", state.data.metadata)}</section>`;
}
function render() {
  if (!state.data) return;
  const page = pages[state.page] ? state.page : "overview";
  $("#navigation").innerHTML = Object.entries(pages)
    .map(
      ([key, [name]]) =>
        `<a class="nav-item ${key === page ? "active" : ""}" href="#${key}" ${key === page ? 'aria-current="page"' : ""}>${icon(key)}<span>${name}</span></a>`,
    )
    .join("");
  $("#content").innerHTML = {
    overview,
    customers: clients,
    segments,
    actions,
    assistant,
    sentiment,
    bias,
    models,
  }[page]();
  document.title = pages[page][0] + " · Azul CRM Intelligence";
}
async function selectCustomer(cid) {
  if (!state.data.dashboard.rows.some((r) => r.customer_id === cid)) {
    toast("Cliente não encontrado. Use um código da carteira sintética.");
    return;
  }
  state.detail = await api("/customers/" + encodeURIComponent(cid));
  state.selected = cid;
  state.tab = "360";
  render();
  if (window.innerWidth < 761 && ["overview", "customers"].includes(state.page))
    $(".customer-focus")?.scrollIntoView({
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
}
function syncNav() {
  const folded = matchMedia("(max-width:1050px)").matches;
  $("#sidebar").inert = folded && !$("#sidebar").classList.contains("open");
}
function navigate() {
  state.page = location.hash.slice(1) || "overview";
  if (!pages[state.page]) state.page = "overview";
  $("#sidebar").classList.remove("open");
  $("#nav-backdrop").hidden = true;
  $("#menu").setAttribute("aria-expanded", "false");
  syncNav();
  render();
  window.scrollTo({ top: 0 });
}
async function changeFilters() {
  state.months = Number($("#months")?.value || 12);
  state.segment = $("#segment")?.value || "";
  state.route = $("#route")?.value || "";
  state.listPage = 0;
  state.dashboard = await api(
    "/dashboard?" +
      new URLSearchParams({
        months: state.months,
        segment: state.segment,
        route: state.route,
      }),
  );
  if (
    state.dashboard.rows.length &&
    !state.dashboard.rows.some((r) => r.customer_id === state.selected)
  ) {
    state.selected = state.dashboard.rows[0].customer_id;
    state.detail = await api("/customers/" + state.selected);
  }
  render();
}
async function review(generate = false) {
  const content = $("#review-content");
  const dialog = $("#review-dialog");
  content.innerHTML =
    '<div class="loading">Preparando rascunho para revisão…</div>';
  if (!dialog.open) dialog.showModal();
  try {
    state.draft = await post("/drafts", {
      customer_id: state.selected,
      generate,
    });
    renderDraft();
  } catch (e) {
    content.innerHTML = `<div class="dialog-head"><h2 id="dialog-title">Recomendação indisponível</h2><button class="icon-button" data-action="close-dialog" aria-label="Fechar">${icon("close")}</button></div><div class="notice error">${esc(e.message)}</div>`;
  }
}
function renderDraft() {
  const r = state.draft;
  $("#review-content").innerHTML =
    `<div class="dialog-head"><div><h2 id="dialog-title">Revisar recomendação</h2><span class="caption">${esc(r.customer_id)} · ${esc(r.action.title)}</span></div><button class="icon-button" data-action="close-dialog" aria-label="Fechar">${icon("close")}</button></div><span class="pill ${r.mode === "gemini_grounded_draft" ? "green" : "neutral"}">${r.mode === "gemini_grounded_draft" ? "Gerado por Gemini com fontes" : "Prévia do playbook · sem geração LLM"}</span><div class="draft-text">${esc(r.draft)}</div>${r.notice ? `<div class="notice warning">${esc(r.notice)}</div>` : ""}<button class="secondary" data-action="generate-draft">${icon("assistant")} Gerar novo texto com Gemini</button>${r.offer ? `<div class="action-well section-gap"><h3>Hipótese comercial · não faz parte da mensagem</h3><p>${esc(r.offer.title)}. ${esc(r.offer.requires)}</p></div>` : ""}<details class="data-details"><summary>Conferir fontes (${r.evidence.length})</summary>${sources(r.evidence)}</details><h3 class="section-gap">Checklist de revisão humana</h3><div class="checklist">${r.review_checklist.map((c) => `<label><input type="checkbox" value="${esc(c.code)}" name="review-check"> <span>${esc(c.text)}</span></label>`).join("")}</div><label for="review-note">Observação da revisão</label><textarea id="review-note" maxlength="1000" placeholder="Registre o motivo ou ajustes necessários…"></textarea><div id="review-error" role="alert"></div><div class="dialog-actions"><button class="danger" data-decision="REJECTED">Rejeitar rascunho</button><button class="primary" data-decision="APPROVED">Aprovar para registro</button></div><p class="caption section-gap">A aprovação registra o rascunho exato. Nenhuma mensagem será enviada.</p>`;
}
async function decide(status, button) {
  button.disabled = true;
  try {
    const row = await post("/decisions", {
      draft_id: state.draft.draft_id,
      status,
      confirmed_checklist: [
        ...document.querySelectorAll('[name="review-check"]:checked'),
      ].map((c) => c.value),
      note: $("#review-note").value,
    });
    $("#review-dialog").close();
    toast(
      row.status === "APPROVED"
        ? "Revisão aprovada e registrada. Nenhuma mensagem foi enviada."
        : "Rejeição registrada no histórico.",
    );
  } catch (e) {
    $("#review-error").innerHTML =
      `<div class="notice error">${esc(e.message)}</div>`;
  } finally {
    button.disabled = false;
  }
}
async function showHistory() {
  const rows = await api("/decisions");
  $("#review-content").innerHTML =
    `<div class="dialog-head"><h2 id="dialog-title">Histórico de revisão</h2><button class="icon-button" data-action="close-dialog" aria-label="Fechar">${icon("close")}</button></div>${rows.length ? rows.map((r) => `<div class="history-item"><strong>${esc(r.customer_id)}</strong> <span class="pill ${r.status === "APPROVED" ? "green" : "red"}">${r.status === "APPROVED" ? "Aprovado" : "Rejeitado"}</span><p>${esc(r.recommendation.action.title)}</p><small>${esc(r.created_at)} · Enviado: não</small>${details("Rascunho e evidências preservados", r)}</div>`).join("") : '<div class="empty">Nenhuma decisão registrada. Revise uma recomendação para começar.</div>'}`;
  $("#review-dialog").showModal();
}
async function ask(question) {
  if (state.busy) return;
  state.busy = true;
  state.chat.push({ role: "user", text: question });
  render();
  try {
    const r = await post("/ask", { question, customer_id: state.selected });
    state.chat.push({ role: "assistant", text: r.answer, ...r });
  } catch (e) {
    state.chat.push({
      role: "assistant",
      text: "Não foi possível consultar o assistente.",
      notice: e.message,
      mode: "error",
      evidence: [],
    });
  } finally {
    state.busy = false;
    if (state.page === "assistant") render();
  }
}
function parseCSV(text) {
  const rows = [];
  let row = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (c === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((v) => v.trim())) rows.push(row);
      row = [];
      cell = "";
    } else cell += c;
  }
  if (quoted) throw Error("CSV contém aspas não fechadas.");
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const heads = (rows.shift() || []).map((h) =>
    h.replace(/^\uFEFF/, "").trim(),
  );
  if (
    !["review_id", "text", "source_url", "is_synthetic"].every((h) =>
      heads.includes(h),
    )
  )
    throw Error("CSV sem as quatro colunas obrigatórias.");
  if (rows.length > 1000) throw Error("O limite é 1.000 avaliações.");
  return rows.map((cells) => {
    const r = Object.fromEntries(heads.map((h, i) => [h, cells[i] || ""]));
    if (!["true", "false"].includes(r.is_synthetic.trim().toLowerCase()))
      throw Error("is_synthetic deve ser true ou false.");
    r.is_synthetic = r.is_synthetic.trim().toLowerCase() === "true";
    return r;
  });
}
function exportData() {
  const data = {
    generated_at: state.data.generated_at,
    dashboard: state.dashboard,
    models: state.data.models,
    limitations: state.dashboard.notes,
  };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "azul-crm-indicadores.json";
  a.click();
  URL.revokeObjectURL(url);
}
function showLogin() {
  $("#app").hidden = true;
  $("#login").hidden = false;
  $("#password").focus();
}
async function start() {
  try {
    state.data = await api("/bootstrap");
  } catch (e) {
    if (e.message.includes("Entre para")) {
      try {
        await post("/session", { password: "" });
        state.data = await api("/bootstrap");
      } catch {
        showLogin();
        return;
      }
    } else {
      showLogin();
      $("#login-error").textContent = e.message;
      return;
    }
  }
  state.dashboard = state.data.dashboard;
  const cid = state.data.dashboard.rows.some(
    (r) => r.customer_id === state.selected,
  )
    ? state.selected
    : state.data.dashboard.rows[0].customer_id;
  state.detail = await api("/customers/" + cid);
  state.selected = cid;
  $("#login").hidden = true;
  $("#app").hidden = false;
  $("#search-icon").innerHTML = icon("search");
  navigate();
}
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const b = e.submitter;
  b.disabled = true;
  try {
    await post("/session", { password: $("#password").value });
    $("#password").value = "";
    await start();
  } catch (err) {
    $("#login-error").textContent = err.message;
  } finally {
    b.disabled = false;
  }
});
$("#menu").addEventListener("click", () => {
  const open = $("#sidebar").classList.toggle("open");
  $("#nav-backdrop").hidden = !open;
  $("#menu").setAttribute("aria-expanded", String(open));
  syncNav();
});
$("#nav-backdrop").addEventListener("click", () => {
  $("#sidebar").classList.remove("open");
  $("#nav-backdrop").hidden = true;
  $("#menu").setAttribute("aria-expanded", "false");
  syncNav();
});
$("#logout").addEventListener("click", async () => {
  await api("/session", { method: "DELETE" });
  state.chat = [];
  state.draft = null;
  showLogin();
});
$("#global-search").addEventListener("keydown", async (e) => {
  if (e.key === "Enter") {
    try {
      await selectCustomer(e.target.value.trim().toUpperCase());
    } catch (err) {
      toast(err.message);
    }
  }
});
window.addEventListener("hashchange", navigate);
window.addEventListener("resize", syncNav);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $("#sidebar").classList.remove("open");
    $("#nav-backdrop").hidden = true;
    $("#menu").setAttribute("aria-expanded", "false");
    syncNav();
  }
  if (e.key === "Enter" && e.target.matches("circle[data-cid]"))
    e.target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
});
document.addEventListener("pointerover", (e) => {
  const dot = e.target.closest("circle[data-cid]");
  if (dot && $("#chart-tip")) {
    const r = state.data.dashboard.rows.find(
      (r) => r.customer_id === dot.dataset.cid,
    );
    $("#chart-tip").textContent =
      r.customer_id + " · " + r.segment + " · " + brl(r.potential_value_12m);
  }
});
document.addEventListener("focusin", (e) => {
  const dot = e.target.closest("circle[data-cid]");
  if (dot && $("#chart-tip")) {
    const r = state.data.dashboard.rows.find(
      (r) => r.customer_id === dot.dataset.cid,
    );
    $("#chart-tip").textContent =
      r.customer_id +
      " · " +
      brl(r.potential_value_12m) +
      " · risco " +
      pct(r.churn_risk);
  }
});
document.addEventListener("click", async (e) => {
  const el = e.target.closest("button,a,circle[data-cid]");
  if (!el) return;
  try {
    if (el.classList.contains("skip-link")) {
      e.preventDefault();
      $("#main").focus();
      return;
    }
    if (el.dataset.cid) {
      await selectCustomer(el.dataset.cid);
      return;
    }
    if (el.dataset.tab) {
      state.tab = el.dataset.tab;
      render();
      return;
    }
    if (el.dataset.filter) {
      state.clientFilter = el.dataset.filter;
      state.listPage = 0;
      render();
      return;
    }
    if (el.dataset.segment) {
      state.segment = el.dataset.segment;
      state.dashboard = await api(
        "/dashboard?" +
          new URLSearchParams({ months: 12, segment: state.segment }),
      );
      state.months = 12;
      state.route = "";
      state.listPage = 0;
      location.hash = "customers";
      if (state.page === "customers") render();
      return;
    }
    if (el.dataset.prompt) {
      $("#question").value = el.dataset.prompt;
      $("#question").focus();
      return;
    }
    if (el.dataset.decision) {
      await decide(el.dataset.decision, el);
      return;
    }
    const action = el.dataset.action;
    if (action === "review") await review();
    else if (action === "generate-draft") {
      el.disabled = true;
      await review(true);
    } else if (action === "close-dialog") $("#review-dialog").close();
    else if (action === "go-assistant") location.hash = "assistant";
    else if (action === "history") await showHistory();
    else if (action === "export") exportData();
    else if (action === "prev") {
      state.listPage--;
      render();
    } else if (action === "next") {
      state.listPage++;
      render();
    } else if (action === "toggle-filters") {
      $("#filters").classList.toggle("expanded");
      el.textContent = $("#filters").classList.contains("expanded")
        ? "Ocultar filtro de rota"
        : "Mostrar filtro de rota";
    }
  } catch (err) {
    toast(err.message);
  }
});
let searchTimer;
document.addEventListener("input", (e) => {
  if (e.target.id === "client-search") {
    state.search = e.target.value;
    state.listPage = 0;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const pos = e.target.selectionStart;
      render();
      $("#client-search").focus();
      $("#client-search").setSelectionRange(pos, pos);
    }, 180);
  }
});
document.addEventListener("change", async (e) => {
  try {
    if (["months", "segment", "route"].includes(e.target.id))
      await changeFilters();
    else if (e.target.id === "focus-customer")
      await selectCustomer(e.target.value);
    else if (e.target.id === "reviews-file") {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 2097152) throw Error("Arquivo excede 2 MiB.");
      const result = await post("/sentiment", {
        reviews: parseCSV(await file.text()),
      });
      $("#sentiment-result").innerHTML = sentimentResults(result);
      toast("Avaliações analisadas sem consumir o Gemini.");
    }
  } catch (err) {
    toast(err.message);
  }
});
document.addEventListener("submit", async (e) => {
  if (!["chat-form", "simulation-form", "sentiment-form"].includes(e.target.id))
    return;
  e.preventDefault();
  try {
    if (e.target.id === "chat-form") {
      await ask($("#question").value.trim());
    } else if (e.target.id === "simulation-form") {
      const cost =
        Number($("#sim-cost").value) * state.data.dashboard.rows.length;
      const retention = Number($("#sim-retention").value) / 100;
      const value = state.data.dashboard.kpis.clv_at_risk * retention;
      $("#simulation-result").innerHTML =
        `<div class="comparison"><div><small>Custo estimado</small><strong>${brl(cost)}</strong></div><div><small>Valor hipotético protegido</small><strong>${brl(value)}</strong></div></div><p>Saldo do cenário: <strong>${brl(value - cost)}</strong>. Hipótese de retenção: ${pct(retention)}. Não estima uplift real.</p>`;
    } else {
      const b = e.submitter;
      b.disabled = true;
      try {
        const result = await post("/sentiment", {
          reviews: [
            {
              review_id: "DEMO-" + Date.now(),
              text: $("#review-text").value,
              source_url: "",
              is_synthetic: true,
            },
          ],
        });
        $("#sentiment-result").innerHTML = sentimentResults(result);
      } finally {
        b.disabled = false;
      }
    }
  } catch (err) {
    toast(err.message);
  }
});
start().catch((e) => {
  showLogin();
  $("#login-error").textContent = e.message;
});

document.addEventListener("keydown", (e) => {
  if (
    !e.target.matches('[role="tab"]') ||
    !["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)
  )
    return;
  e.preventDefault();
  const keys = ["360", "trips", "loyalty", "actions"];
  let i = keys.indexOf(state.tab);
  i =
    e.key === "Home"
      ? 0
      : e.key === "End"
        ? keys.length - 1
        : (i + (e.key === "ArrowRight" ? 1 : keys.length - 1)) % keys.length;
  state.tab = keys[i];
  render();
  document.getElementById("tab-" + state.tab)?.focus();
});

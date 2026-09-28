import { AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";

const STORAGE_KEY = "fraudsense-demo-data-v1";
const DEMO_ROLES: Record<string, { name: string; role: "ADMIN" | "BUSINESS_MANAGER" | "ANALYST" }> = {
  "admin@fraudshield.ai": { name: "Admin User", role: "ADMIN" },
  "manager@fraudshield.ai": { name: "Business Manager", role: "BUSINESS_MANAGER" },
  "analyst@fraudshield.ai": { name: "Analyst User", role: "ANALYST" },
};

type DemoState = {
  transactions: any[];
  alerts: any[];
  customers: any[];
  rules: any[];
  apiKeys: any[];
  notes: Record<string, any[]>;
  feedback: Record<string, any>;
  notifications: any[];
  auditLogs: any[];
};

const timestamp = (daysAgo = 0) => new Date(Date.now() - daysAgo * 86_400_000).toISOString();
const newId = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 10)}`;

function createInitialState(): DemoState {
  const customers = Array.from({ length: 24 }, (_, index) => ({
    id: `customer-${index + 1}`,
    customer_id: `CUST-${1001 + index}`,
    name: ["Jordan Lee", "Sam Rivera", "Taylor Morgan", "Avery Chen", "Casey Patel", "Riley Brooks"][index % 6],
    email: `customer${index + 1}@example.test`,
    account_age_days: 60 + ((index * 19) % 900),
    risk_score: 15 + ((index * 13) % 82),
    risk_level: "LOW",
    total_transactions: 0,
    suspicious_transactions: 0,
    devices_used: 1 + (index % 4),
    locations_used: 1 + (index % 3),
    previous_fraud_reports: index % 7 === 0 ? 1 : 0,
    created_at: timestamp(400 - index * 7),
  }));

  const transactions = Array.from({ length: 96 }, (_, index) => {
    const customer = customers[index % customers.length];
    const riskLevel = index % 11 === 0 ? "HIGH" : index % 3 === 0 ? "MEDIUM" : "LOW";
    const riskScore = riskLevel === "HIGH" ? 78 + (index % 20) : riskLevel === "MEDIUM" ? 36 + (index % 35) : 5 + (index % 25);
    const riskFactors = riskLevel === "HIGH"
      ? ["Unusual transaction amount", "Device shared across multiple customers"]
      : riskLevel === "MEDIUM" ? ["Transaction velocity above customer baseline"] : [];
    const day = index % 27;
    return {
      id: `txn-${String(index + 1).padStart(4, "0")}`,
      transaction_id: `TXN-${260001 + index}`,
      customer_id: customer.customer_id,
      amount: Math.round((45 + ((index * 137) % 3600)) * 100) / 100,
      currency: "USD",
      transaction_datetime: timestamp(day),
      payment_method: ["credit_card", "debit_card", "paypal", "bank_transfer"][index % 4],
      ip_address: index % 9 === 0 ? "198.51.100.42" : `203.0.113.${(index % 220) + 10}`,
      device_id: index % 8 === 0 ? "DEVICE-SHARED-01" : `DEVICE-${(index % 31) + 1}`,
      location: ["Austin", "Chicago", "Seattle", "London", "Lahore"][index % 5],
      account_age_days: customer.account_age_days,
      previous_transaction_count: index % 12,
      transaction_status: riskLevel === "HIGH" ? "BLOCKED" : riskLevel === "MEDIUM" ? "REVIEW" : "APPROVED",
      risk_score: riskScore,
      risk_level: riskLevel,
      decision: riskLevel === "HIGH" ? "BLOCK" : riskLevel === "MEDIUM" ? "REVIEW" : "APPROVE",
      anomaly_score: Math.round((riskScore / 100) * 100) / 100,
      rule_score: riskLevel === "LOW" ? 0 : riskScore - 8,
      risk_factors: riskFactors,
      triggered_rules: riskFactors.map((factor) => factor.replace(/ /g, "_")),
      explanation: riskLevel === "LOW" ? "Activity is consistent with this customer's typical pattern." : `Risk signals detected: ${riskFactors.join(", ")}.`,
      created_at: timestamp(day),
    };
  });

  for (const customer of customers) {
    const rows = transactions.filter((transaction) => transaction.customer_id === customer.customer_id);
    const suspicious = rows.filter((transaction) => transaction.risk_level !== "LOW");
    customer.total_transactions = rows.length;
    customer.suspicious_transactions = suspicious.length;
    customer.risk_score = suspicious.length ? Math.round(suspicious.reduce((sum, row) => sum + row.risk_score, 0) / suspicious.length) : 12 + rows.length % 20;
    customer.risk_level = customer.risk_score >= 70 ? "HIGH" : customer.risk_score >= 30 ? "MEDIUM" : "LOW";
  }

  const alerts = transactions
    .filter((transaction, index) => transaction.risk_level !== "LOW" && (transaction.risk_level === "HIGH" || index % 2 === 0))
    .map((transaction, index) => ({
      id: `alert-${String(index + 1).padStart(4, "0")}`,
      transaction_id: transaction.id,
      customer_id: transaction.customer_id,
      severity: transaction.risk_level,
      title: transaction.risk_level === "HIGH" ? "High-risk transaction detected" : "Unusual transaction activity",
      reason: transaction.risk_factors.join("; "),
      status: index % 9 === 0 ? "CONFIRMED_FRAUD" : index % 7 === 0 ? "INVESTIGATING" : "NEW",
      assigned_to: "Analyst User",
      risk_score: transaction.risk_score,
      created_at: transaction.created_at,
      updated_at: transaction.created_at,
    }));

  return {
    transactions,
    alerts,
    customers,
    rules: [
      { id: "rule-amount", name: "High transaction amount", description: "Flag transactions above the normal range.", rule_type: "AMOUNT_THRESHOLD", configuration: { threshold: 2500 }, risk_weight: 30, is_active: true, created_at: timestamp(40), updated_at: timestamp(2) },
      { id: "rule-velocity", name: "Rapid transaction velocity", description: "Detect bursts in a short window.", rule_type: "VELOCITY", configuration: { max_count: 5, window_minutes: 10 }, risk_weight: 25, is_active: true, created_at: timestamp(40), updated_at: timestamp(4) },
      { id: "rule-device", name: "Shared device activity", description: "Flag a device used by several customers.", rule_type: "DEVICE_SHARING", configuration: { min_customers: 3 }, risk_weight: 20, is_active: false, created_at: timestamp(30), updated_at: timestamp(8) },
    ],
    apiKeys: [{ id: "key-001", business_name: "Demo Checkout", key_prefix: "fsk_demo", is_active: true, created_at: timestamp(12), last_used_at: timestamp(1) }],
    notes: {},
    feedback: {},
    notifications: alerts.slice(0, 8).map((alert) => ({ id: `notification-${alert.id}`, alert_id: alert.id, message: alert.title, is_read: false, created_at: alert.created_at })),
    auditLogs: [
      { id: "audit-001", user_id: "demo-admin", action: "DEMO_SESSION_STARTED", details: "Browser-only sample session", ip_address: null, created_at: timestamp(0) },
      { id: "audit-002", user_id: "demo-analyst", action: "ALERT_REVIEWED", details: "Sample investigation activity", ip_address: null, created_at: timestamp(1) },
    ],
  };
}

function saveState(state: DemoState) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* Current-page demo remains usable. */ }
}

function loadState(): DemoState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved) as DemoState;
  } catch { /* Start with fresh sample data if browser storage is unavailable. */ }
  const state = createInitialState();
  saveState(state);
  return state;
}

function getCustomer(state: DemoState, customerId: string) {
  return state.customers.find((customer) => customer.customer_id === customerId) ?? state.customers[0];
}

function summaryFor(transactions: any[], alerts: any[]) {
  const count = (level: string) => transactions.filter((transaction) => transaction.risk_level === level).length;
  const resolved = alerts.filter((alert) => ["CONFIRMED_FRAUD", "FALSE_POSITIVE"].includes(alert.status));
  const falsePositives = resolved.filter((alert) => alert.status === "FALSE_POSITIVE").length;
  const average = transactions.length ? transactions.reduce((sum, transaction) => sum + transaction.risk_score, 0) / transactions.length : 0;
  return {
    total_transactions: transactions.length,
    high_risk_transactions: count("HIGH"),
    medium_risk_transactions: count("MEDIUM"),
    low_risk_transactions: count("LOW"),
    blocked_transactions: transactions.filter((transaction) => transaction.decision === "BLOCK").length,
    under_review_transactions: transactions.filter((transaction) => transaction.decision === "REVIEW").length,
    fraud_alerts: alerts.length,
    new_alerts: alerts.filter((alert) => alert.status === "NEW").length,
    investigating_alerts: alerts.filter((alert) => alert.status === "INVESTIGATING").length,
    confirmed_fraud: alerts.filter((alert) => alert.status === "CONFIRMED_FRAUD").length,
    false_positives: falsePositives,
    false_positive_rate: resolved.length ? Math.round((falsePositives / resolved.length) * 1000) / 10 : 0,
    average_risk_score: Math.round(average * 100) / 100,
    suspicious_customers: new Set(transactions.filter((transaction) => transaction.risk_level !== "LOW").map((transaction) => transaction.customer_id)).size,
  };
}

function dateRange(items: any[], key: string, params: any) {
  return items.filter((item) => {
    const date = item[key]?.slice(0, 10);
    return (!params.date_from || date >= params.date_from) && (!params.date_to || date <= params.date_to);
  });
}

function buildTrend(transactions: any[], days: number) {
  const points = new Map<string, any>();
  for (let offset = Math.min(days - 1, 89); offset >= 0; offset--) {
    const date = timestamp(offset).slice(0, 10);
    points.set(date, { date, low: 0, medium: 0, high: 0, confirmed: 0, total: 0 });
  }
  for (const transaction of transactions) {
    const point = points.get(transaction.transaction_datetime.slice(0, 10));
    if (point) { point[transaction.risk_level.toLowerCase()]++; point.total++; }
  }
  return [...points.values()];
}

function networkFor(state: DemoState, customerId?: string) {
  const related = state.customers.filter((customer) => customer.customer_id === customerId || ["CUST-1001", "CUST-1009", "CUST-1017", "CUST-1021"].includes(customer.customer_id));
  const nodes: any[] = related.map((customer) => ({ id: customer.customer_id, type: "customer", label: customer.customer_id, risk_level: customer.risk_level }));
  nodes.push({ id: "DEVICE-SHARED-01", type: "device", label: "DEVICE-SHARED-01" }, { id: "198.51.100.42", type: "ip", label: "198.51.100.42" });
  const edges = related.flatMap((customer) => [
    { source: customer.customer_id, target: "DEVICE-SHARED-01", type: "shared_device" },
    { source: customer.customer_id, target: "198.51.100.42", type: "shared_ip" },
  ]);
  return { nodes, edges, root_customer_id: customerId, customer_count: related.length, shared_device_count: 1, shared_ip_count: 1, linking_transaction_count: related.length * 2, truncated: false };
}

function transactionSummary(transaction: any) {
  const { id, transaction_id, customer_id, amount, currency, transaction_datetime, payment_method, device_id, ip_address, location, transaction_status, risk_score, risk_level, decision } = transaction;
  return { id, transaction_id, customer_id, amount, currency, transaction_datetime, payment_method, device_id, ip_address, location, transaction_status, risk_score, risk_level, decision };
}

function investigationCase(state: DemoState, alertId: string) {
  const alert = state.alerts.find((item) => item.id === alertId) ?? state.alerts[0];
  const transaction = state.transactions.find((item) => item.id === alert.transaction_id) ?? state.transactions[0];
  const customer = getCustomer(state, alert.customer_id);
  const history = state.transactions.filter((item) => item.customer_id === customer.customer_id).slice(0, 8);
  const related = state.transactions.filter((item) => item.id !== transaction.id && (item.device_id === transaction.device_id || item.ip_address === transaction.ip_address)).slice(0, 6);
  const fingerprint = (value: string) => ({ value, transaction_count: history.length, first_seen: timestamp(20), last_seen: timestamp(1), city: transaction.location, country: "US" });
  return {
    alert: { ...alert }, customer: { ...customer }, transaction: { ...transaction },
    risk_factors: transaction.risk_factors, triggered_rules: transaction.triggered_rules, ai_explanation: transaction.explanation,
    transaction_history: history.map(transactionSummary), related_transactions: related.map(transactionSummary),
    devices: [fingerprint(transaction.device_id)], ip_addresses: [fingerprint(transaction.ip_address)], locations: [fingerprint(transaction.location)],
    related_alerts: state.alerts.filter((item) => item.customer_id === customer.customer_id).slice(0, 5),
    investigation_notes: state.notes[alert.id] ?? [],
  };
}

function addAudit(state: DemoState, action: string, details: string) {
  state.auditLogs.unshift({ id: newId("audit"), user_id: "demo-user", action, details, ip_address: null, created_at: timestamp() });
}

function createTransaction(state: DemoState, payload: any) {
  const customerId = payload.customer_id || "CUST-1001";
  let customer = state.customers.find((item) => item.customer_id === customerId);
  if (!customer) {
    customer = { id: newId("customer"), customer_id: customerId, name: customerId, email: null, account_age_days: 1, risk_score: 20, risk_level: "LOW", total_transactions: 0, suspicious_transactions: 0, devices_used: 1, locations_used: 1, previous_fraud_reports: 0, created_at: timestamp() };
    state.customers.unshift(customer);
  }
  const amount = Number(payload.amount) || 100;
  const level = amount > 2500 ? "HIGH" : amount > 1200 ? "MEDIUM" : "LOW";
  const score = level === "HIGH" ? 88 : level === "MEDIUM" ? 56 : 14;
  const transaction = {
    id: newId("txn"), transaction_id: payload.transaction_id || newId("TXN"), customer_id: customerId,
    amount, currency: payload.currency || "USD", transaction_datetime: payload.transaction_datetime || timestamp(),
    payment_method: payload.payment_method || "credit_card", ip_address: payload.ip_address || "203.0.113.10",
    device_id: payload.device_id || "DEVICE-DEMO-01", location: payload.location || "Austin",
    account_age_days: customer.account_age_days, previous_transaction_count: customer.total_transactions,
    transaction_status: level === "HIGH" ? "BLOCKED" : level === "MEDIUM" ? "REVIEW" : "APPROVED",
    risk_score: score, risk_level: level, decision: level === "HIGH" ? "BLOCK" : level === "MEDIUM" ? "REVIEW" : "APPROVE",
    anomaly_score: score / 100, rule_score: Math.max(0, score - 8), risk_factors: level === "LOW" ? [] : ["Unusual transaction amount"],
    triggered_rules: level === "LOW" ? [] : ["AMOUNT_THRESHOLD"], explanation: level === "LOW" ? "Activity is within the expected range." : "The amount is unusual for this sample customer.", created_at: timestamp(),
  };
  state.transactions.unshift(transaction);
  customer.total_transactions++;
  if (level !== "LOW") {
    customer.suspicious_transactions++;
    customer.risk_score = score;
    customer.risk_level = level;
    const alert = { id: newId("alert"), transaction_id: transaction.id, customer_id: customerId, severity: level, title: "Unusual transaction activity", reason: transaction.risk_factors.join("; "), status: "NEW", assigned_to: "Analyst User", risk_score: score, created_at: timestamp(), updated_at: timestamp() };
    state.alerts.unshift(alert);
    state.notifications.unshift({ id: newId("notification"), alert_id: alert.id, message: alert.title, is_read: false, created_at: alert.created_at });
  }
  addAudit(state, "TRANSACTION_CREATED", transaction.transaction_id);
  return transaction;
}

function parseBody(data: any) {
  if (typeof data !== "string") return data ?? {};
  try { return JSON.parse(data); } catch { return {}; }
}

function respond(config: InternalAxiosRequestConfig, data: any, status = 200): AxiosResponse {
  return { config, data, status, statusText: status === 201 ? "Created" : "OK", headers: new AxiosHeaders(), request: null };
}

export const demoApiAdapter: AxiosAdapter = async (config) => {
  const state = loadState();
  const method = (config.method || "get").toUpperCase();
  const path = new URL(config.url || "/", "https://demo.local").pathname.replace(/^\/api(?=\/|$)/, "").replace(/\/$/, "") || "/";
  const params = config.params ?? {};
  const body = parseBody(config.data);
  let data: any = {};
  let status = 200;

  if (path === "/auth/login" && method === "POST") {
    const email = String(body.email || "analyst@fraudshield.ai").toLowerCase();
    const profile = DEMO_ROLES[email] ?? { name: email.split("@")[0] || "Demo Analyst", role: "ANALYST" as const };
    data = { access_token: `demo-token-${profile.role.toLowerCase()}`, token_type: "bearer", user: { id: `demo-${profile.role.toLowerCase()}`, email, name: profile.name, role: profile.role, is_active: true } };
  } else if (path === "/auth/register" && method === "POST") {
    data = { id: newId("demo-user"), name: body.name, email: body.email, role: body.role || "ANALYST", is_active: true };
    status = 201;
  } else if (path === "/dashboard/summary") {
    const summary = summaryFor(state.transactions, state.alerts);
    data = { total_transactions: summary.total_transactions, high_risk_transactions: summary.high_risk_transactions, medium_risk_transactions: summary.medium_risk_transactions, fraud_alerts: summary.fraud_alerts, confirmed_fraud: summary.confirmed_fraud, false_positives: summary.false_positives, average_risk_score: summary.average_risk_score };
  } else if (path === "/dashboard/fraud-trend") {
    data = buildTrend(state.transactions, Number(params.days) || 30).filter((point) => point.high + point.medium > 0).map((point) => ({ date: point.date, suspicious_transactions: point.high + point.medium }));
  } else if (path === "/dashboard/recent-alerts") {
    data = state.alerts.slice(0, Number(params.limit) || 10);
  } else if (path === "/dashboard/recent-transactions") {
    data = state.transactions.slice(0, Number(params.limit) || 10);
  } else if (path === "/dashboard/admin/summary") {
    data = summaryFor(dateRange(state.transactions, "transaction_datetime", params), dateRange(state.alerts, "created_at", params));
  } else if (path === "/dashboard/admin/fraud-trend") {
    data = buildTrend(dateRange(state.transactions, "transaction_datetime", params), Number(params.days) || 30);
  } else if (path === "/dashboard/admin/risk-distribution") {
    data = ["HIGH", "MEDIUM", "LOW"].map((risk_level) => ({ risk_level, count: state.transactions.filter((transaction) => transaction.risk_level === risk_level).length }));
  } else if (path === "/dashboard/admin/suspicious-customers") {
    data = state.customers.filter((customer) => customer.suspicious_transactions > 0).slice(0, Number(params.limit) || 20);
  } else if (path === "/dashboard/admin/suspicious-devices" || path === "/dashboard/admin/suspicious-ips") {
    const field = path.endsWith("devices") ? "device_id" : "ip_address";
    const groups = new Map<string, any[]>();
    state.transactions.forEach((transaction) => groups.set(transaction[field], [...(groups.get(transaction[field]) ?? []), transaction]));
    data = [...groups.entries()].filter(([, rows]) => rows.length > 1).slice(0, Number(params.limit) || 10).map(([value, rows]) => ({ value, transaction_count: rows.length, customer_count: new Set(rows.map((row) => row.customer_id)).size, high_risk_count: rows.filter((row) => row.risk_level === "HIGH").length, avg_risk_score: Math.round(rows.reduce((sum, row) => sum + row.risk_score, 0) / rows.length), last_seen: rows[0].created_at, shared_across_customers: new Set(rows.map((row) => row.customer_id)).size > 1, suspicion_score: Math.min(100, rows.length * 12) }));
  } else if (path === "/alerts" && method === "GET") {
    data = state.alerts.filter((alert) => !params.status_filter || alert.status === params.status_filter).slice(0, Number(params.limit) || state.alerts.length);
  } else if (/^\/alerts\/[^/]+\/feedback$/.test(path) && method === "GET") {
    const alertId = path.split("/")[2];
    data = state.feedback[alertId] ? [state.feedback[alertId]] : [];
  } else if (/^\/alerts\/[^/]+\/notes$/.test(path) && method === "POST") {
    const alertId = path.split("/")[2];
    const note = { id: newId("note"), alert_id: alertId, analyst_id: "demo-analyst", analyst_name: "Demo Analyst", note: body.note || "Reviewed in demo", created_at: timestamp() };
    state.notes[alertId] = [note, ...(state.notes[alertId] ?? [])];
    addAudit(state, "INVESTIGATION_NOTE_ADDED", alertId);
    data = note;
  } else if (/^\/alerts\/[^/]+\/feedback$/.test(path) && method === "POST") {
    const alertId = path.split("/")[2];
    const feedback = { id: newId("feedback"), alert_id: alertId, analyst_id: "demo-analyst", analyst_name: "Demo Analyst", actual_result: body.actual_result, comments: body.comments || null, created_at: timestamp() };
    state.feedback[alertId] = feedback;
    const alert = state.alerts.find((item) => item.id === alertId);
    if (alert) alert.status = body.actual_result === "CONFIRMED_FRAUD" ? "CONFIRMED_FRAUD" : "FALSE_POSITIVE";
    addAudit(state, "ALERT_FEEDBACK_SUBMITTED", alertId);
    data = feedback;
  } else if (/^\/investigation\/case\/[^/]+$/.test(path)) {
    data = investigationCase(state, path.split("/").slice(-1)[0] || "");
  } else if (path === "/investigation/ask" && method === "POST") {
    data = { answer: `Demo analysis: ${body.question || "This activity"} is shown with the sample risk signals and transaction history. This response is generated locally for the Vercel demo.` };
  } else if (path === "/notifications" && method === "GET") {
    const notifications = state.notifications.slice(0, Number(params.limit) || 15);
    data = { data: notifications, unread_count: notifications.filter((notification) => !notification.is_read).length };
  } else if (path === "/notifications/read" && method === "POST") {
    state.notifications.forEach((notification) => { notification.is_read = true; });
    data = { success: true };
  } else if (path === "/transactions" && method === "GET") {
    let rows = [...state.transactions];
    if (params.search) rows = rows.filter((transaction) => transaction.transaction_id.toLowerCase().includes(String(params.search).toLowerCase()) || transaction.customer_id.toLowerCase().includes(String(params.search).toLowerCase()));
    if (params.risk_level) rows = rows.filter((transaction) => transaction.risk_level === params.risk_level);
    if (params.payment_method) rows = rows.filter((transaction) => transaction.payment_method === params.payment_method);
    if (params.location) rows = rows.filter((transaction) => transaction.location === params.location);
    const page = Number(params.page) || 1;
    const pageSize = Number(params.page_size) || 20;
    data = { data: rows.slice((page - 1) * pageSize, page * pageSize), page, page_size: pageSize, total: rows.length };
  } else if (path === "/transactions" && method === "POST") {
    data = createTransaction(state, body);
    status = 201;
  } else if (path === "/transactions/import-csv" && method === "POST") {
    const file = config.data instanceof FormData ? config.data.get("file") : null;
    const text = file && typeof file !== "string" ? await file.text() : "";
    const lines = text.split(/\r?\n/).filter(Boolean);
    let successful = 0;
    if (lines.length > 1) {
      const headers = lines[0].split(",").map((header) => header.trim().toLowerCase());
      for (const line of lines.slice(1)) {
        const cells = line.split(",");
        const row = Object.fromEntries(headers.map((header, index) => [header, cells[index]?.trim() || ""]));
        if (!row.transaction_id || !row.customer_id || !Number(row.amount)) continue;
        createTransaction(state, { ...row, amount: Number(row.amount) });
        successful++;
      }
    }
    data = { total_rows: Math.max(0, lines.length - 1), successful_rows: successful, failed_rows: Math.max(0, lines.length - 1 - successful), duplicate_rows: 0, errors: [] };
  } else if (/^\/transactions\/[^/]+\/risk$/.test(path)) {
    const transaction = state.transactions.find((item) => item.id === path.split("/")[2]) ?? state.transactions[0];
    data = { risk_score: transaction.risk_score, risk_level: transaction.risk_level, decision: transaction.decision, triggered_rules: transaction.triggered_rules, anomaly_score: transaction.anomaly_score, risk_factors: transaction.risk_factors, explanation: transaction.explanation };
  } else if (/^\/transactions\/[^/]+$/.test(path) && method === "GET") {
    data = state.transactions.find((transaction) => transaction.id === path.split("/")[2]) ?? state.transactions[0];
  } else if (path === "/customers" && method === "GET") {
    data = state.customers;
  } else if (/^\/customers\/[^/]+\/transactions$/.test(path)) {
    const customer = getCustomer(state, path.split("/")[2]);
    data = { customer, transactions: state.transactions.filter((transaction) => transaction.customer_id === customer.customer_id) };
  } else if (/^\/customers\/[^/]+\/network$/.test(path)) {
    data = networkFor(state, path.split("/")[2]);
  } else if (path === "/fraud-network/rings") {
    const customerIds = ["CUST-1001", "CUST-1009", "CUST-1017", "CUST-1021"];
    data = { rings: [{ ring_id: "ring-001", size: customerIds.length, customer_ids: customerIds, shared_device_count: 1, shared_ip_count: 1, total_suspicious_transactions: 7, avg_risk_score: 76, max_risk_level: "HIGH" }] };
  } else if (/^\/fraud-network\/graph\/[^/]+$/.test(path)) {
    const id = path.split("/").slice(-1)[0] || "";
    data = networkFor(state, id.startsWith("CUST-") ? id : undefined);
  } else if (path === "/reports/fraud-trends") {
    const daily = buildTrend(state.transactions, Number(params.days) || 30);
    data = { daily, total_confirmed_fraud: state.alerts.filter((alert) => alert.status === "CONFIRMED_FRAUD").length, total_false_positives: state.alerts.filter((alert) => alert.status === "FALSE_POSITIVE").length, trend_direction: "stable", change_pct: 4.2, start_date: daily[0]?.date, end_date: daily[daily.length - 1]?.date };
  } else if (/^\/reports\/export\//.test(path)) {
    data = new Blob(["Demo export\nThis browser-only export contains sample FraudSense data."], { type: "text/csv" });
  } else if (path === "/rules" && method === "GET") {
    data = state.rules;
  } else if (path === "/rules" && method === "POST") {
    const rule = { ...body, id: newId("rule"), created_at: timestamp(), updated_at: timestamp() };
    state.rules.unshift(rule);
    addAudit(state, "RULE_CREATED", rule.name);
    data = rule;
    status = 201;
  } else if (/^\/rules\/[^/]+$/.test(path) && method === "PUT") {
    const rule = state.rules.find((item) => item.id === path.split("/")[2]);
    if (rule) Object.assign(rule, body, { updated_at: timestamp() });
    data = rule ?? {};
  } else if (/^\/rules\/[^/]+$/.test(path) && method === "DELETE") {
    state.rules = state.rules.filter((rule) => rule.id !== path.split("/")[2]);
    data = { success: true };
  } else if (path === "/api-keys" && method === "GET") {
    data = state.apiKeys;
  } else if (path === "/api-keys" && method === "POST") {
    const key = { id: newId("key"), business_name: body.business_name, api_key: `fsk_demo_${newId("token")}`, key_prefix: "fsk_demo", is_active: true, created_at: timestamp(), last_used_at: null };
    state.apiKeys.unshift(key);
    data = key;
    status = 201;
  } else if (/^\/api-keys\/[^/]+$/.test(path) && method === "DELETE") {
    const key = state.apiKeys.find((item) => item.id === path.split("/")[2]);
    if (key) key.is_active = false;
    data = key ?? { success: true };
  } else if (path === "/audit-logs") {
    data = state.auditLogs.slice(0, Number(params.limit) || 200);
  }

  saveState(state);
  return respond(config, data, status);
};
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.join(__dirname, "pitch_deck_render");
const PPTX_PATH = path.join(__dirname, "AirSentinel_Hackathon_Pitch_Deck.pptx");

const W = 1280;
const H = 720;
const C = {
  ink: "#0A1728",
  navy: "#10263F",
  panel: "#F3F7F6",
  white: "#FFFFFF",
  teal: "#078B83",
  teal2: "#32B7A5",
  green: "#55B56A",
  lime: "#CDEB68",
  sky: "#88C9E8",
  amber: "#F4B942",
  red: "#D76152",
  grey: "#5B6C7C",
  mist: "#D8E4E2",
  light: "#EAF1F0",
};

function addBox(slide, x, y, w, h, fill = C.white, radius = "rounded-xl", line = "none", lineWidth = 0) {
  const options = {
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: lineWidth },
  };
  if (radius !== "none") options.borderRadius = radius;
  return slide.shapes.add(options);
}

function addText(slide, text, x, y, w, h, size = 24, color = C.ink, bold = false, align = "left") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = { fontSize: size, color, bold, fontFamily: "Aptos", alignment: align };
  return shape;
}

function addCircle(slide, x, y, d, fill, label = "", labelColor = C.white, size = 18) {
  const circle = slide.shapes.add({
    geometry: "ellipse",
    position: { left: x, top: y, width: d, height: d },
    fill,
    line: { style: "solid", fill, width: 0 },
  });
  if (label) addText(slide, label, x, y + d * 0.24, d, d * 0.52, size, labelColor, true, "center");
  return circle;
}

function addPill(slide, text, x, y, w, fill = C.light, color = C.teal, size = 13) {
  addBox(slide, x, y, w, 30, fill, "rounded-full");
  addText(slide, text, x + 8, y + 6, w - 16, 18, size, color, true, "center");
}

function addTitle(slide, kicker, title, subtitle = "") {
  addText(slide, kicker.toUpperCase(), 64, 42, 760, 24, 12, C.teal, true);
  addText(slide, title, 64, 72, 1120, 76, 38, C.ink, true);
  if (subtitle) addText(slide, subtitle, 64, 146, 1110, 46, 17, C.grey, false);
}

function addFooter(slide, page, section = "AIRSentinel") {
  addBox(slide, 64, 680, 1152, 2, C.mist, "none");
  addText(slide, section.toUpperCase(), 64, 691, 300, 18, 10, C.grey, true);
  addText(slide, String(page).padStart(2, "0"), 1170, 691, 46, 18, 10, C.grey, true, "right");
}

function addNotes(slide, body, sources = []) {
  const sourceBlock = sources.length ? `\n\nSources:\n${sources.map((s) => `- ${s}`).join("\n")}` : "";
  slide.speakerNotes.textFrame.setText(`${body}${sourceBlock}`);
  slide.speakerNotes.setVisible(true);
}

function newSlide(presentation, page, section, background = C.white) {
  const slide = presentation.slides.add();
  slide.background.fill = background;
  addFooter(slide, page, section);
  return slide;
}

function metricCard(slide, x, y, w, label, value, detail, accent = C.teal) {
  addBox(slide, x, y, w, 132, C.white, "rounded-xl", C.mist, 1);
  addBox(slide, x, y, 8, 132, accent, "rounded-xl");
  addText(slide, label.toUpperCase(), x + 24, y + 18, w - 40, 20, 11, C.grey, true);
  addText(slide, value, x + 24, y + 46, w - 40, 44, 30, C.ink, true);
  addText(slide, detail, x + 24, y + 94, w - 40, 24, 13, C.grey, false);
}

function node(slide, x, y, w, h, eyebrow, title, detail, fill = C.white, accent = C.teal) {
  addBox(slide, x, y, w, h, fill, "rounded-xl", C.mist, 1);
  addBox(slide, x, y, 7, h, accent, "rounded-xl");
  addText(slide, eyebrow.toUpperCase(), x + 20, y + 16, w - 32, 18, 10, accent, true);
  addText(slide, title, x + 20, y + 42, w - 32, 32, 20, C.ink, true);
  addText(slide, detail, x + 20, y + 82, w - 32, h - 94, 13, C.grey, false);
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function buildDeck() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });

  // 1 — Cover
  {
    const s = presentation.slides.add();
    s.background.fill = C.ink;
    addBox(s, 0, 0, W, 10, C.teal2, "none");
    addCircle(s, 930, 54, 250, C.navy);
    addCircle(s, 1010, 132, 116, C.teal);
    addCircle(s, 882, 256, 70, C.green);
    addPill(s, "CLEAN AIR & CLIMATE RESILIENCE", 64, 62, 316, C.navy, C.sky, 12);
    addText(s, "AirSentinel", 64, 154, 720, 88, 56, C.white, true);
    addText(s, "From city signal to locality action", 64, 240, 760, 58, 30, C.sky, true);
    addText(s, "A human-reviewed, AI-assisted evidence platform for hyper-local pollution detection, short-horizon forecasting and authority coordination.", 64, 330, 715, 110, 22, "#D7E7F4", false);
    addPill(s, "INDIA-FIRST", 64, 480, 126, C.teal, C.white, 12);
    addPill(s, "GOOGLE CLOUD READY", 202, 480, 180, C.navy, C.sky, 12);
    addPill(s, "AUDITABLE BY DESIGN", 394, 480, 178, C.navy, C.lime, 12);
    addText(s, "Working prototype • Sustainability track • Submission package", 64, 590, 750, 28, 16, C.mist, false);
    addText(s, "AIRSentinel  /  2026", 64, 674, 280, 20, 11, C.sky, true);
    addNotes(s, "Open with the problem: governments receive many city-level signals, but local response depends on evidence quality, timeliness and accountable review. AirSentinel connects those steps without pretending that a model can prove a source or authorize enforcement.");
  }

  // 2 — Problem
  {
    const s = newSlide(presentation, 2, "Problem");
    addTitle(s, "01 / PROBLEM", "Macro monitoring misses the decision gap", "The hard part is not drawing another AQI map. It is converting fragmented signals into a defensible, locality-level action case.");
    const cards = [
      [64, 226, "01", "Sparse local coverage", "City averages hide neighbourhood, village, roadside and industrial-corridor spikes.", C.red],
      [350, 226, "02", "Fragmented evidence", "Regulatory monitors, weather, satellite context and citizen reports rarely meet in one review trail.", C.amber],
      [636, 226, "03", "Unexpected spikes", "Forecasts fail when fires, dust, traffic or local activity create a sudden unobserved event.", C.teal],
      [922, 226, "04", "Action-accountability gap", "Authorities need owner, evidence, uncertainty and audit history—not an unexplained model score.", C.green],
    ];
    for (const [x, y, n, t, d, a] of cards) {
      addBox(s, x, y, 258, 330, C.panel, "rounded-xl");
      addCircle(s, x + 20, y + 20, 44, a, n, C.white, 14);
      addText(s, t, x + 20, y + 86, 218, 62, 22, C.ink, true);
      addText(s, d, x + 20, y + 160, 218, 126, 16, C.grey, false);
      addBox(s, x + 20, y + 300, 88, 5, a, "rounded-full");
    }
    addNotes(s, "Frame the problem as an operational evidence gap. AirSentinel targets locality-to-corridor coordination while keeping final decisions with accountable reviewers.");
  }

  // 3 — Working solution
  {
    const s = newSlide(presentation, 3, "Working flow", C.panel);
    addTitle(s, "02 / WORKING SOLUTION", "One evidence-to-action loop, with safety gates", "Every automated step can assist; none can declare a cause or trigger enforcement by itself.");
    const xs = [64, 294, 524, 754, 984];
    const items = [
      ["1", "Sense", "Regulatory/open monitors, weather, citizen text/photo/voice, satellite context", C.sky],
      ["2", "Validate", "Provenance, freshness, unit checks, coverage and consent/privacy controls", C.teal2],
      ["3", "Predict", "Conventional 1h / 3h / 4h forecasts plus residual anomaly detection", C.green],
      ["4", "Review", "Evidence bundle, uncertainty, recommended checks and assigned owner", C.amber],
      ["5", "Act & audit", "Human decision, case status, outcome record and model feedback", C.red],
    ];
    for (let i = 0; i < items.length; i++) {
      const [n, title, detail, accent] = items[i];
      addCircle(s, xs[i] + 72, 226, 58, accent, n, C.ink, 19);
      addText(s, title, xs[i], 304, 202, 32, 22, C.ink, true, "center");
      addText(s, detail, xs[i], 350, 202, 132, 14, C.grey, false, "center");
      if (i < items.length - 1) addBox(s, xs[i] + 194, 252, 48, 5, C.mist, "rounded-full");
    }
    addBox(s, 64, 540, 1120, 82, C.ink, "rounded-xl");
    addText(s, "AUTOMATION BOUNDARY", 88, 562, 190, 18, 11, C.sky, true);
    addText(s, "No automatic source attribution • No automatic enforcement • No official AQI claim from fallback data", 286, 555, 860, 34, 18, C.white, true);
    addNotes(s, "Demonstrate the complete loop. Stress that the guardrail is part of the product: forecasts and Gemini explanations are decision-support, not legal findings.");
  }

  // 4 — Data hierarchy
  {
    const s = newSlide(presentation, 4, "Data trust");
    addTitle(s, "03 / DATA TRUST", "Best available data—without disguising its authority", "A source hierarchy lets the prototype progress while preserving a clear boundary between official, trusted fallback and citizen evidence.");
    const rows = [
      ["A", "Official / approved", "CPCB / data.gov.in or authority-approved feeds", "Use for operational current state after credentials, terms and QA are confirmed", C.green],
      ["B", "Trusted fallback", "OpenAQ measurements + documented provenance", "Development, backfill and controlled evaluation—not relabelled as official", C.teal],
      ["C", "Context layers", "Open-Meteo, Earth Engine Sentinel-5P, Maps", "Weather, atmospheric and geographic context—not ground-truth replacement", C.sky],
      ["D", "Community evidence", "Firebase reports, photos, local sensors / purifiers", "Moderated supporting evidence with consent and device-quality metadata", C.amber],
    ];
    for (let i = 0; i < rows.length; i++) {
      const [rank, title, source, rule, accent] = rows[i];
      const y = 214 + i * 104;
      addCircle(s, 72, y + 12, 52, accent, rank, C.ink, 17);
      addText(s, title, 148, y, 242, 28, 20, C.ink, true);
      addText(s, source, 148, y + 34, 320, 44, 14, C.grey, false);
      addBox(s, 512, y, 672, 76, C.panel, "rounded-xl");
      addText(s, rule, 536, y + 18, 626, 43, 15, C.ink, false);
    }
    addNotes(s, "The official CPCB/data.gov.in route is the operational target. The current 182-day locality backfill is OpenAQ-derived fallback data and remains labelled as such. Community and satellite streams corroborate; they do not silently replace regulatory measurements.", [
      "https://www.data.gov.in/catalog/real-time-air-quality-index",
      "https://docs.openaq.org/resources/measurements",
      "https://docs.openaq.org/api",
    ]);
  }

  // 5 — Data improvement evidence
  {
    const s = newSlide(presentation, 5, "Data evidence", C.panel);
    addTitle(s, "04 / DATA IMPROVEMENT", "Two blocked Delhi localities now have 180+ day evidence", "The backfill is suitable for controlled conventional-model comparison. It is still fallback data—not a claim of official local coverage.");
    metricCard(s, 64, 214, 350, "Saved observations", "168,839", "Six-pollutant OpenAQ-derived records", C.teal);
    metricCard(s, 465, 214, 350, "Najafgarh PM2.5", "7,516 rows", "181.9 days • 86.1% • 2 stations", C.green);
    metricCard(s, 866, 214, 350, "Safdarjung PM2.5", "7,889 rows", "181.9 days • 90.4% • 2 stations", C.sky);
    addBox(s, 64, 382, 1152, 226, C.white, "rounded-xl", C.mist, 1);
    addText(s, "POLLUTANT COVERAGE", 88, 406, 220, 18, 11, C.grey, true);
    const pollutants = ["PM2.5", "PM10", "NO₂", "O₃", "SO₂", "CO"];
    for (let i = 0; i < pollutants.length; i++) {
      const x = 88 + i * 175;
      addBox(s, x, 452, 145, 58, i < 2 ? C.teal : C.light, "rounded-xl");
      addText(s, pollutants[i], x, 470, 145, 24, 17, i < 2 ? C.white : C.ink, true, "center");
    }
    addText(s, "Gate passed: long-history conventional comparison", 88, 544, 490, 22, 15, C.green, true);
    addText(s, "Still required: approved source, live freshness, unit QA and human operational sign-off", 602, 544, 570, 42, 14, C.red, true);
    addNotes(s, "Use these exact stored metrics. Explain the distinction between model-development readiness and operational readiness. Do not call this feed CPCB or official.", [
      "https://docs.openaq.org/resources/measurements",
      "https://www.data.gov.in/catalog/real-time-air-quality-index",
    ]);
  }

  // 6 — Forecast and anomaly guard
  {
    const s = newSlide(presentation, 6, "Forecast safeguards");
    addTitle(s, "05 / FORECASTING", "Forecast what is knowable; flag what is surprising", "AirSentinel combines short-horizon conventional models with residual-based anomaly review so a sudden spike becomes a case—not a silent failure.");
    node(s, 64, 218, 338, 250, "Forecast track", "1h • 3h • 4h", "Lagged pollutants + weather + time features. Models are evaluated chronologically and include empirical uncertainty intervals.", C.panel, C.teal);
    node(s, 471, 218, 338, 250, "Anomaly track", "Observed − expected", "Large robust residuals trigger an unexpected-spike review. Nearby stations, weather and moderated reports are requested.", C.panel, C.amber);
    node(s, 878, 218, 338, 250, "Decision track", "Human verification", "The case remains cause-unverified until corroborated. Recommended actions are checks, not automated enforcement.", C.panel, C.green);
    addBox(s, 64, 510, 1152, 98, C.ink, "rounded-xl");
    addText(s, "MODEL POLICY", 88, 532, 150, 18, 11, C.sky, true);
    addText(s, "Promote the best validated conventional baseline first. Do not present experimental deep or federated approaches as deployed capability.", 244, 526, 924, 46, 18, C.white, true);
    addNotes(s, "Show why an unexpected parali, dust or industrial spike is not a fatal failure: the residual creates a review case. The platform can suggest evidence to collect, but it cannot identify the true source without corroboration.");
  }

  // 7 — Google architecture
  {
    const s = newSlide(presentation, 7, "Google architecture", C.panel);
    addTitle(s, "06 / GOOGLE CLOUD", "Each required Google service has a real job", "The repository contains feature-gated adapters, security boundaries and deployment scripts. Account provisioning and live credentials remain owner actions.");
    const left = [
      ["Firebase", "Citizen report intake, auth and protected media metadata", C.amber],
      ["Maps + Earth Engine", "Locality context, corridors and Sentinel-5P atmospheric layers", C.sky],
      ["Speech + Translation", "Accessible multilingual reporting and read-back", C.green],
    ];
    const right = [
      ["BigQuery", "Provenance-aware analytical history and model input tables", C.teal],
      ["Gemini multimodal", "Guarded photo evidence summary and case explanation", C.lime],
      ["Cloud Run", "Private API + authority; separate public aggregate UI", C.red],
    ];
    addBox(s, 536, 246, 208, 208, C.ink, "rounded-xl");
    addText(s, "AIR", 536, 282, 208, 42, 30, C.sky, true, "center");
    addText(s, "SENTINEL", 536, 330, 208, 42, 30, C.white, true, "center");
    addText(s, "guarded orchestration", 536, 390, 208, 20, 11, C.mist, true, "center");
    for (let i = 0; i < 3; i++) {
      node(s, 64, 212 + i * 130, 404, 106, "INPUT / CONTEXT", left[i][0], left[i][1], C.white, left[i][2]);
      node(s, 812, 212 + i * 130, 404, 106, "DATA / AI / RUNTIME", right[i][0], right[i][1], C.white, right[i][2]);
      addBox(s, 476, 263 + i * 130, 52, 4, C.mist, "rounded-full");
      addBox(s, 752, 263 + i * 130, 52, 4, C.mist, "rounded-full");
    }
    addNotes(s, "The code paths are intentionally feature-gated. Cloud Run private authentication and Secret Manager references are part of the deployment scripts. Firebase rules deny direct client access until an approved schema and backend path are configured.", [
      "https://docs.cloud.google.com/run/docs/authenticating/overview",
      "https://docs.cloud.google.com/run/docs/configuring/services/secrets",
      "https://firebase.google.com/docs/rules/rules-and-auth",
      "https://ai.google.dev/gemini-api/docs/image-understanding",
      "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_NO2",
    ]);
  }

  // 8 — Citizen and accessibility
  {
    const s = newSlide(presentation, 8, "Citizen evidence");
    addTitle(s, "07 / CITIZEN EVIDENCE", "Accessible reporting—without turning people into unverified sensors", "Text, photo and voice reports support investigation when consent, moderation, privacy and device metadata travel with the evidence.");
    const cols = [
      [64, "REPORT", "Text • photo • voice", "Firebase Auth identifies the reporter. Exact contact details are redacted from analytical copies.", C.teal],
      [355, "UNDERSTAND", "Gemini • STT • Translation", "AI extracts a bounded summary and accessibility support. Unsafe or unavailable providers fail closed.", C.sky],
      [646, "CORROBORATE", "Sensors • weather • satellite", "A report gains weight only when timing, location and independent signals agree.", C.green],
      [937, "REVIEW", "Moderator • authority owner", "Human reviewers verify evidence, record uncertainty and choose the next check.", C.amber],
    ];
    for (const [x, k, title, detail, a] of cols) {
      addBox(s, x, 224, 247, 326, C.panel, "rounded-xl");
      addBox(s, x, 224, 247, 10, a, "rounded-xl");
      addText(s, k, x + 20, 254, 207, 18, 11, a, true);
      addText(s, title, x + 20, 292, 207, 66, 21, C.ink, true);
      addText(s, detail, x + 20, 378, 207, 118, 15, C.grey, false);
    }
    addText(s, "Citizen evidence can reveal a blind spot; it cannot by itself prove AQI, cause or culpability.", 64, 588, 1120, 32, 18, C.red, true, "center");
    addNotes(s, "Demonstrate the citizen app using sample data only. Emphasise consent, metadata, moderation and the distinction between evidence and an official measurement.", [
      "https://firebase.google.com/docs/rules/rules-and-auth",
      "https://ai.google.dev/gemini-api/docs/image-understanding",
      "https://docs.cloud.google.com/translate/docs/basic/translating-text",
    ]);
  }

  // 9 — Authority loop
  {
    const s = newSlide(presentation, 9, "Authority workflow", C.panel);
    addTitle(s, "08 / GOVERNMENT WORKFLOW", "A case queue built for accountable intervention", "Authority users see evidence quality, forecast uncertainty and recommended verification steps before they record any decision.");
    addBox(s, 64, 216, 1152, 340, C.white, "rounded-xl", C.mist, 1);
    const steps = [
      ["A", "Triage", "priority + locality + freshness", C.red],
      ["B", "Corroborate", "nearby station + weather + reports", C.amber],
      ["C", "Assign", "named owner + due time", C.teal],
      ["D", "Decide", "monitor / inspect / coordinate", C.green],
      ["E", "Close loop", "outcome + evidence + model feedback", C.sky],
    ];
    for (let i = 0; i < steps.length; i++) {
      const x = 94 + i * 220;
      const [n, title, detail, accent] = steps[i];
      addCircle(s, x + 50, 252, 54, accent, n, C.ink, 16);
      addText(s, title, x, 326, 154, 30, 19, C.ink, true, "center");
      addText(s, detail, x, 370, 154, 78, 13, C.grey, false, "center");
      if (i < steps.length - 1) addBox(s, x + 162, 278, 58, 4, C.mist, "rounded-full");
    }
    addPill(s, "PRIVATE IAM", 92, 494, 126, C.ink, C.sky, 11);
    addPill(s, "HUMAN REVIEW", 232, 494, 148, C.teal, C.white, 11);
    addPill(s, "AUDIT TRAIL", 394, 494, 126, C.green, C.ink, 11);
    addText(s, "Public dashboard = aggregate information only", 700, 500, 452, 22, 15, C.grey, true, "right");
    addNotes(s, "Use the authority dashboard as a private workflow demo. The production gate rejects unsafe configuration. The public dashboard is a different Cloud Run target with no authority privileges.", [
      "https://docs.cloud.google.com/run/docs/authenticating/overview",
      "https://docs.cloud.google.com/run/docs/configuring/services/secrets",
    ]);
  }

  // 10 — Verification and blockers
  {
    const s = newSlide(presentation, 10, "Readiness");
    addTitle(s, "09 / READINESS", "Built, verified and honest about what remains", "The package separates repository-complete work from account-bound deployment and approval tasks.");
    metricCard(s, 64, 214, 338, "Offline safety tests", "38 / 38", "Includes real ASGI request-boundary checks", C.green);
    metricCard(s, 471, 214, 338, "Locality horizons", "1h • 3h • 4h", "Chronological evaluation + intervals", C.teal);
    metricCard(s, 878, 214, 338, "Operational promotion", "0", "Until approved live data and review", C.red);
    addText(s, "REPOSITORY-COMPLETE", 64, 394, 400, 20, 11, C.teal, true);
    addText(s, "• data collectors and source hierarchy\n• citizen, public and authority apps\n• guarded Google adapters\n• Docker / Cloud Run deployment scripts\n• docs, runbook and submission artifacts", 64, 430, 500, 150, 16, C.ink, false);
    addText(s, "OWNER / ACCOUNT-BOUND", 664, 394, 400, 20, 11, C.red, true);
    addText(s, "• create billed GCP project and approved identities\n• provide CPCB/data.gov access and secrets\n• enable APIs, deploy Cloud Run and test URLs\n• push GitHub repository\n• record the 3–5 minute demo", 664, 430, 500, 150, 16, C.ink, false);
    addNotes(s, "Be explicit: no public Cloud Run URL is claimed in this package, no CPCB snapshot was collected without credentials, and no experimental model is promoted. This honesty strengthens the evaluation.");
  }

  // 11 — Submission and close
  {
    const s = newSlide(presentation, 11, "Submission", C.ink);
    addText(s, "READY FOR THE FINAL MILE", 64, 54, 520, 22, 12, C.sky, true);
    addText(s, "A practical clean-air\ndecision-support system", 64, 104, 700, 120, 44, C.white, true);
    addText(s, "Locality evidence. Short-horizon warning. Human-reviewed government action.", 64, 250, 700, 70, 23, C.mist, false);
    const items = [
      ["1", "Connect approved data", "CPCB/data.gov or authority feed"],
      ["2", "Deploy securely", "private API + authority, public aggregate UI"],
      ["3", "Submit", "GitHub • demo video • 10–12 slide deck • link"],
    ];
    for (let i = 0; i < items.length; i++) {
      const y = 370 + i * 82;
      addCircle(s, 68, y, 44, i === 0 ? C.green : i === 1 ? C.teal2 : C.amber, items[i][0], C.ink, 14);
      addText(s, items[i][1], 132, y - 2, 270, 24, 18, C.white, true);
      addText(s, items[i][2], 420, y - 2, 450, 28, 15, C.sky, false);
    }
    addBox(s, 930, 90, 250, 470, C.navy, "rounded-xl");
    addText(s, "THE PROMISE", 960, 126, 190, 20, 11, C.sky, true, "center");
    addText(s, "Faster\nlocal evidence", 960, 190, 190, 94, 30, C.white, true, "center");
    addBox(s, 974, 320, 162, 4, C.teal2, "rounded-full");
    addText(s, "Safer\nautomation", 960, 356, 190, 82, 27, C.lime, true, "center");
    addText(s, "More accountable\nclimate action", 960, 474, 190, 50, 16, C.mist, true, "center");
    addText(s, "AIRSentinel  /  Sustainability  /  2026", 64, 676, 460, 20, 11, C.sky, true);
    addNotes(s, "Close with the system promise: improve the speed and quality of local evidence while keeping accountability with authorities. Invite judges to follow the live demo path in the runbook.");
  }

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await writeBlob(path.join(OUT_DIR, `${stem}.png`), png);
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(OUT_DIR, `${stem}.layout.json`), await layout.text());
  }

  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await writeBlob(path.join(OUT_DIR, "deck-montage.webp"), montage);
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(PPTX_PATH);
  console.log(`Created ${PPTX_PATH}`);
  console.log(`Rendered ${presentation.slides.items.length} slides to ${OUT_DIR}`);
}

buildDeck().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

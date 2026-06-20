'use strict';

const AR_OPTIONS = [
  "Both A and R are true, and R is the correct explanation of A",
  "Both A and R are true, but R is NOT the correct explanation of A",
  "A is true, but R is false",
  "A is false, but R is true",
  "Both A and R are false"
];

const app = document.getElementById('app');
const backBtn = document.getElementById('backBtn');
const titleEl = document.getElementById('appTitle');
const themeBtn = document.getElementById('themeBtn');

let CATALOG = null;
let currentChapter = null;
let activeTab = 'notes';
let viewMode = 'catalog'; /* catalog | harrison | hot_topic | case_report | clinical_trial */

/* ---------- theme ---------- */
(function initTheme(){
  const saved = localStorage.getItem('endo_theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
})();
themeBtn.addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', cur);
  localStorage.setItem('endo_theme', cur);
});

backBtn.addEventListener('click', () => {
  if (viewMode === 'catalog') return;
  showCatalog();
});

/* ---------- utils ---------- */
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function el(html){ const t=document.createElement('template'); t.innerHTML=html.trim(); return t.content.firstElementChild; }

async function loadJSON(path){
  const r = await fetch(path + '?_=' + Date.now());
  if (!r.ok) throw new Error('Failed to load ' + path);
  return r.json();
}

/* ---------- boot ---------- */
(async function boot(){
  try {
    CATALOG = await loadJSON('data/index.json');
    titleEl.textContent = CATALOG.title || "Endocrinology Master";
    showCatalog();
  } catch (e){
    app.innerHTML = '<div class="empty">Could not load catalog.<br><small>'+esc(e.message)+'</small><br><br>Serve this folder over http (e.g. <code>python3 -m http.server</code>) rather than opening the file directly.</div>';
  }
})();

/* ---------- catalog view ---------- */
async function loadContentCounts(entries){
  const counts = {};
  const ready = entries.filter(ch => ch.status === 'ready' && ch.file);
  await Promise.all(ready.map(async ch => {
    try {
      const data = await loadJSON('data/' + ch.file);
      const items = data.items || [];
      counts[ch.id] = {
        notes: items.filter(i=>i.type==='note').length,
        mcq: items.filter(i=>i.type==='mcq').length,
        tf: items.filter(i=>i.type==='true_false').length,
        ar: items.filter(i=>i.type==='assertion_reason').length,
        why: items.filter(i=>i.type==='why').length,
        how: items.filter(i=>i.type==='how').length,
        total: items.length
      };
    } catch(e){ counts[ch.id] = null; }
  }));
  return counts;
}

async function loadTrialCounts(entries){
  const counts = {};
  const ready = entries.filter(ch => ch.status === 'ready' && ch.file);
  await Promise.all(ready.map(async ch => {
    try {
      const data = await loadJSON('data/' + ch.file);
      const items = data.items || [];
      counts[ch.id] = {
        notes: items.filter(i=>i.type==='note').length,
        inclusion: (data.inclusionCriteria||[]).length,
        exclusion: (data.exclusionCriteria||[]).length,
        takeaways: (data.keyTakeaways||[]).length,
        mcq: items.filter(i=>i.type==='mcq').length,
        why: items.filter(i=>i.type==='why').length,
        how: items.filter(i=>i.type==='how').length,
        total: items.length + (data.inclusionCriteria||[]).length + (data.exclusionCriteria||[]).length + (data.keyTakeaways||[]).length
      };
    } catch(e){ counts[ch.id] = null; }
  }));
  return counts;
}

async function showCatalog(){
  currentChapter = null;
  viewMode = 'catalog';
  backBtn.hidden = true;
  titleEl.textContent = CATALOG.title || "Endocrinology Master";
  window.scrollTo(0,0);

  const hotTopics = CATALOG.hotTopics?.topics || [];
  const caseReports = CATALOG.caseReports?.reports || [];
  const trials = CATALOG.trials?.entries || [];

  if (!CATALOG._counts){
    app.innerHTML = '<div class="loading">Loading catalog…</div>';
    CATALOG._counts = {};
    const allChapters = CATALOG.sections.flatMap(s => s.chapters);
    const ready = allChapters.filter(ch => ch.status === 'ready' && ch.file);
    await Promise.all(ready.map(async ch => {
      try {
        const data = await loadJSON('data/' + ch.file);
        const items = data.items || [];
        CATALOG._counts[ch.id] = {
          notes: items.filter(i=>i.type==='note').length,
          mcq: items.filter(i=>i.type==='mcq').length,
          tf: items.filter(i=>i.type==='true_false').length,
          ar: items.filter(i=>i.type==='assertion_reason').length,
          why: 0,
          how: 0,
          total: items.length
        };
      } catch(e){ CATALOG._counts[ch.id] = null; }
    }));
    CATALOG._hotCounts = await loadContentCounts(hotTopics);
    CATALOG._caseCounts = await loadContentCounts(caseReports);
    CATALOG._trialCounts = await loadTrialCounts(trials);
  }

  const allChapters = CATALOG.sections.flatMap(s => s.chapters);
  const readyChapters = allChapters.filter(ch => ch.status === 'ready' && ch.file);
  const pendingChapters = allChapters.filter(ch => !(ch.status === 'ready' && ch.file));
  const total = allChapters.length;
  const pct = total ? Math.round(100 * readyChapters.length / total) : 0;
  const nextUp = pendingChapters[0];

  const totals = readyChapters.reduce((acc, ch) => {
    const c = CATALOG._counts[ch.id];
    if (c){ acc.notes+=c.notes; acc.mcq+=c.mcq; acc.tf+=c.tf; acc.ar+=c.ar; acc.items+=c.total; }
    return acc;
  }, {notes:0, mcq:0, tf:0, ar:0, items:0});

  let html = '<div class="intro-card">Clinically-focused MCQs (diagnosis, management &amp; treatment), chapter notes, true/false and assertion–reason questions — each linked to the source text. <b>Comprehensive study database.</b></div>';

  /* Hot Topics section */
  if (CATALOG.hotTopics){
    const ht = CATALOG.hotTopics;
    const htReady = hotTopics.filter(t => t.status === 'ready' && t.file);
    const htTotals = htReady.reduce((acc, t) => {
      const c = CATALOG._hotCounts?.[t.id];
      if (c){ acc.notes+=c.notes; acc.mcq+=c.mcq; acc.tf+=c.tf; acc.ar+=c.ar; acc.items+=c.total; }
      return acc;
    }, {notes:0, mcq:0, tf:0, ar:0, items:0});

    html += `<div class="hot-topics-banner">
      <div class="hot-topics-title">🔥 ${esc(ht.title || 'Hot Topics')}</div>
      <div class="hot-topics-desc">${esc(ht.description || '')}</div>
      ${htTotals.items ? `<div class="hot-topics-totals">${htTotals.items} items — ${htTotals.notes} notes · ${htTotals.mcq} MCQs · ${htTotals.tf} T/F · ${htTotals.ar} A-R</div>` : ''}
    </div>`;

    html += `<div class="section-head hot-section-head">
      <span class="section-arrow">▾</span>
      <span class="section-name">${esc(ht.title || 'Hot Topics')}</span>
      <span class="section-count">${htReady.length}/${hotTopics.length}</span>
    </div>`;
    html += `<div class="section-body">`;
    for (const t of hotTopics){
      const ready = t.status === 'ready' && t.file;
      const pill = ready ? '<span class="pill ready">ready</span>' : '<span class="pill pending">pending</span>';
      const c = ready ? CATALOG._hotCounts?.[t.id] : null;
      const sub = ready
        ? (c ? `${c.total} items · ${c.notes}N / ${c.mcq}Q / ${c.tf}T / ${c.ar}A` : 'Tap to study')
        : 'Awaiting authoring';
      html += `<div class="chap-card hot-card ${ready?'':'disabled'}" data-file="${ready?esc(t.file):''}" data-kind="hot">
        <div class="chap-no hot-icon">🔥</div>
        <div class="chap-meta">
          <div class="chap-title">${esc(t.title)} ${pill}</div>
          <div class="chap-sub">${esc(t.subtitle||t.category||'')}${sub ? ' · '+sub : ''}</div>
        </div>
      </div>`;
    }
    html += `</div>`;
  }

  /* Case Reports section */
  if (CATALOG.caseReports){
    const cr = CATALOG.caseReports;
    const crReady = caseReports.filter(r => r.status === 'ready' && r.file);
    const crTotals = crReady.reduce((acc, r) => {
      const c = CATALOG._caseCounts?.[r.id];
      if (c){ acc.notes+=c.notes; acc.mcq+=c.mcq; acc.tf+=c.tf; acc.ar+=c.ar; acc.why+=c.why; acc.how+=c.how; acc.items+=c.total; }
      return acc;
    }, {notes:0, mcq:0, tf:0, ar:0, why:0, how:0, items:0});

    html += `<div class="case-reports-banner">
      <div class="case-reports-title">📋 ${esc(cr.title || 'Case Reports')}</div>
      <div class="case-reports-desc">${esc(cr.description || '')}</div>
      ${crTotals.items ? `<div class="case-reports-totals">${crTotals.items} items — ${crTotals.notes} notes · ${crTotals.mcq} MCQs · ${crTotals.tf} T/F · ${crTotals.ar} A-R · ${crTotals.why} Why · ${crTotals.how} How</div>` : ''}
    </div>`;

    html += `<div class="section-head case-section-head">
      <span class="section-arrow">▾</span>
      <span class="section-name">${esc(cr.title || 'Case Reports')}</span>
      <span class="section-count">${crReady.length}/${caseReports.length}</span>
    </div>`;
    html += `<div class="section-body">`;
    for (const r of caseReports){
      const ready = r.status === 'ready' && r.file;
      const pill = ready ? '<span class="pill ready">ready</span>' : '<span class="pill pending">pending</span>';
      const c = ready ? CATALOG._caseCounts?.[r.id] : null;
      const sub = ready
        ? (c ? `${c.total} items · ${c.notes}N / ${c.mcq}Q / ${c.tf}T / ${c.ar}A / ${c.why}W / ${c.how}H` : 'Tap to study')
        : 'Awaiting authoring';
      html += `<div class="chap-card case-card ${ready?'':'disabled'}" data-file="${ready?esc(r.file):''}" data-kind="case">
        <div class="chap-no case-icon">📋</div>
        <div class="chap-meta">
          <div class="chap-title">${esc(r.title)} ${pill}</div>
          <div class="chap-sub">${esc(r.subtitle||r.category||'')}${sub ? ' · '+sub : ''}</div>
        </div>
      </div>`;
    }
    html += `</div>`;
  }

  /* Trials section */
  if (CATALOG.trials){
    const tr = CATALOG.trials;
    const trReady = trials.filter(t => t.status === 'ready' && t.file);
    const trTotals = trReady.reduce((acc, t) => {
      const c = CATALOG._trialCounts?.[t.id];
      if (c){
        acc.notes+=c.notes; acc.inclusion+=c.inclusion; acc.exclusion+=c.exclusion;
        acc.takeaways+=c.takeaways; acc.mcq+=c.mcq; acc.why+=c.why; acc.how+=c.how; acc.items+=c.total;
      }
      return acc;
    }, {notes:0, inclusion:0, exclusion:0, takeaways:0, mcq:0, why:0, how:0, items:0});

    html += `<div class="trials-banner">
      <div class="trials-title">📊 ${esc(tr.title || 'Trials')}</div>
      <div class="trials-desc">${esc(tr.description || '')}</div>
      ${trTotals.items ? `<div class="trials-totals">${trTotals.items} items — ${trTotals.notes} notes · ${trTotals.inclusion} incl · ${trTotals.exclusion} excl · ${trTotals.takeaways} takeaways · ${trTotals.mcq} MCQs · ${trTotals.why} Why · ${trTotals.how} How</div>` : ''}
    </div>`;

    html += `<div class="section-head trial-section-head">
      <span class="section-arrow">▾</span>
      <span class="section-name">${esc(tr.title || 'Trials')}</span>
      <span class="section-count">${trReady.length}/${trials.length}</span>
    </div>`;
    html += `<div class="section-body">`;
    for (const t of trials){
      const ready = t.status === 'ready' && t.file;
      const pill = ready ? '<span class="pill ready">ready</span>' : '<span class="pill pending">pending</span>';
      const c = ready ? CATALOG._trialCounts?.[t.id] : null;
      const sub = ready
        ? (c ? `${c.total} items · ${c.notes}N / ${c.mcq}Q / ${c.why}W / ${c.how}H` : 'Tap to study')
        : 'Awaiting authoring';
      html += `<div class="chap-card trial-card ${ready?'':'disabled'}" data-file="${ready?esc(t.file):''}" data-kind="trial">
        <div class="chap-no trial-icon">📊</div>
        <div class="chap-meta">
          <div class="chap-title">${esc(t.title)} ${pill}</div>
          <div class="chap-sub">${esc(t.subtitle||t.category||'')}${sub ? ' · '+sub : ''}</div>
        </div>
      </div>`;
    }
    html += `</div>`;
  }

  html += `<div class="harrison-divider"><span>Endocrinology Chapters</span></div>`;

  html += `<div class="progress-card">
    <div class="progress-stats">
      <div class="stat"><span class="stat-num">${readyChapters.length}</span><span class="stat-label">Ready</span></div>
      <div class="stat"><span class="stat-num">${pendingChapters.length}</span><span class="stat-label">Pending</span></div>
      <div class="stat"><span class="stat-num">${pct}%</span><span class="stat-label">Complete</span></div>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
    <div class="progress-totals">${totals.items} items authored — ${totals.notes} notes · ${totals.mcq} MCQs · ${totals.tf} T/F · ${totals.ar} A-R</div>
    ${nextUp ? `<div class="next-up">Next up: <b>Ch ${esc(nextUp.no||'')} — ${esc(nextUp.title)}</b> <span class="next-id">(${esc(nextUp.id)})</span></div>` : '<div class="next-up done">All chapters ready 🎉</div>'}
  </div>`;

  for (const sec of CATALOG.sections){
    const readyCount = sec.chapters.filter(ch => ch.status === 'ready' && ch.file).length;
    const hasNext = nextUp && sec.chapters.some(ch => ch.id === nextUp.id);
    const expanded = readyCount > 0 || hasNext;
    html += `<div class="section-head${expanded?'':' collapsed'}" data-toggle>
      <span class="section-arrow">▾</span>
      <span class="section-name">${esc(sec.name)}</span>
      <span class="section-count">${readyCount}/${sec.chapters.length}</span>
    </div>`;
    html += `<div class="section-body"${expanded?'':' hidden'}>`;
    for (const ch of sec.chapters){
      const ready = ch.status === 'ready' && ch.file;
      const isNext = nextUp && ch.id === nextUp.id;
      const pill = ready ? '<span class="pill ready">ready</span>' : (isNext ? '<span class="pill next">next up</span>' : '<span class="pill pending">pending</span>');
      const c = ready ? CATALOG._counts[ch.id] : null;
      const sub = ready
        ? (c ? `${c.total} items · ${c.notes}N / ${c.mcq}Q / ${c.tf}T / ${c.ar}A` : 'Tap to study')
        : (isNext ? 'Author next — see standing workflow' : 'Awaiting authoring');
      html += `<div class="chap-card ${ready?'':'disabled'}${isNext?' next-card':''}" data-file="${ready?esc(ch.file):''}">
        <div class="chap-no">${esc(ch.no||'')}</div>
        <div class="chap-meta">
          <div class="chap-title">${esc(ch.title)} ${pill}</div>
          <div class="chap-sub">${sub}</div>
        </div>
      </div>`;
    }
    html += `</div>`;
  }
  app.innerHTML = html;
  app.querySelectorAll('.chap-card:not(.disabled)').forEach(card => {
    card.addEventListener('click', () => {
      const kind = card.dataset.kind || 'harrison';
      openChapter(card.dataset.file, kind);
    });
  });
  app.querySelectorAll('.section-head').forEach(head => {
    head.addEventListener('click', () => {
      head.classList.toggle('collapsed');
      head.nextElementSibling.hidden = head.classList.contains('collapsed');
    });
  });
}

/* ---------- chapter / topic view ---------- */
async function openChapter(file, kind){
  app.innerHTML = '<div class="loading">Loading…</div>';
  try {
    currentChapter = await loadJSON('data/' + file);
  } catch(e){
    app.innerHTML = '<div class="empty">Could not load content.</div>';
    return;
  }
  viewMode = kind === 'hot' ? 'hot_topic' : (kind === 'case' ? 'case_report' : (kind === 'trial' ? 'clinical_trial' : 'harrison'));
  backBtn.hidden = false;
  backBtn.textContent = viewMode === 'hot_topic' ? '‹ Hot Topics' : (viewMode === 'case_report' ? '‹ Case Reports' : (viewMode === 'clinical_trial' ? '‹ Trials' : '‹ Chapters'));
  activeTab = 'notes';
  renderChapter();
  window.scrollTo(0,0);
}

function trialCounts(){
  const ch = currentChapter;
  const c = ch.items || [];
  return {
    notes: c.filter(i=>i.type==='note').length,
    inclusion: (ch.inclusionCriteria||[]).length,
    exclusion: (ch.exclusionCriteria||[]).length,
    takeaways: (ch.keyTakeaways||[]).length,
    mcq: c.filter(i=>i.type==='mcq').length,
    tf: c.filter(i=>i.type==='true_false').length,
    ar: c.filter(i=>i.type==='assertion_reason').length,
    why: c.filter(i=>i.type==='why').length,
    how: c.filter(i=>i.type==='how').length
  };
}

function counts(){
  const c = currentChapter.items;
  return {
    notes: c.filter(i=>i.type==='note').length,
    mcq: c.filter(i=>i.type==='mcq').length,
    tf: c.filter(i=>i.type==='true_false').length,
    ar: c.filter(i=>i.type==='assertion_reason').length,
    why: c.filter(i=>i.type==='why').length,
    how: c.filter(i=>i.type==='how').length
  };
}

function renderCaseDescription(ch){
  const p = ch.patient || {};
  let patientBlock = '';
  if (p.age || p.sex || p.chiefComplaint){
    patientBlock = `<div class="case-patient-grid">
      ${p.age ? `<div class="case-patient-item"><span class="case-label">Age</span>${esc(String(p.age))}</div>` : ''}
      ${p.sex ? `<div class="case-patient-item"><span class="case-label">Sex</span>${esc(p.sex)}</div>` : ''}
      ${p.chiefComplaint ? `<div class="case-patient-item wide"><span class="case-label">Chief Complaint</span>${esc(p.chiefComplaint)}</div>` : ''}
      ${p.pmh?.length ? `<div class="case-patient-item wide"><span class="case-label">PMH</span>${esc(p.pmh.join('; '))}</div>` : ''}
      ${p.medications?.length ? `<div class="case-patient-item wide"><span class="case-label">Medications</span>${esc(p.medications.join('; '))}</div>` : ''}
    </div>`;
  }
  let findings = '';
  if (ch.keyFindings?.length){
    findings = '<div class="case-findings"><div class="case-label">Key Findings</div><ul>'+
      ch.keyFindings.map(f=>'<li>'+esc(f)+'</li>').join('')+'</ul></div>';
  }
  let dx = ch.finalDiagnosis ? `<div class="case-diagnosis"><span class="case-label">Final Diagnosis</span>${esc(ch.finalDiagnosis)}</div>` : '';
  let objectives = '';
  if (ch.learningObjectives?.length){
    objectives = '<div class="case-objectives"><div class="case-label">Learning Objectives</div><ul>'+
      ch.learningObjectives.map(o=>'<li>'+esc(o)+'</li>').join('')+'</ul></div>';
  }
  return `<div class="case-description-block">
    <div class="case-badge">📋 Case Description</div>
    ${patientBlock}
    <div class="case-narrative">${esc(ch.caseDescription||'')}</div>
    ${findings}
    ${dx}
    ${objectives}
  </div>`;
}

function renderTrialSummary(ch){
  const d = ch.trialDesign || {};
  let meta = '';
  if (d.year || d.design || d.sampleSize){
    meta = `<div class="trial-meta-grid">
      ${d.year ? `<div class="trial-meta-item"><span class="trial-label">Year</span>${esc(String(d.year))}</div>` : ''}
      ${d.design ? `<div class="trial-meta-item wide"><span class="trial-label">Design</span>${esc(d.design)}</div>` : ''}
      ${d.sampleSize ? `<div class="trial-meta-item wide"><span class="trial-label">Sample Size</span>${esc(d.sampleSize)}</div>` : ''}
      ${d.duration ? `<div class="trial-meta-item"><span class="trial-label">Duration</span>${esc(d.duration)}</div>` : ''}
      ${d.intervention ? `<div class="trial-meta-item wide"><span class="trial-label">Intervention</span>${esc(d.intervention)}</div>` : ''}
      ${d.comparator ? `<div class="trial-meta-item wide"><span class="trial-label">Comparator</span>${esc(d.comparator)}</div>` : ''}
      ${d.primaryEndpoint ? `<div class="trial-meta-item wide"><span class="trial-label">Primary Endpoint</span>${esc(d.primaryEndpoint)}</div>` : ''}
    </div>`;
  }
  return `<div class="trial-summary-block">
    <div class="trial-badge">📊 Trial Summary</div>
    ${d.fullName ? `<div class="trial-full-name">${esc(d.fullName)}</div>` : ''}
    ${d.overview ? `<div class="trial-overview">${esc(d.overview)}</div>` : ''}
    ${meta}
  </div>`;
}

function renderCriteriaList(title, items, cssClass){
  if (!items?.length) return '';
  return `<div class="trial-criteria-block ${cssClass}">
    <div class="trial-label">${esc(title)}</div>
    <ul>${items.map(i=>'<li>'+esc(i)+'</li>').join('')}</ul>
  </div>`;
}

function renderChapter(){
  const ch = currentChapter;
  const isHot = ch.topicType === 'hot_topic' || viewMode === 'hot_topic';
  const isCase = ch.reportType === 'case_report' || viewMode === 'case_report';
  const isTrial = ch.trialType === 'clinical_trial' || viewMode === 'clinical_trial';
  titleEl.textContent = isTrial ? (ch.title || 'Trial') : (isCase ? (ch.title || 'Case Report') : (isHot ? (ch.title || 'Hot Topic') : ('Ch ' + (ch.chapterNo||''))));
  const n = isTrial ? trialCounts() : counts();
  const tab = (id,label,cnt)=>`<button class="tab ${activeTab===id?'active':''}" data-tab="${id}">${label}<br><span class="cnt">${cnt}</span></button>`;

  const byline = isTrial
    ? `${esc(ch.section||'Trials')}${ch.category?' · '+esc(ch.category):''}${ch.authors?' · '+esc(ch.authors):''}`
    : isCase
    ? `${esc(ch.section||'Case Reports')}${ch.category?' · '+esc(ch.category):''}${ch.authors?' · '+esc(ch.authors):''}`
    : isHot
    ? `${esc(ch.section||'Hot Topics')}${ch.category?' · '+esc(ch.category):''}${ch.authors?' · '+esc(ch.authors):''}`
    : `Chapter ${esc(ch.chapterNo||'')} · ${esc(ch.section||'')}${ch.authors?' · '+esc(ch.authors):''}`;

  let html = `<div class="chap-header${isHot?' hot-header':''}${isCase?' case-header':''}${isTrial?' trial-header':''}">
      ${isHot ? '<div class="hot-badge">🔥 Hot Topic</div>' : ''}
      ${isCase ? '<div class="case-badge-inline">📋 Case Report</div>' : ''}
      ${isTrial ? '<div class="trial-badge-inline">📊 Clinical Trial</div>' : ''}
      <h2>${esc(ch.title)}</h2>
      ${ch.subtitle ? `<div class="chap-subtitle">${esc(ch.subtitle)}</div>` : ''}
      <div class="by">${byline}</div>
    </div>
    ${isCase ? renderCaseDescription(ch) : ''}
    ${isTrial ? renderTrialSummary(ch) : ''}
    <div class="tabs${isCase||isTrial||(n.why||n.how)?' tabs-scroll':''}">
      ${tab('notes','Notes',n.notes)}
      ${isTrial ? tab('inclusion','Inclusion',n.inclusion)+tab('exclusion','Exclusion',n.exclusion)+tab('takeaways','Takeaways',n.takeaways) : ''}
      ${tab('mcq','MCQs',n.mcq)}
      ${!isTrial ? tab('tf','True/False',n.tf)+tab('ar','Assertion–Reason',n.ar) : ''}
      ${(n.why || n.how) ? tab('why','Why',n.why)+tab('how','How',n.how) : ''}
    </div>
    <div id="tabBody"></div>`;
  app.innerHTML = html;
  app.querySelectorAll('.tab').forEach(t => t.addEventListener('click', ()=>{ activeTab=t.dataset.tab; renderChapter(); }));
  renderTab();
}

function renderTab(){
  const body = document.getElementById('tabBody');
  const items = currentChapter.items;
  let list, html='';
  if (activeTab==='notes'){
    list = items.filter(i=>i.type==='note');
    html = list.map(renderNote).join('') || emptyMsg();
    body.innerHTML = html;
    wireSkepticismToggles(body);
    return;
  } else if (activeTab==='inclusion'){
    html = renderCriteriaList('Inclusion Criteria', currentChapter.inclusionCriteria, 'inclusion-criteria') || emptyMsg();
    body.innerHTML = html;
    return;
  } else if (activeTab==='exclusion'){
    html = renderCriteriaList('Exclusion Criteria', currentChapter.exclusionCriteria, 'exclusion-criteria') || emptyMsg();
    body.innerHTML = html;
    return;
  } else if (activeTab==='takeaways'){
    const tk = currentChapter.keyTakeaways || [];
    html = tk.length
      ? `<div class="trial-takeaways-block">${tk.map((t,i)=>`<div class="note trial-takeaway"><div class="q-top"><span class="q-type">Takeaway ${i+1}</span></div><div class="body">${esc(t)}</div></div>`).join('')}</div>`
      : emptyMsg();
    body.innerHTML = html;
    return;
  } else if (activeTab==='mcq'){
    list = items.filter(i=>i.type==='mcq');
    html = list.map((q,i)=>renderMCQ(q,i+1)).join('') || emptyMsg();
  } else if (activeTab==='tf'){
    list = items.filter(i=>i.type==='true_false');
    html = list.map((q,i)=>renderTF(q,i+1)).join('') || emptyMsg();
  } else if (activeTab==='why'){
    list = items.filter(i=>i.type==='why');
    html = list.map((q,i)=>renderWhyHow(q,i+1,'Why')).join('') || emptyMsg();
  } else if (activeTab==='how'){
    list = items.filter(i=>i.type==='how');
    html = list.map((q,i)=>renderWhyHow(q,i+1,'How')).join('') || emptyMsg();
  } else {
    list = items.filter(i=>i.type==='assertion_reason');
    html = list.map((q,i)=>renderAR(q,i+1)).join('') || emptyMsg();
  }
  body.innerHTML = html;
  wireQuestions(body);
}

function emptyMsg(){ return '<div class="empty">No items in this section yet.</div>'; }

function refBlock(ref){
  if(!ref) return '';
  return `<div class="ref"><span class="ref-h">Source</span>${esc(ref)}</div>`;
}

const SKEPTICISM_SUBTOPIC = 'Skepticism — Needs Verification';

function verifiedKey(noteId){ return 'h22_verified::' + (currentChapter?.id||'') + '::' + noteId; }
function isVerified(noteId){ return localStorage.getItem(verifiedKey(noteId)) === '1'; }

function renderNote(nte){
  let kp = '';
  if (nte.keyPoints && nte.keyPoints.length){
    kp = '<div class="kp"><div class="kp-h">Key clinical points</div><ul>'+
      nte.keyPoints.map(k=>'<li>'+esc(k)+'</li>').join('')+'</ul></div>';
  }
  const isSkeptic = nte.subtopic === SKEPTICISM_SUBTOPIC;
  let skepticBlock = '';
  if (isSkeptic){
    const verified = isVerified(nte.id);
    skepticBlock = `<div class="skeptic-toggle" data-note-id="${esc(nte.id)}">
      <label class="skeptic-check">
        <input type="checkbox" ${verified?'checked':''}>
        <span class="skeptic-badge ${verified?'verified':'unverified'}">${verified ? '✓ Verified' : '⚠ Needs Verification'}</span>
      </label>
    </div>`;
  }
  return `<div class="note${isSkeptic?' skeptic-note':''}">
    <div class="sub">${esc(nte.subtopic||'')}</div>
    ${skepticBlock}
    <h3>${esc(nte.title||'')}</h3>
    <div class="body">${esc(nte.content||'')}</div>
    ${kp}
    ${refBlock(nte.reference)}
  </div>`;
}

function wireSkepticismToggles(scope){
  scope.querySelectorAll('.skeptic-toggle').forEach(toggle => {
    const noteId = toggle.dataset.noteId;
    const checkbox = toggle.querySelector('input[type="checkbox"]');
    const badge = toggle.querySelector('.skeptic-badge');
    checkbox.addEventListener('change', () => {
      const verified = checkbox.checked;
      localStorage.setItem(verifiedKey(noteId), verified ? '1' : '0');
      badge.textContent = verified ? '✓ Verified' : '⚠ Needs Verification';
      badge.classList.toggle('verified', verified);
      badge.classList.toggle('unverified', !verified);
    });
  });
}

function renderMCQ(q, idx){
  const opts = q.options.map((o,i)=>
    `<button class="opt" data-i="${i}"><span class="key">${String.fromCharCode(65+i)}.</span>${esc(o)}</button>`).join('');
  const img = q.image ? `<figure class="q-figure"><img class="q-image" src="${esc(q.image)}" alt="${esc(q.imageAlt||'Clinical reference image')}"><figcaption class="q-caption">${esc(q.imageCaption||q.imageAlt||'')}</figcaption></figure>` : '';
  return `<div class="q" data-correct="${q.correctOption}" data-type="mcq">
    <div class="q-top"><span class="q-type">MCQ ${idx}</span><span class="q-sub">${esc(q.subtopic||'')}</span></div>
    ${img}
    <div class="q-stem">${esc(q.question)}</div>
    <div class="opts">${opts}</div>
    <div class="explain"><div class="verdict"></div><div class="exp-text">${esc(q.explanation||'')}</div>${refBlock(q.reference)}</div>
  </div>`;
}

function renderTF(q, idx){
  const correctIdx = q.correctAnswer === true ? 0 : 1;
  return `<div class="q" data-correct="${correctIdx}" data-type="tf">
    <div class="q-top"><span class="q-type">True / False ${idx}</span><span class="q-sub">${esc(q.subtopic||'')}</span></div>
    <div class="q-stem">${esc(q.statement)}</div>
    <div class="tf-row">
      <button class="opt" data-i="0"><span class="key">T</span>True</button>
      <button class="opt" data-i="1"><span class="key">F</span>False</button>
    </div>
    <div class="explain"><div class="verdict"></div><div class="exp-text">${esc(q.explanation||'')}</div>${refBlock(q.reference)}</div>
  </div>`;
}

function renderWhyHow(q, idx, label){
  let kp = '';
  if (q.keyPoints && q.keyPoints.length){
    kp = '<div class="kp"><div class="kp-h">Key clinical points</div><ul>'+
      q.keyPoints.map(k=>'<li>'+esc(k)+'</li>').join('')+'</ul></div>';
  }
  return `<div class="note why-how-note${viewMode==='clinical_trial'?' trial-why-how':''}">
    <div class="q-top"><span class="q-type">${esc(label)} ${idx}</span><span class="q-sub">${esc(q.subtopic||'')}</span></div>
    <h3>${esc(q.question||'')}</h3>
    <div class="body why-how-answer"><span class="why-how-label">Answer:</span> ${esc(q.answer||'')}</div>
    ${kp}
    ${refBlock(q.reference)}
  </div>`;
}

function renderAR(q, idx){
  const opts = AR_OPTIONS.map((o,i)=>
    `<button class="opt" data-i="${i}"><span class="key">${String.fromCharCode(65+i)}.</span>${esc(o)}</button>`).join('');
  return `<div class="q" data-correct="${q.correctOption}" data-type="ar">
    <div class="q-top"><span class="q-type">Assertion–Reason ${idx}</span><span class="q-sub">${esc(q.subtopic||'')}</span></div>
    <div class="ar-block">
      <div class="ar-line"><b>Assertion (A):</b> ${esc(q.assertion)}</div>
      <div class="ar-line"><b>Reason (R):</b> ${esc(q.reason)}</div>
    </div>
    <div class="opts">${opts}</div>
    <div class="explain"><div class="verdict"></div><div class="exp-text">${esc(q.explanation||'')}</div>${refBlock(q.reference)}</div>
  </div>`;
}

function wireQuestions(scope){
  scope.querySelectorAll('.q').forEach(qEl => {
    const correct = parseInt(qEl.dataset.correct, 10);
    const optEls = qEl.querySelectorAll('.opt');
    optEls.forEach(opt => {
      opt.addEventListener('click', () => {
        if (qEl.dataset.answered) return;
        qEl.dataset.answered = '1';
        const chosen = parseInt(opt.dataset.i, 10);
        optEls.forEach(o => {
          const oi = parseInt(o.dataset.i, 10);
          o.disabled = true;
          if (oi === correct) o.classList.add('correct');
          else if (oi === chosen) o.classList.add('wrong');
        });
        const exp = qEl.querySelector('.explain');
        const verdict = exp.querySelector('.verdict');
        const ok = chosen === correct;
        verdict.textContent = ok ? '✓ Correct' : '✗ Incorrect — see explanation';
        verdict.className = 'verdict ' + (ok ? 'ok' : 'no');
        exp.classList.add('show');
      });
    });
  });
}

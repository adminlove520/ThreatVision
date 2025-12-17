// ThreatVision Premium UI Logic

// Configuration
const API_BASE = 'api';
const REPO_URL = 'https://github.com/adminlove520/ThreatVision';

// State
let state = {
    currentView: 'dashboard',
    reports: [],
    cves: [],
    repos: [],
    theme: localStorage.getItem('theme') || 'light',
    charts: {} // Store chart instances
};

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    await loadData();
    renderDashboard();
    setupEventListeners();

    // Check URL hash for direct navigation
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
});

// Theme Management
function initTheme() {
    if (state.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        state.theme = 'dark';
    } else {
        document.documentElement.classList.remove('dark');
        state.theme = 'light';
    }
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', state.theme);
    initTheme();
}

// Navigation
function switchView(viewName) {
    // Update State
    state.currentView = viewName;

    // Update UI
    document.querySelectorAll('[id^="view-"]').forEach(el => el.classList.add('hidden'));
    document.getElementById(`view-${viewName}`).classList.remove('hidden');

    // Update Nav Active State
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.remove('bg-primary-50', 'text-primary-600', 'dark:bg-primary-500/10', 'dark:text-primary-500');
        el.classList.add('text-gray-600', 'dark:text-gray-400', 'hover:bg-gray-50', 'dark:hover:bg-dark-800');
    });

    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) {
        activeNav.classList.remove('text-gray-600', 'dark:text-gray-400', 'hover:bg-gray-50', 'dark:hover:bg-dark-800');
        activeNav.classList.add('bg-primary-50', 'text-primary-600', 'dark:bg-primary-500/10', 'dark:text-primary-500');
    }

    // Render View Content
    if (viewName === 'reports') renderReportsView();
    if (viewName === 'cves') renderCVEsView();
    if (viewName === 'repos') renderReposView();

    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobile-overlay');
    if (!sidebar.classList.contains('-translate-x-full') && window.innerWidth < 1024) {
        toggleSidebar();
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobile-overlay');

    if (sidebar.classList.contains('-translate-x-full')) {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
    } else {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    }
}

// Data Loading
async function loadData() {
    try {
        const [reportsRes, cvesRes, reposRes] = await Promise.all([
            fetch(`${API_BASE}/reports.json`),
            fetch(`${API_BASE}/cves.json`),
            fetch(`${API_BASE}/repos.json`)
        ]);

        const reportsData = await reportsRes.json();
        const cvesData = await cvesRes.json();
        const reposData = await reposRes.json();

        state.reports = reportsData.reports || [];
        state.cves = cvesData.cves || [];
        state.repos = reposData.repos || [];

    } catch (error) {
        console.error('Failed to load data:', error);
        // Show error toast
    }
}

// Rendering Logic
function renderDashboard() {
    // Stats
    document.getElementById('stat-today-cves').textContent = state.cves.filter(c => isToday(c.publish_time)).length;
    document.getElementById('stat-total-repos').textContent = state.repos.length;
    document.getElementById('stat-total-reports').textContent = state.reports.length;

    const highRiskCount = state.cves.filter(c => {
        try {
            const analysis = JSON.parse(c.ai_analysis);
            const risk = (analysis.risk_level || '').toUpperCase();
            return risk.includes('HIGH') || risk.includes('CRITICAL') || risk.includes('高') || risk.includes('严重');
        } catch { return false; }
    }).length;
    document.getElementById('stat-high-risk').textContent = highRiskCount;

    // Charts
    initCharts();

    // Latest Report Preview
    if (state.reports.length > 0) {
        loadReportContent(state.reports[0].date, 'dashboard-report-preview');
    }

    // Recent CVEs List
    const recentCVEs = state.cves.slice(0, 5);
    const cveListEl = document.getElementById('dashboard-cve-list');
    cveListEl.innerHTML = recentCVEs.map(cve => `
        <div class="p-4 hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors cursor-pointer" onclick="openCVEModal('${cve.cve_id}')">
            <div class="flex justify-between items-start">
                <div>
                    <span class="text-sm font-mono font-medium text-primary-600 dark:text-primary-400">${cve.cve_id}</span>
                    <p class="text-xs text-gray-500 mt-1 line-clamp-1">${cve.description}</p>
                </div>
                ${getRiskBadge(cve.ai_analysis)}
            </div>
        </div>
    `).join('');
}

function renderReportsView() {
    const listEl = document.getElementById('report-list');
    listEl.innerHTML = state.reports.map((report, index) => `
        <button onclick="loadFullReport('${report.date}')" class="w-full text-left p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-dark-800 transition-colors flex items-center justify-between group">
            <div class="flex items-center">
                <div class="w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center mr-3 group-hover:bg-primary-100 transition-colors">
                    <i class="fa-solid fa-file-lines"></i>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-200">${report.date}</p>
                    <p class="text-xs text-gray-500">Security Daily Report</p>
                </div>
            </div>
            <i class="fa-solid fa-chevron-right text-xs text-gray-300 group-hover:text-gray-400"></i>
        </button>
    `).join('');

    // Load first report if none selected
    if (state.reports.length > 0 && !document.querySelector('#report-viewer article').hasAttribute('data-loaded')) {
        loadFullReport(state.reports[0].date);
    }
}

async function loadFullReport(date) {
    const viewerEl = document.getElementById('report-viewer');
    viewerEl.innerHTML = '<div class="flex items-center justify-center h-full"><i class="fa-solid fa-circle-notch fa-spin text-2xl text-primary-500"></i></div>';

    try {
        const res = await fetch(`${API_BASE}/reports/${date}.json`);
        const data = await res.json();

        // Configure Marked
        marked.setOptions({
            highlight: function (code, lang) {
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, { language }).value;
            },
            langPrefix: 'hljs language-'
        });

        viewerEl.innerHTML = `
            <article class="prose dark:prose-invert max-w-4xl mx-auto" data-loaded="true">
                ${marked.parse(data.content)}
            </article>
        `;

        // Highlight code blocks
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });

    } catch (error) {
        viewerEl.innerHTML = '<div class="text-center text-red-500">Failed to load report</div>';
    }
}

async function loadReportContent(date, targetId) {
    try {
        const res = await fetch(`${API_BASE}/reports/${date}.json`);
        const data = await res.json();
        const html = marked.parse(data.content.split('## 安全分析')[0]); // Only show first part for dashboard
        document.getElementById(targetId).innerHTML = html;
    } catch (e) {
        console.error(e);
    }
}

function renderCVEsView() {
    const gridEl = document.getElementById('cve-grid');
    const searchTerm = document.getElementById('cve-search').value.toLowerCase();

    const filtered = state.cves.filter(c =>
        c.cve_id.toLowerCase().includes(searchTerm) ||
        (c.description && c.description.toLowerCase().includes(searchTerm))
    );

    gridEl.innerHTML = filtered.map(cve => `
        <div class="bg-white dark:bg-dark-900 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-bold font-mono text-primary-600 cursor-pointer hover:underline" onclick="openCVEModal('${cve.cve_id}')">${cve.cve_id}</h3>
                ${getRiskBadge(cve.ai_analysis)}
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-4">${cve.description}</p>
            <div class="flex justify-between items-center text-xs text-gray-500">
                <span>${formatDate(cve.publish_time)}</span>
                <button onclick="openCVEModal('${cve.cve_id}')" class="text-primary-500 hover:text-primary-600 font-medium">Details <i class="fa-solid fa-arrow-right ml-1"></i></button>
            </div>
        </div>
    `).join('');
}

function renderReposView() {
    const gridEl = document.getElementById('repo-grid');
    gridEl.innerHTML = state.repos.map(repo => `
        <div class="bg-white dark:bg-dark-900 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div class="flex items-center mb-4">
                <div class="w-10 h-10 rounded-lg bg-gray-100 dark:bg-dark-800 flex items-center justify-center mr-3 text-gray-700 dark:text-gray-300">
                    <i class="fa-brands fa-github text-xl"></i>
                </div>
                <div>
                    <h3 class="font-bold text-gray-900 dark:text-white line-clamp-1">${repo.name}</h3>
                    <div class="flex items-center text-xs text-gray-500 mt-0.5">
                        <span class="flex items-center mr-3"><i class="fa-solid fa-star text-yellow-400 mr-1"></i> ${repo.stars}</span>
                        <span>Updated ${formatDate(repo.last_updated)}</span>
                    </div>
                </div>
            </div>
            <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-4 h-10">${repo.description || 'No description'}</p>
            <a href="${repo.url}" target="_blank" class="block w-full text-center py-2 rounded-lg bg-gray-50 dark:bg-dark-800 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700 transition-colors">
                View Repository
            </a>
        </div>
    `).join('');
}

// Helpers
function getRiskBadge(aiAnalysis) {
    let risk = 'UNKNOWN';
    let colorClass = 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

    if (aiAnalysis) {
        try {
            const analysis = JSON.parse(aiAnalysis);
            risk = (analysis.risk_level || 'UNKNOWN').toUpperCase();

            if (risk.includes('CRITICAL') || risk.includes('严重')) {
                colorClass = 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';
            } else if (risk.includes('HIGH') || risk.includes('高')) {
                colorClass = 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400';
            } else if (risk.includes('MEDIUM') || risk.includes('中')) {
                colorClass = 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400';
            } else if (risk.includes('LOW') || risk.includes('低')) {
                colorClass = 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400';
            }
        } catch (e) { }
    }

    return `<span class="px-2 py-1 rounded text-xs font-bold ${colorClass}">${risk}</span>`;
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('zh-CN');
}

function isToday(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const today = new Date();
    return date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear();
}

// Modals
function openCVEModal(cveId) {
    const cve = state.cves.find(c => c.cve_id === cveId);
    if (!cve) return;

    document.getElementById('modal-title').textContent = cve.cve_id;

    let content = `
        <div class="mb-6">
            <h4 class="text-sm font-bold text-gray-500 uppercase mb-2">Description</h4>
            <p class="text-gray-800 dark:text-gray-200">${cve.description}</p>
        </div>
    `;

    if (cve.ai_analysis) {
        try {
            const analysis = JSON.parse(cve.ai_analysis);
            content += `
                <div class="bg-primary-50 dark:bg-primary-900/20 rounded-xl p-4 mb-6 border border-primary-100 dark:border-primary-800">
                    <h4 class="text-sm font-bold text-primary-600 dark:text-primary-400 uppercase mb-3 flex items-center">
                        <i class="fa-solid fa-robot mr-2"></i> AI Analysis
                    </h4>
                    <div class="grid grid-cols-2 gap-4 mb-4">
                        <div>
                            <span class="text-xs text-gray-500">Risk Level</span>
                            <p class="font-bold">${analysis.risk_level || '-'}</p>
                        </div>
                        <div>
                            <span class="text-xs text-gray-500">Exploit Status</span>
                            <p class="font-bold">${analysis.exploitation_status || '-'}</p>
                        </div>
                    </div>
                    <div class="space-y-3">
                        <div>
                            <span class="text-xs text-gray-500">Summary</span>
                            <p class="text-sm">${analysis.summary || '-'}</p>
                        </div>
                        ${analysis.key_findings ? `
                            <div>
                                <span class="text-xs text-gray-500">Key Findings</span>
                                <ul class="list-disc list-inside text-sm mt-1">
                                    ${analysis.key_findings.map(f => `<li>${f}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } catch (e) { }
    }

    content += `
        <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
                <span class="text-gray-500">Published</span>
                <p>${formatDate(cve.publish_time)}</p>
            </div>
            <div>
                <span class="text-gray-500">CVSS Score</span>
                <p class="font-mono">${cve.cvss_score || 'N/A'}</p>
            </div>
        </div>
    `;

    document.getElementById('modal-content').innerHTML = content;
    document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

function setupEventListeners() {
    document.getElementById('cve-search').addEventListener('input', () => {
        renderCVEsView();
    });
}

function handleHashChange() {
    const hash = window.location.hash.slice(1);
    if (hash && ['dashboard', 'reports', 'cves', 'repos'].includes(hash)) {
        switchView(hash);
    }
}

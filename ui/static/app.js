// ThreatVision Preview UI JavaScript

// API Base URL
const API_BASE_URL = '/api';

// DOM Elements
const reportsTableBody = document.getElementById('reportsTableBody');
const reportContent = document.getElementById('reportContent');
const todayCves = document.getElementById('todayCves');
const totalRepos = document.getElementById('totalRepos');
const totalReports = document.getElementById('totalReports');
const cvesGrid = document.getElementById('cvesGrid');
const reposGrid = document.getElementById('reposGrid');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const closeMobileMenu = document.getElementById('closeMobileMenu');
const mobileMenu = document.getElementById('mobileMenu');
const navLinks = document.querySelectorAll('.nav-link');
const mobileNavLinks = document.querySelectorAll('.mobile-nav-link');
const filterBtns = document.querySelectorAll('.filter-btn');
const searchInput = document.querySelector('.search-input');

// Charts
let cveTrendChart = null;
let riskDistributionChart = null;

// State
let currentFilter = 'all';
let cveData = [];

// Initialize the application
function init() {
    console.log('Initializing ThreatVision UI...');
    
    // Initialize UI components
    initMobileMenu();
    initNavigation();
    initFilters();
    initSearch();
    initSmoothScroll();
    
    // Load data
    loadReports();
    loadStats();
    loadCVEs();
    loadRepos();
    
    // Initialize charts
    initCharts();
    
    // Add event listeners
    document.querySelector('#reports button').addEventListener('click', loadReports);
    document.querySelector('#repos button').addEventListener('click', loadRepos);
    
    // Enable code highlighting
    hljs.highlightAll();
    
    // Add marked options for better rendering
    marked.setOptions({
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        breaks: true,
        gfm: true
    });
}

// Initialize mobile menu
function initMobileMenu() {
    mobileMenuBtn.addEventListener('click', () => {
        mobileMenu.classList.remove('closed');
        mobileMenu.classList.add('open');
        document.body.style.overflow = 'hidden';
    });
    
    closeMobileMenu.addEventListener('click', closeMobileMenuHandler);
    
    // Close menu when clicking outside
    mobileMenu.addEventListener('click', (e) => {
        if (e.target === mobileMenu) {
            closeMobileMenuHandler();
        }
    });
}

// Close mobile menu
function closeMobileMenuHandler() {
    mobileMenu.classList.remove('open');
    mobileMenu.classList.add('closed');
    document.body.style.overflow = '';
}

// Initialize navigation
function initNavigation() {
    // Desktop navigation
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Scroll to section
            const targetId = link.getAttribute('href');
            if (targetId.startsWith('#')) {
                e.preventDefault();
                scrollToSection(targetId);
            }
        });
    });
    
    // Mobile navigation
    mobileNavLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Close mobile menu
            closeMobileMenuHandler();
            
            // Update active state
            mobileNavLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Scroll to section
            const targetId = link.getAttribute('href');
            if (targetId.startsWith('#')) {
                e.preventDefault();
                scrollToSection(targetId);
            }
        });
    });
    
    // Update active link on scroll
    window.addEventListener('scroll', updateActiveLink);
}

// Update active link based on scroll position
function updateActiveLink() {
    const sections = document.querySelectorAll('section[id]');
    const scrollPosition = window.scrollY + 100;
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            // Update desktop navigation
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${sectionId}`) {
                    link.classList.add('active');
                }
            });
            
            // Update mobile navigation
            mobileNavLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${sectionId}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}

// Initialize filters
function initFilters() {
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update filter
            currentFilter = btn.getAttribute('data-filter');
            
            // Apply filter
            applyFilter();
        });
    });
}

// Initialize search
function initSearch() {
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            // TODO: Implement search functionality
            console.log('Searching for:', searchTerm);
        });
    }
}

// Initialize smooth scrolling
function initSmoothScroll() {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            scrollToSection(href);
        });
    });
}

// Scroll to section
function scrollToSection(selector) {
    const element = document.querySelector(selector);
    if (element) {
        const offsetTop = element.offsetTop - 80; // Account for fixed header
        window.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    }
}

// Apply filter to CVEs
function applyFilter() {
    if (cveData.length === 0) return;
    
    // Clear existing CVEs
    cvesGrid.innerHTML = '';
    
    // Filter CVEs
    let filteredCves = cveData;
    if (currentFilter !== 'all') {
        filteredCves = cveData.filter(cve => {
            if (!cve.ai_analysis) return false;
            try {
                const analysis = JSON.parse(cve.ai_analysis);
                return analysis.risk_level?.toLowerCase() === currentFilter;
            } catch (e) {
                return false;
            }
        });
    }
    
    // Render filtered CVEs
    renderCVEs(filteredCves);
}

// Render CVEs
function renderCVEs(cves) {
    cves.forEach(cve => {
        const cveCard = createCVECard(cve);
        cvesGrid.appendChild(cveCard);
    });
    
    // If no CVEs found
    if (cves.length === 0) {
        cvesGrid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-500">
            <i class="fas fa-exclamation-triangle text-4xl mb-4 opacity-50"></i>
            <p class="text-lg">未找到匹配的漏洞</p>
        </div>`;
    }
}

// Create CVE card element
function createCVECard(cve) {
    const cveCard = document.createElement('div');
    cveCard.className = 'cve-card fade-in';
    
    // Get AI analysis if available
    let riskLevel = '未知';
    let riskColor = 'badge bg-gray-100 text-gray-800';
    
    if (cve.ai_analysis) {
        try {
            const analysis = JSON.parse(cve.ai_analysis);
            riskLevel = analysis.risk_level || '未知';
            
            // Set color based on risk level
            switch (riskLevel.toLowerCase()) {
                case 'high':
                    riskColor = 'badge badge-high';
                    break;
                case 'medium':
                    riskColor = 'badge badge-medium';
                    break;
                case 'low':
                    riskColor = 'badge badge-low';
                    break;
                default:
                    riskColor = 'badge bg-gray-100 text-gray-800';
            }
        } catch (e) {
            console.error('Error parsing AI analysis:', e);
        }
    }
    
    cveCard.innerHTML = `
        <div class="flex justify-between items-start mb-3">
            <h3 class="text-lg font-semibold text-gray-900 hover:text-red-600 transition-colors duration-200 cursor-pointer" onclick="loadCVE('${cve.cve_id}')">${cve.cve_id}</h3>
            <span class="${riskColor}">${riskLevel}</span>
        </div>
        <p class="text-sm text-gray-600 mb-3 line-clamp-3">${cve.description}</p>
        <div class="flex items-center justify-between text-sm text-gray-500">
            ${cve.publish_time ? `<span class="flex items-center"><i class="far fa-clock mr-1"></i>${formatDate(cve.publish_time)}</span>` : ''}
            <div class="flex items-center space-x-3">
                <button onclick="loadCVE('${cve.cve_id}')" class="text-red-600 hover:text-red-800 transition-colors duration-200 flex items-center text-sm font-medium">
                    <i class="fas fa-eye mr-1"></i>详情
                </button>
                <a href="#" class="text-gray-500 hover:text-gray-700 transition-colors duration-200">
                    <i class="fas fa-share-alt"></i>
                </a>
            </div>
        </div>
    `;
    
    return cveCard;
}

// Load reports
async function loadReports() {
    try {
        // Show loading state
        showLoading(reportsTableBody, '加载中...');
        
        const response = await fetch(`${API_BASE_URL}/reports`);
        if (!response.ok) {
            throw new Error('Failed to fetch reports');
        }
        const data = await response.json();
        
        // Update stats
        totalReports.textContent = data.total || 0;
        
        // Remove loading state
        removeLoading();
        
        // Clear existing reports
        reportsTableBody.innerHTML = '';
        
        // Ensure reports is an array
        const reports = Array.isArray(data.reports) ? data.reports : [];
        
        // Add new reports
        if (reports.length === 0) {
            reportsTableBody.innerHTML = '<tr><td colspan="4" class="px-6 py-12 text-center text-gray-500">暂无安全日报</td></tr>';
            return;
        }
        
        reports.forEach(report => {
            const row = document.createElement('tr');
            row.className = 'fade-in hover:bg-gray-50 transition-colors duration-200';
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${report.date}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-600">CVE漏洞、GitHub仓库、安全资讯</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="badge bg-green-100 text-green-800">已发布</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                    <button onclick="loadReport('${report.date}')" class="text-red-600 hover:text-red-900 font-medium text-sm mr-3">
                        <i class="fas fa-eye mr-1"></i>查看
                    </button>
                    <a href="${API_BASE_URL}/reports/${report.date}" target="_blank" class="text-gray-600 hover:text-gray-900 font-medium text-sm">
                        <i class="fas fa-download mr-1"></i>下载
                    </a>
                </td>
            `;
            reportsTableBody.appendChild(row);
        });
        
        // Load latest report if available
        if (reports.length > 0) {
            loadReport(reports[0].date);
        }
    } catch (error) {
        console.error('Error loading reports:', error);
        removeLoading();
        reportsTableBody.innerHTML = '<tr><td colspan="4" class="px-6 py-12 text-center text-gray-500">暂无安全日报</td></tr>';
        // Don't show error toast for empty data, it's a normal state
    }
}

// Load a specific report
async function loadReport(date) {
    try {
        // Show loading state
        showLoading(reportContent, '加载报告中...');
        
        const response = await fetch(`${API_BASE_URL}/reports/${date}`);
        const data = await response.json();
        
        // Render markdown content with syntax highlighting
        const htmlContent = marked.parse(data.content);
        reportContent.innerHTML = htmlContent;
        
        // Apply syntax highlighting to code blocks
        hljs.highlightAll();
        
        // Scroll to report section
        scrollToSection('#latestReport');
        
        // Update URL hash
        history.pushState(null, null, `#report-${date}`);
    } catch (error) {
        console.error('Error loading report:', error);
        reportContent.innerHTML = `<div class="flex justify-center items-center py-12 text-red-500">
            <i class="fas fa-exclamation-circle text-4xl mb-4 mr-4"></i>
            <div>
                <h3 class="text-xl font-semibold mb-2">加载报告失败</h3>
                <p>无法加载该报告，请稍后重试</p>
            </div>
        </div>`;
        showError('无法加载报告，请稍后重试');
    }
}

// Load stats
async function loadStats() {
    try {
        // Get CVEs count
        const cveResponse = await fetch(`${API_BASE_URL}/cves?limit=1`);
        if (!cveResponse.ok) {
            throw new Error('Failed to load CVE stats');
        }
        const cveData = await cveResponse.json();
        todayCves.textContent = cveData.total || 0;
        
        // Get repos count
        const repoResponse = await fetch(`${API_BASE_URL}/repos?limit=1`);
        if (!repoResponse.ok) {
            throw new Error('Failed to load repo stats');
        }
        const repoData = await repoResponse.json();
        totalRepos.textContent = repoData.total || 0;
        
    } catch (error) {
        console.error('Error loading stats:', error);
        // Keep default values or show 0 instead of breaking UI
        todayCves.textContent = 0;
        totalRepos.textContent = 0;
    }
}

// Load CVEs
async function loadCVEs() {
    try {
        // Show loading state
        showLoading(cvesGrid, '加载漏洞数据中...');
        
        const response = await fetch(`${API_BASE_URL}/cves?limit=9`);
        if (!response.ok) {
            throw new Error('Failed to fetch CVEs');
        }
        const data = await response.json();
        
        // Store CVE data for filtering
        cveData = Array.isArray(data.cves) ? data.cves : [];
        
        // Remove loading state
        removeLoading();
        
        // Render CVEs
        renderCVEs(cveData);
    } catch (error) {
        console.error('Error loading CVEs:', error);
        removeLoading();
        cvesGrid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-500">
            <i class="fas fa-exclamation-circle text-4xl mb-4 opacity-50"></i>
            <p class="text-lg">暂无漏洞数据</p>
            <p class="text-sm mt-2">系统正在监控中，请稍后刷新查看</p>
        </div>`;
        // Don't show error toast for empty data, it's a normal state
    }
}

// Load repositories
async function loadRepos() {
    try {
        // Show loading state
        showLoading(reposGrid, '加载仓库数据中...');
        
        const response = await fetch(`${API_BASE_URL}/repos?limit=6`);
        if (!response.ok) {
            throw new Error('Failed to fetch repositories');
        }
        const data = await response.json();
        
        // Remove loading state
        removeLoading();
        
        // Clear existing repos
        reposGrid.innerHTML = '';
        
        // Ensure repos is an array
        const repos = Array.isArray(data.repos) ? data.repos : [];
        
        // Add new repos
        if (repos.length === 0) {
            reposGrid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-500">
                <i class="fas fa-github text-4xl mb-4 opacity-50"></i>
                <p class="text-lg">暂无监控仓库数据</p>
                <p class="text-sm mt-2">系统正在监控中，请稍后刷新查看</p>
            </div>`;
            return;
        }
        
        repos.forEach(repo => {
            const repoCard = createRepoCard(repo);
            reposGrid.appendChild(repoCard);
        });
    } catch (error) {
        console.error('Error loading repositories:', error);
        removeLoading();
        reposGrid.innerHTML = `<div class="col-span-full text-center py-12 text-gray-500">
            <i class="fas fa-github text-4xl mb-4 opacity-50"></i>
            <p class="text-lg">暂无监控仓库数据</p>
            <p class="text-sm mt-2">系统正在监控中，请稍后刷新查看</p>
        </div>`;
        // Don't show error toast for empty data, it's a normal state
    }
}

// Create repository card
function createRepoCard(repo) {
    const repoCard = document.createElement('div');
    repoCard.className = 'card fade-in';
    
    repoCard.innerHTML = `
        <div class="flex items-start space-x-4">
            <div class="w-12 h-12 bg-gray-200 rounded-lg flex items-center justify-center text-gray-700 text-2xl">
                <i class="fab fa-github"></i>
            </div>
            <div class="flex-1">
                <div class="flex flex-wrap items-center gap-2 mb-2">
                    <h3 class="text-lg font-semibold text-gray-900 hover:text-red-600 transition-colors duration-200 cursor-pointer">${repo.name}</h3>
                    <span class="text-xs text-gray-500">${repo.stars} <i class="fas fa-star text-yellow-500"></i></span>
                </div>
                <p class="text-sm text-gray-600 mb-4 line-clamp-2">${repo.description || '暂无描述'}</p>
                <div class="flex items-center space-x-4 text-xs text-gray-500">
                    ${repo.last_updated ? `<span class="flex items-center"><i class="far fa-clock mr-1"></i>${formatDate(repo.last_updated)}</span>` : ''}
                    <a href="${repo.url}" target="_blank" rel="noopener noreferrer" class="text-red-600 hover:text-red-800 transition-colors duration-200 flex items-center font-medium">
                        <i class="fas fa-external-link-alt mr-1"></i>访问仓库
                    </a>
                </div>
            </div>
        </div>
    `;
    
    return repoCard;
}

// Load a specific CVE
async function loadCVE(cveId) {
    try {
        // Show loading state
        showLoading(document.body, '加载漏洞详情中...');
        
        const response = await fetch(`${API_BASE_URL}/cves/${cveId}`);
        const cve = await response.json();
        
        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        
        // Get AI analysis if available
        let analysisContent = '';
        if (cve.ai_analysis) {
            try {
                const analysis = JSON.parse(cve.ai_analysis);
                analysisContent = `
                    <div class="mt-6">
                        <h4 class="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-robot text-blue-600 mr-2"></i>
                            AI 分析
                        </h4>
                        <div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <div class="grid grid-cols-2 gap-4 mb-3">
                                <div>
                                    <p class="text-sm font-medium text-gray-700">风险等级:</p>
                                    <p class="text-sm text-gray-900">${analysis.risk_level || '未知'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-700">漏洞类型:</p>
                                    <p class="text-sm text-gray-900">${analysis.vulnerability_type || '未知'}</p>
                                </div>
                            </div>
                            ${analysis.summary ? `
                                <div class="mb-3">
                                    <p class="text-sm font-medium text-gray-700 mb-1">概述:</p>
                                    <p class="text-sm text-gray-900">${analysis.summary}</p>
                                </div>
                            ` : ''}
                            ${analysis.key_findings ? `
                                <div class="mb-3">
                                    <p class="text-sm font-medium text-gray-700 mb-2">关键发现:</p>
                                    <ul class="list-disc list-inside text-sm text-gray-900 space-y-1">
                                        ${analysis.key_findings.map(finding => `<li>${finding}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            ${analysis.technical_details ? `
                                <div>
                                    <p class="text-sm font-medium text-gray-700 mb-2">技术细节:</p>
                                    <div class="bg-gray-100 p-3 rounded-md text-sm text-gray-900">
                                        ${analysis.technical_details.map(detail => `<p class="mb-1">${detail}</p>`).join('')}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            } catch (e) {
                console.error('Error parsing AI analysis:', e);
            }
        }
        
        modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6">
                    <div class="flex justify-between items-start mb-6">
                        <div>
                            <h3 class="text-2xl font-bold text-gray-900">${cve.cve_id}</h3>
                            ${cve.publish_time ? `<p class="text-sm text-gray-500 mt-1 flex items-center"><i class="far fa-clock mr-1"></i>${formatDate(cve.publish_time)}</p>` : ''}
                        </div>
                        <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600 transition-colors duration-300">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    
                    <div class="border-b border-gray-200 pb-6">
                        <h4 class="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-info-circle text-blue-600 mr-2"></i>
                            漏洞描述
                        </h4>
                        <p class="text-sm text-gray-700 whitespace-pre-wrap">${cve.description}</p>
                    </div>
                    
                    ${analysisContent}
                    
                    <div class="mt-6 flex justify-end space-x-3">
                        <button onclick="this.closest('.fixed').remove()" class="btn-secondary">
                            关闭
                        </button>
                        <a href="#" class="btn-primary flex items-center space-x-2">
                            <i class="fas fa-share-alt"></i>
                            <span>分享</span>
                        </a>
                    </div>
                </div>
            </div>
        `;
        
        // Remove loading state
        removeLoading();
        
        // Add modal to DOM
        document.body.appendChild(modal);
        
        // Add close event listener for modal background
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    } catch (error) {
        console.error('Error loading CVE:', error);
        removeLoading();
        showError('无法加载漏洞详情，请稍后重试');
    }
}

// Initialize charts
function initCharts() {
    // CVE Trend Chart
    const cveTrendCtx = document.getElementById('cveTrendChart').getContext('2d');
    cveTrendChart = new Chart(cveTrendCtx, {
        type: 'line',
        data: {
            labels: ['7天前', '6天前', '5天前', '4天前', '3天前', '2天前', '昨天'],
            datasets: [{
                label: '新增漏洞数',
                data: [12, 19, 3, 5, 2, 3, 7],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#ef4444',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    cornerRadius: 8,
                    displayColors: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
    
    // Risk Distribution Chart
    const riskDistributionCtx = document.getElementById('riskDistributionChart').getContext('2d');
    riskDistributionChart = new Chart(riskDistributionCtx, {
        type: 'doughnut',
        data: {
            labels: ['高风险', '中风险', '低风险', '未知'],
            datasets: [{
                data: [35, 45, 15, 5],
                backgroundColor: [
                    '#ef4444',
                    '#f59e0b',
                    '#10b981',
                    '#6b7280'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    cornerRadius: 8
                }
            },
            animation: {
                animateScale: true,
                animateRotate: true,
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Show loading spinner
function showLoading(element, message = '加载中...') {
    // Create loading element
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
    loadingDiv.id = 'loading-overlay';
    
    loadingDiv.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl p-8 text-center">
            <div class="loading-spinner mx-auto mb-4"></div>
            <p class="text-gray-700 font-medium">${message}</p>
        </div>
    `;
    
    document.body.appendChild(loadingDiv);
    document.body.style.overflow = 'hidden';
}

// Remove loading spinner
function removeLoading() {
    const loadingDiv = document.getElementById('loading-overlay');
    if (loadingDiv) {
        loadingDiv.remove();
        document.body.style.overflow = '';
    }
}

// Show error message
function showError(message) {
    // Create error element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 slide-up';
    
    errorDiv.innerHTML = `
        <div class="flex items-center space-x-3">
            <i class="fas fa-exclamation-circle text-xl"></i>
            <span class="font-medium">${message}</span>
            <button onclick="this.parentElement.remove()" class="text-white hover:text-gray-200 transition-colors duration-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Add to DOM
    document.body.appendChild(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.style.transform = 'translateY(-100%)';
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 300);
        }
    }, 5000);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

// Add event listener for DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Add scroll event for header shadow
window.addEventListener('scroll', () => {
    const header = document.querySelector('header');
    if (window.scrollY > 10) {
        header.classList.add('shadow-lg');
        header.classList.remove('shadow-md');
    } else {
        header.classList.add('shadow-md');
        header.classList.remove('shadow-lg');
    }
});

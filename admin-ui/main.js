// =========================
// 🧭 Tab Navigation Setup
// =========================

const tabButtons = document.querySelectorAll('.tab-btn');
const tabPages = document.querySelectorAll('.tab-page');
const loadedTabs = {};

// Tab switching logic
tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.getAttribute('data-tab');
    tabPages.forEach(page => {
      page.classList.toggle('hidden', page.id !== tab);
    });
    tabButtons.forEach(b => b.classList.remove('text-blue-600', 'font-bold'));
    btn.classList.add('text-blue-600', 'font-bold');

    if (!loadedTabs[tab] && pageHandlers[tab]) {
      pageHandlers[tab]();
      loadedTabs[tab] = true;
    }
  });
});


// =========================
// 📄 Logs Page
// =========================

async function loadLogs() {
  const container = document.getElementById('logs-table');
  container.innerHTML = '<p class="text-gray-500">Loading logs...</p>';

  try {
    const res = await fetch('webhook_logs.json');
    let logs = await res.json();

    if (!Array.isArray(logs) || logs.length === 0) {
      container.innerHTML = '<p class="text-gray-500">No logs found.</p>';
      return;
    }

    // ✅ Sort newest first
    logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    const rows = logs.map((log, i) => {
      const timestamp = new Date(log.timestamp);
      const date = timestamp.toLocaleDateString();
      const time = timestamp.toLocaleTimeString();

      const statusClass = log.status === 'success'
        ? 'text-green-600 font-semibold'
        : 'text-red-600 font-semibold';

      const changes = log.changes ? `
        <details class="bg-gray-50 p-2 border rounded mt-1">
          <summary class="cursor-pointer font-medium text-sm text-gray-700">Changes</summary>
          <pre class="mt-1 overflow-x-auto text-xs">${JSON.stringify(log.changes, null, 2)}</pre>
        </details>` : '';

      const payload = log.payload ? `
        <details class="bg-gray-50 p-2 border rounded mt-1">
          <summary class="cursor-pointer font-medium text-sm text-gray-700">Payload</summary>
          <pre class="mt-1 overflow-x-auto text-xs">${JSON.stringify(log.payload, null, 2)}</pre>
          <button
            class="mt-2 bg-blue-500 text-white text-xs px-3 py-1 rounded hover:bg-blue-600"
            onclick="replayPayload(this)"
            data-payload='${JSON.stringify(log.payload).replace(/'/g, "&#39;")}'
          >↻ Replay</button>
          <small class="replay-status ml-2 text-gray-500 text-xs"></small>
        </details>` : '';

      return `
        <tr class="border-b border-gray-200">
          <td class="p-2 whitespace-nowrap">${date}</td>
          <td class="p-2 whitespace-nowrap">${time}</td>
          <td class="p-2">${log.event}</td>
          <td class="p-2">${log.email || ''}</td>
          <td class="p-2 ${statusClass}">${log.status}</td>
          <td class="p-2 space-y-2">${changes}${payload}</td>
        </tr>`;
    }).join('');

    container.innerHTML = `
      <div class="overflow-auto">
        <table class="w-full text-left bg-white shadow-sm rounded-lg overflow-hidden text-sm">
          <thead class="bg-gray-100 text-gray-600">
            <tr>
              <th class="p-2">Date</th>
              <th class="p-2">Time</th>
              <th class="p-2">Event</th>
              <th class="p-2">Email</th>
              <th class="p-2">Status</th>
              <th class="p-2">Details</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch (err) {
    console.error('Error loading logs:', err);
    container.innerHTML = '<p class="text-red-500">Error loading logs. Check console for details.</p>';
  }
}

// =========================
// 📧 Event Replay Logic
// =========================

async function replayPayload(button) {
  const statusElem = button.nextElementSibling;
  const payloadJson = button.getAttribute('data-payload');
  button.disabled = true;
  statusElem.textContent = '⏳ Replaying...';

  try {
    const payload = JSON.parse(payloadJson);

    const res = await fetch('/replay-log', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Memberful-Webhook-Signature': 'REPLAY'
      },
      body: JSON.stringify(payload)
    });

    statusElem.textContent = res.ok ? '✅ Replayed' : `❌ Error (${res.status})`;
  } catch (err) {
    console.error('Replay error:', err);
    statusElem.textContent = '❌ Failed';
  } finally {
    button.disabled = false;
  }
}


// =========================
// 📧 Email Cache Page
// =========================

async function loadEmailCache() {
  const container = document.getElementById('cache');
  container.innerHTML = `
    <h2 class="text-lg font-semibold mb-2">Email Cache Viewer</h2>
    <p class="text-sm text-gray-500">Loading...</p>`;

  try {
    const res = await fetch('email_cache.json');
    const cache = await res.json();

    if (!cache || Object.keys(cache).length === 0) {
      container.innerHTML += '<p class="text-gray-500 mt-2">No cache data available.</p>';
      return;
    }

    const rows = Object.entries(cache).map(([id, email]) => {
      return `
        <tr class="border-b border-gray-200">
          <td class="p-2 font-mono text-xs">${id}</td>
          <td class="p-2">${email}</td>
        </tr>`;
    }).join('');

    container.innerHTML = `
      <h2 class="text-lg font-semibold mb-2">Email Cache Viewer</h2>
      <table class="w-full text-left bg-white shadow-sm rounded-lg overflow-hidden text-sm">
        <thead class="bg-gray-100 text-gray-600">
          <tr>
            <th class="p-2">Memberful ID</th>
            <th class="p-2">Email</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (err) {
    console.error('Error loading email cache:', err);
    container.innerHTML += '<p class="text-red-500">Failed to load email cache.</p>';
  }
}


// =========================
// 📊 Dashboard Page
// =========================

async function loadDashboard() {
  console.log('🚀 loadDashboard() triggered');

  const statsContainer = document.getElementById('dashboard-stats');
  const chartCanvas = document.getElementById('event-chart');
  const lineCanvas = document.getElementById('line-chart');
  const topEventsContainer = document.getElementById('top-events');
  statsContainer.innerHTML = 'Loading stats...';

  try {
    const res = await fetch('webhook_logs.json');
    let logs = await res.json();
    logs = logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    if (!Array.isArray(logs)) throw new Error('Invalid logs data');

    const total = logs.length;
    const success = logs.filter(l => l.status === 'success').length;
    const failed = total - success;

    // 👉 Stat Cards
    statsContainer.innerHTML = `
      <div class="bg-white p-4 rounded-lg shadow border border-blue-100 text-center">
        <i data-lucide="webhook" class="mx-auto text-blue-400 mb-2 w-6 h-6"></i>
        <div class="text-sm text-gray-500">Total Webhooks</div>
        <div class="text-3xl font-bold text-blue-600">${total}</div>
      </div>
      <div class="bg-white p-4 rounded-lg shadow border border-green-100 text-center">
        <i data-lucide="check-circle" class="mx-auto text-green-400 mb-2 w-6 h-6"></i>
        <div class="text-sm text-gray-500">Successful</div>
        <div class="text-3xl font-bold text-green-600">${success}</div>
      </div>
      <div class="bg-white p-4 rounded-lg shadow border border-red-100 text-center">
        <i data-lucide="x-circle" class="mx-auto text-red-400 mb-2 w-6 h-6"></i>
        <div class="text-sm text-gray-500">Failed</div>
        <div class="text-3xl font-bold text-red-600">${failed}</div>
      </div>
    `;

    // 👉 Count event types
    const counts = {};
    logs.forEach(l => {
      counts[l.event] = (counts[l.event] || 0) + 1;
    });

    console.log('📊 Chart data:', counts);

    // 👉 Top 5 Events summary
    const top = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    topEventsContainer.innerHTML = `
      <ul class="text-sm text-gray-700 space-y-1">
        ${top.map(([event, count]) => `
          <li class="flex justify-between border-b py-1">
            <span class="font-medium">${event}</span>
            <span class="text-gray-500">${count}</span>
          </li>
        `).join('')}
      </ul>
    `;

    // 👉 Bar Chart: Events by type
    const chartColors = [
      '#3B82F6', '#10B981', '#F59E0B',
      '#EF4444', '#8B5CF6', '#F43F5E',
      '#0EA5E9', '#14B8A6', '#6366F1',
    ];

    new Chart(chartCanvas, {
      type: 'bar',
      data: {
        labels: Object.keys(counts),
        datasets: [{
          label: 'Webhook Events',
          data: Object.values(counts),
          backgroundColor: Object.keys(counts).map((_, i) => chartColors[i % chartColors.length]),
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 }
          }
        }
      }
    });

    // 👉 Line Chart: Webhooks over time
    const dateCounts = {};
    logs.forEach(l => {
      const date = l.timestamp?.slice(0, 10); // 'YYYY-MM-DD'
      if (date) dateCounts[date] = (dateCounts[date] || 0) + 1;
    });

    const sortedDates = Object.keys(dateCounts).sort();

    new Chart(lineCanvas, {
      type: 'line',
      data: {
        labels: sortedDates,
        datasets: [{
          label: 'Webhooks Per Day',
          data: sortedDates.map(date => dateCounts[date]),
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#3B82F6',
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            title: { display: true, text: 'Date' }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Webhooks' },
            ticks: { precision: 0 }
          }
        }
      }
    });

    // 🪄 Replace Lucide icon tags
    lucide.createIcons();

  } catch (err) {
    console.error('Dashboard load error:', err);
    statsContainer.innerHTML = '<p class="text-red-500">Failed to load dashboard data.</p>';
  }
}

// =========================
// 🌗 Dark Mode Toggle
// =========================


// =========================
// ✅ Page Handlers & Init
// =========================

const pageHandlers = {
  logs: loadLogs,
  cache: loadEmailCache,
  dashboard: loadDashboard,
};

document.querySelector('[data-tab="dashboard"]').click();

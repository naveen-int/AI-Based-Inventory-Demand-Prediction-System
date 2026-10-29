
const API_BASE = "http://127.0.0.1:5000/api";
const $ = (id) => document.getElementById(id);

let topChartInstance = null;
let trendChartInstance = null;
let lastReorderRows = [];
let currentUser = null;

function setMessage(message, type = "") {
  $("message").textContent = message;
  $("message").className = `message ${type}`;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

function money(value) {
  return "₹" + Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// Verify the logged-in user and show the correct dashboard.
async function initDashboard() {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      credentials: "include"
    });

    if (!response.ok) {
      window.location.replace("login.html");
      return;
    }

    const result = await response.json();
    currentUser = result.user;

    $("userName").textContent = currentUser.name;

    // Profit Insights are visible only to Admin.
    $("profitSection").hidden = currentUser.role !== "admin";

    $("dashboardContent").hidden = false;

    await checkBackend();
  } catch (error) {
    console.error("Session verification failed:", error);
    window.location.replace("login.html");
  }
}

// Check backend availability without displaying a status button.
async function checkBackend() {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      credentials: "include"
    });

    if (!response.ok) {
      throw new Error("Backend health check failed.");
    }

    return await response.json();
  } catch (error) {
    console.warn("Backend health check failed.", error);
    return null;
  }
}

// Render reusable tables.
function renderTableRows(targetId, rows, columns, emptyMessage) {
  const tbody = $(targetId);

  if (!tbody) {
    console.error(`HTML element not found: ${targetId}`);
    return;
  }

  if (!rows || !rows.length) {
    tbody.innerHTML = `
      <tr>
        <td class="empty" colspan="${columns.length}">
          ${escapeHTML(emptyMessage)}
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = rows.map(row =>
    `<tr>${columns.map(col =>
      `<td>${escapeHTML(
        row[col.key] == null
          ? ""
          : col.format
            ? col.format(row[col.key])
            : row[col.key]
      )}</td>`
    ).join("")}</tr>`
  ).join("");
}

// Render stock replenishment recommendations.
function renderReplenishment(rows) {
  lastReorderRows = rows || [];

  const downloadButton = $("downloadReorder");
  const reorderHead = $("reorderHead");
  const reorderBody = $("reorderBody");

  if (!downloadButton || !reorderHead || !reorderBody) {
    console.error("Stock replenishment HTML elements are missing.");
    return;
  }

  downloadButton.disabled = !lastReorderRows.length;

  const columns = [
    ["Product_ID", "Product ID"],
    ["Product_Name", "Product name"],
    ["Current_Stock", "Current stock"],
    ["Reorder_Level", "Reorder level"],
    ["Total_Units_Sold", "Units sold"],
    ["Average_Daily_Demand", "Avg. daily demand"],
    ["Recommended_Order_Qty", "Recommended order"]
  ];

  reorderHead.innerHTML = columns
    .map(column => `<th>${column[1]}</th>`)
    .join("");

  if (!lastReorderRows.length) {
    reorderBody.innerHTML = `
      <tr>
        <td class="empty" colspan="${columns.length}">
          No products need replenishment, or inventory data has not been analyzed.
        </td>
      </tr>`;
    return;
  }

  reorderBody.innerHTML = lastReorderRows.map(row =>
    `<tr>${columns.map(([key]) => {
      const value = row[key];

      const formatted = typeof value === "number"
        ? key === "Average_Daily_Demand"
          ? value.toFixed(2)
          : value.toLocaleString("en-IN")
        : value;

      return `<td>${escapeHTML(formatted ?? "")}</td>`;
    }).join("")}</tr>`
  ).join("");
}

// Render the sales charts.
function renderCharts(data) {
  const topCanvas = $("topChart");
  const trendCanvas = $("trendChart");

  if (!topCanvas || !trendCanvas) {
    console.error("Sales chart elements are missing.");
    return;
  }

  if (topChartInstance) {
    topChartInstance.destroy();
    topChartInstance = null;
  }

  if (trendChartInstance) {
    trendChartInstance.destroy();
    trendChartInstance = null;
  }

  const top = data.top_selling || [];

  topChartInstance = new Chart(topCanvas, {
    type: "bar",
    data: {
      labels: top.map(p => p.Product_Name || p.Product_ID),
      datasets: [{
        label: "Units sold",
        data: top.map(p => p.Total_Units_Sold),
        backgroundColor: "#008b8b"
      }]
    },
    options: {
      responsive: true,
      indexAxis: "y",
      animation: false,
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });

  const trend = data.daily_sales || [];

  trendChartInstance = new Chart(trendCanvas, {
    type: "line",
    data: {
      labels: trend.map(row => row.Date),
      datasets: [{
        label: "Units sold",
        data: trend.map(row => row.Units_Sold),
        borderColor: "#008b8b",
        backgroundColor: "#008b8b",
        tension: 0,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      animation: false,
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}

// Render Admin-only historical profit insights.
function renderProfit(profit) {
  if (currentUser?.role !== "admin") {
    return;
  }

  const profitMessage = $("profitMessage");
  const profitTableBody = $("profitTableBody");

  if (!profitMessage || !profitTableBody) {
    console.error("Profit Insights HTML elements are missing.");
    return;
  }

  if (!profit || !profit.available) {
    profitMessage.textContent =
      profit?.message ||
      "Upload both datasets with unit costs to calculate profit.";

    profitTableBody.innerHTML = `
      <tr>
        <td class="empty" colspan="6">
          Profit data is not available.
        </td>
      </tr>`;

    return;
  }

  const summary = profit.summary || {};

  $("grossProfit").textContent = money(summary.gross_profit);

  $("profitMargin").textContent =
    `${Number(summary.profit_margin_percent || 0).toFixed(2)}%`;

  $("profitRevenue").textContent = money(summary.total_revenue);

  $("profitCost").textContent =
    money(summary.cost_of_goods_sold);

  const rows = profit.top_products || [];

  if (!rows.length) {
    profitTableBody.innerHTML = `
      <tr>
        <td class="empty" colspan="6">
          No matched product profit data.
        </td>
      </tr>`;

    return;
  }

  profitTableBody.innerHTML = rows.map((product, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${escapeHTML(product.Product_ID)}</td>
      <td>${escapeHTML(product.Product_Name)}</td>
      <td>${Number(product.Units_Sold || 0).toLocaleString("en-IN")}</td>
      <td>${money(product.Gross_Profit)}</td>
      <td>${Number(product.Profit_Margin_Percent || 0).toFixed(2)}%</td>
    </tr>
  `).join("");

  profitMessage.textContent =
    "Historical gross profit from uploaded sales. It excludes operating expenses and taxes.";
}

// Analyze uploaded inventory and sales datasets.
$("uploadForm").addEventListener("submit", async event => {
  event.preventDefault();

  const inventoryFile = $("inventoryFile").files[0];
  const salesFile = $("salesFile").files[0];

  if (!inventoryFile) {
    setMessage("Please select an inventory CSV file.", "error");
    return;
  }

  const formData = new FormData();

  formData.append("inventory", inventoryFile);

  if (salesFile) {
    formData.append("sales", salesFile);
  }

  $("analyzeButton").disabled = true;

  setMessage("Uploading and analyzing datasets...");

  try {
    const response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      body: formData,
      credentials: "include"
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Analysis failed.");
    }

    const summary = result.summary || {};

    $("productCount").textContent =
      Number(summary.inventory_products || 0).toLocaleString("en-IN");

    $("reorderCount").textContent =
      Number(summary.products_to_reorder || 0).toLocaleString("en-IN");

    $("stockTotal").textContent =
      Number(summary.total_units_in_stock || 0).toLocaleString("en-IN");

    $("unitsSold").textContent =
      summary.total_units_sold == null
        ? "—"
        : Number(summary.total_units_sold).toLocaleString("en-IN");

    // Stock replenishment list.
    renderReplenishment(result.replenishment || []);

    // Top-selling and low-selling products.
    const salesColumns = [
      {
        key: "Product_ID"
      },
      {
        key: "Product_Name"
      },
      {
        key: "Total_Units_Sold",
        format: value => Number(value).toLocaleString("en-IN")
      }
    ];

    renderTableRows(
      "topBody",
      result.top_selling,
      salesColumns,
      "Sales data not uploaded."
    );

    renderTableRows(
      "lowBody",
      result.low_selling,
      salesColumns,
      "Sales data not uploaded."
    );

    // Charts remain unchanged.
    renderCharts(result);

    // Only Admin can view profit insights.
    if (currentUser?.role === "admin") {
      renderProfit(result.profit_insights);
    }

    setMessage(
      result.message || "Analysis completed.",
      "success"
    );

  } catch (error) {
    console.error("Dataset analysis failed:", error);

    setMessage(
      error.message ||
      "Could not connect to the backend. Check that Flask is running.",
      "error"
    );
  } finally {
    $("analyzeButton").disabled = false;
  }
});

// Download the stock replenishment list as CSV.
$("downloadReorder").addEventListener("click", () => {
  if (!lastReorderRows.length) {
    return;
  }

  const columns = Object.keys(lastReorderRows[0]);

  const escapeCell = value =>
    `"${String(value ?? "").replace(/"/g, '""')}"`;

  const csv = [
    columns.join(","),
    ...lastReorderRows.map(row =>
      columns.map(key => escapeCell(row[key])).join(",")
    )
  ].join("\n");

  const url = URL.createObjectURL(
    new Blob([csv], {
      type: "text/csv;charset=utf-8;"
    })
  );

  const link = document.createElement("a");

  link.href = url;
  link.download = "stock_replenishment_list.csv";

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
});

// Clear the dashboard results.
$("clearButton").addEventListener("click", () => {
  $("uploadForm").reset();

  [
    "productCount",
    "reorderCount",
    "stockTotal",
    "unitsSold"
  ].forEach(id => {
    $(id).textContent = "—";
  });

  // Reset stock replenishment.
  renderReplenishment([]);

  // Reset top-selling products.
  renderTableRows(
    "topBody",
    [],
    [
      { key: "Product_ID" },
      { key: "Product_Name" },
      { key: "Total_Units_Sold" }
    ],
    "Sales data not uploaded."
  );

  // Reset low-selling products.
  renderTableRows(
    "lowBody",
    [],
    [
      { key: "Product_ID" },
      { key: "Product_Name" },
      { key: "Total_Units_Sold" }
    ],
    "Sales data not uploaded."
  );

  // Clear chart instances.
  if (topChartInstance) {
    topChartInstance.destroy();
    topChartInstance = null;
  }

  if (trendChartInstance) {
    trendChartInstance.destroy();
    trendChartInstance = null;
  }

  // Reset Admin-only profit results.
  if (currentUser?.role === "admin") {
    [
      "grossProfit",
      "profitMargin",
      "profitRevenue",
      "profitCost"
    ].forEach(id => {
      $(id).textContent = "—";
    });

    $("profitTableBody").innerHTML = `
      <tr>
        <td class="empty" colspan="6">
          Upload inventory and sales CSVs to calculate profit insights.
        </td>
      </tr>`;

    $("profitMessage").textContent = "";
  }

  setMessage("Results cleared.");
});

// Log out the current user.
$("logoutButton").addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      credentials: "include"
    });
  } catch (error) {
    console.error("Logout request failed:", error);
  } finally {
    window.location.replace("login.html");
  }
});

// Start the dashboard.
initDashboard();

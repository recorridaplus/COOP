document.addEventListener("DOMContentLoaded", () => {
    let allDiscrepancies = [];
    let isProcessing = false;

    const searchInput = document.getElementById("searchFilter");
    const spSelect = document.getElementById("supermarketFilter");
    const alertSelect = document.getElementById("alertFilter");
    const grid = document.getElementById("discrepanciesGrid");
    const emptyState = document.getElementById("emptyState");
    const resultsCount = document.getElementById("resultsCount");

    const btnRunFast = document.getElementById("btnRunFast");
    const btnRunFull = document.getElementById("btnRunFull");
    const spinnerContainer = document.getElementById("spinnerContainer");
    const spinnerLabel = document.getElementById("spinnerLabel");

    async function loadReportData() {
        try {
            const resp = await fetch("/api/report");
            const data = await resp.json();

            document.getElementById("statTotalOfficial").innerText = data.total_official_products || 0;
            allDiscrepancies = data.discrepancies || [];

            document.getElementById("statTotalDiscrepancies").innerText = allDiscrepancies.length;

            const redCount = allDiscrepancies.filter(d => d.alert_level === "RED").length;
            const yellowCount = allDiscrepancies.filter(d => d.alert_level === "YELLOW").length;

            document.getElementById("statRedAlerts").innerText = redCount;
            document.getElementById("statYellowAlerts").innerText = yellowCount;

            renderDiscrepancies();
        } catch (err) {
            console.error("Error cargando reporte:", err);
        }
    }

    function renderDiscrepancies() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const selectedSp = spSelect.value;
        const selectedAlert = alertSelect.value;

        const filtered = allDiscrepancies.filter(item => {
            const offName = item.conaprole_product.name.toLowerCase();
            const spName = item.supermarket_product.name.toLowerCase();

            const matchesSearch = !searchTerm || offName.includes(searchTerm) || spName.includes(searchTerm);
            const matchesSp = selectedSp === "ALL" || item.supermarket === selectedSp;
            const matchesAlert = selectedAlert === "ALL" || item.alert_level === selectedAlert;

            return matchesSearch && matchesSp && matchesAlert;
        });

        resultsCount.innerText = `Mostrando ${filtered.length} de ${allDiscrepancies.length} discrepancias`;

        if (filtered.length === 0) {
            grid.innerHTML = "";
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");
        grid.innerHTML = filtered.map(item => createCardHtml(item)).join("");
    }

    function createCardHtml(item) {
        const type = item.discrepancy_type || (item.alert_level === "RED" ? "APOCRYPHAL_IMAGE" : "DIFFERENT_IMAGE");

        let badgeClass = "badge-yellow-tag";
        let badgeLabel = "🟡 FOTO DIFERENTE";
        let cardBorderClass = "badge-yellow";

        if (type === "APOCRYPHAL_IMAGE" || item.alert_level === "RED") {
            badgeClass = "badge-red-tag";
            badgeLabel = "🔴 FOTO APÓCRIFA (CM)";
            cardBorderClass = "badge-red";
        } else if (type === "NAME_DISCREPANCY" || item.alert_level === "BLUE") {
            badgeClass = "badge-blue-tag";
            badgeLabel = "📝 DIFERENCIA DE NOMBRE";
            cardBorderClass = "badge-blue";
        } else {
            badgeClass = "badge-yellow-tag";
            badgeLabel = "🟡 FOTO DIFERENTE";
            cardBorderClass = "badge-yellow";
        }

        const offImg = item.conaprole_product.image_url || "/static/no-img.png";
        const spImg = item.supermarket_product.image_url || "/static/no-img.png";

        const offUrl = item.conaprole_product.url || "#";
        const spUrl = item.supermarket_product.url || "#";

        const simScore = item.name_comparison ? item.name_comparison.similarity_score : 100;

        return `
            <div class="comparison-card ${cardBorderClass}">
                <div class="card-header-bar">
                    <span class="sp-tag">🏪 ${item.supermarket}</span>
                    <span class="badge ${badgeClass}">${badgeLabel}</span>
                </div>
                <div class="side-by-side">
                    <!-- Conaprole Oficial -->
                    <div class="product-side">
                        <span class="side-label">OFICIAL CONAPROLE</span>
                        <a href="${offUrl}" target="_blank" rel="noopener noreferrer" class="img-container clickable-img" title="Ver ficha en Conaprole">
                            <img src="${offImg}" alt="${item.conaprole_product.name}" onerror="this.src='https://via.placeholder.com/140?text=Sin+Imagen'" />
                        </a>
                        <span class="product-name">${item.conaprole_product.name}</span>
                        <span class="match-bar">Cat: ${item.conaprole_product.category}</span>
                        <a href="${offUrl}" target="_blank" rel="noopener noreferrer" class="source-link">
                            🌐 Ver Ficha Oficial ↗
                        </a>
                    </div>

                    <!-- Supermercado -->
                    <div class="product-side">
                        <span class="side-label sp-side">PUBLICACIÓN SUPERMERCADO</span>
                        <a href="${spUrl}" target="_blank" rel="noopener noreferrer" class="img-container clickable-img" title="Ver en sitio de ${item.supermarket}">
                            <img src="${spImg}" alt="${item.supermarket_product.name}" onerror="this.src='https://via.placeholder.com/140?text=Sin+Imagen'" />
                        </a>
                        <span class="product-name">${item.supermarket_product.name}</span>
                        <span class="match-bar">Similitud nombre: <strong>${simScore}%</strong></span>
                        <a href="${spUrl}" target="_blank" rel="noopener noreferrer" class="source-link sp-source-link">
                            🛒 Ver en ${item.supermarket} ↗
                        </a>
                    </div>
                </div>
            </div>
        `;
    }

    function setProcessingState(active, labelText = "Procesando...") {
        isProcessing = active;
        btnRunFast.disabled = active;
        btnRunFull.disabled = active;

        if (active) {
            spinnerLabel.innerText = labelText;
            spinnerContainer.classList.remove("hidden");
        } else {
            spinnerContainer.classList.add("hidden");
        }
    }

    btnRunFast.addEventListener("click", async () => {
        if (isProcessing) return;
        setProcessingState(true, "Re-comparando datos...");
        try {
            await fetch("/api/run-comparison", { method: "POST" });
            await loadReportData();
        } catch (e) {
            alert("Error ejecutando re-comparación rápida.");
        } finally {
            setProcessingState(false);
        }
    });

    btnRunFull.addEventListener("click", async () => {
        if (isProcessing) return;
        setProcessingState(true, "Iniciando recorrido completo...");

        try {
            const startResp = await fetch("/api/run-full-rescrape", { method: "POST" });
            const startData = await startResp.json();

            if (startData.status === "started" || startData.status === "busy") {
                const pollInterval = setInterval(async () => {
                    try {
                        const statusResp = await fetch("/api/status");
                        const statusData = await statusResp.json();

                        if (statusData.is_running) {
                            spinnerLabel.innerText = statusData.current_step || "Scrapeando supermercados...";
                        } else {
                            clearInterval(pollInterval);
                            await loadReportData();
                            setProcessingState(false);
                        }
                    } catch (err) {
                        clearInterval(pollInterval);
                        setProcessingState(false);
                    }
                }, 3000);
            } else {
                setProcessingState(false);
            }
        } catch (e) {
            alert("Error iniciando el recorrido completo.");
            setProcessingState(false);
        }
    });

    searchInput.addEventListener("input", renderDiscrepancies);
    spSelect.addEventListener("change", renderDiscrepancies);
    alertSelect.addEventListener("change", renderDiscrepancies);

    loadReportData();
});

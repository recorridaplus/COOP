document.addEventListener("DOMContentLoaded", () => {
    let allDiscrepancies = [];

    const searchInput = document.getElementById("searchFilter");
    const spSelect = document.getElementById("supermarketFilter");
    const alertSelect = document.getElementById("alertFilter");
    const grid = document.getElementById("discrepanciesGrid");
    const emptyState = document.getElementById("emptyState");
    const resultsCount = document.getElementById("resultsCount");
    const btnRun = document.getElementById("btnRun");

    async function loadReportData() {
        try {
            const resp = await fetch("/api/report");
            const data = await resp.json();

            // Actualizar Stats
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
        const isRed = item.alert_level === "RED";
        const badgeClass = isRed ? "badge-red-tag" : "badge-yellow-tag";
        const badgeLabel = isRed ? "🔴 FOTO APÓCRIFA (CM)" : "🟡 IMAGEN DIFERENTE";
        const cardBorderClass = isRed ? "badge-red" : "badge-yellow";

        const offImg = item.conaprole_product.image_url || "/static/no-img.png";
        const spImg = item.supermarket_product.image_url || "/static/no-img.png";

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
                        <div class="img-container">
                            <img src="${offImg}" alt="${item.conaprole_product.name}" onerror="this.src='https://via.placeholder.com/140?text=Sin+Imagen'" />
                        </div>
                        <span class="product-name">${item.conaprole_product.name}</span>
                        <span class="match-bar">Cat: ${item.conaprole_product.category}</span>
                    </div>

                    <!-- Supermercado -->
                    <div class="product-side">
                        <span class="side-label sp-side">PUBLICACIÓN SUPERMERCADO</span>
                        <div class="img-container">
                            <img src="${spImg}" alt="${item.supermarket_product.name}" onerror="this.src='https://via.placeholder.com/140?text=Sin+Imagen'" />
                        </div>
                        <span class="product-name">${item.supermarket_product.name}</span>
                        <span class="match-bar">Similitud nombre: <strong>${simScore}%</strong></span>
                    </div>
                </div>
            </div>
        `;
    }

    // Event listeners
    searchInput.addEventListener("input", renderDiscrepancies);
    spSelect.addEventListener("change", renderDiscrepancies);
    alertSelect.addEventListener("change", renderDiscrepancies);

    btnRun.addEventListener("click", async () => {
        btnRun.disabled = true;
        btnRun.innerText = "⏳ Ejecutando...";
        try {
            await fetch("/api/run-comparison", { method: "POST" });
            await loadReportData();
        } catch (e) {
            alert("Error ejecutando comparación.");
        } finally {
            btnRun.disabled = false;
            btnRun.innerText = "🔄 Re-evaluar Ahora";
        }
    });

    // Cargar inicial
    loadReportData();
});

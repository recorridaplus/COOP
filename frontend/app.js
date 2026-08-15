document.addEventListener("DOMContentLoaded", () => {
    let allDiscrepancies = [];
    let allMatches = [];
    let activeTab = "DISCREPANCIES"; // "DISCREPANCIES" or "MATCHES"
    let isProcessing = false;

    const searchInput = document.getElementById("searchFilter");
    const spSelect = document.getElementById("supermarketFilter");
    const alertSelect = document.getElementById("alertFilter");
    const grid = document.getElementById("discrepanciesGrid");
    const emptyState = document.getElementById("emptyState");
    const resultsCount = document.getElementById("resultsCount");

    const tabDiscrepancies = document.getElementById("tabDiscrepancies");
    const tabMatches = document.getElementById("tabMatches");
    const countDiscrepanciesTab = document.getElementById("countDiscrepanciesTab");
    const countMatchesTab = document.getElementById("countMatchesTab");

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
            allMatches = data.matches_list || [];

            document.getElementById("statTotalMatches").innerText = allMatches.length;
            document.getElementById("statTotalDiscrepancies").innerText = allDiscrepancies.length;

            countDiscrepanciesTab.innerText = allDiscrepancies.length;
            countMatchesTab.innerText = allMatches.length;

            const redCount = allDiscrepancies.filter(d => d.alert_level === "RED").length;
            const yellowCount = allDiscrepancies.filter(d => d.alert_level === "YELLOW").length;

            document.getElementById("statRedAlerts").innerText = redCount;
            document.getElementById("statYellowAlerts").innerText = yellowCount;

            renderGrid();
        } catch (err) {
            console.error("Error cargando reporte:", err);
        }
    }

    function renderGrid() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const selectedSp = spSelect.value;
        const selectedAlert = alertSelect.value;

        const currentDataset = activeTab === "DISCREPANCIES" ? allDiscrepancies : allMatches;

        const filtered = currentDataset.filter(item => {
            const offName = item.conaprole_product.name.toLowerCase();
            const spName = item.supermarket_product.name.toLowerCase();

            const matchesSearch = !searchTerm || offName.includes(searchTerm) || spName.includes(searchTerm);
            const matchesSp = selectedSp === "ALL" || item.supermarket === selectedSp;
            
            let matchesAlert = true;
            if (activeTab === "DISCREPANCIES") {
                matchesAlert = selectedAlert === "ALL" || item.alert_level === selectedAlert;
            }

            return matchesSearch && matchesSp && matchesAlert;
        });

        const tabNameText = activeTab === "DISCREPANCIES" ? "discrepancias" : "coincidencias correctas";
        resultsCount.innerText = `Mostrando ${filtered.length} de ${currentDataset.length} ${tabNameText}`;

        if (filtered.length === 0) {
            grid.innerHTML = "";
            emptyState.classList.remove("hidden");
            return;
        }

        emptyState.classList.add("hidden");
        grid.innerHTML = filtered.map((item, index) => createCardHtml(item, index)).join("");

        attachCardInteractions();
    }

    function createCardHtml(item, index) {
        let badgeClass = "badge-yellow-tag";
        let badgeLabel = "🟡 FOTO DIFERENTE";
        let cardBorderClass = "badge-yellow";

        if (activeTab === "MATCHES") {
            badgeClass = "badge-green-tag";
            badgeLabel = "🟢 COINCIDENCIA VERIFICADA";
            cardBorderClass = "badge-green";
        } else {
            const type = item.discrepancy_type || (item.alert_level === "RED" ? "APOCRYPHAL_IMAGE" : "DIFFERENT_IMAGE");

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
        }

        const offImg = item.conaprole_product.image_url || "/static/no-img.png";
        const spImg = item.supermarket_product.image_url || "/static/no-img.png";

        const offUrl = item.conaprole_product.url || "#";
        const spUrl = item.supermarket_product.url || "#";

        const simScore = item.name_comparison ? item.name_comparison.similarity_score : 100;

        const aiHtml = item.ai_verification && item.ai_verification.explanation ? `
            <div class="ai-explanation-bar" style="margin-top: 12px; padding: 8px 12px; background: rgba(124, 58, 237, 0.12); border-left: 3px solid #a855f7; border-radius: 6px; font-size: 0.85rem; color: #e2e8f0; grid-column: 1 / -1;">
                <strong style="color: #c084fc;">🤖 Dictamen IA:</strong> ${item.ai_verification.explanation}
            </div>
        ` : '';

        return `
            <div class="comparison-card ${cardBorderClass}" data-card-idx="${index}">
                <div class="card-header-bar">
                    <span class="sp-tag">🏪 ${item.supermarket}</span>
                    <span class="badge ${badgeClass}">${badgeLabel}</span>
                </div>

                <div class="side-by-side-row">
                    <!-- Columna Izquierda: Ficha Oficial -->
                    <div class="info-column left-column">
                        <span class="column-badge">OFICIAL CONAPROLE</span>
                        <span class="product-name">${item.conaprole_product.name}</span>
                        <span class="match-bar">Cat: ${item.conaprole_product.category}</span>
                        <a href="${offUrl}" target="_blank" rel="noopener noreferrer" class="source-link">
                            🌐 Ficha Oficial ↗
                        </a>
                    </div>

                    <!-- Columna Centro: Comparador de Fotos Ultracercano -->
                    <div class="tight-compare-wrapper">
                        <div class="tight-stage">
                            <!-- Foto Oficial -->
                            <div class="tight-img-box img-off-box" data-off-url="${offImg}" data-sp-url="${spImg}" title="Haz clic o mantén presionado para alternar foto">
                                <span class="img-tag-badge off-badge">OFICIAL</span>
                                <img src="${offImg}" class="card-img-off" alt="Oficial" onerror="this.src='https://via.placeholder.com/150?text=Sin+Imagen'" />
                            </div>

                            <div class="vs-divider">
                                <span class="vs-badge">VS</span>
                            </div>

                            <!-- Foto Supermercado -->
                            <div class="tight-img-box img-sp-box" data-off-url="${offImg}" data-sp-url="${spImg}" title="Haz clic o mantén presionado para alternar foto">
                                <span class="img-tag-badge">${item.supermarket.toUpperCase()}</span>
                                <img src="${spImg}" class="card-img-sp" alt="Supermercado" onerror="this.src='https://via.placeholder.com/150?text=Sin+Imagen'" />
                            </div>
                        </div>
                        <span class="press-hint">👆 Haz clic o mantén presionado para alternar</span>
                    </div>

                    <!-- Columna Derecha: Ficha Supermercado -->
                    <div class="info-column right-column">
                        <span class="column-badge sp-badge">PUBLICACIÓN SUPERMERCADO</span>
                        <span class="product-name">${item.supermarket_product.name}</span>
                        <span class="match-bar">Similitud: <strong>${simScore}%</strong></span>
                        <a href="${spUrl}" target="_blank" rel="noopener noreferrer" class="source-link sp-source-link">
                            🛒 En ${item.supermarket} ↗
                        </a>
                    </div>
                </div>
                ${aiHtml}
            </div>
        `;
    }

    function attachCardInteractions() {
        document.querySelectorAll(".tight-img-box").forEach(box => {
            const imgEl = box.querySelector("img");
            const offUrl = box.getAttribute("data-off-url");
            const spUrl = box.getAttribute("data-sp-url");

            const isOffBox = box.classList.contains("img-off-box");

            function showOther() {
                box.classList.add("is-pressed");
                imgEl.src = isOffBox ? spUrl : offUrl;
            }

            function restoreOriginal() {
                box.classList.remove("is-pressed");
                imgEl.src = isOffBox ? offUrl : spUrl;
            }

            box.addEventListener("mousedown", showOther);
            box.addEventListener("mouseup", restoreOriginal);
            box.addEventListener("mouseleave", restoreOriginal);

            box.addEventListener("touchstart", (e) => { e.preventDefault(); showOther(); });
            box.addEventListener("touchend", restoreOriginal);
        });
    }

    // Manejo de Solapas (Tabs)
    tabDiscrepancies.addEventListener("click", () => {
        activeTab = "DISCREPANCIES";
        tabDiscrepancies.classList.add("active");
        tabMatches.classList.remove("active");
        alertSelect.disabled = false;
        renderGrid();
    });

    tabMatches.addEventListener("click", () => {
        activeTab = "MATCHES";
        tabMatches.classList.add("active");
        tabDiscrepancies.classList.remove("active");
        alertSelect.disabled = true;
        renderGrid();
    });

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
                            if (statusData.current_step && statusData.current_step.startsWith("Error")) {
                                alert("⚠️ Ocurrió un inconveniente al ejecutar el recorrido completo:\n\n" + statusData.current_step + "\n\nSi estás usando la versión en Vercel, recuerda que el scraping de supermercados con navegador debe ejecutarse localmente en tu PC.");
                            } else {
                                await loadReportData();
                            }
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
            alert("Error iniciando el recorrido completo. Verifica la conexión con el servidor backend.");
            setProcessingState(false);
        }
    });

    searchInput.addEventListener("input", renderGrid);
    spSelect.addEventListener("change", renderGrid);
    alertSelect.addEventListener("change", renderGrid);

    loadReportData();
});

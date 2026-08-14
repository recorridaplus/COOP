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

    // Modal elements
    const pixelModal = document.getElementById("pixelModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const modalProductName = document.getElementById("modalProductName");
    const modalOffImg = document.getElementById("modalOffImg");
    const modalSpImg = document.getElementById("modalSpImg");
    const opacitySlider = document.getElementById("opacitySlider");
    const opacityVal = document.getElementById("opacityVal");
    const btnHoldCompare = document.getElementById("btnHoldCompare");

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
        grid.innerHTML = filtered.map((item, index) => createCardHtml(item, index)).join("");

        // Activar manejadores de eventos interactivos en las tarjetas recién renderizadas
        attachCardInteractions(filtered);
    }

    function createCardHtml(item, index) {
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
            <div class="comparison-card ${cardBorderClass}" data-card-idx="${index}">
                <div class="card-header-bar">
                    <span class="sp-tag">🏪 ${item.supermarket}</span>
                    <span class="badge ${badgeClass}">${badgeLabel}</span>
                </div>

                <div class="side-by-side">
                    <!-- Tight Stage comparador ultracercano -->
                    <div class="tight-compare-wrapper">
                        <div class="tight-stage">
                            <!-- Foto Oficial -->
                            <div class="tight-img-box img-off-box" data-off-url="${offImg}" data-sp-url="${spImg}" title="Mantén presionado para alternar foto">
                                <span class="img-tag-badge off-badge">OFICIAL</span>
                                <img src="${offImg}" class="card-img-off" alt="Oficial" onerror="this.src='https://via.placeholder.com/150?text=Sin+Imagen'" />
                            </div>

                            <div class="vs-divider">
                                <span class="vs-badge">VS</span>
                            </div>

                            <!-- Foto Supermercado -->
                            <div class="tight-img-box img-sp-box" data-off-url="${offImg}" data-sp-url="${spImg}" title="Mantén presionado para alternar foto">
                                <span class="img-tag-badge">${item.supermarket.toUpperCase()}</span>
                                <img src="${spImg}" class="card-img-sp" alt="Supermercado" onerror="this.src='https://via.placeholder.com/150?text=Sin+Imagen'" />
                            </div>
                        </div>

                        <span class="press-hint">👆 Haz clic o mantén presionado para alternar fotos</span>

                        <button class="btn btn-secondary btn-pixel" data-card-idx="${index}">
                            🔍 Comparar Pixel a Pixel
                        </button>
                    </div>

                    <!-- Datos del producto -->
                    <div class="card-info-grid">
                        <div class="info-column">
                            <span class="product-name">${item.conaprole_product.name}</span>
                            <span class="match-bar">Cat: ${item.conaprole_product.category}</span>
                            <a href="${offUrl}" target="_blank" rel="noopener noreferrer" class="source-link">
                                🌐 Ficha Oficial ↗
                            </a>
                        </div>
                        <div class="info-column">
                            <span class="product-name">${item.supermarket_product.name}</span>
                            <span class="match-bar">Similitud: <strong>${simScore}%</strong></span>
                            <a href="${spUrl}" target="_blank" rel="noopener noreferrer" class="source-link sp-source-link">
                                🛒 En ${item.supermarket} ↗
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function attachCardInteractions(filteredItems) {
        // Manejadores de Presionar y Mantener en las fotos de las tarjetas
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

        // Botón "Comparar Pixel a Pixel" -> abre el modal
        document.querySelectorAll(".btn-pixel").forEach(btn => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.getAttribute("data-card-idx"));
                const item = filteredItems[idx];
                if (item) {
                    openPixelModal(item);
                }
            });
        });
    }

    function openPixelModal(item) {
        modalProductName.innerText = `${item.conaprole_product.name} (vs ${item.supermarket})`;
        modalOffImg.src = item.conaprole_product.image_url || "/static/no-img.png";
        modalSpImg.src = item.supermarket_product.image_url || "/static/no-img.png";

        opacitySlider.value = 50;
        opacityVal.innerText = "50%";
        modalSpImg.style.opacity = 0.5;

        pixelModal.classList.remove("hidden");
    }

    function closePixelModal() {
        pixelModal.classList.add("hidden");
    }

    closeModalBtn.addEventListener("click", closePixelModal);
    pixelModal.addEventListener("click", (e) => {
        if (e.target === pixelModal) closePixelModal();
    });

    opacitySlider.addEventListener("input", () => {
        const val = opacitySlider.value;
        opacityVal.innerText = `${val}%`;
        modalSpImg.style.opacity = val / 100;
    });

    // Mantener presionado en el Modal para alternar al 100% de opacidad
    function modalPressStart() {
        modalSpImg.style.opacity = 1.0;
    }

    function modalPressEnd() {
        modalSpImg.style.opacity = opacitySlider.value / 100;
    }

    btnHoldCompare.addEventListener("mousedown", modalPressStart);
    btnHoldCompare.addEventListener("mouseup", modalPressEnd);
    btnHoldCompare.addEventListener("mouseleave", modalPressEnd);

    btnHoldCompare.addEventListener("touchstart", (e) => { e.preventDefault(); modalPressStart(); });
    btnHoldCompare.addEventListener("touchend", modalPressEnd);

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

window.AssetFlowApp = (() => {
    const API_BASE = "https://inventory-monetisation-system.onrender.com";
    const pageMap = {
        inventory: "./index.html",
        analytics: "./analytics.html",
        monetization: "./monetization.html",
        orchestration: "./orchestration.html",
        settings: "./settings.html",
        login: "./login.html",
        inventory_view: "./inventory_view.html",
        base: "./base.html",
    };

    function formatCurrency(value) {
        const numeric = Number(value || 0);
        return `Rs. ${numeric.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function defaultProfile() {
        return {
            name: "Alex Rivera",
            email: "alex@example.com",
            company: "AssetFlow",
        };
    }

    function loadProfile() {
        try {
            const stored = localStorage.getItem("assetflowSettingsProfile");
            return stored ? { ...defaultProfile(), ...JSON.parse(stored) } : defaultProfile();
        } catch (error) {
            return defaultProfile();
        }
    }

    async function fetchJson(path, options) {
        const response = await fetch(`${API_BASE}${path}`, options);
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        return response.json();
    }

    return {
        API_BASE,
        pageMap,
        formatCurrency,
        escapeHtml,
        loadProfile,
        fetchJson,
    };
})();

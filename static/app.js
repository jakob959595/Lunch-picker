async function loadData() {
    try {
        const response = await fetch("/api/data");
        const data = await response.json();

        document.getElementById("status").textContent =
            "Status: " + data.status;

        document.getElementById("aura").textContent =
            "Aura: " + data.aura;

    } catch (e) {
        document.getElementById("status").textContent =
            "Napaka pri nalaganju";
    }
}

loadData();
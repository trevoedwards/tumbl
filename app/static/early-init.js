(function () {
    "use strict";
    try {
        var settings = JSON.parse(localStorage.getItem("tumbl.settings") || "{}");
        if (settings.darkMode) {
            document.documentElement.classList.add("dark-mode");
        }
    } catch (e) {}
})();

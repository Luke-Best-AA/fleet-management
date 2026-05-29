/* Auto-format UK registration plates: LL##_LLL (space after digits on blur) */
(function () {
    var el = document.getElementById("registration_number");
    if (!el) return;

    el.addEventListener("blur", function () {
        var v = el.value.replace(/\s+/g, "").toUpperCase();
        // UK format: 2 letters, 2 digits, 3 letters
        if (/^[A-Z]{2}\d{2}[A-Z]{3}$/.test(v)) {
            el.value = v.slice(0, 4) + " " + v.slice(4);
        }
    });
})();

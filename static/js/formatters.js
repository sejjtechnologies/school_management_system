// formatters.js
// Converts names/places to Title Case (capitalizes first letter of each word and after - or ')
(function () {
    'use strict';

    function titleCase(str) {
        if (!str) return '';
        // normalize whitespace and lowercase everything first
        var s = String(str).trim().replace(/\s+/g, ' ').toLowerCase();
        // Capitalize after start, space, hyphen or apostrophe
        return s.replace(/(^\w)|(\s\w)|(-\w)|('\w)/g, function (match) {
            return match.toUpperCase();
        });
    }

    function formatField(field) {
        if (!field || field.readOnly || field.disabled) return;
        var v = field.value;
        if (!v) return;
        field.value = titleCase(v);
    }

    function bindSentenceCase(field) {
        if (!field) return;
        // Use blur/change for stable formatting so caret isn't jumpy while typing
        field.addEventListener('blur', function () { formatField(field); });
        field.addEventListener('change', function () { formatField(field); });
        // handle paste
        field.addEventListener('paste', function () { setTimeout(function () { formatField(field); }, 0); });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var inputs = document.querySelectorAll('input.sentence-case');
        if (!inputs.length) return;
        inputs.forEach(function (el) { bindSentenceCase(el); });
    });
})();

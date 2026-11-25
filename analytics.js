// Shared Google Analytics 4 (GA4) loader for Kai Kleinbard's portfolio sites.
// Property: Kai Portfolio (properties/565841989) | Measurement ID: G-NVX0XJGFFL
(function () {
  if (typeof window === 'undefined' || window.location.protocol === 'file:') return;
  if (window.__KAI_GA_INITIALIZED__) return;
  window.__KAI_GA_INITIALIZED__ = true;

  var GA_ID = 'G-NVX0XJGFFL';

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () {
    window.dataLayer.push(arguments);
  };

  var script = document.createElement('script');
  script.async = true;
  script.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(script);

  window.gtag('js', new Date());
  window.gtag('config', GA_ID, {
    send_page_view: true
  });
})();

(() => {
  'use strict';
  const btn = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('mobile-backdrop');
  const close = () => { if (!sidebar || !btn || !backdrop) return; sidebar.classList.remove('sidebar-open'); backdrop.hidden = true; btn.setAttribute('aria-expanded', 'false'); document.body.classList.remove('nav-open'); };
  btn?.addEventListener('click', () => { const open = !sidebar.classList.contains('sidebar-open'); sidebar.classList.toggle('sidebar-open', open); backdrop.hidden = !open; btn.setAttribute('aria-expanded', String(open)); document.body.classList.toggle('nav-open', open); });
  backdrop?.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  const input = document.getElementById('module-search');
  const cards = Array.from(document.querySelectorAll('.module-card'));
  const filters = Array.from(document.querySelectorAll('.filter-tab'));
  const empty = document.getElementById('no-results');
  let filter = 'all';
  const update = () => {
    const query = (input?.value || '').trim().toLocaleLowerCase('fr');
    let count = 0;
    cards.forEach(card => {
      const matches = card.dataset.name.includes(query) && (filter === 'all' || card.dataset.method === filter);
      card.hidden = !matches;
      if (matches) count++;
    });
    if (empty) empty.hidden = count !== 0;
  };
  input?.addEventListener('input', update);
  filters.forEach(tab => tab.addEventListener('click', () => {
    filter = tab.dataset.filter;
    filters.forEach(t => { t.classList.toggle('active', t === tab); t.setAttribute('aria-pressed', String(t === tab)); });
    update();
  }));
})();

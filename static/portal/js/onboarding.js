(() => {
  const form = document.getElementById('onboarding-form');
  const steps = [...form.querySelectorAll('.onboarding-step')];
  const next = document.getElementById('next-step');
  const previous = document.getElementById('previous-step');
  const finish = document.getElementById('finish-onboarding');
  let current = Math.max(0, steps.findIndex(step => step.querySelector('.field-error')));
  const render = (focus = false) => {
    steps.forEach((step, i) => { step.hidden = i !== current; });
    document.querySelectorAll('[data-step-label]').forEach((label, i) => { label.classList.toggle('current', i === current); label.classList.toggle('complete', i < current); if (i === current) label.setAttribute('aria-current', 'step'); else label.removeAttribute('aria-current'); });
    previous.hidden = current === 0; next.hidden = current === steps.length - 1; finish.hidden = current !== steps.length - 1;
    document.getElementById('step-counter').textContent = `ÉTAPE 0${current + 1} / 03`;
    document.getElementById('step-progress').style.width = `${(current + 1) / steps.length * 100}%`;
    if (focus) { steps[current].querySelector('legend').setAttribute('tabindex', '-1'); steps[current].querySelector('legend').focus(); }
  };
  const valid = () => {
    if (current === 0) {
      const boxes = [...steps[0].querySelectorAll('input[type=checkbox]')];
      boxes[0].setCustomValidity(boxes.some(box => box.checked) ? '' : 'Choisissez au moins un sujet.');
      if (!boxes[0].reportValidity()) return false;
    }
    return [...steps[current].querySelectorAll('input, select')].every(input => input.reportValidity());
  };
  form.noValidate = true;
  form.addEventListener('change', () => { const box = steps[0].querySelector('input'); box.setCustomValidity(''); });
  next.addEventListener('click', () => { if (valid()) { current++; render(true); } });
  previous.addEventListener('click', () => { current--; render(true); });
  form.addEventListener('submit', event => {
    if (current < steps.length - 1) { event.preventDefault(); next.click(); return; }
    if (!valid()) event.preventDefault();
  });
  render();
})();

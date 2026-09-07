for (const group of document.querySelectorAll('[data-code-tabs]')) {
  const buttons = [...group.querySelectorAll('[data-tab]')];
  const panes = [...group.querySelectorAll('[data-pane]')];

  for (const button of buttons) {
    button.addEventListener('click', () => {
      buttons.forEach((item) => item.classList.toggle('active', item === button));
      panes.forEach((pane) => pane.classList.toggle('active', pane.dataset.pane === button.dataset.tab));
    });
  }
}

for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const pane = button.closest('.code-pane');
    const code = pane?.querySelector('code')?.textContent ?? '';
    try {
      await navigator.clipboard.writeText(code);
      const original = button.textContent;
      button.textContent = button.dataset.copied || 'Copied';
      setTimeout(() => { button.textContent = original; }, 1400);
    } catch {
      button.textContent = button.dataset.failed || 'Select text';
    }
  });
}

for (const group of document.querySelectorAll('[data-reading-path]')) {
  const steps = [...group.querySelectorAll('[data-reading-step]')];
  const panels = [...group.querySelectorAll('[data-reading-panel]')];

  const selectStep = (step, moveFocus = false) => {
    const key = step.dataset.readingStep;
    steps.forEach((item) => {
      const selected = item === step;
      item.classList.toggle('active', selected);
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => {
      const selected = panel.dataset.readingPanel === key;
      panel.classList.toggle('active', selected);
      panel.hidden = !selected;
    });
    if (moveFocus) step.focus();
  };

  steps.forEach((step, index) => {
    step.addEventListener('click', () => selectStep(step));
    step.addEventListener('keydown', (event) => {
      if (!['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = (index + 1) % steps.length;
      if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = (index - 1 + steps.length) % steps.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = steps.length - 1;
      selectStep(steps[next], true);
    });
  });
}

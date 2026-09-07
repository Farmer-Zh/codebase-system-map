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

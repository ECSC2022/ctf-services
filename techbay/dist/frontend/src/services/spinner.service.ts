export function hide() {
  document.querySelector('div.spinner-background')?.setAttribute('style', 'display: none');
}

export function show() {
  document.querySelector('div.spinner-background')?.removeAttribute('style');
}

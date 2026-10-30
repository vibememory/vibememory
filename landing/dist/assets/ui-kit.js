'use strict';

(() => {
  const focusableSelector = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');
  let flyoutReturnFocus = null;
  let confirmResolve = null;

  const focusables = container => [...container.querySelectorAll(focusableSelector)]
    .filter(element => !element.hidden && element.getClientRects().length);

  function setShellInert(inert) {
    document.querySelectorAll('[data-ui-shell]').forEach(element => {
      if (inert) element.setAttribute('inert', '');
      else element.removeAttribute('inert');
    });
  }

  function openModal(dialog) {
    if (!dialog || dialog.open) return;
    dialog.showModal();
    requestAnimationFrame(() => {
      const preferred = dialog.querySelector('[autofocus],input:not([type="hidden"]):not([disabled]),textarea:not([disabled]),select:not([disabled]),button[type="submit"]:not([disabled])');
      (preferred || focusables(dialog)[0] || dialog).focus();
    });
  }

  function closeModal(dialog, returnValue = '') {
    if (dialog?.open) dialog.close(returnValue);
  }

  function openFlyout({title, eyebrow = 'DETAIL', content = ''}) {
    const flyout = document.querySelector('#detail-dialog');
    const scrim = document.querySelector('#detail-scrim');
    if (!flyout || !scrim) return;
    flyoutReturnFocus = document.activeElement;
    flyout.querySelector('#detail-title').textContent = title;
    flyout.querySelector('#detail-kicker').textContent = eyebrow;
    flyout.querySelector('#detail-content').innerHTML = content;
    flyout.hidden = false;
    scrim.hidden = false;
    flyout.setAttribute('aria-hidden', 'false');
    setShellInert(true);
    document.body.classList.add('ui-layer-open');
    requestAnimationFrame(() => {
      flyout.classList.add('is-open');
      scrim.classList.add('is-open');
      (focusables(flyout)[0] || flyout).focus();
    });
  }

  function closeFlyout() {
    const flyout = document.querySelector('#detail-dialog');
    const scrim = document.querySelector('#detail-scrim');
    if (!flyout || flyout.hidden) return;
    flyout.classList.remove('is-open');
    scrim?.classList.remove('is-open');
    flyout.setAttribute('aria-hidden', 'true');
    setShellInert(false);
    document.body.classList.remove('ui-layer-open');
    window.setTimeout(() => {
      if (flyout.classList.contains('is-open')) return;
      flyout.hidden = true;
      if (scrim) scrim.hidden = true;
      flyout.querySelector('#detail-content')?.replaceChildren();
    }, 240);
    if (flyoutReturnFocus instanceof HTMLElement) flyoutReturnFocus.focus();
    flyoutReturnFocus = null;
  }

  function confirmAction({
    title = '계속할까요?',
    message = '',
    confirmLabel = '확인',
    cancelLabel = '취소',
    tone = 'default'
  } = {}) {
    const dialog = document.querySelector('#confirm-dialog');
    if (!dialog) return Promise.resolve(false);
    if (confirmResolve) confirmResolve(false);
    dialog.querySelector('#confirm-title').textContent = title;
    dialog.querySelector('#confirm-message').textContent = message;
    dialog.querySelector('#confirm-submit').textContent = confirmLabel;
    dialog.querySelector('#confirm-cancel').textContent = cancelLabel;
    dialog.dataset.tone = tone;
    dialog.returnValue = '';
    openModal(dialog);
    return new Promise(resolve => { confirmResolve = resolve; });
  }

  function settleConfirmation(accepted) {
    if (!confirmResolve) return;
    const resolve = confirmResolve;
    confirmResolve = null;
    resolve(accepted);
  }

  document.addEventListener('click', event => {
    if (event.target.closest('[data-ui-dismiss="flyout"]') || event.target.closest('#detail-scrim')) closeFlyout();
  });

  document.addEventListener('keydown', event => {
    const flyout = document.querySelector('#detail-dialog');
    if (!flyout || flyout.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeFlyout();
      return;
    }
    if (event.key !== 'Tab') return;
    const items = focusables(flyout);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    const dialog = document.querySelector('#confirm-dialog');
    if (!dialog) return;
    dialog.querySelector('form')?.addEventListener('submit', event => {
      event.preventDefault();
      closeModal(dialog, 'confirm');
    });
    dialog.querySelectorAll('[data-ui-confirm-cancel]').forEach(button => {
      button.addEventListener('click', () => closeModal(dialog, 'cancel'));
    });
    dialog.addEventListener('cancel', event => {
      event.preventDefault();
      closeModal(dialog, 'cancel');
    });
    dialog.addEventListener('close', () => settleConfirmation(dialog.returnValue === 'confirm'));
    dialog.addEventListener('click', event => {
      if (event.target === dialog) closeModal(dialog, 'cancel');
    });
  });

  window.VMUI = {openModal, closeModal, openFlyout, closeFlyout, confirm: confirmAction};
})();

(() => {
  'use strict';

  const stage = document.getElementById('stage');
  const tabButtons = [...document.querySelectorAll('[data-scene-button]')];
  const scenes = [...document.querySelectorAll('[data-scene-panel]')];
  const stackCards = [...document.querySelectorAll('[data-stack-card]')];
  const bottomSheet = document.getElementById('bottomSheet');
  const sheetScrim = document.getElementById('sheetScrim');
  const sheetPrompt = document.getElementById('sheetPrompt');
  const sheetState = document.getElementById('sheetState');
  const sharedOrb = document.getElementById('sharedOrb');
  const orbHome = document.getElementById('orbHome');
  const orbDetail = document.getElementById('orbDetail');
  const orbThumbSpace = document.getElementById('orbThumbSpace');
  const orbHeroSpace = document.getElementById('orbHeroSpace');

  let activeScene = 'stack';
  let sheetOffset = 0;
  let sheetClosedOffset = 0;
  let sheetSpringFrame = 0;
  let sheetOpen = false;
  let orbOpen = false;
  let orbAnimation = null;

  const contract = {
    version: 1,
    viewport: { width: 390, height: 844 },
    scenes: {
      stack: {
        trigger: 'scene-enter',
        durationMs: 620,
        staggerMs: 85,
        properties: ['opacity', 'transform.translateY', 'transform.scale'],
        curve: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
        interruption: 'replay cancels active animations'
      },
      sheet: {
        trigger: 'tap-or-pan',
        openThreshold: 0.35,
        closeThreshold: 0.65,
        spring: { mass: 1, stiffness: 220, damping: 26 },
        properties: ['transform.translateY', 'scrim.opacity'],
        interruption: 'pointerdown stops spring and continues from current offset'
      },
      orb: {
        trigger: 'tap',
        durationMs: 520,
        properties: ['frame', 'cornerRadius', 'content.opacity'],
        curve: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
        interruption: 'close uses the current rendered frame as the reverse origin'
      }
    }
  };

  function activateScene(name, options = {}) {
    if (!contract.scenes[name]) return;
    activeScene = name;
    tabButtons.forEach((button) => {
      const active = button.dataset.sceneButton === name;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    scenes.forEach((scene) => {
      scene.classList.toggle('is-active', scene.dataset.scenePanel === name);
    });
    if (name === 'stack' && options.play !== false) replayStack();
    if (name === 'sheet') ensureSheetMetrics();
    if (name === 'orb') requestAnimationFrame(() => placeOrbAtHome(false));
    if (name === 'orb' && options.state === 'open') requestAnimationFrame(() => openOrb(false));
    if (name === 'orb' && options.state === 'closed') requestAnimationFrame(() => closeOrb(false));
    if (name === 'sheet' && options.state === 'open') openSheet(false);
    if (name === 'sheet' && options.state === 'closed') closeSheet(false);
  }

  function replayStack() {
    stackCards.forEach((card, index) => {
      card.getAnimations().forEach((animation) => animation.cancel());
      card.animate(
        [
          { opacity: 0, transform: 'translate3d(0, 34px, 0) scale(0.93)' },
          { opacity: 1, transform: 'translate3d(0, -5px, 0) scale(1.015)', offset: 0.72 },
          { opacity: 1, transform: 'translate3d(0, 0, 0) scale(1)' }
        ],
        {
          duration: 620,
          delay: index * 85,
          easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
          fill: 'both'
        }
      );
    });
  }

  function ensureSheetMetrics() {
    if (!bottomSheet.offsetHeight) return;
    sheetClosedOffset = Math.max(0, bottomSheet.offsetHeight - 88);
    if (!sheetOpen && !sheetSpringFrame) setSheetOffset(sheetClosedOffset);
    drawSheetState();
  }

  function setSheetOffset(value) {
    sheetOffset = Math.max(0, Math.min(sheetClosedOffset, value));
    bottomSheet.style.transform = `translate3d(0, ${sheetOffset}px, 0)`;
    sheetScrim.classList.toggle('is-visible', sheetOffset < sheetClosedOffset * 0.58);
  }

  function drawSheetState() {
    const openRatio = sheetClosedOffset ? 1 - sheetOffset / sheetClosedOffset : 0;
    sheetState.textContent = openRatio > 0.55 ? 'open' : 'closed';
  }

  function stopSheetSpring() {
    if (sheetSpringFrame) cancelAnimationFrame(sheetSpringFrame);
    sheetSpringFrame = 0;
  }

  function springSheetTo(target, inheritedVelocity = 0) {
    stopSheetSpring();
    const state = { x: sheetOffset, v: inheritedVelocity, last: performance.now() };
    const stiffness = 220;
    const damping = 26;
    const mass = 1;

    const tick = (now) => {
      const elapsed = Math.min((now - state.last) / 1000, 1 / 30);
      state.last = now;
      const steps = 4;
      for (let i = 0; i < steps; i++) {
        const dt = elapsed / steps;
        const acceleration = (-stiffness * (state.x - target) - damping * state.v) / mass;
        state.v += acceleration * dt;
        state.x += state.v * dt;
      }
      setSheetOffset(state.x);
      drawSheetState();
      if (Math.abs(state.x - target) < 0.4 && Math.abs(state.v) < 8) {
        setSheetOffset(target);
        sheetOpen = target === 0;
        drawSheetState();
        sheetSpringFrame = 0;
        return;
      }
      sheetSpringFrame = requestAnimationFrame(tick);
    };
    sheetSpringFrame = requestAnimationFrame(tick);
  }

  function openSheet(animated = true) {
    ensureSheetMetrics();
    sheetOpen = true;
    if (animated) springSheetTo(0, -0.2);
    else { stopSheetSpring(); setSheetOffset(0); drawSheetState(); }
  }

  function closeSheet(animated = true) {
    ensureSheetMetrics();
    sheetOpen = false;
    if (animated) springSheetTo(sheetClosedOffset, 0.2);
    else { stopSheetSpring(); setSheetOffset(sheetClosedOffset); drawSheetState(); }
  }

  let drag = null;
  let velocitySamples = [];
  bottomSheet.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    stopSheetSpring();
    ensureSheetMetrics();
    drag = { y: event.clientY, startOffset: sheetOffset, pointerId: event.pointerId };
    velocitySamples = [{ y: event.clientY, t: performance.now() }];
    bottomSheet.setPointerCapture(event.pointerId);
    bottomSheet.style.cursor = 'grabbing';
  });
  bottomSheet.addEventListener('pointermove', (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    setSheetOffset(drag.startOffset + event.clientY - drag.y);
    const now = performance.now();
    velocitySamples.push({ y: event.clientY, t: now });
    velocitySamples = velocitySamples.filter((sample) => now - sample.t < 120);
    drawSheetState();
  });
  const finishDrag = (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const first = velocitySamples[0];
    const last = velocitySamples[velocitySamples.length - 1];
    const dt = last && first ? Math.max(1, last.t - first.t) : 1;
    const velocity = last && first ? (last.y - first.y) / dt : 0;
    const ratio = sheetClosedOffset ? sheetOffset / sheetClosedOffset : 0;
    drag = null;
    bottomSheet.style.cursor = '';
    if (velocity < -0.35 || (velocity <= 0.35 && ratio < 0.35)) openSheet(true);
    else closeSheet(true);
  };
  bottomSheet.addEventListener('pointerup', finishDrag);
  bottomSheet.addEventListener('pointercancel', finishDrag);
  sheetPrompt.addEventListener('click', () => openSheet(true));
  sheetScrim.addEventListener('click', () => closeSheet(true));

  function relativeRect(element) {
    const stageRect = stage.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    return {
      left: rect.left - stageRect.left,
      top: rect.top - stageRect.top,
      width: rect.width,
      height: rect.height
    };
  }

  function applyOrbFrame(frame, radius) {
    sharedOrb.style.left = `${frame.left}px`;
    sharedOrb.style.top = `${frame.top}px`;
    sharedOrb.style.width = `${frame.width}px`;
    sharedOrb.style.height = `${frame.height}px`;
    sharedOrb.style.borderRadius = radius;
  }

  function placeOrbAtHome(animated = false) {
    if (!orbThumbSpace.offsetWidth) return;
    const frame = relativeRect(orbThumbSpace);
    if (orbAnimation) orbAnimation.cancel();
    if (!animated) {
      applyOrbFrame(frame, '22px');
      return;
    }
    orbAnimation = sharedOrb.animate([
      { left: `${parseFloat(sharedOrb.style.left) || frame.left}px`, top: `${parseFloat(sharedOrb.style.top) || frame.top}px`, width: `${parseFloat(sharedOrb.style.width) || frame.width}px`, height: `${parseFloat(sharedOrb.style.height) || frame.height}px`, borderRadius: sharedOrb.style.borderRadius || '22px' },
      { left: `${frame.left}px`, top: `${frame.top}px`, width: `${frame.width}px`, height: `${frame.height}px`, borderRadius: '22px' }
    ], { duration: 420, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'forwards' });
  }

  function openOrb(animated = true) {
    if (orbOpen || !orbHeroSpace.offsetWidth) return;
    orbOpen = true;
    const home = relativeRect(orbThumbSpace);
    const hero = relativeRect(orbHeroSpace);
    const start = {
      left: parseFloat(sharedOrb.style.left) || home.left,
      top: parseFloat(sharedOrb.style.top) || home.top,
      width: parseFloat(sharedOrb.style.width) || home.width,
      height: parseFloat(sharedOrb.style.height) || home.height
    };
    orbHome.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 220, easing: 'ease-out', fill: 'forwards' });
    orbDetail.classList.add('is-open');
    orbDetail.setAttribute('aria-hidden', 'false');
    orbDetail.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 360, delay: 100, easing: 'ease-out', fill: 'forwards' });
    if (orbAnimation) orbAnimation.cancel();
    if (!animated) {
      applyOrbFrame(hero, '50%');
      return;
    }
    orbAnimation = sharedOrb.animate([
      { left: `${start.left}px`, top: `${start.top}px`, width: `${start.width}px`, height: `${start.height}px`, borderRadius: '22px' },
      { left: `${hero.left}px`, top: `${hero.top}px`, width: `${hero.width}px`, height: `${hero.height}px`, borderRadius: '50%' }
    ], { duration: 520, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'forwards' });
  }

  function closeOrb(animated = true) {
    if (!orbOpen) return;
    orbOpen = false;
    const home = relativeRect(orbThumbSpace);
    const hero = relativeRect(orbHeroSpace);
    const start = {
      left: parseFloat(sharedOrb.style.left) || hero.left,
      top: parseFloat(sharedOrb.style.top) || hero.top,
      width: parseFloat(sharedOrb.style.width) || hero.width,
      height: parseFloat(sharedOrb.style.height) || hero.height
    };
    orbDetail.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 180, easing: 'ease-out', fill: 'forwards' });
    orbDetail.classList.remove('is-open');
    orbDetail.setAttribute('aria-hidden', 'true');
    orbHome.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 260, delay: 140, easing: 'ease-out', fill: 'forwards' });
    if (orbAnimation) orbAnimation.cancel();
    if (!animated) {
      applyOrbFrame(home, '22px');
      return;
    }
    orbAnimation = sharedOrb.animate([
      { left: `${start.left}px`, top: `${start.top}px`, width: `${start.width}px`, height: `${start.height}px`, borderRadius: '50%' },
      { left: `${home.left}px`, top: `${home.top}px`, width: `${home.width}px`, height: `${home.height}px`, borderRadius: '22px' }
    ], { duration: 460, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'forwards' });
  }

  tabButtons.forEach((button) => button.addEventListener('click', () => activateScene(button.dataset.sceneButton)));
  document.getElementById('replayStack').addEventListener('click', replayStack);
  document.getElementById('openDetail').addEventListener('click', () => openOrb(true));
  document.getElementById('closeDetail').addEventListener('click', () => closeOrb(true));
  window.addEventListener('resize', () => {
    ensureSheetMetrics();
    if (activeScene === 'orb') placeOrbAtHome(false);
  });

  const clock = document.getElementById('clock');
  const started = performance.now();
  const tickClock = () => {
    const elapsed = Math.floor((performance.now() - started) / 1000);
    clock.textContent = `T+${String(elapsed).padStart(2, '0')}`;
    requestAnimationFrame(tickClock);
  };
  requestAnimationFrame(tickClock);

  window.motionLab = {
    contract,
    activateScene,
    replayStack,
    openSheet: () => openSheet(true),
    closeSheet: () => closeSheet(true),
    openOrb: () => openOrb(true),
    closeOrb: () => closeOrb(true)
  };

  const params = new URLSearchParams(window.location.search);
  const requestedScene = params.get('scene');
  const requestedState = params.get('state');
  if (requestedScene && contract.scenes[requestedScene]) {
    activateScene(requestedScene, { state: requestedState, play: requestedState !== 'still' });
  } else {
    requestAnimationFrame(() => activateScene('stack'));
  }
})();
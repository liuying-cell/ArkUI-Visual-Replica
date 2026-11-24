(() => {
  'use strict';

  const tabButtons = [...document.querySelectorAll('[data-scene-button]')];
  const scenes = [...document.querySelectorAll('[data-scene-panel]')];
  const scrollView = document.getElementById('scrollView');
  const scrollHero = document.getElementById('scrollHero');
  const compactBar = document.getElementById('compactBar');
  const scrollProgress = document.getElementById('scrollProgress');
  const tabViewport = document.getElementById('tabViewport');
  const tabTrack = document.getElementById('tabTrack');
  const tabPill = document.getElementById('tabPill');
  const tabChoices = [...document.querySelectorAll('[data-tab-button]')];
  const tabState = document.getElementById('tabState');
  const burstButton = document.getElementById('burstButton');
  const particleField = document.getElementById('particleField');
  const reactionCount = document.getElementById('reactionCount');
  const motionToggle = document.getElementById('motionToggle');
  const burstRings = [...document.querySelectorAll('[data-burst-ring]')];

  const contract = {
    version: 2,
    viewport: { width: 390, height: 844 },
    scenes: {
      scroll: {
        trigger: 'scroll-progress',
        progress: { start: 0, end: 180, unit: 'css-px' },
        properties: ['hero.scale', 'hero.opacity', 'masthead.translateY', 'masthead.opacity', 'progress.scaleX'],
        interruption: 'Scroll updates directly; no delayed animation owns the property while dragging.'
      },
      tabs: {
        trigger: 'tap-or-pan',
        axis: 'horizontal',
        durationMs: 440,
        threshold: 0.2,
        velocityHandoff: true,
        properties: ['track.translateX', 'indicator.translateX', 'content.opacity'],
        interruption: 'Pointer down cancels snapping and continues from the current pixel offset.'
      },
      burst: {
        trigger: 'tap',
        durationMs: 480,
        keyframes: [
          { at: 0.22, scale: 0.82 },
          { at: 0.56, scale: 1.12 },
          { at: 1, scale: 1 }
        ],
        particles: { count: 12, staggerMs: 16 },
        properties: ['button.scale', 'ring.scale', 'ring.opacity', 'particle.translate', 'particle.opacity'],
        interruption: 'A new tap cancels active WAAPI effects and restarts from the settled button frame.'
      }
    }
  };

  let activeScene = 'scroll';
  let tabIndex = 0;
  let tabDrag = null;
  let tabAnimation = null;
  let tabVelocitySamples = [];
  let burstCount = 128;
  let burstAnimations = [];
  let motionEnabled = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function activateScene(name) {
    if (!contract.scenes[name]) return;
    activeScene = name;
    tabButtons.forEach((button) => {
      const active = button.dataset.sceneButton === name;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    scenes.forEach((scene) => scene.classList.toggle('is-active', scene.dataset.scenePanel === name));
    if (name === 'scroll') requestAnimationFrame(updateScrollMotion);
    if (name === 'tabs') requestAnimationFrame(() => snapTab(tabIndex, false));
  }

  function updateScrollMotion() {
    const scrollTop = scrollView.scrollTop;
    const maxScroll = Math.max(1, scrollView.scrollHeight - scrollView.clientHeight);
    const headerProgress = clamp(scrollTop / 180, 0, 1);
    const traceProgress = clamp(scrollTop / maxScroll, 0, 1);
    scrollHero.style.transform = `translateY(${-headerProgress * 28}px) scale(${1 - headerProgress * 0.06})`;
    scrollHero.style.opacity = `${1 - headerProgress * 0.78}`;
    compactBar.style.opacity = `${headerProgress}`;
    compactBar.style.transform = `translateY(${-12 + headerProgress * 12}px)`;
    scrollProgress.style.transform = `scaleX(${traceProgress})`;
  }

  function currentTrackPixels() {
    const style = getComputedStyle(tabTrack).transform;
    if (!style || style === 'none') return 0;
    const values = style.match(/matrix(?:3d)?\(([^)]+)\)/);
    if (!values) return 0;
    const parts = values[1].split(',').map(Number);
    return parts.length === 16 ? parts[12] : parts[4];
  }

  function setTrackPixels(value) {
    tabTrack.style.transform = `translate3d(${value}px, 0, 0)`;
  }

  function updateTabUi(index) {
    tabIndex = index;
    tabChoices.forEach((choice, choiceIndex) => {
      const active = choiceIndex === index;
      choice.classList.toggle('is-active', active);
      choice.setAttribute('aria-selected', String(active));
    });
    tabPill.style.transform = `translateX(${index * 100}%)`;
    tabState.textContent = `INDEX 0${index}`;
  }

  function snapTab(index, animated = true) {
    const targetIndex = clamp(index, 0, 2);
    const width = tabViewport.clientWidth || 1;
    const target = -targetIndex * width;
    if (tabAnimation) {
      tabAnimation.cancel();
      tabAnimation = null;
    }
    updateTabUi(targetIndex);
    if (!animated) {
      setTrackPixels(target);
      return;
    }
    const from = currentTrackPixels();
    const animation = tabTrack.animate(
      [
        { transform: `translate3d(${from}px, 0, 0)` },
        { transform: `translate3d(${target}px, 0, 0)` }
      ],
      { duration: 440, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'forwards' }
    );
    tabAnimation = animation;
    animation.onfinish = () => {
      if (tabAnimation !== animation) return;
      setTrackPixels(target);
      animation.cancel();
      tabAnimation = null;
    };
  }
  function finishTabDrag(event) {
    if (!tabDrag || tabDrag.pointerId !== event.pointerId) return;
    const width = tabViewport.clientWidth || 1;
    const first = tabVelocitySamples[0];
    const last = tabVelocitySamples[tabVelocitySamples.length - 1];
    const dt = first && last ? Math.max(1, last.t - first.t) : 1;
    const velocity = first && last ? (last.x - first.x) / dt : 0;
    const delta = tabDrag.current - tabDrag.start;
    let next = tabIndex;
    if (delta < -width * 0.2 || velocity < -0.35) next += 1;
    else if (delta > width * 0.2 || velocity > 0.35) next -= 1;
    tabDrag = null;
    snapTab(next, true);
  }

  tabViewport.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    if (tabAnimation) {
      tabAnimation.cancel();
      tabAnimation = null;
    }
    const width = tabViewport.clientWidth || 1;
    tabDrag = { pointerId: event.pointerId, startX: event.clientX, start: -tabIndex * width, current: -tabIndex * width };
    tabVelocitySamples = [{ x: event.clientX, t: performance.now() }];
    tabViewport.setPointerCapture(event.pointerId);
    tabViewport.style.cursor = 'grabbing';
  });

  tabViewport.addEventListener('pointermove', (event) => {
    if (!tabDrag || tabDrag.pointerId !== event.pointerId) return;
    const width = tabViewport.clientWidth || 1;
    let delta = event.clientX - tabDrag.startX;
    if ((tabIndex === 0 && delta > 0) || (tabIndex === 2 && delta < 0)) delta *= 0.28;
    tabDrag.current = clamp(tabDrag.start + delta, -2 * width, 0);
    setTrackPixels(tabDrag.current);
    const now = performance.now();
    tabVelocitySamples.push({ x: event.clientX, t: now });
    tabVelocitySamples = tabVelocitySamples.filter((sample) => now - sample.t < 120);
  });

  tabViewport.addEventListener('pointerup', finishTabDrag);
  tabViewport.addEventListener('pointercancel', finishTabDrag);
  tabChoices.forEach((choice) => {
    choice.addEventListener('click', () => snapTab(Number(choice.dataset.tabButton), true));
  });

  const particleColors = ['#d7ff57', '#b7a2ff', '#8de8e1', '#ffb18c'];
  for (let index = 0; index < 12; index++) {
    const particle = document.createElement('i');
    particle.className = 'particle';
    particle.style.background = particleColors[index % particleColors.length];
    particle.dataset.angle = String((Math.PI * 2 * index) / 12 - Math.PI / 2);
    particle.dataset.distance = String(82 + (index % 3) * 18);
    particleField.appendChild(particle);
  }
  const particles = [...document.querySelectorAll('.particle')];

  function updateMotionToggle() {
    motionToggle.setAttribute('aria-pressed', String(motionEnabled));
    motionToggle.textContent = motionEnabled ? 'MOTION ON' : 'MOTION OFF';
  }

  function triggerBurst() {
    burstCount += 1;
    reactionCount.textContent = String(burstCount);
    if (!motionEnabled) return;

    burstAnimations.forEach((animation) => animation.cancel());
    burstAnimations = [];

    const buttonAnimation = burstButton.animate(
      [
        { transform: 'translate(-50%, -50%) scale(1)', offset: 0 },
        { transform: 'translate(-50%, -50%) scale(0.82)', offset: 0.22 },
        { transform: 'translate(-50%, -50%) scale(1.12)', offset: 0.56 },
        { transform: 'translate(-50%, -50%) scale(1)', offset: 1 }
      ],
      { duration: 480, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }
    );
    burstAnimations.push(buttonAnimation);

    burstRings.forEach((ring, index) => {
      const ringAnimation = ring.animate(
        [
          { opacity: 0.55, transform: 'translate(-50%, -50%) scale(0.68)' },
          { opacity: 0, transform: 'translate(-50%, -50%) scale(1.75)' }
        ],
        { duration: 720, delay: index * 72, easing: 'cubic-bezier(0.1, 0.7, 0.2, 1)' }
      );
      burstAnimations.push(ringAnimation);
    });

    particles.forEach((particle, index) => {
      const angle = Number(particle.dataset.angle);
      const distance = Number(particle.dataset.distance);
      const x = Math.cos(angle) * distance;
      const y = Math.sin(angle) * distance;
      const particleAnimation = particle.animate(
        [
          { opacity: 0.9, transform: 'translate(-50%, -50%) translate(0px, 0px) scale(1) rotate(0deg)' },
          { opacity: 0, transform: `translate(-50%, -50%) translate(${x}px, ${y}px) scale(0.25) rotate(90deg)` }
        ],
        { duration: 620, delay: index * 16, easing: 'cubic-bezier(0.15, 0.75, 0.25, 1)' }
      );
      burstAnimations.push(particleAnimation);
    });
  }

  burstButton.addEventListener('click', triggerBurst);
  motionToggle.addEventListener('click', () => {
    motionEnabled = !motionEnabled;
    updateMotionToggle();
  });

  scrollView.addEventListener('scroll', updateScrollMotion, { passive: true });
  window.addEventListener('resize', () => {
    updateScrollMotion();
    if (activeScene === 'tabs') snapTab(tabIndex, false);
  });

  const clock = document.getElementById('clock');
  const started = performance.now();
  const tickClock = () => {
    const elapsed = Math.floor((performance.now() - started) / 1000);
    clock.textContent = `T+${String(elapsed).padStart(2, '0')}`;
    requestAnimationFrame(tickClock);
  };
  requestAnimationFrame(tickClock);
  updateMotionToggle();

  window.motionLab = {
    contract,
    activateScene,
    triggerBurst,
    setTab: (index) => snapTab(index, true),
    scrollTo: (value) => {
      scrollView.scrollTop = value;
      updateScrollMotion();
    }
  };

  const params = new URLSearchParams(window.location.search);
  const requestedScene = params.get('scene');
  const requestedState = params.get('state');
  if (requestedScene && contract.scenes[requestedScene]) {
    activateScene(requestedScene);
    if (requestedScene === 'scroll' && requestedState === 'scrolled') {
      requestAnimationFrame(() => {
        scrollView.scrollTop = 180;
        updateScrollMotion();
      });
    }
    if (requestedScene === 'burst' && requestedState === 'burst') {
      requestAnimationFrame(() => setTimeout(triggerBurst, 120));
    }
  } else {
    requestAnimationFrame(() => activateScene('scroll'));
  }
})();
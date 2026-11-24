(() => {
  const stage = document.getElementById('stage');
  const sceneButtons = [...document.querySelectorAll('[data-scene-button]')];
  const scenePanels = [...document.querySelectorAll('[data-scene-panel]')];
  const routeHome = document.getElementById('routeHome');
  const routeDetail = document.getElementById('routeDetail');
  const routeCard = document.getElementById('routeCard');
  const detailClose = document.getElementById('detailClose');
  const rowList = document.getElementById('rowList');
  const rowCount = document.getElementById('rowCount');
  const addRowButton = document.getElementById('addRow');
  const removeRowButton = document.getElementById('removeRow');
  const chaosRowsButton = document.getElementById('chaosRows');
  const stackTop = document.getElementById('stackTop');
  const stackIndex = document.getElementById('stackIndex');
  const stackTitle = document.getElementById('stackTitle');
  const resetStackButton = document.getElementById('resetStack');

  const contract = {
    id: 'motion-lab-batch-03',
    scenes: {
      route: { durationMs: 520, interruption: 'Pop during push uses the current geometry and page surface without a snap.' },
      list: { durationMs: 360, staggerMs: 34, interruption: 'Rapid add/remove keeps the latest state and starts layout from current positions.' },
      stack: { threshold: 110, spring: { response: 0.45, dampingFraction: 0.8 } }
    }
  };

  let activeScene = 'route';
  let detailOpen = false;
  let rowItems = [
    { id: 1, title: 'Signal captured', copy: 'BASELINE ROW', hot: false },
    { id: 2, title: 'Context attached', copy: 'STAGGER 034 MS', hot: true },
    { id: 3, title: 'Layout recomputed', copy: 'STATE OWNS ORDER', hot: false },
    { id: 4, title: 'Frame settled', copy: 'READY TO INTERRUPT', hot: false }
  ];
  let nextRowId = 5;
  let chaosTimer = -1;

  function activateScene(name) {
    activeScene = name;
    sceneButtons.forEach((button) => {
      const active = button.dataset.sceneButton === name;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    scenePanels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.scenePanel === name));
  }

  function setTransitionName(element, name) {
    if (!element) return;
    element.style.viewTransitionName = name || 'none';
  }

  function openDetail() {
    if (detailOpen || activeScene !== 'route') return;
    detailOpen = true;
    setTransitionName(document.getElementById('routeVisual'), 'hero-geometry');
    setTransitionName(document.getElementById('detailVisual'), 'hero-geometry');
    const update = () => {
      routeHome.style.display = 'none';
      routeDetail.classList.add('is-open');
      routeDetail.setAttribute('aria-hidden', 'false');
    };
    if (document.startViewTransition) {
      document.startViewTransition(update);
    } else {
      update();
    }
  }

  function closeDetail() {
    if (!detailOpen) return;
    detailOpen = false;
    const update = () => {
      routeDetail.classList.remove('is-open');
      routeDetail.setAttribute('aria-hidden', 'true');
      routeHome.style.display = 'block';
    };
    if (document.startViewTransition) {
      document.startViewTransition(update);
    } else {
      update();
    }
  }

  function rowTemplate(item) {
    return '<span class="row-number">' + String(item.id).padStart(2, '0') + '</span>' +
      '<span class="row-copy"><b>' + item.title + '</b><small>' + item.copy + '</small></span>' +
      '<span class="row-signal"></span>';
  }

  function renderRows(animate) {
    const previous = new Map();
    if (animate) {
      [...rowList.children].forEach((element) => previous.set(element.dataset.id, element.getBoundingClientRect()));
    }
    rowList.replaceChildren();
    rowItems.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'row-item' + (item.hot ? ' hot' : '');
      row.dataset.id = String(item.id);
      row.innerHTML = rowTemplate(item);
      rowList.appendChild(row);
      if (animate) {
        const old = previous.get(String(item.id));
        if (old) {
          const now = row.getBoundingClientRect();
          const deltaY = old.top - now.top;
          if (Math.abs(deltaY) > 0.5) {
            row.animate(
              [{ transform: 'translateY(' + deltaY + 'px)' }, { transform: 'translateY(0)' }],
              { duration: 330, delay: index * 34, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }
            );
          }
        } else {
          row.animate(
            [
              { opacity: 0, transform: 'translateY(-18px) scale(0.94)' },
              { opacity: 1, transform: 'translateY(0) scale(1)' }
            ],
            { duration: 360, delay: index * 34, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }
          );
        }
      }
    });
    rowCount.textContent = String(rowItems.length).padStart(2, '0') + ' ROWS';
  }

  function addRow() {
    if (activeScene !== 'list') return;
    const starts = ['Fresh signal', 'New layer', 'Input accepted', 'State appended'];
    const index = nextRowId++;
    rowItems.splice(Math.min(1, rowItems.length), 0, {
      id: index,
      title: starts[index % starts.length],
      copy: 'ENTERING FROM STATE',
      hot: index % 3 === 0
    });
    if (rowItems.length > 7) rowItems.pop();
    renderRows(true);
  }

  function removeRow() {
    if (activeScene !== 'list' || rowItems.length <= 1) return;
    rowItems.splice(Math.max(0, rowItems.length - 2), 1);
    renderRows(true);
  }

  function triggerChaos() {
    if (activeScene !== 'list') return;
    if (chaosTimer >= 0) clearInterval(chaosTimer);
    let tick = 0;
    chaosTimer = setInterval(() => {
      if (tick % 2 === 0) addRow(); else removeRow();
      tick += 1;
      if (tick >= 5) {
        clearInterval(chaosTimer);
        chaosTimer = -1;
      }
    }, 80);
  }

  const stackCards = [
    { index: '01', title: 'Spring handed.' },
    { index: '02', title: 'Velocity remembered.' },
    { index: '03', title: 'Depth resolved.' },
    { index: '04', title: 'Stack restored.' }
  ];
  let stackCursor = 0;
  let drag = null;
  let stackAnimation = null;

  function applyStack(x, y, rotationX, rotationY) {
    stackTop.style.transform = 'translate(-50%, -50%) translate(' + x + 'px,' + y + 'px) rotateX(' + rotationX + 'deg) rotateY(' + rotationY + 'deg)';
  }

  function resetStack(animated) {
    if (stackAnimation) stackAnimation.cancel();
    const keyframes = [
      { transform: stackTop.style.transform || 'translate(-50%, -50%)' },
      { transform: 'translate(-50%, -50%)' }
    ];
    if (animated) {
      stackAnimation = stackTop.animate(keyframes, { duration: 520, easing: 'cubic-bezier(0.2, 0.9, 0.2, 1)' });
    } else {
      stackTop.style.transform = 'translate(-50%, -50%)';
    }
    stackTop.classList.remove('dragging');
    drag = null;
  }

  function advanceStack(direction) {
    if (stackAnimation) stackAnimation.cancel();
    stackAnimation = stackTop.animate(
      [
        { transform: stackTop.style.transform || 'translate(-50%, -50%)', opacity: 1 },
        { transform: 'translate(-50%, -50%) translate(' + direction * 380 + 'px,-42px) rotate(' + direction * 24 + 'deg)', opacity: 0 }
      ],
      { duration: 340, easing: 'cubic-bezier(0.15, 0.75, 0.25, 1)' }
    );
    stackAnimation.onfinish = () => {
      stackCursor = (stackCursor + 1) % stackCards.length;
      const item = stackCards[stackCursor];
      stackIndex.textContent = item.index;
      stackTitle.textContent = item.title;
      stackTop.style.opacity = '0';
      stackTop.style.transform = 'translate(-50%, -50%) translateY(20px) scale(0.92)';
      requestAnimationFrame(() => {
        stackTop.animate(
          [
            { opacity: 0, transform: 'translate(-50%, -50%) translateY(20px) scale(0.92)' },
            { opacity: 1, transform: 'translate(-50%, -50%) scale(1)' }
          ],
          { duration: 220, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }
        ).onfinish = () => {
          stackTop.style.opacity = '1';
          stackTop.style.transform = 'translate(-50%, -50%)';
        };
      });
    };
  }

  stackTop.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    if (stackAnimation) stackAnimation.cancel();
    drag = { id: event.pointerId, startX: event.clientX, startY: event.clientY, samples: [{ x: event.clientX, t: performance.now() }] };
    stackTop.classList.add('dragging');
    stackTop.setPointerCapture(event.pointerId);
  });

  stackTop.addEventListener('pointermove', (event) => {
    if (!drag || drag.id !== event.pointerId) return;
    const x = event.clientX - drag.startX;
    const y = event.clientY - drag.startY;
    drag.samples.push({ x: event.clientX, t: performance.now() });
    drag.samples = drag.samples.filter((sample) => performance.now() - sample.t < 120);
    applyStack(x, y, Math.max(-9, Math.min(9, -y / 18)), Math.max(-16, Math.min(16, x / 12)));
  });

  function endStackDrag(event) {
    if (!drag || drag.id !== event.pointerId) return;
    const x = event.offsetX;
    const y = event.offsetY;
    const first = drag.samples[0];
    const last = drag.samples[drag.samples.length - 1];
    const dt = Math.max(1, (last ? last.t : performance.now()) - (first ? first.t : performance.now()));
    const velocity = last ? (last.x - first.x) / dt : 0;
    const direction = Math.sign(x || velocity || 1);
    drag = null;
    stackTop.classList.remove('dragging');
    if (Math.abs(x) > 110 || Math.abs(velocity) > 0.55) {
      advanceStack(direction);
    } else {
      resetStack(true);
    }
  }

  stackTop.addEventListener('pointerup', endStackDrag);
  stackTop.addEventListener('pointercancel', endStackDrag);

  sceneButtons.forEach((button) => button.addEventListener('click', () => activateScene(button.dataset.sceneButton)));
  routeCard.addEventListener('click', openDetail);
  detailClose.addEventListener('click', closeDetail);
  addRowButton.addEventListener('click', addRow);
  removeRowButton.addEventListener('click', removeRow);
  chaosRowsButton.addEventListener('click', triggerChaos);
  resetStackButton.addEventListener('click', () => resetStack(true));

  renderRows(false);
  applyStack(0, 0, 0, 0);

  const clock = document.getElementById('clock');
  const started = performance.now();
  const tickClock = () => {
    const elapsed = Math.floor((performance.now() - started) / 1000);
    clock.textContent = 'T+' + String(elapsed).padStart(2, '0');
    requestAnimationFrame(tickClock);
  };
  requestAnimationFrame(tickClock);

  window.motionLab = {
    contract,
    activateScene,
    openDetail,
    closeDetail,
    addRow,
    removeRow,
    triggerChaos,
    resetStack: () => resetStack(true),
    advanceStack: (direction) => advanceStack(direction >= 0 ? 1 : -1)
  };

  const params = new URLSearchParams(window.location.search);
  const requestedScene = params.get('scene');
  if (requestedScene && contract.scenes[requestedScene]) {
    activateScene(requestedScene);
    if (requestedScene === 'route' && params.get('state') === 'detail') {
      requestAnimationFrame(() => setTimeout(openDetail, 120));
    }
  } else {
    requestAnimationFrame(() => activateScene('route'));
  }
})();

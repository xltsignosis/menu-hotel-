/**
 * Grand Hotel Aurelia — Interactive Menu & Room Service Controller
 */
document.addEventListener('DOMContentLoaded', () => {
  const state = {
    category: 'Todos',
    dietary: new Set(),
    search: '',
    sort: 'featured',
    mode: localStorage.getItem('hotel_menu_mode') || 'guest',
    cart: JSON.parse(localStorage.getItem('hotel_room_cart') || '[]'),
  };

  // --- MODE SWITCHER (GUEST vs ADMIN) ---
  const modeGuestBtn = document.getElementById('mode-guest-btn');
  const modeAdminBtn = document.getElementById('mode-admin-btn');

  function applyMode(mode) {
    state.mode = mode;
    localStorage.setItem('hotel_menu_mode', mode);
    document.body.classList.toggle('admin-mode', mode === 'admin');
    if (modeGuestBtn && modeAdminBtn) {
      modeGuestBtn.classList.toggle('active', mode === 'guest');
      modeAdminBtn.classList.toggle('active', mode === 'admin');
    }
  }

  if (modeGuestBtn && modeAdminBtn) {
    applyMode(state.mode);
    modeGuestBtn.addEventListener('click', () => applyMode('guest'));
    modeAdminBtn.addEventListener('click', () => applyMode('admin'));
  }

  // --- FILTERING, SEARCH & SORTING ---
  const dishGrid = document.getElementById('menu-grid');
  const catTabs = document.querySelectorAll('.cat-tab');
  const dietaryChips = document.querySelectorAll('.dietary-chip');
  const searchInput = document.getElementById('menu-search-input');
  const sortSelect = document.getElementById('menu-sort-select');
  const resultsCounter = document.getElementById('results-counter');
  const emptyFilterState = document.getElementById('empty-filter-state');
  const resetFiltersBtn = document.getElementById('reset-filters-btn');

  function filterAndSortDishes() {
    if (!dishGrid) return;
    const cards = Array.from(dishGrid.querySelectorAll('.dish-card'));
    let visibleCount = 0;

    cards.forEach((card) => {
      const cardCat = card.dataset.category || '';
      const cardName = (card.dataset.name || '').toLowerCase();
      const cardDesc = (card.dataset.description || '').toLowerCase();
      const cardTags = (card.dataset.dietary || '')
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      const matchesCat =
        state.category === 'Todos' || cardCat === state.category;
      const matchesSearch =
        !state.search ||
        cardName.includes(state.search) ||
        cardDesc.includes(state.search) ||
        cardCat.toLowerCase().includes(state.search);

      let matchesDietary = true;
      for (const reqTag of state.dietary) {
        if (!cardTags.includes(reqTag)) {
          matchesDietary = false;
          break;
        }
      }

      const isVisible = matchesCat && matchesSearch && matchesDietary;
      card.style.display = isVisible ? '' : 'none';
      if (isVisible) visibleCount++;
    });

    // Sort cards
    const sortedCards = cards.sort((a, b) => {
      const priceA = parseFloat(a.dataset.price || '0');
      const priceB = parseFloat(b.dataset.price || '0');
      const featA = a.dataset.featured === 'true' ? 1 : 0;
      const featB = b.dataset.featured === 'true' ? 1 : 0;
      const nameA = (a.dataset.name || '').toLowerCase();
      const nameB = (b.dataset.name || '').toLowerCase();

      if (state.sort === 'price-asc') return priceA - priceB;
      if (state.sort === 'price-desc') return priceB - priceA;
      if (state.sort === 'name-asc') return nameA.localeCompare(nameB, 'es');
      // Default: featured first, then available
      if (featB !== featA) return featB - featA;
      return nameA.localeCompare(nameB, 'es');
    });

    sortedCards.forEach((card) => dishGrid.appendChild(card));

    if (resultsCounter) {
      resultsCounter.textContent = `${visibleCount} ${
        visibleCount === 1 ? 'platillo mostrado' : 'platillos mostrados'
      }`;
    }

    if (emptyFilterState) {
      emptyFilterState.style.display =
        visibleCount === 0 && cards.length > 0 ? 'block' : 'none';
    }
  }

  catTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      catTabs.forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      state.category = tab.dataset.category || 'Todos';
      filterAndSortDishes();
    });
  });

  dietaryChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const tag = chip.dataset.tag;
      if (!tag) return;
      if (state.dietary.has(tag)) {
        state.dietary.delete(tag);
        chip.classList.remove('active');
      } else {
        state.dietary.add(tag);
        chip.classList.add('active');
      }
      filterAndSortDishes();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.search = e.target.value.trim().toLowerCase();
      filterAndSortDishes();
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      state.sort = e.target.value;
      filterAndSortDishes();
    });
  }

  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', () => {
      state.category = 'Todos';
      state.dietary.clear();
      state.search = '';
      state.sort = 'featured';
      if (searchInput) searchInput.value = '';
      if (sortSelect) sortSelect.value = 'featured';
      catTabs.forEach((t) =>
        t.classList.toggle('active', t.dataset.category === 'Todos')
      );
      dietaryChips.forEach((c) => c.classList.remove('active'));
      filterAndSortDishes();
    });
  }

  // --- ADD DISH MODAL ---
  const addModal = document.getElementById('add-dish-modal');
  const openAddBtns = document.querySelectorAll('[data-open-add-modal]');
  const closeAddBtns = document.querySelectorAll('[data-close-add-modal]');

  openAddBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (addModal) addModal.classList.add('open');
    });
  });

  closeAddBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (addModal) addModal.classList.remove('open');
    });
  });

  // --- DELETE CONFIRMATION MODAL ---
  const deleteModal = document.getElementById('delete-confirm-modal');
  const deleteForm = document.getElementById('confirm-delete-form');
  const deleteDishName = document.getElementById('delete-dish-name');
  const closeDeleteBtns = document.querySelectorAll('[data-close-delete-modal]');

  document.querySelectorAll('[data-delete-trigger]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const itemId = btn.dataset.itemId;
      const itemName = btn.dataset.itemName;
      if (deleteForm && deleteModal) {
        deleteForm.action = `/delete/${itemId}`;
        if (deleteDishName) deleteDishName.textContent = itemName;
        deleteModal.classList.add('open');
      }
    });
  });

  closeDeleteBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (deleteModal) deleteModal.classList.remove('open');
    });
  });

  // --- LIVE IMAGE PREVIEW (ADD & EDIT FORMS) ---
  document.querySelectorAll('[data-image-input]').forEach((input) => {
    const previewId = input.dataset.previewTarget;
    const previewImg = document.getElementById(previewId);
    if (!previewImg) return;

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          previewImg.src = ev.target.result;
        };
        reader.readAsDataURL(file);
      }
    });
  });

  document.querySelectorAll('[data-image-url-input]').forEach((input) => {
    const previewId = input.dataset.previewTarget;
    const previewImg = document.getElementById(previewId);
    if (!previewImg) return;

    input.addEventListener('input', () => {
      const url = input.value.trim();
      if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/static/')) {
        previewImg.src = url;
      }
    });
  });

  // --- ROOM SERVICE CART & ORDER DRAWER ---
  const cartDrawer = document.getElementById('room-service-drawer');
  const openCartBtn = document.getElementById('open-cart-btn');
  const closeCartBtns = document.querySelectorAll('[data-close-cart]');
  const cartItemsContainer = document.getElementById('cart-items-list');
  const cartCountBadge = document.getElementById('cart-count-badge');
  const cartSubtotalEl = document.getElementById('cart-subtotal');
  const cartServiceEl = document.getElementById('cart-service-fee');
  const cartTotalEl = document.getElementById('cart-total');
  const orderForm = document.getElementById('room-service-form');
  const orderReceipt = document.getElementById('order-receipt-box');

  function saveCart() {
    localStorage.setItem('hotel_room_cart', JSON.stringify(state.cart));
    renderCart();
  }

  function formatMXN(amount) {
    return '$' + Number(amount || 0).toFixed(2);
  }

  function renderCart() {
    const totalQty = state.cart.reduce((acc, item) => acc + item.qty, 0);
    if (cartCountBadge) {
      cartCountBadge.textContent = totalQty;
    }

    if (!cartItemsContainer) return;

    if (state.cart.length === 0) {
      cartItemsContainer.innerHTML = `
        <div style="text-align:center; padding: 2.2rem 1rem; color: var(--text-muted);">
          <p style="margin:0 0 0.4rem 0; font-family: var(--font-serif); font-size: 1.25rem; color: var(--text-primary);">
            Tu bandeja está vacía
          </p>
          <p style="margin:0; font-size:0.84rem;">
            Selecciona platillos de la carta para solicitar servicio a tu habitación.
          </p>
        </div>
      `;
      if (cartSubtotalEl) cartSubtotalEl.textContent = '$0.00';
      if (cartServiceEl) cartServiceEl.textContent = '$0.00';
      if (cartTotalEl) cartTotalEl.textContent = '$0.00';
      return;
    }

    let subtotal = 0;
    cartItemsContainer.innerHTML = state.cart
      .map((item) => {
        const lineTotal = item.price * item.qty;
        subtotal += lineTotal;
        return `
          <div class="cart-item">
            <div class="cart-item-info">
              <h4>${item.name}</h4>
              <span>${formatMXN(item.price)} c/u · Subtotal: ${formatMXN(lineTotal)}</span>
            </div>
            <div class="qty-controls">
              <button type="button" class="qty-btn" data-cart-dec="${item.id}" aria-label="Disminuir cantidad">−</button>
              <span style="font-size:0.85rem; font-weight:600; min-width:18px; text-align:center;">${item.qty}</span>
              <button type="button" class="qty-btn" data-cart-inc="${item.id}" aria-label="Aumentar cantidad">+</button>
            </div>
          </div>
        `;
      })
      .join('');

    const serviceFee = subtotal * 0.1;
    const total = subtotal + serviceFee;

    if (cartSubtotalEl) cartSubtotalEl.textContent = formatMXN(subtotal);
    if (cartServiceEl) cartServiceEl.textContent = formatMXN(serviceFee);
    if (cartTotalEl) cartTotalEl.textContent = formatMXN(total);

    cartItemsContainer.querySelectorAll('[data-cart-inc]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.cartInc;
        const found = state.cart.find((i) => i.id === id);
        if (found) {
          found.qty += 1;
          saveCart();
        }
      });
    });

    cartItemsContainer.querySelectorAll('[data-cart-dec]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.cartDec;
        const idx = state.cart.findIndex((i) => i.id === id);
        if (idx > -1) {
          state.cart[idx].qty -= 1;
          if (state.cart[idx].qty <= 0) {
            state.cart.splice(idx, 1);
          }
          saveCart();
        }
      });
    });
  }

  document.querySelectorAll('[data-add-to-cart]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      const name = btn.dataset.name;
      const price = parseFloat(btn.dataset.price || '0');

      const existing = state.cart.find((i) => i.id === id);
      if (existing) {
        existing.qty += 1;
      } else {
        state.cart.push({ id, name, price, qty: 1 });
      }
      if (orderReceipt) orderReceipt.style.display = 'none';
      saveCart();

      const originalText = btn.innerHTML;
      btn.innerHTML = '✓ En tu orden';
      setTimeout(() => {
        btn.innerHTML = originalText;
      }, 900);
    });
  });

  if (openCartBtn && cartDrawer) {
    openCartBtn.addEventListener('click', () => {
      cartDrawer.classList.add('open');
    });
  }

  closeCartBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (cartDrawer) cartDrawer.classList.remove('open');
    });
  });

  if (orderForm) {
    orderForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (state.cart.length === 0) return;

      const roomNumber = document.getElementById('order-room-input').value.trim();
      const guestName = document.getElementById('order-guest-input').value.trim();

      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            roomNumber,
            guestName,
            items: state.cart,
          }),
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          state.cart = [];
          saveCart();
          orderForm.reset();
          if (orderReceipt) {
            orderReceipt.style.display = 'block';
            orderReceipt.innerHTML = `
              <div style="background: var(--sage-bg); color: var(--sage-text); border: 1px solid hsla(148,42%,28%,0.3); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem;">
                <strong style="display:block; font-size:0.95rem; margin-bottom:0.25rem;">
                  ✓ Orden Confirmada · Folio ${data.folio}
                </strong>
                <span style="font-size:0.83rem;">
                  Habitación <b>${data.roomNumber}</b> (${data.guestName}) · Tiempo estimado: <b>${data.estimatedDelivery}</b> · Total: <b>${formatMXN(data.total)}</b>
                </span>
              </div>
            `;
          }
        } else {
          alert(data.error || 'No se pudo procesar tu solicitud.');
        }
      } catch (err) {
        alert('Error de conexión al enviar la orden.');
      }
    });
  }

  // Close backdrops when clicking outside card/panel
  [addModal, deleteModal, cartDrawer].forEach((backdrop) => {
    if (!backdrop) return;
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('open');
      }
    });
  });

  renderCart();
  filterAndSortDishes();
});

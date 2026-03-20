const state = {
  session: null,
  currentTab: 'mail',
  currentFilter: 'all',
  mailboxes: [],
  messages: [],
  selectedMailboxId: null,
  selectedMessageId: null,
  selectedMessageCache: null,
  mainSearch: '',
  aliasSearch: '',
  recentMessageIds: {},
  hasLoadedMessages: false,
};

const dom = {};
let mainSearchTimer = null;
let aliasSearchTimer = null;
let autoRefreshTimer = null;
let refreshPromise = null;
let relativeTimeTimer = null;

const AUTO_VIEW_REFRESH_MS = 8000;
const RELATIVE_TIME_REFRESH_MS = 10000;
const NEW_MESSAGE_HIGHLIGHT_MS = 180000;

document.addEventListener('DOMContentLoaded', async () => {
  cacheDom();
  bindEvents();
  lucide.createIcons();
  await bootstrapSession();
});

function cacheDom() {
  const ids = [
    'loginPage', 'appPage', 'loginForm', 'loginEmail', 'loginPassword', 'loginError', 'logoutBtn',
    'tabMailBtn', 'tabTempBtn', 'mailNav', 'tempPanel', 'folderTitle', 'folderCount', 'emailList',
    'emptyState', 'detailContent', 'mobileDetail', 'mobileDetailContent', 'sidebar', 'sidebarOverlay',
    'sidebarToggle', 'closeSidebarBtn', 'mainSearch', 'tempSearch', 'refreshBtn', 'syncNowBtn',
    'currentEmail', 'currentAliasMeta', 'copyEmailBtn', 'aliasLocalPartInput', 'aliasLabelInput',
    'aliasExpirySelect', 'generateAliasBtn', 'createAliasBtn', 'expireAliasBtn', 'deleteAliasBtn',
    'aliasList', 'heroCreateBtn', 'adminName', 'toast', 'toastMsg', 'closeMobileDetailBtn',
  ];
  ids.forEach((id) => { dom[id] = document.getElementById(id); });
}

function bindEvents() {
  dom.loginForm.addEventListener('submit', onLoginSubmit);
  dom.logoutBtn.addEventListener('click', logout);
  dom.tabMailBtn.addEventListener('click', () => switchTab('mail'));
  dom.tabTempBtn.addEventListener('click', () => switchTab('tempmail'));
  dom.sidebarToggle.addEventListener('click', openSidebar);
  dom.closeSidebarBtn.addEventListener('click', closeSidebar);
  dom.sidebarOverlay.addEventListener('click', closeSidebar);
  dom.refreshBtn.addEventListener('click', () => refreshData({ silent: false, forceSync: true }));
  dom.syncNowBtn.addEventListener('click', () => refreshData({ silent: false, forceSync: true }));
  dom.heroCreateBtn.addEventListener('click', () => {
    switchTab('tempmail');
    dom.aliasLocalPartInput.focus();
  });
  dom.copyEmailBtn.addEventListener('click', copySelectedAlias);
  dom.generateAliasBtn.addEventListener('click', () => createAlias(true));
  dom.createAliasBtn.addEventListener('click', () => createAlias(false));
  dom.expireAliasBtn.addEventListener('click', expireSelectedAlias);
  dom.deleteAliasBtn.addEventListener('click', deleteSelectedAlias);
  dom.mainSearch.addEventListener('input', onMainSearchChange);
  dom.tempSearch.addEventListener('input', onAliasSearchChange);
  dom.closeMobileDetailBtn.addEventListener('click', closeMobileDetail);

  document.querySelectorAll('#mailNav .folder-btn').forEach((button) => {
    button.addEventListener('click', () => setMailFilter(button.dataset.filter));
  });

  document.addEventListener('visibilitychange', onVisibilityChange);
}

async function bootstrapSession() {
  try {
    const payload = await api('/api/auth/session');
    state.session = payload.user;
    showApp();
    await loadDashboard();
    restartAutoRefresh();
    restartRelativeTimeTicker();
  } catch {
    showLogin();
  }
}

async function onLoginSubmit(event) {
  event.preventDefault();
  dom.loginError.classList.add('hidden');
  try {
    const payload = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: dom.loginEmail.value.trim(),
        password: dom.loginPassword.value,
      }),
    });
    state.session = payload.user;
    showApp();
    await loadDashboard();
    restartAutoRefresh();
    restartRelativeTimeTicker();
    showToast('Đăng nhập thành công');
  } catch (error) {
    dom.loginError.textContent = error.message || 'Đăng nhập thất bại';
    dom.loginError.classList.remove('hidden');
  }
}

async function logout() {
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } catch {
    // Ignore logout network errors and clear UI anyway.
  }
  state.session = null;
  state.mailboxes = [];
  state.messages = [];
  state.selectedMailboxId = null;
  state.selectedMessageId = null;
  state.selectedMessageCache = null;
  state.recentMessageIds = {};
  state.hasLoadedMessages = false;
  stopAutoRefresh();
  stopRelativeTimeTicker();
  showLogin();
}

function showLogin() {
  dom.appPage.classList.add('hidden');
  dom.loginPage.classList.remove('hidden');
  dom.loginPassword.value = '';
  stopAutoRefresh();
  stopRelativeTimeTicker();
  closeSidebar();
  resetDetail();
  lucide.createIcons();
}

function showApp() {
  dom.adminName.textContent = state.session?.username || 'admin';
  dom.loginPage.classList.add('hidden');
  dom.appPage.classList.remove('hidden');
  lucide.createIcons();
}

function onVisibilityChange() {
  if (!state.session) {
    return;
  }
  if (document.visibilityState === 'visible') {
    refreshData({ silent: true, forceSync: true }).catch(handleError);
    restartAutoRefresh();
    restartRelativeTimeTicker();
    return;
  }
  stopAutoRefresh();
  stopRelativeTimeTicker();
}

function restartAutoRefresh() {
  stopAutoRefresh();
  if (!state.session || document.visibilityState !== 'visible') {
    return;
  }
  autoRefreshTimer = window.setInterval(() => {
    refreshData({ silent: true, forceSync: true }).catch(handleError);
  }, AUTO_VIEW_REFRESH_MS);
}

function stopAutoRefresh() {
  if (!autoRefreshTimer) {
    return;
  }
  window.clearInterval(autoRefreshTimer);
  autoRefreshTimer = null;
}

function restartRelativeTimeTicker() {
  stopRelativeTimeTicker();
  if (!state.session) {
    return;
  }
  relativeTimeTimer = window.setInterval(() => {
    refreshRelativeTimeLabels();
  }, RELATIVE_TIME_REFRESH_MS);
}

function stopRelativeTimeTicker() {
  if (!relativeTimeTimer) {
    return;
  }
  window.clearInterval(relativeTimeTimer);
  relativeTimeTimer = null;
}

function openSidebar() {
  dom.sidebar.classList.remove('-translate-x-full');
  dom.sidebarOverlay.classList.remove('hidden');
}

function closeSidebar() {
  dom.sidebar.classList.add('-translate-x-full');
  dom.sidebarOverlay.classList.add('hidden');
}

function switchTab(tab) {
  state.currentTab = tab;
  dom.tabMailBtn.classList.toggle('active', tab === 'mail');
  dom.tabTempBtn.classList.toggle('active', tab === 'tempmail');
  dom.mailNav.classList.toggle('hidden', tab !== 'mail');
  dom.tempPanel.classList.toggle('hidden', tab !== 'tempmail');
  closeSidebar();
  updateHeader();
  loadMessages().catch(handleError);
}

function setMailFilter(filterName) {
  state.currentFilter = filterName;
  document.querySelectorAll('#mailNav .folder-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.filter === filterName);
  });
  state.selectedMessageId = null;
  state.selectedMessageCache = null;
  updateHeader();
  resetDetail();
  loadMessages().catch(handleError);
}

async function refreshData(options = {}) {
  const { silent = false, forceSync = true } = options;
  if (refreshPromise) {
    return refreshPromise;
  }

  const icon = dom.refreshBtn.querySelector('i');
  if (!silent) {
    icon?.classList.add('spin');
  }

  refreshPromise = (async () => {
    try {
      let syncPayload = null;
      if (forceSync) {
        syncPayload = await api('/api/sync', { method: 'POST' });
      }
      await loadDashboard({ preserveDetail: true });
      if (!silent && syncPayload) {
        showToast(syncPayload.synced ? `Đã đồng bộ ${syncPayload.synced} email mới` : 'Không có email mới');
      }
    } finally {
      if (!silent) {
        icon?.classList.remove('spin');
      }
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

function refreshRelativeTimeLabels() {
  if (!state.session || document.visibilityState !== 'visible') {
    return;
  }

  document.querySelectorAll('[data-relative-time]').forEach((node) => {
    node.textContent = formatRelativeDate(node.dataset.relativeTime);
  });

  document.querySelectorAll('[data-alias-relative-time]').forEach((node) => {
    node.textContent = formatAliasRelativeTime(node.dataset.aliasRelativeTime);
  });

  pruneRecentMessageIds();
  updateRecentMessageDecorations();
}

async function loadDashboard(options = {}) {
  const { preserveDetail = false } = options;
  await loadMailboxes();
  await loadMessages();

  if (!preserveDetail || !state.selectedMessageId || !state.selectedMessageCache) {
    resetDetail();
  }
}

async function loadMailboxes() {
  const payload = await api(`/api/mailboxes?status=visible&search=${encodeURIComponent(state.aliasSearch)}`);
  state.mailboxes = payload.items;

  if (state.mailboxes.length === 0) {
    state.selectedMailboxId = null;
  } else if (!state.mailboxes.some((item) => item.id === state.selectedMailboxId)) {
    const firstActive = state.mailboxes.find((item) => item.status === 'active') || state.mailboxes[0];
    state.selectedMailboxId = firstActive.id;
  }

  renderMailboxes();
  updateCurrentAliasCard();
}

async function loadMessages() {
  const previousIds = new Set(state.messages.map((item) => item.id));
  const params = new URLSearchParams();

  if (state.currentTab === 'tempmail' && state.selectedMailboxId) {
    params.set('alias_id', state.selectedMailboxId);
  }
  params.set('filter_name', state.currentTab === 'mail' ? state.currentFilter : 'all');
  if (state.mainSearch.trim()) {
    params.set('search', state.mainSearch.trim());
  }

  if (state.currentTab === 'tempmail' && !state.selectedMailboxId) {
    state.messages = [];
    renderMessages();
    resetDetail();
    updateHeader();
    return;
  }

  const payload = await api(`/api/messages?${params.toString()}`);
  state.messages = payload.items;
  markRecentMessages(previousIds, state.messages);

  if (!state.messages.some((item) => item.id === state.selectedMessageId)) {
    state.selectedMessageId = null;
    state.selectedMessageCache = null;
  }

  renderMessages();
  updateHeader();
  state.hasLoadedMessages = true;
}

async function createAlias(randomMode) {
  try {
    const localPart = randomMode ? '' : dom.aliasLocalPartInput.value.trim().toLowerCase();
    const label = dom.aliasLabelInput.value.trim();
    const expiresInHours = Number(dom.aliasExpirySelect.value || '24');
    const payload = await api('/api/mailboxes', {
      method: 'POST',
      body: JSON.stringify({
        local_part: localPart,
        label,
        expires_in_hours: expiresInHours,
      }),
    });

    await loadMailboxes();
    state.selectedMailboxId = payload.item.id;
    updateCurrentAliasCard();
    await loadMessages();
    switchTab('tempmail');
    showToast(`Đã tạo ${payload.item.address}`);
  } catch (error) {
    handleError(error);
  }
}

async function expireSelectedAlias() {
  if (!state.selectedMailboxId) {
    showToast('Chưa chọn alias');
    return;
  }
  try {
    await api(`/api/mailboxes/${state.selectedMailboxId}/expire`, { method: 'POST' });
    await loadMailboxes();
    await loadMessages();
    showToast('Alias đã được expire');
  } catch (error) {
    handleError(error);
  }
}

async function deleteSelectedAlias() {
  if (!state.selectedMailboxId) {
    showToast('Chưa chọn alias');
    return;
  }
  try {
    await api(`/api/mailboxes/${state.selectedMailboxId}`, { method: 'DELETE' });
    state.selectedMailboxId = null;
    await loadMailboxes();
    await loadMessages();
    showToast('Alias đã được xóa');
  } catch (error) {
    handleError(error);
  }
}

function onMainSearchChange(event) {
  clearTimeout(mainSearchTimer);
  state.mainSearch = event.target.value;
  mainSearchTimer = setTimeout(() => {
    loadMessages().catch(handleError);
  }, 220);
}

function onAliasSearchChange(event) {
  clearTimeout(aliasSearchTimer);
  state.aliasSearch = event.target.value;
  aliasSearchTimer = setTimeout(() => {
    loadMailboxes().catch(handleError);
  }, 220);
}

function renderMailboxes() {
  if (!dom.aliasList) return;

  if (state.mailboxes.length === 0) {
    dom.aliasList.innerHTML = `
      <div class="text-center text-sm text-gray-400 py-6">
        Chưa có alias nào. Bạn có thể tạo trước hoặc chờ mail gửi tới một địa chỉ bất kỳ để hệ thống tự phát hiện.
      </div>
    `;
    lucide.createIcons();
    return;
  }

  dom.aliasList.innerHTML = state.mailboxes.map((mailbox) => {
    const activeClass = mailbox.id === state.selectedMailboxId ? 'active' : '';
    const statusClass = `status-${mailbox.status}`;
    const label = mailbox.label ? `<p class="text-xs text-gray-500 truncate mt-1">${escapeHtml(mailbox.label)}</p>` : '';
    const meta = mailbox.last_message_at
      ? `Email gần nhất <span data-alias-relative-time="${escapeAttribute(mailbox.last_message_at)}">${formatAliasRelativeTime(mailbox.last_message_at)}</span>`
      : 'Chưa có email';

    return `
      <button class="alias-card ${activeClass} w-full text-left" data-alias-id="${mailbox.id}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-gray-900 truncate">${escapeHtml(mailbox.address)}</p>
            ${label}
            <p class="text-xs text-gray-400 mt-1">${meta}</p>
          </div>
          <span class="status-badge ${statusClass}">${mailbox.status}</span>
        </div>
        <div class="flex items-center justify-between mt-3 text-xs text-gray-500">
          <span>${mailbox.message_count} email</span>
          <span>${mailbox.expires_at ? 'Hết hạn ' + formatShortDate(mailbox.expires_at) : 'Không có hạn'}</span>
        </div>
      </button>
    `;
  }).join('');

  dom.aliasList.querySelectorAll('[data-alias-id]').forEach((button) => {
    button.addEventListener('click', async () => {
      state.selectedMailboxId = Number(button.dataset.aliasId);
      updateCurrentAliasCard();
      renderMailboxes();
      await loadMessages();
    });
  });

  updateCurrentAliasCard();
  lucide.createIcons();
}

function updateCurrentAliasCard() {
  const mailbox = state.mailboxes.find((item) => item.id === state.selectedMailboxId);
  if (!mailbox) {
    dom.currentEmail.textContent = 'Chưa chọn alias';
    dom.currentAliasMeta.textContent = 'Tạo hoặc chọn một alias để xem inbox theo địa chỉ đó.';
    return;
  }
  dom.currentEmail.textContent = mailbox.address;
  dom.currentAliasMeta.textContent = `${mailbox.status} • ${mailbox.message_count} email • ${mailbox.label || 'chưa gắn nhãn'}`;
}

function renderMessages() {
  if (!state.messages.length) {
    dom.emailList.innerHTML = '';
    dom.emailList.classList.add('hidden');
    dom.emptyState.classList.remove('hidden');
    dom.emptyState.classList.add('flex');
    lucide.createIcons();
    return;
  }

  dom.emailList.classList.remove('hidden');
  dom.emptyState.classList.add('hidden');
  dom.emptyState.classList.remove('flex');

  dom.emailList.innerHTML = state.messages.map((message) => {
    const selectedCls = message.id === state.selectedMessageId ? 'selected' : '';
    const unreadCls = message.unread ? 'unread' : '';
    const recentCls = isRecentMessage(message.id) ? 'recent' : '';
    const otpBadge = message.extracted_otps?.length ? `<span class="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">OTP</span>` : '';
    const linkBadge = message.extracted_links?.length ? `<span class="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-semibold">Link</span>` : '';
    const newBadge = isRecentMessage(message.id) ? '<span class="mail-badge mail-badge-new">Email mới</span>' : '';

    return `
      <div class="email-row ${selectedCls} ${unreadCls} ${recentCls} px-4 sm:px-6 py-4 flex items-start gap-3" data-message-id="${message.id}" data-recent-message="${isRecentMessage(message.id) ? 'true' : 'false'}">
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-lush-400 to-lush-600 flex-shrink-0 flex items-center justify-center text-white text-sm font-semibold mt-0.5">
          ${(message.from_name || '?').charAt(0).toUpperCase()}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2 mb-0.5">
            <span class="text-sm ${message.unread ? 'font-bold text-gray-900' : 'font-medium text-gray-700'} truncate">${escapeHtml(message.from_name || message.from_email || 'Unknown Sender')}</span>
            <span class="text-xs text-gray-400 flex-shrink-0 whitespace-nowrap" data-relative-time="${escapeAttribute(message.received_at)}">${formatRelativeDate(message.received_at)}</span>
          </div>
          <p class="text-sm ${message.unread ? 'font-semibold text-gray-800' : 'text-gray-600'} truncate">${escapeHtml(message.subject || '(No subject)')}</p>
          <p class="text-xs text-gray-400 truncate mt-0.5">${escapeHtml(message.recipient_address)}</p>
          <div class="flex items-center gap-2 mt-2 flex-wrap">
            ${newBadge}
            ${otpBadge}
            ${linkBadge}
          </div>
        </div>
      </div>
    `;
  }).join('');

  dom.emailList.querySelectorAll('[data-message-id]').forEach((row) => {
    row.addEventListener('click', () => openMessage(Number(row.dataset.messageId)));
  });

  lucide.createIcons();
}

async function openMessage(messageId) {
  try {
    const payload = await api(`/api/messages/${messageId}`);
    state.selectedMessageId = messageId;
    state.selectedMessageCache = payload.item;
    delete state.recentMessageIds[messageId];
    renderMessages();
    renderDetail(payload.item);
    if (window.innerWidth < 1024) {
      dom.mobileDetail.classList.remove('hidden');
    }
  } catch (error) {
    handleError(error);
  }
}

function renderDetail(message) {
  const detailHTML = `
    <div class="detail-fade-in">
      <div class="flex items-start gap-3 mb-6">
        <div class="w-11 h-11 rounded-full bg-gradient-to-br from-lush-400 to-lush-600 flex-shrink-0 flex items-center justify-center text-white font-semibold">
          ${(message.from_name || '?').charAt(0).toUpperCase()}
        </div>
        <div class="flex-1 min-w-0">
          <h4 class="font-fustat text-base font-bold text-gray-900">${escapeHtml(message.from_name || 'Unknown Sender')}</h4>
          <p class="text-xs text-gray-400 break-all">${escapeHtml(message.from_email || '')}</p>
          <p class="text-xs text-lush-600 mt-1 font-mono">${escapeHtml(message.recipient_address)}</p>
        </div>
      </div>

      <h3 class="font-fustat text-xl font-bold text-gray-900 mb-4 leading-snug">${escapeHtml(message.subject || '(No subject)')}</h3>

      <div class="flex items-center gap-2 mb-6 py-3 border-y border-gray-100">
        <i data-lucide="calendar" class="w-4 h-4 text-gray-400"></i>
        <span class="text-xs text-gray-500">${formatFullDate(message.received_at)}</span>
      </div>

      ${renderDetailExtras(message)}

      <div class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap break-words">
        ${linkifyText(message.text_body || message.snippet || '')}
      </div>
    </div>
  `;

  dom.detailContent.innerHTML = detailHTML;
  dom.mobileDetailContent.innerHTML = detailHTML;
  lucide.createIcons();

  document.querySelectorAll('[data-copy-code]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.copyCode, 'Đã copy OTP'));
  });
}

function renderDetailExtras(message) {
  const otpSection = (message.extracted_otps || []).map((item) => `
    <button data-copy-code="${escapeAttribute(item.code)}" class="detail-chip detail-chip-otp hover:opacity-80">
      <i data-lucide="badge-check" class="w-3.5 h-3.5"></i>
      ${escapeHtml(item.code)}
    </button>
  `).join('');

  const linkSection = (message.extracted_links || []).map((item) => `
    <a href="${escapeAttribute(item.url)}" target="_blank" rel="noreferrer" class="detail-chip detail-chip-link hover:opacity-80">
      <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
      ${escapeHtml(item.type === 'verify' ? 'Mở link verify' : item.type === 'reset_password' ? 'Mở link reset' : 'Mở link')}
    </a>
  `).join('');

  if (!otpSection && !linkSection) {
    return '';
  }

  return `
    <div class="space-y-3 mb-6">
      ${otpSection ? `<div><p class="text-xs uppercase tracking-wider text-gray-400 mb-2 font-semibold">OTP tìm thấy</p><div class="flex flex-wrap gap-2">${otpSection}</div></div>` : ''}
      ${linkSection ? `<div><p class="text-xs uppercase tracking-wider text-gray-400 mb-2 font-semibold">Link quan trọng</p><div class="flex flex-wrap gap-2">${linkSection}</div></div>` : ''}
    </div>
  `;
}

function resetDetail() {
  const html = `
    <div class="flex flex-col items-center justify-center py-20 text-center">
      <div class="w-16 h-16 rounded-full bg-gray-50 flex items-center justify-center mb-4">
        <i data-lucide="mouse-pointer-click" class="w-7 h-7 text-gray-300"></i>
      </div>
      <p class="text-sm text-gray-400">Chọn email để xem chi tiết</p>
    </div>
  `;
  dom.detailContent.innerHTML = html;
  dom.mobileDetailContent.innerHTML = html;
  lucide.createIcons();
}

function closeMobileDetail() {
  dom.mobileDetail.classList.add('hidden');
}

function updateHeader() {
  if (state.currentTab === 'mail') {
    const titles = {
      all: 'Tất cả email',
      unread: 'Email chưa đọc',
      otp: 'Email có OTP',
      links: 'Email có link verify',
    };
    dom.folderTitle.textContent = titles[state.currentFilter] || 'Mail feed';
  } else {
    const mailbox = state.mailboxes.find((item) => item.id === state.selectedMailboxId);
    dom.folderTitle.textContent = mailbox ? mailbox.address : 'Inbox theo alias';
  }
  dom.folderCount.textContent = `${state.messages.length} email`;
}

function copySelectedAlias() {
  const mailbox = state.mailboxes.find((item) => item.id === state.selectedMailboxId);
  if (!mailbox) {
    showToast('Chưa chọn alias');
    return;
  }
  copyText(mailbox.address, 'Đã copy alias');
}

function copyText(value, successMessage) {
  navigator.clipboard.writeText(value).then(() => {
    showToast(successMessage);
  }).catch(() => {
    const temp = document.createElement('textarea');
    temp.value = value;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    showToast(successMessage);
  });
}

function showToast(message) {
  dom.toastMsg.textContent = message;
  dom.toast.classList.add('toast-show');
  setTimeout(() => dom.toast.classList.remove('toast-show'), 2200);
}

function handleError(error) {
  if (error?.status === 401) {
    showToast('Phiên đăng nhập đã hết hạn');
    showLogin();
    return;
  }
  showToast(error.message || 'Đã có lỗi xảy ra');
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = 'Request failed';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      detail = await response.text();
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

function markRecentMessages(previousIds, nextMessages) {
  if (!state.hasLoadedMessages) {
    pruneRecentMessageIds();
    return;
  }

  const now = Date.now();
  nextMessages.forEach((message) => {
    if (!previousIds.has(message.id)) {
      state.recentMessageIds[message.id] = now;
    }
  });
  pruneRecentMessageIds();
}

function pruneRecentMessageIds() {
  const cutoff = Date.now() - NEW_MESSAGE_HIGHLIGHT_MS;
  Object.keys(state.recentMessageIds).forEach((id) => {
    if (state.recentMessageIds[id] < cutoff) {
      delete state.recentMessageIds[id];
    }
  });
}

function isRecentMessage(messageId) {
  return Boolean(state.recentMessageIds[messageId]);
}

function updateRecentMessageDecorations() {
  dom.emailList?.querySelectorAll('[data-recent-message]').forEach((row) => {
    const messageId = Number(row.dataset.messageId);
    const isRecent = isRecentMessage(messageId);
    row.dataset.recentMessage = isRecent ? 'true' : 'false';
    row.classList.toggle('recent', isRecent);
    const badge = row.querySelector('.mail-badge-new');
    if (badge) {
      badge.classList.toggle('hidden', !isRecent);
    }
  });
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}

function linkifyText(value) {
  const escaped = escapeHtml(value);
  return escaped.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" class="text-lush-500 hover:underline break-all" target="_blank" rel="noreferrer">$1</a>');
}

function formatRelativeDate(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Vừa xong';
  if (minutes < 60) return `${minutes} phút trước`;
  if (hours < 24) return `${hours} giờ trước`;
  if (days < 7) return `${days} ngày trước`;
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function formatAliasRelativeTime(dateStr) {
  return formatRelativeDate(dateStr);
}

function formatShortDate(dateStr) {
  return new Date(dateStr).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatFullDate(dateStr) {
  return new Date(dateStr).toLocaleString('vi-VN', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

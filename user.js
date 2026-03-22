const state = {
  session: null,
  currentAlias: '',
  messages: [],
  selectedMessageId: null,
  selectedMessageCache: null,
  detailCache: {},
};

const dom = {};
let toastTimer = null;
let activeLookupToken = 0;
let activeDetailToken = 0;
let userEventsSource = null;
let userEventReconnectTimer = null;
let userEventVersion = 0;

const STREAM_RECONNECT_DELAY_MS = 2500;

const AVATAR_PALETTES = [
  { background: '#ff5528', color: '#fff7f5' },
  { background: '#f97316', color: '#fffaf4' },
  { background: '#2563eb', color: '#eff6ff' },
  { background: '#059669', color: '#ecfdf5' },
  { background: '#7c3aed', color: '#f5f3ff' },
];

document.addEventListener('DOMContentLoaded', async () => {
  cacheDom();
  bindEvents();
  resetShell();
  lucide.createIcons();
  const hasSession = await bootstrapSession();
  if (!hasSession) {
    return;
  }
  await bootstrapFromQuery();
});

function cacheDom() {
  const ids = [
    'lookupForm',
    'aliasInput',
    'lookupBtn',
    'aliasError',
    'userLogoutBtn',
    'lookupShell',
    'preLookupState',
    'currentAliasLabel',
    'messageCountLabel',
    'listLoading',
    'messageList',
    'listEmptyState',
    'detailContent',
    'mobileDetail',
    'mobileDetailContent',
    'closeMobileDetailBtn',
    'toast',
    'toastMsg',
  ];
  ids.forEach((id) => {
    dom[id] = document.getElementById(id);
  });
}

function bindEvents() {
  dom.lookupForm.addEventListener('submit', onLookupSubmit);
  dom.closeMobileDetailBtn.addEventListener('click', closeMobileDetail);
  dom.userLogoutBtn.addEventListener('click', logout);
}

async function bootstrapSession() {
  try {
    const payload = await api('/api/auth/session');
    state.session = payload.user;
    if (state.session.role !== 'user') {
      window.location.replace('/');
      return false;
    }
    return true;
  } catch {
    window.location.replace('/');
    return false;
  }
}

async function bootstrapFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const alias = params.get('alias');
  if (!alias) {
    return;
  }
  dom.aliasInput.value = alias;
  await lookupAlias(alias, { silent: true });
}

async function onLookupSubmit(event) {
  event.preventDefault();
  const rawAlias = String(dom.aliasInput.value || '').trim();
  if (!rawAlias) {
    setAliasError('Vui lòng nhập alias email');
    dom.aliasInput.focus();
    return;
  }
  clearAliasError();
  await lookupAlias(rawAlias);
}

async function lookupAlias(rawAlias, options = {}) {
  const {
    silent = false,
    allowStaleSync = !silent,
    preserveSelection = false,
    scrollAfterLoad = !silent,
    announceResult = !silent,
  } = options;
  const lookupToken = ++activeLookupToken;
  const previousSelectedMessageId = preserveSelection ? state.selectedMessageId : null;
  const shouldShowLoadingState = !(silent && preserveSelection && state.messages.length);
  setLookupBusy(true);
  showShell();
  if (shouldShowLoadingState) {
    renderListLoading(true);
    renderDetailSkeleton();
  }

  try {
    if (allowStaleSync && await shouldForceUserSync()) {
      await api('/api/public/sync', { method: 'POST' });
    }
    const payload = await api(`/api/public/inbox?alias=${encodeURIComponent(rawAlias)}`);
    if (lookupToken !== activeLookupToken) {
      return;
    }

    state.currentAlias = payload.alias?.address || rawAlias.toLowerCase();
    state.messages = Array.isArray(payload.items) ? payload.items : [];
    state.detailCache = preserveSelection
      ? Object.fromEntries(Object.entries(state.detailCache).filter(([messageId]) => state.messages.some((item) => item.id === Number(messageId))))
      : {};
    state.selectedMessageId = previousSelectedMessageId && state.messages.some((item) => item.id === previousSelectedMessageId)
      ? previousSelectedMessageId
      : state.messages[0]?.id || null;
    state.selectedMessageCache = state.selectedMessageId ? (state.detailCache[state.selectedMessageId] || null) : null;

    dom.aliasInput.value = state.currentAlias;
    dom.currentAliasLabel.textContent = state.currentAlias;
    dom.messageCountLabel.textContent = `${state.messages.length} email`;
    updateQueryString(state.currentAlias);
    startUserEventStream(state.currentAlias);
    renderMessages();

    if (!state.messages.length) {
      renderListEmpty(
        'Alias chưa có email',
        `Hệ thống chưa ghi nhận thư nào cho ${state.currentAlias}.`,
      );
      resetDetail(
        'Chưa có thư để hiển thị',
        'Khi alias này nhận email đầu tiên, nội dung sẽ hiện ở panel bên phải.',
      );
    } else if (preserveSelection && state.selectedMessageCache) {
      renderDetail(state.selectedMessageCache);
    } else {
      await openMessage(state.selectedMessageId);
    }

    if (scrollAfterLoad) {
      scrollToLookupResults();
    }
    if (announceResult) {
      showToast(state.messages.length ? `Đã tải ${state.messages.length} email` : 'Chưa thấy email nào cho alias này');
    }
  } catch (error) {
    if (lookupToken !== activeLookupToken) {
      return;
    }
    state.currentAlias = '';
    state.messages = [];
    state.selectedMessageId = null;
    state.selectedMessageCache = null;
    state.detailCache = {};
    stopUserEventStream();
    renderListEmpty('Không tải được inbox', error.message || 'Có lỗi khi kiểm tra alias.');
    resetDetail('Kiểm tra lại alias', 'Alias không hợp lệ hoặc hệ thống chưa sẵn sàng.');
    setAliasError(error.message || 'Không thể kiểm tra alias');
  } finally {
    if (lookupToken === activeLookupToken) {
      setLookupBusy(false);
      renderListLoading(false);
    }
  }
}

function resetShell() {
  stopUserEventStream();
  dom.lookupShell.classList.add('hidden');
  dom.preLookupState.classList.remove('hidden');
  dom.currentAliasLabel.textContent = '-';
  dom.messageCountLabel.textContent = '0 email';
  renderListEmpty('Chưa có email', 'Nhập alias phía trên để kiểm tra hộp thư.');
  resetDetail();
}

function showShell() {
  dom.lookupShell.classList.remove('hidden');
  dom.preLookupState.classList.add('hidden');
}

function scrollToLookupResults() {
  const formTop = dom.lookupForm.getBoundingClientRect().top + window.scrollY;
  const targetTop = Math.max(formTop - 45, 0);
  const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

  window.scrollTo({
    top: targetTop,
    behavior,
  });
}

async function shouldForceUserSync() {
  try {
    const payload = await api('/api/mail-sync/status');
    return Boolean(payload.item?.is_stale);
  } catch {
    return true;
  }
}

function startUserEventStream(alias) {
  stopUserEventStream();
  if (!alias || typeof EventSource === 'undefined') {
    return;
  }

  userEventVersion = 0;
  userEventsSource = new EventSource(`/api/public/events?alias=${encodeURIComponent(alias)}`, { withCredentials: true });
  userEventsSource.addEventListener('ready', handleUserStreamEvent);
  userEventsSource.addEventListener('heartbeat', handleUserStreamEvent);
  userEventsSource.addEventListener('messages', handleUserStreamEvent);
  userEventsSource.onerror = () => {
    scheduleUserEventReconnect();
  };
}

function stopUserEventStream() {
  if (userEventsSource) {
    userEventsSource.close();
    userEventsSource = null;
  }
  if (userEventReconnectTimer) {
    window.clearTimeout(userEventReconnectTimer);
    userEventReconnectTimer = null;
  }
}

function scheduleUserEventReconnect() {
  if (userEventReconnectTimer || !state.currentAlias) {
    return;
  }
  stopUserEventStream();
  userEventReconnectTimer = window.setTimeout(() => {
    userEventReconnectTimer = null;
    startUserEventStream(state.currentAlias);
  }, STREAM_RECONNECT_DELAY_MS);
}

function handleUserStreamEvent(event) {
  let payload;
  try {
    payload = JSON.parse(event.data || '{}');
  } catch {
    return;
  }

  if (typeof payload.version === 'number' && payload.version > userEventVersion) {
    userEventVersion = payload.version;
  }

  if (event.type !== 'messages' || !state.currentAlias) {
    return;
  }

  lookupAlias(state.currentAlias, {
    silent: true,
    allowStaleSync: false,
    preserveSelection: true,
    scrollAfterLoad: false,
    announceResult: false,
  }).catch(handleError);
}

function renderListLoading(isVisible) {
  dom.listLoading.classList.toggle('hidden', !isVisible);
  dom.messageList.classList.toggle('hidden', isVisible);
  if (isVisible) {
    dom.listEmptyState.classList.add('hidden');
  }
}

function renderListEmpty(title, description) {
  dom.messageList.innerHTML = '';
  dom.messageList.classList.add('hidden');
  dom.listLoading.classList.add('hidden');
  dom.listEmptyState.classList.remove('hidden');
  dom.listEmptyState.innerHTML = `
    <div class="mx-auto flex h-16 w-16 items-center justify-center border border-slate-200 bg-slate-50 text-slate-300">
      <i data-lucide="inbox" class="w-7 h-7"></i>
    </div>
    <p class="mt-5 font-fustat text-xl font-bold text-slate-900">${escapeHtml(title)}</p>
    <p class="mt-2 text-sm leading-7 text-slate-500">${escapeHtml(description)}</p>
  `;
  lucide.createIcons();
}

function renderMessages() {
  if (!state.messages.length) {
    renderListEmpty('Chưa có email', 'Alias này hiện chưa có thư nào.');
    return;
  }

  dom.listLoading.classList.add('hidden');
  dom.listEmptyState.classList.add('hidden');
  dom.messageList.classList.remove('hidden');
  dom.messageList.innerHTML = state.messages.map((message) => {
    const isSelected = state.selectedMessageId === message.id;
    const avatar = getAvatarPresentation(message);
    const sender = escapeHtml(getSenderDisplayName(message));
    const subject = escapeHtml(message.subject || '(No subject)');
    const snippet = escapeHtml(getMessagePreview(message));

    return `
      <article class="user-message-row ${isSelected ? 'selected' : ''}" data-message-id="${message.id}">
        <div class="mail-avatar" style="background:${avatar.background}; color:${avatar.color};">
          ${avatar.label}
        </div>
        <div class="user-message-main">
          <div class="user-message-top">
            <p class="user-message-sender">${sender}</p>
            <span class="user-message-time">${formatRelativeDate(message.received_at)}</span>
          </div>
          <p class="user-message-subject ${message.unread ? 'is-unread' : ''}">${subject}</p>
          <p class="user-message-snippet">${snippet}</p>
        </div>
      </article>
    `;
  }).join('');

  dom.messageList.querySelectorAll('[data-message-id]').forEach((row) => {
    row.addEventListener('click', async () => {
      await openMessage(Number(row.dataset.messageId));
    });
  });
}

async function openMessage(messageId) {
  if (!state.currentAlias || !messageId) {
    return;
  }

  state.selectedMessageId = messageId;
  renderMessages();

  if (state.detailCache[messageId]) {
    state.selectedMessageCache = state.detailCache[messageId];
    renderDetail(state.selectedMessageCache);
  } else {
    renderDetailSkeleton();
  }

  const detailToken = ++activeDetailToken;
  try {
    const payload = await api(`/api/public/messages/${messageId}?alias=${encodeURIComponent(state.currentAlias)}`);
    if (detailToken !== activeDetailToken || state.selectedMessageId !== messageId) {
      return;
    }

    const detail = payload.item;
    state.detailCache[messageId] = detail;
    state.selectedMessageCache = detail;
    markMessageReadLocally(messageId);
    renderMessages();
    renderDetail(detail);
    if (window.innerWidth < 1024) {
      openMobileDetail();
    }
  } catch (error) {
    if (detailToken !== activeDetailToken) {
      return;
    }
    handleError(error);
  }
}

async function logout() {
  stopUserEventStream();
  try {
    await api('/api/auth/logout', { method: 'POST' });
  } catch {
    // Ignore logout failures and continue redirecting to the shared login page.
  }
  window.location.replace('/');
}

function markMessageReadLocally(messageId) {
  const target = state.messages.find((item) => item.id === messageId);
  if (target) {
    target.unread = false;
  }
}

function renderDetailSkeleton() {
  const html = `
    <div class="detail-card p-6 sm:p-7">
      <div class="detail-skeleton">
        <div class="flex items-center gap-4">
          <div class="h-12 w-12 rounded-full bg-slate-200"></div>
          <div class="flex-1 space-y-3">
            <div class="line w-32"></div>
            <div class="line w-48"></div>
          </div>
        </div>
        <div class="detail-divider my-1"></div>
        <div class="line w-20"></div>
        <div class="line w-[82%]"></div>
        <div class="line w-[64%]"></div>
        <div class="detail-divider my-1"></div>
        <div class="line w-[92%]"></div>
        <div class="line w-[96%]"></div>
        <div class="line w-[86%]"></div>
      </div>
    </div>
  `;
  dom.detailContent.innerHTML = html;
  dom.mobileDetailContent.innerHTML = html;
}

function renderDetail(message) {
  const avatar = getAvatarPresentation(message);
  const detailHtml = `
    <div class="detail-card p-6 sm:p-7">
      <div class="flex items-start gap-4">
        <div class="mail-avatar-detail" style="background:${avatar.background}; color:${avatar.color};">
          ${avatar.label}
        </div>
        <div class="min-w-0">
          <p class="text-sm font-semibold text-slate-900">${escapeHtml(getSenderDisplayName(message))}</p>
          <p class="mt-1 break-all text-sm text-slate-500">${escapeHtml(message.from_email || '')}</p>
          <p class="mt-2 break-all text-sm text-slate-500">${escapeHtml(message.recipient_address)}</p>
        </div>
      </div>

      <div class="detail-divider mt-6"></div>

      <div class="pt-6">
        <h4 class="font-fustat text-[30px] font-bold leading-snug text-slate-900">${escapeHtml(message.subject || '(No subject)')}</h4>
        <p class="mt-4 text-sm text-slate-500">${escapeHtml(formatFullDate(message.received_at))}</p>
      </div>

      <div class="detail-divider mt-6"></div>

      <div class="pt-6">
        <div class="detail-body-copy">${linkifyText(message.text_body || message.snippet || 'Email này không có nội dung text preview.')}</div>
      </div>
    </div>
  `;

  dom.detailContent.innerHTML = detailHtml;
  dom.mobileDetailContent.innerHTML = detailHtml;
}

function resetDetail(
  title = 'Chọn email để xem chi tiết',
  description = 'Sau khi kiểm tra alias, chọn một email trong danh sách bên trái để mở nội dung.',
) {
  const html = `
    <div class="detail-card flex min-h-[560px] items-center justify-center p-6 sm:p-7">
      <div class="max-w-md text-center">
        <div class="mx-auto flex h-16 w-16 items-center justify-center border border-slate-200 bg-white text-slate-300">
          <i data-lucide="panel-right-open" class="w-7 h-7"></i>
        </div>
        <p class="mt-5 font-fustat text-2xl font-bold text-slate-900">${escapeHtml(title)}</p>
        <p class="mt-3 text-sm leading-7 text-slate-500">${escapeHtml(description)}</p>
      </div>
    </div>
  `;
  dom.detailContent.innerHTML = html;
  dom.mobileDetailContent.innerHTML = html;
  lucide.createIcons();
}

function openMobileDetail() {
  dom.mobileDetail.classList.remove('hidden');
}

function closeMobileDetail() {
  dom.mobileDetail.classList.add('hidden');
}

function setLookupBusy(isBusy) {
  dom.lookupBtn.disabled = isBusy;
}

function setAliasError(message) {
  dom.aliasError.textContent = message;
  dom.aliasError.classList.remove('hidden');
}

function clearAliasError() {
  dom.aliasError.textContent = '';
  dom.aliasError.classList.add('hidden');
}

function updateQueryString(alias) {
  const url = new URL(window.location.href);
  if (alias) {
    url.searchParams.set('alias', alias);
  } else {
    url.searchParams.delete('alias');
  }
  window.history.replaceState({}, '', url);
}

function getAvatarPresentation(message) {
  const seed = `${message.recipient_address || ''}|${message.from_email || ''}|${message.from_name || ''}`;
  const palette = AVATAR_PALETTES[Math.abs(hashCode(seed)) % AVATAR_PALETTES.length];
  return {
    background: palette.background,
    color: palette.color,
    label: getInitials(getSenderDisplayName(message)),
  };
}

function getSenderDisplayName(message) {
  const fromName = String(message.from_name || '').trim();
  if (fromName) {
    return fromName;
  }

  const fromEmail = String(message.from_email || '').trim();
  if (fromEmail) {
    return fromEmail;
  }

  return 'Unknown Sender';
}

function getMessagePreview(message) {
  const preview = String(message.snippet || message.text_body || '')
    .replace(/\s+/g, ' ')
    .trim();

  if (preview) {
    return preview;
  }

  return 'Chưa có preview cho email này.';
}

function getInitials(value) {
  const normalized = String(value || '').replace(/<[^>]+>/g, ' ').trim();
  if (!normalized) {
    return '?';
  }

  const tokens = normalized
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2);

  if (!tokens.length) {
    return normalized.charAt(0).toUpperCase();
  }

  return tokens
    .map((token) => token.charAt(0).toUpperCase())
    .join('')
    .slice(0, 2);
}

function hashCode(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash) + value.charCodeAt(index);
    hash |= 0;
  }
  return hash;
}

function showToast(message) {
  dom.toastMsg.textContent = message;
  dom.toast.classList.add('toast-show');
  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }
  toastTimer = window.setTimeout(() => {
    dom.toast.classList.remove('toast-show');
  }, 2200);
}

function handleError(error) {
  if (error?.status === 401 || error?.status === 403) {
    window.location.replace('/');
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
    const rawText = await response.text();
    if (rawText) {
      try {
        const payload = JSON.parse(rawText);
        detail = payload.detail || detail;
      } catch {
        detail = rawText;
      }
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

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
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

const $ = id => document.getElementById(id);
const stage = $('stage');
const draw = $('draw');
const cookie = $('cookie');
const copy = $('copy');
const status = $('status');
const paper = $('paper');
const content = $('paper-content');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const mini = new URLSearchParams(location.search).get('mini') === '1';
document.body.classList.toggle('mini', mini);
let state = 'idle';
let busy = false;
let lastIndex = -1;
let currentFortune = '';
let drawCount = 0;
let popupWindow;
const pause = ms => new Promise(resolve => setTimeout(resolve, reducedMotion ? 0 : ms));
const cookieReady = Promise.all([...cookie.querySelectorAll('img')].map(img => img.decode().catch(() => {})));
const finishMotion = () => Promise.all(stage.getAnimations({subtree:true}).map(animation => animation.finished.catch(() => {})));

function announce(message, visible = false) {
  status.classList.toggle('announcement', !visible);
  status.textContent = message;
}

function setBusy(value) {
  busy = value;
  draw.disabled = $('redraw').disabled = value;
}

function revealFortune() {
  state = 'open';
  content.removeAttribute('aria-hidden');
  $('close-paper').hidden = false;
  $('hint').textContent = '쿠키 안에 있던, 당신을 위한 한마디.';
  draw.textContent = '하나 더 뽑기';
  copy.hidden = false;
  $('redraw').hidden = true;
  setBusy(false);
  announce(currentFortune);
  $('close-paper').focus({preventScroll:true});
}

async function crackCookie() {
  if (busy) return;
  setBusy(true);
  state = 'drawing';
  ++drawCount;
  copy.hidden = $('redraw').hidden = true;
  $('close-paper').hidden = true;
  content.setAttribute('aria-hidden', 'true');
  cookie.disabled = true;
  announce('');
  await cookieReady;
  if (lastIndex !== -1) {
    stage.classList.add('resetting');
    await pause(180);
  }
  paper.hidden = true;
  stage.classList.remove('drawn', 'flowing', 'tucked');
  if (lastIndex !== -1) {
    // Settle the hidden scene before fading the next cookie back in.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    stage.classList.remove('resetting');
    await pause(180);
  }
  let index;
  do {
    const value = new Uint32Array(1);
    crypto.getRandomValues(value);
    index = Math.floor(value[0] / 4294967296 * FORTUNES.length);
  } while (index === lastIndex && FORTUNES.length > 1);
  lastIndex = index;
  currentFortune = FORTUNES[index].text;
  $('fortune').textContent = currentFortune;
  content.hidden = false;
  paper.hidden = false;
  $('hint').textContent = '쿠키 속 작은 행운을 꺼내는 중…';
  // Cookie, paper and printed text share one overlapping timeline.
  stage.classList.add('drawn', 'flowing');
  await finishMotion();
  stage.classList.remove('flowing');
  revealFortune();
}

function closeFortune() {
  if (busy || state !== 'open') return;
  state = 'closed';
  content.setAttribute('aria-hidden', 'true');
  $('close-paper').hidden = true;
  stage.classList.add('tucked');
  copy.hidden = true;
  draw.textContent = '문구 다시 보기';
  $('redraw').hidden = false;
  $('hint').textContent = '잠시 접어 둘게요. 같은 문구를 다시 볼 수 있어요.';
  announce('');
  draw.focus({preventScroll:true});
}

async function openOrDraw() {
  if (busy) return;
  if (state !== 'closed') return crackCookie();
  setBusy(true);
  stage.classList.remove('tucked');
  await finishMotion();
  revealFortune();
}

draw.addEventListener('click', openOrDraw);
cookie.addEventListener('click', crackCookie);
$('close-paper').addEventListener('click', closeFortune);
$('redraw').addEventListener('click', crackCookie);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closeFortune();
});
copy.addEventListener('click', async () => {
  const copiedDraw = drawCount;
  try {
    await navigator.clipboard.writeText(currentFortune);
    if (copiedDraw !== drawCount || state !== 'open') return;
    announce('작은 행운을 복사했어요.', true);
  } catch {
    if (copiedDraw !== drawCount || state !== 'open') return;
    announce('문구를 길게 누르거나 드래그해서 복사해 주세요.', true);
  }
});

$('small-window').addEventListener('click', () => {
  if (popupWindow && !popupWindow.closed) {
    popupWindow.focus();
    return;
  }
  const width = Math.min(440, screen.availWidth);
  const height = Math.min(660, screen.availHeight);
  const left = Math.max(0, Math.round(window.screenX + (window.outerWidth - width) / 2));
  const top = Math.max(0, Math.round(window.screenY + (window.outerHeight - height) / 2));
  const url = new URL(location.href);
  url.searchParams.set('mini', '1');
  try {
    popupWindow = window.open(url.href, 'gahee42-fortune-cookie', `popup=yes,width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`);
  } catch { popupWindow = null; }
  if (popupWindow) {
    popupWindow.focus();
    announce('새 탭으로 열렸다면 데스크톱 브라우저에서 작은 창을 이용해 주세요.', true);
  } else {
    announce('팝업이 차단됐어요. 팝업을 허용한 뒤 다시 눌러 주세요.', true);
  }
});

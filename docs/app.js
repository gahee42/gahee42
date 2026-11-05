const $ = id => document.getElementById(id);
const stage = $('stage');
const draw = $('draw');
const cookie = $('cookie');
const copy = $('copy');
const status = $('status');
const paper = $('paper');
const unfold = $('unfold');
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

function announce(message, visible = false) {
  status.classList.toggle('announcement', !visible);
  status.textContent = message;
}

function setBusy(value) {
  busy = value;
  draw.disabled = unfold.disabled = $('redraw').disabled = value;
}

async function crackCookie() {
  if (busy) return;
  setBusy(true);
  state = 'drawing';
  ++drawCount;
  copy.hidden = $('redraw').hidden = true;
  content.hidden = true;
  unfold.hidden = false;
  paper.hidden = true;
  $('fortune').textContent = '';
  cookie.disabled = true;
  stage.classList.remove('drawn', 'unfolded');
  $('hint').textContent = '쿠키 속 작은 쪽지를 꺼내는 중…';
  announce('');
  if (lastIndex !== -1) await pause(500);
  let index;
  do {
    const value = new Uint32Array(1);
    crypto.getRandomValues(value);
    index = Math.floor(value[0] / 4294967296 * FORTUNES.length);
  } while (index === lastIndex && FORTUNES.length > 1);
  lastIndex = index;
  currentFortune = FORTUNES[index].text;
  stage.classList.add('cracking');
  await pause(300);
  stage.classList.remove('cracking');
  stage.classList.add('drawn');
  await pause(300);
  paper.hidden = false;
  await pause(500);
  state = 'folded';
  $('hint').textContent = '작은 쪽지가 나왔어요. 살며시 펼쳐 볼까요?';
  draw.textContent = '쪽지 펼치기';
  $('redraw').hidden = false;
  setBusy(false);
  announce('접힌 쪽지가 나왔어요. 펼쳐서 운세를 확인해 보세요.');
  unfold.focus({preventScroll:true});
}

async function unfoldFortune() {
  if (busy || state !== 'folded') return;
  setBusy(true);
  unfold.hidden = true;
  stage.classList.add('unfolded');
  await pause(650);
  $('fortune').textContent = currentFortune;
  content.hidden = false;
  state = 'open';
  $('hint').textContent = '오늘 당신에게 도착한 작은 행운이에요.';
  draw.textContent = '하나 더 뽑기';
  copy.hidden = false;
  $('redraw').hidden = true;
  setBusy(false);
  announce(currentFortune);
  $('close-paper').focus({preventScroll:true});
}

async function foldFortune() {
  if (busy || state !== 'open') return;
  setBusy(true);
  content.hidden = true;
  copy.hidden = true;
  announce('');
  stage.classList.remove('unfolded');
  await pause(650);
  state = 'folded';
  unfold.hidden = false;
  $('hint').textContent = '잘 접어 두었어요. 다시 펼쳐도 같은 행운이에요.';
  draw.textContent = '쪽지 다시 펼치기';
  $('redraw').hidden = false;
  setBusy(false);
  unfold.focus({preventScroll:true});
}

draw.addEventListener('click', () => state === 'folded' ? unfoldFortune() : crackCookie());
cookie.addEventListener('click', crackCookie);
unfold.addEventListener('click', unfoldFortune);
$('close-paper').addEventListener('click', foldFortune);
$('redraw').addEventListener('click', crackCookie);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') foldFortune();
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

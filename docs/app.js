const $ = id => document.getElementById(id);
const stage = $('stage');
const draw = $('draw');
const cookie = $('cookie');
const copy = $('copy');
const status = $('status');
const mini = new URLSearchParams(location.search).get('mini') === '1';
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
document.body.classList.toggle('mini', mini);
let busy = false;
let lastIndex = -1;
let currentFortune = '';
let drawCount = 0;
let isOpen = false;
let returnFocus = draw;

function closeFortune() {
  if (busy || !isOpen) return;
  isOpen = false;
  stage.classList.remove('opened');
  $('paper').setAttribute('aria-hidden', 'true');
  $('close-paper').tabIndex = -1;
  cookie.disabled = false;
  cookie.setAttribute('aria-label', '같은 운세 다시 보기');
  draw.textContent = '문구 다시 보기';
  copy.hidden = true;
  $('redraw').hidden = false;
  $('hint').textContent = '잠깐 접어 둘게요. 다시 봐도 같은 문구예요.';
  status.textContent = '';
  returnFocus.focus();
}

function revealFortune() {
  isOpen = true;
  stage.classList.add('opened');
  $('paper').setAttribute('aria-hidden', 'false');
  $('close-paper').tabIndex = 0;
  cookie.disabled = true;
  $('hint').textContent = '오늘의 운세 도착! 좋은 기운만 챙겨 가요.';
  draw.innerHTML = '하나 더 뽑기 <span aria-hidden="true">↻</span>';
  copy.hidden = false;
  $('redraw').hidden = true;
  status.classList.add('announcement');
  status.textContent = currentFortune;
  $('close-paper').focus({preventScroll:true});
}

function openOrDraw() {
  if (busy) return;
  returnFocus = document.activeElement === cookie ? cookie : draw;
  if (currentFortune && !isOpen) revealFortune();
  else crackCookie();
}

async function crackCookie() {
  if (busy) return;
  busy = true;
  ++drawCount;
  isOpen = false;
  draw.disabled = cookie.disabled = true;
  copy.hidden = true;
  $('redraw').hidden = true;
  $('close-paper').tabIndex = -1;
  status.textContent = '';
  $('paper').setAttribute('aria-hidden', 'true');
  stage.classList.remove('opened', 'cracking');
  $('hint').textContent = '쿠키 속 행운을 꺼내는 중…';
  if (lastIndex !== -1) await new Promise(resolve => setTimeout(resolve, reducedMotion ? 0 : 650));
  let index;
  do {
    const value = new Uint32Array(1);
    crypto.getRandomValues(value);
    index = Math.floor(value[0] / 4294967296 * FORTUNES.length);
  } while (index === lastIndex && FORTUNES.length > 1);
  lastIndex = index;
  currentFortune = FORTUNES[index].text;
  $('fortune').textContent = currentFortune;
  stage.classList.add('cracking');
  await new Promise(resolve => setTimeout(resolve, reducedMotion ? 0 : 350));
  stage.classList.remove('cracking');
  stage.classList.add('opened');
  await new Promise(resolve => setTimeout(resolve, reducedMotion ? 0 : 750));
  revealFortune();
  draw.disabled = false;
  busy = false;
}

draw.addEventListener('click', openOrDraw);
cookie.addEventListener('click', openOrDraw);
$('close-paper').addEventListener('click', closeFortune);
$('redraw').addEventListener('click', () => { returnFocus = draw; crackCookie(); });
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && isOpen) closeFortune();
});
copy.addEventListener('click', async () => {
  const copiedDraw = drawCount;
  try {
    await navigator.clipboard.writeText(currentFortune);
    if (copiedDraw !== drawCount) return;
    status.classList.remove('announcement');
    status.textContent = '작은 행운을 복사했어요.';
  } catch {
    status.classList.remove('announcement');
    status.textContent = '문구를 길게 누르거나 드래그해서 복사해 주세요.';
  }
});

$('small-window').addEventListener('click', () => {
  const width = Math.min(480, screen.availWidth);
  const height = Math.min(660, screen.availHeight);
  const left = Math.max(0, Math.round(window.screenX + (window.outerWidth - width) / 2));
  const top = Math.max(0, Math.round(window.screenY + (window.outerHeight - height) / 2));
  const url = new URL(location.href);
  url.searchParams.set('mini', '1');
  let popup;
  try { popup = window.open(url.href, 'gahee42-fortune-cookie', `popup=yes,width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`); } catch {}
  status.classList.remove('announcement');
  if (popup) {
    popup.focus();
    status.textContent = '별도 창으로 열었어요. 창 모양은 브라우저에 따라 달라요.';
  } else {
    status.textContent = '팝업이 차단됐어요. 이 화면에서도 바로 쿠키를 뽑을 수 있어요.';
  }
});

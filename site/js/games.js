/* The Double Wide's daily puzzle. One game a day (Mon Sudoku · Tue Word Search · Wed Cryptogram · Thu Jumble · Fri Minesweeper ·
   Sat Nonogram · Sun Five Leaf), built from the day's date so everybody gets the same puzzle, and played full-screen on its own layer
   so page turns can't steal a tap. The paper's page only holds the button: <button class="pz-play" data-game data-date data-words data-quotes>. */
(function () {
  'use strict';
  var NAMES = { sudoku: 'Sudoku', wordsearch: 'Word Search', cryptogram: 'Cryptogram', jumble: 'Jumble', mines: 'Minesweeper', nonogram: 'Nonogram', fiveleaf: 'Five Leaf' };
  var HOWTO = {
    sudoku: 'Fill every row, column and 3×3 box with 1–9. Tap a square, then a number.',
    wordsearch: 'Tap the first letter of a word, then its last letter. Words run any direction.',
    cryptogram: 'Each letter stands for another. Tap a letter, then pick what you think it really is.',
    jumble: 'Unscramble each word from today\'s paper.',
    mines: 'Clear the board without hitting a mine. Numbers count the mines touching that square. Switch to 🚩 to flag.',
    nonogram: 'The numbers are runs of filled squares in that row or column, in order. Tap to fill; switch to ✕ to mark blanks.',
    fiveleaf: 'Guess the five-letter word in six tries. Green = right spot, gold = in the word, gray = not in it.'
  };
  var GARDEN = ['GANJA', 'CHRONIC', 'MAPLE', 'HERBIE', 'HOMIE', 'IBBY', 'BAKER', 'CYPHER', 'CLYDIUS', 'GARDEN', 'RELAY', 'VAULT', 'TOKENS', 'PAYROLL', 'SPORTS', 'WEATHER'];
  var SAYINGS = ['A watched cron job never runs.', 'Roll it tight, ship it right.', 'Every seed was once a little nut that held its ground.',
                 'The best time to plant a tree was twenty years ago. The second best time is now.', 'Measure twice, reboot once.',
                 'Leave the Garden better than you found it.', 'Slow and steady keeps the tokens ready.'];
  var LEAVES = ['PLANT', 'SEEDS', 'ROOTS', 'BLOOM', 'GRASS', 'TOKEN', 'RELAY', 'VAULT', 'SHELL', 'PIXEL', 'CACHE', 'PROXY', 'ROUTE', 'BUILD', 'PATCH',
                'DEBUG', 'STACK', 'QUEUE', 'LINUX', 'SPORE', 'PETAL', 'STEMS', 'THORN', 'TULIP', 'BASIL', 'THYME', 'CLOVE', 'DAISY', 'LILAC', 'MAPLE',
                'CEDAR', 'BIRCH', 'ACORN', 'HONEY', 'BAKED', 'GREEN', 'SMOKE', 'ROACH', 'PAPER', 'FLAME', 'LIGHT', 'HERBS', 'CHILL', 'TORCH', 'FROST',
                'MULCH', 'SPADE', 'HEDGE', 'FERNS', 'PEONY', 'OLIVE', 'LEMON', 'MANGO', 'GRAPE', 'SPRIG', 'CLOUD', 'NODES', 'BYTES', 'LOGIN'];

  // ---------- helpers ----------
  function hash(s) { var h = 1779033703 ^ s.length; for (var i = 0; i < s.length; i++) { h = Math.imul(h ^ s.charCodeAt(i), 3432918353); h = h << 13 | h >>> 19; } return h >>> 0; }
  function rng(seed) { var a = hash(seed); return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function shuffle(a, r) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(r() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function store(k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem('dw-game-' + k) || 'null'); localStorage.setItem('dw-game-' + k, JSON.stringify(v)); } catch (e) { return null; } }

  // ---------- the full-screen layer ----------
  var layer, body, status, current;
  function open(btn) {
    var game = btn.dataset.game, date = btn.dataset.date, words = [], quotes = [];
    try { words = JSON.parse(btn.dataset.words || '[]'); } catch (e) {}
    try { quotes = JSON.parse(btn.dataset.quotes || '[]'); } catch (e) {}
    if (!layer) {
      layer = el('div', 'gm'); layer.setAttribute('role', 'dialog'); layer.setAttribute('aria-modal', 'true');
      layer.innerHTML = '<div class="gm-card"><header class="gm-top"><div><div class="gm-kick">The Daily Puzzle</div><h2 class="gm-title"></h2></div>' +
        '<button type="button" class="gm-x" aria-label="Close the puzzle">×</button></header><p class="gm-how"></p><div class="gm-body"></div>' +
        '<div class="gm-status" aria-live="polite"></div></div>';
      document.body.appendChild(layer);
      ['touchstart', 'touchmove', 'touchend', 'wheel', 'mousedown', 'mousemove', 'mouseup', 'keydown', 'keyup', 'pointerdown', 'pointermove', 'pointerup'].forEach(function (t) {
        layer.addEventListener(t, function (e) { e.stopPropagation(); }, { passive: t.indexOf('touch') === 0 || t === 'wheel' });
      });
      layer.addEventListener('click', function (e) { e.stopPropagation(); if (e.target === layer) close(); });
      layer.querySelector('.gm-x').onclick = close;
      body = layer.querySelector('.gm-body'); status = layer.querySelector('.gm-status');
    }
    layer.querySelector('.gm-title').textContent = NAMES[game] + ' · ' + new Date(date + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
    layer.querySelector('.gm-how').textContent = HOWTO[game];
    body.innerHTML = ''; body.className = 'gm-body gm-' + game; say('');
    current = { key: date + '-' + game, btn: btn };
    document.documentElement.classList.add('gm-open'); layer.hidden = false;
    var r = rng(date + ':' + game);
    ({ sudoku: sudoku, wordsearch: wordsearch, cryptogram: cryptogram, jumble: jumble, mines: mines, nonogram: nonogram, fiveleaf: fiveleaf })[game](r, words, quotes);
    if (store(current.key)) say('✅ You already solved this one — play it again for fun.');
  }
  function close() { if (layer) layer.hidden = true; document.documentElement.classList.remove('gm-open'); }
  function say(t) { status.textContent = t; }
  function won(msg) {
    say('🎉 ' + (msg || 'Solved!'));
    store(current.key, { solved: new Date().toISOString() });
    paintSolved();
  }
  function paintSolved() {
    Array.prototype.forEach.call(document.querySelectorAll('.pz-play'), function (b) {
      if (store(b.dataset.date + '-' + b.dataset.game)) b.classList.add('solved');
    });
  }
  function bar(buttons) {
    var b = el('div', 'gm-bar');
    buttons.forEach(function (x) { var k = el('button', 'gm-btn' + (x.cls ? ' ' + x.cls : ''), x.label); k.type = 'button'; k.onclick = function () { x.fn(k); }; b.appendChild(k); });
    body.appendChild(b); return b;
  }
  function paperWords(words, min, max) {
    var seen = {}, out = [];
    words.concat(GARDEN).forEach(function (w) { w = String(w).toUpperCase().replace(/[^A-Z]/g, ''); if (w.length >= min && w.length <= max && !seen[w]) { seen[w] = 1; out.push(w); } });
    return out;
  }

  // ---------- Sudoku ----------
  function sudoku(r) {
    var base = [], i, rows = [], cols = [];
    [0, 1, 2].forEach(function (b) { shuffle([0, 1, 2], r).forEach(function (x) { rows.push(b * 3 + x); }); });
    var bands = shuffle([0, 1, 2], r); rows = bands.reduce(function (a, b) { return a.concat(rows.slice(b * 3, b * 3 + 3)); }, []);
    [0, 1, 2].forEach(function (b) { shuffle([0, 1, 2], r).forEach(function (x) { cols.push(b * 3 + x); }); });
    var stacks = shuffle([0, 1, 2], r); cols = stacks.reduce(function (a, b) { return a.concat(cols.slice(b * 3, b * 3 + 3)); }, []);
    var digits = shuffle([1, 2, 3, 4, 5, 6, 7, 8, 9], r);
    for (i = 0; i < 81; i++) { var rr = rows[Math.floor(i / 9)], cc = cols[i % 9]; base.push(digits[(3 * (rr % 3) + Math.floor(rr / 3) + cc) % 9]); }
    var puzzle = base.slice();
    function ok(g, p, v) { var y = Math.floor(p / 9), x = p % 9, by = y - y % 3, bx = x - x % 3;
      for (var k = 0; k < 9; k++) { if (g[y * 9 + k] === v || g[k * 9 + x] === v || g[(by + Math.floor(k / 3)) * 9 + bx + k % 3] === v) return false; } return true; }
    function count(g, lim) { var p = g.indexOf(0); if (p < 0) return 1; var n = 0;
      for (var v = 1; v <= 9 && n < lim; v++) if (ok(g, p, v)) { g[p] = v; n += count(g, lim - n); g[p] = 0; } return n; }
    var order = shuffle(Array.from({ length: 81 }, function (_, k) { return k; }), r), removed = 0;
    for (i = 0; i < 81 && removed < 50; i++) { var p = order[i], keep = puzzle[p]; puzzle[p] = 0; if (count(puzzle.slice(), 2) !== 1) puzzle[p] = keep; else removed++; }
    var grid = el('div', 'sd-grid'), sel = -1, cells = [];
    puzzle.forEach(function (v, k) {
      var c = el('button', 'sd-c' + (v ? ' given' : ''), v || ''); c.type = 'button';
      if (Math.floor(k / 9) % 3 === 2 && k < 72) c.classList.add('bb'); if (k % 9 % 3 === 2 && k % 9 < 8) c.classList.add('br');
      c.onclick = function () { if (v) return; if (sel >= 0) cells[sel].classList.remove('sel'); sel = k; c.classList.add('sel'); };
      cells.push(c); grid.appendChild(c);
    });
    body.appendChild(grid);
    var pad = el('div', 'sd-pad');
    [1, 2, 3, 4, 5, 6, 7, 8, 9, '⌫'].forEach(function (n) {
      var b = el('button', 'gm-key', n); b.type = 'button';
      b.onclick = function () { if (sel < 0) return say('Tap an empty square first.');
        cells[sel].textContent = n === '⌫' ? '' : n; cells[sel].classList.remove('bad'); check(false); };
      pad.appendChild(b);
    });
    body.appendChild(pad);
    function check(show) {
      var full = true, right = true;
      cells.forEach(function (c, k) { var v = +c.textContent || 0; if (!v) full = false; else if (v !== base[k]) { right = false; if (show) c.classList.add('bad'); } });
      if (full && right) won('Sudoku solved!'); else if (show) say(right ? 'So far so good — keep going.' : 'The red squares aren\'t right.');
    }
    bar([{ label: 'Check', fn: function () { check(true); } }, { label: 'Reveal a square', fn: function () {
      var empty = cells.map(function (c, k) { return (!c.classList.contains('given') && +c.textContent !== base[k]) ? k : -1; }).filter(function (k) { return k >= 0; });
      if (empty.length) { var k = empty[Math.floor(Math.random() * empty.length)]; cells[k].textContent = base[k]; cells[k].classList.remove('bad'); cells[k].classList.add('hint'); check(false); } } }]);
  }

  // ---------- Word Search ----------
  function wordsearch(r, words) {
    var N = 11, list = shuffle(paperWords(words, 4, N), r).slice(0, 10), g = [], placed = [];
    for (var i = 0; i < N * N; i++) g.push('');
    var dirs = [[0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1]];
    list.forEach(function (w) {
      for (var t = 0; t < 200; t++) {
        var d = dirs[Math.floor(r() * (t < 60 ? 4 : 8))], y = Math.floor(r() * N), x = Math.floor(r() * N), fit = true, k;
        for (k = 0; k < w.length; k++) { var yy = y + d[0] * k, xx = x + d[1] * k; if (yy < 0 || yy >= N || xx < 0 || xx >= N || (g[yy * N + xx] && g[yy * N + xx] !== w[k])) { fit = false; break; } }
        if (!fit) continue;
        var path = []; for (k = 0; k < w.length; k++) { var p = (y + d[0] * k) * N + x + d[1] * k; g[p] = w[k]; path.push(p); }
        placed.push({ w: w, path: path }); return;
      }
    });
    var A = 'ABCDEFGHIJKLMNOPRSTUWY';
    g = g.map(function (c) { return c || A[Math.floor(r() * A.length)]; });
    var grid = el('div', 'ws-grid'); grid.style.gridTemplateColumns = 'repeat(' + N + ', 1fr)';
    var cells = g.map(function (c, k) { var b = el('button', 'ws-c', c); b.type = 'button'; b.onclick = function () { tap(k); }; grid.appendChild(b); return b; });
    body.appendChild(grid);
    var ul = el('ul', 'ws-list'); placed.forEach(function (p) { p.li = el('li', '', p.w); ul.appendChild(p.li); }); body.appendChild(ul);
    var start = -1, found = 0;
    function tap(k) {
      if (start < 0) { start = k; cells[k].classList.add('pick'); return say('Now tap the last letter.'); }
      cells[start].classList.remove('pick');
      var hit = placed.filter(function (p) { return !p.done && ((p.path[0] === start && p.path[p.path.length - 1] === k) || (p.path[0] === k && p.path[p.path.length - 1] === start)); })[0];
      start = -1;
      if (!hit) return say('Not a word — try again.');
      hit.done = true; hit.li.classList.add('got'); hit.path.forEach(function (p) { cells[p].classList.add('got'); }); found++;
      say(hit.w + '! ' + found + ' of ' + placed.length);
      if (found === placed.length) won('Every word found!');
    }
    bar([{ label: 'Show one', fn: function () { var p = placed.filter(function (x) { return !x.done; })[0]; if (p) p.path.forEach(function (q) { cells[q].classList.add('hint'); }); } }]);
  }

  // ---------- Cryptogram ----------
  function cryptogram(r, words, quotes) {
    var pool = quotes.filter(function (q) { return q && q.length >= 25 && q.length <= 110; });
    var quote = (pool.length ? pool[Math.floor(r() * pool.length)] : SAYINGS[Math.floor(r() * SAYINGS.length)]).toUpperCase();
    var A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split(''), key;
    do { key = shuffle(A.slice(), r); } while (key.some(function (c, i) { return c === A[i]; }));
    var enc = {}, dec = {}; A.forEach(function (c, i) { enc[c] = key[i]; dec[key[i]] = c; });
    var guess = {}, cells = {}, sel = null, wrap = el('div', 'cg-quote');
    quote.split(' ').forEach(function (word) {
      var wd = el('span', 'cg-word');
      word.split('').forEach(function (ch) {
        if (/[A-Z]/.test(ch)) {
          var c = enc[ch], b = el('button', 'cg-c', '<b></b><small>' + c + '</small>'); b.type = 'button';
          b.onclick = function () { sel = c; paint(); };
          (cells[c] = cells[c] || []).push(b); wd.appendChild(b);
        } else wd.appendChild(el('span', 'cg-p', esc(ch)));
      });
      wrap.appendChild(wd);
    });
    body.appendChild(wrap);
    var letters = Object.keys(cells), hints = shuffle(letters.slice(), r).slice(0, 2);
    hints.forEach(function (c) { guess[c] = dec[c]; });
    var kb = el('div', 'gm-kb');
    A.concat(['⌫']).forEach(function (ch) { var b = el('button', 'gm-key', ch); b.type = 'button';
      b.onclick = function () { if (!sel) return say('Tap a letter in the quote first.'); if (ch === '⌫') delete guess[sel]; else {
        Object.keys(guess).forEach(function (k) { if (guess[k] === ch && k !== sel && hints.indexOf(k) < 0) delete guess[k]; }); guess[sel] = ch; }
        paint(); if (letters.every(function (c) { return guess[c] === dec[c]; })) won('Cracked it: “' + quote + '”'); };
      kb.appendChild(b); });
    body.appendChild(kb);
    function paint() { letters.forEach(function (c) { cells[c].forEach(function (b) { b.querySelector('b').textContent = guess[c] || ''; b.classList.toggle('sel', c === sel); b.classList.toggle('hint', hints.indexOf(c) >= 0); }); }); }
    paint();
    bar([{ label: 'Check', fn: function () { var bad = letters.filter(function (c) { return guess[c] && guess[c] !== dec[c]; });
      bad.forEach(function (c) { cells[c].forEach(function (b) { b.classList.add('bad'); setTimeout(function () { b.classList.remove('bad'); }, 1500); }); });
      say(bad.length ? bad.length + ' letter' + (bad.length > 1 ? 's are' : ' is') + ' wrong.' : 'Everything so far is right.'); } }]);
  }

  // ---------- Jumble ----------
  function jumble(r, words) {
    var list = shuffle(paperWords(words, 5, 8), r).slice(0, 5), done = 0;
    list.forEach(function (w) {
      var s; do { s = shuffle(w.split(''), r).join(''); } while (s === w && w.length > 1);
      var row = el('div', 'jb-row'), inp = el('input', 'jb-in');
      row.appendChild(el('div', 'jb-scr', s.split('').map(function (c) { return '<i>' + c + '</i>'; }).join('')));
      inp.maxLength = w.length; inp.autocapitalize = 'characters'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.setAttribute('aria-label', 'Unscramble ' + s);
      inp.oninput = function () { inp.value = inp.value.toUpperCase().replace(/[^A-Z]/g, '');
        if (inp.value === w && !row.classList.contains('got')) { row.classList.add('got'); inp.readOnly = true; done++; say(w + '! ' + done + ' of ' + list.length); if (done === list.length) won('All unscrambled!'); } };
      row.appendChild(inp); row.dataset.w = w; body.appendChild(row);
    });
    bar([{ label: 'First letters', fn: function () { Array.prototype.forEach.call(body.querySelectorAll('.jb-row:not(.got)'), function (row) {
      var inp = row.querySelector('input'); if (!inp.value) inp.placeholder = row.dataset.w[0] + '…'; }); } }]);
  }

  // ---------- Minesweeper ----------
  function mines(r) {
    var N = 9, M = 10, grid = el('div', 'ms-grid'), cells = [], mine = null, open = 0, over = false, flag = false;
    grid.style.gridTemplateColumns = 'repeat(' + N + ', 1fr)';
    function nb(k) { var y = Math.floor(k / N), x = k % N, out = [];
      for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) { if (!dy && !dx) continue; var yy = y + dy, xx = x + dx; if (yy >= 0 && yy < N && xx >= 0 && xx < N) out.push(yy * N + xx); } return out; }
    function lay(first) { mine = {}; var safe = nb(first).concat([first]), spots = shuffle(Array.from({ length: N * N }, function (_, k) { return k; }), r).filter(function (k) { return safe.indexOf(k) < 0; });
      spots.slice(0, M).forEach(function (k) { mine[k] = 1; }); }
    function reveal(k) {
      var c = cells[k]; if (c.classList.contains('open') || c.classList.contains('flag')) return;
      c.classList.add('open'); open++;
      var n = nb(k).filter(function (q) { return mine[q]; }).length;
      if (n) { c.textContent = n; c.classList.add('n' + n); } else nb(k).forEach(reveal);
    }
    for (var k = 0; k < N * N; k++) (function (k) {
      var c = el('button', 'ms-c'); c.type = 'button'; cells.push(c); grid.appendChild(c);
      c.onclick = function () {
        if (over) return;
        if (flag) { if (!c.classList.contains('open')) { c.classList.toggle('flag'); c.textContent = c.classList.contains('flag') ? '🚩' : ''; } return; }
        if (c.classList.contains('flag')) return;
        if (!mine) lay(k);
        if (mine[k]) { over = true; Object.keys(mine).forEach(function (q) { cells[q].textContent = '💣'; cells[q].classList.add('boom'); }); return say('💥 Boom! Close and reopen to try again.'); }
        reveal(k);
        if (open === N * N - M) { over = true; Object.keys(mine).forEach(function (q) { cells[q].textContent = '🚩'; }); won('Board cleared!'); }
      };
    })(k);
    body.appendChild(grid);
    bar([{ label: '⛏ Dig', cls: 'on', fn: function (b) { flag = !flag; b.innerHTML = flag ? '🚩 Flag' : '⛏ Dig'; b.classList.toggle('on', !flag); } }]);
  }

  // ---------- Nonogram ----------
  function nonogram(r) {
    var N = 8, sol = [], k;
    for (k = 0; k < N * N; k++) sol.push(r() < 0.56 ? 1 : 0);
    function runs(a) { var out = [], n = 0; a.forEach(function (v) { if (v) n++; else if (n) { out.push(n); n = 0; } }); if (n) out.push(n); return out.length ? out : [0]; }
    function row(g, y) { return g.slice(y * N, y * N + N); }
    function col(g, x) { var o = []; for (var y = 0; y < N; y++) o.push(g[y * N + x]); return o; }
    var rc = [], cc = [];
    for (k = 0; k < N; k++) { rc.push(runs(row(sol, k))); cc.push(runs(col(sol, k))); }
    var t = el('div', 'ng-grid'), user = sol.map(function () { return 0; }), cells = [], mode = 1;
    t.style.gridTemplateColumns = 'auto repeat(' + N + ', 1fr)';
    t.appendChild(el('div', 'ng-corner'));
    cc.forEach(function (c) { t.appendChild(el('div', 'ng-cc', c.join('<br>'))); });
    for (var y = 0; y < N; y++) {
      t.appendChild(el('div', 'ng-rc', rc[y].join(' ')));
      for (var x = 0; x < N; x++) (function (p) {
        var c = el('button', 'ng-c'); c.type = 'button'; if (p % N === 3) c.classList.add('br'); if (Math.floor(p / N) === 3) c.classList.add('bb');
        c.onclick = function () { user[p] = user[p] === mode ? 0 : mode; c.className = c.className.replace(/ ?(fill|mark)/g, '') + (user[p] === 1 ? ' fill' : user[p] === 2 ? ' mark' : ''); check(); };
        cells.push(c); t.appendChild(c);
      })(y * N + x);
    }
    body.appendChild(t);
    function check() { var g = user.map(function (v) { return v === 1 ? 1 : 0; });
      for (var i = 0; i < N; i++) if (runs(row(g, i)).join() !== rc[i].join() || runs(col(g, i)).join() !== cc[i].join()) return;
      won('Picture complete!'); }
    bar([{ label: '■ Fill', cls: 'on', fn: function (b) { mode = mode === 1 ? 2 : 1; b.innerHTML = mode === 1 ? '■ Fill' : '✕ Mark blank'; b.classList.toggle('on', mode === 1); } }]);
  }

  // ---------- Five Leaf (a five-letter word in six tries) ----------
  function fiveleaf(r) {
    var ans = LEAVES[Math.floor(r() * LEAVES.length)], rows = [], cur = '', tries = 0, over = false, keys = {};
    var board = el('div', 'fl-board');
    for (var i = 0; i < 6; i++) { var rw = el('div', 'fl-row'); for (var j = 0; j < 5; j++) rw.appendChild(el('span', 'fl-t')); rows.push(rw); board.appendChild(rw); }
    body.appendChild(board);
    var kb = el('div', 'gm-kb fl-kb');
    'QWERTYUIOP ASDFGHJKL ⏎ZXCVBNM⌫'.split('').forEach(function (ch) {
      if (ch === ' ') return kb.appendChild(el('span', 'gm-break'));
      var b = el('button', 'gm-key' + (ch === '⏎' || ch === '⌫' ? ' wide' : ''), ch === '⏎' ? 'ENTER' : ch); b.type = 'button'; keys[ch] = b;
      b.onclick = function () { press(ch); }; kb.appendChild(b);
    });
    body.appendChild(kb);
    layer.onkeydown = function (e) { if (!body.classList.contains('gm-fiveleaf')) return; var k = e.key.toUpperCase();
      if (k === 'ENTER') press('⏎'); else if (k === 'BACKSPACE') press('⌫'); else if (/^[A-Z]$/.test(k)) press(k); };
    function paint() { var t = rows[tries].children; for (var i = 0; i < 5; i++) t[i].textContent = cur[i] || ''; }
    function press(ch) {
      if (over) return;
      if (ch === '⌫') { cur = cur.slice(0, -1); return paint(); }
      if (ch === '⏎') {
        if (cur.length < 5) return say('Five letters, please.');
        var res = [0, 0, 0, 0, 0], left = {}, i;
        for (i = 0; i < 5; i++) { if (cur[i] === ans[i]) res[i] = 2; else left[ans[i]] = (left[ans[i]] || 0) + 1; }
        for (i = 0; i < 5; i++) if (!res[i] && left[cur[i]]) { res[i] = 1; left[cur[i]]--; }
        var t = rows[tries].children;
        res.forEach(function (v, i) { t[i].classList.add(['no', 'near', 'yes'][v]); var k = keys[cur[i]];
          if (k && !k.classList.contains('yes')) { k.classList.remove('near', 'no'); k.classList.add(['no', 'near', 'yes'][v]); } });
        tries++;
        if (cur === ans) { over = true; return won('Got it in ' + tries + '!'); }
        cur = '';
        if (tries === 6) { over = true; return say('The word was ' + ans + '. New leaf tomorrow!'); }
        return say((6 - tries) + ' tries left.');
      }
      if (cur.length < 5) { cur += ch; paint(); }
    }
  }

  // ---------- wiring ----------
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.pz-play'); if (!b) return;
    ev.preventDefault(); ev.stopPropagation(); open(b);
  }, true);
  paintSolved();
  if (window.jQuery) jQuery('#flipbook').bind('turned', function () { setTimeout(paintSolved, 60); });
})();

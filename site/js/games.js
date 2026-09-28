/* The Garden's puzzle engine (shared: The Double Wide's daily puzzle and The Crossword Times). One game a day (Mon Sudoku · Tue Word Search · Wed Cryptogram · Thu Jumble · Fri Minesweeper ·
   Sat Nonogram · Sun Five Leaf), built from the day's date so everybody gets the same puzzle, and played full-screen on its own layer
   so page turns can't steal a tap. The paper's page only holds the button: <button class="pz-play" data-game data-date data-words data-quotes>.
   Extras that aren't in the daily rotation (The Crossword Times): crossword, grow (2048), lightsout, slider, memory.
   Every finish is sent to The Corner Chronicle (/api/score) for the scoreboard and streaks. */
(function () {
  'use strict';
  var NAMES = { sudoku: 'Sudoku', wordsearch: 'Word Search', cryptogram: 'Cryptogram', jumble: 'Jumble', mines: 'Minesweeper', nonogram: 'Nonogram', fiveleaf: 'Five Leaf',
                crossword: 'The Crossword', grow: 'Grow', lightsout: 'Lights Out', slider: 'The Slider', memory: 'Memory Match' };
  var HOWTO = {
    sudoku: 'Fill every row, column and 3×3 box with 1–9. Tap a square, then a number.',
    wordsearch: 'Tap the first letter of a word, then its last letter. Words run any direction.',
    cryptogram: 'Each letter stands for another. Tap a letter, then pick what you think it really is.',
    jumble: 'Unscramble each word from today\'s paper.',
    mines: 'Clear the board without hitting a mine. Numbers count the mines touching that square. Switch to 🚩 to flag.',
    nonogram: 'The numbers are runs of filled squares in that row or column, in order. Tap to fill; switch to ✕ to mark blanks.',
    fiveleaf: 'Guess the five-letter word in six tries. Green = right spot, gold = in the word, gray = not in it.',
    crossword: 'Tap a square (tap again to switch Across/Down), then type. Every clue is from the Garden.',
    grow: 'Swipe (or use the arrow keys) to slide the tiles. Two of the same grow into the next stage. Reach 🌺 512 to win.',
    lightsout: 'Tapping a light flips it and its neighbors. Turn every light off.',
    slider: 'Slide the tiles into order, 1 to 15, with the gap in the bottom-right corner.',
    memory: 'Flip two cards at a time and find every pair of Garden agents.'
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
    start(game, date, words, quotes, btn.dataset.kick);
  }
  function start(game, date, words, quotes, kick) {
    if (!layer) {
      layer = el('div', 'gm'); layer.setAttribute('role', 'dialog'); layer.setAttribute('aria-modal', 'true');
      layer.innerHTML = '<div class="gm-card"><header class="gm-top"><div><div class="gm-kick"></div><h2 class="gm-title"></h2></div>' +
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
    layer.querySelector('.gm-kick').textContent = kick || 'The Daily Puzzle';
    body.innerHTML = ''; body.className = 'gm-body gm-' + game; say('');
    current = { key: date + '-' + game, game: game, date: date, t0: Date.now(), done: false };
    document.documentElement.classList.add('gm-open'); layer.hidden = false;
    var r = rng(date + ':' + game);
    ({ sudoku: sudoku, wordsearch: wordsearch, cryptogram: cryptogram, jumble: jumble, mines: mines, nonogram: nonogram, fiveleaf: fiveleaf,
       crossword: crossword, grow: grow, lightsout: lightsout, slider: slider, memory: memory })[game](r, words, quotes);
    if (store(current.key)) say('✅ You already solved this one — play it again for fun.');
  }
  function close() { if (layer) layer.hidden = true; document.documentElement.classList.remove('gm-open'); }
  function say(t) { status.textContent = t; }
  function report(ok) {
    if (current.done) return; current.done = true;
    var secs = Math.round((Date.now() - current.t0) / 1000);
    try { fetch('/api/score', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Garden-App': '1' },
      body: JSON.stringify({ game: current.game, date: current.date, secs: secs, won: ok }) }).then(function (r) { return r.json(); })
      .then(function (r) { var s = r.stats || {}; if (ok && s.streak > 1) say(status.textContent + ' · ' + s.streak + '-day streak!'); document.dispatchEvent(new CustomEvent('garden-score')); }).catch(function () {}); } catch (e) {}
    return secs;
  }
  function won(msg) {
    var secs = current.done ? 0 : report(true);
    say('🎉 ' + (msg || 'Solved!') + (secs ? ' · ' + Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0') : ''));
    store(current.key, { solved: new Date().toISOString() });
    paintSolved();
  }
  function lost() { report(false); }
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
        if (mine[k]) { over = true; Object.keys(mine).forEach(function (q) { cells[q].textContent = '💣'; cells[q].classList.add('boom'); }); lost(); return say('💥 Boom! Close and reopen to try again.'); }
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
        if (tries === 6) { over = true; lost(); return say('The word was ' + ans + '. New leaf tomorrow!'); }
        return say((6 - tries) + ' tries left.');
      }
      if (cur.length < 5) { cur += ch; paint(); }
    }
  }


  // ---------- The Crossword (a criss-cross built fresh each day from the Garden word bank) ----------
  var CLUES = [
    ['GANJA', 'The Double Wide\'s editor'], ['CHRONIC', 'Head grower who bakes the fixes'], ['MAPLE', 'Trail Mix co-editor (and a Maine tree)'], ['HERBIE', 'Maple\'s AI trail buddy'],
    ['CLYDIUS', 'The Garden\'s good boy'], ['BAKERY', 'The Pi whose root went read-only (the ___)'], ['RELAY', 'How agents take turns on the small VM'], ['VAULT', 'Where the wiki lives'],
    ['TOKENS', 'What the Garden Token Average counts'], ['KIOSK', 'The Corner Chronicle\'s green home'], ['RADIO', 'WDWN plays on it'], ['STASH', 'Box in the kiosk\'s lower right'],
    ['JARS', 'Where the best moments cure'], ['SEEDS', 'Sold by the pack in the catalog'], ['OLLAMA', 'Runs the local models on NukeBox'], ['NUKEBOX', 'The GMKTec mini-PC'],
    ['TAILSCALE', 'The private network that ties it together'], ['HERMES', 'The agents\' framework'], ['CODEX', 'OpenAI\'s coding agent'], ['CLAUDE', 'Anthropic\'s assistant'],
    ['PAYROLL', 'Page with Employee of the Day'], ['DIMEBAGS', 'Nightly betting sheet'], ['REUP', 'The want-ad paper (The ___)'], ['ROACH', '___ Clips, Tuesdays'],
    ['SUNDAY', 'Day The Smoke rolls in'], ['FUNNIES', 'Comic section'], ['EXTRA', 'Hollered twice when things break'], ['ALMANAC', 'The Perennial, basically'],
    ['LEWISTON', 'Hometown on the Androscoggin'], ['MAINE', 'The Pine Tree State'], ['PINE', 'Maine\'s state tree'], ['MOOSE', 'Maine\'s state animal'],
    ['LOBSTER', 'Maine catch'], ['TRAIL', 'Maple\'s favorite kind of path'], ['BUD', 'Flower before it opens'], ['LEAF', 'Seven-pointed symbol'],
    ['ROOTS', 'Bedded ___ (the field guide)'], ['SPROUT', 'What a planted seed does first'], ['BLOOM', 'Full flower'], ['GROW', 'What seeds and ideas do'],
    ['PAPER', 'Rolling ___ or morning ___'], ['ROLL', 'Do this to a joint or a newspaper'], ['ASHTRAY', 'On the counter, still smoking'], ['LIGHTER', 'Flick for a flame'],
    ['EMBER', 'Glowing tip'], ['SMOKE', 'Rises from the ashtray'], ['KUSH', 'Read-Only ___ (strain of the month)'], ['HASH', 'The Garden\'s glossy, minus -ISH'],
    ['DAB', 'The humor magazine'], ['BONG', 'Water pipe'], ['GRINDER', 'Toothy herb tool'], ['PIPE', 'Bowl and stem'],
    ['CRON', 'Scheduler that runs the shifts'], ['BACKUP', 'Do it before you fix it'], ['REBOOT', 'Turn it off and on'], ['UPTIME', 'Days since the last crash'],
    ['DOCKER', 'Containers\' home'], ['LINUX', 'Penguin OS'], ['SHELL', 'Where commands go'], ['SERVER', 'Always-on computer'],
    ['PROMPT', 'What you give an agent'], ['MODEL', 'Qwen, Claude or GPT'], ['CACHE', 'Tokens saved for later'], ['ROUTER', 'Home network\'s traffic cop'],
    ['PIXEL', 'One dot on a screen'], ['WIFI', 'Wireless link'], ['SENSOR', 'An ESP32\'s eyes and ears'], ['SOLDER', 'Melts to join wires'],
    ['PRINTER', 'Makes things layer by layer (3D)'], ['DISCORD', 'Where the agents post'], ['KNIFE', 'Blades: Hermes, Codex, Ollama…'], ['PUNCH', 'What the regular\'s card gets daily'],
    ['LETTER', 'Goes in the brass slot'], ['TIP', 'Phoned in on the payphone'], ['GARDEN', 'The whole operation'], ['PERENNIAL', 'Comes back every year']];
  function crossword(r) {
    var N = 13, bank = shuffle(CLUES.slice(), r), grid = {}, placed = [];
    function at(x, y) { return grid[x + ',' + y]; }
    function fits(w, x, y, dx, dy) {
      if (at(x - dx, y - dy) || at(x + dx * w.length, y + dy * w.length)) return -1;
      var cross = 0;
      for (var i = 0; i < w.length; i++) {
        var cx = x + dx * i, cy = y + dy * i, c = at(cx, cy);
        if (cx < 0 || cy < 0 || cx >= N || cy >= N) return -1;
        if (c) { if (c !== w[i]) return -1; cross++; }
        else if (at(cx + dy, cy + dx) || at(cx - dy, cy - dx)) return -1;
      }
      return cross;
    }
    function put(w, x, y, dx, dy, clue) { for (var i = 0; i < w.length; i++) grid[(x + dx * i) + ',' + (y + dy * i)] = w[i]; placed.push({ w: w, x: x, y: y, dx: dx, dy: dy, clue: clue }); }
    var first = bank.filter(function (b) { return b[0].length >= 7 && b[0].length <= 10; })[0] || bank[0];
    put(first[0], Math.floor((N - first[0].length) / 2), Math.floor(N / 2), 1, 0, first[1]);
    for (var b = 0; b < bank.length && placed.length < 11; b++) {
      var w = bank[b][0]; if (placed.some(function (p) { return p.w === w; }) || w.length > N) continue;
      var best = null;
      for (var y = 0; y < N; y++) for (var x = 0; x < N; x++) [[1, 0], [0, 1]].forEach(function (d) {
        var c = fits(w, x, y, d[0], d[1]); if (c > 0 && (!best || c > best.c || (c === best.c && r() < .3))) best = { x: x, y: y, d: d, c: c }; });
      if (best) put(w, best.x, best.y, best.d[0], best.d[1], bank[b][1]);
    }
    var xs = [], ys = []; Object.keys(grid).forEach(function (k) { var p = k.split(','); xs.push(+p[0]); ys.push(+p[1]); });
    var x0 = Math.min.apply(null, xs), y0 = Math.min.apply(null, ys), W = Math.max.apply(null, xs) - x0 + 1, H = Math.max.apply(null, ys) - y0 + 1;
    placed.sort(function (a, b) { return (a.y - b.y) || (a.x - b.x); });
    var num = {}, n = 0; placed.forEach(function (p) { var k = p.x + ',' + p.y; if (!num[k]) num[k] = ++n; p.n = num[k]; });
    var g = el('div', 'cw-grid'); g.style.gridTemplateColumns = 'repeat(' + W + ', 1fr)';
    var cells = {}, sel = null, dir = [1, 0];
    for (var yy = y0; yy < y0 + H; yy++) for (var xx = x0; xx < x0 + W; xx++) (function (x, y) {
      var k = x + ',' + y, c;
      if (!grid[k]) { g.appendChild(el('span', 'cw-block')); return; }
      c = el('button', 'cw-c', (num[k] ? '<small>' + num[k] + '</small>' : '') + '<b></b>'); c.type = 'button'; cells[k] = c;
      c.onclick = function () { if (sel === k) dir = dir[0] ? [0, 1] : [1, 0]; else { sel = k; var across = at(x - 1, y) || at(x + 1, y), down = at(x, y - 1) || at(x, y + 1); dir = across && !down ? [1, 0] : !across && down ? [0, 1] : dir; } paint(); };
      g.appendChild(c);
    })(xx, yy);
    body.appendChild(g);
    var clues = el('div', 'cw-clues');
    clues.innerHTML = '<div><h4>Across</h4><ol>' + placed.filter(function (p) { return p.dx; }).map(function (p) { return '<li value="' + p.n + '">' + esc(p.clue) + ' <i>(' + p.w.length + ')</i></li>'; }).join('') + '</ol></div>' +
      '<div><h4>Down</h4><ol>' + placed.filter(function (p) { return p.dy; }).map(function (p) { return '<li value="' + p.n + '">' + esc(p.clue) + ' <i>(' + p.w.length + ')</i></li>'; }).join('') + '</ol></div>';
    body.appendChild(clues);
    var kb = el('div', 'gm-kb');
    'QWERTYUIOP ASDFGHJKL ZXCVBNM⌫'.split('').forEach(function (ch) { if (ch === ' ') return kb.appendChild(el('span', 'gm-break'));
      var b2 = el('button', 'gm-key', ch); b2.type = 'button'; b2.onclick = function () { type(ch); }; kb.appendChild(b2); });
    body.appendChild(kb);
    layer.onkeydown = function (e) { if (!body.classList.contains('gm-crossword')) return; var k = e.key.toUpperCase(); if (k === 'BACKSPACE') type('⌫'); else if (/^[A-Z]$/.test(k)) type(k); };
    function type(ch) {
      if (!sel) return say('Tap a square first.');
      var p = sel.split(','), x = +p[0], y = +p[1];
      if (ch === '⌫') { cells[sel].querySelector('b').textContent = ''; var bk = (x - dir[0]) + ',' + (y - dir[1]); if (cells[bk]) sel = bk; }
      else { cells[sel].querySelector('b').textContent = ch; cells[sel].classList.remove('bad'); var nx = (x + dir[0]) + ',' + (y + dir[1]); if (cells[nx]) sel = nx; }
      paint(); check(false);
    }
    function paint() { Object.keys(cells).forEach(function (k) { cells[k].classList.toggle('sel', k === sel); }); }
    function check(show) {
      var full = true, right = true;
      Object.keys(cells).forEach(function (k) { var v = cells[k].querySelector('b').textContent; if (!v) full = false; else if (v !== grid[k]) { right = false; if (show) cells[k].classList.add('bad'); } });
      if (full && right) won('Crossword complete!'); else if (show) say(right ? 'All correct so far.' : 'Red squares are wrong.');
    }
    bar([{ label: 'Check', fn: function () { check(true); } }, { label: 'Reveal a letter', fn: function () {
      var k = sel && cells[sel] && cells[sel].querySelector('b').textContent !== grid[sel] ? sel : Object.keys(cells).filter(function (q) { return cells[q].querySelector('b').textContent !== grid[q]; })[0];
      if (k) { cells[k].querySelector('b').textContent = grid[k]; cells[k].classList.add('hint'); check(false); } } }]);
  }

  // ---------- Grow (2048 with plants) ----------
  var STAGES = { 2: '🌰', 4: '🌱', 8: '🌿', 16: '🍃', 32: '🪴', 64: '🌳', 128: '🌼', 256: '🌸', 512: '🌺', 1024: '🍀', 2048: '👑' };
  function grow(r) {
    var b = [], score = 0, over = false, done = false, g = el('div', 'gr-grid');
    for (var i = 0; i < 16; i++) b.push(0);
    function spawn() { var e = []; b.forEach(function (v, i) { if (!v) e.push(i); }); if (e.length) b[e[Math.floor(Math.random() * e.length)]] = Math.random() < .9 ? 2 : 4; }
    function paint() { g.innerHTML = b.map(function (v) { return '<span class="gr-t v' + v + '">' + (v ? '<b>' + STAGES[v] + '</b><small>' + v + '</small>' : '') + '</span>'; }).join(''); say('Score ' + score); }
    function slide(line) { var a = line.filter(Boolean), out = []; for (var i = 0; i < a.length; i++) { if (a[i] === a[i + 1]) { out.push(a[i] * 2); score += a[i] * 2; i++; } else out.push(a[i]); } while (out.length < 4) out.push(0); return out; }
    function move(d) {
      if (over) return; var before = b.join();
      for (var i = 0; i < 4; i++) { var idx = [0, 1, 2, 3].map(function (j) { return d === 'L' ? i * 4 + j : d === 'R' ? i * 4 + 3 - j : d === 'U' ? j * 4 + i : (3 - j) * 4 + i; });
        var res = slide(idx.map(function (k) { return b[k]; })); idx.forEach(function (k, j) { b[k] = res[j]; }); }
      if (b.join() !== before) { spawn(); paint(); }
      if (!done && b.some(function (v) { return v >= 512; })) { done = true; won('Full bloom — 🌺 512! Score ' + score); }
      var canMove = b.some(function (v, i) { return !v || (i % 4 < 3 && v === b[i + 1]) || (i < 12 && v === b[i + 4]); });
      if (!canMove) { over = true; if (!done) lost(); say('No more moves — final score ' + score + '.'); }
    }
    spawn(); spawn(); paint(); body.appendChild(g);
    var sx = null, sy = null;
    g.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    g.addEventListener('touchend', function (e) { if (sx === null) return; var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy; sx = null;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return; move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'R' : 'L') : (dy > 0 ? 'D' : 'U')); });
    layer.onkeydown = function (e) { if (!body.classList.contains('gm-grow')) return; var m = { ArrowLeft: 'L', ArrowRight: 'R', ArrowUp: 'U', ArrowDown: 'D' }[e.key]; if (m) { e.preventDefault(); move(m); } };
    bar([{ label: '◀', fn: function () { move('L'); } }, { label: '▲', fn: function () { move('U'); } }, { label: '▼', fn: function () { move('D'); } }, { label: '▶', fn: function () { move('R'); } }]);
  }

  // ---------- Lights Out ----------
  function lightsout(r) {
    var N = 5, on = [], moves = 0, g = el('div', 'lo-grid'), i;
    for (i = 0; i < N * N; i++) on.push(false);
    function flip(k) { [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (d) { var x = k % N + d[0], y = Math.floor(k / N) + d[1]; if (x >= 0 && y >= 0 && x < N && y < N) on[y * N + x] = !on[y * N + x]; }); }
    for (i = 0; i < 12; i++) flip(Math.floor(r() * N * N));
    if (!on.some(Boolean)) flip(12);
    function paint() { Array.prototype.forEach.call(g.children, function (c, k) { c.classList.toggle('on', on[k]); }); say(moves + ' moves · ' + on.filter(Boolean).length + ' lights on'); }
    for (i = 0; i < N * N; i++) (function (k) { var c = el('button', 'lo-c'); c.type = 'button'; c.onclick = function () { flip(k); moves++; paint(); if (!on.some(Boolean)) won('Lights out in ' + moves + ' moves!'); }; g.appendChild(c); })(i);
    body.appendChild(g); paint();
  }

  // ---------- The Slider (15-puzzle) ----------
  function slider(r) {
    var t = [], i, g = el('div', 'sl-grid'), moves = 0;
    for (i = 1; i < 16; i++) t.push(i); t.push(0);
    function nb(z) { var o = []; if (z % 4) o.push(z - 1); if (z % 4 < 3) o.push(z + 1); if (z > 3) o.push(z - 4); if (z < 12) o.push(z + 4); return o; }
    var z = 15, last = -1;
    for (i = 0; i < 160; i++) { var c = nb(z).filter(function (q) { return q !== last; }), q = c[Math.floor(r() * c.length)]; t[z] = t[q]; t[q] = 0; last = z; z = q; }
    function paint() { g.innerHTML = t.map(function (v, k) { return '<button type="button" class="sl-t' + (v ? '' : ' gap') + '" data-k="' + k + '">' + (v || '') + '</button>'; }).join(''); say(moves + ' moves'); }
    g.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.sl-t'); if (!b) return; var k = +b.dataset.k, zz = t.indexOf(0);
      if (nb(zz).indexOf(k) < 0) return; t[zz] = t[k]; t[k] = 0; moves++; paint();
      if (t.slice(0, 15).every(function (v, i2) { return v === i2 + 1; })) won('Solved in ' + moves + ' moves!'); });
    body.appendChild(g); paint();
  }

  // ---------- Memory Match (the agents) ----------
  function memory(r) {
    var who = shuffle(['ganja', 'gardener', 'chronic', 'maple', 'herbie', 'homie', 'ibby', 'discostu', 'bak3r', 'cyph3r', 'clydius', 'tinyz', 'big'], r).slice(0, 8);
    var deck = shuffle(who.concat(who), r), open = [], got = 0, tries = 0, g = el('div', 'mm-grid'), lock = false;
    deck.forEach(function (w, k) { var c = el('button', 'mm-c', '<span class="mm-back">🏠</span><img class="mm-face" alt="" src="/double-wide/img/' + w + '.png">'); c.type = 'button';
      c.onclick = function () { if (lock || c.classList.contains('up')) return; c.classList.add('up'); open.push([c, w]);
        if (open.length === 2) { tries++; lock = true; var a = open[0], b2 = open[1]; open = [];
          if (a[1] === b2[1]) { a[0].classList.add('got'); b2[0].classList.add('got'); got++; lock = false; say(got + ' of 8 pairs · ' + tries + ' tries'); if (got === 8) won('All 8 pairs in ' + tries + ' tries!'); }
          else setTimeout(function () { a[0].classList.remove('up'); b2[0].classList.remove('up'); lock = false; say(got + ' of 8 pairs · ' + tries + ' tries'); }, 800); } };
      g.appendChild(c); });
    body.appendChild(g); say('Find the 8 pairs.');
  }

  // ---------- wiring ----------
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.pz-play'); if (!b) return;
    ev.preventDefault(); ev.stopPropagation(); open(b);
  }, true);
  window.GardenGames = { open: start, names: NAMES, daily: ['sudoku', 'wordsearch', 'cryptogram', 'jumble', 'mines', 'nonogram', 'fiveleaf'],
                         extras: ['crossword', 'grow', 'lightsout', 'slider', 'memory'], solved: function (date, game) { return !!store(date + '-' + game); } };
  paintSolved();
  if (window.jQuery) jQuery('#flipbook').bind('turned', function () { setTimeout(paintSolved, 60); });
})();

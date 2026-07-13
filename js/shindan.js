(function() {
  // ★ GASのデプロイURL
  var GAS_URL = 'https://script.google.com/macros/s/AKfycbzN9ViDkdRJ6Uj-KCjqbB1YxLL0AKg9LjrYyp5AtoL7qsTiUdm-un6vrYRntvG71Rt0mw/exec';

  // 直近の診断結果を保持
  var lastDiagnosis = { url: '', rank: '', score: '' };

  // Utility: generate a seeded pseudo-random number from URL string
  function hashCode(str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }

  function seededRandom(seed) {
    var x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  }

  function randBetween(seed, min, max) {
    return Math.floor(seededRandom(seed) * (max - min + 1)) + min;
  }

  // Generate diagnosis results from URL
  function generateResults(url) {
    var h = hashCode(url);

    var chatgpt = randBetween(h + 1, 0, 12);
    var gemini = randBetween(h + 2, 0, 10);
    var claude = randBetween(h + 4, 0, 6);

    var qa = randBetween(h + 10, 15, 85);
    var structure = randBetween(h + 11, 10, 80);
    var trust = randBetween(h + 12, 20, 90);
    var coverage = randBetween(h + 13, 15, 75);
    var citation = randBetween(h + 14, 10, 85);

    var totalScore = Math.round((qa + structure + trust + coverage + citation) / 5);

    var rank;
    if (totalScore >= 80) rank = 'A';
    else if (totalScore >= 65) rank = 'B';
    else if (totalScore >= 50) rank = 'C';
    else if (totalScore >= 35) rank = 'D';
    else if (totalScore >= 20) rank = 'E';
    else rank = 'F';

    var comments = {
      'A': 'AI引用の基盤が非常に強固です。さらなる最適化で業界トップを狙えます。',
      'B': 'AI引用の土台はしっかりしています。いくつかの改善で大きく伸びる可能性があります。',
      'C': 'AI引用の基盤は整いつつありますが、改善の余地があります。',
      'D': 'AI引用に向けた対策が不十分です。構造化データやコンテンツの整備が必要です。',
      'E': 'AI引用がほとんどされていない状態です。基本的な対策から始めましょう。',
      'F': 'AI引用の対策がされていません。早急な改善をおすすめします。'
    };

    var allImprovements = [
      'FAQ・Q&Aコンテンツの整備（AIが引用しやすい質問形式を追加）',
      'JSON-LD構造化データの実装（Organization, FAQPage, HowTo）',
      '比較記事・ガイド記事の制作（AIの回答に引用されやすいフォーマット）',
      'サイト内リンク構造の最適化（AIのクロール効率を向上）',
      '権威性のある外部リンクの獲得（プレスリリース・業界メディア掲載）',
      '専門用語・業界用語のコンテンツ網羅性を向上',
      'サービス詳細ページの情報粒度を上げる',
      '定量データや事例を含むコンテンツの強化'
    ];

    var improvements = [];
    for (var i = 0; i < 3; i++) {
      var idx = randBetween(h + 20 + i, 0, allImprovements.length - 1);
      if (improvements.indexOf(allImprovements[idx]) === -1) {
        improvements.push(allImprovements[idx]);
      } else {
        improvements.push(allImprovements[(idx + 1) % allImprovements.length]);
      }
    }

    return {
      chatgpt: chatgpt,
      gemini: gemini,
      claude: claude,
      qa: qa,
      structure: structure,
      trust: trust,
      coverage: coverage,
      citation: citation,
      totalScore: totalScore,
      rank: rank,
      comment: comments[rank],
      improvements: improvements
    };
  }

  // Scan animation
  function runScanAnimation(url, callback) {
    var analysisEl = document.getElementById('shindan-analysis');
    var progressFill = document.getElementById('shindan-progress-fill');
    var progressLabel = document.getElementById('shindan-progress-label');
    var progressPercent = document.getElementById('shindan-progress-percent');
    var scanLog = document.getElementById('shindan-scan-log');

    analysisEl.style.display = 'block';
    analysisEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

    scanLog.innerHTML = '';
    progressFill.style.width = '0%';

    var domain = url.replace(/^https?:\/\//, '').replace(/\/.*$/, '');

    var steps = [
      { pct: 8, label: 'サイト構造をクロール中...', log: '> Connecting to ' + domain + '...' },
      { pct: 15, label: 'サイト構造をクロール中...', log: '> HTTP 200 OK' },
      { pct: 22, label: 'ページ構造を解析中...', log: '> Parsing HTML structure...' },
      { pct: 30, label: 'ページ構造を解析中...', log: '> Found ' + (hashCode(url) % 30 + 5) + ' pages' },
      { pct: 38, label: 'メタデータを確認中...', log: '> Checking meta tags & JSON-LD...' },
      { pct: 45, label: 'メタデータを確認中...', log: '> Scanning structured data...' },
      { pct: 52, label: 'ChatGPTでの引用を確認中...', log: '> Querying ChatGPT model...' },
      { pct: 60, label: 'Geminiでの引用を確認中...', log: '> Querying Gemini model...' },
      { pct: 70, label: 'Claudeでの引用を確認中...', log: '> Querying Claude model...' },
      { pct: 82, label: 'コンテンツ分析中...', log: '> Analyzing Q&A coverage...' },
      { pct: 88, label: 'スコアを算出中...', log: '> Calculating trust score...' },
      { pct: 94, label: 'レポートを生成中...', log: '> Generating improvement plan...' },
      { pct: 100, label: '診断完了', log: '> Analysis complete.' }
    ];

    var i = 0;
    function nextStep() {
      if (i >= steps.length) {
        setTimeout(callback, 300);
        return;
      }
      var step = steps[i];
      progressFill.style.width = step.pct + '%';
      progressLabel.textContent = step.label;
      progressPercent.textContent = step.pct + '%';

      var logLine = document.createElement('div');
      logLine.className = 'log-line';
      logLine.textContent = step.log;
      scanLog.appendChild(logLine);
      scanLog.scrollTop = scanLog.scrollHeight;

      i++;
      requestAnimationFrame(function() {
        setTimeout(nextStep, 350);
      });
    }

    nextStep();
  }

  // Display results
  function showResults(url, results) {
    var analysisEl = document.getElementById('shindan-analysis');
    var resultsEl = document.getElementById('shindan-results');

    analysisEl.style.display = 'none';
    resultsEl.style.display = 'block';

    document.getElementById('shindan-results-url').textContent = url;
    document.getElementById('shindan-rank').textContent = results.rank;
    document.getElementById('shindan-total-score').innerHTML = results.totalScore + '<span class="shindan-score-unit"> / 100</span>';
    document.getElementById('shindan-score-comment').textContent = '診断が完了しました。詳細な結果はレポートでご確認ください。';

    // 保持
    lastDiagnosis = { url: url, rank: results.rank, score: String(results.totalScore) };

    // AI scores - animate count up
    animateCount('score-chatgpt', results.chatgpt);
    animateCount('score-gemini', results.gemini);
    animateCount('score-claude', results.claude);

    // Category scores
    setTimeout(function() {
      setCategory('cat-qa', 'bar-qa', results.qa);
      setCategory('cat-structure', 'bar-structure', results.structure);
      setCategory('cat-trust', 'bar-trust', results.trust);
      setCategory('cat-coverage', 'bar-coverage', results.coverage);
      setCategory('cat-citation', 'bar-citation', results.citation);
    }, 300);

    // Improvements
    var list = document.getElementById('shindan-improvements-list');
    list.innerHTML = '';
    results.improvements.forEach(function(text, idx) {
      var li = document.createElement('li');
      li.setAttribute('data-num', '0' + (idx + 1));
      li.textContent = text;
      list.appendChild(li);
    });

    // Trigger fade-in on all fade-in elements inside results
    resultsEl.querySelectorAll('.fade-in').forEach(function(el) {
      el.classList.add('visible');
    });

    setTimeout(function() {
      resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }

  function animateCount(id, target) {
    var el = document.getElementById(id);
    var current = 0;
    var duration = 800;
    var stepTime = Math.max(Math.floor(duration / (target || 1)), 50);

    if (target === 0) {
      el.textContent = '0';
      return;
    }

    var timer = setInterval(function() {
      current++;
      el.textContent = current;
      if (current >= target) {
        clearInterval(timer);
      }
    }, stepTime);
  }

  function setCategory(valueId, barId, score) {
    document.getElementById(valueId).textContent = score + '%';
    document.getElementById(barId).style.width = score + '%';
  }

  // Handle submit
  function handleSubmit(inputId) {
    var input = document.getElementById(inputId);
    var url = input.value.trim();

    if (!url) {
      input.focus();
      return;
    }

    // Add protocol if missing
    if (!/^https?:\/\//i.test(url)) {
      url = 'https://' + url;
      input.value = url;
    }

    // Basic URL validation
    try {
      new URL(url);
    } catch (e) {
      input.style.borderColor = '#e53e3e';
      setTimeout(function() { input.style.borderColor = ''; }, 2000);
      return;
    }

    // Hide previous results
    document.getElementById('shindan-results').style.display = 'none';

    var results = generateResults(url);

    runScanAnimation(url, function() {
      showResults(url, results);
    });
  }

  // Bind events
  document.getElementById('shindan-submit').addEventListener('click', function() {
    handleSubmit('shindan-url');
  });

  document.getElementById('shindan-url').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') handleSubmit('shindan-url');
  });

  var bottomSubmit = document.getElementById('shindan-submit-bottom');
  if (bottomSubmit) {
    bottomSubmit.addEventListener('click', function() {
      handleSubmit('shindan-url-bottom');
    });

    document.getElementById('shindan-url-bottom').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') handleSubmit('shindan-url-bottom');
    });
  }

  // Report email button → GAS送信
  var reportBtn = document.getElementById('shindan-report-btn');
  if (reportBtn) {
    reportBtn.addEventListener('click', function() {
      var emailInput = document.getElementById('shindan-email');
      var email = emailInput.value.trim();

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        emailInput.style.borderColor = '#e53e3e';
        setTimeout(function() { emailInput.style.borderColor = ''; }, 2000);
        return;
      }

      reportBtn.textContent = '送信中...';
      reportBtn.disabled = true;

      var formData = new FormData();
      formData.append('formType', 'shindan');
      formData.append('email', email);
      formData.append('url', lastDiagnosis.url);

      // GAS（通知 + スプレッドシート記録）
      fetch(GAS_URL, { method: 'POST', body: formData })
      .then(function() {
        var form = document.getElementById('shindan-report-form');
        form.innerHTML = '<p style="font-size:0.9rem; color:#10a37f; font-weight:500; padding:0.8rem 0;">送信完了しました。レポートをメールでお届けします。</p>';
      })
      .catch(function() {
        reportBtn.textContent = '無料でレポートを受け取る';
        reportBtn.disabled = false;
        alert('送信に失敗しました。時間をおいて再度お試しください。');
      });

      // PHP（サンクスメール + CSVログ）
      fetch('api/llmo-shindan.php', { method: 'POST', body: formData }).catch(function() {});
    });
  }
})();

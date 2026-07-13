(function() {
  'use strict';

  var SCORE_API = 'api/llmo-score.php';
  var GAS_URL = 'https://script.google.com/macros/s/AKfycbzN9ViDkdRJ6Uj-KCjqbB1YxLL0AKg9LjrYyp5AtoL7qsTiUdm-un6vrYRntvG71Rt0mw/exec';
  var lastDiagnosis = { url: '', score: '', diagnosisToken: '' };

  function addLog(message) {
    var scanLog = document.getElementById('shindan-scan-log');
    var line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = message;
    scanLog.appendChild(line);
    scanLog.scrollTop = scanLog.scrollHeight;
  }

  function setProgress(percent, label) {
    document.getElementById('shindan-progress-fill').style.width = percent + '%';
    document.getElementById('shindan-progress-percent').textContent = percent + '%';
    document.getElementById('shindan-progress-label').textContent = label;
  }

  function startProgress(url) {
    var analysis = document.getElementById('shindan-analysis');
    var error = document.getElementById('shindan-analysis-error');
    var domain = new URL(url).hostname;
    var stages = [
      { percent: 12, label: 'サイトへ接続しています...', log: domain + ' へ接続' },
      { percent: 28, label: 'ページの基本情報を確認しています...', log: 'タイトル・説明文・見出しを確認' },
      { percent: 46, label: '文章とリンク構造を確認しています...', log: '公開されている本文を確認' },
      { percent: 64, label: '構造化データを確認しています...', log: '会社情報・FAQ・記事情報を確認' },
      { percent: 80, label: 'AI引用準備度を計算しています...', log: '15項目を100点満点で採点' },
      { percent: 88, label: '診断結果をまとめています...', log: '最終スコアを作成' }
    ];
    var index = 0;

    error.hidden = true;
    error.textContent = '';
    document.getElementById('shindan-scan-log').innerHTML = '';
    analysis.style.display = 'block';
    setProgress(4, 'サイトへ接続しています...');
    analysis.scrollIntoView({ behavior: 'smooth', block: 'center' });

    function advance() {
      if (index >= stages.length) return;
      var stage = stages[index++];
      setProgress(stage.percent, stage.label);
      addLog(stage.log);
    }

    advance();
    var timer = window.setInterval(advance, 650);

    return {
      complete: function() {
        window.clearInterval(timer);
        setProgress(100, '診断が完了しました');
        addLog('AI引用準備度スコアを算出しました');
      },
      fail: function(message) {
        window.clearInterval(timer);
        setProgress(0, '診断できませんでした');
        error.textContent = message;
        error.hidden = false;
      }
    };
  }

  function animateScore(target) {
    var score = document.getElementById('shindan-total-score');
    var current = 0;
    var step = Math.max(1, Math.ceil(target / 32));
    score.textContent = '0';

    var timer = window.setInterval(function() {
      current = Math.min(target, current + step);
      score.textContent = String(current);
      if (current >= target) window.clearInterval(timer);
    }, 28);
  }

  function showResults(url, score, diagnosisToken) {
    var analysis = document.getElementById('shindan-analysis');
    var results = document.getElementById('shindan-results');

    analysis.style.display = 'none';
    results.style.display = 'block';
    document.getElementById('shindan-results-url').textContent = url;
    animateScore(score);
    lastDiagnosis = { url: url, score: String(score), diagnosisToken: diagnosisToken };

    results.querySelectorAll('.fade-in').forEach(function(element) {
      element.classList.add('visible');
    });

    window.setTimeout(function() {
      results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  }

  function friendlyError(code) {
    var messages = {
      invalid_url: 'URLを確認してください。httpまたはhttpsで始まる公開サイトを入力してください。',
      private_network: '社内サイトやローカル環境は診断できません。一般公開されているURLを入力してください。',
      site_fetch_failed: 'サイトを読み込めませんでした。URLやアクセス制限をご確認ください。',
      unsupported_content: 'HTMLページを確認できませんでした。トップページのURLを入力してください。',
      timeout: 'サイトの応答に時間がかかっています。少し時間をおいて再度お試しください。'
    };
    return messages[code] || '診断中に問題が起きました。少し時間をおいて再度お試しください。';
  }

  async function requestScore(url) {
    var controller = new AbortController();
    var timeout = window.setTimeout(function() { controller.abort(); }, 18000);

    try {
      var response = await fetch(SCORE_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url }),
        signal: controller.signal
      });
      var data = await response.json();
      if (!response.ok || data.result !== 'success' || typeof data.score !== 'number' || !/^[a-f0-9]{40}$/.test(data.diagnosisToken || '')) {
        throw new Error(data.code || 'site_fetch_failed');
      }
      return data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('timeout');
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function handleSubmit(inputId) {
    var input = document.getElementById(inputId);
    var submit = document.getElementById('shindan-submit');
    var url = input.value.trim();

    if (!url) {
      input.focus();
      return;
    }

    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;

    try {
      var parsed = new URL(url);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') throw new Error('invalid_url');
      parsed.hash = '';
      url = parsed.toString();
      input.value = url;
    } catch (error) {
      input.setAttribute('aria-invalid', 'true');
      input.focus();
      return;
    }

    input.removeAttribute('aria-invalid');
    submit.disabled = true;
    document.getElementById('shindan-results').style.display = 'none';
    var progress = startProgress(url);

    try {
      var diagnosis = await requestScore(url);
      progress.complete();
      window.setTimeout(function() {
        showResults(diagnosis.url || url, diagnosis.score, diagnosis.diagnosisToken);
      }, 350);
    } catch (error) {
      progress.fail(friendlyError(error.message));
    } finally {
      submit.disabled = false;
    }
  }

  document.getElementById('shindan-submit').addEventListener('click', function() {
    handleSubmit('shindan-url');
  });

  document.getElementById('shindan-url').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') handleSubmit('shindan-url');
  });

  var reportBtn = document.getElementById('shindan-report-btn');
  if (reportBtn) {
    reportBtn.addEventListener('click', async function() {
      var emailInput = document.getElementById('shindan-email');
      var email = emailInput.value.trim();

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        emailInput.setAttribute('aria-invalid', 'true');
        emailInput.focus();
        return;
      }

      emailInput.removeAttribute('aria-invalid');
      reportBtn.textContent = '送信中...';
      reportBtn.disabled = true;

      var formData = new FormData();
      formData.append('formType', 'shindan');
      formData.append('email', email);
      formData.append('diagnosisToken', lastDiagnosis.diagnosisToken);
      formData.append('url', lastDiagnosis.url);
      formData.append('score', lastDiagnosis.score);

      try {
        var response = await fetch('api/llmo-shindan.php', { method: 'POST', body: formData });
        var data = await response.json();
        if (!response.ok || data.result !== 'success' || !data.reportUrl) {
          throw new Error(data.code || 'report_failed');
        }

        fetch(GAS_URL, { method: 'POST', body: formData }).catch(function() {});

        var form = document.getElementById('shindan-report-form');
        form.innerHTML = '' +
          '<div class="shindan-report-success">' +
            '<strong>個別レポートを発行しました</strong>' +
            '<span>同じURLをメールにも送りました。</span>' +
            '<a class="shindan-report-open-btn" href="' + encodeURI(data.reportUrl) + '">詳しいレポートを見る</a>' +
          '</div>';
      } catch (error) {
        reportBtn.textContent = '無料レポートを発行する';
        reportBtn.disabled = false;
        if (error.message === 'diagnosis_expired' || error.message === 'report_not_found') {
          alert('診断結果の有効時間が切れました。もう一度診断してください。');
        } else {
          alert('レポートを発行できませんでした。時間をおいて再度お試しください。');
        }
      }
    });
  }
})();

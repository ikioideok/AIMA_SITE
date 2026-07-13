(function() {
  'use strict';

  var loading = document.getElementById('report-loading');
  var errorSection = document.getElementById('report-error');
  var content = document.getElementById('report-content');

  function addTextElement(parent, tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    parent.appendChild(element);
    return element;
  }

  function formatDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('ja-JP', {
      year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
    }).format(date) + ' 診断';
  }

  function scoreMessage(score) {
    if (score >= 85) return 'AIに内容を理解してもらうための土台は、かなり整っています。';
    if (score >= 70) return '基本は整っています。弱い項目を補うと、さらに伝わりやすくなります。';
    if (score >= 50) return '土台はありますが、改善すると大きく伸ばせる項目があります。';
    return 'AIが内容を判断するための情報が不足しています。優先項目から整えましょう。';
  }

  function renderBreakdown(items) {
    var container = document.getElementById('report-breakdown');
    items.forEach(function(item, index) {
      var card = document.createElement('article');
      card.className = 'report-breakdown-card';
      addTextElement(card, 'span', 'report-breakdown-number', String(index + 1).padStart(2, '0'));
      addTextElement(card, 'h3', '', item.label);
      var score = addTextElement(card, 'p', 'report-breakdown-score', String(item.earned));
      addTextElement(score, 'span', '', ' / ' + item.max);
      var track = document.createElement('div');
      track.className = 'report-breakdown-track';
      track.setAttribute('role', 'progressbar');
      track.setAttribute('aria-label', item.label);
      track.setAttribute('aria-valuemin', '0');
      track.setAttribute('aria-valuemax', String(item.max));
      track.setAttribute('aria-valuenow', String(item.earned));
      var fill = document.createElement('span');
      fill.style.width = Math.round((item.earned / item.max) * 100) + '%';
      track.appendChild(fill);
      card.appendChild(track);
      container.appendChild(card);
    });
  }

  function renderHighlights(targetId, items, emptyMessage) {
    var list = document.getElementById(targetId);
    if (!items.length) {
      var empty = document.createElement('li');
      empty.className = 'report-highlight-empty';
      empty.textContent = emptyMessage;
      list.appendChild(empty);
      return;
    }
    items.forEach(function(item) {
      var row = document.createElement('li');
      addTextElement(row, 'strong', '', item.label);
      addTextElement(row, 'p', '', item.text);
      list.appendChild(row);
    });
  }

  function renderChecks(checks) {
    var list = document.getElementById('report-checks');
    checks.forEach(function(check) {
      var row = document.createElement('article');
      row.className = 'report-check-row report-check-' + check.status;

      var status = check.status === 'good' ? '良好' : (check.status === 'partial' ? '改善余地' : '要改善');
      addTextElement(row, 'span', 'report-check-status', status);

      var body = document.createElement('div');
      addTextElement(body, 'h3', '', check.label);
      addTextElement(body, 'p', '', check.detail);
      if (check.status !== 'good') addTextElement(body, 'p', 'report-check-advice', check.recommendation);
      row.appendChild(body);

      var points = addTextElement(row, 'strong', 'report-check-points', String(check.earned));
      addTextElement(points, 'span', '', ' / ' + check.max);
      list.appendChild(row);
    });
  }

  function showError(code) {
    var messages = {
      invalid_report: 'レポートURLが正しくありません。',
      report_not_found: 'レポートが見つからないか、有効期限が切れています。',
      report_expired: 'このレポートの有効期限が切れています。'
    };
    loading.hidden = true;
    errorSection.hidden = false;
    document.getElementById('report-error-message').textContent = messages[code] || '時間をおいて、もう一度お試しください。';
  }

  function renderReport(report) {
    document.title = report.siteName + 'のLLMO診断レポート｜AIMA';
    document.getElementById('report-site-name').textContent = report.siteName;
    var siteUrl = document.getElementById('report-site-url');
    siteUrl.textContent = report.url;
    siteUrl.href = report.url;
    document.getElementById('report-checked-at').textContent = formatDate(report.checkedAt);
    document.getElementById('report-score').textContent = String(report.score);
    document.getElementById('report-score-message').textContent = scoreMessage(report.score);

    renderBreakdown(report.breakdown || []);
    renderHighlights('report-strengths', report.strengths || [], '良好と判定できる項目は、これから増やしていきましょう。');
    renderHighlights('report-improvements', report.improvements || [], '大きな改善項目は見つかりませんでした。');
    renderChecks(report.checks || []);

    var copyButton = document.getElementById('report-copy-btn');
    copyButton.addEventListener('click', function() {
      navigator.clipboard.writeText(window.location.href).then(function() {
        document.getElementById('report-copy-status').textContent = 'URLをコピーしました。';
        copyButton.textContent = 'コピーしました';
      }).catch(function() {
        document.getElementById('report-copy-status').textContent = 'コピーできませんでした。ブラウザのURL欄からコピーしてください。';
      });
    });

    if (typeof navigator.share === 'function') {
      var shareButton = document.getElementById('report-share-btn');
      shareButton.hidden = false;
      shareButton.addEventListener('click', function() {
        navigator.share({
          title: report.siteName + 'のLLMO診断レポート',
          text: 'AI引用準備度スコア ' + report.score + '点',
          url: window.location.href
        }).catch(function() {});
      });
    }

    loading.hidden = true;
    content.hidden = false;
  }

  var reportId = new URLSearchParams(window.location.search).get('id') || '';
  if (!/^[a-f0-9]{40}$/.test(reportId)) {
    showError('invalid_report');
    return;
  }

  fetch('api/llmo-report.php?id=' + encodeURIComponent(reportId), { cache: 'no-store' })
    .then(function(response) {
      return response.json().then(function(data) {
        if (!response.ok || data.result !== 'success') throw new Error(data.code || 'report_failed');
        return data.report;
      });
    })
    .then(renderReport)
    .catch(function(error) { showError(error.message); });
})();

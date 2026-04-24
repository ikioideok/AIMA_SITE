// ============================================================
// 統合フォーム処理 Google Apps Script
// お問い合わせフォーム ＋ LLMO診断レポート請求 ＋ メルマガ購読
// ============================================================
// デプロイ手順:
// 1. https://script.google.com で「新しいプロジェクト」を作成
// 2. このコードを貼り付けて保存
// 3. 必要なら「サービス」から Gmail API を有効化
// 4. 「デプロイ」→「新しいデプロイ」
//    - 種類: ウェブアプリ
//    - 次のユーザーとして実行: 自分
//    - アクセスできるユーザー: 全員
// 5. 「デプロイ」ボタンを押す
// 6. 表示されたURLをコピーし、必要なら WEB_APP_URL に反映
// 7. 毎日配信する場合は sendDailyNewsletter に時間トリガーを設定
// ============================================================

// ▼▼▼ 設定 ▼▼▼
var SPREADSHEET_ID = '1053yH7EmZyhrtnANOwEVvWhTDQvaOxARXWdj0uvmKVw';
var NOTIFY_EMAIL = 'info@ai-and-marketing.jp';
var WEB_APP_URL = '';

var NEWSLETTER_FROM_EMAIL = 'newsletter@ai-and-marketing.jp';
var NEWSLETTER_FROM_NAME = '株式会社AIMA';
var NEWSLETTER_REPLY_TO = 'info@ai-and-marketing.jp';
var NEWSLETTER_LIST_NAME = 'LLMO内製化マガジン';
var NEWSLETTER_LIST_ID = 'llmo-naiseika.ai-and-marketing.jp';

// シート名
var SHEET_CONTACT = 'お問い合わせ';
var SHEET_SHINDAN = '診断レポート請求';
var SHEET_NEWSLETTER_SUBSCRIBERS = 'メルマガ購読者';
var SHEET_NEWSLETTER_ISSUES = 'メルマガ配信';
var SHEET_NEWSLETTER_LOG = 'メルマガ送信ログ';
// ▲▲▲ 設定 ▲▲▲

function jsonResponse_(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

function textResponse_(text) {
  return ContentService
    .createTextOutput(text)
    .setMimeType(ContentService.MimeType.TEXT);
}

function htmlResponse_(title, heading, message, actionHtml) {
  var html = ''
    + '<!DOCTYPE html>'
    + '<html lang="ja"><head><meta charset="UTF-8">'
    + '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    + '<title>' + escapeHtml_(title) + '</title>'
    + '<style>'
    + 'body{margin:0;background:#f0f0f0;color:#0a0a0a;font-family:"Noto Sans JP",sans-serif;}'
    + '.wrap{max-width:640px;margin:0 auto;padding:56px 20px;}'
    + '.card{background:#fafafa;border:1px solid #e8e8e8;border-radius:16px;padding:32px 28px;}'
    + '.eyebrow{font:700 12px/1.4 sans-serif;letter-spacing:.08em;color:#666;margin-bottom:12px;}'
    + 'h1{margin:0 0 14px;font-size:28px;line-height:1.45;}'
    + 'p{margin:0 0 12px;font-size:15px;line-height:1.9;color:#4f4f4f;}'
    + '.btn{display:inline-block;margin-top:12px;padding:12px 20px;background:#0a0a0a;color:#fff;text-decoration:none;border-radius:4px;font-size:14px;font-weight:700;}'
    + '</style></head><body><div class="wrap"><div class="card">'
    + '<div class="eyebrow">LLMO内製化マガジン</div>'
    + '<h1>' + escapeHtml_(heading) + '</h1>'
    + '<p>' + message + '</p>'
    + (actionHtml || '')
    + '</div></div></body></html>';
  return HtmlService.createHtmlOutput(html).setTitle(title);
}

function getOrCreateSheet_(sheetName, headerRow) {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    sheet.appendRow(headerRow);
    sheet.getRange(1, 1, 1, headerRow.length).setFontWeight('bold');
  }
  return sheet;
}

function formatTimestamp_(date) {
  return Utilities.formatDate(date, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
}

function formatDateKey_(date) {
  return Utilities.formatDate(date, 'Asia/Tokyo', 'yyyy-MM-dd');
}

function normalizeEmail_(email) {
  return String(email || '').trim().toLowerCase();
}

function escapeHtml_(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function generateToken_() {
  return Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
}

function getWebAppUrl_() {
  if (WEB_APP_URL) return WEB_APP_URL;
  try {
    return ScriptApp.getService().getUrl();
  } catch (error) {
    return '';
  }
}

function getNewsletterSubscribersSheet_() {
  return getOrCreateSheet_(SHEET_NEWSLETTER_SUBSCRIBERS, [
    'email',
    'status',
    'source',
    'confirm_token',
    'unsubscribe_token',
    'created_at',
    'confirmed_at',
    'unsubscribed_at',
    'last_sent_at'
  ]);
}

function getNewsletterIssuesSheet_() {
  return getOrCreateSheet_(SHEET_NEWSLETTER_ISSUES, [
    'send_date',
    'subject',
    'preheader',
    'html_body',
    'text_body',
    'status',
    'sent_at',
    'sent_count'
  ]);
}

function getNewsletterLogSheet_() {
  return getOrCreateSheet_(SHEET_NEWSLETTER_LOG, [
    'timestamp',
    'send_date',
    'email',
    'subject',
    'result',
    'detail'
  ]);
}

function findSubscriberRowByEmail_(sheet, email) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;

  var values = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();
  var normalized = normalizeEmail_(email);
  var i;

  for (i = 0; i < values.length; i += 1) {
    if (normalizeEmail_(values[i][0]) === normalized) {
      return {
        row: i + 2,
        values: values[i]
      };
    }
  }

  return null;
}

function findSubscriberRowByToken_(sheet, token, email) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;

  var values = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();
  var normalizedEmail = normalizeEmail_(email);
  var i;

  for (i = 0; i < values.length; i += 1) {
    var rowEmail = normalizeEmail_(values[i][0]);
    var confirmToken = String(values[i][3] || '');
    var unsubscribeToken = String(values[i][4] || '');
    var matchesEmail = !normalizedEmail || rowEmail === normalizedEmail;
    var matchesToken = confirmToken === token || unsubscribeToken === token;

    if (matchesEmail && matchesToken) {
      return {
        row: i + 2,
        values: values[i]
      };
    }
  }

  return null;
}

function getSubscriberRecord_(rowValues) {
  return {
    email: normalizeEmail_(rowValues[0]),
    status: String(rowValues[1] || ''),
    source: String(rowValues[2] || ''),
    confirmToken: String(rowValues[3] || ''),
    unsubscribeToken: String(rowValues[4] || ''),
    createdAt: String(rowValues[5] || ''),
    confirmedAt: String(rowValues[6] || ''),
    unsubscribedAt: String(rowValues[7] || ''),
    lastSentAt: String(rowValues[8] || '')
  };
}

function buildConfirmUrl_(email, token) {
  return getWebAppUrl_() + '?action=confirm&email=' + encodeURIComponent(email) + '&token=' + encodeURIComponent(token);
}

function buildUnsubscribeUrl_(email, token) {
  return getWebAppUrl_() + '?action=unsubscribe&email=' + encodeURIComponent(email) + '&token=' + encodeURIComponent(token);
}

function appendNewsletterLog_(timestamp, sendDate, email, subject, result, detail) {
  try {
    var sheet = getNewsletterLogSheet_();
    sheet.appendRow([timestamp, sendDate, email, subject, result, detail || '']);
  } catch (error) {}
}

function sendNewsletterConfirmMail_(email, confirmUrl, unsubscribeUrl) {
  var subject = '【AIMA】LLMO内製化マガジンの登録確認';
  var textBody = ''
    + 'LLMO内製化マガジンへのご登録ありがとうございます。\n\n'
    + 'まだ登録は完了していません。以下のURLを開くと購読が確定します。\n'
    + confirmUrl + '\n\n'
    + 'このメールに心当たりがない場合は、そのまま破棄してください。\n'
    + '配信停止はこちら:\n'
    + unsubscribeUrl + '\n';
  var htmlBody = ''
    + '<div style="font-family:\'Noto Sans JP\',sans-serif;color:#0a0a0a;line-height:1.8;">'
    + '<p>LLMO内製化マガジンへのご登録ありがとうございます。</p>'
    + '<p>まだ登録は完了していません。以下のボタンを押すと購読が確定します。</p>'
    + '<p style="margin:28px 0;">'
    + '<a href="' + escapeHtml_(confirmUrl) + '" style="display:inline-block;padding:12px 20px;background:#0a0a0a;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:700;">登録を確定する</a>'
    + '</p>'
    + '<p style="font-size:13px;color:#666;">このメールに心当たりがない場合は、そのまま破棄してください。<br>配信停止: <a href="' + escapeHtml_(unsubscribeUrl) + '">' + escapeHtml_(unsubscribeUrl) + '</a></p>'
    + '</div>';

  MailApp.sendEmail({
    to: email,
    subject: subject,
    body: textBody,
    htmlBody: htmlBody,
    name: NEWSLETTER_FROM_NAME,
    replyTo: NEWSLETTER_REPLY_TO
  });
}

function sendNewsletterWelcomeMail_(email, unsubscribeUrl) {
  var subject = '【AIMA】LLMO内製化マガジンへようこそ';
  var textBody = ''
    + 'LLMO内製化マガジンへのご登録ありがとうございます。\n\n'
    + 'これから、LLMOを自社で進めるときに役立つ実務メモをお送りします。\n'
    + '内容は、まずは自分たちで試せることを中心にまとめます。\n\n'
    + '最初の1アクションとして、おすすめは次の3つです。\n'
    + '- サービスページを1枚だけ選んで見直す\n'
    + '- 「誰向けか」「何をやるか」「どこまでやるか」を1画面で伝える\n'
    + '- 料金、対応範囲、進め方のうち不足している1項目を足す\n\n'
    + '関連記事はこちら:\n'
    + 'https://ai-and-marketing.jp/blog.html\n\n'
    + '進める中で「どこから直すべきかだけ見てほしい」という状態になったら、必要なときだけこちらからご相談ください。\n'
    + 'https://ai-and-marketing.jp/service.html\n\n'
    + '配信停止はこちら:\n'
    + unsubscribeUrl + '\n';
  var htmlBody = ''
    + '<div style="font-family:\'Noto Sans JP\',sans-serif;color:#0a0a0a;line-height:1.9;">'
    + '<p>LLMO内製化マガジンへのご登録ありがとうございます。</p>'
    + '<p>これから、LLMOを自社で進めるときに役立つ実務メモをお送りします。内容は、まずは自分たちで試せることを中心にまとめます。</p>'
    + '<div style="margin:24px 0;padding:18px 20px;background:#f7f4ee;border:1px solid #e5dccd;border-radius:14px;">'
    + '<div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#7b6a53;margin-bottom:8px;">最初の1アクション</div>'
    + '<ul style="padding-left:18px;margin:0;">'
    + '<li>サービスページを1枚だけ選んで見直す</li>'
    + '<li>「誰向けか」「何をやるか」「どこまでやるか」を1画面で伝える</li>'
    + '<li>料金、対応範囲、進め方のうち不足している1項目を足す</li>'
    + '</ul>'
    + '</div>'
    + '<p>関連記事はこちらから読めます。</p>'
    + '<p style="margin:24px 0 14px;">'
    + '<a href="https://ai-and-marketing.jp/blog.html" style="display:inline-block;padding:12px 20px;background:#0a0a0a;color:#ffffff;text-decoration:none;border-radius:999px;font-weight:700;">ブログを見る</a>'
    + '</p>'
    + '<p>進める中で「どこから直すべきかだけ見てほしい」という状態になったら、必要なときだけこちらからご相談ください。</p>'
    + '<p style="margin:0 0 22px;">'
    + '<a href="https://ai-and-marketing.jp/service.html" style="display:inline-block;padding:12px 20px;background:#0a0a0a;color:#ffffff;text-decoration:none;border-radius:999px;font-weight:700;">ご相談はこちら</a>'
    + '</p>'
    + '<p style="font-size:13px;color:#666;">配信停止: <a href="' + escapeHtml_(unsubscribeUrl) + '">' + escapeHtml_(unsubscribeUrl) + '</a></p>'
    + '</div>';

  MailApp.sendEmail({
    to: email,
    subject: subject,
    body: textBody,
    htmlBody: htmlBody,
    name: NEWSLETTER_FROM_NAME,
    replyTo: NEWSLETTER_REPLY_TO
  });

  return subject;
}

function buildNewsletterTextBody_(issue, unsubscribeUrl) {
  var textBody = String(issue.textBody || '').trim();
  if (!textBody && issue.htmlBody) {
    textBody = String(issue.htmlBody)
      .replace(/<style[\s\S]*?<\/style>/gi, '')
      .replace(/<script[\s\S]*?<\/script>/gi, '')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .replace(/\n{3,}/g, '\n\n');
  }

  return textBody
    + '\n\n'
    + '配信停止はこちら:\n'
    + unsubscribeUrl + '\n';
}

function buildNewsletterHtmlBody_(issue, unsubscribeUrl) {
  var preheader = issue.preheader ? '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">' + escapeHtml_(issue.preheader) + '</div>' : '';
  var body = String(issue.htmlBody || '').trim();

  return ''
    + '<!DOCTYPE html><html lang="ja"><body style="margin:0;background:#f0f0f0;">'
    + preheader
    + '<div style="padding:32px 16px;">'
    + '<div style="max-width:680px;margin:0 auto;background:#fafafa;border:1px solid #e8e8e8;border-radius:16px;overflow:hidden;">'
    + '<div style="padding:14px 20px;border-bottom:1px solid #e8e8e8;font:700 12px/1.4 sans-serif;letter-spacing:.08em;color:#666;">LLMO内製化マガジン</div>'
    + '<div style="padding:28px 20px;font-family:\'Noto Sans JP\',sans-serif;color:#0a0a0a;line-height:1.9;font-size:15px;">'
    + body
    + '</div>'
    + '<div style="padding:18px 20px;border-top:1px solid #e8e8e8;font-family:\'Noto Sans JP\',sans-serif;font-size:12px;line-height:1.8;color:#666;">'
    + 'まずは自分たちで進めたい方向けに、LLMOの設計・運用・改善のヒントをお届けしています。<br>'
    + '<a href="' + escapeHtml_(unsubscribeUrl) + '" style="color:#666;">配信停止</a>'
    + '</div></div></div></body></html>';
}

function encodeSubjectHeader_(subject) {
  return '=?UTF-8?B?' + Utilities.base64Encode(Utilities.newBlob(subject).getBytes()) + '?=';
}

function sendRawNewsletterEmail_(email, subject, htmlBody, textBody, unsubscribeUrl) {
  var boundary = 'aima-' + Utilities.getUuid();
  var lines = [
    'MIME-Version: 1.0',
    'To: ' + email,
    'From: ' + NEWSLETTER_FROM_NAME + ' <' + NEWSLETTER_FROM_EMAIL + '>',
    'Reply-To: ' + NEWSLETTER_REPLY_TO,
    'Subject: ' + encodeSubjectHeader_(subject),
    'List-ID: ' + NEWSLETTER_LIST_NAME + ' <' + NEWSLETTER_LIST_ID + '>',
    'List-Unsubscribe: <' + unsubscribeUrl + '>',
    'List-Unsubscribe-Post: List-Unsubscribe=One-Click',
    'Content-Type: multipart/alternative; boundary="' + boundary + '"',
    '',
    '--' + boundary,
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 7bit',
    '',
    textBody,
    '',
    '--' + boundary,
    'Content-Type: text/html; charset=UTF-8',
    'Content-Transfer-Encoding: 7bit',
    '',
    htmlBody,
    '',
    '--' + boundary + '--'
  ];
  var raw = Utilities.base64EncodeWebSafe(lines.join('\r\n'), Utilities.Charset.UTF_8);
  Gmail.Users.Messages.send({ raw: raw }, 'me');
}

function sendNewsletterMessage_(subscriber, issue) {
  var unsubscribeUrl = buildUnsubscribeUrl_(subscriber.email, subscriber.unsubscribeToken);
  var textBody = buildNewsletterTextBody_(issue, unsubscribeUrl);
  var htmlBody = buildNewsletterHtmlBody_(issue, unsubscribeUrl);

  try {
    sendRawNewsletterEmail_(subscriber.email, issue.subject, htmlBody, textBody, unsubscribeUrl);
  } catch (error) {
    MailApp.sendEmail({
      to: subscriber.email,
      subject: issue.subject,
      body: textBody,
      htmlBody: htmlBody,
      name: NEWSLETTER_FROM_NAME,
      replyTo: NEWSLETTER_REPLY_TO
    });
  }
}

function getPendingIssueRow_(sheet, dateKey) {
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return null;

  var values = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();
  var i;

  for (i = 0; i < values.length; i += 1) {
    var sendDate = String(values[i][0] || '');
    var status = String(values[i][5] || '').toLowerCase();

    if (!sendDate || sendDate > dateKey) continue;
    if (status !== 'ready' && status !== 'pending' && status !== 'draft') continue;

    return {
      row: i + 2,
      subject: String(values[i][1] || ''),
      preheader: String(values[i][2] || ''),
      htmlBody: String(values[i][3] || ''),
      textBody: String(values[i][4] || ''),
      status: status,
      sendDate: sendDate
    };
  }

  return null;
}

function doPost(e) {
  try {
    var params = (e && e.parameter) || {};
    var now = new Date();
    var timestamp = formatTimestamp_(now);
    var action = String(params.action || '').trim();

    if (action === 'unsubscribe') {
      handleNewsletterUnsubscribe_(params, timestamp);
      return textResponse_('OK');
    }

    var formType = String(params.formType || '').trim();

    if (!formType) {
      if (params.rank || params.score) {
        formType = 'shindan';
      } else if (params.message || params.name || params.company || params.tel) {
        formType = 'contact';
      }
    }

    if (formType === 'shindan') {
      return handleShindan_(params, timestamp);
    }

    if (formType === 'newsletter') {
      return handleNewsletterSubscribe_(params, timestamp);
    }

    return handleContact_(params, timestamp);
  } catch (error) {
    try {
      MailApp.sendEmail(
        NOTIFY_EMAIL,
        '【AIMA】GASエラー通知',
        'フォーム処理でエラーが発生しました。\n\n' + error.toString()
      );
    } catch (innerError) {}
    return jsonResponse_({ result: 'error', message: error.toString() });
  }
}

// ────────────────────────────────────────
// お問い合わせフォーム処理
// ────────────────────────────────────────
function handleContact_(params, timestamp) {
  var name = (params.name || '').trim();
  var email = (params.email || '').trim();
  var company = (params.company || '').trim();
  var message = (params.message || '').trim();
  var tel = (params.tel || '').trim();

  try {
    var sheet = getOrCreateSheet_(SHEET_CONTACT, ['日時', '会社名', '氏名', 'メールアドレス', '電話番号', 'お問い合わせ内容']);
    sheet.appendRow([timestamp, company, name, email, tel, message]);
  } catch (error) {}

  try {
    var subject = '【AIMA】お問い合わせ: ' + (company || name || '(未入力)');
    var body = '新しいお問い合わせがありました。\n\n'
      + '日時: ' + timestamp + '\n'
      + '会社名: ' + company + '\n'
      + '氏名: ' + name + '\n'
      + 'メールアドレス: ' + email + '\n'
      + '電話番号: ' + tel + '\n'
      + '\n--- お問い合わせ内容 ---\n'
      + message + '\n';

    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: subject,
      body: body,
      replyTo: email || NOTIFY_EMAIL
    });
  } catch (error) {}

  return jsonResponse_({ result: 'success', formType: 'contact' });
}

// ────────────────────────────────────────
// LLMO診断レポート請求処理
// ────────────────────────────────────────
function handleShindan_(params, timestamp) {
  var email = (params.email || '').trim();
  var url = (params.url || '').trim();
  var rank = (params.rank || '').trim();
  var score = (params.score || '').trim();

  if (!email || !url) {
    return jsonResponse_({ result: 'error', message: 'email and url are required.' });
  }

  try {
    var sheet = getOrCreateSheet_(SHEET_SHINDAN, ['日時', 'メールアドレス', '診断URL', 'ランク', '総合スコア']);
    sheet.appendRow([timestamp, email, url, rank, score]);
  } catch (error) {}

  try {
    var subject = '【LLMO診断】レポート請求: ' + url;
    var body = '新しいLLMO診断レポートの請求がありました。\n\n'
      + '日時: ' + timestamp + '\n'
      + 'メールアドレス: ' + email + '\n'
      + '診断URL: ' + url + '\n'
      + 'ランク: ' + rank + '\n'
      + '総合スコア: ' + score + '\n';

    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: subject,
      body: body,
      replyTo: email
    });
  } catch (error) {}

  return jsonResponse_({ result: 'success', formType: 'shindan' });
}

// ────────────────────────────────────────
// メルマガ購読処理
// ────────────────────────────────────────
function handleNewsletterSubscribe_(params, timestamp) {
  var email = normalizeEmail_(params.email || '');
  var source = String(params.source || 'site').trim();

  if (!email || !/@/.test(email)) {
    return jsonResponse_({ result: 'error', message: 'email is required.' });
  }

  var sheet = getNewsletterSubscribersSheet_();
  var existing = findSubscriberRowByEmail_(sheet, email);
  var confirmToken = generateToken_();
  var unsubscribeToken = generateToken_();

  if (existing) {
    var current = getSubscriberRecord_(existing.values);

    if (current.status === 'active') {
      return jsonResponse_({
        result: 'success',
        formType: 'newsletter',
        message: 'すでに登録済みです。次回以降の配信をお待ちください。'
      });
    }

    sheet.getRange(existing.row, 2, 1, 7).setValues([[
      'pending',
      source,
      confirmToken,
      unsubscribeToken,
      timestamp,
      '',
      ''
    ]]);
  } else {
    sheet.appendRow([
      email,
      'pending',
      source,
      confirmToken,
      unsubscribeToken,
      timestamp,
      '',
      '',
      ''
    ]);
  }

  var confirmUrl = buildConfirmUrl_(email, confirmToken);
  var unsubscribeUrl = buildUnsubscribeUrl_(email, unsubscribeToken);
  sendNewsletterConfirmMail_(email, confirmUrl, unsubscribeUrl);

  return jsonResponse_({
    result: 'success',
    formType: 'newsletter',
    message: '確認メールを送信しました。メール内のリンクを押すと登録が完了します。'
  });
}

function handleNewsletterConfirm_(params, timestamp) {
  var email = normalizeEmail_(params.email || '');
  var token = String(params.token || '').trim();

  if (!token) {
    return htmlResponse_('登録確認', 'リンクが無効です', '確認URLに必要な情報が不足しています。最初からもう一度ご登録ください。');
  }

  var sheet = getNewsletterSubscribersSheet_();
  var found = findSubscriberRowByToken_(sheet, token, email);

  if (!found) {
    return htmlResponse_('登録確認', 'リンクが無効です', '有効期限切れ、またはすでに別の確認リンクに更新されています。フォームから再度ご登録ください。');
  }

  var current = getSubscriberRecord_(found.values);
  if (current.confirmToken !== token) {
    return htmlResponse_('登録確認', 'リンクが無効です', '確認用リンクではありません。');
  }

  if (current.status === 'active') {
    return htmlResponse_('登録確認', 'すでに登録済みです', 'LLMO内製化マガジンはすでに登録済みです。次回以降の配信をお待ちください。');
  }

  sheet.getRange(found.row, 2, 1, 7).setValues([[
    'active',
    current.source || 'site',
    current.confirmToken,
    current.unsubscribeToken,
    current.createdAt || timestamp,
    timestamp,
    ''
  ]]);

  try {
    var welcomeSubject = sendNewsletterWelcomeMail_(current.email, buildUnsubscribeUrl_(current.email, current.unsubscribeToken));
    appendNewsletterLog_(timestamp, 'welcome', current.email, welcomeSubject, 'sent', 'confirmation welcome mail');
  } catch (error) {
    appendNewsletterLog_(timestamp, 'welcome', current.email, '【AIMA】LLMO内製化マガジンへようこそ', 'error', error.toString());
  }

  return htmlResponse_(
    '登録完了',
    '登録が完了しました',
    'LLMO内製化マガジンの購読を開始しました。毎朝5分で読める実務メモをお届けします。',
    '<a class="btn" href="https://ai-and-marketing.jp/blog.html">ブログを見る</a>'
  );
}

function handleNewsletterUnsubscribe_(params, timestamp) {
  var email = normalizeEmail_(params.email || '');
  var token = String(params.token || '').trim();
  var sheet = getNewsletterSubscribersSheet_();
  var found = token ? findSubscriberRowByToken_(sheet, token, email) : findSubscriberRowByEmail_(sheet, email);

  if (!found) {
    return htmlResponse_('配信停止', '配信停止リンクを確認できませんでした', 'URLが古い可能性があります。必要であればフォームから再登録してください。');
  }

  var current = getSubscriberRecord_(found.values);
  if (token && current.unsubscribeToken !== token) {
    return htmlResponse_('配信停止', '配信停止リンクを確認できませんでした', 'URLが古い可能性があります。必要であればフォームから再登録してください。');
  }

  sheet.getRange(found.row, 2, 1, 7).setValues([[
    'unsubscribed',
    current.source,
    current.confirmToken,
    current.unsubscribeToken,
    current.createdAt,
    current.confirmedAt,
    timestamp
  ]]);

  return htmlResponse_(
    '配信停止',
    '配信を停止しました',
    'LLMO内製化マガジンの配信停止を受け付けました。再開したい場合は、サイトの登録フォームからもう一度ご登録ください。',
    '<a class="btn" href="https://ai-and-marketing.jp/blog.html">ブログへ戻る</a>'
  );
}

function doGet(e) {
  var params = (e && e.parameter) || {};
  var action = String(params.action || '').trim();
  var timestamp = formatTimestamp_(new Date());

  if (action === 'confirm') {
    return handleNewsletterConfirm_(params, timestamp);
  }

  if (action === 'unsubscribe') {
    return handleNewsletterUnsubscribe_(params, timestamp);
  }

  return textResponse_('AIMA Unified GAS is running. OK');
}

// ────────────────────────────────────────
// 毎日配信用トリガー
// ────────────────────────────────────────
function sendDailyNewsletter() {
  var now = new Date();
  var timestamp = formatTimestamp_(now);
  var dateKey = formatDateKey_(now);
  var issuesSheet = getNewsletterIssuesSheet_();
  var issue = getPendingIssueRow_(issuesSheet, dateKey);

  if (!issue) {
    appendNewsletterLog_(timestamp, dateKey, '', '', 'skip', 'ready status issue not found');
    return;
  }

  if (!issue.subject || (!issue.htmlBody && !issue.textBody)) {
    appendNewsletterLog_(timestamp, issue.sendDate, '', issue.subject || '', 'error', 'subject or body is missing');
    return;
  }

  var subscribersSheet = getNewsletterSubscribersSheet_();
  var lastRow = subscribersSheet.getLastRow();
  if (lastRow < 2) {
    appendNewsletterLog_(timestamp, issue.sendDate, '', issue.subject, 'skip', 'active subscribers not found');
    return;
  }

  var values = subscribersSheet.getRange(2, 1, lastRow - 1, subscribersSheet.getLastColumn()).getValues();
  var sentCount = 0;
  var i;

  for (i = 0; i < values.length; i += 1) {
    var subscriber = getSubscriberRecord_(values[i]);
    if (subscriber.status !== 'active') continue;

    try {
      sendNewsletterMessage_(subscriber, issue);
      subscribersSheet.getRange(i + 2, 9).setValue(timestamp);
      appendNewsletterLog_(timestamp, issue.sendDate, subscriber.email, issue.subject, 'sent', '');
      sentCount += 1;
      Utilities.sleep(250);
    } catch (error) {
      appendNewsletterLog_(timestamp, issue.sendDate, subscriber.email, issue.subject, 'error', error.toString());
    }
  }

  issuesSheet.getRange(issue.row, 6, 1, 3).setValues([[
    'sent',
    timestamp,
    sentCount
  ]]);
}

// ============================================================
// LLMO診断レポート請求用 Google Apps Script
// ============================================================
// 使い方:
// 1. Google スプレッドシートを開く（既存 or 新規）
// 2. 拡張機能 → Apps Script を開く
// 3. このコードを貼り付けて保存
// 4. デプロイ → 新しいデプロイ → ウェブアプリ
//    - 次のユーザーとして実行: 自分
//    - アクセスできるユーザー: 全員
// 5. デプロイURLをコピーして shindan.js の GAS_URL に貼り付け
// ============================================================

// standalone の Web アプリとして動かす場合は、記録先スプレッドシートIDを入れる
// 例: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
var SPREADSHEET_ID = '1053yH7EmZyhrtnANOwEVvWhTDQvaOxARXWdj0uvmKVw';

// 記録先のシート名
var SHEET_NAME = '診断レポート請求';

// メール通知先（自分のアドレス）
var NOTIFY_EMAIL = 'info@ai-and-marketing.jp';

function jsonResponse_(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}

function getSpreadsheet_() {
  if (SPREADSHEET_ID) {
    return SpreadsheetApp.openById(SPREADSHEET_ID);
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss) {
    return ss;
  }

  throw new Error('Spreadsheet is not configured. Set SPREADSHEET_ID or bind this script to a spreadsheet.');
}

function getOrCreateSheet_() {
  var ss = getSpreadsheet_();
  var sheet = ss.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['日時', 'メールアドレス', '診断URL', 'ランク', '総合スコア']);
    sheet.getRange(1, 1, 1, 5).setFontWeight('bold');
  }

  return sheet;
}

function doPost(e) {
  try {
    var params = (e && e.parameter) || {};
    var email = (params.email || '').trim();
    var url = (params.url || '').trim();
    var rank = (params.rank || '').trim();
    var score = (params.score || '').trim();
    var now = new Date();
    var timestamp = Utilities.formatDate(now, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm:ss');
    var sheetLogged = false;
    var sheetError = '';
    var notifySent = false;
    var notifyError = '';

    if (!email || !url) {
      return jsonResponse_({
        result: 'error',
        message: 'email and url are required.'
      });
    }

    try {
      var sheet = getOrCreateSheet_();
      sheet.appendRow([timestamp, email, url, rank, score]);
      sheetLogged = true;
    } catch (error) {
      sheetError = error.toString();
    }

    if (NOTIFY_EMAIL) {
      try {
        var subject = '【LLMO診断】レポート請求: ' + url;
        var body = '新しいLLMO診断レポートの請求がありました。\n\n'
        + '日時: ' + timestamp + '\n'
        + 'メールアドレス: ' + email + '\n'
        + '診断URL: ' + url + '\n'
        + 'ランク: ' + rank + '\n'
        + '総合スコア: ' + score + '\n';

        if (sheetError) {
          body += '\n[警告] スプレッドシート記録に失敗しました。\n' + sheetError + '\n';
        }

        MailApp.sendEmail(NOTIFY_EMAIL, subject, body);
        notifySent = true;
      } catch (error) {
        notifyError = error.toString();
      }
    }

    if (!sheetLogged && !notifySent) {
      return jsonResponse_({
        result: 'error',
        message: 'Failed to log request and send notification.',
        sheetError: sheetError,
        notifyError: notifyError
      });
    }

    return jsonResponse_({
      result: 'success',
      sheetLogged: sheetLogged,
      notifySent: notifySent,
      sheetError: sheetError,
      notifyError: notifyError
    });

  } catch (error) {
    return jsonResponse_({ result: 'error', message: error.toString() });
  }
}

// GET でアクセスされた場合（テスト用）
function doGet(e) {
  return ContentService
    .createTextOutput('LLMO Shindan GAS is running.')
    .setMimeType(ContentService.MimeType.TEXT);
}

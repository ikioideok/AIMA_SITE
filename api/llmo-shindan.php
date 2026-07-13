<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');
header('Cache-Control: no-store');

require_once __DIR__ . '/llmo-diagnosis-store.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'result' => 'error',
        'message' => 'Method not allowed.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$email = trim((string)($_POST['email'] ?? ''));
$diagnosisToken = trim((string)($_POST['diagnosisToken'] ?? ''));
$timestamp = (new DateTimeImmutable('now', new DateTimeZone('Asia/Tokyo')))->format('Y/m/d H:i:s');

if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode([
        'result' => 'error',
        'message' => 'Valid email is required.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if (!validDiagnosisToken($diagnosisToken)) {
    http_response_code(400);
    echo json_encode([
        'result' => 'error',
        'code' => 'invalid_token',
        'message' => 'Valid diagnosis token is required.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

try {
    $finalized = finalizeDiagnosisReport($diagnosisToken);
    $reportId = (string)$finalized['id'];
    $report = $finalized['report'];
} catch (InvalidArgumentException $error) {
    http_response_code(400);
    echo json_encode([
        'result' => 'error',
        'code' => $error->getMessage(),
        'message' => 'Invalid diagnosis token.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
} catch (RuntimeException $error) {
    $code = $error->getMessage();
    http_response_code($code === 'diagnosis_expired' || $code === 'report_not_found' ? 410 : 500);
    echo json_encode([
        'result' => 'error',
        'code' => $code,
        'message' => 'Failed to create diagnosis report.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$url = (string)($report['url'] ?? '');
$score = (int)($report['score'] ?? 0);
$reportUrl = 'https://ai-and-marketing.jp/llmo-report.html?id=' . rawurlencode($reportId);

$notifyEmail = 'info@ai-and-marketing.jp';
$fromEmail = 'info@ai-and-marketing.jp';
$replyTo = $email;
$clientIp = (string)($_SERVER['REMOTE_ADDR'] ?? '');
$userAgent = trim((string)($_SERVER['HTTP_USER_AGENT'] ?? ''));
$referer = trim((string)($_SERVER['HTTP_REFERER'] ?? ''));

$logDir = __DIR__ . '/logs';
$logPath = $logDir . '/llmo-shindan.csv';
$logWritten = false;
$logError = '';
$mailSent = false;
$mailError = '';

if (!is_dir($logDir) && !mkdir($logDir, 0775, true) && !is_dir($logDir)) {
    $logError = 'Failed to create log directory.';
}

if ($logError === '') {
    $fp = @fopen($logPath, 'ab');
    if ($fp === false) {
        $logError = 'Failed to open log file.';
    } else {
        if (filesize($logPath) === 0) {
            fputcsv($fp, ['timestamp', 'email', 'url', 'score', 'report_url', 'referer', 'client_ip', 'user_agent']);
        }
        $logWritten = fputcsv($fp, [$timestamp, $email, $url, $score, $reportUrl, $referer, $clientIp, $userAgent]) !== false;
        if (!$logWritten) {
            $logError = 'Failed to write log row.';
        }
        fclose($fp);
    }
}

mb_language('Japanese');
mb_internal_encoding('UTF-8');

$subject = '【LLMO診断】レポート請求: ' . $url;
$body = implode("\n", [
    '新しいLLMO診断レポートの請求がありました。',
    '',
    '日時: ' . $timestamp,
    'メールアドレス: ' . $email,
    '診断URL: ' . $url,
    'AI引用準備度スコア: ' . $score . ' / 100',
    '個別レポート: ' . $reportUrl,
    '参照元: ' . $referer,
    'IP: ' . $clientIp,
    'UA: ' . $userAgent,
]);

if ($logError !== '') {
    $body .= "\n\n[警告] CSVログ書き込みに失敗しました。\n" . $logError;
}

$headers = [
    'From: AIMA <' . $fromEmail . '>',
    'Reply-To: ' . $replyTo,
    'Content-Type: text/plain; charset=UTF-8',
];

$mailSent = @mb_send_mail($notifyEmail, $subject, $body, implode("\r\n", $headers), '-f' . $fromEmail);
if (!$mailSent) {
    $mailError = 'mb_send_mail returned false.';
}

// サンクスメール（自動返信）をお客さんに送信
$thanksSubject = '【AIMA】LLMO診断の個別レポートを発行しました（' . $score . '点）';
$thanksBody = implode("\n", [
    'このたびはLLMO診断をご利用いただき、誠にありがとうございます。',
    '',
    '診断結果の内訳と改善ポイントをまとめた個別レポートを発行しました。',
    '',
    '─────────────────────────',
    '診断URL: ' . $url,
    'AI引用準備度スコア: ' . $score . ' / 100',
    '─────────────────────────',
    '',
    '▼個別レポートを見る',
    $reportUrl,
    '',
    'このURLを保存しておくと、あとから診断結果を確認できます。',
    'URLを知っている方は閲覧できますので、共有先にはご注意ください。',
    '',
    'ご質問がございましたら、お気軽にご連絡ください。',
    '',
    '━━━━━━━━━━━━━━━━━━━━',
    '株式会社AIMA',
    'https://ai-and-marketing.jp',
    'info@ai-and-marketing.jp',
    '大阪府大阪市北区梅田一丁目2番2号',
    '大阪駅前第2ビル2階5-6号室',
    '━━━━━━━━━━━━━━━━━━━━',
]);

$thanksHeaders = [
    'From: AIMA <' . $fromEmail . '>',
    'Reply-To: ' . $fromEmail,
    'Content-Type: text/plain; charset=UTF-8',
];

$thanksSent = @mb_send_mail($email, $thanksSubject, $thanksBody, implode("\r\n", $thanksHeaders), '-f' . $fromEmail);
$thanksError = $thanksSent ? '' : 'Thanks mail: mb_send_mail returned false.';

if (!$mailSent && !$logWritten) {
    http_response_code(500);
    echo json_encode([
        'result' => 'error',
        'message' => 'Failed to send notification and write log.',
        'mailError' => $mailError,
        'logError' => $logError,
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode([
    'result' => 'success',
    'reportUrl' => $reportUrl,
    'score' => $score,
    'url' => $url,
    'mailSent' => $mailSent,
    'thanksSent' => $thanksSent,
    'logWritten' => $logWritten,
    'mailError' => $mailError,
    'thanksError' => $thanksError,
    'logError' => $logError,
], JSON_UNESCAPED_UNICODE);

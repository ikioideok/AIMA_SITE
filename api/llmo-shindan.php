<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'result' => 'error',
        'message' => 'Method not allowed.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

$email = trim((string)($_POST['email'] ?? ''));
$url = trim((string)($_POST['url'] ?? ''));
$timestamp = (new DateTimeImmutable('now', new DateTimeZone('Asia/Tokyo')))->format('Y/m/d H:i:s');

if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode([
        'result' => 'error',
        'message' => 'Valid email is required.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($url === '' || filter_var($url, FILTER_VALIDATE_URL) === false) {
    http_response_code(400);
    echo json_encode([
        'result' => 'error',
        'message' => 'Valid url is required.',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

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
            fputcsv($fp, ['timestamp', 'email', 'url', 'referer', 'client_ip', 'user_agent']);
        }
        $logWritten = fputcsv($fp, [$timestamp, $email, $url, $referer, $clientIp, $userAgent]) !== false;
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
$thanksSubject = '【LLMO診断】診断レポートのご依頼ありがとうございます';
$thanksBody = implode("\n", [
    'このたびはLLMO診断をご利用いただき、誠にありがとうございます。',
    '',
    '以下の内容で診断レポートのご請求を受け付けました。',
    '',
    '─────────────────────────',
    '診断URL: ' . $url,
    '─────────────────────────',
    '',
    '詳細な診断レポートは、担当者が確認のうえ',
    '通常1営業日以内にメールでお届けいたします。',
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
    'mailSent' => $mailSent,
    'thanksSent' => $thanksSent,
    'logWritten' => $logWritten,
    'mailError' => $mailError,
    'thanksError' => $thanksError,
    'logError' => $logError,
], JSON_UNESCAPED_UNICODE);

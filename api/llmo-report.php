<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');
header('Cache-Control: private, no-store');
header('X-Robots-Tag: noindex, nofollow, noarchive');

require_once __DIR__ . '/llmo-diagnosis-store.php';

function reportRespond(int $status, array $data): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    reportRespond(405, ['result' => 'error', 'code' => 'method_not_allowed']);
}

$reportId = trim((string)($_GET['id'] ?? ''));
if (!validDiagnosisToken($reportId)) {
    reportRespond(400, ['result' => 'error', 'code' => 'invalid_report']);
}

try {
    $report = loadDiagnosisReport($reportId);
    unset($report['expiresAt'], $report['createdAt'], $report['version']);
    reportRespond(200, ['result' => 'success', 'report' => $report]);
} catch (InvalidArgumentException $error) {
    reportRespond(400, ['result' => 'error', 'code' => 'invalid_report']);
} catch (RuntimeException $error) {
    $code = $error->getMessage();
    $status = in_array($code, ['report_not_found', 'report_expired'], true) ? 404 : 500;
    reportRespond($status, ['result' => 'error', 'code' => $code]);
} catch (Throwable $error) {
    error_log('LLMO report error: ' . $error->getMessage());
    reportRespond(500, ['result' => 'error', 'code' => 'report_failed']);
}

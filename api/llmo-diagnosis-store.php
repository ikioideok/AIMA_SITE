<?php
declare(strict_types=1);

const DIAGNOSIS_PENDING_TTL = 1800;
const DIAGNOSIS_REPORT_TTL = 31536000;

function diagnosisStorageRoot(): string
{
    $configured = getenv('AIMA_DIAGNOSIS_STORAGE');
    if (is_string($configured) && $configured !== '') {
        return rtrim($configured, '/');
    }

    return dirname(__DIR__, 2) . '/aima-private/llmo-diagnosis';
}
function ensureDiagnosisDirectory(string $type): string
{
    if (!in_array($type, ['pending', 'reports'], true)) {
        throw new RuntimeException('storage_failed');
    }

    $directory = diagnosisStorageRoot() . '/' . $type;
    if (!is_dir($directory) && !mkdir($directory, 0700, true) && !is_dir($directory)) {
        throw new RuntimeException('storage_failed');
    }

    return $directory;
}

function validDiagnosisToken(string $token): bool
{
    return preg_match('/\A[a-f0-9]{40}\z/', $token) === 1;
}

function diagnosisRecordPath(string $type, string $token): string
{
    if (!validDiagnosisToken($token)) {
        throw new InvalidArgumentException('invalid_token');
    }

    return ensureDiagnosisDirectory($type) . '/' . $token . '.json';
}

function writeDiagnosisRecord(string $type, string $token, array $record): void
{
    $path = diagnosisRecordPath($type, $token);
    $temporary = $path . '.' . bin2hex(random_bytes(6)) . '.tmp';
    $json = json_encode($record, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    if (!is_string($json) || file_put_contents($temporary, $json, LOCK_EX) === false) {
        @unlink($temporary);
        throw new RuntimeException('storage_failed');
    }
    @chmod($temporary, 0600);
    if (!rename($temporary, $path)) {
        @unlink($temporary);
        throw new RuntimeException('storage_failed');
    }
}

function readDiagnosisRecord(string $type, string $token): array
{
    $path = diagnosisRecordPath($type, $token);
    if (!is_file($path)) {
        throw new RuntimeException('report_not_found');
    }

    $raw = file_get_contents($path);
    $record = json_decode(is_string($raw) ? $raw : '', true);
    if (!is_array($record)) {
        throw new RuntimeException('storage_failed');
    }

    return $record;
}

function createPendingDiagnosis(array $diagnosis): string
{
    $token = bin2hex(random_bytes(20));
    $now = time();
    writeDiagnosisRecord('pending', $token, [
        'version' => 1,
        'createdAt' => $now,
        'expiresAt' => $now + DIAGNOSIS_PENDING_TTL,
        'diagnosis' => $diagnosis,
    ]);
    return $token;
}

function finalizeDiagnosisReport(string $pendingToken): array
{
    $pending = readDiagnosisRecord('pending', $pendingToken);
    if ((int)($pending['expiresAt'] ?? 0) < time()) {
        throw new RuntimeException('diagnosis_expired');
    }

    $existingReportId = (string)($pending['reportId'] ?? '');
    if (validDiagnosisToken($existingReportId)) {
        return ['id' => $existingReportId, 'report' => readDiagnosisRecord('reports', $existingReportId)];
    }

    $diagnosis = $pending['diagnosis'] ?? null;
    if (!is_array($diagnosis)) {
        throw new RuntimeException('storage_failed');
    }

    $reportId = bin2hex(random_bytes(20));
    $now = time();
    $report = $diagnosis + [
        'version' => 1,
        'createdAt' => $now,
        'expiresAt' => $now + DIAGNOSIS_REPORT_TTL,
    ];
    writeDiagnosisRecord('reports', $reportId, $report);

    $pending['reportId'] = $reportId;
    writeDiagnosisRecord('pending', $pendingToken, $pending);

    return ['id' => $reportId, 'report' => $report];
}

function loadDiagnosisReport(string $reportId): array
{
    $report = readDiagnosisRecord('reports', $reportId);
    if ((int)($report['expiresAt'] ?? 0) < time()) {
        throw new RuntimeException('report_expired');
    }
    return $report;
}

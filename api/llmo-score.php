<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');
header('Cache-Control: no-store');

require_once __DIR__ . '/llmo-diagnosis-store.php';

const MAX_HTML_BYTES = 1572864;
const MAX_REDIRECTS = 3;

function respond(int $status, array $data): void
{
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function publicIpv4ForHost(string $host): string
{
    $lowerHost = strtolower(rtrim($host, '.'));
    if ($lowerHost === 'localhost' || substr($lowerHost, -6) === '.local' || substr($lowerHost, -9) === '.internal') {
        throw new RuntimeException('private_network');
    }

    if (filter_var($lowerHost, FILTER_VALIDATE_IP)) {
        if (filter_var($lowerHost, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4 | FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) {
            throw new RuntimeException('private_network');
        }
        return $lowerHost;
    }

    if (function_exists('idn_to_ascii')) {
        $asciiHost = idn_to_ascii($lowerHost, IDNA_DEFAULT, INTL_IDNA_VARIANT_UTS46);
        if (is_string($asciiHost) && $asciiHost !== '') {
            $lowerHost = $asciiHost;
        }
    }

    $records = @dns_get_record($lowerHost, DNS_A);
    if (!is_array($records) || count($records) === 0) {
        throw new RuntimeException('site_fetch_failed');
    }

    $publicIps = [];
    foreach ($records as $record) {
        $ip = (string)($record['ip'] ?? '');
        if ($ip === '' || filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4 | FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) {
            throw new RuntimeException('private_network');
        }
        $publicIps[] = $ip;
    }

    return $publicIps[0];
}

function validatedUrlParts(string $url): array
{
    if (strlen($url) > 2048 || filter_var($url, FILTER_VALIDATE_URL) === false) {
        throw new InvalidArgumentException('invalid_url');
    }

    $parts = parse_url($url);
    $scheme = strtolower((string)($parts['scheme'] ?? ''));
    $host = (string)($parts['host'] ?? '');
    $port = isset($parts['port']) ? (int)$parts['port'] : ($scheme === 'https' ? 443 : 80);

    if (($scheme !== 'http' && $scheme !== 'https') || $host === '' || !in_array($port, [80, 443], true)) {
        throw new InvalidArgumentException('invalid_url');
    }

    if (isset($parts['user']) || isset($parts['pass'])) {
        throw new InvalidArgumentException('invalid_url');
    }

    return ['scheme' => $scheme, 'host' => $host, 'port' => $port];
}

function absoluteRedirectUrl(string $baseUrl, string $location): string
{
    $location = trim($location);
    if ($location === '') {
        throw new RuntimeException('site_fetch_failed');
    }
    if (preg_match('#^https?://#i', $location)) {
        return $location;
    }

    $base = parse_url($baseUrl);
    $scheme = (string)$base['scheme'];
    $host = (string)$base['host'];
    $port = isset($base['port']) ? ':' . (int)$base['port'] : '';

    if (substr($location, 0, 2) === '//') {
        return $scheme . ':' . $location;
    }
    if (substr($location, 0, 1) === '/') {
        return $scheme . '://' . $host . $port . $location;
    }

    $path = (string)($base['path'] ?? '/');
    $directory = preg_replace('#/[^/]*$#', '/', $path);
    return $scheme . '://' . $host . $port . $directory . $location;
}

function fetchHtml(string $initialUrl): array
{
    if (!function_exists('curl_init')) {
        throw new RuntimeException('site_fetch_failed');
    }

    $url = $initialUrl;
    for ($redirect = 0; $redirect <= MAX_REDIRECTS; $redirect++) {
        $parts = validatedUrlParts($url);
        $ip = publicIpv4ForHost($parts['host']);
        $body = '';
        $tooLarge = false;
        $responseHeaders = [];
        $curl = curl_init($url);
        if ($curl === false) {
            throw new RuntimeException('site_fetch_failed');
        }

        curl_setopt_array($curl, [
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 12,
            CURLOPT_USERAGENT => 'AIMA-LLMO-Diagnosis/1.0 (+https://ai-and-marketing.jp/)',
            CURLOPT_HTTPHEADER => ['Accept: text/html,application/xhtml+xml'],
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_RESOLVE => [$parts['host'] . ':' . $parts['port'] . ':' . $ip],
            CURLOPT_HEADERFUNCTION => function ($handle, string $line) use (&$responseHeaders): int {
                $length = strlen($line);
                $position = strpos($line, ':');
                if ($position !== false) {
                    $name = strtolower(trim(substr($line, 0, $position)));
                    $responseHeaders[$name] = trim(substr($line, $position + 1));
                }
                return $length;
            },
            CURLOPT_WRITEFUNCTION => function ($handle, string $chunk) use (&$body, &$tooLarge): int {
                $remaining = MAX_HTML_BYTES - strlen($body);
                if ($remaining <= 0) {
                    $tooLarge = true;
                    return 0;
                }
                $body .= substr($chunk, 0, $remaining);
                if (strlen($chunk) > $remaining) {
                    $tooLarge = true;
                    return 0;
                }
                return strlen($chunk);
            },
        ]);

        $ok = curl_exec($curl);
        $status = (int)curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
        $contentType = (string)curl_getinfo($curl, CURLINFO_CONTENT_TYPE);
        $curlError = curl_errno($curl);
        curl_close($curl);

        if ($ok === false && !$tooLarge) {
            if ($curlError === CURLE_OPERATION_TIMEDOUT) {
                throw new RuntimeException('timeout');
            }
            throw new RuntimeException('site_fetch_failed');
        }

        if (in_array($status, [301, 302, 303, 307, 308], true)) {
            if ($redirect >= MAX_REDIRECTS || empty($responseHeaders['location'])) {
                throw new RuntimeException('site_fetch_failed');
            }
            $url = absoluteRedirectUrl($url, $responseHeaders['location']);
            continue;
        }

        if ($status < 200 || $status >= 300 || $body === '') {
            throw new RuntimeException('site_fetch_failed');
        }
        if ($contentType !== '' && stripos($contentType, 'text/html') === false && stripos($contentType, 'application/xhtml+xml') === false) {
            throw new RuntimeException('unsupported_content');
        }

        return ['html' => $body, 'url' => $url, 'status' => $status];
    }

    throw new RuntimeException('site_fetch_failed');
}

function xpathValue(DOMXPath $xpath, string $query): string
{
    $nodes = $xpath->query($query);
    if ($nodes === false || $nodes->length === 0) {
        return '';
    }
    return trim((string)$nodes->item(0)->nodeValue);
}

function textLength(string $text): int
{
    return function_exists('mb_strlen') ? mb_strlen($text, 'UTF-8') : strlen($text);
}

function collectJsonLdTypes($value, array &$types): void
{
    if (!is_array($value)) {
        return;
    }
    if (isset($value['@type'])) {
        $found = is_array($value['@type']) ? $value['@type'] : [$value['@type']];
        foreach ($found as $type) {
            if (is_string($type)) {
                $types[] = strtolower($type);
            }
        }
    }
    foreach ($value as $child) {
        if (is_array($child)) {
            collectJsonLdTypes($child, $types);
        }
    }
}

function calculateDiagnosis(string $html, string $finalUrl, int $status): array
{
    if (!class_exists('DOMDocument')) {
        throw new RuntimeException('site_fetch_failed');
    }

    $previous = libxml_use_internal_errors(true);
    $document = new DOMDocument();
    $loaded = $document->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOWARNING | LIBXML_NOERROR | LIBXML_NONET);
    libxml_clear_errors();
    libxml_use_internal_errors($previous);
    if (!$loaded) {
        throw new RuntimeException('unsupported_content');
    }

    $xpath = new DOMXPath($document);
    $checks = [];
    $addCheck = static function (
        string $id,
        string $group,
        string $label,
        int $earned,
        int $maximum,
        string $detail,
        string $recommendation
    ) use (&$checks): void {
        $checks[] = [
            'id' => $id,
            'group' => $group,
            'label' => $label,
            'earned' => $earned,
            'max' => $maximum,
            'status' => $earned === $maximum ? 'good' : ($earned > 0 ? 'partial' : 'missing'),
            'detail' => $detail,
            'recommendation' => $recommendation,
        ];
    };

    $isHttps = stripos($finalUrl, 'https://') === 0;
    $addCheck('https', 'connection', 'HTTPS', $isHttps ? 10 : 0, 10,
        $isHttps ? 'HTTPSで安全に公開されています。' : 'HTTPSで公開されていません。',
        'サイト全体をHTTPSに統一し、HTTPからHTTPSへ転送しましょう。');
    $isHealthy = $status >= 200 && $status < 300;
    $addCheck('http_status', 'connection', 'ページの表示状態', $isHealthy ? 10 : 0, 10,
        $isHealthy ? '外部から正常にページを読み込めました。' : 'ページを正常に読み込めませんでした。',
        '外部からページが正常に表示できる状態か、サーバー設定を確認しましょう。');

    $title = xpathValue($xpath, '//title');
    $titleLength = textLength($title);
    $titleOk = $titleLength >= 8 && $titleLength <= 70;
    $addCheck('title', 'basics', 'ページタイトル', $titleOk ? 8 : 0, 8,
        $titleOk ? '内容を説明できる長さのタイトルがあります。' : 'タイトルが未設定、または長さが適切ではありません。',
        'ページの内容が伝わる8〜70文字程度のタイトルに整えましょう。');

    $description = xpathValue($xpath, "//meta[translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='description']/@content");
    $descriptionLength = textLength($description);
    $descriptionOk = $descriptionLength >= 50 && $descriptionLength <= 180;
    $addCheck('description', 'basics', 'ページの説明文', $descriptionOk ? 8 : 0, 8,
        $descriptionOk ? '内容を要約した説明文があります。' : '説明文が未設定、または長さが適切ではありません。',
        'ページの要点が伝わる50〜180文字程度の説明文を設定しましょう。');

    $hasCanonical = xpathValue($xpath, "//link[contains(concat(' ', translate(@rel,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), ' '), ' canonical ')]/@href") !== '';
    $addCheck('canonical', 'basics', '正規URL', $hasCanonical ? 5 : 0, 5,
        $hasCanonical ? '正規URLが指定されています。' : '正規URLの指定が見つかりません。',
        'canonicalタグで、このページの正式なURLを明示しましょう。');
    $hasLang = xpathValue($xpath, '//html/@lang') !== '';
    $addCheck('language', 'basics', 'ページの言語', $hasLang ? 3 : 0, 3,
        $hasLang ? 'ページの言語が指定されています。' : 'ページの言語指定が見つかりません。',
        'htmlタグにlang="ja"など、ページの言語を指定しましょう。');

    $robots = strtolower(xpathValue($xpath, "//meta[translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='robots']/@content"));
    $isIndexable = strpos($robots, 'noindex') === false;
    $addCheck('indexable', 'publishing', '検索・取得の公開設定', $isIndexable ? 4 : 0, 4,
        $isIndexable ? 'noindexは設定されていません。' : 'noindexが設定されています。',
        '公開したいページであれば、noindex設定を外しましょう。');

    $h1Nodes = $xpath->query('//h1');
    $h1Ok = $h1Nodes !== false && $h1Nodes->length === 1 && trim((string)$h1Nodes->item(0)->textContent) !== '';
    $addCheck('h1', 'content', '主見出し（H1）', $h1Ok ? 6 : 0, 6,
        $h1Ok ? '内容を示すH1が1つあります。' : 'H1がない、空、または複数あります。',
        'ページの主題を示すH1見出しを1つだけ設定しましょう。');
    $h2Nodes = $xpath->query('//h2');
    $h2Ok = $h2Nodes !== false && $h2Nodes->length >= 2;
    $addCheck('h2', 'content', '中見出し（H2）', $h2Ok ? 4 : 0, 4,
        $h2Ok ? '内容を整理するH2が複数あります。' : '内容を整理するH2が不足しています。',
        '主な話題ごとにH2見出しを置き、情報のまとまりを明確にしましょう。');

    $textNodes = $xpath->query('//body//text()[not(ancestor::script) and not(ancestor::style) and not(ancestor::noscript)]');
    $visibleText = '';
    if ($textNodes !== false) {
        foreach ($textNodes as $textNode) {
            $visibleText .= ' ' . trim((string)$textNode->nodeValue);
        }
    }
    $visibleText = preg_replace('/\s+/u', ' ', $visibleText) ?? '';
    $visibleLength = textLength($visibleText);
    $contentPoints = $visibleLength >= 1500 ? 10 : ($visibleLength >= 700 ? 5 : 0);
    $addCheck('visible_content', 'content', '本文の情報量', $contentPoints, 10,
        $contentPoints === 10 ? '判断材料になる十分な本文があります。' : ($contentPoints === 5 ? '本文はありますが、情報量を増やせます。' : 'AIが判断できる本文が不足しています。'),
        'サービス内容、対象者、特徴、実績、よくある質問などを具体的な文章で補いましょう。');

    $jsonLdNodes = $xpath->query("//script[translate(@type,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='application/ld+json']");
    $validJsonLd = false;
    $types = [];
    if ($jsonLdNodes !== false) {
        foreach ($jsonLdNodes as $node) {
            $decoded = json_decode(trim((string)$node->textContent), true);
            if (is_array($decoded)) {
                $validJsonLd = true;
                collectJsonLdTypes($decoded, $types);
            }
        }
    }
    $types = array_values(array_unique($types));
    $hasOrganization = count(array_intersect($types, ['organization', 'localbusiness', 'corporation'])) > 0;
    $hasFaq = in_array('faqpage', $types, true);
    $hasContentType = count(array_intersect($types, ['article', 'blogposting', 'service', 'product', 'website'])) > 0;
    $addCheck('json_ld', 'structured_data', '構造化データの形式', $validJsonLd ? 8 : 0, 8,
        $validJsonLd ? '読み取れるJSON-LDがあります。' : '読み取れるJSON-LDが見つかりません。',
        'ページの情報をJSON-LD形式の構造化データでも明示しましょう。');
    $addCheck('organization_schema', 'structured_data', '会社・運営者情報', $hasOrganization ? 7 : 0, 7,
        $hasOrganization ? '会社・運営者を示す構造化データがあります。' : '会社・運営者を示す構造化データが見つかりません。',
        'Organizationなどの構造化データで、会社名・URL・連絡先を明示しましょう。');
    $addCheck('faq_schema', 'structured_data', 'よくある質問', $hasFaq ? 7 : 0, 7,
        $hasFaq ? 'FAQPageの構造化データがあります。' : 'FAQPageの構造化データが見つかりません。',
        '利用者のよくある質問と回答を掲載し、FAQPageの構造化データを追加しましょう。');
    $addCheck('content_schema', 'structured_data', 'ページ種類の明示', $hasContentType ? 5 : 0, 5,
        $hasContentType ? '記事・サービスなどのページ種類が明示されています。' : 'ページの種類を示す構造化データが見つかりません。',
        'Service、Article、WebSiteなど、内容に合う構造化データを追加しましょう。');

    $ogTitle = xpathValue($xpath, "//meta[translate(@property,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='og:title']/@content");
    $ogDescription = xpathValue($xpath, "//meta[translate(@property,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='og:description']/@content");
    $ogImage = xpathValue($xpath, "//meta[translate(@property,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='og:image']/@content");
    $ogpOk = $ogTitle !== '' && $ogDescription !== '' && $ogImage !== '';
    $addCheck('ogp', 'sharing', 'OGP設定', $ogpOk ? 5 : 0, 5,
        $ogpOk ? '共有時のタイトル・説明・画像が揃っています。' : 'OGPのタイトル・説明・画像が揃っていません。',
        'og:title、og:description、og:imageを設定しましょう。');

    $groupDefinitions = [
        'connection' => ['label' => '接続・安全性', 'max' => 20],
        'basics' => ['label' => 'ページ基本情報', 'max' => 24],
        'publishing' => ['label' => '公開設定', 'max' => 4],
        'content' => ['label' => '見出し・本文', 'max' => 20],
        'structured_data' => ['label' => '構造化データ', 'max' => 27],
        'sharing' => ['label' => '共有設定', 'max' => 5],
    ];
    $breakdown = [];
    foreach ($groupDefinitions as $groupId => $definition) {
        $earned = 0;
        foreach ($checks as $check) {
            if ($check['group'] === $groupId) $earned += (int)$check['earned'];
        }
        $breakdown[] = [
            'id' => $groupId,
            'label' => $definition['label'],
            'earned' => $earned,
            'max' => $definition['max'],
        ];
    }

    $score = array_sum(array_column($checks, 'earned'));
    $improvements = array_values(array_filter($checks, static fn(array $check): bool => $check['earned'] < $check['max']));
    usort($improvements, static function (array $left, array $right): int {
        return (($right['max'] - $right['earned']) <=> ($left['max'] - $left['earned']));
    });
    $improvements = array_slice(array_map(static function (array $check): array {
        return ['id' => $check['id'], 'label' => $check['label'], 'text' => $check['recommendation']];
    }, $improvements), 0, 3);

    $strengths = array_slice(array_map(static function (array $check): array {
        return ['id' => $check['id'], 'label' => $check['label'], 'text' => $check['detail']];
    }, array_values(array_filter($checks, static fn(array $check): bool => $check['status'] === 'good'))), 0, 3);

    return [
        'url' => $finalUrl,
        'siteName' => $title !== '' ? $title : (string)(parse_url($finalUrl, PHP_URL_HOST) ?? $finalUrl),
        'score' => max(0, min(100, $score)),
        'breakdown' => $breakdown,
        'checks' => $checks,
        'strengths' => $strengths,
        'improvements' => $improvements,
        'checkedAt' => (new DateTimeImmutable('now', new DateTimeZone('Asia/Tokyo')))->format(DateTimeInterface::ATOM),
    ];
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(405, ['result' => 'error', 'code' => 'method_not_allowed']);
}

$raw = file_get_contents('php://input');
$payload = json_decode(is_string($raw) ? $raw : '', true);
$url = trim((string)(is_array($payload) ? ($payload['url'] ?? '') : ''));

try {
    validatedUrlParts($url);
    $page = fetchHtml($url);
    $diagnosis = calculateDiagnosis($page['html'], $page['url'], $page['status']);
    $diagnosisToken = createPendingDiagnosis($diagnosis);
    respond(200, [
        'result' => 'success',
        'score' => $diagnosis['score'],
        'url' => $diagnosis['url'],
        'checkedAt' => $diagnosis['checkedAt'],
        'diagnosisToken' => $diagnosisToken,
    ]);
} catch (InvalidArgumentException $error) {
    respond(400, ['result' => 'error', 'code' => $error->getMessage()]);
} catch (RuntimeException $error) {
    $code = $error->getMessage();
    $status = $code === 'private_network' ? 400 : ($code === 'timeout' ? 504 : 422);
    respond($status, ['result' => 'error', 'code' => $code]);
} catch (Throwable $error) {
    error_log('LLMO score error: ' . $error->getMessage());
    respond(500, ['result' => 'error', 'code' => 'site_fetch_failed']);
}

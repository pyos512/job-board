# ============================================================
#  무설치 정적 웹서버 (Windows PowerShell HttpListener)
#  사용: powershell -File tools\serve.ps1 [port]
#  - job-board 폴더를 http://localhost:<port> 로 서빙
#  - 배포 환경과 동일한 보안 헤더(CSP 등) 적용
# ============================================================
# $Port / $Root 는 호출측(-Command 부트스트랩)에서 미리 지정될 수 있음
$ErrorActionPreference = 'Stop'
if (-not $Port) { $Port = 8123 }
if (-not $Root) {
  if ($PSCommandPath) { $Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }
  else { $Root = (Get-Location).Path }
}

$mime = @{
  '.html'='text/html; charset=utf-8'; '.js'='application/javascript; charset=utf-8';
  '.css'='text/css; charset=utf-8'; '.json'='application/json; charset=utf-8';
  '.svg'='image/svg+xml'; '.ico'='image/x-icon'; '.png'='image/png'; '.txt'='text/plain; charset=utf-8';
  '.woff2'='font/woff2'; '.map'='application/json'
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "Serving $Root  ->  http://localhost:$Port/  (Ctrl+C to stop)"

while ($listener.IsListening) {
  try {
    $ctx = $listener.GetContext()
    $req = $ctx.Request; $res = $ctx.Response
    $res.KeepAlive = $false                 # 단일 스레드 서버 — 연결 누적 방지
    $res.Headers['Connection'] = 'close'
    $rel = [System.Uri]::UnescapeDataString($req.Url.AbsolutePath.TrimStart('/'))
    if ([string]::IsNullOrWhiteSpace($rel)) { $rel = 'index.html' }
    # 경로 탈출 방지
    $full = [System.IO.Path]::GetFullPath((Join-Path $Root $rel))
    if (-not $full.StartsWith([System.IO.Path]::GetFullPath($Root), [StringComparison]::OrdinalIgnoreCase)) {
      $res.StatusCode = 403; $res.Close(); continue
    }
    if (Test-Path $full -PathType Container) { $full = Join-Path $full 'index.html' }

    # 보안 헤더 (배포 환경과 동일)
    $res.Headers['X-Content-Type-Options'] = 'nosniff'
    $res.Headers['X-Frame-Options'] = 'DENY'
    $res.Headers['Referrer-Policy'] = 'no-referrer'
    $res.Headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), interest-cohort=()'
    $res.Headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'"

    if (Test-Path $full -PathType Leaf) {
      $ext = [System.IO.Path]::GetExtension($full).ToLower()
      $res.ContentType = $(if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'application/octet-stream' })
      if ($ext -eq '.json' -or $ext -eq '.js') { $res.Headers['Cache-Control'] = 'no-store' }
      $bytes = [System.IO.File]::ReadAllBytes($full)
      $res.ContentLength64 = $bytes.Length
      $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $res.StatusCode = 404
      $b = [System.Text.Encoding]::UTF8.GetBytes('404 Not Found')
      $res.OutputStream.Write($b, 0, $b.Length)
    }
    $res.Close()
  } catch {
    try { $ctx.Response.StatusCode = 500; $ctx.Response.Close() } catch {}
  }
}

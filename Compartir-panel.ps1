$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$origin = 'http://127.0.0.1:8000'
$script:publicIpFamily = '-4'
function Get-PublicContent([string]$Uri) {
    # Algunas redes anuncian IPv6 aunque la salida no funciona. Probar ambas
    # familias sin depender de la espera larga del cliente HTTP de Windows.
    foreach ($family in @($script:publicIpFamily, $(if ($script:publicIpFamily -eq '-4') { '-6' } else { '-4' }))) {
        $result = & curl.exe $family --silent --fail --location --max-redirs 3 --connect-timeout 3 --max-time 8 --header 'Accept: application/dns-json, application/json, text/html' $Uri 2>$null
        if ($LASTEXITCODE -eq 0) { $script:publicIpFamily = $family; return ($result -join "`n") }
    }
    throw "No responde por HTTPS: $Uri"
}
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) {
    foreach ($candidate in @("${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe")) {
        if (Test-Path -LiteralPath $candidate) { $cloudflared = $candidate; break }
    }
}
if (-not $cloudflared) { throw 'Instala cloudflared: winget install --id Cloudflare.cloudflared' }
try {
    $status = Invoke-RestMethod "$origin/auth/status" -TimeoutSec 5
} catch {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'No encuentro Python del proyecto. Ejecuta herramientas\Iniciar panel.bat.' }
    $panelLogs = Join-Path $PSScriptRoot 'logs'
    New-Item -ItemType Directory -Path $panelLogs -Force | Out-Null
    $panelStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $panelLogs "panel-$panelStamp-out.log") -RedirectStandardError (Join-Path $panelLogs "panel-$panelStamp-error.log") | Out-Null
    $status = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { $status = Invoke-RestMethod "$origin/auth/status" -TimeoutSec 2; break } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $status) { throw "El panel no responde. Revisa los registros en $panelLogs" }
}
if (-not $status.configurado) { throw 'Configura primero las tres cuentas del panel antes de compartirlo.' }
$logs = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$log = Join-Path $logs "cloudflare-$stamp.log"
$stdout = Join-Path $logs "cloudflare-$stamp-out.log"
$stderr = Join-Path $logs "cloudflare-$stamp-error.log"
$linkFile = Join-Path $logs 'enlace-publico.txt'
$shortcut = Join-Path $PSScriptRoot 'ENLACE PUBLICO.url'
$ownerFile = Join-Path $logs 'propietario-enlace.txt'
# Cada proceso modifica el enlace compartido solo mientras es su propietario.
# Un tunel viejo que se cierra no debe borrar la URL del nuevo.
Set-Content -LiteralPath $ownerFile -Value $stamp
Set-Content -LiteralPath $linkFile -Value 'El enlace nuevo todavia no esta verificado.'
if (Test-Path -LiteralPath $shortcut) { Set-Content -LiteralPath $shortcut -Value "[InternetShortcut]`r`nURL=http://127.0.0.1:8000/" }
$tunnel = $null
try {
    # HTTP/2 evita depender de UDP/QUIC en redes que lo bloquean.
    $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @('tunnel','--protocol','http2','--edge-ip-version','auto','--url',$origin,'--logfile',$log) -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Write-Host 'Conectando con Cloudflare y comprobando el acceso publico...'
    $deadline = (Get-Date).AddSeconds(120)
    $publicUrl = $null
    $verified = $false
    $dnsVerified = $false
    while ((Get-Date) -lt $deadline) {
        if ($tunnel.HasExited) { throw "Cloudflare se detuvo. Revisa $log y $stderr" }
        $content = (@($log,$stdout,$stderr) | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Content -LiteralPath $_ -Raw }) -join "`n"
        $match = [regex]::Match($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) {
            $publicUrl = $match.Value
            if (-not $dnsVerified) {
                $hostname = ([uri]$publicUrl).DnsSafeHost
                # DNS publico por HTTPS: evita dar por bueno un nombre que solo
                # resuelve en la cache de esta PC. No prueba cada red del mundo.
                foreach ($resolver in @("https://dns.google/resolve?name=$hostname&type=A", "https://cloudflare-dns.com/dns-query?name=$hostname&type=A")) {
                    try {
                        $dns = (Get-PublicContent $resolver) | ConvertFrom-Json
                        if ($dns.Status -eq 0 -and @($dns.Answer | Where-Object { $_.type -eq 1 }).Count -gt 0) { $dnsVerified = $true; break }
                    } catch { }
                }
            }
            try {
                $response = (Get-PublicContent "$publicUrl/auth/status") | ConvertFrom-Json
                $page = Get-PublicContent "$publicUrl/"
                if ($dnsVerified -and $response.configurado -eq $true -and $page -match 'Dely Drinks') { $verified = $true; break }
            } catch { }
        }
        Start-Sleep -Seconds 2
    }
    if (-not $verified) { throw "El enlace publico no respondio en 120 segundos. URL: $publicUrl. Revisa $log y $stderr. La red debe permitir salida TCP al puerto 7844." }
    Set-Content -LiteralPath $linkFile -Value $publicUrl
    Set-Content -LiteralPath $shortcut -Value "[InternetShortcut]`r`nURL=$publicUrl"
    try { Set-Clipboard -Value $publicUrl } catch { }
    Write-Host "`nENLACE NUEVO (HTTPS Y DNS PUBLICO COMPROBADOS): $publicUrl" -ForegroundColor Green
    Write-Host "Guardado en: $linkFile"
    Write-Host 'El enlace se copio al portapapeles. Pegalo con Ctrl+V para compartirlo.'
    Write-Host 'Puede abrirse desde distintas IP y redes; cada usuario inicia sesion en el panel.'
    Write-Host 'Si una red devuelve error DNS o bloquea trycloudflare.com, generar otra URL no garantiza resolverlo.'
    Write-Host 'Cada nueva apertura genera otra URL. Comparte siempre la ultima.'
    Write-Host 'Abri este enlace HTTPS desde otro equipo o desde el celular con datos moviles.'
    Write-Host 'Deja esta ventana y el panel abiertos. Ctrl+C detiene este tunel.'
    $fallos = 0
    while (-not $tunnel.HasExited) {
        Start-Sleep -Seconds 20
        if ((Get-Content -LiteralPath $ownerFile -Raw).Trim() -ne $stamp) { break }
        try {
            $check = (Get-PublicContent "$publicUrl/auth/status") | ConvertFrom-Json
            if ($check.configurado -ne $true) { throw 'Respuesta inesperada del panel' }
            if ($fallos -gt 0) { Write-Host "Conexion recuperada: $publicUrl" -ForegroundColor Green }
            $fallos = 0
            Set-Content -LiteralPath $linkFile -Value $publicUrl
        } catch {
            $fallos++
            if ($fallos -ge 3) {
                Write-Host "No puedo confirmar el acceso publico. Cloudflare intenta reconectarse. Revisa internet y el panel. URL: $publicUrl" -ForegroundColor Yellow
                Set-Content -LiteralPath $linkFile -Value "Acceso sin confirmar. Ultima URL: $publicUrl"
            }
        }
    }
    throw "El tunel se desconecto. Revisa $log y $stderr y volve a ejecutar el iniciador."
} finally {
    if ($tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    if ((Get-Content -LiteralPath $ownerFile -Raw).Trim() -eq $stamp) {
        Set-Content -LiteralPath $linkFile -Value 'Tunel detenido. Ejecuta Compartir panel por internet.bat para obtener un enlace nuevo.'
        Set-Content -LiteralPath $shortcut -Value "[InternetShortcut]`r`nURL=http://127.0.0.1:8000/"
    }
}


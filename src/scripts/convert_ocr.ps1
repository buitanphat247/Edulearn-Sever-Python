
param ([string]$inputPath, [string]$outputPath)
try {
    Add-Type -AssemblyName System.Drawing
    if (-not (Test-Path $inputPath)) { exit 1 }
    $img = [System.Drawing.Image]::FromFile($inputPath)
    
    # Target clearer resolution (approx 1024px width for better OCR)
    # User requested clarity, so we prefer upscaling or maintaining high/300 DPI
    
    $scale = 1.0
    if ($img.Width -lt 1024) { $scale = 1024 / $img.Width }
    if ($img.Width -gt 2048) { $scale = 2048 / $img.Width } # Cap at 2048 to avoid huge tokens
    
    $newW = [int]($img.Width * $scale)
    $newH = [int]($img.Height * $scale)
    
    if ($newW -lt 1) { $newW = 1 }
    $bmp = New-Object System.Drawing.Bitmap($newW, $newH)
    $bmp.SetResolution(300, 300) # Increase DPI for clarity
    
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::White)
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    
    $g.DrawImage($img, 0, 0, $newW, $newH)
    $bmp.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose(); $img.Dispose()
    Write-Host "Success"
} catch { exit 1 }

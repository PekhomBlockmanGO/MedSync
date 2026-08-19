$content = Get-Content -Path 'c:\Users\Jyosim\Downloads\CoreFour\frontend\app.html' -Raw
$start = $content.IndexOf('<div id="view-subscription"')
$end = $content.IndexOf('</main>', $start)
$prefix = $content.Substring(0, $start)
$div = $content.Substring($start, $content.IndexOf(">", $start) - $start + 1)
$suffix = "
    </div>
        " + $content.Substring($end)
$newContent = $prefix + $div + $suffix
Set-Content -Path 'c:\Users\Jyosim\Downloads\CoreFour\frontend\app.html' -Value $newContent -Encoding UTF8

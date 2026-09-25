param([string]$Path,[string]$Out)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[System.IO.Compression.ZipFile]::OpenRead($Path)
$entry=$zip.Entries | Where-Object { $_.FullName -eq 'word/document.xml' }
$sr=New-Object System.IO.StreamReader($entry.Open(),[System.Text.Encoding]::UTF8)
$xmlText=$sr.ReadToEnd(); $sr.Close(); $zip.Dispose()
$xml=New-Object System.Xml.XmlDocument
$xml.PreserveWhitespace=$true
$xml.LoadXml($xmlText)
$ns=New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
$sb=New-Object System.Text.StringBuilder
$body=$xml.SelectSingleNode('//w:body',$ns)
foreach($node in $body.ChildNodes){
  if($node.LocalName -eq 'p'){
    $style=$node.SelectSingleNode('w:pPr/w:pStyle/@w:val',$ns)
    $st=$style.Value
    $txt=New-Object System.Text.StringBuilder
    foreach($r in $node.SelectNodes('.//w:t | .//w:tab | .//w:br',$ns)){
      switch($r.LocalName){ 't'{[void]$txt.Append($r.InnerText)} 'tab'{[void]$txt.Append("`t")} 'br'{[void]$txt.Append("`n")} }
    }
    $t=$txt.ToString()
    if($st -like 'Heading*' -or $st -eq 'Title'){
      $lvl = if($st -eq 'Title'){1}else{[int]($st -replace '\D','')}
      if($lvl -lt 1){$lvl=1}; if($lvl -gt 6){$lvl=6}
      [void]$sb.AppendLine(('#'*$lvl)+' '+$t)
    } elseif($t.Trim().Length -eq 0){ [void]$sb.AppendLine('') }
    else { [void]$sb.AppendLine($t) }
    [void]$sb.AppendLine('')
  }
  elseif($node.LocalName -eq 'tbl'){
    [void]$sb.AppendLine('')
    foreach($tr in $node.SelectNodes('w:tr',$ns)){
      $cells=@()
      foreach($tc in $tr.SelectNodes('w:tc',$ns)){
        $ct=($tc.SelectNodes('.//w:t',$ns) | ForEach-Object { $_.InnerText }) -join ''
        $cells += ($ct -replace '\|','/')
      }
      [void]$sb.AppendLine('| '+($cells -join ' | ')+' |')
    }
    [void]$sb.AppendLine('')
  }
}
$utf8=New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($Out,$sb.ToString(),$utf8)
"WROTE $Out  ($($sb.Length) chars)"

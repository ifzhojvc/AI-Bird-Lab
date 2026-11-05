$ports = @(8000, 5100, 5173, 8081, 1433)
foreach ($port in $ports) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
    [PSCustomObject]@{ Port = $port; Status = if ($listeners.Count) { 'Зайнятий' } else { 'Вільний' }; ProcessId = ($listeners.OwningProcess | Select-Object -Unique) -join ',' }
}

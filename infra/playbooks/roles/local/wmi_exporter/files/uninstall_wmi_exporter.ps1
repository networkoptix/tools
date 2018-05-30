$app = Get-WmiObject -Class Win32_Product -Filter "Name = 'WMI exporter'"
$app.Uninstall()
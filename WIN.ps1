Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "My PowerShell GUI"
$form.Size = New-Object System.Drawing.Size(300, 180)
$form.StartPosition = "CenterScreen"
$label = New-Object System.Windows.Forms.Label
$label.Text = "Click the button"
$label.Location = New-Object System.Drawing.Point(20, 20)
$label.AutoSize = $true
$form.Controls.Add($label)
$button = New-Object System.Windows.Forms.Button
$button.Text = "Button"
$button.Location = New-Object System.Drawing.Point(20, 60)
$button.Add_Click({
    $label.Text = "Button Clicked!"
})
$form.Controls.Add($button)
$form.ShowDialog() | Out-Null
$form.Dispose()

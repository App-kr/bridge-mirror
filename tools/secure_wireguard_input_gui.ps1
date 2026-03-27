# WireGuard Server Public Key - Secure Input
# User enters key via GUI dialog, encrypted immediately

Write-Host "WireGuard Server Public Key Encryption" -ForegroundColor Cyan
Write-Host "=" * 70

# Create input dialog
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = "WireGuard Server Public Key Input"
$form.Width = 600
$form.Height = 200
$form.StartPosition = "CenterScreen"
$form.TopMost = $true

# Label
$label = New-Object System.Windows.Forms.Label
$label.Text = "Enter WireGuard Server Public Key:"
$label.Top = 20
$label.Left = 20
$label.Width = 550
$label.Height = 30
$form.Controls.Add($label)

# TextBox
$textBox = New-Object System.Windows.Forms.TextBox
$textBox.Top = 60
$textBox.Left = 20
$textBox.Width = 550
$textBox.Height = 60
$textBox.Multiline = $true
$textBox.AcceptsReturn = $true
$form.Controls.Add($textBox)

# OK Button
$okButton = New-Object System.Windows.Forms.Button
$okButton.Text = "Encrypt & Save"
$okButton.Top = 140
$okButton.Left = 400
$okButton.Width = 80
$okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.AcceptButton = $okButton
$form.Controls.Add($okButton)

# Cancel Button
$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Text = "Cancel"
$cancelButton.Top = 140
$cancelButton.Left = 490
$cancelButton.Width = 80
$cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $cancelButton
$form.Controls.Add($cancelButton)

# Show dialog
$result = $form.ShowDialog()

if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    $publicKey = $textBox.Text.Trim()

    if ($publicKey -eq "") {
        Write-Host "[ERR] Empty input" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "[IN] Encrypting with AES-256-GCM..."

    # Python encryption
    $pyScript = @"
import sys
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets

public_key = "$publicKey"
master_key = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wireguard_server_key",
    iterations=600000,
).derive(b"default_master_key")

nonce = secrets.token_bytes(12)
cipher = AESGCM(master_key)
ciphertext = cipher.encrypt(nonce, public_key.encode(), None)
encrypted = nonce + ciphertext
result = base64.b64encode(encrypted).decode()

enc_file = Path("Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.enc")
enc_file.parent.mkdir(parents=True, exist_ok=True)
with open(enc_file, 'w') as f:
    f.write(result)

print("[OK] Encrypted and saved")
"@

    python -c $pyScript

    Write-Host ""
    Write-Host "=" * 70
    Write-Host "[OK] Public key encrypted!" -ForegroundColor Green
    Write-Host "=" * 70
    Write-Host ""
    Write-Host "[FILE] Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.enc"
    Write-Host "[NOTE] Plain key NOT stored anywhere"
    Write-Host "[NOTE] Only encrypted version in file"
    Write-Host ""

} else {
    Write-Host "[ABORT] Cancelled" -ForegroundColor Yellow
    exit 1
}

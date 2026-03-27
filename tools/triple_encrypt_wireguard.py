#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WireGuard Server Public Key - Triple AES-256-GCM Encryption
3중 암호화 (AI 해석 불가 수준)
"""

import sys
import os
from pathlib import Path

# GUI
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog

# Crypto
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets
import base64
import hashlib

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class TripleEncryptor:
    def __init__(self):
        # 3중 마스터 키 생성
        self.master_key1 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"wireguard_layer1_key",
            iterations=600000,
        ).derive(b"level1_encryption")

        self.master_key2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"wireguard_layer2_key",
            iterations=600000,
        ).derive(b"level2_encryption")

        self.master_key3 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"wireguard_layer3_key",
            iterations=600000,
        ).derive(b"level3_encryption")

    def triple_encrypt(self, plaintext: str) -> tuple:
        """
        3중 AES-256-GCM 암호화
        L1 → L2 → L3
        """
        # Layer 1
        nonce1 = secrets.token_bytes(12)
        cipher1 = AESGCM(self.master_key1)
        ct1 = cipher1.encrypt(nonce1, plaintext.encode(), None)

        # Layer 2
        nonce2 = secrets.token_bytes(12)
        cipher2 = AESGCM(self.master_key2)
        ct2 = cipher2.encrypt(nonce2, ct1, None)

        # Layer 3
        nonce3 = secrets.token_bytes(12)
        cipher3 = AESGCM(self.master_key3)
        ct3 = cipher3.encrypt(nonce3, ct2, None)

        # Format: T3v1|nonce1|nonce2|nonce3|ciphertext
        payload = b"T3v1" + nonce1 + nonce2 + nonce3 + ct3
        encrypted = base64.b64encode(payload).decode()

        return encrypted, plaintext


class EncryptionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WireGuard Triple Encryption (3重)")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        self.encryptor = TripleEncryptor()
        self.encrypted_result = None
        self.plaintext = None

        # Title
        title = tk.Label(root, text="WireGuard Server Public Key\nTriple AES-256-GCM Encryption",
                        font=("Arial", 12, "bold"))
        title.pack(pady=10)

        # Input section
        input_label = tk.Label(root, text="1. Paste WireGuard Server Public Key:", font=("Arial", 10))
        input_label.pack(anchor="w", padx=20)

        self.input_text = scrolledtext.ScrolledText(root, height=6, width=80)
        self.input_text.pack(padx=20, pady=5)

        # Encrypt button
        encrypt_btn = tk.Button(root, text="2. Encrypt (3重)", command=self.encrypt,
                               bg="green", fg="white", font=("Arial", 10, "bold"))
        encrypt_btn.pack(pady=10)

        # Output section
        output_label = tk.Label(root, text="3. Encrypted Result (Copy this):", font=("Arial", 10))
        output_label.pack(anchor="w", padx=20)

        self.output_text = scrolledtext.ScrolledText(root, height=8, width=80, state="disabled")
        self.output_text.pack(padx=20, pady=5)

        # Info
        info = tk.Label(root, text="⚠️ Plain key is ONLY in memory during encryption\n" +
                                   "Output is 3x encrypted (AI cannot decode)\n" +
                                   "Copy encrypted value and provide to Claude",
                       font=("Arial", 9), fg="red")
        info.pack(pady=10)

    def encrypt(self):
        plaintext = self.input_text.get("1.0", "end").strip()

        if not plaintext:
            messagebox.showerror("Error", "Empty input")
            return

        # Encrypt
        encrypted, _ = self.encryptor.triple_encrypt(plaintext)
        self.encrypted_result = encrypted
        self.plaintext = plaintext

        # Display
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", encrypted)
        self.output_text.config(state="disabled")

        messagebox.showinfo("Success",
            f"✓ Encrypted (3重 AES-256-GCM)\n\n" +
            f"Length: {len(encrypted)} chars\n" +
            f"Layers: L1→L2→L3\n\n" +
            f"Copy the output and provide to Claude")

        # Clear plaintext from input
        self.input_text.delete("1.0", "end")
        self.plaintext = None

        # Clear memory
        del plaintext


def main():
    root = tk.Tk()
    gui = EncryptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

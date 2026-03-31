#!/usr/bin/env node
/**
 * Generate VAPID keys for Web Push Notifications
 * Usage: node scripts/generate-vapid-keys.js
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function generateVAPIDKeys() {
  console.log('🔐 VAPID Keys 생성 중...\n');

  // Generate EC P-256 key pair
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ec', {
    namedCurve: 'prime256v1',
    publicKeyEncoding: {
      type: 'spki',
      format: 'der'
    },
    privateKeyEncoding: {
      type: 'pkcs8',
      format: 'der'
    }
  });

  // Extract public key bytes (skip the first 26 bytes of DER header for prime256v1)
  // For SPKI format DER, the public key (uncompressed point) is at position 26
  const publicKeyDER = publicKey;
  const publicKeyPoint = publicKeyDER.slice(26); // 65 bytes for uncompressed P-256

  // Base64url encode the public key point
  const publicKeyB64url = publicKeyPoint
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  // Export private key in PEM format
  const privateKeyPEM = crypto
    .createPrivateKey({
      key: privateKey,
      format: 'der',
      type: 'pkcs8'
    })
    .export({ format: 'pem', type: 'pkcs8' });

  return {
    publicKey: publicKeyB64url,
    privateKeyPEM: privateKeyPEM.toString()
  };
}

function main() {
  try {
    const keys = generateVAPIDKeys();

    console.log('═'.repeat(70));
    console.log('PUBLIC KEY (클라이언트에 제공):');
    console.log('─'.repeat(70));
    console.log(keys.publicKey);

    console.log('\n' + '═'.repeat(70));
    console.log('PRIVATE KEY (서버 환경변수 — 절대 노출 금지):');
    console.log('─'.repeat(70));
    console.log(keys.privateKeyPEM);

    console.log('\n' + '═'.repeat(70));
    console.log('✅ VAPID 키 생성 완료!\n');

    // Save to JSON file
    const outputFile = path.join(__dirname, '..', 'vapid_keys.json');
    fs.writeFileSync(
      outputFile,
      JSON.stringify(
        {
          VAPID_PUBLIC_KEY: keys.publicKey,
          VAPID_PRIVATE_KEY_PEM: keys.privateKeyPEM,
          generated_at: new Date().toISOString(),
          warning: '⚠️  이 파일은 비밀입니다! .gitignore에 추가했는지 확인하세요.'
        },
        null,
        2
      )
    );

    console.log(`저장됨: ${outputFile}\n`);

    console.log('🔧 다음 단계:');
    console.log('1. Render Dashboard → "bridge" 서비스 → Environment 탭');
    console.log('2. 환경변수 추가:');
    console.log(`   VAPID_PUBLIC_KEY=${keys.publicKey}`);
    console.log(`   VAPID_PRIVATE_KEY_PEM=(위의 PRIVATE KEY 전체)`);
    console.log('3. 저장 후 "Redeploy" 클릭\n');
  } catch (error) {
    console.error('❌ 오류:', error.message);
    process.exit(1);
  }
}

main();

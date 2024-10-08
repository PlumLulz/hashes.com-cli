validalgs = {
    "0": "MD5",
    "10": "md5($plaintext.$salt)",
    "11": "Joomla < 2.5.18",
    "20": "md5($salt.$plaintext)",
    "21": "osCommerce, xt:Commerce",
    "50": "HMAC-MD5 (key = $plaintext)",
    "60": "HMAC-MD5 (key = $salt)",
    "100": "SHA1",
    "101": "nsldap, SHA-1(Base64), Netscape LDAP SHA",
    "104": "SHA1.Substr(0, 32)",
    "110": "sha1($plaintext.$salt)",
    "111": "nsldaps, SSHA-1(Base64), Netscape LDAP SSHA",
    "120": "sha1($salt.$plaintext)",
    "121": "SMF (Simple Machines Forum) > v1.1",
    "124": "Django (SHA-1)",
    "130": "sha1(utf16le($plaintext).$salt)",
    "140": "sha1($salt.utf16le($plaintext))",
    "160": "HMAC-SHA1 (key = $salt)",
    "170": "SHA1(UTF16-LE($plaintext))",
    "200": "MySQL323",
    "220": "sha1DASH sha1(--$salt--$plaintext--)",
    "221": "sha1(eMinor--$saltsha1(eMinor--$plaintext--})--})",
    "300": "MySQL4.1/MySQL5",
    "400": "phpass, phpBB3 (MD5), Joomla >= 2.5.18 (MD5), WordPress (MD5)",
    "401": "phpass(MD5($plaintext))/PHPBB3MD5",
    "500": "md5crypt, MD5 (Unix), Cisco-IOS $1$ (MD5), Cisco-IOS $1$ (MD5)",
    "900": "MD4",
    "1000": "NTLM",
    "1300": "SHA224",
    "1400": "SHA256",
    "1410": "sha256($plaintext.$salt)",
    "1420": "sha256($salt.$plaintext)",
    "1450": "HMAC-SHA256 (key = $plaintext)",
    "1451": "HMAC-SHA256($salt.$plaintext key = $secret) (hash:salt:secret)",
    "1460": "HMAC-SHA256 (key = $salt)",
    "1600": "Apache $apr1$ MD5, md5apr1, MD5 (APR)",
    "1700": "SHA512",
    "1710": "sha512($plaintext.$salt)",
    "1711": "SSHA-512(Base64), LDAP {SSHA512}",
    "1720": "sha512($salt.$plaintext)",
    "1750": "HMAC-SHA512 (key = $plaintext)",
    "1760": "HMAC-SHA512 (key = $salt)",
    "1800": "sha512crypt $6$, SHA512 (Unix)",
    "2100": "Domain Cached Credentials 2 (DCC2), MS Cache 2",
    "2500": "WPA/WPA2",
    "2501": "WPA/WPA2 PMK",
    "2600": "md5(md5($plaintext))",
    "2611": "vBulletin < v3.8.5",
    "2612": "PHPS",
    "2711": "vBulletin >= v3.8.5",
    "2811": "MyBB 1.2+, IPB2+ (Invision Power Board)",
    "3000": "LM",
    "3200": "bcrypt $2*$, Blowfish (Unix)",
    "3910": "md5(md5($plaintext).md5($salt))",
    "4110": "md5($salt.md5($plaintext.$salt))",
    "4400": "md5(sha1($plaintext))",
    "5100": "Half MD5",
    "5200": "Password Safe v3 pwsafe3",
    "5600": "NetNTLMv2",
    "6100": "Whirlpool",
    "6600": "1Password, agilekeychain",
    "6700": "AIX {ssha1}",
    "6900": "GOST R 34.11-94",
    "7100": "macOS v10.8+ (PBKDF2-SHA512)",
    "7300": "IPMI2 RAKP HMAC-SHA1",
    "7400": "sha256crypt $5$, SHA256 (Unix)",
    "7500": "Kerberos 5 AS-REQ Pre-Auth etype 23",
    "7900": "Drupal7",
    "8800": "Android FDE <= 4.3",
    "8900": "scrypt",
    "9200": "Cisco-IOS $8$ (PBKDF2-SHA256)",
    "9300": "Cisco-IOS $9$ (scrypt)",
    "9400": "MS Office 2007",
    "9500": "MS Office 2010",
    "9600": "MS Office 2013",
    "9700": "MS Office <= 2003 $0/$1, MD5 + RC4",
    "9710": "MS Office <= 2003 $0/$1, MD5 + RC4, collider #1",
    "9720": "MS Office <= 2003 $0/$1, MD5 + RC4, collider #2",
    "9800": "MS Office <= 2003 $3/$4, SHA1 + RC4",
    "9810": "MS Office <= 2003 $3, SHA1 + RC4, collider #1",
    "9820": "MS Office <= 2003 $3, SHA1 + RC4, collider #2",
    "10000": "Django (PBKDF2-SHA256)",
    "10400": "PDF 1.1 - 1.3 (Acrobat 2 - 4)",
    "10410": "PDF 1.1 - 1.3 (Acrobat 2 - 4), collider #1",
    "10420": "PDF 1.1 - 1.3 (Acrobat 2 - 4), collider #2",
    "10500": "PDF 1.4 - 1.6 (Acrobat 5 - 8)",
    "10600": "PDF 1.7 Level 3 (Acrobat 9)",
    "10700": "PDF 1.7 Level 8 (Acrobat 10 - 11)",
    "10800": "SHA384",
    "10900": "PBKDF2-HMAC-SHA256",
    "11300": "Bitcoin/Litecoin wallet.dat",
    "11600": "7-Zip",
    "11900": "PBKDF2-HMAC-MD5",
    "12000": "PBKDF2-HMAC-SHA1",
    "12001": "Atlassian (PBKDF2-HMAC-SHA1)",
    "12100": "PBKDF2-HMAC-SHA512",
    "12500": "RAR3-hp (*0* only)",
    "12700": "Blockchain, My Wallet",
    "12900": "Android FDE (Samsung DEK)",
    "13000": "RAR5",
    "13100": "Kerberos 5 TGS-REP etype 23",
    "13200": "AxCrypt",
    "13300": "AxCrypt in-memory SHA1",
    "13400": "KeePass 1 (AES/Twofish) and KeePass 2 (AES)",
    "13600": "WinZip",
    "13800": "Windows Phone 8+ PIN/plaintext",
    "13900": "OpenCart",
    "14400": "sha1(CX)",
    "14600": "LUKS",
    "14700": "iTunes backup < 10.0",
    "14800": "iTunes backup >= 10.0",
    "15200": "Blockchain, My Wallet, V2",
    "15600": "Ethereum Wallet, PBKDF2-HMAC-SHA256",
    "15700": "Ethereum Wallet, SCRYPT",
    "16200": "Apple Secure Notes",
    "16300": "Ethereum Pre-Sale Wallet, PBKDF2-HMAC-SHA256",
    "16500": "JWT (JSON Web Token)",
    "16600": "Electrum Wallet (Salt-Type 1-3)",
    "16700": "FileVault 2",
    "16800": "WPA-PMKID-PBKDF2",
    "17010": "GPG (AES-128/AES-256 (SHA-1($plaintext)))",
    "17200": "PKZIP (Compressed)",
    "17210": "PKZIP (Uncompressed)",
    "17220": "PKZIP (Compressed Multi-File)",
    "17225": "PKZIP (Mixed Multi-File)",
    "17230": "PKZIP (Compressed Multi-File Checksum-Only)",
    "17400": "SHA3-256",
    "17500": "SHA3-384",
    "17700": "Keccak-224",
    "17800": "Keccak-256",
    "17900": "Keccak-384",
    "18000": "Keccak-512",
    "18300": "Apple File System (APFS)",
    "18800": "Blockchain, My Wallet, Second (SHA256)",
    "18900": "Android Backup",
    "19500": "Ruby on Rails Restful-Authentication",
    "19600": "Kerberos 5, etype 17, TGS-REP (AES128-CTS-HMAC-SHA1-96)",
    "19700": "Kerberos 5, etype 18, TGS-REP (AES256-CTS-HMAC-SHA1-96) ",
    "19800": "Kerberos 5, etype 17, Pre-Auth",
    "19900": "Kerberos 5, etype 18, Pre-Auth",
    "20011": "DiskCryptor SHA512 + XTS 512 bit (AES/Twofish/Serpent)",
    "20012": "DiskCryptor SHA512 + XTS 1024 bit (AES-Twofish/Twofish-Serpent/Serpent-AES)",
    "20013": "DiskCryptor SHA512 + XTS 1536 bit (AES-Twofish-Serpent)",
    "20710": "sha256(sha256($plaintext).$salt)",
    "20711": "AuthMe sha256",
    "20800": "sha256(md5($plaintext))",
    "20900": "md5(sha1($plaintext).md5($plaintext).sha1($plaintext)) ",
    "21100": "sha1(md5($plaintext.$salt))",
    "21200": "md5(sha1($salt).md5($plaintext))",
    "21300": "md5($salt.sha1($salt.$plaintext))",
    "21700": "Electrum Wallet (Salt-Type 4)",
    "21800": "Electrum Wallet (Salt-Type 5)",
    "22000": "WPA-PBKDF2-PMKID+EAPOL",
    "22100": "BitLocker",
    "22300": "sha256($salt.$plaintext.$salt)",
    "22301": "Telegram client app passcode (SHA256)",
    "22500": "MultiBit Classic .key (MD5)",
    "22700": "MultiBit HD (scrypt)",
    "22911": "RSA/DSA/EC/OpenSSH Private Keys ($0$)",
    "22921": "RSA/DSA/EC/OpenSSH Private Keys ($6$)",
    "22931": "RSA/DSA/EC/OpenSSH Private Keys ($1, $3$)",
    "22941": "RSA/DSA/EC/OpenSSH Private Keys ($4$)",
    "22951": "RSA/DSA/EC/OpenSSH Private Keys ($5$)",
    "23700": "RAR3-p (Uncompressed)",
    "23800": "RAR3-p (Compressed)",
    "23900": "BestCrypt v3 Volume Encryption",
    "24300": "sha1($salt.sha1($plaintext.$salt))",
    "24410": "PKCS#8 Private Keys (PBKDF2-HMAC-SHA1 + 3DES/AES)",
    "24420": "PKCS#8 Private Keys (PBKDF2-HMAC-SHA256 + 3DES/AES)",
    "24500": "Telegram Desktop >= v2.1.14 (PBKDF2-HMAC-SHA512)",
    "25300": "MS Office 2016 - SheetProtection",
    "25600": "bcrypt(md5($plaintext))",
    "26000": "Mozilla key3.db",
    "26100": "Mozilla key4.db",
    "26600": "MetaMask Wallet",
    "26610": "MetaMask Wallet (short hash, plaintext check)",
    "27700": "MultiBit Classic .wallet (scrypt)",
    "28200": "Exodus Desktop Wallet (scrypt)",
    "28800": "Kerberos 5, etype 17, DB",
    "28900": "Kerberos 5, etype 18, DB",
    "99849": "Yescrypt $y$"
}
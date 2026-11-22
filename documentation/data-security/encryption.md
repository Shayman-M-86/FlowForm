# Encryption and key management

**Status: Current answer encryption; key hierarchy redesign is proposed.**

The platform encrypts response values before persistence. Keys and decryption privileges are more sensitive than encrypted response storage and require independently controlled access.

The proposed evolution separates encryption capability from decryption authorization and uses an explicit key hierarchy. Ideas include per-survey keys, per-session data keys and independently authorized decryption services. These are design options, not claims about current production deployment.

Document approved key sources, envelope formats, rotation procedures, disaster recovery and decryption authorization only after their implementation has been verified. Never store keys or production secrets in GitBook.

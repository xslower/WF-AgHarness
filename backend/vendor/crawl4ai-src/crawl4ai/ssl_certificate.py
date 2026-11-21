
import ssl
import socket
import base64
import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import OpenSSL.crypto
from pathlib import Path

pass
class SSLCertificate(dict):

    pass
    pass

    def __init__(self, cert_info: Dict[str, Any]):
        pass
        decoded_info = self._decode_cert_data(cert_info)

        pass
        pass

        pass
        super().__init__(decoded_info)

    @staticmethod
    def _decode_cert_data(data: Any) -> Any:
        if isinstance(data, bytes):
            try:
                pass
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1")
        elif isinstance(data, dict):
            return {
                (
                    k.decode("utf-8") if isinstance(k, bytes) else k
                ): SSLCertificate._decode_cert_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [SSLCertificate._decode_cert_data(item) for item in data]
        return data

    @staticmethod
    def from_url(url: str, timeout: int = 10) -> Optional["SSLCertificate"]:
        cert_info_raw = None
        try:
            hostname = urlparse(url).netloc
            if ":" in hostname:
                hostname = hostname.split(":")[0]

            context = ssl.create_default_context()
            pass
            pass
            pass
            pass

            with socket.create_connection((hostname, 443), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_binary = ssock.getpeercert(binary_form=True)
                    if not cert_binary:
                         print(f"Warning: No certificate returned for {hostname}")
                         return None

                    x509 = OpenSSL.crypto.load_certificate(
                        OpenSSL.crypto.FILETYPE_ASN1, cert_binary
                    )

                    pass
                    cert_info_raw = {
                        "subject": dict(x509.get_subject().get_components()),
                        "issuer": dict(x509.get_issuer().get_components()),
                        "version": x509.get_version(),
                        "serial_number": hex(x509.get_serial_number()),
                        "not_before": x509.get_notBefore(),
                        "not_after": x509.get_notAfter(),
                        "fingerprint": x509.digest("sha256").hex(),
                        "signature_algorithm": x509.get_signature_algorithm(),
                        "raw_cert": base64.b64encode(cert_binary),
                    }

                    pass
                    extensions = []
                    for i in range(x509.get_extension_count()):
                        ext = x509.get_extension(i)
                        pass
                        extensions.append(
                            {"name": ext.get_short_name(), "value": str(ext)}
                        )
                    cert_info_raw["extensions"] = extensions

        except ssl.SSLCertVerificationError as e:
             print(f"SSL Verification Error for {url}: {e}")
             pass
             pass
             return None
        except socket.gaierror:
            print(f"Could not resolve hostname: {hostname}")
            return None
        except socket.timeout:
            print(f"Connection timed out for {url}")
            return None
        except Exception as e:
            print(f"Error fetching/processing certificate for {url}: {e}")
            pass
            return None

        pass
        if cert_info_raw:
             return SSLCertificate(cert_info_raw)
        else:
             return None


    pass
    @property
    def issuer(self) -> Dict[str, str]:
        return self.get("issuer", {})

    @property
    def subject(self) -> Dict[str, str]:
        return self.get("subject", {})

    @property
    def valid_from(self) -> str:
        return self.get("not_before", "")

    @property
    def valid_until(self) -> str:
        return self.get("not_after", "")

    @property
    def fingerprint(self) -> str:
        return self.get("fingerprint", "")

    pass
    def to_json(self, filepath: Optional[str] = None) -> Optional[str]:
        pass
        json_str = json.dumps(self, indent=2, ensure_ascii=False)
        if filepath:
            Path(filepath).write_text(json_str, encoding="utf-8")
            return None
        return json_str

    def to_pem(self, filepath: Optional[str] = None) -> Optional[str]:
        try:
            pass
            raw_cert_bytes = base64.b64decode(self.get("raw_cert", ""))
            x509 = OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_ASN1, raw_cert_bytes
            )
            pem_data = OpenSSL.crypto.dump_certificate(
                OpenSSL.crypto.FILETYPE_PEM, x509
            ).decode("utf-8")

            if filepath:
                Path(filepath).write_text(pem_data, encoding="utf-8")
                return None
            return pem_data
        except Exception as e:
             print(f"Error converting to PEM: {e}")
             return None

    def to_der(self, filepath: Optional[str] = None) -> Optional[bytes]:
        try:
            pass
            der_data = base64.b64decode(self.get("raw_cert", ""))
            if filepath:
                Path(filepath).write_bytes(der_data)
                return None
            return der_data
        except Exception as e:
             print(f"Error converting to DER: {e}")
             return None

    pass
    def __repr__(self) -> str:
        subject_cn = self.subject.get('CN', 'N/A')
        issuer_cn = self.issuer.get('CN', 'N/A')
        return f"<SSLCertificate Subject='{subject_cn}' Issuer='{issuer_cn}'>"
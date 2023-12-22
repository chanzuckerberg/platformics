"""
Script to generate public/private keypair for testing
"""

from jwcrypto import jwk
from jwcrypto.common import json_decode

public_key = jwk.JWK()
private_key = jwk.JWK.generate(kty="EC", crv="P-384")
public_key.import_key(**json_decode(private_key.export_public()))
print(public_key.export_to_pem().decode("utf-8"))
print(private_key.export_to_pem(private_key=True, password=None).decode("utf-8"))

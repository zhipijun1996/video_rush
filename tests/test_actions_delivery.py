"""The public Actions check must not reveal the scoped upload capability."""
import base64
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


def test_runner_capsule_only_decrypts_with_the_matching_private_key():
    crypto = pytest.importorskip('cryptography')
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    module_spec = importlib.util.spec_from_file_location('delivery', Path(__file__).parents[1]/'tools/deliver_actions.py')
    delivery = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(delivery)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    url = 'https://example.blob.core.windows.net/artifact/one.zip?sig=fixture-capability'
    # Same Node built-in encryption used by the hosted receiver; never a real URL.
    js = '''const crypto=require('node:crypto');
    const [pub,url]=JSON.parse(process.argv[1]);
    const key=crypto.randomBytes(32), nonce=crypto.randomBytes(12);
    const c=crypto.createCipheriv('aes-256-gcm',key,nonce);
    const data=Buffer.concat([c.update(url),c.final(),c.getAuthTag()]);
    console.log(Buffer.from(JSON.stringify({key:crypto.publicEncrypt({key:pub,oaepHash:'sha256'},key).toString('base64'),nonce:nonce.toString('base64'),data:data.toString('base64')})).toString('base64'));'''
    capsule = subprocess.check_output(['node','-e',js,json.dumps([public,url])],text=True).strip()
    assert 'fixture-capability' not in base64.b64decode(capsule).decode()
    assert delivery.decrypt_capsule(capsule,private)==url
    wrong = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    with pytest.raises(ValueError):delivery.decrypt_capsule(capsule,wrong)
    payload=json.loads(base64.b64decode(capsule));payload['data']=base64.b64encode(b'changed').decode()
    with pytest.raises(Exception):delivery.decrypt_capsule(base64.b64encode(json.dumps(payload).encode()),private)

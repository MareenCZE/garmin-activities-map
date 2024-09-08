import ftplib
import json
import os.path

from cryptography.fernet import Fernet

from common import logger

FTP_CONFIG_FILENAME = '.auth/ftp_config.json'
CRYPTO_KEY = 'mMF32hspwbAhawquFRC070fczdWLb0nF3dX4fHd7R_k='


class FtpConfig:
    def __init__(self, ftp_host, ftp_user, ftp_pass, remote_path, remote_filename):
        self.host = ftp_host
        self.user = ftp_user
        self.password = ftp_pass
        self.remote_path = remote_path
        self.remote_filename = remote_filename

    @staticmethod
    def load_from_file(filename: str):
        logger.info(f"Reading FTP config from {filename}")
        with open(filename, 'r') as config_file:
            config_json = json.load(config_file)
            return FtpConfig(
                ftp_host=config_json.get('host'),
                ftp_user=config_json.get('user'),
                ftp_pass=decrypt(config_json.get('pass')),
                remote_path=config_json.get('remotePath'),
                remote_filename=config_json.get('remoteFilename')
            )


def upload_file_to_ftp(filename: str):
    if not os.path.exists(FTP_CONFIG_FILENAME):
        logger.info(f"Skipping upload to FTP - config {FTP_CONFIG_FILENAME} not found")
        return

    ftp_config = FtpConfig.load_from_file(FTP_CONFIG_FILENAME)
    try:
        logger.info(f"Going to connect to {ftp_config.host} as {ftp_config.user}")
        ftp = ftplib.FTP(ftp_config.host)
        ftp.login(user=ftp_config.user, passwd=ftp_config.password)
        ftp.cwd(ftp_config.remote_path)

        with open(filename, 'rb') as file:
            # Upload the file to the FTP server
            ftp.storbinary(f'STOR {ftp_config.remote_filename}', file)

        logger.info(f"Uploaded {filename} to FTP server {ftp.host} as {ftp_config.remote_path}/{ftp_config.remote_filename}")
    except ftplib.all_errors as e:
        logger.error("Failed to FTP the file. {0}", e)
    finally:
        ftp.quit()


def decrypt(encrypted_text):
    cipher_suite = Fernet(CRYPTO_KEY)
    decrypted_text = cipher_suite.decrypt(encrypted_text).decode()
    return decrypted_text


def encrypt(input_string):
    cipher_suite = Fernet(CRYPTO_KEY)
    encrypted_text = cipher_suite.encrypt(input_string.encode())
    return encrypted_text

# use to encrypt your password before storing it in the config json (not very secure but better than having it in plain text there)
# print(encrypt("your ftp password"))

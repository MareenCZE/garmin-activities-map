import ftplib

from cryptography.fernet import Fernet

from common import logger, config

# random key used to encrypt/decrypt FTP password
CRYPTO_KEY = 'mMF32hspwbAhawquFRC070fczdWLb0nF3dX4fHd7R_k='


class FtpConfig:
    def __init__(self, ftp_host, ftp_user, ftp_pass, remote_path, remote_filename):
        self.host = ftp_host
        self.user = ftp_user
        self.password = ftp_pass
        self.remote_path = remote_path
        self.remote_filename = remote_filename

    @staticmethod
    def create_config(config_dict):
        return FtpConfig(
            ftp_host=config_dict['ftp']['host'],
            ftp_user=config_dict['ftp']['user'],
            ftp_pass=decrypt(config_dict['ftp']['pass']),
            remote_path=config_dict['ftp']['remote-path'],
            remote_filename=config_dict['ftp']['remote-filename']
        )


def upload_file_to_ftp(filename: str):
    if not config["ftp"]["host"]:
        logger.info(f"Skipping upload to FTP - no FTP config provided")
        return

    ftp_config = FtpConfig.create_config(config)
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


def encrypt_password():
    cipher_suite = Fernet(CRYPTO_KEY)
    encrypted_text = cipher_suite.encrypt(config['ftp']['pass'].encode())
    print(encrypted_text.decode())

import ftplib
import os
from pathlib import Path
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from common import logger, config

# Per-machine key that encrypts the FTP password, generated on the first ENCRYPT_FTP_PASSWORD run.
# Lives next to the Garmin tokens (git-ignored); without it the password must be re-encrypted.
KEY_FILENAME = 'ftp.key'

PROTOCOLS = ('FTP', 'FTPS')


class FtpConfig:
    def __init__(self, ftp_host, ftp_user, ftp_pass, remote_path, remote_filename, protocol='FTPS'):
        if protocol not in PROTOCOLS:
            raise ValueError(f"Unsupported [ftp] protocol '{protocol}' - use one of {', '.join(PROTOCOLS)}")
        self.host = ftp_host
        self.user = ftp_user
        self.password = ftp_pass
        self.remote_path = remote_path
        self.remote_filename = remote_filename
        self.protocol = protocol

    @staticmethod
    def create_config(config_dict):
        return FtpConfig(
            ftp_host=config_dict['ftp']['host'],
            ftp_user=config_dict['ftp']['user'],
            ftp_pass=decrypt(config_dict['ftp']['pass']),
            remote_path=config_dict['ftp']['remote-path'],
            remote_filename=config_dict['ftp']['remote-filename'],
            protocol=config_dict['ftp'].get('protocol', 'FTPS').upper()
        )


def connect(ftp_config):
    """Open a logged-in connection; FTPS also encrypts the data channel."""
    if ftp_config.protocol == 'FTPS':
        ftp = ftplib.FTP_TLS(ftp_config.host)
        ftp.login(user=ftp_config.user, passwd=ftp_config.password)
        ftp.prot_p()
    else:
        ftp = ftplib.FTP(ftp_config.host)
        ftp.login(user=ftp_config.user, passwd=ftp_config.password)
    return ftp


def get_remote_file_info(ftp, filename):
    """Get remote file modification time and size"""
    try:
        # Get file size
        size = ftp.size(filename)

        # Get modification time
        mdtm_response = ftp.sendcmd(f'MDTM {filename}')
        # MDTM response format: "213 YYYYMMDDHHMMSS"
        timestamp_str = mdtm_response.split()[1]
        remote_mtime = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S').timestamp()

        return {'size': size, 'mtime': remote_mtime}
    except (ftplib.error_perm, ftplib.error_temp, ValueError):
        # File doesn't exist or server doesn't support MDTM/SIZE
        return None


def should_upload_file(local_file_path, remote_file_info):
    """Determine if a local file should be uploaded based on size"""
    # Size check does not work for manifest.json - it changes when there is a new activity, but its size usually remains the same
    if remote_file_info is None or local_file_path.name == 'manifest.json':
        return True

    local_stat = local_file_path.stat()
    local_size = local_stat.st_size

    # Upload if size differs
    size_differs = local_size != remote_file_info['size']

    if size_differs:
        logger.debug(f"File {local_file_path.name} needs upload: size_differs={size_differs}")
        return True

    logger.debug(f"File {local_file_path.name} is up to date, skipping")
    return False


def upload_map_with_data_to_ftp_incremental(html_filename: str):
    """Upload HTML file and JSON data files to FTP, only uploading changed files"""
    if not config["ftp"]["host"]:
        logger.info("Skipping upload to FTP - no FTP config provided")
        return

    ftp_config = FtpConfig.create_config(config)

    # Determine the output directory and data directory
    html_path = Path(html_filename)
    output_dir = html_path.parent
    data_dir = output_dir / 'data'

    if not html_path.exists():
        logger.error(f"HTML file not found: {html_filename}")
        return

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    files_uploaded = 0
    files_skipped = 0
    total_size_uploaded = 0

    ftp = None
    try:
        logger.info(f"Connecting to {ftp_config.host} as {ftp_config.user} ({ftp_config.protocol})")
        ftp = connect(ftp_config)
        ftp.cwd(ftp_config.remote_path)

        # Check and upload the main HTML file
        logger.info(f"Checking main HTML file: {html_filename}")
        remote_html_info = get_remote_file_info(ftp, ftp_config.remote_filename)

        if should_upload_file(html_path, remote_html_info):
            logger.info(f"Uploading main HTML file: {html_filename}")
            with open(html_filename, 'rb') as file:
                ftp.storbinary(f'STOR {ftp_config.remote_filename}', file)
            logger.info(f"Uploaded {html_filename} as {ftp_config.remote_filename}")
            files_uploaded += 1
            total_size_uploaded += html_path.stat().st_size
        else:
            logger.info(f"HTML file {html_filename} is up to date, skipping")
            files_skipped += 1

        # Create data directory on FTP server if it doesn't exist
        try:
            ftp.mkd('data')
            logger.info("Created 'data' directory on FTP server")
        except ftplib.error_perm as e:
            if "550" in str(e):  # Directory already exists
                logger.debug("'data' directory already exists on FTP server")
            else:
                raise e

        # Change to data directory on FTP server
        ftp.cwd('data')

        # Check and upload JSON files from the data directory
        json_files = list(data_dir.glob('*.json'))
        if not json_files:
            logger.warning(f"No JSON files found in {data_dir}")
        else:
            logger.info(f"Checking {len(json_files)} JSON files for changes")

            for json_file in json_files:
                remote_json_info = get_remote_file_info(ftp, json_file.name)

                if should_upload_file(json_file, remote_json_info):
                    logger.info(f"Uploading JSON file: {json_file.name}")
                    with open(json_file, 'rb') as file:
                        ftp.storbinary(f'STOR {json_file.name}', file)
                    logger.info(f"Uploaded {json_file.name}")
                    files_uploaded += 1
                    total_size_uploaded += json_file.stat().st_size
                else:
                    logger.info(f"JSON file {json_file.name} is up to date, skipping")
                    files_skipped += 1

        # Summary
        logger.info(f"Upload complete: {files_uploaded} files uploaded, {files_skipped} files skipped")
        if files_uploaded > 0:
            logger.info(f"Total size uploaded: {round(total_size_uploaded / 1048576, 2)} MB")
        else:
            logger.info("No files needed uploading - all files are up to date")

    except ftplib.all_errors as e:
        logger.error(f"Failed to FTP the files. {e}")
    finally:
        close_ftp(ftp)


def upload_map_with_data_to_ftp(html_filename: str):
    """Upload HTML file and associated JSON data files to FTP (full upload)"""
    if not config["ftp"]["host"]:
        logger.info("Skipping upload to FTP - no FTP config provided")
        return

    ftp_config = FtpConfig.create_config(config)

    # Determine the output directory and data directory
    html_path = Path(html_filename)
    output_dir = html_path.parent
    data_dir = output_dir / 'data'

    if not html_path.exists():
        logger.error(f"HTML file not found: {html_filename}")
        return

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    ftp = None
    try:
        logger.info(f"Connecting to {ftp_config.host} as {ftp_config.user} ({ftp_config.protocol})")
        ftp = connect(ftp_config)
        ftp.cwd(ftp_config.remote_path)

        # Upload the main HTML file
        logger.info(f"Uploading main HTML file: {html_filename}")
        with open(html_filename, 'rb') as file:
            ftp.storbinary(f'STOR {ftp_config.remote_filename}', file)
        logger.info(f"Uploaded {html_filename} as {ftp_config.remote_filename}")

        # Create data directory on FTP server if it doesn't exist
        try:
            ftp.mkd('data')
            logger.info("Created 'data' directory on FTP server")
        except ftplib.error_perm as e:
            if "550" in str(e):  # Directory already exists
                logger.info("'data' directory already exists on FTP server")
            else:
                raise e

        # Change to data directory on FTP server
        ftp.cwd('data')

        # Upload all JSON files from the data directory
        json_files = list(data_dir.glob('*.json'))
        if not json_files:
            logger.warning(f"No JSON files found in {data_dir}")
        else:
            logger.info(f"Found {len(json_files)} JSON files to upload")

            for json_file in json_files:
                logger.info(f"Uploading JSON file: {json_file.name}")
                with open(json_file, 'rb') as file:
                    ftp.storbinary(f'STOR {json_file.name}', file)
                logger.info(f"Uploaded {json_file.name}")

        # Calculate total size uploaded
        total_size = html_path.stat().st_size
        for json_file in json_files:
            total_size += json_file.stat().st_size

        logger.info(f"Successfully uploaded map with data files. Total size: {round(total_size / 1048576, 2)} MB")
        logger.info("Files uploaded:")
        logger.info(f"  - {ftp_config.remote_path}/{ftp_config.remote_filename}")
        for json_file in json_files:
            logger.info(f"  - {ftp_config.remote_path}/data/{json_file.name}")

    except ftplib.all_errors as e:
        logger.error(f"Failed to FTP the files. {e}")
    finally:
        close_ftp(ftp)


def close_ftp(ftp):
    """Quietly close an FTP connection that may be None or already broken."""
    if ftp is None:
        return
    try:
        ftp.quit()
    except ftplib.all_errors:
        pass


def clean_remote_data_directory(ftp_config):
    """Clean old JSON files from the remote data directory before uploading new ones"""
    ftp = None
    try:
        ftp = connect(ftp_config)
        ftp.cwd(ftp_config.remote_path)

        # Try to change to data directory
        try:
            ftp.cwd('data')

            # List all files in the data directory
            files = []
            ftp.retrlines('NLST', files.append)

            # Delete JSON files
            json_files_deleted = 0
            for filename in files:
                if filename.endswith('.json'):
                    try:
                        ftp.delete(filename)
                        json_files_deleted += 1
                        logger.info(f"Deleted old file: data/{filename}")
                    except ftplib.error_perm as e:
                        logger.warning(f"Could not delete {filename}: {e}")

            if json_files_deleted > 0:
                logger.info(f"Cleaned {json_files_deleted} old JSON files from remote data directory")
            else:
                logger.info("No old JSON files found to clean")

        except ftplib.error_perm:
            # Data directory doesn't exist, which is fine
            logger.info("Remote data directory doesn't exist yet")

    except ftplib.all_errors as e:
        logger.warning(f"Could not clean remote data directory: {e}")
    finally:
        close_ftp(ftp)


def upload_map_with_data_to_ftp_clean(html_filename: str):
    """Upload HTML file and JSON data files to FTP, cleaning old JSON files first"""
    if not config["ftp"]["host"]:
        logger.info("Skipping upload to FTP - no FTP config provided")
        return

    ftp_config = FtpConfig.create_config(config)

    # Clean old JSON files first
    logger.info("Cleaning old JSON files from remote server...")
    clean_remote_data_directory(ftp_config)

    # Upload new files
    upload_map_with_data_to_ftp(html_filename)


REENCRYPT_HINT = ("Put the plain-text password into [ftp] pass in config-local.toml, run with "
                  "--utility-mode ENCRYPT_FTP_PASSWORD and replace it with the printed value.")


def key_file_path():
    return Path(config['storage']['directory-token-store']) / KEY_FILENAME


def load_key(create=False):
    """Read the per-machine key; with create=True, generate it (mode 0600) if missing."""
    key_file = key_file_path()
    if key_file.exists():
        return key_file.read_bytes().strip()
    if not create:
        raise RuntimeError(f"FTP password key {key_file} not found. {REENCRYPT_HINT}")
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as file:
        file.write(key)
    logger.info(f"Generated a new FTP password key in {key_file} - back it up together with your config")
    return key


def decrypt(encrypted_text):
    cipher_suite = Fernet(load_key())
    try:
        return cipher_suite.decrypt(encrypted_text).decode()
    except InvalidToken:
        raise RuntimeError(f"FTP password cannot be decrypted with {key_file_path()}. {REENCRYPT_HINT}") from None


def encrypt_password():
    cipher_suite = Fernet(load_key(create=True))
    encrypted_text = cipher_suite.encrypt(config['ftp']['pass'].encode())
    print(encrypted_text.decode())
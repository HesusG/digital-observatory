import logging
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    gspread = None
    ServiceAccountCredentials = None


class SheetsOutput:
    def __init__(
        self,
        sheet_id: str | None = None,
        credentials_path: str | None = None,
    ):
        self.sheet_id = sheet_id if sheet_id is not None else settings.google_sheet_id
        self.credentials_path = credentials_path or str(settings.google_credentials_path)
        self._sheet = None

    @property
    def available(self) -> bool:
        if gspread is None:
            return False
        if not self.sheet_id:
            return False
        if not Path(self.credentials_path).exists():
            return False
        return True

    def _connect(self):
        if self._sheet is not None:
            return
        if not self.available:
            return

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
        client = gspread.authorize(creds)
        self._sheet = client.open_by_key(self.sheet_id).sheet1
        logger.info("Connected to Google Sheets")

    def append_row(
        self,
        title: str,
        url: str,
        source: str,
        score: int,
        summary: str = "",
        category: str = "general",
    ) -> bool:
        # Use cached connection if available, otherwise check availability before connecting
        if self._sheet is None:
            if not self.available:
                return False
            self._connect()
        if self._sheet is None:
            return False

        row = [title, url, source, score, summary, category]
        try:
            self._sheet.append_row(row)
            return True
        except gspread.exceptions.APIError:
            logger.warning("Sheets API error. Reconnecting...")
            self._sheet = None
            self._connect()
            if self._sheet:
                try:
                    self._sheet.append_row(row)
                    return True
                except Exception as e:
                    logger.error(f"Sheets retry failed: {e}")
                    return False
        except Exception as e:
            logger.error(f"Error writing to Sheets: {e}")
            return False
        return False

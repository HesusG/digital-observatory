import pytest
from unittest.mock import patch, MagicMock
from observatory.outputs.sheets import SheetsOutput


def test_sheets_unavailable_without_config():
    output = SheetsOutput(sheet_id="", credentials_path="/nonexistent.json")
    assert output.available is False


@patch("observatory.outputs.sheets.gspread")
@patch("observatory.outputs.sheets.ServiceAccountCredentials")
def test_connect_and_append(mock_creds_cls, mock_gspread):
    mock_sheet = MagicMock()
    mock_client = MagicMock()
    mock_client.open_by_key.return_value.sheet1 = mock_sheet
    mock_gspread.authorize.return_value = mock_client
    mock_creds_cls.from_json_keyfile_name.return_value = MagicMock()

    output = SheetsOutput(sheet_id="test-id", credentials_path="creds.json")

    with patch("observatory.outputs.sheets.Path.exists", return_value=True):
        output._connect()

    assert output._sheet is not None

    output.append_row("Title", "https://x.com", "Source", 8, "Summary", "scholarship")
    mock_sheet.append_row.assert_called_once_with(
        ["Title", "https://x.com", "Source", 8, "Summary", "scholarship"]
    )

"""
Reads pending return tasks from Excel and writes results back — always at the
line-item (row) level, never rolled up to the order level.
"""
from datetime import datetime
from openpyxl import load_workbook
import config


class ExcelTaskStore:
    def __init__(self, path=None, sheet_name=None):
        self.path = path or config.EXCEL_PATH
        self.sheet_name = sheet_name or config.SHEET_NAME
        self.wb = load_workbook(self.path)
        self.ws = self.wb[self.sheet_name] if self.sheet_name in self.wb.sheetnames else self.wb.active
        self._header_to_col = self._map_headers()

    def _map_headers(self):
        """Map column header text (row 1) -> column index, so row order in the
        sheet can change without breaking the script."""
        headers = {}
        for cell in self.ws[1]:
            if cell.value:
                headers[str(cell.value).strip()] = cell.column
        return headers

    def _col(self, key):
        header_text = config.COLUMNS[key]
        col = self._header_to_col.get(header_text)
        if col is None:
            raise KeyError(
                f"Expected column '{header_text}' not found in sheet headers: "
                f"{list(self._header_to_col.keys())}"
            )
        return col

    def get_pending_tasks(self):
        """Yield (row_number, task_dict) for every row whose Status is pending."""
        status_col = self._col("status")
        order_col = self._col("order_id")
        tasks = []
        for row in range(2, self.ws.max_row + 1):
            order_val = self.ws.cell(row=row, column=order_col).value
            if not order_val or not str(order_val).strip():
                continue  # skip fully blank/ghost rows entirely
            status_val = self.ws.cell(row=row, column=status_col).value
            status_val = (status_val or "").strip()
            if status_val in config.PENDING_STATUSES:
                task = {
                    "row": row,
                    "platform": self._get(row, "platform"),
                    "order_id": self._get(row, "order_id"),
                    "product_link": self._get(row, "product_link"),
                    "return_window": self._get(row, "return_window"),
                }
                tasks.append(task)
        return tasks

    def _get(self, row, key):
        return self.ws.cell(row=row, column=self._col(key)).value

    def write_result(self, row, *, return_id=None, return_status=None,
                      refund_amount=None, task_status=None, log_message=""):
        """Write the outcome back against this exact line item's row.
        Never aggregates to order level — every SKU/row gets its own outcome."""
        if return_id is not None:
            self.ws.cell(row=row, column=self._col("return_id"), value=return_id)
        if return_status is not None:
            self.ws.cell(row=row, column=self._col("return_status"), value=return_status)
        if refund_amount is not None:
            self.ws.cell(row=row, column=self._col("refund_amount"), value=refund_amount)
        if task_status is not None:
            self.ws.cell(row=row, column=self._col("status"), value=task_status)

        self.ws.cell(row=row, column=self._col("timestamp"),
                      value=datetime.now().isoformat(timespec="seconds"))
        self.ws.cell(row=row, column=self._col("log"), value=log_message)

        # Save after every row — if the script crashes mid-run, completed
        # line items are never lost or re-processed.
        self.wb.save(self.path)
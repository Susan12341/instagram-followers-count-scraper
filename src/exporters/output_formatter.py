import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd
from xml.etree.ElementTree import Element, SubElement, ElementTree

@dataclass
class OutputFormatError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message

class OutputFormatter:
    def __init__(self, output_dir: Path, base_filename: str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.base_filename = base_filename

    def _ensure_dir(self) -> None:
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _timestamp_suffix() -> str:
        return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def export(self, records: List[Dict[str, Any]], fmt: str) -> Path:
        if fmt not in {"json", "csv", "excel", "xml", "html"}:
            raise OutputFormatError(f"Unsupported format: {fmt}")

        self._ensure_dir()
        suffix = self._timestamp_suffix()

        if fmt == "json":
            path = self.output_dir / f"{self.base_filename}_{suffix}.json"
            self._to_json(records, path)
        elif fmt == "csv":
            path = self.output_dir / f"{self.base_filename}_{suffix}.csv"
            self._to_csv(records, path)
        elif fmt == "excel":
            path = self.output_dir / f"{self.base_filename}_{suffix}.xlsx"
            self._to_excel(records, path)
        elif fmt == "xml":
            path = self.output_dir / f"{self.base_filename}_{suffix}.xml"
            self._to_xml(records, path)
        else:  # html
            path = self.output_dir / f"{self.base_filename}_{suffix}.html"
            self._to_html(records, path)

        return path

    @staticmethod
    def _to_json(records: List[Dict[str, Any]], path: Path) -> None:
        logging.info("Writing JSON output to %s", path.as_posix())
        with path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_csv(records: List[Dict[str, Any]], path: Path) -> None:
        logging.info("Writing CSV output to %s", path.as_posix())
        if not records:
            # Write an empty file with just headers for consistency
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["username", "followersCount", "followingCount", "profileUrl", "timestamp"])
            return

        fieldnames = list(records[0].keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in records:
                writer.writerow(row)

    @staticmethod
    def _to_excel(records: List[Dict[str, Any]], path: Path) -> None:
        logging.info("Writing Excel output to %s", path.as_posix())
        df = pd.DataFrame(records)
        df.to_excel(path, index=False)

    @staticmethod
    def _to_xml(records: Iterable[Dict[str, Any]], path: Path) -> None:
        logging.info("Writing XML output to %s", path.as_posix())
        root = Element("profiles")
        for rec in records:
            profile_el = SubElement(root, "profile")
            for key, value in rec.items():
                field_el = SubElement(profile_el, key)
                field_el.text = str(value)

        tree = ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    @staticmethod
    def _to_html(records: List[Dict[str, Any]], path: Path) -> None:
        logging.info("Writing HTML output to %s", path.as_posix())
        headers = ["username", "followersCount", "followingCount", "profileUrl", "timestamp"]

        rows_html = ""
        for rec in records:
            row_cells = []
            for h in headers:
                value = rec.get(h, "")
                if h == "profileUrl":
                    cell = f'<td><a href="{value}" target="_blank" rel="noreferrer">{value}</a></td>'
                else:
                    cell = f"<td>{value}</td>"
                row_cells.append(cell)
            rows_html += "<tr>" + "".join(row_cells) + "</tr>\n"

        table_html = (
            "<table border='1' cellspacing='0' cellpadding='6'>\n"
            "  <thead>\n"
            "    <tr>"
            + "".join(f"<th>{h}</th>" for h in headers)
            + "</tr>\n"
            "  </thead>\n"
            "  <tbody>\n"
            f"{rows_html}"
            "  </tbody>\n"
            "</table>"
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Instagram Followers Count Export</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      padding: 16px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      max-width: 960px;
    }}
    th, td {{
      text-align: left;
    }}
    th {{
      background-color: #f4f4f4;
    }}
  </style>
</head>
<body>
  <h1>Instagram Followers Count Export</h1>
  <p>Generated at {datetime.utcnow().isoformat()}Z</p>
  {table_html}
</body>
</html>
"""
        with path.open("w", encoding="utf-8") as f:
            f.write(html)
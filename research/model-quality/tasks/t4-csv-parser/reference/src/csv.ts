// A small CSV reader. Fields may be quoted; a quoted field may hold the delimiter, newlines and
// doubled quotes ("" is one literal quote).

export interface CsvOptions {
  delimiter?: string;
}

export class CsvParser {
  readonly delimiter: string;

  constructor(options: CsvOptions = {}) {
    this.delimiter = options.delimiter ?? ",";
  }

  parse(text: string): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let field = "";
    let inQuotes = false;
    let fieldStarted = false;
    let i = 0;
    while (i < text.length) {
      const ch = text[i] as string;
      if (inQuotes) {
        if (ch === '"') {
          if (text[i + 1] === '"') {
            field += '"';
            i += 2;
            continue;
          }
          inQuotes = false;
          i += 1;
          continue;
        }
        field += ch;
        i += 1;
        continue;
      }
      if (ch === '"' && field === "" && !fieldStarted) {
        inQuotes = true;
        fieldStarted = true;
        i += 1;
        continue;
      }
      if (ch === this.delimiter) {
        row.push(field);
        field = "";
        fieldStarted = false;
        i += 1;
        continue;
      }
      if (ch === "\r" || ch === "\n") {
        if (ch === "\r" && text[i + 1] === "\n") {
          i += 1;
        }
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
        fieldStarted = false;
        i += 1;
        continue;
      }
      field += ch;
      fieldStarted = true;
      i += 1;
    }
    // The last row has no line break after it. An empty last line adds no row.
    if (fieldStarted || field !== "" || row.length > 0) {
      row.push(field);
      rows.push(row);
    }
    return rows;
  }
}

export function parseCsv(text: string, delimiter: string = ","): string[][] {
  return new CsvParser({ delimiter }).parse(text);
}

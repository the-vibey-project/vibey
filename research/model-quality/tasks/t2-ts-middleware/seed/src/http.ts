export interface Request {
  method: string;
  path: string;
  headers: Record<string, string>;
  body?: string;
}

export interface Response {
  status: number;
  body: string;
  headers: Record<string, string>;
}

export type Handler = (req: Request) => Response;

export function response(
  status: number,
  body: string,
  headers: Record<string, string> = {},
): Response {
  return { status, body, headers };
}

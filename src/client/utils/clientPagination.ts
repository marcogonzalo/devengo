export const CLIENT_PAGE_SIZE = 100;

export function buildClientsQueryPath(
  skip = 0,
  limit = CLIENT_PAGE_SIZE,
): string {
  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
  });
  return `/clients?${params.toString()}`;
}

export function hasMorePages(
  pageLength: number,
  pageSize = CLIENT_PAGE_SIZE,
): boolean {
  return pageLength === pageSize;
}

export function nextSkip(currentSkip: number, pageLength: number): number {
  return currentSkip + pageLength;
}

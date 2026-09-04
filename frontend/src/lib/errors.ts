/** Map low-level fetch failures to a user-facing string. */
export function networkErrorMessage(message: string): string {
  if (message.toLowerCase().includes("failed to fetch")) {
    return "Could not reach the API. Is it running?";
  }
  return message;
}

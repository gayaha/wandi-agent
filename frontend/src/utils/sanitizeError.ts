export function sanitizeError(error: unknown): string {
  const msg =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : '';

  const lower = msg.toLowerCase();

  if (lower.includes('401') || lower.includes('unauthorized') || lower.includes('not authenticated')) {
    return 'פג תוקף ההתחברות. נסי להתחבר מחדש.';
  }
  if (lower.includes('403') || lower.includes('forbidden')) {
    return 'אין הרשאה לפעולה זו.';
  }
  if (lower.includes('429') || lower.includes('too many')) {
    return 'יותר מדי בקשות. נסי שוב בעוד דקה.';
  }
  if (lower.includes('500') || lower.includes('internal')) {
    return 'שגיאת שרת. נסי שוב מאוחר יותר.';
  }
  if (lower.includes('failed to fetch') || lower.includes('networkerror') || lower.includes('network')) {
    return 'בעיית חיבור לשרת. בדקי את האינטרנט ונסי שוב.';
  }
  if (lower.includes('timeout') || lower.includes('aborted')) {
    return 'הבקשה לקחה יותר מדי זמן. נסי שוב.';
  }

  return 'משהו השתבש. נסי שוב.';
}

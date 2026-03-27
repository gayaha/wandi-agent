# חזרה ל-Lovable

אם הפרונט החדש לא עובד ורוצים לחזור:

## אם עדיין על branch (לפני merge ל-main):
1. git checkout main
2. git branch -D feature/self-hosted-frontend
3. זהו — הכל חזר למצב המקורי. אפס שינויים.

## אם כבר עשינו merge ל-main ו-deploy:
1. הפנה DNS חזרה ל-Lovable
2. (אופציונלי) הסר את ה-domain החדש מ-Supabase Auth Redirect URLs
3. (אופציונלי) מחק את תיקיית frontend/ אם רוצים

בשני המקרים — הבק (wandi-agent) לא נפגע כי לא שינינו בו כלום.

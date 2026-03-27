import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://zsfhcschstsxpiveqkgm.supabase.co';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

if (import.meta.env.DEV && !import.meta.env.VITE_SUPABASE_URL) {
  console.warn('VITE_SUPABASE_URL not set in .env — using fallback');
}
if (import.meta.env.DEV && !import.meta.env.VITE_SUPABASE_ANON_KEY) {
  console.warn('VITE_SUPABASE_ANON_KEY not set in .env');
}

export const SUPABASE_URL = supabaseUrl;

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    storage: localStorage,
    persistSession: true,
    autoRefreshToken: true,
  }
});

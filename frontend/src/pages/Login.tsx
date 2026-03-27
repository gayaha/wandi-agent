import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Loader2, Instagram } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

const Login = () => {
  const navigate = useNavigate();
  const { language, setLanguage, t } = useLanguage();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (isSignUp) {
      if (password !== confirmPassword) {
        toast.error(t('login.passwordMismatch'));
        setLoading(false);
        return;
      }
      const { error } = await supabase.auth.signUp({ email, password });
      if (error) {
        toast.error(error.message);
      } else {
        toast.success(t('login.signUpSuccess'));
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        toast.error(error.message);
      } else {
        navigate('/');
      }
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center gradient-bg relative">
      <div className="absolute inset-0 bg-background" />
      <div className="absolute inset-0 gradient-bg" />

      <button
        type="button"
        onClick={() => setLanguage(language === 'he' ? 'en' : 'he')}
        className="absolute top-4 right-4 z-20 px-3 py-1.5 text-sm font-medium rounded-md bg-secondary/80 hover:bg-secondary text-foreground transition-colors"
      >
        {language === 'he' ? 'EN' : 'HE'}
      </button>

      <div className="relative z-10 w-full max-w-md mx-4">
        <div className="glass p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Instagram className="h-8 w-8 text-primary" />
              <h1 className="text-3xl font-bold text-gradient">Wandi AI</h1>
            </div>
            <p className="text-muted-foreground">{t('login.subtitle')}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('login.email')}</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                required
                className="bg-secondary/50 border-border"
                dir="ltr"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('login.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="--------"
                required
                className="bg-secondary/50 border-border"
                dir="ltr"
              />
            </div>

            {isSignUp && (
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">{t('login.confirmPassword')}</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="--------"
                  required
                  className="bg-secondary/50 border-border"
                  dir="ltr"
                />
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full gradient-primary text-primary-foreground font-semibold h-11"
            >
              {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
              {isSignUp ? t('login.signUp') : t('login.signIn')}
            </Button>
          </form>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-sm text-muted-foreground hover:text-primary transition-colors"
            >
              {isSignUp ? t('login.hasAccount') : t('login.noAccount')}
            </button>
          </div>

          <div className="flex items-center justify-center gap-3 text-xs text-muted-foreground pt-2 border-t border-border/50">
            <a href="/privacy" className="hover:text-primary transition-colors">Privacy Policy</a>
            <span>.</span>
            <a href="/terms" className="hover:text-primary transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

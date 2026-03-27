import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { supabase } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Instagram, ArrowRight, ArrowLeft, Globe, LogOut, Menu } from 'lucide-react';

interface ChatHeaderProps {
  onToggleSidebar?: () => void;
}

export default function ChatHeader({ onToggleSidebar }: ChatHeaderProps) {
  const navigate = useNavigate();
  const { language, t, setLanguage, direction } = useLanguage();

  const BackArrow = direction === 'rtl' ? ArrowRight : ArrowLeft;

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'he' ? 'en' : 'he');
  };

  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-background/80 backdrop-blur-md shrink-0">
      <div className="flex items-center gap-2">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" className="md:hidden h-8 w-8" onClick={onToggleSidebar}>
            <Menu className="h-4 w-4" />
          </Button>
        )}
        <Instagram className="h-5 w-5 text-primary" />
        <span className="text-lg font-bold text-gradient">{t('chat.title')}</span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={toggleLanguage}
          className="gap-1.5 text-xs font-medium rounded-lg px-2.5 h-8"
        >
          <Globe className="h-3.5 w-3.5" />
          {language === 'he' ? 'EN' : 'HE'}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => navigate('/')} className="gap-1.5 text-xs h-8">
          <BackArrow className="h-3.5 w-3.5" />
          {t('chat.backToApp')}
        </Button>
        <Button variant="ghost" size="icon" onClick={handleSignOut} title={t('nav.signOut')} className="h-8 w-8">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}

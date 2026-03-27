import { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useMetaConnection } from '@/hooks/useMetaConnection';
import { useLanguage } from '@/contexts/LanguageContext';
import { supabase } from '@/lib/supabase';
import {
  LayoutDashboard,
  CalendarDays,
  FileImage,
  Settings,
  LogOut,
  Plus,
  Instagram,
  Sparkles,
  MessageCircle,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dock, DockIcon, DockItem, DockLabel } from '@/components/ui/dock';

interface AppLayoutProps {
  children: ReactNode;
  title: string;
  onNewPost?: () => void;
}

export default function AppLayout({ children, title, onNewPost }: AppLayoutProps) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { connection } = useMetaConnection();
  const { language, direction, setLanguage, t } = useLanguage();

  const navItems = [
    { title: t('nav.dashboard'), href: '/', icon: LayoutDashboard },
    { title: t('nav.media'), href: '/media', icon: FileImage },
    { title: t('nav.studio'), href: '/content', icon: Sparkles },
    { title: t('nav.calendar'), href: '/calendar', icon: CalendarDays },
    { title: t('nav.chat'), href: '/chat', icon: MessageCircle },
    { title: t('nav.settings'), href: '/settings', icon: Settings },
  ];

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };

  const toggleLanguage = () => {
    setLanguage(language === 'he' ? 'en' : 'he');
  };

  return (
    <div className="min-h-screen flex flex-col" dir={direction}>
      {/* Top header */}
      <header className="h-16 border-b border-border flex items-center justify-between px-6 bg-background/80 backdrop-blur-md sticky top-0 z-30 shadow-soft">
        <div className="flex items-center gap-3">
          <Instagram className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold text-gradient">Wandi AI</span>
        </div>
        <div className="flex items-center gap-3">
          {connection && (
            <span className="text-xs text-muted-foreground hidden sm:inline">
              @{connection.ig_username}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleLanguage}
            className="gap-1.5 text-xs font-medium rounded-lg px-2.5 h-8"
          >
            <Globe className="h-3.5 w-3.5" />
            {language === 'he' ? 'EN' : 'HE'}
          </Button>
          {onNewPost && (
            <Button onClick={onNewPost} className="gradient-primary text-primary-foreground gap-2 btn-soft shadow-soft rounded-xl">
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline">{t('nav.newPost')}</span>
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={handleSignOut} title={t('nav.signOut')}>
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6 pb-40 gradient-bg organic-bg">
        {children}
      </main>

      {/* Bottom Dock Navigation */}
      <div className="fixed bottom-4 left-0 right-0 z-50 flex justify-center">
        <Dock
          magnification={60}
          distance={120}
          panelHeight={56}
          className="gap-3"
        >
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <DockItem
                key={item.href}
                onClick={() => navigate(item.href)}
              >
                <DockLabel>{item.title}</DockLabel>
                <DockIcon>
                  <item.icon
                    className={`h-full w-full transition-colors ${
                      isActive ? 'text-primary' : 'text-muted-foreground'
                    }`}
                  />
                </DockIcon>
              </DockItem>
            );
          })}
        </Dock>
      </div>
    </div>
  );
}

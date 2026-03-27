import { Insights } from "@/hooks/useInsights";
import { Trophy, Flame, Star, Target, Zap, Crown, Medal, Rocket, Heart, TrendingUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useLanguage } from '@/contexts/LanguageContext';
import { TranslationKey } from '@/lib/translations';

interface Award {
  id: string;
  icon: typeof Trophy;
  titleKey: TranslationKey;
  descriptionKey: TranslationKey;
  unlocked: boolean;
  progress: number; // 0-100
  color: string;
  glowColor: string;
}

function buildAwards(insights: Insights): Award[] {
  const { follower_count, reach, impressions, engagement_rate, top_posts } = insights;
  const postCount = top_posts?.length ?? 0;
  const totalLikes = top_posts?.reduce((s, p) => s + p.likes, 0) ?? 0;
  const totalComments = top_posts?.reduce((s, p) => s + p.comments, 0) ?? 0;
  const maxReach = top_posts?.reduce((m, p) => Math.max(m, p.reach), 0) ?? 0;

  return [
    {
      id: "first_steps",
      icon: Rocket,
      titleKey: 'awards.firstSteps',
      descriptionKey: 'awards.firstStepsDesc',
      unlocked: postCount >= 3,
      progress: Math.min(100, (postCount / 3) * 100),
      color: "from-blue-500 to-cyan-400",
      glowColor: "shadow-blue-500/30",
    },
    {
      id: "content_machine",
      icon: Flame,
      titleKey: 'awards.contentMachine',
      descriptionKey: 'awards.contentMachineDesc',
      unlocked: postCount >= 10,
      progress: Math.min(100, (postCount / 10) * 100),
      color: "from-orange-500 to-red-400",
      glowColor: "shadow-orange-500/30",
    },
    {
      id: "community_builder",
      icon: Heart,
      titleKey: 'awards.communityBuilder',
      descriptionKey: 'awards.communityBuilderDesc',
      unlocked: follower_count >= 100,
      progress: Math.min(100, (follower_count / 100) * 100),
      color: "from-pink-500 to-rose-400",
      glowColor: "shadow-pink-500/30",
    },
    {
      id: "influencer",
      icon: Crown,
      titleKey: 'awards.influencer',
      descriptionKey: 'awards.influencerDesc',
      unlocked: follower_count >= 1000,
      progress: Math.min(100, (follower_count / 1000) * 100),
      color: "from-amber-400 to-yellow-300",
      glowColor: "shadow-amber-400/30",
    },
    {
      id: "viral_hit",
      icon: Zap,
      titleKey: 'awards.viralHit',
      descriptionKey: 'awards.viralHitDesc',
      unlocked: maxReach >= 500,
      progress: Math.min(100, (maxReach / 500) * 100),
      color: "from-violet-500 to-purple-400",
      glowColor: "shadow-violet-500/30",
    },
    {
      id: "engagement_queen",
      icon: Star,
      titleKey: 'awards.engagementQueen',
      descriptionKey: 'awards.engagementQueenDesc',
      unlocked: engagement_rate >= 5,
      progress: Math.min(100, (engagement_rate / 5) * 100),
      color: "from-emerald-500 to-green-400",
      glowColor: "shadow-emerald-500/30",
    },
    {
      id: "like_magnet",
      icon: Target,
      titleKey: 'awards.likeMagnet',
      descriptionKey: 'awards.likeMagnetDesc',
      unlocked: totalLikes >= 500,
      progress: Math.min(100, (totalLikes / 500) * 100),
      color: "from-red-500 to-pink-400",
      glowColor: "shadow-red-500/30",
    },
    {
      id: "conversation_starter",
      icon: Medal,
      titleKey: 'awards.conversationStarter',
      descriptionKey: 'awards.conversationStarterDesc',
      unlocked: totalComments >= 100,
      progress: Math.min(100, (totalComments / 100) * 100),
      color: "from-teal-500 to-cyan-400",
      glowColor: "shadow-teal-500/30",
    },
    {
      id: "reach_master",
      icon: TrendingUp,
      titleKey: 'awards.reachMaster',
      descriptionKey: 'awards.reachMasterDesc',
      unlocked: reach >= 5000,
      progress: Math.min(100, (reach / 5000) * 100),
      color: "from-indigo-500 to-blue-400",
      glowColor: "shadow-indigo-500/30",
    },
    {
      id: "exposure_boss",
      icon: Trophy,
      titleKey: 'awards.exposureBoss',
      descriptionKey: 'awards.exposureBossDesc',
      unlocked: impressions >= 10000,
      progress: Math.min(100, (impressions / 10000) * 100),
      color: "from-yellow-500 to-orange-400",
      glowColor: "shadow-yellow-500/30",
    },
  ];
}

const AwardBadge = ({ award, index }: { award: Award; index: number }) => {
  const { t } = useLanguage();
  const Icon = award.icon;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.06, type: "spring", stiffness: 260, damping: 20 }}
          className={`relative flex flex-col items-center gap-2 p-3 rounded-xl transition-all cursor-default
            ${
              award.unlocked
                ? `bg-gradient-to-br ${award.color} shadow-lg ${award.glowColor} text-white`
                : "bg-secondary/40 text-muted-foreground/40"
            }`}
        >
          {award.unlocked && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ delay: index * 0.06 + 0.3, duration: 0.5 }}
              className="absolute -top-1 -right-1 bg-background rounded-full p-0.5"
            >
              <div className="bg-green-500 rounded-full p-0.5">
                <svg
                  className="h-2.5 w-2.5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={3}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </motion.div>
          )}
          <Icon className={`h-6 w-6 ${award.unlocked ? "drop-shadow-md" : ""}`} />
          <span className="text-[10px] font-semibold text-center leading-tight">{t(award.titleKey)}</span>
          {!award.unlocked && (
            <div className="w-full bg-muted/30 rounded-full h-1 mt-0.5">
              <div
                className={`h-1 rounded-full bg-gradient-to-r ${award.color} transition-all`}
                style={{ width: `${award.progress}%` }}
              />
            </div>
          )}
        </motion.div>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[200px] text-xs text-center">
        <p className="font-semibold">{t(award.titleKey)}</p>
        <p className="text-muted-foreground">{t(award.descriptionKey)}</p>
        {!award.unlocked && <p className="text-primary mt-1">{Math.round(award.progress)}{t('awards.completed')}</p>}
      </TooltipContent>
    </Tooltip>
  );
};

export default function AwardsSection({ insights }: { insights: Insights }) {
  const { t } = useLanguage();
  const awards = buildAwards(insights);
  const unlockedCount = awards.filter((a) => a.unlocked).length;

  return (
    <div className="glass p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <Trophy className="h-4 w-4 text-amber-400" />
            {t('awards.title')}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('awards.unlocked').replace('{count}', String(unlockedCount)).replace('{total}', String(awards.length))}
          </p>
        </div>
      </div>
      <div className="grid grid-cols-5 sm:grid-cols-5 md:grid-cols-10 gap-2">
        {awards.map((award, i) => (
          <AwardBadge key={award.id} award={award} index={i} />
        ))}
      </div>
    </div>
  );
}

import { Insights } from '@/hooks/useInsights';
import { useMemo } from 'react';
import { Lightbulb, TrendingUp, Clock, Image, Play, Images, MessageCircle, Heart, Eye } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLanguage } from '@/contexts/LanguageContext';

interface ContentInsight {
  id: string;
  icon: typeof Lightbulb;
  text: string;
  type: 'positive' | 'neutral' | 'tip';
}

function generateInsights(insights: Insights, t: (key: string) => string): ContentInsight[] {
  const { top_posts, engagement_rate, reach, follower_count } = insights;
  if (!top_posts || top_posts.length === 0) return [];

  const results: ContentInsight[] = [];

  // Analyze media type performance
  const byType: Record<string, { likes: number; comments: number; reach: number; count: number }> = {};
  for (const p of top_posts) {
    const mt = p.media_type || 'IMAGE';
    if (!byType[mt]) byType[mt] = { likes: 0, comments: 0, reach: 0, count: 0 };
    byType[mt].likes += p.likes;
    byType[mt].comments += p.comments;
    byType[mt].reach += p.reach;
    byType[mt].count++;
  }

  const typeLabels: Record<string, string> = {
    IMAGE: t('insights.typeImages'),
    VIDEO: t('insights.typeVideos'),
    CAROUSEL_ALBUM: t('insights.typeCarousels'),
  };
  const types = Object.entries(byType);

  if (types.length > 1) {
    // Best type by engagement
    const bestEngagement = types.sort((a, b) => ((b[1].likes + b[1].comments) / b[1].count) - ((a[1].likes + a[1].comments) / a[1].count))[0];
    const avgEng = ((bestEngagement[1].likes + bestEngagement[1].comments) / bestEngagement[1].count).toFixed(0);
    results.push({
      id: 'best_type_engagement',
      icon: Heart,
      text: t('insights.bestTypeEngagement')
        .replace('{type}', typeLabels[bestEngagement[0]] || bestEngagement[0])
        .replace('{avg}', avgEng),
      type: 'positive',
    });

    // Best type by reach
    const bestReach = types.sort((a, b) => (b[1].reach / b[1].count) - (a[1].reach / a[1].count))[0];
    if (bestReach[0] !== bestEngagement[0]) {
      results.push({
        id: 'best_type_reach',
        icon: Eye,
        text: t('insights.bestTypeReach')
          .replace('{type}', typeLabels[bestReach[0]] || bestReach[0])
          .replace('{avg}', Math.round(bestReach[1].reach / bestReach[1].count).toLocaleString()),
        type: 'positive',
      });
    }
  }

  // Best posting time analysis
  const hourBuckets: Record<string, { engagement: number; count: number }> = {};
  for (const p of top_posts) {
    const hour = new Date(p.timestamp).getHours();
    let bucket: string;
    if (hour >= 6 && hour < 12) bucket = t('insights.timeMorning');
    else if (hour >= 12 && hour < 17) bucket = t('insights.timeAfternoon');
    else if (hour >= 17 && hour < 21) bucket = t('insights.timeEvening');
    else bucket = t('insights.timeNight');

    if (!hourBuckets[bucket]) hourBuckets[bucket] = { engagement: 0, count: 0 };
    hourBuckets[bucket].engagement += p.likes + p.comments;
    hourBuckets[bucket].count++;
  }

  const bucketEntries = Object.entries(hourBuckets).filter(([, v]) => v.count >= 2);
  if (bucketEntries.length > 1) {
    const bestTime = bucketEntries.sort((a, b) => (b[1].engagement / b[1].count) - (a[1].engagement / a[1].count))[0];
    results.push({
      id: 'best_time',
      icon: Clock,
      text: t('insights.bestTime').replace('{time}', bestTime[0]),
      type: 'tip',
    });
  }

  // Engagement rate insight
  if (engagement_rate >= 5) {
    results.push({
      id: 'high_engagement',
      icon: TrendingUp,
      text: t('insights.highEngagement').replace('{rate}', engagement_rate.toFixed(1)),
      type: 'positive',
    });
  } else if (engagement_rate >= 2) {
    results.push({
      id: 'decent_engagement',
      icon: TrendingUp,
      text: t('insights.decentEngagement').replace('{rate}', engagement_rate.toFixed(1)),
      type: 'neutral',
    });
  } else if (engagement_rate > 0) {
    results.push({
      id: 'low_engagement',
      icon: MessageCircle,
      text: t('insights.lowEngagement').replace('{rate}', engagement_rate.toFixed(1)),
      type: 'tip',
    });
  }

  // Caption length analysis
  const withLongCaption = top_posts.filter(p => (p.caption?.length ?? 0) > 150);
  const withShortCaption = top_posts.filter(p => (p.caption?.length ?? 0) <= 150 && (p.caption?.length ?? 0) > 0);

  if (withLongCaption.length >= 2 && withShortCaption.length >= 2) {
    const longAvg = withLongCaption.reduce((s, p) => s + p.likes + p.comments, 0) / withLongCaption.length;
    const shortAvg = withShortCaption.reduce((s, p) => s + p.likes + p.comments, 0) / withShortCaption.length;

    if (longAvg > shortAvg * 1.3) {
      results.push({
        id: 'long_captions_win',
        icon: Lightbulb,
        text: t('insights.longCaptionsWin'),
        type: 'positive',
      });
    } else if (shortAvg > longAvg * 1.3) {
      results.push({
        id: 'short_captions_win',
        icon: Lightbulb,
        text: t('insights.shortCaptionsWin'),
        type: 'positive',
      });
    }
  }

  // Reach vs followers ratio
  if (follower_count > 0 && reach > 0) {
    const reachRatio = reach / follower_count;
    if (reachRatio > 1.5) {
      results.push({
        id: 'viral_reach',
        icon: TrendingUp,
        text: t('insights.viralReach').replace('{ratio}', reachRatio.toFixed(1)),
        type: 'positive',
      });
    }
  }

  // Most commented post topic hint
  const mostCommented = [...top_posts].sort((a, b) => b.comments - a.comments)[0];
  if (mostCommented && mostCommented.comments > 5) {
    const preview = mostCommented.caption?.slice(0, 60) || t('insights.noCaption');
    const suffix = mostCommented.caption && mostCommented.caption.length > 60 ? '...' : '';
    results.push({
      id: 'most_discussed',
      icon: MessageCircle,
      text: t('insights.mostDiscussed')
        .replace('{preview}', preview + suffix)
        .replace('{count}', String(mostCommented.comments)),
      type: 'tip',
    });
  }

  return results.slice(0, 6);
}

const typeStyles: Record<string, string> = {
  positive: 'border-emerald-500/30 bg-emerald-500/5',
  neutral: 'border-blue-500/30 bg-blue-500/5',
  tip: 'border-amber-500/30 bg-amber-500/5',
};

const iconStyles: Record<string, string> = {
  positive: 'text-emerald-400',
  neutral: 'text-blue-400',
  tip: 'text-amber-400',
};

export default function ContentInsightsSection({ insights }: { insights: Insights }) {
  const { t } = useLanguage();
  const insightsList = useMemo(() => generateInsights(insights, t), [insights, t]);

  if (insightsList.length === 0) return null;

  return (
    <div className="glass p-6 space-y-4">
      <div>
        <h3 className="font-semibold flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-400" />
          {t('insights.title')}
        </h3>
        <p className="text-xs text-muted-foreground mt-0.5">{t('insights.subtitle')}</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {insightsList.map((insight, i) => {
          const Icon = insight.icon;
          return (
            <motion.div
              key={insight.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`flex items-start gap-3 p-4 rounded-xl border ${typeStyles[insight.type]}`}
            >
              <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${iconStyles[insight.type]}`} />
              <p className="text-sm leading-relaxed">{insight.text}</p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

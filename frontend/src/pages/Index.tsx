import { useMetaConnection } from "@/hooks/useMetaConnection";
import { useInsights, Insights } from "@/hooks/useInsights";
import { usePosts } from "@/hooks/usePosts";
import AppLayout from "@/components/AppLayout";
import CreatePostModal from "@/components/CreatePostModal";
import AwardsSection from "@/components/AwardsSection";
import ContentInsightsSection from "@/components/ContentInsightsSection";
import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Instagram,
  Users,
  Eye,
  BarChart3,
  TrendingUp,
  Loader2,
  Heart,
  MessageCircle,
  Clock,
  AlertTriangle,
  Info,
  Play,
  Images,
  Image,
  ArrowUpDown,
  Filter,
} from "lucide-react";
import { format } from "date-fns";
import GlassAreaChart from "@/components/GlassAreaChart";
import { useLanguage } from "@/contexts/LanguageContext";

const StatCard = ({
  icon: Icon,
  label,
  value,
  color,
  explanation,
}: {
  icon: any;
  label: string;
  value: string | number;
  color: string;
  explanation?: string;
}) => (
  <div className="stat-card animate-fade-up group">
    <div className="flex items-center justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-1.5">
          <p className="text-sm text-muted-foreground">{label}</p>
          {explanation && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="h-3.5 w-3.5 text-muted-foreground/50 cursor-help hover:text-primary transition-colors" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[240px] text-xs leading-relaxed">
                {explanation}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <p className="text-2xl font-bold">{typeof value === "number" ? value.toLocaleString() : value}</p>
      </div>
      <div className={`p-3 rounded-xl ${color} transition-transform group-hover:scale-110`}>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  </div>
);

const mediaTypeIcon: Record<string, typeof Image> = {
  IMAGE: Image,
  VIDEO: Play,
  CAROUSEL_ALBUM: Images,
};

const Dashboard = () => {
  const { t } = useLanguage();
  const { connection, loading: connLoading, connectInstagram } = useMetaConnection();
  const { insights, loading: insightsLoading } = useInsights(connection?.id);
  const { posts: upcomingPosts } = usePosts(connection?.id, "pending");
  const [createPostOpen, setCreatePostOpen] = useState(false);
  const [chartMetric, setChartMetric] = useState<"reach" | "impressions">("reach");

  // Top posts filters
  const [postTypeFilter, setPostTypeFilter] = useState<string>("all");
  const [postSortBy, setPostSortBy] = useState<string>("engagement");
  const [postTimeFilter, setPostTimeFilter] = useState<string>("all");

  const statExplanations: Record<string, string> = {
    followers: t('stat.followers'),
    reach: t('stat.reach'),
    impressions: t('stat.impressions'),
    engagement: t('stat.engagement'),
  };

  const mediaTypeLabel: Record<string, string> = {
    IMAGE: t('media.image'),
    VIDEO: t('media.video'),
    CAROUSEL_ALBUM: t('media.carousel'),
  };

  const filteredTopPosts = useMemo(() => {
    if (!insights?.top_posts) return [];
    let posts = [...insights.top_posts];

    // Filter by media type
    if (postTypeFilter !== "all") {
      posts = posts.filter((p) => p.media_type === postTypeFilter);
    }

    // Filter by time
    if (postTimeFilter !== "all") {
      const now = Date.now();
      const daysMap: Record<string, number> = { "7": 7, "14": 14, "30": 30 };
      const days = daysMap[postTimeFilter];
      if (days) {
        posts = posts.filter((p) => (now - new Date(p.timestamp).getTime()) / 86400000 <= days);
      }
    }

    // Sort
    if (postSortBy === "engagement") {
      posts.sort((a, b) => b.likes + b.comments - (a.likes + a.comments));
    } else if (postSortBy === "likes") {
      posts.sort((a, b) => b.likes - a.likes);
    } else if (postSortBy === "comments") {
      posts.sort((a, b) => b.comments - a.comments);
    } else if (postSortBy === "reach") {
      posts.sort((a, b) => b.reach - a.reach);
    } else if (postSortBy === "recent") {
      posts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    }

    return posts;
  }, [insights?.top_posts, postTypeFilter, postSortBy, postTimeFilter]);

  if (connLoading) {
    return (
      <AppLayout title={t('dashboard.title')}>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!connection) {
    return (
      <AppLayout title={t('dashboard.title')}>
        <div className="flex-1 flex items-center justify-center">
          <div className="glass p-12 text-center max-w-md space-y-4">
            <Instagram className="h-16 w-16 text-primary mx-auto" />
            <h2 className="text-2xl font-bold">{t('dashboard.connectTitle')}</h2>
            <p className="text-muted-foreground">{t('dashboard.connectDesc')}</p>
            <Button onClick={connectInstagram} className="gradient-primary text-primary-foreground font-semibold px-8 h-11">
              {t('dashboard.connectNow')}
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  const tokenExpiresAt = connection?.token_expires_at ? new Date(connection.token_expires_at) : null;
  const daysUntilExpiry = tokenExpiresAt
    ? Math.ceil((tokenExpiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;
  const showTokenWarning = daysUntilExpiry !== null && daysUntilExpiry <= 14;

  return (
    <AppLayout title={t('dashboard.title')} onNewPost={() => setCreatePostOpen(true)}>
      <div className="space-y-6">
        {showTokenWarning && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">
                {daysUntilExpiry! <= 0
                  ? t('dashboard.tokenExpired')
                  : t('dashboard.tokenExpiring').replace('{days}', String(daysUntilExpiry))}
              </p>
              <p className="text-sm text-yellow-400/70">{t('dashboard.tokenRenew')}</p>
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Users}
            label={t('dashboard.followers')}
            value={insights?.follower_count ?? "\u2014"}
            color="bg-primary/20 text-primary"
            explanation={statExplanations.followers}
          />
          <StatCard
            icon={Eye}
            label={t('dashboard.reach')}
            value={insights?.reach ?? "\u2014"}
            color="bg-success/20 text-success"
            explanation={statExplanations.reach}
          />
          <StatCard
            icon={BarChart3}
            label={t('dashboard.impressions')}
            value={insights?.impressions ?? "\u2014"}
            color="bg-warning/20 text-warning"
            explanation={statExplanations.impressions}
          />
          <StatCard
            icon={TrendingUp}
            label={t('dashboard.engagement')}
            value={insights?.engagement_rate ? `${insights.engagement_rate.toFixed(1)}%` : "\u2014"}
            color="bg-destructive/20 text-destructive"
            explanation={statExplanations.engagement}
          />
        </div>

        {/* Awards */}
        {insights && <AwardsSection insights={insights} />}

        {/* Content Insights */}
        {insights && <ContentInsightsSection insights={insights} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={chartMetric === "reach" ? "default" : "ghost"}
                onClick={() => setChartMetric("reach")}
                className={chartMetric === "reach" ? "gradient-primary text-primary-foreground" : ""}
              >
                {t('dashboard.reach')}
              </Button>
              <Button
                size="sm"
                variant={chartMetric === "impressions" ? "default" : "ghost"}
                onClick={() => setChartMetric("impressions")}
                className={chartMetric === "impressions" ? "gradient-primary text-primary-foreground" : ""}
              >
                {t('dashboard.impressions')}
              </Button>
            </div>
            {insightsLoading ? (
              <div className="h-64 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <GlassAreaChart
                title={chartMetric === "reach" ? t('dashboard.dailyReach') : t('dashboard.dailyImpressions')}
                data={(insights?.daily_stats ?? []).map((s) => ({
                  label: s.date.slice(5),
                  value: s[chartMetric],
                }))}
              />
            )}
          </div>

          {/* Upcoming posts */}
          <div className="glass p-6 space-y-4">
            <h3 className="font-semibold">{t('dashboard.upcomingPosts')}</h3>
            {upcomingPosts.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">{t('dashboard.noScheduledPosts')}</p>
            ) : (
              <div className="space-y-3">
                {upcomingPosts.slice(0, 5).map((post) => (
                  <div key={post.id} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30">
                    {post.media_url && (
                      <img src={post.media_url} className="h-10 w-10 rounded-md object-cover" alt="" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{post.caption || t('dashboard.noCaption')}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {format(new Date(post.scheduled_at), "dd/MM HH:mm")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top posts */}
        {insights?.top_posts && insights.top_posts.length > 0 && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-semibold">{t('dashboard.topPosts')}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{t('dashboard.topPostsDesc')}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Select value={postTypeFilter} onValueChange={setPostTypeFilter}>
                  <SelectTrigger className="h-8 w-[120px] text-xs glass border-border/50">
                    <Filter className="h-3 w-3 ml-1 shrink-0" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('filter.all')}</SelectItem>
                    <SelectItem value="IMAGE">{t('filter.images')}</SelectItem>
                    <SelectItem value="VIDEO">{t('filter.videos')}</SelectItem>
                    <SelectItem value="CAROUSEL_ALBUM">{t('filter.carousels')}</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={postTimeFilter} onValueChange={setPostTimeFilter}>
                  <SelectTrigger className="h-8 w-[120px] text-xs glass border-border/50">
                    <Clock className="h-3 w-3 ml-1 shrink-0" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('filter.allTime')}</SelectItem>
                    <SelectItem value="7">{t('filter.lastWeek')}</SelectItem>
                    <SelectItem value="14">{t('filter.twoWeeks')}</SelectItem>
                    <SelectItem value="30">{t('filter.lastMonth')}</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={postSortBy} onValueChange={setPostSortBy}>
                  <SelectTrigger className="h-8 w-[130px] text-xs glass border-border/50">
                    <ArrowUpDown className="h-3 w-3 ml-1 shrink-0" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="engagement">{t('filter.engagement')}</SelectItem>
                    <SelectItem value="likes">{t('filter.likes')}</SelectItem>
                    <SelectItem value="comments">{t('filter.comments')}</SelectItem>
                    <SelectItem value="reach">{t('filter.reach')}</SelectItem>
                    <SelectItem value="recent">{t('filter.newest')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {filteredTopPosts.length === 0 ? (
              <div className="glass p-8 text-center text-muted-foreground">
                <p className="text-sm">{t('dashboard.noMatchingPosts')}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTopPosts.slice(0, 6).map((post) => {
                  const TypeIcon = mediaTypeIcon[post.media_type] || Image;
                  const typeLabel = mediaTypeLabel[post.media_type] || t('dashboard.post');
                  return (
                    <div key={post.id} className="glass-hover overflow-hidden group">
                      <div className="relative">
                        <img
                          src={post.thumbnail_url || post.media_url}
                          className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-105"
                          alt=""
                        />
                        <div className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full bg-background/80 backdrop-blur-sm text-xs font-medium">
                          <TypeIcon className="h-3 w-3" />
                          {typeLabel}
                        </div>
                        {post.media_type === "VIDEO" && (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="p-3 rounded-full bg-background/60 backdrop-blur-sm">
                              <Play className="h-6 w-6 text-foreground" />
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="p-4 space-y-2">
                        <p className="text-sm line-clamp-2">{post.caption || t('dashboard.noCaption')}</p>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Heart className="h-4 w-4" />
                            {post.likes.toLocaleString()}
                          </span>
                          <span className="flex items-center gap-1">
                            <MessageCircle className="h-4 w-4" />
                            {post.comments.toLocaleString()}
                          </span>
                          <span className="flex items-center gap-1">
                            <Eye className="h-4 w-4" />
                            {post.reach.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {connection && (
        <CreatePostModal open={createPostOpen} onOpenChange={setCreatePostOpen} connectionId={connection.id} />
      )}
    </AppLayout>
  );
};

export default Dashboard;
